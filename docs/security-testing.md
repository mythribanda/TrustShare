# Security testing

Security testing of the **live deployment** (`https://<YOUR-DOMAIN>`) on **TODO: fill from my own run (<date>)**, as part of Milestone 4.

> See also [SECURITY_TEST_REPORT.md](SECURITY_TEST_REPORT.md) for the recorded Milestone 4 SAST, dependency audit, and defensive security test results.

## Summary

| | |
|---|---|
| Tests run against the live site | TODO: fill from my own run |
| Passed | TODO: fill from my own run |
| Weaknesses found | TODO: fill from my own run |
| Dependency scan (backend + frontend) | TODO: fill from my own run |
| Attacks noticed by threat detection | TODO: fill from my own run |
| Automated tests in CI | TODO: fill from my own run |

| Area | Tests | Passed | Fixed |
|---|---|---|---|
| HTTPS and TLS | 4 | TODO: fill from my own run | TODO: fill from my own run |
| Security headers | 8 | TODO: fill from my own run | TODO: fill from my own run |
| Network exposure | 5 | TODO: fill from my own run | TODO: fill from my own run |
| Information exposure | 11 | TODO: fill from my own run | TODO: fill from my own run |
| Sessions and tokens | 7 | TODO: fill from my own run | TODO: fill from my own run |
| Authentication | 8 | TODO: fill from my own run | TODO: fill from my own run |
| Brute-force protection | 2 | TODO: fill from my own run | TODO: fill from my own run |
| Access control (RBAC and ownership) | 18 | TODO: fill from my own run | TODO: fill from my own run |
| Direct sharing | 5 | TODO: fill from my own run | TODO: fill from my own run |
| Share links | 12 | TODO: fill from my own run | TODO: fill from my own run |
| File upload validation | 11 | TODO: fill from my own run | TODO: fill from my own run |
| Injection | 7 | TODO: fill from my own run | TODO: fill from my own run |
| Error handling | 2 | TODO: fill from my own run | TODO: fill from my own run |
| Input validation | 2 | TODO: fill from my own run | TODO: fill from my own run |
| Data protection | 2 | TODO: fill from my own run | TODO: fill from my own run |

## Scope and method

- **Target:** the production stack (`Caddy (HTTPS) → FastAPI → PostgreSQL, MongoDB, Redis, object storage`) at `https://<YOUR-DOMAIN>`.
- **Accounts:** dedicated test accounts only; no real user data touched.
- **Method:** black-box HTTP/TLS/socket checks against the live endpoint, cross-checked against server logs and `security_events`.
- **Checklist:** based on the OWASP Top 10 (2021).

| OWASP Top 10 (2021) | Covered by |
|---|---|
| A01 Broken access control | Access control, direct sharing, share links (IDOR, privilege escalation, role tampering) |
| A02 Cryptographic failures | HTTPS / TLS, cookie flags, file decrypted correctly, no keys in responses, [key management](key-management.md) |
| A03 Injection | SQL, NoSQL operator and regex injection; script in file names; HTML in text previews |
| A04 Insecure design | Download limits, link expiry and revoke, enumeration-safe login and reset |
| A05 Security misconfiguration | Headers, open ports, API schema / `.env` / `.git` exposure, CORS, TRACE, error messages |
| A06 Vulnerable components | `pip-audit` and `npm audit` |
| A07 Identification and authentication failures | Token forgery, refresh-token reuse, lockout, rate limits, weak passwords |
| A08 Software and data integrity failures | Signed JWTs (`HS256` only, `alg=none` refused); hash-chained audit log |
| A09 Security logging and monitoring failures | Security events raised during the test run |
| A10 Server-side request forgery | Not applicable – the server never fetches URLs supplied by users |

## Findings

| ID | Finding | Severity | Status |
|---|---|---|---|
| TODO | TODO: fill from my own run | TODO | TODO |

### Observations (by design, no change needed)

- TODO: fill from my own run (document any design observations from your live test run).

## Threat detection during the test

| Security event | Count | Caused by |
|---|---|---|
| `unauthorized_access` | TODO: fill from my own run | Another user / wrong role trying files and admin pages |
| `blocked_request` | TODO: fill from my own run | Requests stopped by rate limits and lockout |
| `token_reuse` | TODO: fill from my own run | Re-used refresh tokens |
| `policy_violation` | TODO: fill from my own run | Disallowed file types uploaded |
| `file_threat` | TODO: fill from my own run | Disguised files |
| `multiple_failed_logins`, `repeated_failed_logins` | TODO: fill from my own run | Wrong-password attempts |
| `account_locked` | TODO: fill from my own run | Lockout test |
| `repeated_unauthorized_access` | TODO: fill from my own run | Access-control tests in a row |
| `revoked_link_abuse` | TODO: fill from my own run | Opening a revoked link |
| `suspicious_ip`, `new_device_login` | TODO: fill from my own run | Failures from one IP / new test client |

## Dependency scan

| Part | Tool | Result |
|---|---|---|
| Backend (Python) | `pip-audit -r backend/requirements.txt` | TODO: fill from my own run |
| Frontend (npm) | `npm audit` | TODO: fill from my own run |

## Automated security tests

The live test complements the automated tests (`docker compose exec backend pytest` and `docs/test-results/`), which cover encryption, RBAC, tokens, audit hash chain, detection rules, and the secure vault.

## How to repeat the test

1. Create test accounts on the target (`@uicheck.example.com`).
2. Run the request-level checks below or the Postman collections in `postman/`.
3. Afterwards, remove the test accounts:
   `docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python -m app.scripts.remove_test_accounts uicheck.example.com`.

