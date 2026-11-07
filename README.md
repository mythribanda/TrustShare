# TrustShare

**Secure file storage, controlled sharing, and security monitoring.**

TrustShare is a full-stack file-management platform focused on protecting files throughout upload, storage, sharing, and access. It combines encrypted file storage with user access controls, secure share links, a private vault, activity history, and administrative security insights.

This repository is maintained and customised by **Mythri Raj Banda**. The implementation brings together the platform's application features, integration work, configuration, documentation, and ongoing improvements.

[![CI](https://github.com/mythribanda/TrustShare/actions/workflows/ci.yml/badge.svg?branch=trustshare-complete)](https://github.com/mythribanda/TrustShare/actions/workflows/ci.yml?query=branch%3Atrustshare-complete)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)
![Frontend: React](https://img.shields.io/badge/Frontend-React-61DAFB)
![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB)

## Project overview

TrustShare provides a central workspace for users to upload, organise, protect, and share files. The application also includes administrative tools for reviewing platform activity, security events, and storage usage.

### Main capabilities

- **Account security:** registration, login, JWT-based sessions, password reset, email verification, Google sign-in configuration, and multi-factor authentication.
- **File workspace:** upload, preview, download, search, organise, rename, move, favourite, and restore files.
- **Secure storage:** per-file AES-256-GCM encryption, wrapped file keys, key versioning, and configurable object storage.
- **Sharing controls:** expiring and revocable links, optional link passwords, download limits, direct user sharing, QR codes, and access history.
- **Private vault:** a separate password-protected area with additional key protection for sensitive files.
- **Activity and audit:** activity history, append-only hash-chained audit records, and CSV export.
- **Security monitoring:** suspicious-activity rules, security events, alert review, and administrative monitoring.
- **Notifications and reports:** in-app notifications, email preferences, usage reports, file analytics, and storage analytics.
- **Administration:** user management, system overview, audit review, security dashboards, and storage reporting.

## Technology stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript, React Router, Recharts |
| Backend | Python, FastAPI, Pydantic |
| Databases | PostgreSQL, MongoDB, Redis |
| File protection | AES-256-GCM, envelope encryption, SHA-256 |
| Object storage | RustFS / S3-compatible storage, with Azure Blob support |
| Infrastructure | Docker Compose, Caddy |
| Quality checks | GitHub Actions, Ruff, Pytest, ESLint, Prettier |

## Architecture

The React application communicates with the FastAPI service through the API layer. PostgreSQL stores relational security and key-management data, MongoDB stores application metadata, and Redis supports sessions, rate limiting, notifications, and detection windows. Encrypted file objects are stored separately through the configured object-storage provider.

```text
Browser
  |
  v
React + Vite frontend
  |
  v
FastAPI backend
  |          |           |
  v          v           v
PostgreSQL  MongoDB     Redis
  |
  v
Encrypted object storage
(RustFS / S3 / Azure Blob)
```

## Run locally

### Requirements

- Git
- Docker Desktop with Docker Compose
- A modern browser

### 1. Get the project

```bash
git clone https://github.com/mythribanda/TrustShare.git
cd TrustShare
git switch trustshare-complete
```

### 2. Configure environment variables

Create your local environment file from the example:

**Windows PowerShell**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux**
```bash
cp .env.example .env
```

Open `.env` and replace the development placeholders with strong local values. In particular, configure database passwords, `JWT_SECRET`, `MFA_ENCRYPTION_KEY`, `MASTER_KEYS`, and the RustFS credentials consistently with the values used by the application. Keep this file private and never commit it.

### 3. Start the services

```bash
docker compose up --build -d
```

Check the service status:

```bash
docker compose ps
```

View logs if a service does not start:

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

### 4. Open the application

| Service | Local address |
|---|---|
| Web application | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API documentation | http://localhost:8000/docs |
| RustFS console | http://localhost:9001/rustfs/console/ |

To stop the services:

```bash
docker compose down
```

To stop services and remove the local database/storage volumes, use `docker compose down -v` only if you intentionally want to delete that local data.

## Development checks

### Backend

Run from the `backend` directory after installing `requirements-dev.txt`:

```bash
ruff check .
ruff format --check .
pytest -v
```

### Frontend

Run from the `frontend` directory:

```bash
npm ci
npm run lint
npm run format:check
npm run build
```

## Continuous integration

GitHub Actions runs backend linting, formatting, database migrations, and tests, together with frontend linting, formatting, and production build checks.

The workflow is configured to run for pull requests and pushes to `main` and `trustshare-complete`. The status badge above tracks the `trustshare-complete` branch in this repository.

## Repository layout

```text
TrustShare/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── audit/
│   │   ├── analytics/
│   │   ├── notifications/
│   │   ├── security_monitoring/
│   │   ├── services/
│   │   └── storage/
│   ├── alembic/
│   └── tests/
├── frontend/
│   └── src/
│       ├── api/
│       ├── components/
│       ├── pages/
│       └── theme/
├── caddy/
├── docs/
├── scripts/
├── docker-compose.yml
└── .github/workflows/
```

## Security notes

- Do not commit `.env`, credentials, private keys, access tokens, or real user uploads.
- Use unique, strong secrets outside local development.
- Keep object-storage buckets private.
- Back up master keys securely; encrypted files cannot be recovered if the required keys are lost.
- Review the deployment and key-management documentation before exposing the service to the internet.

## Project status

The repository includes the core file-management, authentication, encryption, sharing, vault, analytics, monitoring, audit, notification, and administration modules. Deployment hardening, end-to-end validation, and continued UI refinement remain part of the ongoing development work.

## Credits and licence

This repository contains adaptations of an MIT-licensed upstream TrustShare implementation. The original licence and copyright notice are retained in [LICENSE](LICENSE), and upstream attribution is preserved as required by that licence.

The project-specific integration, configuration, documentation, and subsequent modifications in this repository are maintained here. See [LICENSE](LICENSE) for the applicable terms.
