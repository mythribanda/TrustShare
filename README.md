# TrustShare Plus

**Built and maintained by [Mythri Raj Banda](https://github.com/mythribanda).**

TrustShare Plus is a privacy-first file workspace for securely storing, organizing, and sharing files. This repository builds on the existing TrustShare milestone implementation and adds a distinct security-transparency layer.

## What is included

- User registration and authentication with role checks
- File and folder management
- AES-256-GCM file encryption with per-file data keys and versioned master-key wrapping
- Expiring, revocable share links and direct file sharing
- Optional authenticator-based MFA and one-time backup codes
- Separate password-protected Secure Vault
- Active session review and revocation
- **New: Security Center overview** with account, sharing, and session posture
- **New: File integrity verification** using SHA-256 digests for stored objects
- **New: Security snapshot export** as a downloadable JSON report
- **New: Activity summary** for recent activity events when MongoDB is available

## Technology

React 18, Vite, Tailwind CSS, FastAPI, SQLAlchemy, PostgreSQL, MongoDB, Redis, Docker Compose, and Python cryptography.

## Run locally

1. Copy `.env.example` to `.env`.
2. Set a unique `JWT_SECRET` and a base64-encoded 32-byte `ENCRYPTION_MASTER_KEY`. Never commit secrets.
3. Run:

```bash
docker compose up --build
```

4. Open the frontend at http://localhost:5173 and API docs at http://localhost:8000/docs.

## New security endpoints

All endpoints below require a valid bearer token:

- `GET /api/security-center/overview`
- `GET /api/security-center/file-integrity`
- `GET /api/security-center/activity-summary`
- `GET /api/security-center/export`

File integrity checking compares the SHA-256 value stored in the application's file record with the bytes retrieved from the configured storage backend. It reports mismatches; it does not repair or overwrite files.

## Validation status

The changes in this feature branch have not been run against a live Docker stack in this editing session. Validate locally with:

```bash
docker compose up --build
```

Then open `/docs` and exercise the security-center routes using an authenticated account. Run the project's existing backend and frontend checks before merging.

## Attribution and project origin

This is an independently maintained extension of the TrustShare milestone project in this account. The original reference project that informed the feature direction is [TrustShare Encrypted File Sharing & Collaboration Platform](https://github.com/Vimaladharsan/TrustShare-Encrypted-File-Sharing-Collaboration-Platform), authored by its original maintainer. The upstream repository has not been modified.
