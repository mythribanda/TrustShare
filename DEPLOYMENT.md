# TrustShare AWS Production Deployment Guide

This guide provides click-by-click manual instructions to deploy the complete **TrustShare** production stack to a single **AWS EC2 Ubuntu 22.04 LTS** instance with real HTTPS via **Let's Encrypt**, **AWS S3** for envelope-encrypted file storage, and automated GitHub Actions CI/CD.

---

## Architecture Overview

```
                                      Internet
                                         │
                                   Ports 80 & 443
                                         │
                                         ▼
                 ┌────────────────────────────────────────────────┐
                 │                Caddy (Docker)                  │
                 │   • Automated Let's Encrypt TLS (HSTS enabled) │
                 │   • Serves static React/Vite SPA bundle        │
                 └───────┬────────────────────────────────┬───────┘
                         │                                │
                 /api/* requests                    Static assets
                         │                                │
                         ▼                                ▼
                 ┌───────────────┐                  /srv (built HTML/JS)
                 │    FastAPI    │
                 │    Backend    │
                 └───────┬───────┘
                         │
        ┌────────────────┼────────────────┬────────────────┐
        ▼                ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  PostgreSQL  │ │   MongoDB    │ │    Redis     │ │    AWS S3    │
│  (User/RBAC) │ │(Audit/Events)│ │ (Sessions/RL)│ │  (Encrypted) │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

---

## Step 1: Create the AWS S3 Bucket

Every uploaded file is envelope-encrypted server-side with its own unique AES-256-GCM data encryption key and stored as an encrypted blob in Amazon S3.

1. Sign in to the [AWS Management Console](https://console.aws.amazon.com/).
2. In the top search bar, navigate to **S3** and click **Create bucket**.
3. Configure the bucket details:
   - **Bucket name**: Enter a globally unique name, e.g. `trustshare-storage-mythri-prod`.
   - **AWS Region**: Select `ap-south-1` (Asia Pacific - Mumbai) or your preferred region.
   - **Object Ownership**: Leave **ACLs disabled (recommended)** selected.
   - **Block Public Access settings for this bucket**:
     - Ensure **Block all public access** is **CHECKED** (all 4 checkboxes below it checked). *All file objects are private; users download exclusively via backend authenticated/signed streams.*
   - **Bucket Versioning**: Keep **Disable** (or Enable if desired).
   - **Default encryption**: Leave **Server-side encryption with Amazon S3 managed keys (SSE-S3)** selected.
4. Click **Create bucket** at the bottom.

---

## Step 2: Create IAM Policy & User for S3 Storage

Create a dedicated IAM user with least-privilege permissions granting access exclusively to your TrustShare bucket.

### 2.1 Create the IAM Policy
1. Navigate to **IAM** -> **Policies** -> **Create policy**.
2. Select the **JSON** policy editor tab.
3. Replace the placeholder with the following policy (substituting your actual bucket name from Step 1):
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "TrustShareListBucket",
         "Effect": "Allow",
         "Action": ["s3:ListBucket"],
         "Resource": "arn:aws:s3:::YOUR-BUCKET-NAME"
       },
       {
         "Sid": "TrustShareObjectOperations",
         "Effect": "Allow",
         "Action": [
           "s3:PutObject",
           "s3:GetObject",
           "s3:DeleteObject",
           "s3:AbortMultipartUpload"
         ],
         "Resource": "arn:aws:s3:::YOUR-BUCKET-NAME/*"
       }
     ]
   }
   ```
4. Click **Next**.
5. Set **Policy name**: `TrustShareS3AccessPolicy`.
6. Click **Create policy**.

