# Performance and responsiveness

Measured on the **live deployment** (`https://<YOUR-DOMAIN>`) on **TODO: fill from my own run (<date>)**, as part of Milestone 4. It covers the performance metrics named in the project brief: encryption speed, upload / download time, API response time, concurrent users, detection accuracy, and UI responsiveness.

## Summary

| Brief metric | Result |
|---|---|
| Encryption speed | TODO: fill from my own run |
| Upload / download time | TODO: fill from my own run |
| API response time | TODO: fill from my own run |
| Concurrent users | TODO: fill from my own run |
| Detection accuracy | TODO: fill from my own run |
| UI responsiveness | TODO: fill from my own run |

## Test environment

| | |
|---|---|
| Server | TODO: fill from my own run (instance type, vCPU, RAM, region) |
| Software | Production stack from `docker-compose.yml` + `docker-compose.prod.yml`: Caddy → FastAPI → PostgreSQL, MongoDB, Redis; encrypted objects in cloud object storage |
| Users' side | TODO: fill from my own run |
| Data | Test accounts only; test files deleted afterwards |
| Idle memory | TODO: fill from my own run |

## 1. Encryption speed

Run inside the live backend container with the real encryption code (`encrypt_file`, `decrypt_bytes` in `app/services/encryption_service.py`):

| File size | Encrypt | Decrypt + verify | Size overhead |
|---|---|---|---|
| 1 MB | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run |
| 10 MB | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run |
| 25 MB | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run |

| Other cryptographic step | Time |
|---|---|
| Create a file key and wrap / unwrap it with the master key (envelope encryption) | TODO: fill from my own run |
| bcrypt password hash (cost 12) | TODO: fill from my own run |

## 2. API response time

**Server processing time** (from the backend request logs):

| Request | Median | 95th percentile |
|---|---|---|
| `GET /api/files` (list) | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/files/usage` | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/folders` | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/files/{id}` | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/users/me` | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/analytics/me` | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/s/{token}` (public link) | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/files/{id}/download` | TODO: fill from my own run | TODO: fill from my own run |
| `POST /api/auth/login` | TODO: fill from my own run | TODO: fill from my own run |

**As seen by a user** (from client machine):

| Request | Median | 95th percentile |
|---|---|---|
| `GET /api/health` | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/users/me` | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/files` (list) | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/files?q=` (search) | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/folders` | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/files/usage` | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/files/{id}` | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/files/{id}/download` | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/analytics/me` | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/notifications/unread-count` | TODO: fill from my own run | TODO: fill from my own run |
| `GET /api/s/{token}` (public link) | TODO: fill from my own run | TODO: fill from my own run |

## 3. Upload and download time

| File size | Upload – server network | Download – server network | Upload – client broadband | Download – client broadband |
|---|---|---|---|---|
| 1 MB | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run |
| 5 MB | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run |
| 10 MB | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run |
| 24 MB | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run |

## 4. Concurrent users

| Simultaneous active users | Requests per second | Median response | 95th percentile | Errors |
|---|---|---|---|---|
| 10 | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run |
| 25 | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run |
| 50 | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run |
| 100 | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run |

## 5. Detection accuracy

| Scenario | Expected | Result |
|---|---|---|
| Normal session (upload, folder, rename, downloads, share link, trash and restore) | no alert | TODO: fill from my own run |
| Wrong passwords up to limit | no rule alert | TODO: fill from my own run |
| Wrong password above limit | `repeated_failed_logins` | TODO: fill from my own run |
| Unauthorized file access up to limit | no alert | TODO: fill from my own run |
| Unauthorized file access above limit | `repeated_unauthorized_access` | TODO: fill from my own run |
| Downloads up to limit | no alert | TODO: fill from my own run |
| Download above limit | `excessive_downloads` | TODO: fill from my own run |
| Revoked link tries up to limit | no alert | TODO: fill from my own run |
| Revoked link try above limit | `revoked_link_abuse` | TODO: fill from my own run |
| Expired link tries up to limit | no alert | TODO: fill from my own run |
| Expired link try above limit | `expired_link_abuse` | TODO: fill from my own run |
| Upload of a real PDF | no alert | TODO: fill from my own run |
| Upload of a program renamed to `.pdf` | `file_threat` | TODO: fill from my own run |
| Same browser refreshes twice within grace window | no alert | TODO: fill from my own run |
| Old refresh token used from another device | `token_reuse` | TODO: fill from my own run |

| | |
|---|---|
| Attacks detected (true positives) | TODO: fill from my own run |
| Normal behaviour wrongly flagged (false positives) | TODO: fill from my own run |
| Precision · Recall | TODO: fill from my own run |

## 6. UI responsiveness and optimisation

**Page weight** (measured with `curl --compressed` on the live site):

| What | Compressed size |
|---|---|
| `index.html` | TODO: fill from my own run |
| Main JavaScript | TODO: fill from my own run |
| Styles | TODO: fill from my own run |
| Font | TODO: fill from my own run |
| **First visit total** | **TODO: fill from my own run** |
| Charts (lazy-loaded on analytics pages) | TODO: fill from my own run |

**Page load in a real browser**:

| Device size | First visit – first content | Later pages – median first content | Sideways scrolling | Console errors |
|---|---|---|---|---|
| Phone (375 × 812) | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run |
| Tablet (768 × 1024) | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run |
| Desktop (1366 × 768) | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run | TODO: fill from my own run |

## How to repeat

| Metric | How |
|---|---|
| Encryption speed | In the backend container, time `encrypt_file` / `decrypt_bytes` from `app/services/encryption_service.py` on random data |
| API time (server side) | Every request is logged with its duration: `docker compose -f docker-compose.yml -f docker-compose.prod.yml logs backend \| grep app.request` |
| API time / transfers (user side) | Time requests with any HTTP client against `https://<YOUR-DOMAIN>` using a test account |
| Concurrent users | Many async clients with a short pause between requests, run from inside the server to exclude home-network latency |
| Detection accuracy | On a local stack: for each rule, repeat the action up to the limit (no alert) and once more (alert); read `security_events` |
| Page weight / load | `curl --compressed` for sizes; a browser's Performance panel or Playwright for timings at phone / tablet / desktop sizes |
