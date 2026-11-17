# TrustShare Administrator Guide

This guide provides operational and security instructions for system administrators managing the **TrustShare** platform.

---

## 1. Administrative Architecture & Privacy Boundary

TrustShare enforces strict role-based access control (RBAC) and privacy boundaries:

- **Role Hierarchy:**
  - **Admin:** Manages user accounts, monitors system security, inspects audit logs, handles suspicious activity alerts, and reviews compliance reports.
  - **User:** Full file storage, folder hierarchy, sharing, and personal vault capabilities.
  - **Guest:** Read-only access to files shared directly with them.
- **Strict Privacy Separation:**
  - Administrators **cannot read, open, download, or decrypt other users' files**.
  - File names are anonymized in administrative reports, alerts, and audit logs (displaying file IDs, categories, and sizes only) to prevent unauthorized surveillance.
  - Vault files are strictly sealed with user-derived keys and are inaccessible to administrators.

---

## 2. Admin Console Overview

When signed in as an administrator, click the **Admin Console** link in the navigation menu. The admin console operates in a specialized dark operations theme (violet/amber highlights) to distinguish administrative tasks from standard file management.

The console provides nine integrated modules:
1. **Security Dashboard:** High-level threat intelligence, authentication trends, and severity breakdowns.
2. **User Activity Monitoring:** Real-time stream of platform events.
3. **Audit Logs:** Tamper-evident, hash-chained records of all operations.
4. **Suspicious Activity Alerts:** Automated detection and incident triage.
5. **File Activity Reports:** Usage summaries and CSV exports.
6. **Storage Analytics:** Storage consumption, growth trends, and quotas.
7. **Notification Management:** Broadcasts and system notification delivery stats.
8. **Users:** Account provisioning, role modification, unlocking, and status management.
9. **System Health:** Status of PostgreSQL, MongoDB, Redis, and object storage.

---

## 3. Account Provisioning & User Management

### 3.1 Creating the First Administrator
The initial administrator account cannot be registered through the public web interface. It must be provisioned via the command line:

```bash
docker compose exec backend python -m app.scripts.create_admin --email admin@example.com --name "System Administrator"
```
You will be prompted to enter a secure password interactively.

### 3.2 Managing User Accounts
From the **Users** tab (`/admin/users`):
- **Role Assignment:** Change a user's role between `Admin`, `User`, and `Guest`.
- **Disable / Enable Account:** Disabling an account immediately invalidates all active JWT tokens, revokes current Redis refresh sessions, and temporarily deactivates all active share links created by that user.
- **Unlock Account:** If a user is locked out after 5 consecutive incorrect password attempts, click **Unlock Account** to immediately clear the Redis lockout key and reset their failure counter.
- **Delete Inactive Accounts:** Users who have not signed in for over 30 days can be deleted. This permanently deletes their files, object storage data, wrapped encryption keys, and sessions while preserving audit log integrity.

---

## 4. Security Monitoring & Alert Management

TrustShare features an automated rule engine that monitors platform activity in sliding time windows (backed by Redis) and raises high-priority alerts.

### 4.1 Detection Rules & Thresholds

| Alert Rule | Default Trigger Condition | Default Threshold |
|---|---|---|
| **Brute-Force Login** | Repeated failed login attempts on an account | > 5 failures in 10 minutes |
| **Excessive Downloads** | Rapid downloads from a single IP or user account | > 20 downloads in 5 minutes |
| **Unauthorized Access** | Multiple HTTP 403 Forbidden responses | > 4 attempts in 10 minutes |
| **Expired Link Probing** | Repeated requests targeting expired share tokens | > 2 attempts in 10 minutes |
| **Revoked Link Probing** | Repeated requests targeting revoked share tokens | > 2 attempts in 10 minutes |

Thresholds can be customized in `.env` using variables such as `DETECT_FAILED_LOGINS_LIMIT` and `DETECT_FAILED_LOGINS_MINUTES`.

