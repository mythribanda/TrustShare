"""
TrustShare Milestone 1 — Comprehensive Evidence-Based Engineering Audit Suite
Tests:
- Health & readiness endpoints
- User registration (valid, duplicate, short password, bad email)
- Password hashing verification (bcrypt salt check in PostgreSQL)
- Login (valid, wrong password, non-existent user)
- Token & session verification (valid, missing, invalid, logout session revocation via Redis)
- Role-based access control (RBAC: user vs admin on /api/admin/users)
- Folder creation, listing, and cross-user isolation
- File upload validation (unsupported extension, empty file, oversize file, spoofed MIME/header)
- Cross-user folder injection prevention (upload to other's folder)
- SHA-256 computation and download integrity verification
- Cross-user file isolation (list, metadata, download, delete)
- Admin audit logging for cross-user inspection and owner-only deletion enforcement
- Metadata synchronization and reconciliation
- File deletion and cascading cleanup (PostgreSQL, MongoDB, local disk)
"""

import sys
import os
import json
import time
import uuid
import hashlib
import urllib.request
import urllib.error
import urllib.parse
import subprocess

API_URL = os.getenv("API_URL", "http://localhost:8000")

passed_tests = []
failed_tests = []

def log(section, msg):
    print(f"[{section}] {msg}")

def request(method, path, data=None, token=None, headers=None, content_type="application/json"):
    url = f"{API_URL}{path}"
    req_headers = headers.copy() if headers else {}
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    
    body = None
    if data is not None:
        if content_type == "application/json":
            req_headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode("utf-8")
        elif isinstance(data, (bytes, bytearray)):
            body = data
        elif isinstance(data, str):
            body = data.encode("utf-8")
    
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = resp.read()
            status = resp.status
            content_type_resp = resp.headers.get("Content-Type", "")
            if "application/json" in content_type_resp:
                try:
                    parsed = json.loads(resp_body.decode("utf-8"))
                except Exception:
                    parsed = resp_body.decode("utf-8", errors="replace")
            else:
                parsed = resp_body
            return status, parsed, resp.headers
    except urllib.error.HTTPError as e:
        resp_body = e.read()
        try:
            parsed = json.loads(resp_body.decode("utf-8"))
        except Exception:
            parsed = resp_body.decode("utf-8", errors="replace")
        return e.code, parsed, e.headers
    except Exception as e:
        return 0, str(e), {}

def encode_multipart_formdata(fields, files):
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body = bytearray()
    
    for k, v in fields.items():
        if v is not None:
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode("utf-8"))
            body.extend(f"{v}\r\n".encode("utf-8"))
            
    for field_name, (filename, file_bytes, content_type) in files.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(file_bytes)
        body.extend(b"\r\n")
        
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    return body, headers

def run_psql(cmd):
    try:
        res = subprocess.run(
            ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "trustshare", "-d", "trustshare", "-t", "-A", "-c", cmd],
            capture_output=True, text=True, check=True
        )
        return res.stdout.strip()
    except Exception as e:
        return None

def run_mongosh(cmd):
    try:
        res = subprocess.run(
            ["docker", "compose", "exec", "-T", "mongo", "mongosh", "--quiet", "--eval", cmd],
            capture_output=True, text=True, check=True
        )
        return res.stdout.strip()
    except Exception as e:
        return None

