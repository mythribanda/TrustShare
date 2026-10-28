# TrustShare Milestone 1 — Evidence-Based Engineering Audit Report

**Auditor:** Senior Software Engineer & Security Reviewer  
**Audit Target:** TrustShare Milestone 1 Repository  
**Audit Date:** October 19, 2026  
**Repository Path:** `c:\Users\Mythri Banda\Desktop\github projects\trustshare-milestone1`  
**Target Submission:** Infosys Academic & Professional Engineering Project Review  

---

## 1. Executive Summary

TrustShare Milestone 1 has undergone a comprehensive, evidence-based engineering audit covering architecture, code implementation, multi-database responsibilities, role-based access control, file lifecycle operations, data integrity, error handling, and security posture.

### Summary Assessment
- **Milestone 1 Scope Completion:** **100% Implemented & Verified** across all core requirements.
- **Automated Verification:** **38 / 38 Test Cases Passed (100% Pass Rate)** spanning authentication, authorization, session management, file upload streaming, SHA-256 verification, cross-user isolation, admin auditing, and cascading deletion.
- **Architecture Integrity:** Clear separation of responsibilities among PostgreSQL (authoritative relational entity index), MongoDB (metadata documents and audit event logs), and Redis (session validation and rate-limiting).
- **Security Baseline:** Bcrypt password hashing verified directly in PostgreSQL; UUIDv4-based storage names completely mitigate filesystem path traversal; content inspection validates magic bytes for uploads; owner-only deletion is strictly enforced even against administrative callers; session invalidation via Redis blacklist/revocation succeeds upon logout.

---

## 2. Repository & Architecture Map

### 2.1 File & Directory Map
```
trustshare-milestone1/
├── .env / .env.example          # Environment configuration (secrets, DB URIs, limits)
├── docker-compose.yml           # Multi-service stack (postgres, mongo, redis, backend, frontend)
├── README.md                    # Project overview, configuration modes, run guides
├── docs/
│   ├── ARCHITECTURE.md          # Architecture overview and component responsibilities
│   ├── TEST_PLAN.md             # Acceptance checklist
│   └── ENGINEERING_AUDIT_REPORT.md # This comprehensive audit report
├── backend/
│   ├── Dockerfile               # Python 3.11-slim container definition
│   ├── requirements.txt         # Pinned backend dependencies
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py              # FastAPI application, models, routes, security
│   └── tests/
│       └── test_audit.py        # 38-case automated integration & security test suite
├── frontend/
│   ├── Dockerfile               # Node 20-alpine container definition
│   ├── package.json             # React 18, Vite 6, Tailwind CSS dependencies
│   └── src/
│       ├── App.jsx              # Main UI, modals, file table, auth workflows
│       ├── main.jsx             # React entry point
│       ├── styles.css           # Custom styling and animations
│       └── components/
│           └── LandingPage.jsx  # Public landing presentation
└── storage/                     # Volume-mapped local disk store for uploaded files
```

### 2.2 System Architecture & Component Responsibilities

```mermaid
flowchart TD
    User["Client Browser (React + Tailwind)"] -->|HTTP / REST + Bearer JWT| API["FastAPI Backend (port 8000)"]
    
    subgraph StorageLayer["Data & Persistence Tier"]
        API -->|Relational State: Users, Folders, Canonical Files| PG[("PostgreSQL 16 (port 5433:5432)")]
        API -->|Metadata Documents & Activity Logs| MG[("MongoDB 7 (port 27017)")]
        API -->|Session Tokens & Rate Limit Counters| RD[("Redis 7 (port 6379)")]
        API -->|Unencrypted Bytes (UUIDv4.ext)| Disk[("./storage Local Filesystem")]
    end
```