### 2.2 Create IAM User & Access Keys
1. In the IAM console, go to **Users** -> **Create user**.
2. Set **User name**: `trustshare-s3-service`.
3. Do **NOT** enable AWS Management Console access (programmatic access only). Click **Next**.
4. In permissions, choose **Attach policies directly**.
5. Search for and select `TrustShareS3AccessPolicy`. Click **Next** -> **Create user**.
6. Click on the newly created user `trustshare-s3-service`.
7. Go to the **Security credentials** tab.
8. Scroll to **Access keys** and click **Create access key**.
9. Select use case **Application running outside AWS** (or Other). Click **Next**.
10. Click **Create access key**.
11. **Save these credentials immediately**:
    - **Access Key ID**: (e.g. `AKIAIOSFODNN7EXAMPLE`)
    - **Secret Access Key**: (e.g. `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`)

---

## Step 3: Launch the EC2 Instance (`t3.small`)

1. In the AWS console, navigate to **EC2** -> **Launch instance**.
2. **Name and tags**: `TrustShare-Production`.
3. **Application and OS Images (Amazon Machine Image)**:
   - Select **Ubuntu**.
   - Ensure the version is **Ubuntu Server 22.04 LTS (HVM), SSD Volume Type**, Architecture: **64-bit (x86)**.
4. **Instance type**:
   - Choose `t3.small` (2 vCPUs, 2 GiB memory).
5. **Key pair (login)**:
   - Click **Create new key pair**.
   - Key pair name: `trustshare-ec2-key`.
   - Key pair type: **RSA**.
   - Private key file format: **.pem** (for OpenSSH, macOS, Linux, Windows 10/11).
   - Click **Create key pair** and save the downloaded file into `~/.ssh/trustshare-ec2-key.pem`.
   - Set strict local permissions:
     ```bash
     chmod 400 ~/.ssh/trustshare-ec2-key.pem
     ```
6. **Network settings**:
   - Click **Edit** network settings.
   - Ensure **Auto-assign public IP** is enabled.
   - Select **Create security group**.
   - Security group name: `trustshare-prod-sg`.
   - Configure Firewall (Security group rules):
     - **Rule 1 (SSH)**: Type `SSH`, Port `22`, Source: `My IP` (or `0.0.0.0/0` if dynamic IP).
     - **Rule 2 (HTTP)**: Type `HTTP`, Port `80`, Source: `Anywhere-IPv4` (`0.0.0.0/0`).
     - **Rule 3 (HTTPS)**: Type `HTTPS`, Port `443`, Source: `Anywhere-IPv4` (`0.0.0.0/0`).
     - *(Optional: Add Rule 4 for HTTPS IPv6 `::/0` and HTTP IPv6 `::/0`)*.
     - *Notice: Internal database ports (5432, 27017, 6379, 8000) are NOT exposed.*
7. **Configure storage**:
   - Set root volume to **30 GiB**, Volume type: **gp3**.
8. Click **Launch instance**.

---

## Step 4: Allocate and Associate an Elastic IP

An Elastic IP provides a permanent, fixed public IPv4 address that does not change upon server reboots.

