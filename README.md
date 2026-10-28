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

This branch adds AES-256-GCM encryption for newly uploaded files, authenticated owner-only downloads, hashed expiring share tokens with revocation, user/admin dashboard APIs, and a Security Center UI. Existing plaintext files are not automatically migrated; back them up and migrate them before treating the deployment as fully encrypted.

Before uploading files, set `ENCRYPTION_MASTER_KEY` in your local `.env` to a base64-encoded random 32-byte key. Generate one in PowerShell with:

```powershell
[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

Never commit the actual `.env` or lose this key: encrypted files cannot be decrypted without it. Install updated dependencies with `pip install -r backend/requirements.txt`. This branch has not yet been validated with a full Docker build or end-to-end browser test.