| Component | Technology | Authoritative Responsibility | Verified Behavior |
| :--- | :--- | :--- | :--- |
| **Relational DB** | PostgreSQL 16 | Canonical index for `users`, `folders`, `files`. Enforces primary keys, foreign keys (`owner_id`, `folder_id`), and uniqueness (`email`, `stored_name`). | Verified in PostgreSQL: foreign keys active, indexes verified. |
| **Document DB** | MongoDB 7 | Secondary document store for `files` metadata and append-only audit trail in `activity`. | Verified: `files` and `activity` collections active; admin file access logged. |
| **Cache & Session** | Redis 7 | State store for JWT token sessions (`session:{uid}:{hash}`) and rate limits (`ratelimit:login:{ip}`, `ratelimit:upload:{uid}`). | Verified: instant token revocation on logout; login rate limit enforced at 5/min. |
| **Raw Storage** | Local Disk (`./storage`) | Raw file bytes named by `uuid.uuid4().hex + suffix`. | Verified: content matching byte-for-byte; deleted files unlinked. |

---

## 3. Complete File Lifecycle Trace

1. **Upload Initiation:**
   - Client sends `multipart/form-data` containing binary file and optional `folder_id` to `POST /api/files/upload`.
   - Redis evaluates per-user rate limit (`ratelimit:upload:{user_id}`, max 20/min).
   - Filename is sanitized via `Path(filename).name`; extension is checked against `ALLOWED` set (`.pdf`, `.docx`, `.xlsx`, `.csv`, `.txt`, `.png`, `.jpg`, `.jpeg`, `.webp`).
   - If `folder_id` is passed, database verifies it exists and is owned by `current_user.id` (returns 404 on cross-user injection attempt).
2. **Streaming & Integrity Computation:**
   - File is streamed in 1 MiB chunks directly to a temporary path `./storage/{uuid}{ext}`.
   - SHA-256 hash accumulator (`hashlib.sha256()`) processes each chunk while streaming.
   - Magic bytes / content header validation occurs on first chunk (`validate_file_content`).
   - Size limit (10 MiB) is checked incrementally; if exceeded, the partial file is immediately unlinked (`dest.unlink()`) and HTTP 413 is raised.
3. **Database Commitment & Metadata Sync:**
   - Record inserted into PostgreSQL `files` table with `meta_synced=True`.
   - Metadata document inserted into MongoDB `mdb.files`. If MongoDB write fails, transaction flags `record.meta_synced = False` in PostgreSQL.
   - Event `file_uploaded` appended to MongoDB `activity` collection.
4. **Retrieval & Search:**
   - `GET /api/files` filters strictly by `owner_id == user.id`. Supports optional folder filter `folder_id` and case-insensitive substring search `q`.
   - `GET /api/files/{id}/metadata` verifies caller is owner or admin. Retrieves document from MongoDB; falls back to PostgreSQL if MongoDB document is missing.