1. In the EC2 console left sidebar, navigate to **Network & Security** -> **Elastic IPs**.
2. Click **Allocate Elastic IP address**.
3. Leave default settings (Amazon's pool of IPv4 addresses) and click **Allocate**.
4. Select the allocated Elastic IP checkbox.
5. Click **Actions** -> **Associate Elastic IP address**.
6. Set:
   - **Resource type**: `Instance`.
   - **Instance**: Choose your running `TrustShare-Production` instance.
   - **Private IP address**: Select the private IP of the instance.
7. Click **Associate**.
8. Copy the **Public IPv4 address** (e.g. `13.235.45.67`).

---

## Step 5: Configure Free Domain via DuckDNS

Caddy requires a valid domain name pointing to your Elastic IP to issue an automatic Let's Encrypt TLS certificate.

1. Navigate to [DuckDNS](https://www.duckdns.org).
2. Sign in using GitHub, Google, or your preferred provider.
3. Under **domains**, choose a subdomain prefix (e.g. `trustshare-demo`), and click **add domain**.
4. In the **current ip** field next to your domain, paste your EC2 **Elastic IP address** (from Step 4).
5. Click **update ip**.
6. Your domain is now active:
   `trustshare-demo.duckdns.org` -> Points to your EC2 Elastic IP.

---

## Step 6: Connect to EC2 & Run the Bootstrap Script

1. Connect to your instance via SSH:
   ```bash
   ssh -i ~/.ssh/trustshare-ec2-key.pem ubuntu@<YOUR-ELASTIC-IP>
   ```

2. Run the automated setup script:
   ```bash
   # Clone repository
   git clone https://github.com/mythribanda/TrustShare.git
   cd TrustShare

   # Make scripts executable
   chmod +x deploy/setup-ec2.sh deploy/backup.sh

   # Run system setup (Docker, 2GB swap, permissions)
   ./deploy/setup-ec2.sh
   ```

3. Configure your production environment variables:
   ```bash
   nano .env
   ```
   Fill in your actual production values:
   - `DOMAIN=trustshare-demo.duckdns.org`
   - `COOKIE_SECURE=true`
   - `STORAGE_PROVIDER=s3`
   - `S3_ENDPOINT_URL=` *(must be left blank for real AWS S3)*
   - `S3_REGION=ap-south-1`
   - `S3_BUCKET=your-actual-bucket-name`
   - `S3_ACCESS_KEY_ID=AKIA...`
   - `S3_SECRET_ACCESS_KEY=...`

   *(Generate real secrets for JWT, MFA, and master keys directly on the server)*:
   ```bash
   # Generate JWT_SECRET
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"

   # Generate MFA_ENCRYPTION_KEY
   python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"

   # Generate MASTER_KEYS
   python3 -c "import base64, os; print('1:' + base64.b64encode(os.urandom(32)).decode())"

   # Generate DB passwords
   python3 -c "import secrets; print(secrets.token_urlsafe(24))"
   ```

4. Launch the production containers:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   ```

5. Create the initial administrative account:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python -m app.scripts.create_admin --email admin@yourdomain.com --name "Administrator"
   ```

---

## Step 7: Configure Automated Daily Database Backups

Ensure your PostgreSQL and MongoDB databases are backed up nightly.

1. Open crontab on the EC2 server:
   ```bash
   crontab -e
   ```
2. Add the following line at the end (runs every night at 2:00 AM UTC):
   ```cron
   0 2 * * * /home/ubuntu/TrustShare/deploy/backup.sh >> /home/ubuntu/backups/trustshare/backup.log 2>&1
   ```
3. Verify backups can run manually:
   ```bash
   /home/ubuntu/TrustShare/deploy/backup.sh
   ls -lh ~/backups/trustshare/
   ```

---

## Step 8: Set Up GitHub Actions CI/CD Pipeline

The `.github/workflows/deploy.yml` workflow automatically deploys changes pushed to the `main` branch.

1. In your GitHub repository, navigate to **Settings** -> **Secrets and variables** -> **Actions**.
2. Click **New repository secret** and add the following 3 secrets:

   | Secret Name | Value |
   |---|---|
   | `EC2_HOST` | Your Elastic IP address or DuckDNS domain name |
   | `EC2_USER` | `ubuntu` |
   | `EC2_SSH_KEY` | The full content of `~/.ssh/trustshare-ec2-key.pem` (including the `-----BEGIN ...-----` and `-----END ...-----` headers) |

3. Any push to `main` will now trigger an automated SSH zero-downtime deployment.

---

## Step 9: Verification & Smoke Testing

1. Open `https://<YOUR-DOMAIN>.duckdns.org` in your web browser.
2. Confirm the **SSL Padlock icon** indicates a valid Let's Encrypt certificate.
3. Test core operations:
   - **Register/Login**: Sign in with the administrator account created in Step 6.5.
   - **Upload**: Upload a test PDF or image.
   - **S3 Verification**: Open AWS S3 Console -> navigate to your bucket. Confirm the uploaded encrypted blob exists under `files/`.
   - **Download**: Download the file from the web UI; verify the decrypted file opens properly.
   - **Share Link**: Create an expiring share link; open it in an incognito window and verify the public download works.
   - **Admin Console**: Access the `/admin` dashboard to inspect system status and security metrics.
