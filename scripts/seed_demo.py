"""Seed script for TrustShare demo.

Creates:
- Demo user: demo.user@example.com / DemoUserPass2026!#
- 3 folders: Projects, Reports, Personal
- 6 sample files (PDF, TXT, CSV, PNG)
- 2 active share links (1-hour expiry, password-protected)
- 1 revoked share link
- Suspicious activity events (brute force + revoked link probe) to populate admin alerts
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
import requests

BASE_URL = "http://localhost:8000/api"

DEMO_USER_EMAIL = "demo.user@example.com"
DEMO_USER_PASSWORD = "DemoUserPass2026!#"
DEMO_USER_NAME = "Demo User"

# Sample file contents
VALID_PDF = b"%PDF-1.4\n1 0 obj\n<< /Title (TrustShare Secure Architecture) >>\nendobj\n2 0 obj\n<< /Type /Catalog /Pages 3 0 R >>\nendobj\n3 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\ntrailer\n<< /Root 2 0 R >>\n%%EOF\n"

CHECKLIST_PDF = b"%PDF-1.4\n1 0 obj\n<< /Title (Security Audit Checklist) >>\nendobj\n2 0 obj\n<< /Type /Catalog /Pages 3 0 R >>\nendobj\ntrailer\n<< /Root 2 0 R >>\n%%EOF\n"

CSV_CONTENT = (
    "Quarter,Revenue_USD,Operating_Costs,R_and_D,Net_Margin\n"
    "Q1-2026,1250000,720000,280000,250000\n"
    "Q2-2026,1480000,810000,310000,360000\n"
    "Q3-2026,1720000,890000,350000,480000\n"
    "Q4-2026,2100000,980000,410000,710000\n"
).encode("utf-8")

ROADMAP_TXT = (
    "TrustShare Engineering Roadmap 2026\n"
    "====================================\n"
    "[x] Milestone 1: Authentication, RBAC, TOTP MFA, Secure Upload, Workspace UI\n"
    "[x] Milestone 2: AES-256-GCM Envelope Encryption, S3 Storage, Secure Links, Key Rotation\n"
    "[x] Milestone 3: Real-Time SSE Notifications, Tamper-Evident Audit Logs, Detection Rules\n"
    "[x] Milestone 4: Security Verification (SAST/SCA), AWS EC2 Deployment, Guides & Documentation\n"
).encode("utf-8")

CONTACTS_TXT = (
    "Personal Emergency Reference & Operational Notes\n"
    "------------------------------------------------\n"
    "Primary Contact: demo.user@example.com\n"
    "Security Officer Hotline: +1 (555) 019-2834\n"
    "Backup KMS Region: ap-south-1\n"
    "Storage Bucket: trustshare-files (S3 / RustFS)\n"
).encode("utf-8")

# Minimal 1x1 valid PNG image
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00"
    b"\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def seed():
    print("=== TrustShare Demo Seeding ===")

    # 1. Login or register demo user
    print(f"\n1. Authenticating demo user: {DEMO_USER_EMAIL}")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": DEMO_USER_EMAIL,
        "password": DEMO_USER_PASSWORD
    })

    if login_resp.status_code == 200:
        print("  Demo user already exists, logged in successfully.")
        token = login_resp.json()["access_token"]
    else:
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={
            "full_name": DEMO_USER_NAME,
            "email": DEMO_USER_EMAIL,
            "password": DEMO_USER_PASSWORD
        })
        if reg_resp.status_code in [200, 201]:
            print("  Registered demo user successfully.")
        else:
            print(f"  Registration response: {reg_resp.status_code} {reg_resp.text}")
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": DEMO_USER_EMAIL,
            "password": DEMO_USER_PASSWORD
        })
        token = login_resp.json()["access_token"]
        print("  Logged in as demo user.")

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create 3 Folders: Projects, Reports, Personal
    print("\n2. Creating folders: Projects, Reports, Personal")
    folders = {}
    existing_folders = requests.get(f"{BASE_URL}/folders", headers=headers).json().get("items", [])
    folder_map = {f["name"]: f["id"] for f in existing_folders}

    for name in ["Projects", "Reports", "Personal"]:
        if name in folder_map:
            folders[name] = folder_map[name]
            print(f"  Folder '{name}' already exists (ID: {folders[name]})")
        else:
            f_resp = requests.post(f"{BASE_URL}/folders", headers=headers, json={"name": name})
            if f_resp.status_code == 201:
                folders[name] = f_resp.json()["id"]
                print(f"  Created folder '{name}' (ID: {folders[name]})")
            else:
                print(f"  Error creating folder {name}: {f_resp.status_code} {f_resp.text}")

    # 3. Upload 6 sample files
    print("\n3. Uploading 6 sample files into folders")
    files_to_upload = [
        ("TrustShare_Architecture.pdf", VALID_PDF, "application/pdf", folders.get("Projects")),
        ("Project_Roadmap_2026.txt", ROADMAP_TXT, "text/plain", folders.get("Projects")),
        ("System_Architecture_Diagram.png", PNG_BYTES, "image/png", folders.get("Projects")),
        ("Quarterly_Financial_Summary.csv", CSV_CONTENT, "text/csv", folders.get("Reports")),
        ("Security_Audit_Checklist.pdf", CHECKLIST_PDF, "application/pdf", folders.get("Reports")),
        ("Emergency_Contacts.txt", CONTACTS_TXT, "text/plain", folders.get("Personal")),
    ]

    uploaded_files = {}
    for filename, content, mime_type, folder_id in files_to_upload:
        params = {"allow_duplicate": "true"}
        if folder_id:
            params["folder_id"] = folder_id

        up_resp = requests.post(
            f"{BASE_URL}/files",
            headers=headers,
            params=params,
            files={"file": (filename, content, mime_type)}
        )
        if up_resp.status_code in [200, 201]:
            f_info = up_resp.json()
            uploaded_files[filename] = f_info["id"]
            print(f"  Uploaded: {filename} -> {f_info['id']} ({f_info['size_bytes']} bytes)")
        else:
            print(f"  Failed to upload {filename}: {up_resp.status_code} {up_resp.text}")

    # 4. Create 2 share links
    print("\n4. Creating active share links")
    # Link 1: 1-hour expiry, view only on TrustShare_Architecture.pdf
    arch_file_id = uploaded_files.get("TrustShare_Architecture.pdf")
    link1_url = None
    if arch_file_id:
        exp_1h = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        sh1_resp = requests.post(
            f"{BASE_URL}/files/{arch_file_id}/shares",
            headers=headers,
            json={"share_type": "link", "permission": "view", "expires_at": exp_1h}
        )
        if sh1_resp.status_code == 201:
            link1_info = sh1_resp.json()
            link1_url = link1_info.get("url")
            print(f"  Share Link 1 (1-hour expiry, View only): {link1_url}")
        else:
            print(f"  Share Link 1 creation error: {sh1_resp.status_code} {sh1_resp.text}")

    # Link 2: with password on Quarterly_Financial_Summary.csv, download permission
    csv_file_id = uploaded_files.get("Quarterly_Financial_Summary.csv")
    link2_url = None
    link2_pw = "ShareSecret2026!"
    if csv_file_id:
        exp_7d = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        sh2_resp = requests.post(
            f"{BASE_URL}/files/{csv_file_id}/shares",
            headers=headers,
            json={
                "share_type": "link",
                "permission": "download",
                "expires_at": exp_7d,
                "password": link2_pw,
                "max_downloads": 25
            }
        )
        if sh2_resp.status_code == 201:
            link2_info = sh2_resp.json()
            link2_url = link2_info.get("url")
            print(f"  Share Link 2 (Password Protected: '{link2_pw}', Download allowed): {link2_url}")
        else:
            print(f"  Share Link 2 creation error: {sh2_resp.status_code} {sh2_resp.text}")

    # 5. Create and revoke 1 share link
    print("\n5. Creating and revoking share link")
    chk_file_id = uploaded_files.get("Security_Audit_Checklist.pdf")
    revoked_token = None
    if chk_file_id:
        exp_3d = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        sh3_resp = requests.post(
            f"{BASE_URL}/files/{chk_file_id}/shares",
            headers=headers,
            json={"share_type": "link", "permission": "view", "expires_at": exp_3d}
        )
        if sh3_resp.status_code == 201:
            sh3_data = sh3_resp.json()
            sh3_id = sh3_data["id"]
            sh3_url = sh3_data.get("url", "")
            revoked_token = sh3_url.rstrip("/").split("/")[-1]
            
            # Revoke it
            del_resp = requests.delete(f"{BASE_URL}/shares/{sh3_id}", headers=headers)
            print(f"  Share Link 3 created and REVOKED: {sh3_url} (HTTP {del_resp.status_code})")
        else:
            print(f"  Share Link 3 error: {sh3_resp.status_code} {sh3_resp.text}")

    # 6. Trigger suspicious-activity events for Admin Security Alerts
    print("\n6. Triggering suspicious activity events to populate Admin Security Alerts")
    # Rule 1: Brute-force failed logins (6 consecutive attempts)
    target_victim = "intruder.target@example.com"
    print(f"  Simulating brute-force attack on {target_victim}...")
    for i in range(6):
        requests.post(f"{BASE_URL}/auth/login", json={"email": target_victim, "password": "WrongPasswordAttempt!"})
    print("  Triggered 'repeated_failed_logins' alert (6 failed attempts).")

    # Rule 2: Probing revoked link
    if revoked_token:
        print(f"  Probing revoked share link token: {revoked_token}...")
        for i in range(3):
            requests.get(f"{BASE_URL}/s/{revoked_token}")
        print("  Triggered 'repeated_access_to_revoked_link' alert.")

    print("\n=== Demo Seeding Complete! ===")
    print(f"User:        {DEMO_USER_EMAIL}")
    print(f"Password:    {DEMO_USER_PASSWORD}")
    print(f"Folders:     Projects, Reports, Personal")
    print(f"Share 1:     {link1_url} (Expires in 1h, View only)")
    print(f"Share 2:     {link2_url} (Password: {link2_pw}, Download allowed)")
    print(f"Revoked:     /s/{revoked_token} (Returns 410 Gone)")


if __name__ == "__main__":
    seed()