## All test results

### HTTPS and TLS

| # | Test | Expected | Result on the live site |
|---|---|---|---|
| 1 | HTTP is redirected to HTTPS | 301/308 to `https://<YOUR-DOMAIN>/` | TODO: fill from my own run |
| 2 | Old protocol TLS 1.0 refused | handshake fails | TODO: fill from my own run |
| 3 | Old protocol TLS 1.1 refused | handshake fails | TODO: fill from my own run |
| 4 | Trusted certificate, modern TLS | valid chain, TLS 1.2+ | TODO: fill from my own run |

### Security headers

| # | Test | Expected | Result on the live site |
|---|---|---|---|
| 5 | `strict-transport-security` on pages | present with `max-age` | TODO: fill from my own run |
| 6 | `content-security-policy` on pages | present | TODO: fill from my own run |
| 7 | `x-frame-options` on pages | `DENY` | TODO: fill from my own run |
| 8 | `x-content-type-options` on pages | `nosniff` | TODO: fill from my own run |
| 9 | `referrer-policy` on pages | `strict-origin-when-cross-origin` | TODO: fill from my own run |
| 10 | `permissions-policy` on pages | present | TODO: fill from my own run |
| 11 | No `Server`/`X-Powered-By` version banner | absent | TODO: fill from my own run |
| 12 | API responses not cached (`Cache-Control`) | `no-store` | TODO: fill from my own run |

### Network exposure

| # | Test | Expected | Result on the live site |
|---|---|---|---|
| 13 | Port 5432 (PostgreSQL) from the internet | closed | TODO: fill from my own run |
| 14 | Port 27017 (MongoDB) from the internet | closed | TODO: fill from my own run |
| 15 | Port 6379 (Redis) from the internet | closed | TODO: fill from my own run |
| 16 | Port 8000 (backend direct) from the internet | closed | TODO: fill from my own run |
| 17 | Port 22 (SSH) from the internet | key-only login | TODO: fill from my own run |

### Information exposure

| # | Test | Expected | Result on the live site |
|---|---|---|---|
| 18–26 | `/docs`, `/openapi.json`, `/redoc`, `/api/docs`, `/api/openapi.json`, `/.env`, `/.git/config`, `/api/.env`, `/backend/.env` | no schema or secrets exposed | TODO: fill from my own run |
| 27 | `TRACE` method disabled | 405/404 | TODO: fill from my own run |
| 28 | CORS: other websites not allowed | no `Access-Control-Allow-Origin` | TODO: fill from my own run |

### Sessions and tokens

| # | Test | Expected | Result on the live site |
|---|---|---|---|
| 29–35 | Refresh cookie flags, access token TTL, refresh rotation, reuse detection, logout invalidation | expected flags, rotation, and 401 on reuse/logout | TODO: fill from my own run |

### Authentication

| # | Test | Expected | Result on the live site |
|---|---|---|---|
| 36–43 | Missing/garbage/tampered/`alg=none`/wrong-secret/expired tokens, enumeration-safe login and forgot-password | 401 on invalid tokens; uniform responses | TODO: fill from my own run |

### Brute-force protection

| # | Test | Expected | Result on the live site |
|---|---|---|---|
| 44–45 | 5 wrong passwords lock account; per-IP login rate limit | 401 ×5 then 429; rate limit 429 | TODO: fill from my own run |

### Access control (RBAC and ownership)

| # | Test | Expected | Result on the live site |
|---|---|---|---|
| 46–63 | User role blocked from admin routes (403); role escalation blocked; another user's files return 404; path traversal blocked | 403 / 404 / 422 | TODO: fill from my own run |

### Direct sharing

| # | Test | Expected | Result on the live site |
|---|---|---|---|
| 64–68 | View-only blocks download (403) and allows preview (200); recipient cannot revoke or read access history; revoked share returns 410 | 403 / 200 / 404 / 410 | TODO: fill from my own run |

### Share links

| # | Test | Expected | Result on the live site |
|---|---|---|---|
| 69–80 | Unknown/injected tokens, view-only, download limits, decryption integrity, revocation, `no-store`, password protection, expiry bounds, trashed file, no owner PII leaked | expected statuses and no PII | TODO: fill from my own run |

### File upload validation

| # | Test | Expected | Result on the live site |
|---|---|---|---|
| 81–91 | Disallowed types/magic bytes/SVG/double extension rejected (415); >25 MB rejected (413); path traversal sanitized; script filename escaped; text preview sandboxed; download attachment header | 415 / 413 / safe storage & headers | TODO: fill from my own run |

### Injection

| # | Test | Expected | Result on the live site |
|---|---|---|---|
| 92–98 | SQLi, NoSQL operator injection, regex wildcard in search, operator in `folder_id`/`file_id` | 422 / 401 / 200 (0 results) / 404 | TODO: fill from my own run |

### Error handling

| # | Test | Expected | Result on the live site |
|---|---|---|---|
| 99–100 | Malformed JSON; unknown API route | 422 / 404, no stack trace | TODO: fill from my own run |

### Input validation

| # | Test | Expected | Result on the live site |
|---|---|---|---|
| 101–102 | Very long folder name; weak password | 422 | TODO: fill from my own run |

### Data protection

| # | Test | Expected | Result on the live site |
|---|---|---|---|
| 103–104 | File details omit keys/storage paths; profile omits password hash/MFA secret | none present | TODO: fill from my own run |