### 4.2 Incident Triage Workflow
1. Navigate to **Suspicious Activity Alerts** (`/admin/alerts`).
2. Each alert card displays the rule triggered, timestamp, target user or IP address, severity level (`medium`, `high`, `critical`), and event details.
3. Click **Activity around this time** to jump directly to the audit log filtered from **30 minutes before** to **30 minutes after** the incident for forensic analysis.
4. **Update Status:**
   - **Acknowledge:** Assign the incident to yourself while investigating.
   - **Resolve:** Add mandatory resolution notes (e.g., "Legitimate user forgot password; confirmed via phone") and mark as resolved.
   - **Reopen:** Reopen the incident if new suspicious activity is observed.
5. All alert state transitions and notes are logged to the tamper-evident audit trail.

---

## 5. Audit Logging & Verification

Every critical event (authentication, uploads, downloads, link creation, revocations, permission changes, administrative actions) is logged to the `audit_logs` collection.

### 5.1 Tamper-Evident Hash Chain
Audit entries are linked using a cryptographic SHA-256 hash chain:
$$\text{Entry Hash} = \text{SHA256}(\text{Previous Hash} \parallel \text{Timestamp} \parallel \text{Actor ID} \parallel \text{Action} \parallel \text{Details})$$
If any row in the database is modified or deleted, the subsequent hashes will fail verification.

### 5.2 Verifying Audit Log Integrity
To verify the complete audit log chain:
1. In the Admin Console, navigate to **Audit Logs**.
2. Click **Verify Chain Integrity**.
3. The server computes the chain across all records and returns either:
   - `{"status": "valid", "total_records": <count>}`: The audit trail has not been tampered with.
   - `{"status": "broken", "broken_at_id": "<id>"}`: Indicates the exact record where tampering occurred.

### 5.3 Exporting Audit Logs
Click **Export CSV** to download audit log records for external compliance reporting. The exporter automatically sanitizes spreadsheet values by escaping leading `=`, `+`, `-`, or `@` characters to prevent formula injection attacks.

---

## 6. Reports & Storage Analytics

### 6.1 Compliance & Activity Reports
Navigate to **File Activity Reports** (`/admin/reports`) to generate filtered reports for:
- **Upload Trends:** Volume and file types ingested over time.
- **Download Statistics:** Internal user vs. external share link downloads.
- **Sharing Reports:** Active links, direct shares, and expired/revoked links.
- **Security Events Summary:** Breakdown of lockouts, rate-limiting triggers, and token errors.

### 6.2 Storage Analytics
Navigate to **Storage Analytics** (`/admin/analytics`):
- Monitor total capacity consumed vs. remaining storage.
- Identify users nearing their allocated quota (default 1,024 MB).
- Review breakdown by MIME category (Documents, Spreadsheets, Presentations, Images).

---

## 7. Maintenance & CLI Operations

### 7.1 Master Key Rotation
TrustShare supports envelope encryption key rotation without re-encrypting underlying files.
1. Generate a new 32-byte base64 master key:
   ```bash
   python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
   ```
2. Update `.env`:
   ```ini
   MASTER_KEYS=1:<existing_key>,2:<new_key>
   ACTIVE_MASTER_KEY_VERSION=2
   ```
3. Run the rotation script inside the backend container:
   ```bash
   docker compose exec backend python -m app.scripts.rotate_keys
   ```
   This unwraps all file keys in PostgreSQL with key v1 and re-wraps them with key v2.
4. Once rotation completes, remove version 1 from `MASTER_KEYS`.

### 7.2 Database Backups & Restoration
To perform manual backups:
```bash
bash deploy/backup.sh
```
This script generates timestamped `.sql.gz` and `.gz` dumps of PostgreSQL and MongoDB in `~/backups/trustshare` and prunes backups older than 14 days.

To restore a backup:
```bash
# Restore PostgreSQL
gunzip < ~/backups/trustshare/postgres_YYYYMMDD_HHMMSS.sql.gz | docker compose exec -T postgres psql -U trustshare trustshare

# Restore MongoDB
docker compose exec -T mongo mongorestore --username trustshare --password <password> --authenticationDatabase admin --archive --gzip < ~/backups/trustshare/mongo_YYYYMMDD_HHMMSS.gz
```

### 7.3 Purging Test Accounts
To remove throwaway accounts created during testing or Newman runs:
```bash
docker compose exec backend python -m app.scripts.remove_test_accounts postman.example.com
```
Only domains ending with `.example.com` (RFC 2606) can be purged with this script, ensuring real accounts cannot be deleted accidentally.
