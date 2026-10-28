"""Re-wrap per-file data keys with the active master-key version.

Configure MASTER_KEYS with both old and new versions, set ACTIVE_MASTER_KEY_VERSION
to the new version, back up the database, then run:
    python -m app.rotate_keys --dry-run
    python -m app.rotate_keys --apply
"""
import argparse
from sqlalchemy import select
from app.main import FileKey, SessionLocal, StoredFile
from app.security_crypto import rewrap_key

def rotate(apply: bool = False) -> tuple[int, int, int]:
    changed = unchanged = failed = 0
    with SessionLocal() as db:
        keys = db.scalars(select(FileKey).order_by(FileKey.id)).all()
        for row in keys:
            record = db.get(StoredFile, row.file_id)
            if not record:
                failed += 1
                print(f"FAILED key_id={row.id}: associated file record is missing")
                continue
            try:
                wrapped, nonce, version = rewrap_key(row.wrapped_key, row.wrap_nonce, row.key_version, record.stored_name)
                if version == row.key_version:
                    unchanged += 1
                    continue
                if apply:
                    row.wrapped_key = wrapped
                    row.wrap_nonce = nonce
                    row.key_version = version
                    db.commit()
                changed += 1
                print(f"{'ROTATED' if apply else 'WOULD ROTATE'} file_id={row.file_id} from={row.key_version if not apply else 'previous'} to={version}")
            except Exception as exc:
                db.rollback()
                failed += 1
                print(f"FAILED file_id={row.file_id} reason={type(exc).__name__}: {exc}")
    return changed, unchanged, failed

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="persist changes; default is a dry run")
    args = parser.parse_args()
    if args.apply and input("Confirm database backup by typing ROTATE: ") != "ROTATE":
        raise SystemExit("Key rotation cancelled")
    changed, unchanged, failed = rotate(args.apply)
    print(f"{'APPLIED' if args.apply else 'DRY RUN'}: rotated_or_eligible={changed} unchanged={unchanged} failed={failed}")
    if failed:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
