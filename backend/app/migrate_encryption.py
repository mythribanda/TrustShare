"""Migrate legacy plaintext TrustShare uploads to envelope-encrypted storage.

Run from backend/ with the configured environment:
    python -m app.migrate_encryption          # dry run
    python -m app.migrate_encryption --apply  # perform migration

Back up the database, storage volume, and master key before applying.
"""
import argparse
from sqlalchemy import select
from app.main import FileKey, SessionLocal, STORAGE, StoredFile
from app.security_crypto import MAGIC, encrypt_bytes
from app.storage_backend import get_bytes, put_bytes

def migrate(apply: bool = False) -> tuple[int, int, int]:
    migrated = skipped = failed = 0
    with SessionLocal() as db:
        records = db.scalars(select(StoredFile).order_by(StoredFile.id)).all()
        for record in records:
            key_row = db.scalar(select(FileKey).where(FileKey.file_id == record.id))
            if key_row:
                skipped += 1
                continue
            try:
                raw = get_bytes(record.stored_name, STORAGE)
                if raw.startswith(MAGIC):
                    raise RuntimeError("Object already has encrypted format but its FileKey record is missing")
                if not apply:
                    print(f"WOULD MIGRATE file_id={record.id} name={record.original_name!r} size={record.size}")
                    migrated += 1
                    continue
                encrypted, wrapped_key, wrap_nonce, version = encrypt_bytes(raw, record.stored_name)
                put_bytes(record.stored_name, encrypted, STORAGE)
                db.add(FileKey(file_id=record.id, wrapped_key=wrapped_key, wrap_nonce=wrap_nonce, key_version=version))
                try:
                    db.commit()
                except Exception:
                    db.rollback()
                    put_bytes(record.stored_name, raw, STORAGE)
                    raise
                print(f"MIGRATED file_id={record.id} size={record.size}")
                migrated += 1
            except Exception as exc:
                db.rollback()
                failed += 1
                print(f"FAILED file_id={record.id} reason={type(exc).__name__}: {exc}")
    return migrated, skipped, failed

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="perform migration; without this flag only report eligible files")
    args = parser.parse_args()
    if args.apply:
        confirm = input("Confirm you backed up the database, storage and master key by typing ENCRYPT: ")
        if confirm != "ENCRYPT":
            raise SystemExit("Migration cancelled")
    migrated, skipped, failed = migrate(args.apply)
    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"{mode}: migrated_or_eligible={migrated} already_encrypted={skipped} failed={failed}")
    if failed:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