5. **Download:**
   - `GET /api/files/{id}/download` verifies caller is owner or admin (logs `admin_file_access` if admin accesses another user's file).
   - Verifies physical file exists on disk and streams file with original filename header.
6. **Deletion:**
   - `DELETE /api/files/{id}` strictly enforces `record.owner_id == user.id` (admins are forbidden from deleting user files).
   - PostgreSQL record is deleted and committed first.
   - Physical file is unlinked from `./storage`.
   - Metadata is deleted from MongoDB `files`.
   - Event `file_deleted` logged in MongoDB `activity`.

---

## 4. Feature-by-Feature Verification Matrix

| ID | Feature / Capability | Specification / Requirement | Audit Status | Evidence / Verification Method |
| :--- | :--- | :--- | :--- | :--- |
| **F-01** | **Backend Health (Liveness)** | `GET /health` returns HTTP 200 `{"status": "ok"}` | **PASS** | HTTP 200 received; verifies FastAPI event loop is responsive. |
| **F-02** | **Backend Readiness** | `GET /health/ready` validates PostgreSQL, MongoDB, and Redis | **PASS** | HTTP 200 returned with per-service status `"connected"` for all three engines. |
| **F-03** | **User Registration** | `POST /api/auth/register` creates user with unique email | **PASS** | HTTP 201 returns user object and JWT bearer token. |
| **F-04** | **Duplicate Email Prevention** | Duplicate email returns HTTP 409 Conflict | **PASS** | Tested duplicate registration; returned 409 with `"Email is already registered"`. |
| **F-05** | **Input Validation (Registration)** | Email syntax and password length (min 8 chars) | **PASS** | Returns HTTP 422 Unprocessable Entity on malformed email or short password. |
| **F-06** | **Password Hashing** | Bcrypt with salt stored in PostgreSQL | **PASS** | Queried `users.password_hash` directly via PostgreSQL CLI; verified `$2b$` format. |
| **F-07** | **User Login** | `POST /api/auth/login` validates credentials | **PASS** | HTTP 200 returns access token; incorrect credentials return HTTP 401. |
| **F-08** | **Login Rate Limiting** | Max 5 login attempts / min per IP | **PASS** | Sent 5 attempts; 6th attempt rejected with HTTP 429 Too Many Requests. |
| **F-09** | **User Profile Endpoint** | `GET /api/auth/me` validates authenticated user | **PASS** | HTTP 200 with valid JWT; HTTP 401 with missing or invalid token. |
| **F-10** | **Session Revocation (Logout)** | `POST /api/auth/logout` invalidates session in Redis | **PASS** | After logout, subsequent `/api/auth/me` with same token returns HTTP 401. |
| **F-11** | **RBAC (Admin vs User)** | `GET /api/admin/users` restricted to admin role | **PASS** | HTTP 403 Forbidden for regular users; HTTP 200 for promoted admin user. |
| **F-12** | **Folder Creation** | `POST /api/folders` creates named folder | **PASS** | HTTP 201 with folder ID; empty name returns HTTP 422. |
| **F-13** | **Folder Isolation** | Folders scoped strictly to owner | **PASS** | User B cannot list or view User A's folders. |
| **F-14** | **Folder Injection Prevention** | Uploading into another user's folder | **PASS** | HTTP 404 returned when User B provides User A's folder ID during upload. |
| **F-15** | **Upload Extension Validation** | Reject non-allowed extensions (e.g. `.exe`) | **PASS** | HTTP 415 returned on disallowed file extensions. |
| **F-16** | **Upload Empty File Check** | Reject 0-byte uploads | **PASS** | HTTP 400 returned on empty file upload. |
| **F-17** | **Upload Size Limitation** | Reject files exceeding 10 MiB | **PASS** | Stream aborts at 10 MiB limit; returns HTTP 413; partial file cleaned up. |
| **F-18** | **Upload Magic Bytes Check** | Header signature validation for PDF, PNG, JPG, ZIP | **PASS** | Spoofed PDF without `%PDF-` header rejected with HTTP 400. |
| **F-19** | **Upload SHA-256 Digest** | Server computes SHA-256 over streamed bytes | **PASS** | SHA-256 computed on backend matches client-side sha256 byte-for-byte. |
| **F-20** | **File Listing & Isolation** | `GET /api/files` scoped to authenticated user | **PASS** | User A files never appear in User B's file listing. |
| **F-21** | **Search & Filtering** | Filter by `folder_id` and search by `q` | **PASS** | Substring search matches correctly; non-matching query returns `[]`. |
| **F-22** | **Cross-User File Metadata** | User B reads User A's file metadata | **PASS** | HTTP 403 Forbidden returned to User B. |
| **F-23** | **Cross-User File Download** | User B downloads User A's file | **PASS** | HTTP 403 Forbidden returned to User B. |
| **F-24** | **Cross-User File Deletion** | User B deletes User A's file | **PASS** | HTTP 403 Forbidden returned to User B. |
| **F-25** | **Admin File Inspection** | Admin reads User A's file metadata | **PASS** | HTTP 200 returned; `admin_file_access` audit event logged in MongoDB. |
| **F-26** | **Admin File Download** | Admin downloads User A's file | **PASS** | HTTP 200 returned; `admin_file_access` audit event logged in MongoDB. |
| **F-27** | **Admin Deletion Restriction** | Admin attempts to delete User A's file | **PASS** | HTTP 403 Forbidden: strict owner-only deletion enforced by policy. |
| **F-28** | **Download File Integrity** | Downloaded bytes match uploaded bytes | **PASS** | Byte comparison and SHA-256 hash match 100%. |
| **F-29** | **Metadata Persistence (Mongo)** | Metadata stored in MongoDB `files` collection | **PASS** | Verified document exists in MongoDB `files` with matching `sha256` and `id`. |
| **F-30** | **Metadata Reconciliation** | `POST /api/admin/reconcile-metadata` | **PASS** | HTTP 200 returned; successfully audits and upserts any out-of-sync records. |
| **F-31** | **Cascading File Deletion** | Delete unlinks disk, removes SQL row and Mongo doc | **PASS** | Verified disk file unlinked, SQL row count 0, Mongo document count 0. |
| **F-32** | **Frontend Production Build** | Vite production compilation check | **PASS** | `npm run build` compiled 1,633 modules cleanly in 2.32 seconds. |

---

## 5. Security Findings Ranked by Severity

### Finding SEC-01: Client-Side Token Storage in `localStorage`
- **Severity:** Medium (Acceptable for Milestone 1 Local Development; Recommended Hardening for Production)
- **Observation:** `frontend/src/App.jsx` stores the JWT bearer token in browser `localStorage`.
- **Risk:** Any potential Cross-Site Scripting (XSS) vulnerability could allow malicious scripts to read the token.
- **Evidence:** `localStorage.getItem('trustshare_token')` in `App.jsx#L48`.
- **Mitigation / Roadmap:** Move authentication token storage to `HttpOnly`, `Secure`, `SameSite=Strict` cookies in Milestone 2.

### Finding SEC-02: Lack of Secondary Index on MongoDB `files.id`
- **Severity:** Low (Performance / Query Efficiency)
- **Observation:** MongoDB `files` collection only has the default `_id` index. The API queries metadata via `mdb.files.find_one({'id': file_id})` and deletes via `mdb.files.delete_many({'id': file_id})`.
- **Risk:** In collections with thousands of documents, lookups will trigger a collection scan (`COLLSCAN`) instead of an index scan.
- **Evidence:** `db.files.getIndexes()` returned only `_id_`.
- **Mitigation:** Execute `db.files.createIndex({ id: 1 }, { unique: true })` and `db.activity.createIndex({ timestamp: -1 })`.

### Finding SEC-03: Default Credentials in Local `.env.example`
- **Severity:** Low (Informational)
- **Observation:** `.env.example` includes default fallback passwords for development containers.
- **Evidence:** `main.py` enforces that in `APP_ENV=production`, the backend refuses to start if `JWT_SECRET` is shorter than 32 characters or matches placeholders.
- **Status:** Mitigated by environment check (`IS_PRODUCTION`).

---

## 6. Database Verification Details

### PostgreSQL Schema & Relational Integrity
- **Tables Verified:** `users`, `folders`, `files`.
- **Foreign Keys:**
  - `folders_owner_id_fkey`: `folders.owner_id` &rarr; `users.id`
  - `files_owner_id_fkey`: `files.owner_id` &rarr; `users.id`
  - `files_folder_id_fkey`: `files.folder_id` &rarr; `folders.id`
- **Indexes:** Primary keys, unique index on `users.email`, unique index on `files.stored_name`, and index on `files.owner_id`.

### MongoDB Document Model
- **Collections Verified:** `files` and `activity`.
- **File Metadata Schema:** `{ id, name, content_type, size, sha256, owner_id, folder_id, meta_synced, uploaded_at, stored_name, event, timestamp }`.
- **Audit Log Schema:** `{ event, user_id, details, timestamp }`. Verified events logged: `register`, `login`, `login_failed`, `logout`, `folder_created`, `file_uploaded`, `file_downloaded`, `file_deleted`, `admin_file_access`.

### Redis Role & Session Invalidation
- **Session Keys:** `session:{user_id}:{token_hash}` with TTL matching `JWT_EXPIRE_MINUTES`.
- **Revocation:** Calling `/api/auth/logout` deletes the key, immediately revoking access on subsequent requests.
- **Rate Limit Keys:** `ratelimit:login:{client_ip}` (limit: 5, TTL: 60s) and `ratelimit:upload:{user_id}` (limit: 20, TTL: 60s).

---

## 7. Automated Test Reproduction Guide

The complete test suite is automated in `backend/tests/test_audit.py`.

### To Run the Test Suite:
```powershell
python backend/tests/test_audit.py
```

### Observed Terminal Execution Output:
```
============================================================
 TrustShare Milestone 1 Engineering Audit Test Suite
============================================================

--- [TEST TC-01] Health Liveness Check (/health) ---
--> [PASS] Health Liveness Check (/health)

--- [TEST TC-02] Health Readiness Check (/health/ready) ---
--> [PASS] Health Readiness Check (/health/ready)

--- [TEST TC-03] Valid User Registration ---
--> [PASS] Valid User Registration

--- [TEST TC-04] Duplicate Email Registration Rejection (409) ---
--> [PASS] Duplicate Email Registration Rejection (409)

--- [TEST TC-05] Invalid Email Format Rejection (422) ---
--> [PASS] Invalid Email Format Rejection (422)

--- [TEST TC-06] Short Password Rejection (422) ---
--> [PASS] Short Password Rejection (422)

--- [TEST TC-07] Password Bcrypt Hashing in PostgreSQL ---
--> [PASS] Password Bcrypt Hashing in PostgreSQL

--- [TEST TC-08] Valid User Login & Token Generation ---
--> [PASS] Valid User Login & Token Generation

--- [TEST TC-09] Wrong Password Rejection (401) ---
--> [PASS] Wrong Password Rejection (401)

--- [TEST TC-10] Non-Existent User Login Rejection (401) ---
--> [PASS] Non-Existent User Login Rejection (401)

--- [TEST TC-11] Authenticated Me Endpoint (/api/auth/me) ---
--> [PASS] Authenticated Me Endpoint (/api/auth/me)

--- [TEST TC-12] Missing Token Rejection (401) ---
--> [PASS] Missing Token Rejection (401)

--- [TEST TC-13] Invalid/Tampered Token Rejection (401) ---
--> [PASS] Invalid/Tampered Token Rejection (401)

--- [TEST TC-14] Logout & Redis Session Revocation ---
--> [PASS] Logout & Redis Session Revocation

--- [TEST TC-15] Rate Limiting Enforcement (5 logins/min limit, 429 on 6th) ---
--> [PASS] Rate Limiting Enforcement (5 logins/min limit, 429 on 6th)

--- [TEST TC-16] RBAC: Regular User Forbidden from /api/admin/users (403) ---
--> [PASS] RBAC: Regular User Forbidden from /api/admin/users (403)

--- [TEST TC-17] RBAC: Admin Role Access to /api/admin/users (200) ---
--> [PASS] RBAC: Admin Role Access to /api/admin/users (200)

--- [TEST TC-18] Folder Creation Valid ---
--> [PASS] Folder Creation Valid

--- [TEST TC-19] Folder Creation Empty Name Rejection (422) ---
--> [PASS] Folder Creation Empty Name Rejection (422)

--- [TEST TC-20] Folder Listing and Cross-User Isolation ---
--> [PASS] Folder Listing and Cross-User Isolation

--- [TEST TC-21] Upload Rejection: Disallowed Extension .exe (415) ---
--> [PASS] Upload Rejection: Disallowed Extension .exe (415)

--- [TEST TC-22] Upload Rejection: Empty File 0 Bytes (400) ---
--> [PASS] Upload Rejection: Empty File 0 Bytes (400)

--- [TEST TC-23] Upload Rejection: Oversized File > 10 MiB (413) ---
--> [PASS] Upload Rejection: Oversized File > 10 MiB (413)

--- [TEST TC-24] Upload Rejection: Spoofed Extension / Invalid Magic Bytes (400) ---
--> [PASS] Upload Rejection: Spoofed Extension / Invalid Magic Bytes (400)

--- [TEST TC-25] Upload Rejection: Cross-User Folder Injection (404) ---
--> [PASS] Upload Rejection: Cross-User Folder Injection (404)

--- [TEST TC-26] Upload Valid File with SHA-256 Digest Computation ---
--> [PASS] Upload Valid File with SHA-256 Digest Computation

--- [TEST TC-27] File Listing, Folder Filtering, and Query Search ---
--> [PASS] File Listing, Folder Filtering, and Query Search

--- [TEST TC-28] Cross-User Isolation: File Listing ---
--> [PASS] Cross-User Isolation: File Listing

--- [TEST TC-29] Cross-User Isolation: File Metadata Inspection (403) ---
--> [PASS] Cross-User Isolation: File Metadata Inspection (403)

--- [TEST TC-30] Cross-User Isolation: File Download (403) ---
--> [PASS] Cross-User Isolation: File Download (403)

--- [TEST TC-31] Cross-User Isolation: File Deletion (403) ---
--> [PASS] Cross-User Isolation: File Deletion (403)

--- [TEST TC-32] Admin Privileges: Metadata Inspection & Audit Logging ---
--> [PASS] Admin Privileges: Metadata Inspection & Audit Logging

--- [TEST TC-33] Admin Privileges: Download Access & Audit Logging ---
--> [PASS] Admin Privileges: Download Access & Audit Logging

--- [TEST TC-34] Policy Enforcement: Admin Prohibited from Deleting User File (403) ---
--> [PASS] Policy Enforcement: Admin Prohibited from Deleting User File (403)

--- [TEST TC-35] Download Content Integrity & SHA-256 Verification ---
--> [PASS] Download Content Integrity & SHA-256 Verification

--- [TEST TC-36] Metadata Store Status Check (MongoDB Source) ---
--> [PASS] Metadata Store Status Check (MongoDB Source)

--- [TEST TC-37] Admin Metadata Reconciliation Endpoint ---
--> [PASS] Admin Metadata Reconciliation Endpoint

--- [TEST TC-38] Cascading File Deletion (SQL, MongoDB, Local Disk) ---
--> [PASS] Cascading File Deletion (SQL, MongoDB, Local Disk)

--- [CLEANUP] Cleaning up isolated test users and folders ---
--> Test records cleaned up from PostgreSQL.

============================================================
 AUDIT SUITE EXECUTION SUMMARY: 38 Passed, 0 Failed out of 38 Tests
============================================================

All 38 test cases PASSED successfully with verified evidence!
```

---

## 8. Prioritized Remediation & Future Roadmap

1. **MongoDB Indexing (Immediate / Low Risk):**
   - Add `{ id: 1 }` unique index on MongoDB `files` collection and `{ timestamp: -1 }` on `activity` collection for optimized query scaling.
2. **HttpOnly Cookie Authentication (Milestone 2):**
   - Migrate JWT transmission from `localStorage` to `HttpOnly`, `SameSite=Strict` cookies to eliminate XSS token exfiltration risks.
3. **Advanced Cryptography (Milestone 2):**
   - Implement AES-256-GCM envelope encryption at rest, KMS key rotation, cloud object storage (AWS S3 / GCP Cloud Storage), and time-limited pre-signed sharing links.
