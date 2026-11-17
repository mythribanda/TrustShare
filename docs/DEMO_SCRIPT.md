# TrustShare: 7-Minute Mentor Demo Script

**Project:** TrustShare — Encrypted Document Management & Secure Collaboration Platform  
**Target Audience:** Technical Mentor / Project Evaluator  
**Total Duration:** 7 Minutes  
**Demo URL:** [https://localhost:8443](https://localhost:8443)  

---

## Demo Credentials & Quick Reference

| Account / Resource | Identifier / URL | Credentials / Details | Role / Purpose |
|---|---|---|---|
| **Demo User** | `demo.user@example.com` | `DemoUserPass2026!#` | Standard User (file owner, sharing, vault) |
| **Administrator** | `admin@example.com` | `<ADMIN_PASSWORD>$Adm1nSec` | Platform Admin (alerts, audit log, analytics) |
| **Share Link 1** | [Expiring Link](https://localhost:8443/s/wq8hzrKKmcwv1DvHJQ5mjPRRA-zot24FVwmZGSjXb-M) | No password, 1-hour expiration | View-only link demonstration |
| **Share Link 2** | [Protected Link](https://localhost:8443/s/RE4JVPl7bC6ajig2M-uvU1QQKwQlZWbc9Q_1QC4BNjk) | Password: `ShareSecret2026!` | Password-protected download link |
| **Revoked Link** | [Revoked Link](https://localhost:8443/s/HUR3KanOdc43U8LsurSi0Rg1ewSINdOI15zjnkQOhJM) | None (Returns HTTP 410) | Revocation proof demonstration |
| **Vault Password** | Personal Vault | `DemoVaultPass2026!#` | Zero-knowledge scrypt secondary key |

---

## 7-Minute Step-by-Step Demo Flow

```
[0:00 - 0:45] Intro & Landing Page
     ↓
[0:45 - 1:45] Authentication, Account Security Score & Dashboard
     ↓
[1:45 - 2:45] Secure Upload, AES-256-GCM Envelope Encryption & Folders
     ↓
[2:45 - 3:45] Secure Sharing (Expiry, Passwords, QR) & Instant Revocation
     ↓
[3:45 - 4:30] Zero-Knowledge Secure Vault & TOTP 2FA
     ↓
[4:30 - 5:45] Admin Operations Console, Live Feed & Suspicious Activity Alerts
     ↓
[5:45 - 6:30] Tamper-Evident Audit Trail & Storage Analytics
     ↓
[6:30 - 7:00] Test Results, AWS EC2 / S3 Deployment Architecture & Wrap-Up
```

---

### Step 1: Introduction & Architecture Overview (0:00 – 0:45)
- **Action:** Open [https://localhost:8443](https://localhost:8443). Show the branded landing page with responsive theme toggling.
- **What to Say:**
  > *"Good morning. Today I am presenting TrustShare, a secure document management and file sharing platform built as a zero-trust, private alternative to public cloud storage like Google Drive.*
  >
  > *TrustShare enforces server-side envelope encryption: every file is encrypted with its own unique AES-256-GCM Data Encryption Key (DEK), chunked in 1 MB authenticated pieces, and stored in private cloud object storage. The backend is built with FastAPI, PostgreSQL, MongoDB, Redis, and Caddy with TLS 1.3 reverse proxying. Let's sign in to see how this works in practice."*

---

### Step 2: User Login & Security Posture (0:45 – 1:45)
- **Action:**
  1. Click **Sign In**.
  2. Enter `demo.user@example.com` and password `DemoUserPass2026!#`.
  3. Once on the dashboard, click the top-right user avatar and select **My Account**.
- **What to Say:**
  > *"Authentication is protected against brute-force attacks via Redis rate limiters and exponential lockouts. Passwords use bcrypt hashing with strict complexity policies.*
  >
  > *Here on the My Account page, TrustShare provides a live Account Security Score evaluating 2FA readiness, verified email, password age, active session counts, and personal vault status. Notice the Devices tab: users can monitor all active sessions across browsers and remotely terminate any single session with instant token revocation."*

---

### Step 3: Secure Upload, Envelope Encryption & Folders (1:45 – 2:45)
- **Action:**
  1. Click **My Files** in the sidebar.
  2. Point out the pre-seeded folders: **Projects**, **Reports**, and **Personal**.
  3. Click into **Projects** (contains `TrustShare_Architecture.pdf`, `Project_Roadmap_2026.txt`, `System_Architecture_Diagram.png`).
  4. Click `TrustShare_Architecture.pdf` to open the sandboxed in-app previewer.
  5. Select multiple files using the checkboxes; show the floating action bar with **Download as ZIP**.
- **What to Say:**
  > *"TrustShare's upload pipeline implements defense-in-depth: it enforces a 25 MB streaming limit, checks MIME types, and verifies initial magic bytes to reject disguised executables.*
  >
  > *When a file is uploaded, a random 256-bit AES key is generated in memory, the file is chunked into 1 MB authenticated blocks with unique nonces, and the key itself is encrypted using our active Master Key. Raw storage holds only high-entropy ciphertext—even if an attacker breached the S3 bucket directly, they cannot read a single byte.*
  >
  > *Notice our multi-select capability: selecting several files allows instant bulk moving, trashing, or downloading as a dynamically generated ZIP archive decrypted in-flight without touching server disk."*

---

### Step 4: Secure Sharing & Instant Revocation (2:45 – 3:45)
- **Action:**
  1. Click the **Share** icon on `Quarterly_Financial_Summary.csv`.
  2. Show the modal: permission (View vs. Download), custom expiry date, download count limits, optional link password, and client-side generated QR code.
  3. Open a new private browser tab (or incognito window) and navigate to **Share Link 2**:
     `https://localhost:8443/s/RE4JVPl7bC6ajig2M-uvU1QQKwQlZWbc9Q_1QC4BNjk`
  4. Show the visitor password prompt. Enter `ShareSecret2026!` to access the download.
  5. Now open the **Revoked Link**:
     `https://localhost:8443/s/HUR3KanOdc43U8LsurSi0Rg1ewSINdOI15zjnkQOhJM`
  6. Point out the `410 Gone` error: *"The owner has revoked this share."*
- **What to Say:**
  > *"Sharing links are cryptographically random 256-bit URL-safe tokens stored only as SHA-256 hashes in PostgreSQL. Links can enforce view-only restrictions, download quotas, expiration ceilings (max 30 days), and bcrypt-hashed visitor passwords.*
  >
  > *If an owner revokes a link, the status updates instantaneously in Redis and PostgreSQL. As you see here in incognito, any subsequent request returns an immediate HTTP 410 Gone, blocking data access."*

---

### Step 5: Zero-Knowledge Secure Vault & 2FA (3:45 – 4:30)
- **Action:**
  1. Click **Vault** in the sidebar.
  2. Enter the dedicated vault password: `DemoVaultPass2026!#`.
  3. Show the unlocked vault with sensitive personal files.
  4. Click **Lock Vault**.
- **What to Say:**
  > *"For ultra-sensitive records, TrustShare features a Secure Vault. The vault uses zero-knowledge secondary encryption: file keys are wrapped inside an envelope derived from the user's vault password using scrypt.*
  >
  > *The server never retains the vault password in memory or in the database. After 5 incorrect attempts, the vault locks for 15 minutes. If a user loses their vault password, data is unrecoverable by design, ensuring complete confidentiality even from database administrators."*

---

### Step 6: Admin Operations Console, Live Feed & Security Alerts (4:30 – 5:45)
- **Action:**
  1. Open a new incognito window or log out and log in as Administrator:
     - **Email:** `admin@example.com`
     - **Password:** `<ADMIN_PASSWORD>$Adm1nSec`
  2. Navigate to **Admin Console** (`/admin/dashboard`).
  3. Point out the distinct dark operations theme with amber/violet styling.
  4. Click **User Activity** to show the live Server-Sent Events (SSE) feed.
  5. Click **Suspicious Activity Alerts** (`/admin/alerts`).
  6. Point out the pre-triggered alert: `repeated_failed_logins` on `intruder.target@example.com`.
  7. Click **Activity around this time** to inspect the ±30 minute forensic audit window.
  8. Click **Resolve Alert**, enter a note (`"Simulated penetration test confirmed"`), and mark as resolved.
- **What to Say:**
  > *"Notice the immediate visual shift: the Admin Console operates in a specialized dark operations console so administrators never confuse administrative actions with their personal workspace.*
  >
  > *Admins can never read, download, or decrypt user files—file names are anonymized in logs and alerts to maintain strict privacy boundaries.*
  >
  > *Our automated threat detection engine monitors platform actions in sliding time windows. Here you can see an open alert triggered by repeated brute-force login failures. Clicking 'Activity around this time' pivots directly into the audit log filtered from 30 minutes before to 30 minutes after the attack. When we resolve it with notes, the entire resolution workflow is audited."*

---

### Step 7: Tamper-Evident Audit Trail, Analytics & Cloud Deploy (5:45 – 7:00)
- **Action:**
  1. Click **Audit Logs** (`/admin/audit-logs`).
  2. Click the **Verify Chain Integrity** button. Show the green confirmation:
     `{"valid": true, "checked": 314, "broken_at_seq": null}`.
  3. Click **Storage Analytics** (`/admin/analytics`) to display the storage breakdown charts and user quota utilization.
  4. Briefly switch to VS Code or GitHub to highlight:
     - `docs/SECURITY_TEST_REPORT.md` (318 pytest, 77 Newman assertions, 0 vulnerabilities in pip/npm audit, 14 defensive security verifications).
     - `docker-compose.prod.yml`, `caddy/Caddyfile.prod`, and `deploy/setup-ec2.sh`.
- **What to Say:**
  > *"Every operational action is committed to an append-only audit collection linked through a cryptographic SHA-256 hash chain. When I click 'Verify Chain Integrity', the server traverses all entries; any modified or deleted record breaks the sequence immediately.*
  >
  > *Finally, our test report confirms 315 passing unit tests, 77 automated Newman checks, zero vulnerabilities in pip-audit and npm-audit, and 14 manual defensive penetration checks covering SQLi, XSS, and IDOR.*
  >
  > *The system is fully containerized and production-ready for deployment on AWS EC2 Ubuntu 22.04 with AWS S3 storage, automated Let's Encrypt certificates, daily backup scripts, and automated GitHub Actions CI/CD.*
  >
  > *Thank you. I am ready for any questions or deep dives into the codebase."*

---

## Troubleshooting & Demo Tips

1. **If a rate limit error (HTTP 429) appears during live clicking:**
   - Wait 60 seconds (rate limit windows are 1 minute) or flush Redis keys via terminal:
     ```bash
     docker compose exec redis redis-cli -a <REDIS_PASSWORD> KEYS "rl:*" | xargs -r docker compose exec redis redis-cli -a <REDIS_PASSWORD> DEL
     ```
2. **If Caddy SSL warning appears in browser:**
   - Click **Advanced → Proceed to localhost (unsafe)** or import `caddy/root.crt` into the Windows certificate store.
3. **Re-seeding Demo Data:**
   - Run `python scripts/seed_demo.py` at any time to re-populate files, active links, and alerts.
