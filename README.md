# TrustShare — Milestone 1

A foundation for secure file management, built to match the Milestone 1 specifications: React + Tailwind frontend, FastAPI backend, PostgreSQL user/folder/file records, MongoDB file metadata/activity logs, Redis session and rate-limit support, JWT authentication, bcrypt password hashing, role-based access control (RBAC), local file uploads, search/filtering, and folders.

## Requirements
- Docker Desktop with Compose (recommended for full multi-container stack)
- Or Node.js 20+ and Python 3.11+ (if running backend and frontend locally outside Docker)

## Configuration & Environments (`APP_ENV`)

Configure environment variables in `.env` (copy from `.env.example`).

The system supports two operating modes via the `APP_ENV` variable:

### 1. Development Mode (`APP_ENV=development`, default)
- Designed for local development and live demonstrations.
- **Database Fallback:** If PostgreSQL is unreachable, the system automatically falls back to local SQLite storage at `storage/trustshare.db`.
- **Fault-Tolerant Redis:** If Redis is down, rate limiting and session lookups fail open with logged warnings so developer flows are not blocked.
- **JWT Secret:** Insecure or default secrets log a warning at startup without aborting.

### 2. Production Mode (`APP_ENV=production`)
- Designed for production deployments requiring strict security guarantees.
- **Fail-Closed Database:** Refuses to start if PostgreSQL is unreachable; SQLite fallback is strictly prohibited.
- **Fail-Closed Sessions:** All JWT authentications require an active session key in Redis (`session:{user_id}:{token_hash}`). If Redis is unreachable or the session is absent, requests return `HTTP 503` or `HTTP 401`. Registration and login will fail with `HTTP 503` if the session cannot be saved to Redis.
- **Fail-Closed Rate Limiting:** Returns `HTTP 503` if Redis is unavailable rather than bypassing limits (5 logins/min per IP, 20 uploads/min per user).
- **JWT Secret Enforcement:** Refuses to start if `JWT_SECRET` is unset, matches placeholder values, or is shorter than 32 characters. Generate one using:
  ```bash
  openssl rand -hex 32
  ```

---

## Health & Readiness Endpoints

- **`GET /health` (Liveness):**
  Simple liveness check returning HTTP 200 with `{"status": "ok"}` when the FastAPI process is running.
- **`GET /health/ready` (Readiness):**
  Comprehensive readiness check verifying database connectivity, MongoDB ping, and Redis ping.
  - Returns `HTTP 200` with `status: "ok"` only when all required services are reachable and PostgreSQL is in use (or SQLite in development).
  - Returns `HTTP 503` with `status: "degraded"` and per-service statuses (`database`, `postgres`, `mongodb`, `redis`) if any required dependency is failing or if SQLite fallback is detected in production.
  - Used by Docker Compose to ensure the backend is fully healthy before traffic is routed.

---

## Access Control & Admin Policy

TrustShare implements consistent Role-Based Access Control (RBAC):
- **File Owners:** Full access to their own files (view metadata, download, and delete).
- **Admins:** Can inspect users (`GET /api/admin/users`), view metadata for any file (`GET /api/files/{id}/metadata`), and download any file (`GET /api/files/{id}/download`).
- **Owner-Only Deletion:** Only the file owner can delete their file (`DELETE /api/files/{id}`). Cross-user file deletion is prohibited for admins unless using an explicit administrative audit workflow.
- **Admin Audit Trail:** Whenever an admin views metadata or downloads a file belonging to another user, an `admin_file_access` audit event is logged in MongoDB's `activity` collection (`event: "admin_file_access"`, `action: "download" | "metadata"`, `file_id`, `file_owner_id`).
- **Metadata Reconciliation:** Admins can trigger `POST /api/admin/reconcile-metadata` to reconcile any SQL files missing from MongoDB or flagged with `meta_synced=false`.

---

## Data Integrity & Storage Scope

- **Milestone 1 Scope:** Files are uploaded and stored directly on disk in `./storage` using unique identifiers. A SHA-256 digest (`SHA-256 Digest (content integrity hash)`) is computed on stream to verify file integrity. Raw files are stored unencrypted in Milestone 1.
- **Milestone 2 Scope (Planned):** AES-256 at-rest encryption, envelope key management, cloud object storage (S3/GCS), expiring secure share links, full OAuth2/OIDC providers, and hardware MFA.

---

## Running the Application

### Option A: Docker Compose (Full Stack)
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Start the services:
   ```bash
   docker compose up --build
   ```
3. Open:
   - Frontend: http://localhost:5173
   - Backend API Docs: http://localhost:8000/docs
   - Readiness Check: http://localhost:8000/health/ready

### Option B: Local Standalone Development (FastAPI + Vite)
1. Ensure Python 3.11+ and Node.js 20+ are installed.
2. In `.env`, ensure `APP_ENV=development`.
3. Start the backend:
   ```powershell
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
4. Start the frontend:
   ```powershell
   cd frontend
   npm run dev
   ```

### Promoting a User to Admin
1. Register a regular user through the UI at http://localhost:5173.
2. If using Docker PostgreSQL:
   ```bash
   docker compose exec postgres psql -U trustshare -d trustshare -c "UPDATE users SET role='admin' WHERE email='your-email@example.com';"
   ```
   Or if using local SQLite development mode:
   ```powershell
   python -c "import sqlite3; con = sqlite3.connect('storage/trustshare.db'); con.execute(\"UPDATE users SET role='admin' WHERE email='your-email@example.com'\"); con.commit(); con.close()"
   ```
3. Log out and log back in to refresh the JWT claims and Redis session.
