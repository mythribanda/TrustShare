# TrustShare — Milestone 1

A local development foundation for secure file management, built to match the two supplied Milestone 1 PDFs: React + Tailwind frontend, FastAPI API, PostgreSQL user/folder/file records, MongoDB file metadata/activity logs, Redis support, JWT auth, bcrypt password hashing, role checks, local uploads, search/filtering, and folders.

## Requirements
- Docker Desktop with Compose
- Node.js 20+ and npm (only if running frontend outside Docker)
- Or Python 3.11+ (only if running backend outside Docker)

## Run
1. Copy `.env.example` to `.env` and replace `JWT_SECRET` with a long random secret.
2. From this folder run: `docker compose up --build`
3. Open the frontend at http://localhost:5173 and API docs at http://localhost:8000/docs.
4. Register an account. The first account is a regular `user`; create an admin via the protected admin-only route after promoting a user directly in PostgreSQL for local demos.

Docker Compose starts PostgreSQL, MongoDB, Redis, FastAPI, and the Vite frontend. Uploaded file bytes are stored in `./storage`; metadata is written to PostgreSQL and MongoDB. This is a local milestone build, not production-hardened.

## API highlights
- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `GET/POST /api/files`, `POST /api/files/upload`, `GET /api/files/{id}/download`, `DELETE /api/files/{id}`
- `GET/POST /api/folders`
- `GET /api/admin/users` (admin only)
- `GET /health`

## Milestone 1 scope
Included: registration/login, bcrypt, JWT bearer tokens, Admin/User/Guest role model and protected admin endpoint, PostgreSQL + MongoDB + Redis connectivity, file type/size validation, local file storage, metadata/activity records, dashboard search/filter, folders, architecture and test notes.

Not included (Milestone 2 per PDFs): AES-256 encryption/key management, S3/cloud storage, secure share links, full MFA implementation, OAuth provider integration. Password-reset screen is present as a UI foundation; a real email reset flow requires an email provider and token workflow.

## Notes
- The default allowed file types are PDF, DOCX, XLSX, CSV, TXT, PNG, JPG/JPEG, and WEBP. Maximum size defaults to 10 MiB.
- For a demo admin, register a user and run `docker compose exec postgres psql -U trustshare -d trustshare -c "UPDATE users SET role='admin' WHERE email='your-email@example.com';"` then log out/in to obtain a fresh token.
- Never commit `.env` or use the default secrets in a public deployment.


## Milestone 2 security branch

This branch adds AES-256-GCM chunked file encryption with per-file data keys, master-key versioning and re-wrapping, private local/S3-compatible object storage, expiring and revocable share links, recipient-based sharing, TOTP MFA with one-time backup codes, active-session revocation, a password-derived Secure Vault, user/admin dashboards, audit CSV export, and file analytics. Existing plaintext files are not automatically migrated.

Before uploading files, set `ENCRYPTION_MASTER_KEY` in your local `.env` to a base64-encoded random 32-byte key. Generate one in PowerShell with:

```powershell
[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

Never commit the actual `.env` or lose this key: encrypted files cannot be decrypted without it. Install updated dependencies with `pip install -r backend/requirements.txt`. This branch has not yet been validated with a full Docker build or end-to-end browser test.

### Milestone 2: configure and migrate safely

**1. Configure secrets before starting the backend.** Set a unique `JWT_SECRET` and a base64-encoded random 32-byte `ENCRYPTION_MASTER_KEY` in your ignored local `.env`. Never paste these values into chat or commit them. Install the new dependencies with `pip install -r backend/requirements.txt`.

**2. Choose object storage.** Local encrypted files remain in the configured storage directory by default. For private S3 or an S3-compatible service, set `STORAGE_PROVIDER=s3`, `S3_BUCKET`, `S3_REGION`, and AWS credentials (or `S3_ENDPOINT_URL` for compatible services). Use a private bucket, least-privilege IAM, TLS, and bucket-side access controls; do not enable public object access. File contents are encrypted before upload.

**3. Back up before migrating legacy files.** Stop writes during migration and back up the database, storage volume, and master key. From the `backend` directory, first run a dry run:

```bash
python -m app.migrate_encryption
```

If the list is correct and backups are verified, run:

```bash
python -m app.migrate_encryption --apply
```

The migration asks for the exact confirmation word `ENCRYPT`. It skips files with existing key records and fails closed when an object looks encrypted but its key record is missing. Test restore and decryption before resuming normal writes.

**4. Master-key rotation.** Keep the old key available while adding a new key to `MASTER_KEYS` using `version:base64-key` entries. Set `ACTIVE_MASTER_KEY_VERSION` to the new version. Run `python -m app.rotate_keys` for a dry run, verify the result, then `python -m app.rotate_keys --apply` and enter `ROTATE`. This re-wraps per-file data keys without re-encrypting file content. Do not remove the old key until all records have been rotated and backups verified.

**5. Run checks.** From `backend/`, run `PYTHONPATH=. pytest -q` (PowerShell: `$env:PYTHONPATH='.'; pytest -q`). GitHub Actions compiles the backend, runs security unit tests, and builds the frontend.

### Milestone 2 API highlights

- `POST /api/files/{id}/shares`, `GET /api/shares/links`, `POST /api/shares/{id}/revoke`, `GET /share/{token}`
- `POST /api/files/{id}/direct-shares`, `GET /api/shares/direct`, `DELETE /api/shares/direct/{grant_id}`
- `GET /api/dashboard/user`, `GET /api/dashboard/admin`, `GET /api/dashboard/security`, `GET /api/analytics/files`
- `GET /api/auth/mfa/status`, `POST /api/auth/mfa/setup`, `POST /api/auth/mfa/confirm`, `POST /api/auth/mfa/disable`
- `GET /api/auth/sessions`, `POST /api/auth/sessions/{id}/revoke`, `POST /api/auth/sessions/revoke-all`
- `POST /api/vault/setup`, `GET /api/vault/status`, `GET /api/vault/files`, `POST /api/vault/files/upload`, `GET /api/vault/files/{id}/download`, `DELETE /api/vault/files/{id}`, `POST /api/vault/change-password`, `POST /api/vault/reset`
- `GET /api/admin/reports/sharing`, `GET /api/admin/audit.csv`

The Vault has its own password-derived key. Forgetting that password means its encrypted files cannot be recovered; reset explicitly deletes them. Public share links can now optionally require a separate password (minimum 8 characters), stored as a bcrypt hash. Password-protected links show an unlock form before the file is returned. Links still expire, can be revoked, and can have download limits. Share only the link and password through separate channels when practical.

**Validation status:** The baseline GitHub Actions run passed backend compilation, security unit tests, and the frontend production build before the latest password-link changes. The latest commits have been pushed, but no current status checks are reported yet. Verify the newest workflow run and complete the local end-to-end checklist before presenting. S3 has not been tested against a live bucket, and a full deployed end-to-end security review is still required before production use.