def run_redis(cmd):
    try:
        args = ["docker", "compose", "exec", "-T", "redis", "redis-cli"] + cmd.split()
        res = subprocess.run(args, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception as e:
        return None

def reset_login_ratelimits():
    keys = run_redis("keys ratelimit:login:*")
    if keys:
        for k in keys.split():
            if k.strip():
                run_redis(f"del {k.strip()}")

def run_test(test_id, name, fn):
    try:
        print(f"\n--- [TEST {test_id}] {name} ---")
        fn()
        print(f"--> [PASS] {name}")
        passed_tests.append((test_id, name))
    except AssertionError as e:
        print(f"--> [FAIL] {name}: Assertion failed: {e}")
        failed_tests.append((test_id, name, str(e)))
    except Exception as e:
        print(f"--> [ERROR] {name}: Exception: {e}")
        failed_tests.append((test_id, name, str(e)))

# State across tests
ctx = {
    "user_a_email": f"audit.user.a.{uuid.uuid4().hex[:8]}@example.com",
    "user_a_pass": "SuperSecurePass123!",
    "user_a_token": None,
    "user_a_id": None,
    "user_b_email": f"audit.user.b.{uuid.uuid4().hex[:8]}@example.com",
    "user_b_pass": "SuperSecurePass456!",
    "user_b_token": None,
    "user_b_id": None,
    "admin_email": f"audit.admin.{uuid.uuid4().hex[:8]}@example.com",
    "admin_pass": "AdminMasterPass789!",
    "admin_token": None,
    "admin_id": None,
    "user_a_folder_id": None,
    "user_a_file_id": None,
    "user_a_file_content": b"TrustShare Milestone 1 Audit Verification Payload",
    "user_a_file_hash": None,
    "user_a_file_stored_name": None,
}

# 1. Health & Readiness Tests
def test_health():
    status, body, _ = request("GET", "/health")
    assert status == 200, f"Expected 200, got {status}"
    assert body.get("status") == "ok", f"Expected status ok, got {body}"

def test_health_ready():
    status, body, _ = request("GET", "/health/ready")
    assert status == 200, f"Expected 200, got {status} ({body})"
    assert body.get("status") == "ok", f"Expected status ok, got {body}"
    assert body.get("postgres") == "connected", f"Postgres not connected: {body}"
    assert body.get("mongodb") == "connected", f"MongoDB not connected: {body}"
    assert body.get("redis") == "connected", f"Redis not connected: {body}"

# 2. Registration Tests
def test_registration_valid():
    payload = {"name": "Audit User A", "email": ctx["user_a_email"], "password": ctx["user_a_pass"]}
    status, body, _ = request("POST", "/api/auth/register", data=payload)
    assert status == 201, f"Expected 201, got {status} ({body})"
    assert "access_token" in body, "access_token missing from registration response"
    assert "user" in body, "user object missing from registration response"
    assert body["user"]["email"] == ctx["user_a_email"], "email mismatch"
    ctx["user_a_token"] = body["access_token"]
    ctx["user_a_id"] = body["user"]["id"]

def test_registration_duplicate():
    payload = {"name": "Audit User A Duplicate", "email": ctx["user_a_email"], "password": ctx["user_a_pass"]}
    status, body, _ = request("POST", "/api/auth/register", data=payload)
    assert status == 409, f"Expected 409, got {status} ({body})"

def test_registration_invalid_email():
    payload = {"name": "Invalid Email", "email": "not-an-email", "password": "Password123!"}
    status, body, _ = request("POST", "/api/auth/register", data=payload)
    assert status == 422, f"Expected 422, got {status} ({body})"

def test_registration_short_password():
    payload = {"name": "Short Pass", "email": f"short.{uuid.uuid4().hex[:6]}@example.com", "password": "short"}
    status, body, _ = request("POST", "/api/auth/register", data=payload)
    assert status == 422, f"Expected 422, got {status} ({body})"

def test_db_password_hashing():
    pw_hash = run_psql(f"SELECT password_hash FROM users WHERE id={ctx['user_a_id']};")
    assert pw_hash is not None, "Failed to query users table in PostgreSQL"
    assert pw_hash != ctx["user_a_pass"], "Password stored as plaintext!"
    assert pw_hash.startswith("$2b$") or pw_hash.startswith("$2a$"), f"Password is not a valid bcrypt hash: {pw_hash[:10]}..."

# 3. Authentication & Session Tests
def test_login_valid():
    payload = {"email": ctx["user_a_email"], "password": ctx["user_a_pass"]}
    status, body, _ = request("POST", "/api/auth/login", data=payload)
    assert status == 200, f"Expected 200, got {status} ({body})"
    assert "access_token" in body, "access_token missing"
    ctx["user_a_token"] = body["access_token"]

def test_login_wrong_password():
    payload = {"email": ctx["user_a_email"], "password": "WrongPassword999!"}
    status, body, _ = request("POST", "/api/auth/login", data=payload)
    assert status == 401, f"Expected 401, got {status} ({body})"

def test_login_nonexistent_email():
    payload = {"email": f"ghost.{uuid.uuid4().hex[:8]}@example.com", "password": "Password123!"}
    status, body, _ = request("POST", "/api/auth/login", data=payload)
    assert status == 401, f"Expected 401, got {status} ({body})"

def test_auth_me_valid():
    status, body, _ = request("GET", "/api/auth/me", token=ctx["user_a_token"])
    assert status == 200, f"Expected 200, got {status} ({body})"
    assert body.get("user", {}).get("id") == ctx["user_a_id"], "User ID mismatch on /api/auth/me"

def test_auth_me_missing_token():
    status, body, _ = request("GET", "/api/auth/me")
    assert status == 401, f"Expected 401, got {status} ({body})"

def test_auth_me_invalid_token():
    status, body, _ = request("GET", "/api/auth/me", token="invalid.token.structure")
    assert status == 401, f"Expected 401, got {status} ({body})"

def test_logout_session_revocation():
    # Login again to get a fresh token to test revocation
    status, body, _ = request("POST", "/api/auth/login", data={"email": ctx["user_a_email"], "password": ctx["user_a_pass"]})
    assert status == 200
    temp_token = body["access_token"]
    
    # Confirm valid
    status, _, _ = request("GET", "/api/auth/me", token=temp_token)
    assert status == 200, "Token should be valid before logout"
    
    # Logout
    status, body, _ = request("POST", "/api/auth/logout", token=temp_token)
    assert status == 200, f"Logout returned {status}: {body}"
    
    # Attempt /api/auth/me again with the logged-out token
    status, body, _ = request("GET", "/api/auth/me", token=temp_token)
    assert status == 401, f"Expected 401 after logout session revocation, got {status} ({body})"
    
    # Re-login User A so ctx["user_a_token"] is active for subsequent tests
    reset_login_ratelimits()
    status, body, _ = request("POST", "/api/auth/login", data={"email": ctx["user_a_email"], "password": ctx["user_a_pass"]})
    assert status == 200, f"Expected 200, got {status} ({body})"
    ctx["user_a_token"] = body["access_token"]

def test_login_rate_limiting():
    # Reset ratelimits first
    reset_login_ratelimits()
    # Execute 5 failed logins
    for i in range(5):
        st, _, _ = request("POST", "/api/auth/login", data={"email": "ratelimit.test@example.com", "password": "WrongPassword!"})
        assert st == 401, f"Expected 401 on attempt {i+1}, got {st}"
    # 6th attempt within window should return 429 Too Many Requests
    st, body, _ = request("POST", "/api/auth/login", data={"email": "ratelimit.test@example.com", "password": "WrongPassword!"})
    assert st == 429, f"Expected 429 Rate Limit Exceeded on attempt 6, got {st} ({body})"
    assert "Rate limit exceeded" in str(body), f"Expected 'Rate limit exceeded' in response detail: {body}"
    # Reset ratelimits so following tests proceed smoothly
    reset_login_ratelimits()

# 4. RBAC & Admin Tests
def test_admin_users_forbidden_for_regular_user():
    status, body, _ = request("GET", "/api/admin/users", token=ctx["user_a_token"])
    assert status == 403, f"Expected 403 Forbidden for non-admin, got {status} ({body})"

def test_admin_users_allowed_for_admin():
    # Register admin candidate
    status, body, _ = request("POST", "/api/auth/register", data={"name": "Audit Admin", "email": ctx["admin_email"], "password": ctx["admin_pass"]})
    assert status == 201, f"Admin registration failed: {status} ({body})"
    ctx["admin_id"] = body["user"]["id"]
    
    # Promote admin in PostgreSQL
    run_psql(f"UPDATE users SET role='admin' WHERE id={ctx['admin_id']};")
    
    # Reset ratelimits before admin login to avoid tripping the 5 logins/min limit
    reset_login_ratelimits()
    
    # Login as admin to get admin token
    status, body, _ = request("POST", "/api/auth/login", data={"email": ctx["admin_email"], "password": ctx["admin_pass"]})
    assert status == 200, f"Admin login failed: expected 200, got {status} ({body})"
    ctx["admin_token"] = body["access_token"]
    assert body["user"]["role"] == "admin", f"Expected admin role, got {body['user']['role']}"
    
    # Call /api/admin/users
    status, body, _ = request("GET", "/api/admin/users", token=ctx["admin_token"])
    assert status == 200, f"Expected 200 for admin, got {status} ({body})"
    assert isinstance(body, list), "Expected list of users"
    assert any(u["id"] == ctx["admin_id"] for u in body), "Admin user not found in /api/admin/users list"

# 5. Folder Tests
def test_folder_creation_valid():
    status, body, _ = request("POST", "/api/folders", data={"name": "Audit Folder A1"}, token=ctx["user_a_token"])
    assert status == 201, f"Expected 201, got {status} ({body})"
    assert body.get("name") == "Audit Folder A1"
    ctx["user_a_folder_id"] = body["id"]

def test_folder_creation_empty_name():
    status, body, _ = request("POST", "/api/folders", data={"name": "   "}, token=ctx["user_a_token"])
    assert status in (422, 400), f"Expected 422 or 400 for empty folder name, got {status} ({body})"

def test_folder_listing_and_isolation():
    # Register User B
    status, body, _ = request("POST", "/api/auth/register", data={"name": "Audit User B", "email": ctx["user_b_email"], "password": ctx["user_b_pass"]})
    assert status == 201
    ctx["user_b_token"] = body["access_token"]
    ctx["user_b_id"] = body["user"]["id"]
    
    # User A lists folders
    status, body_a, _ = request("GET", "/api/folders", token=ctx["user_a_token"])
    assert status == 200
    assert any(f["id"] == ctx["user_a_folder_id"] for f in body_a), "User A should see own folder"
    
    # User B lists folders
    status, body_b, _ = request("GET", "/api/folders", token=ctx["user_b_token"])
    assert status == 200
    assert not any(f["id"] == ctx["user_a_folder_id"] for f in body_b), "User B must NOT see User A's folder"

# 6. File Upload Validation Tests
def test_upload_unsupported_extension():
    content = b"MZ\x90\x00\x03\x00\x00\x00executable bytes"
    body, headers = encode_multipart_formdata({}, {"file": ("malware.exe", content, "application/octet-stream")})
    status, res, _ = request("POST", "/api/files/upload", data=body, token=ctx["user_a_token"], headers=headers, content_type=None)
    assert status == 415, f"Expected 415 for .exe, got {status} ({res})"

def test_upload_empty_file():
    body, headers = encode_multipart_formdata({}, {"file": ("empty.txt", b"", "text/plain")})
    status, res, _ = request("POST", "/api/files/upload", data=body, token=ctx["user_a_token"], headers=headers, content_type=None)
    assert status == 400, f"Expected 400 for empty file, got {status} ({res})"

def test_upload_oversized_file():
    # 10 MiB limit + 256 KiB = 10.25 MiB
    oversized = b"0" * (10 * 1024 * 1024 + 256 * 1024)
    body, headers = encode_multipart_formdata({}, {"file": ("huge.txt", oversized, "text/plain")})
    status, res, _ = request("POST", "/api/files/upload", data=body, token=ctx["user_a_token"], headers=headers, content_type=None)
    assert status == 413, f"Expected 413 for oversized file, got {status} ({res})"

def test_upload_spoofed_pdf_magic_bytes():
    # Text file masquerading as .pdf without %PDF- header
    fake_pdf = b"This is just a plain text file pretending to be PDF"
    body, headers = encode_multipart_formdata({}, {"file": ("spoofed.pdf", fake_pdf, "application/pdf")})
    status, res, _ = request("POST", "/api/files/upload", data=body, token=ctx["user_a_token"], headers=headers, content_type=None)
    assert status == 400, f"Expected 400 for invalid PDF signature, got {status} ({res})"

def test_upload_cross_user_folder_injection():
    # User B attempts to upload into User A's folder
    txt_content = b"Hello from user B"
    body, headers = encode_multipart_formdata(
        {"folder_id": str(ctx["user_a_folder_id"])},
        {"file": ("injected.txt", txt_content, "text/plain")}
    )
    status, res, _ = request("POST", "/api/files/upload", data=body, token=ctx["user_b_token"], headers=headers, content_type=None)
    assert status == 404, f"Expected 404 for uploading to another user's folder, got {status} ({res})"

def test_upload_valid_file_with_sha256():
    ctx["user_a_file_hash"] = hashlib.sha256(ctx["user_a_file_content"]).hexdigest()
    body, headers = encode_multipart_formdata(
        {"folder_id": str(ctx["user_a_folder_id"])},
        {"file": ("audit_sample.txt", ctx["user_a_file_content"], "text/plain")}
    )
    status, res, _ = request("POST", "/api/files/upload", data=body, token=ctx["user_a_token"], headers=headers, content_type=None)
    assert status == 201, f"Expected 201 for valid upload, got {status} ({res})"
    assert res.get("name") == "audit_sample.txt", "Original name mismatch"
    assert res.get("sha256") == ctx["user_a_file_hash"], f"SHA-256 mismatch: {res.get('sha256')} vs {ctx['user_a_file_hash']}"
    assert res.get("folder_id") == ctx["user_a_folder_id"], "Folder ID mismatch"
    ctx["user_a_file_id"] = res["id"]

# 7. Search, Listing, and Filtering Tests
def test_file_listing_and_filtering():
    # List all files for User A
    status, files, _ = request("GET", "/api/files", token=ctx["user_a_token"])
    assert status == 200
    assert any(f["id"] == ctx["user_a_file_id"] for f in files), "Uploaded file not in file list"
    
    # Filter by folder_id
    status, folder_files, _ = request("GET", f"/api/files?folder_id={ctx['user_a_folder_id']}", token=ctx["user_a_token"])
    assert status == 200
    assert any(f["id"] == ctx["user_a_file_id"] for f in folder_files), "File missing from folder filter"
    
    # Search by term 'audit_sample'
    status, search_match, _ = request("GET", "/api/files?q=audit_sample", token=ctx["user_a_token"])
    assert status == 200
    assert any(f["id"] == ctx["user_a_file_id"] for f in search_match), "Search match failed"
    
    # Search by non-matching query
    status, search_nomatch, _ = request("GET", "/api/files?q=non_existent_query_term_12345", token=ctx["user_a_token"])
    assert status == 200
    assert len(search_nomatch) == 0, "Non-matching query should return empty list"

# 8. Cross-User File Isolation Tests
def test_cross_user_file_listing_isolation():
    status, b_files, _ = request("GET", "/api/files", token=ctx["user_b_token"])
    assert status == 200
    assert not any(f["id"] == ctx["user_a_file_id"] for f in b_files), "User B must NOT see User A's file in listing"

def test_cross_user_file_metadata_isolation():
    status, res, _ = request("GET", f"/api/files/{ctx['user_a_file_id']}/metadata", token=ctx["user_b_token"])
    assert status in (404, 403), f"Expected 404 Not Found for User B accessing User A's file metadata, got {status} ({res})"

def test_cross_user_file_download_isolation():
    status, res, _ = request("GET", f"/api/files/{ctx['user_a_file_id']}/download", token=ctx["user_b_token"])
    assert status in (404, 403), f"Expected 404 Not Found for User B downloading User A's file, got {status} ({res})"

def test_cross_user_file_delete_isolation():
    status, res, _ = request("DELETE", f"/api/files/{ctx['user_a_file_id']}", token=ctx["user_b_token"])
    assert status in (404, 403), f"Expected 404 Not Found for User B deleting User A's file, got {status} ({res})"

# 9. Admin Privileges & Auditing Tests
def test_admin_metadata_access_and_audit():
    status, res, _ = request("GET", f"/api/files/{ctx['user_a_file_id']}/metadata", token=ctx["admin_token"])
    assert status == 200, f"Expected 200 for admin metadata inspection, got {status} ({res})"
    assert res.get("metadata", {}).get("id") == ctx["user_a_file_id"]
    
    # Verify MongoDB activity audit log
    event_check = run_mongosh(f"db.getSiblingDB('trustshare').activity.findOne({{event: 'admin_file_access', 'details.file_id': {ctx['user_a_file_id']}, 'details.action': 'metadata'}})")
    assert event_check is not None and "admin_file_access" in event_check, "admin_file_access event missing from MongoDB activity collection"

def test_admin_download_access_and_audit():
    status, content, _ = request("GET", f"/api/files/{ctx['user_a_file_id']}/download", token=ctx["admin_token"])
    assert status == 200, f"Expected 200 for admin download, got {status}"
    assert content == ctx["user_a_file_content"], "Downloaded content mismatch"
    
    # Verify MongoDB activity audit log
    event_check = run_mongosh(f"db.getSiblingDB('trustshare').activity.findOne({{event: 'admin_file_access', 'details.file_id': {ctx['user_a_file_id']}, 'details.action': 'download'}})")
    assert event_check is not None and "admin_file_access" in event_check, "admin_file_access download event missing from MongoDB"

def test_admin_delete_prohibition():
    # Enforces owner-only deletion policy
    status, res, _ = request("DELETE", f"/api/files/{ctx['user_a_file_id']}", token=ctx["admin_token"])
    assert status == 403, f"Expected 403 Forbidden: Admin should not be permitted to delete another user's file. Got: {status} ({res})"

# 10. Download Integrity Verification
def test_download_integrity():
    status, content, headers = request("GET", f"/api/files/{ctx['user_a_file_id']}/download", token=ctx["user_a_token"])
    assert status == 200, f"Expected 200, got {status}"
    assert content == ctx["user_a_file_content"], "Downloaded bytes do not match uploaded bytes"
    dl_hash = hashlib.sha256(content).hexdigest()
    assert dl_hash == ctx["user_a_file_hash"], f"Integrity hash mismatch: {dl_hash} vs {ctx['user_a_file_hash']}"

# 11. Metadata Sync & Reconciliation Tests
def test_metadata_sync_status():
    status, res, _ = request("GET", f"/api/files/{ctx['user_a_file_id']}/metadata", token=ctx["user_a_token"])
    assert status == 200, f"Expected 200, got {status} ({res})"
    assert res.get("source") == "mongodb", f"Expected metadata source to be mongodb, got {res.get('source')}"
    assert res.get("synced") is True, f"Expected synced True, got {res.get('synced')}"

def test_metadata_reconciliation():
    status, res, _ = request("POST", "/api/admin/reconcile-metadata", token=ctx["admin_token"])
    assert status == 200, f"Expected 200 for reconcile-metadata, got {status} ({res})"
    assert "scanned" in res, "Reconcile response missing 'scanned' count"

# 12. File Deletion and Cascading Cleanup Tests
def test_file_deletion_and_cleanup():
    # 1. Fetch storage_key before deletion
    stored_name = run_psql(f"SELECT storage_key FROM files WHERE id={ctx['user_a_file_id']};")
    assert stored_name is not None and len(stored_name) > 0, "Failed to get storage_key from PostgreSQL"
    ctx["user_a_file_stored_name"] = stored_name
    
    # 2. Delete the file as User A
    status, res, _ = request("DELETE", f"/api/files/{ctx['user_a_file_id']}", token=ctx["user_a_token"])
    assert status == 200, f"Expected 200 on delete, got {status} ({res})"
    
    # 3. Verify PostgreSQL record is gone
    sql_check = run_psql(f"SELECT COUNT(*) FROM files WHERE id={ctx['user_a_file_id']};")
    assert sql_check == "0", f"File record still present in PostgreSQL: count={sql_check}"
    
    # 4. Verify MongoDB record is gone
    mongo_check = run_mongosh(f"db.getSiblingDB('trustshare').files.countDocuments({{id: {ctx['user_a_file_id']}}})")
    assert mongo_check == "0", f"File record still present in MongoDB: count={mongo_check}"
    
    # 5. Verify physical file is gone from ./storage
    storage_path = os.path.join(os.path.dirname(__file__), "..", "..", "storage", ctx["user_a_file_stored_name"])
    assert not os.path.exists(storage_path), f"Physical file was not unlinked from storage: {storage_path}"
    
    # 6. Verify subsequent GET returns 404
    status_dl, _, _ = request("GET", f"/api/files/{ctx['user_a_file_id']}/download", token=ctx["user_a_token"])
    assert status_dl == 404, f"Expected 404 on download after deletion, got {status_dl}"
    
    status_meta, _, _ = request("GET", f"/api/files/{ctx['user_a_file_id']}/metadata", token=ctx["user_a_token"])
    assert status_meta == 404, f"Expected 404 on metadata after deletion, got {status_meta}"

# 13. Test Cleanup
def cleanup_test_data():
    print("\n--- [CLEANUP] Cleaning up isolated test users and folders ---")
    if ctx["admin_id"]:
        run_psql(f"DELETE FROM users WHERE id={ctx['admin_id']};")
    if ctx["user_a_folder_id"]:
        run_psql(f"DELETE FROM folders WHERE id={ctx['user_a_folder_id']};")
    if ctx["user_a_id"]:
        run_psql(f"DELETE FROM users WHERE id={ctx['user_a_id']};")
    if ctx["user_b_id"]:
        run_psql(f"DELETE FROM users WHERE id={ctx['user_b_id']};")
    print("--> Test records cleaned up from PostgreSQL.")

def main():
    print("=" * 60)
    print(" TrustShare Milestone 1 Engineering Audit Test Suite")
    print("=" * 60)
    
    tests = [
        ("TC-01", "Health Liveness Check (/health)", test_health),
        ("TC-02", "Health Readiness Check (/health/ready)", test_health_ready),
        ("TC-03", "Valid User Registration", test_registration_valid),
        ("TC-04", "Duplicate Email Registration Rejection (409)", test_registration_duplicate),
        ("TC-05", "Invalid Email Format Rejection (422)", test_registration_invalid_email),
        ("TC-06", "Short Password Rejection (422)", test_registration_short_password),
        ("TC-07", "Password Bcrypt Hashing in PostgreSQL", test_db_password_hashing),
        ("TC-08", "Valid User Login & Token Generation", test_login_valid),
        ("TC-09", "Wrong Password Rejection (401)", test_login_wrong_password),
        ("TC-10", "Non-Existent User Login Rejection (401)", test_login_nonexistent_email),
        ("TC-11", "Authenticated Me Endpoint (/api/auth/me)", test_auth_me_valid),
        ("TC-12", "Missing Token Rejection (401)", test_auth_me_missing_token),
        ("TC-13", "Invalid/Tampered Token Rejection (401)", test_auth_me_invalid_token),
        ("TC-14", "Logout & Redis Session Revocation", test_logout_session_revocation),
        ("TC-15", "Rate Limiting Enforcement (5 logins/min limit, 429 on 6th)", test_login_rate_limiting),
        ("TC-16", "RBAC: Regular User Forbidden from /api/admin/users (403)", test_admin_users_forbidden_for_regular_user),
        ("TC-17", "RBAC: Admin Role Access to /api/admin/users (200)", test_admin_users_allowed_for_admin),
        ("TC-18", "Folder Creation Valid", test_folder_creation_valid),
        ("TC-19", "Folder Creation Empty Name Rejection (422)", test_folder_creation_empty_name),
        ("TC-20", "Folder Listing and Cross-User Isolation", test_folder_listing_and_isolation),
        ("TC-21", "Upload Rejection: Disallowed Extension .exe (415)", test_upload_unsupported_extension),
        ("TC-22", "Upload Rejection: Empty File 0 Bytes (400)", test_upload_empty_file),
        ("TC-23", "Upload Rejection: Oversized File > 10 MiB (413)", test_upload_oversized_file),
        ("TC-24", "Upload Rejection: Spoofed Extension / Invalid Magic Bytes (400)", test_upload_spoofed_pdf_magic_bytes),
        ("TC-25", "Upload Rejection: Cross-User Folder Injection (404)", test_upload_cross_user_folder_injection),
        ("TC-26", "Upload Valid File with SHA-256 Digest Computation", test_upload_valid_file_with_sha256),
        ("TC-27", "File Listing, Folder Filtering, and Query Search", test_file_listing_and_filtering),
        ("TC-28", "Cross-User Isolation: File Listing", test_cross_user_file_listing_isolation),
        ("TC-29", "Cross-User Isolation: File Metadata Inspection (403)", test_cross_user_file_metadata_isolation),
        ("TC-30", "Cross-User Isolation: File Download (403)", test_cross_user_file_download_isolation),
        ("TC-31", "Cross-User Isolation: File Deletion (403)", test_cross_user_file_delete_isolation),
        ("TC-32", "Admin Privileges: Metadata Inspection & Audit Logging", test_admin_metadata_access_and_audit),
        ("TC-33", "Admin Privileges: Download Access & Audit Logging", test_admin_download_access_and_audit),
        ("TC-34", "Policy Enforcement: Admin Prohibited from Deleting User File (403)", test_admin_delete_prohibition),
        ("TC-35", "Download Content Integrity & SHA-256 Verification", test_download_integrity),
        ("TC-36", "Metadata Store Status Check (MongoDB Source)", test_metadata_sync_status),
        ("TC-37", "Admin Metadata Reconciliation Endpoint", test_metadata_reconciliation),
        ("TC-38", "Cascading File Deletion (SQL, MongoDB, Local Disk)", test_file_deletion_and_cleanup),
    ]

    for test_id, name, fn in tests:
        run_test(test_id, name, fn)

    cleanup_test_data()

    print("\n" + "=" * 60)
    print(f" AUDIT SUITE EXECUTION SUMMARY: {len(passed_tests)} Passed, {len(failed_tests)} Failed out of {len(tests)} Tests")
    print("=" * 60)
    
    if failed_tests:
        print("\nFailed Tests:")
        for t_id, t_name, reason in failed_tests:
            print(f"- [{t_id}] {t_name}: {reason}")
        sys.exit(1)
    else:
        print(f"\nAll {len(tests)} test cases PASSED successfully with verified evidence!")
        sys.exit(0)

if __name__ == "__main__":
    main()
