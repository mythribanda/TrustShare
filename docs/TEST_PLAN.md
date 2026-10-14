# TrustShare Milestone 1 — Test Plan

Run `docker compose up --build`; verify http://localhost:8000/health reports PostgreSQL, MongoDB and Redis status as connected.

## Manual acceptance checklist
- [ ] Register with name, email and password of at least 8 characters.
- [ ] Register same email again; expect HTTP 409.
- [ ] Inspect PostgreSQL `users`; password must be a bcrypt hash, not plaintext.
- [ ] Log in with correct credentials; receive a bearer JWT. Wrong password should return 401.
- [ ] Call `/api/auth/me` without a token (401) and with a token (200).
- [ ] Register two accounts; verify one user cannot list/download/delete the other user's files.
- [ ] Upload a PDF/TXT/PNG; verify it is stored under `./storage`, appears in the dashboard and is indexed in PostgreSQL and MongoDB.
- [ ] Upload an unsupported extension (for example `.exe`); expect HTTP 415.
- [ ] Upload a file over `MAX_UPLOAD_MB`; expect HTTP 413 and no retained partial file.
- [ ] Search by filename; create a folder and upload a file into it.
- [ ] Download and delete an owned file; verify the local file and database record are removed.
- [ ] Verify `/api/admin/users` returns 403 for a regular user and works for an admin.
- [ ] Confirm login, upload, download and delete activity records appear in MongoDB `activity`.

## Promote a local demo admin
After registering the account, run:
`docker compose exec postgres psql -U trustshare -d trustshare -c "UPDATE users SET role='admin' WHERE email='you@example.com';"`
Log out and sign in again to receive a JWT with the updated role.

## Known limitations
- Password reset is UI-only; no reset email is sent.
- MFA and OAuth are not implemented beyond foundations/roadmap.
- MongoDB writes are best-effort so local demos can still be inspected if Mongo is temporarily unavailable; check `/health` and logs when evaluating metadata persistence.
- This project has not been run in the user's environment yet. Execute the checklist and resolve environment-specific errors before claiming acceptance.
