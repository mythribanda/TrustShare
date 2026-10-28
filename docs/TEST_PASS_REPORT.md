# TrustShare Milestone 1 — In-Depth Functional and Security Test Pass Report

**Execution Date:** October 19, 2026  
**Auditor / Reviewer:** Senior Software Engineer & Security Auditor  
**Target Environment:** Dockerized Multi-Container Stack (PostgreSQL 16, MongoDB 7, Redis 7, FastAPI, React 18 / Vite)  
**Execution Target:** `c:\Users\Mythri Banda\Desktop\github projects\trustshare-milestone1`  
**Automated Deep Suite:** [`backend/tests/test_deep_audit.py`](file:///c:/Users/Mythri%20Banda/Desktop/github%20projects/trustshare-milestone1/backend/tests/test_deep_audit.py)  
**Raw JSON Evidence:** [`docs/TEST_PASS_RESULTS.json`](file:///c:/Users/Mythri%20Banda/Desktop/github%20projects/trustshare-milestone1/docs/TEST_PASS_RESULTS.json)

---

## 1. Executive Summary

This test pass conducted rigorous, end-to-end functional and security testing across the six required areas:
- **A. Search and Folders:** 12 tests executed.
- **B. Upload Validation & Path Traversal:** 10 tests executed.
- **C. Authentication and Authorization:** 10 tests executed.
- **D. File Integrity and Lifecycle:** 3 tests executed.
- **E. Database Consistency:** 4 tests executed.
- **F. Automated Tests & Build Verification:** 2 test suites + production build executed.

**Overall Test Results:** **39 / 39 Tests PASSED (100% Success Rate)** with zero critical failures.

---

## 2. Comprehensive Test Execution Matrix

| Test ID | Category | Test Description | Expected Result | Actual Observed Result | Status | Concrete Evidence / Trace |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **TEST-A01** | Search & Folders | Create folder with valid name | HTTP 201 with folder id & name | HTTP 201 | **PASS** | Created folder ID 6 (`name: "Financial_Reports"`) |
| **TEST-A02** | Search & Folders | Create folder with empty/whitespace name | HTTP 422 or 400 rejection | HTTP 422 | **PASS** | Returned 422 with `'Folder name is required'` |
| **TEST-A03** | Search & Folders | Create folder with duplicate name | Permitted by schema or 409 | HTTP 201 | **PASS** | Schema allows duplicates per user; created ID 7 |
| **TEST-A04** | Search & Folders | List user folders | HTTP 200 with user's folders | HTTP 200, count=2 | **PASS** | Returned folders: `['Financial_Reports', 'Financial_Reports']` |
| **TEST-A05** | Search & Folders | Exact filename search (`Quarterly_Summary_2026.txt`) | HTTP 200 with exactly matched file | HTTP 200, count=1 | **PASS** | Matched file ID 6 |
| **TEST-A06** | Search & Folders | Partial filename search (`q=Quarterly`) | HTTP 200 containing partial match | HTTP 200, count=1 | **PASS** | Matched file `Quarterly_Summary_2026.txt` |
| **TEST-A07** | Search & Folders | Mixed-case search (`q=qUaRtErLy_SuMmArY`) | HTTP 200 case-insensitive match | HTTP 200, count=1 | **PASS** | `ilike` query successfully matched mixed-case input |
| **TEST-A08** | Search & Folders | Nonexistent filename search | HTTP 200 with empty list | HTTP 200, count=0 | **PASS** | Returned `[]` (empty array) |
| **TEST-A09** | Search & Folders | Clearing search parameter (omitting `q`) | HTTP 200 restoring full file list | HTTP 200, count=2 | **PASS** | Returned all files belonging to authenticated user |
| **TEST-A10** | Search & Folders | Search scope check (files only vs folders) | `/api/files?q=` covers filenames only | Files matched: 0 | **PASS** | Query matching folder name returns 0 files; scope is files only |
| **TEST-A11** | Search & Folders | Filter files by `folder_id` | HTTP 200 returning files in folder | HTTP 200, count=2 | **PASS** | All returned files have `folder_id == 6` |
| **TEST-A12** | Search & Folders | Cross-user search isolation (User B searches User A file) | HTTP 200 with 0 results | HTTP 200, count=0 | **PASS** | Query filtered by `owner_id == user_b.id`; 0 records leaked |
| **TEST-B01** | Upload Validation | Upload valid small text file | HTTP 201 created | HTTP 201 | **PASS** | Assigned file ID 8; SHA-256 computed on stream |
| **TEST-B02** | Upload Validation | Upload zero-byte file | HTTP 400 rejection | HTTP 400 | **PASS** | Returned 400 with `'Empty files are not allowed'` |
| **TEST-B03** | Upload Validation | Upload unsupported extension (`.exe`) | HTTP 415 rejection | HTTP 415 | **PASS** | Returned 415 with `'File type not allowed'` |
| **TEST-B04** | Upload Validation | Upload unsupported extension (`.sh`) | HTTP 415 rejection | HTTP 415 | **PASS** | Returned 415 with `'File type not allowed'` |
| **TEST-B05** | Upload Validation | Upload file exactly at 10 MiB limit (10,485,760 B) | HTTP 201 created (size <= limit) | HTTP 201 | **PASS** | File stored successfully; size = 10,485,760 bytes |
| **TEST-B06** | Upload Validation | Upload file exceeding 10 MiB limit (+128 KiB) | HTTP 413 rejection | HTTP 413 | **PASS** | Returned 413 `'File exceeds 10 MiB limit'` |
| **TEST-B07** | Upload Validation | Path traversal filename (`../../etc/passwd.txt`) | Traversal neutralized via UUID name | HTTP 201, stored='d7478...txt' | **PASS** | Saved as `{uuid}.txt`; original name sanitized to `passwd.txt` |
| **TEST-B08** | Upload Validation | Spoofed extension (plain text named `.pdf`) | HTTP 400 magic bytes rejection | HTTP 400 | **PASS** | Rejected: missing `%PDF-` header signature |
| **TEST-B09** | Upload Validation | Inconsistent Content-Type header vs extension | Server derives canonical MIME type | HTTP 201, MIME: text/plain | **PASS** | Client header ignored; server applied `text/plain` |
| **TEST-B10** | Upload Validation | Orphaned files check after rejected upload | 0 residual files on disk / DB | New files on disk: 0 | **PASS** | Partial file unlinked in try/except; 0 orphaned files |
| **TEST-C01** | Auth & Authz | Protected route without token | HTTP 401 rejection | HTTP 401 | **PASS** | Returned 401 `'Authentication required'` |
| **TEST-C02** | Auth & Authz | Protected route with malformed token | HTTP 401 rejection | HTTP 401 | **PASS** | Returned 401 `'Invalid or expired token'` |
| **TEST-C03** | Auth & Authz | Protected route with tampered signature | HTTP 401 rejection | HTTP 401 | **PASS** | Returned 401 `'Invalid or expired token'` |
| **TEST-C04** | Auth & Authz | Protected route with expired JWT token | HTTP 401 rejection | HTTP 401 | **PASS** | Returned 401 `'Invalid or expired token'` |
| **TEST-C05** | Auth & Authz | Login with incorrect password | HTTP 401 rejection | HTTP 401 | **PASS** | Returned 401 `'Incorrect email or password'` |
| **TEST-C06** | Auth & Authz | Cross-user metadata inspection by ID guessing | HTTP 403 Forbidden | HTTP 403 | **PASS** | User B receives 403 when requesting User A's file ID |
| **TEST-C07** | Auth & Authz | Cross-user file download by ID guessing | HTTP 403 Forbidden | HTTP 403 | **PASS** | User B receives 403 when downloading User A's file ID |
| **TEST-C08** | Auth & Authz | Cross-user file deletion by ID guessing | HTTP 403 Forbidden | HTTP 403 | **PASS** | User B receives 403 `'Only the file owner can delete this file'` |
| **TEST-C09** | Auth & Authz | Regular user calls admin route (`/api/admin/users`) | HTTP 403 Forbidden | HTTP 403 | **PASS** | Regular user rejected with HTTP 403 `'Insufficient permissions'` |
| **TEST-C10** | Auth & Authz | Admin user calls admin route (`/api/admin/users`) | HTTP 200 with user list | HTTP 200, count=6 | **PASS** | Admin receives full list of registered accounts |
| **TEST-D01** | Integrity & Lifecycle | Independent SHA-256 calculation comparison | Client == API == PostgreSQL == MongoDB | Match: True | **PASS** | All 4 hash locations match exact 64-character digest |
| **TEST-D02** | Integrity & Lifecycle | Download byte-for-byte exact match | 100% byte comparison match | HTTP 200, size=73 B | **PASS** | Downloaded payload identical to uploaded test buffer |
| **TEST-D03** | Integrity & Lifecycle | Cascading deletion across all tiers | SQL=0, Mongo=0, Disk=False | SQL=0, Mongo=0, Disk=False | **PASS** | File record, MongoDB metadata, and physical disk file all removed |
| **TEST-E01** | Database Consistency | PostgreSQL relational foreign keys | Active FK constraints in Postgres | FK exists: True | **PASS** | `files_owner_id_fkey` confirmed active in PostgreSQL |
| **TEST-E02** | Database Consistency | MongoDB metadata document sync | source: 'mongodb', synced: true | HTTP 200, source=mongodb | **PASS** | Metadata successfully queried from MongoDB collection |
| **TEST-E03** | Database Consistency | Redis session revocation on logout | Active session deleted on logout | Before=True, After=False, 401 | **PASS** | Token immediately rejected on `/api/auth/me` after logout |
| **TEST-E04** | Database Consistency | Admin metadata reconciliation endpoint | HTTP 200 with scanned report | HTTP 200, scanned=8 | **PASS** | Reconciled any out-of-sync records successfully |

---

## 3. Defects, Observations, and Prioritized Fix Plan

### Defect / Observation OBS-01: Duplicate Folder Names Allowed per User
- **Location:** `backend/app/main.py#L120-L125` (`class Folder`) and `#L370-L376` (`create_folder`)
- **Severity:** Low (Usability / Schema Design)
- **Observation:** Neither the database schema (`folders` table) nor the endpoint `create_folder` checks whether a folder with the same name already exists for the user. When a user submits an identical folder name twice, two rows are created with different IDs.
- **Evidence:** `TEST-A03` returned HTTP 201 twice, creating folder IDs 6 and 7 with the name `"Financial_Reports"`.
- **Recommendation:** Add a uniqueness check in `create_folder`:
  ```python
  if db.scalar(select(Folder).where(Folder.owner_id == user.id, Folder.name == name)):
      raise HTTPException(409, 'A folder with this name already exists')
  ```

### Defect / Observation OBS-02: Missing Secondary Index on MongoDB `files.id`
- **Location:** `backend/app/main.py#L160-L171` (`init_mongo`)
- **Severity:** Low (Query Scaling)
- **Observation:** The MongoDB `files` collection has only the default `_id` index. Metadata lookups (`mdb.files.find_one({'id': file_id})`) and deletions perform collection scans.
- **Recommendation:** Add an index during application startup:
  ```python
  mdb.files.create_index([("id", 1)], unique=True)
  mdb.activity.create_index([("timestamp", -1)])
  ```

### Defect / Observation OBS-03: Client-Side Token Storage in `localStorage`
- **Location:** `frontend/src/App.jsx#L48`
- **Severity:** Medium (Milestone 2 Security Roadmap)
- **Observation:** JWT tokens are stored in `localStorage`, which is accessible to client-side scripts.
- **Recommendation:** Migrate authentication token transport to `HttpOnly`, `Secure`, `SameSite=Strict` cookies in Milestone 2.
