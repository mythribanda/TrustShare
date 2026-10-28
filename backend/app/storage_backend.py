import os
from pathlib import Path
from functools import lru_cache

def provider():
    value=os.getenv("STORAGE_PROVIDER","local").strip().lower()
    if value not in {"local","s3"}:
        raise RuntimeError("STORAGE_PROVIDER must be 'local' or 's3'")
    return value

@lru_cache(maxsize=1)
def _s3_client():
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL") or None,
        region_name=os.getenv("S3_REGION","us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID") or None,
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY") or None,
    )

def put_bytes(name:str,data:bytes,local_root:Path):
    if provider()=="local":
        path=local_root/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data)
        return
    bucket=os.getenv("S3_BUCKET","").strip()
    if not bucket: raise RuntimeError("S3_BUCKET must be set when STORAGE_PROVIDER=s3")
    _s3_client().put_object(Bucket=bucket,Key=name,Body=data)

def get_bytes(name:str,local_root:Path)->bytes:
    if provider()=="local":
        return (local_root/name).read_bytes()
    bucket=os.getenv("S3_BUCKET","").strip()
    if not bucket: raise RuntimeError("S3_BUCKET must be set when STORAGE_PROVIDER=s3")
    result=_s3_client().get_object(Bucket=bucket,Key=name)
    return result["Body"].read()

def object_exists(name:str,local_root:Path)->bool:
    if provider()=="local":
        return (local_root/name).is_file()
    bucket=os.getenv("S3_BUCKET","").strip()
    if not bucket: return False
    try:
        _s3_client().head_object(Bucket=bucket,Key=name)
        return True
    except Exception as exc:
        response=getattr(exc,"response",{})
        code=str(response.get("Error",{}).get("Code",""))
        if code in {"404","NoSuchKey","NotFound"}: return False
        raise

def delete_object(name:str,local_root:Path):
    if provider()=="local":
        path=local_root/name
        if path.exists(): path.unlink()
        return
    bucket=os.getenv("S3_BUCKET","").strip()
    if not bucket: raise RuntimeError("S3_BUCKET must be set when STORAGE_PROVIDER=s3")
    _s3_client().delete_object(Bucket=bucket,Key=name)

def health(local_root:Path):
    if provider()=="local":
        return {"provider":"local","available":local_root.exists() and os.access(local_root,os.W_OK)}
    bucket=os.getenv("S3_BUCKET","").strip()
    if not bucket: return {"provider":"s3","available":False,"detail":"S3_BUCKET is not configured"}
    try:
        _s3_client().head_bucket(Bucket=bucket)
        return {"provider":"s3","available":True,"bucket_configured":True}
    except Exception:
        return {"provider":"s3","available":False,"bucket_configured":True}
