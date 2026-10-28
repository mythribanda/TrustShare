import os, uuid, shutil, hashlib, logging, secrets, csv, io, zipfile, json, hmac, base64
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt
import redis
from app.security_crypto import encrypt_bytes, decrypt_bytes, encrypt_secret, decrypt_secret
from app.storage_backend import put_bytes, get_bytes, object_exists, delete_object, health as storage_health
from jose import jwt, JWTError
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from pymongo import MongoClient
from sqlalchemy import create_engine, String, Integer, DateTime, ForeignKey, Text, Boolean, func, select, update, delete, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

logger = logging.getLogger("trustshare")

try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env')
except Exception:
    pass

DATABASE_URL=os.getenv('DATABASE_URL','postgresql+psycopg://trustshare:change-this-local-password@localhost:5432/trustshare')
MONGO_URL=os.getenv('MONGO_URL','mongodb://localhost:27017')
MONGO_DB=os.getenv('MONGO_DB','trustshare')
REDIS_URL=os.getenv('REDIS_URL','redis://localhost:6379/0')
JWT_SECRET=os.getenv('JWT_SECRET','local-only-change-me')
JWT_ALGORITHM='HS256'
JWT_EXPIRE_MINUTES=int(os.getenv('JWT_EXPIRE_MINUTES','60'))
MAX_UPLOAD_BYTES=int(os.getenv('MAX_UPLOAD_MB','10'))*1024*1024
_proj_storage = Path(__file__).resolve().parent.parent.parent / 'storage'
STORAGE = Path('/app/storage') if Path('/app').exists() else (_proj_storage if _proj_storage.parent.exists() else Path('storage'))
STORAGE.mkdir(parents=True, exist_ok=True)
ALLOWED={'.pdf','.docx','.xlsx','.pptx','.csv','.txt','.png','.jpg','.jpeg','.webp'}

def init_database(url: str):
    target_url = url
    if target_url.startswith('postgresql+psycopg://'):
        try:
            import psycopg
        except ImportError:
            target_url = target_url.replace('postgresql+psycopg://', 'postgresql+psycopg2://', 1)
    try:
        eng = create_engine(target_url, pool_pre_ping=True)
        with eng.connect():
            pass
        return eng, 'postgres'
    except Exception as exc:
        print(f"[TrustShare] PostgreSQL ({target_url}) not reachable: {exc}")
        sqlite_file = (STORAGE / 'trustshare.db').resolve()
        print(f"[TrustShare] Using SQLite fallback at: {sqlite_file}")
        eng = create_engine(f"sqlite:///{sqlite_file}", connect_args={"check_same_thread": False})
        return eng, 'sqlite'

engine, db_backend = init_database(DATABASE_URL)
SessionLocal=sessionmaker(bind=engine,autoflush=False,autocommit=False)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__='users'
    id: Mapped[int]=mapped_column(Integer,primary_key=True,index=True)
    name: Mapped[str]=mapped_column(String(120))
    email: Mapped[str]=mapped_column(String(255),unique=True,index=True)
    password_hash: Mapped[str]=mapped_column(String(255))
    role: Mapped[str]=mapped_column(String(20),default='user')
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Folder(Base):
    __tablename__='folders'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    name: Mapped[str]=mapped_column(String(120))
    owner_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class StoredFile(Base):
    __tablename__='files'
    id: Mapped[int]=mapped_column(Integer,primary_key=True,index=True)
    original_name: Mapped[str]=mapped_column(String(255))
    stored_name: Mapped[str]=mapped_column(String(255),unique=True)
    content_type: Mapped[str]=mapped_column(String(150),default='application/octet-stream')
    size: Mapped[int]=mapped_column(Integer)
    sha256: Mapped[str]=mapped_column(String(64))
    owner_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    folder_id: Mapped[Optional[int]]=mapped_column(ForeignKey('folders.id'),nullable=True)
    uploaded_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class FileShare(Base):
    __tablename__='file_shares'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    file_id: Mapped[int]=mapped_column(ForeignKey('files.id'),index=True)
    owner_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    token_hash: Mapped[str]=mapped_column(String(64),unique=True,index=True)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool]=mapped_column(Boolean,default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class SharePolicy(Base):
    __tablename__='share_policies'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    share_id: Mapped[int]=mapped_column(ForeignKey('file_shares.id'),unique=True,index=True)
    max_downloads: Mapped[Optional[int]]=mapped_column(Integer,nullable=True)
    download_count: Mapped[int]=mapped_column(Integer,default=0)
    permission: Mapped[str]=mapped_column(String(20),default='download')

class FileGrant(Base):
    __tablename__='file_grants'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    file_id: Mapped[int]=mapped_column(ForeignKey('files.id'),index=True)
    owner_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    recipient_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    permission: Mapped[str]=mapped_column(String(20),default='view_download')
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class Vault(Base):
    __tablename__='vaults'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),unique=True,index=True)
    salt: Mapped[str]=mapped_column(String(64))
    verifier: Mapped[str]=mapped_column(String(64))
    failed_attempts: Mapped[int]=mapped_column(Integer,default=0)
    locked_until: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class VaultFile(Base):
    __tablename__='vault_files'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    stored_name: Mapped[str]=mapped_column(String(255),unique=True)
    sealed_name: Mapped[str]=mapped_column(Text)
    nonce: Mapped[str]=mapped_column(String(32))
    content_type: Mapped[str]=mapped_column(String(150))
    size: Mapped[int]=mapped_column(Integer)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class UserMfa(Base):
    __tablename__='user_mfa'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),unique=True,index=True)
    encrypted_secret: Mapped[str]=mapped_column(Text)
    nonce: Mapped[str]=mapped_column(String(64))
    key_version: Mapped[int]=mapped_column(Integer,default=1)
    enabled: Mapped[bool]=mapped_column(Boolean,default=False)
    backup_hashes: Mapped[str]=mapped_column(Text,default='[]')
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class AuthSession(Base):
    __tablename__='auth_sessions'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    token_hash: Mapped[str]=mapped_column(String(64),unique=True,index=True)
    ip_address: Mapped[str]=mapped_column(String(100),default='unknown')
    user_agent: Mapped[str]=mapped_column(String(500),default='unknown')
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    last_active_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    revoked: Mapped[bool]=mapped_column(Boolean,default=False)

class FileKey(Base):
    __tablename__='file_keys'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    file_id: Mapped[int]=mapped_column(ForeignKey('files.id'),unique=True,index=True)
    wrapped_key: Mapped[str]=mapped_column(Text)
    wrap_nonce: Mapped[str]=mapped_column(String(64))
    key_version: Mapped[int]=mapped_column(Integer,default=1)
    algorithm: Mapped[str]=mapped_column(String(30),default='AES-256-GCM')
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

Base.metadata.create_all(bind=engine)

def migrate_legacy_file_schema():
    """Add columns missing from older SQLite databases without deleting user data."""
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    if "files" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("files")}
    if "stored_name" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE files ADD COLUMN stored_name VARCHAR(255)"))
            # Preserve existing rows. Legacy object names may need manual reconciliation
            # if the older version stored files under a different naming convention.
            connection.execute(text(
                "UPDATE files SET stored_name = 'legacy-' || id || '-' || original_name "
                "WHERE stored_name IS NULL OR stored_name = ''"
            ))
            connection.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_files_stored_name_migration "
                "ON files (stored_name)"
            ))

migrate_legacy_file_schema()
def init_redis(url: str):
    for u in list(dict.fromkeys([url, url.replace('://redis:', '://localhost:'), 'redis://localhost:6379/0'])):
        try:
            r = redis.Redis.from_url(u, decode_responses=True, socket_connect_timeout=1)
            r.ping()
            return r
        except Exception:
            pass
    return None

def init_mongo(url: str):
    for u in list(dict.fromkeys([url, url.replace('://mongo:', '://localhost:'), 'mongodb://localhost:27017'])):
        try:
            client = MongoClient(u, serverSelectionTimeoutMS=500)
            client.admin.command('ping')
            return client, True
        except Exception:
            pass
    return MongoClient(url, serverSelectionTimeoutMS=500), False

mongo_client, mongo_available = init_mongo(MONGO_URL)
mdb = mongo_client[MONGO_DB] if mongo_available else None
cache = init_redis(REDIS_URL)

app=FastAPI(title='TrustShare API',version='1.0.0',description='TrustShare Milestone 1 file management API')
@app.middleware('http')
async def security_observability(request:Request,call_next):
    request_id=request.headers.get('x-request-id') or uuid.uuid4().hex
    response=await call_next(request)
    response.headers['X-Request-ID']=request_id
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    if response.status_code in (401,403,429):
        path=request.url.path
        if path.startswith('/share/'): path='/share/[REDACTED]'
        log_event('request_blocked',None,{'path':path,'method':request.method,'status':response.status_code,'ip':request.client.host if request.client else None,'user_agent':request.headers.get('user-agent','')[:300],'request_id':request_id})
    return response

frontend_origin=os.getenv('FRONTEND_ORIGIN','http://localhost:5173')
origins = list({frontend_origin, 'http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost:3000'})
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
bearer=HTTPBearer(auto_error=False)
class RegisterIn(BaseModel):
    name: str=Field(min_length=2,max_length=120)
    email: EmailStr
    password: str=Field(min_length=8,max_length=128)
class LoginIn(BaseModel): email: EmailStr; password: str; otp: Optional[str]=None
class FolderIn(BaseModel): name: str=Field(min_length=1,max_length=120)

def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()

def check_rate_limit(key: str, limit: int, window: int = 60):
    if not cache:
        return
    try:
        count = cache.incr(key)
        if count == 1:
            cache.expire(key, window)
        if count > limit:
            ttl = cache.ttl(key)
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Too many requests. Please wait {max(ttl, 1)} seconds before trying again."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Redis rate limiting bypassed due to error: {e}")

def log_event(event, user_id=None, details=None):
    if not mongo_available or mdb is None: return
    try:
        mdb.activity.insert_one({'event':event,'user_id':user_id,'details':details or {},'timestamp':datetime.now(timezone.utc)})
    except Exception as e:
        logger.warning(f"MongoDB log_event failed for '{event}': {e}")

def create_token(user):
    now=datetime.now(timezone.utc)
    return jwt.encode({'sub':str(user.id),'role':user.role,'iat':now,'exp':now+timedelta(minutes=JWT_EXPIRE_MINUTES)},JWT_SECRET,algorithm=JWT_ALGORITHM)

def record_session(user:User,token:str,request:Request,db:Session):
    full_hash=hashlib.sha256(token.encode()).hexdigest()
    existing=db.scalar(select(AuthSession).where(AuthSession.token_hash==full_hash))
    if existing:
        existing.revoked=False
        existing.last_active_at=datetime.now(timezone.utc)
        existing.ip_address=request.client.host if request.client else 'unknown'
        existing.user_agent=request.headers.get('user-agent','unknown')[:500]
    else:
        db.add(AuthSession(user_id=user.id,token_hash=full_hash,ip_address=request.client.host if request.client else 'unknown',user_agent=request.headers.get('user-agent','unknown')[:500]))
    db.commit()


def current_user(creds: HTTPAuthorizationCredentials=Depends(bearer),db:Session=Depends(get_db)):
    if not creds: raise HTTPException(401,'Authentication required')
    try: payload=jwt.decode(creds.credentials,JWT_SECRET,algorithms=[JWT_ALGORITHM]); uid=int(payload['sub'])
    except (JWTError,ValueError,KeyError): raise HTTPException(401,'Invalid or expired token')
    if cache:
        try:
            token_hash = hashlib.sha256(creds.credentials.encode()).hexdigest()[:16]
            session_key = f'session:{uid}:{token_hash}'
            if not cache.exists(session_key):
                raise HTTPException(401, 'Session has expired or was revoked')
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Redis session lookup failed: {e}")
    user=db.get(User,uid)
    if not user: raise HTTPException(401,'Account not found')
    session_hash=hashlib.sha256(creds.credentials.encode()).hexdigest()
    session_record=db.scalar(select(AuthSession).where(AuthSession.token_hash==session_hash))
    if session_record:
        if session_record.revoked: raise HTTPException(401,'Session has been revoked')
        now=datetime.now(timezone.utc)
        last=session_record.last_active_at
        if last.tzinfo is None: last=last.replace(tzinfo=timezone.utc)
        if (now-last).total_seconds()>60:
            session_record.last_active_at=now
            db.commit()
    return user

def require_roles(*roles):
    def check(user:User=Depends(current_user)):
        if user.role not in roles: raise HTTPException(403,'Insufficient permissions')
        return user
    return check

def user_dict(u): return {'id':u.id,'name':u.name,'email':u.email,'role':u.role,'created_at':u.created_at.isoformat() if u.created_at else None}
def file_dict(f): return {'id':f.id,'name':f.original_name,'content_type':f.content_type,'size':f.size,'sha256':f.sha256,'owner_id':f.owner_id,'folder_id':f.folder_id,'uploaded_at':f.uploaded_at.isoformat() if f.uploaded_at else None}
def validate_file_content(filename: str, content: bytes):
    suffix=Path(filename).suffix.lower()
    signatures={
        '.pdf':content.startswith(b'%PDF-'),
        '.png':content.startswith(bytes([137,80,78,71,13,10,26,10])),
        '.jpg':content.startswith(bytes([255,216,255])),
        '.jpeg':content.startswith(bytes([255,216,255])),
        '.webp':len(content)>=12 and content[:4]==b'RIFF' and content[8:12]==b'WEBP',
    }
    if suffix in signatures and not signatures[suffix]: raise HTTPException(415,'File content does not match its extension')
    if suffix in {'.docx','.xlsx','.pptx'}:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names=set(archive.namelist())
                needed={'.docx':'word/document.xml','.xlsx':'xl/workbook.xml','.pptx':'ppt/presentation.xml'}[suffix]
                if '[Content_Types].xml' not in names or needed not in names: raise HTTPException(415,'Office document structure is invalid')
                if len(names)>5000 or sum(max(0,item.file_size) for item in archive.infolist())>100*1024*1024: raise HTTPException(413,'Office document expands beyond safe inspection limits')
        except zipfile.BadZipFile: raise HTTPException(415,'Office document is not a valid Office container')
    if suffix in {'.txt','.csv'}:
        if 0 in content[:8192]: raise HTTPException(415,'Text file contains binary content')
        try: content.decode('utf-8-sig')
        except UnicodeDecodeError: raise HTTPException(415,'Text files must use UTF-8 encoding')

def audit_events_for(user:User, days:int=30, admin:bool=False):
    if not mongo_available or mdb is None: return []
    cutoff=datetime.now(timezone.utc)-timedelta(days=days)
    query={'timestamp':{'$gte':cutoff}}
    if not admin: query['user_id']=user.id
    try:
        rows=mdb.activity.find(query,{'_id':0}).sort('timestamp',-1).limit(5000)
        return [{k:(v.isoformat() if isinstance(v,datetime) else v) for k,v in row.items()} for row in rows]
    except Exception as exc:
        logger.warning(f'Activity query failed: {exc}')
        return []


@app.get('/health')
def health():
    return {
        'status':'ok',
        'database':db_backend,
        'postgres':'connected' if db_backend=='postgres' else 'fallback_sqlite',
        'mongodb':'connected' if mongo_available else 'unavailable',
        'redis':'connected' if cache else 'unavailable',
        'storage':storage_health(STORAGE)
    }

@app.post('/api/auth/register',status_code=201)
def register(data:RegisterIn,request:Request,db:Session=Depends(get_db)):
    email=data.email.lower().strip()
    if db.scalar(select(User).where(User.email==email)): raise HTTPException(409,'Email is already registered')
    user=User(name=data.name.strip(),email=email,password_hash=bcrypt.hashpw(data.password.encode(),bcrypt.gensalt()).decode(),role='user')
    db.add(user); db.commit(); db.refresh(user); log_event('register',user.id,{'email':email})
    token=create_token(user)
    record_session(user,token,request,db)
    if cache:
        try: cache.setex(f'session:{user.id}:{hashlib.sha256(token.encode()).hexdigest()[:16]}',JWT_EXPIRE_MINUTES*60,'active')
        except Exception as e: logger.warning(f"Redis session write failed on register: {e}")
    return {'user':user_dict(user),'access_token':token,'token_type':'bearer'}

@app.post('/api/auth/login')
def login(data:LoginIn,request:Request,db:Session=Depends(get_db)):
    client_ip = request.client.host if request.client else '127.0.0.1'
    check_rate_limit(f'ratelimit:login:{client_ip}', limit=5, window=60)
    user=db.scalar(select(User).where(User.email==data.email.lower().strip()))
    if not user or not bcrypt.checkpw(data.password.encode(),user.password_hash.encode()):
        log_event('login_failed',None,{'email':data.email.lower().strip()}); raise HTTPException(401,'Incorrect email or password')
    mfa=db.scalar(select(UserMfa).where(UserMfa.user_id==user.id))
    if mfa and mfa.enabled:
        valid=False
        try:
            secret=decrypt_secret(mfa.encrypted_secret,mfa.nonce,mfa.key_version,f'trustshare:mfa:{user.id}')
            import pyotp
            valid=bool(data.otp and pyotp.TOTP(secret).verify(data.otp.strip(),valid_window=1))
        except Exception as exc:
            logger.warning(f'MFA verification error: {type(exc).__name__}')
        if not valid and data.otp:
            hashes=json.loads(mfa.backup_hashes or '[]')
            supplied=hashlib.sha256(data.otp.strip().upper().encode()).hexdigest()
            if supplied in hashes:
                hashes.remove(supplied); mfa.backup_hashes=json.dumps(hashes); db.commit(); valid=True
        if not valid:
            log_event('login_mfa_failed',None,{'email':data.email.lower().strip(),'ip':client_ip})
            raise HTTPException(401,'A valid authenticator code or backup code is required')
    token=create_token(user)
    record_session(user,token,request,db)
    if cache:
        try: cache.setex(f'session:{user.id}:{hashlib.sha256(token.encode()).hexdigest()[:16]}',JWT_EXPIRE_MINUTES*60,'active')
        except Exception as e: logger.warning(f"Redis session write failed on login: {e}")
    log_event('login',user.id)
    return {'user':user_dict(user),'access_token':token,'token_type':'bearer'}

@app.get('/api/auth/me')
def me(user:User=Depends(current_user)): return {'user':user_dict(user)}

@app.post('/api/auth/logout')
def logout(creds: HTTPAuthorizationCredentials=Depends(bearer), user:User=Depends(current_user),db:Session=Depends(get_db)):
    if cache and creds:
        try:
            token_hash = hashlib.sha256(creds.credentials.encode()).hexdigest()[:16]
            cache.delete(f'session:{user.id}:{token_hash}')
        except Exception as e:
            logger.warning(f"Redis session deletion failed on logout: {e}")
    session_record=db.scalar(select(AuthSession).where(AuthSession.token_hash==hashlib.sha256(creds.credentials.encode()).hexdigest())) if creds else None
    if session_record: session_record.revoked=True; db.commit()
    log_event('logout',user.id)
    return {'message':'Logged out. Session revoked.'}

@app.get('/api/admin/users')
def list_users(user:User=Depends(require_roles('admin')),db:Session=Depends(get_db)):
    return [user_dict(u) for u in db.scalars(select(User).order_by(User.id.desc())).all()]

@app.get('/api/folders')
def folders(user:User=Depends(current_user),db:Session=Depends(get_db)):
    return [{'id':f.id,'name':f.name,'created_at':f.created_at.isoformat() if f.created_at else None} for f in db.scalars(select(Folder).where(Folder.owner_id==user.id).order_by(Folder.name)).all()]

@app.post('/api/folders',status_code=201)
def create_folder(data:FolderIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    name=data.name.strip()
    if not name: raise HTTPException(422,'Folder name is required')
    folder=Folder(name=name,owner_id=user.id); db.add(folder); db.commit(); db.refresh(folder); log_event('folder_created',user.id,{'folder_id':folder.id,'name':name})
    return {'id':folder.id,'name':folder.name,'created_at':folder.created_at.isoformat()}

@app.get('/api/files')
def list_files(q:Optional[str]=None,folder_id:Optional[int]=None,user:User=Depends(current_user),db:Session=Depends(get_db)):
    stmt=select(StoredFile).where(StoredFile.owner_id==user.id)
    if folder_id is not None: stmt=stmt.where(StoredFile.folder_id==folder_id)
    if q: stmt=stmt.where(StoredFile.original_name.ilike(f'%{q[:100]}%'))
    owned=db.scalars(stmt.order_by(StoredFile.uploaded_at.desc())).all()
    shared_ids=[grant.file_id for grant in db.scalars(select(FileGrant).where(FileGrant.recipient_id==user.id)).all()]
    shared=db.scalars(select(StoredFile).where(StoredFile.id.in_(shared_ids))).all() if shared_ids and folder_id is None else []
    combined={item.id:item for item in [*owned,*shared] if not q or q[:100].lower() in item.original_name.lower()}
    return [file_dict(item) for item in sorted(combined.values(),key=lambda item:item.uploaded_at or datetime.min,reverse=True)]

@app.get('/api/files/{file_id}/metadata')
def get_file_metadata(file_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    record=db.scalar(select(StoredFile).where(StoredFile.id==file_id))
    if not record: raise HTTPException(404,'File not found')
    if record.owner_id!=user.id and user.role!='admin' and not db.scalar(select(FileGrant.id).where(FileGrant.file_id==file_id,FileGrant.recipient_id==user.id)):
        raise HTTPException(404,'File not found')
    doc=None
    if mongo_available and mdb is not None:
        try:
            doc=mdb.files.find_one({'id':file_id},{'_id':0})
        except Exception as e:
            logger.warning(f"MongoDB metadata query failed for file {file_id}: {e}")
    if doc:
        if 'timestamp' in doc and isinstance(doc['timestamp'], datetime):
            doc['timestamp']=doc['timestamp'].isoformat()
        return {'source':'mongodb','metadata':doc}
    fallback=file_dict(record)
    fallback['stored_name']=record.stored_name
    return {'source':'postgres_fallback','metadata':fallback}

@app.post('/api/files/upload',status_code=201)
def upload_file(file:UploadFile=File(...),folder_id:Optional[int]=Form(None),user:User=Depends(current_user),db:Session=Depends(get_db)):
    check_rate_limit(f'ratelimit:upload:{user.id}', limit=20, window=60)
    original=Path(file.filename or 'upload').name
    suffix=Path(original).suffix.lower()
    if suffix not in ALLOWED: raise HTTPException(415,'File type not allowed')
    if folder_id is not None and not db.scalar(select(Folder).where(Folder.id==folder_id,Folder.owner_id==user.id)): raise HTTPException(404,'Folder not found')
    stored=f'{uuid.uuid4().hex}{suffix}'; dest=STORAGE/stored; size=0; digest=hashlib.sha256()
    try:
        chunks=[]
        while True:
            chunk=file.file.read(1024*1024)
            if not chunk: break
            size+=len(chunk)
            if size>MAX_UPLOAD_BYTES: raise HTTPException(413,f'File exceeds {MAX_UPLOAD_BYTES//1024//1024} MiB limit')
            digest.update(chunk); chunks.append(chunk)
        if size==0: raise HTTPException(400,'Empty files are not allowed')
        plaintext=b''.join(chunks)
        validate_file_content(original,plaintext)
        if db.scalar(select(StoredFile.id).where(StoredFile.owner_id==user.id,StoredFile.sha256==digest.hexdigest())): raise HTTPException(409,'You already uploaded an identical file')
        quota_bytes=int(os.getenv('USER_STORAGE_QUOTA_MB','100'))*1024*1024
        current_bytes=db.scalar(select(func.coalesce(func.sum(StoredFile.size),0)).where(StoredFile.owner_id==user.id)) or 0
        vault_bytes=db.scalar(select(func.coalesce(func.sum(VaultFile.size),0)).where(VaultFile.user_id==user.id)) or 0
        if current_bytes+vault_bytes+size>quota_bytes: raise HTTPException(413,'Your storage quota would be exceeded')
        encrypted,wrapped_key,wrap_nonce,key_version=encrypt_bytes(plaintext,stored)
        put_bytes(stored,encrypted,STORAGE)
        record=StoredFile(original_name=original,stored_name=stored,content_type=file.content_type or 'application/octet-stream',size=size,sha256=digest.hexdigest(),owner_id=user.id,folder_id=folder_id)
        db.add(record); db.flush()
        db.add(FileKey(file_id=record.id,wrapped_key=wrapped_key,wrap_nonce=wrap_nonce,key_version=key_version))
        db.commit(); db.refresh(record)
        metadata={**file_dict(record),'stored_name':stored,'event':'file_uploaded'}
        if mongo_available and mdb is not None:
            try:
                mdb.files.insert_one({**metadata,'timestamp':datetime.now(timezone.utc)})
            except Exception as e:
                logger.warning(f"MongoDB file metadata insertion failed: {e}")
        log_event('file_uploaded',user.id,{'file_id':record.id,'name':original,'size':size})
        return file_dict(record)
    except Exception:
        delete_object(stored,STORAGE)
        db.rollback(); raise
    finally: file.file.close()

@app.get('/api/files/{file_id}/download')
def download_file(file_id:int,request:Request,user:User=Depends(current_user),db:Session=Depends(get_db)):
    record=db.scalar(select(StoredFile).where(StoredFile.id==file_id))
    grant=db.scalar(select(FileGrant).where(FileGrant.file_id==file_id,FileGrant.recipient_id==user.id))
    if not record or (record.owner_id!=user.id and grant is None): raise HTTPException(404,'File not found')
    if grant and grant.permission=='view': raise HTTPException(403,'Download is disabled for this shared file')
    if not object_exists(record.stored_name,STORAGE): raise HTTPException(404,'Stored file is missing')
    key_record=db.scalar(select(FileKey).where(FileKey.file_id==record.id))
    try:
        if not key_record:
            raise HTTPException(409,'This legacy file is not encrypted yet. Run the encryption migration first.')
        plaintext=decrypt_bytes(get_bytes(record.stored_name,STORAGE),record.stored_name,key_record.wrapped_key,key_record.wrap_nonce,key_record.key_version)
    except HTTPException:
        raise
    except Exception:
        log_event('file_decryption_failed',user.id,{'file_id':file_id})
        raise HTTPException(500,'Could not decrypt stored file')
    log_event('file_downloaded',user.id,{'file_id':file_id,'ip':request.client.host if request.client else None})
    return Response(content=plaintext,media_type=record.content_type,headers={'Content-Disposition':f'attachment; filename="{record.original_name}"'})

@app.delete('/api/files/{file_id}')
def delete_file(file_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    record=db.scalar(select(StoredFile).where(StoredFile.id==file_id,StoredFile.owner_id==user.id))
    if not record: raise HTTPException(404,'File not found')
    delete_object(record.stored_name,STORAGE)
    share_ids=list(db.scalars(select(FileShare.id).where(FileShare.file_id==file_id)).all())
    if share_ids: db.execute(delete(SharePolicy).where(SharePolicy.share_id.in_(share_ids)))
    db.execute(delete(FileShare).where(FileShare.file_id==file_id))
    db.execute(delete(FileGrant).where(FileGrant.file_id==file_id))
    db.execute(delete(FileKey).where(FileKey.file_id==file_id))
    db.delete(record); db.commit()
    if mongo_available and mdb is not None:
        try:
            mdb.files.delete_many({'id':file_id,'owner_id':user.id})
        except Exception as e:
            logger.warning(f"MongoDB file deletion failed: {e}")
    log_event('file_deleted',user.id,{'file_id':file_id}); return {'message':'File deleted'}

class DirectShareIn(BaseModel):
    email:EmailStr
    permission:str=Field(default='view_download',pattern='^(view|view_download)$')

class ShareCreateIn(BaseModel):
    expires_in_hours:int=Field(default=24,ge=1,le=720)
    max_downloads:Optional[int]=Field(default=None,ge=1,le=10000)
    permission:str=Field(default='download',pattern='^(view|download)$')

class VaultSetupIn(BaseModel):
    password:str=Field(min_length=12,max_length=128)
class VaultPasswordChangeIn(BaseModel):
    new_password:str=Field(min_length=12,max_length=128)
class VaultRenameIn(BaseModel):
    name:str=Field(min_length=1,max_length=255)

class ConfirmAccountPasswordIn(BaseModel):
    password:str=Field(min_length=1,max_length=128)

@app.post('/api/files/{file_id}/shares',status_code=201)
def create_share(file_id:int,request:Request,data:ShareCreateIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    f=db.scalar(select(StoredFile).where(StoredFile.id==file_id,StoredFile.owner_id==user.id))
    if not f: raise HTTPException(404,'File not found')
    token=secrets.token_urlsafe(32)
    sh=FileShare(file_id=file_id,owner_id=user.id,token_hash=hashlib.sha256(token.encode()).hexdigest(),expires_at=datetime.now(timezone.utc)+timedelta(hours=data.expires_in_hours))
    db.add(sh); db.flush(); db.add(SharePolicy(share_id=sh.id,max_downloads=data.max_downloads,download_count=0,permission=data.permission)); db.commit(); db.refresh(sh)
    log_event('share_created',user.id,{'file_id':file_id,'share_id':sh.id,'expires_at':sh.expires_at.isoformat()})
    return {'id':sh.id,'url':str(request.base_url).rstrip('/')+'/share/'+token,'expires_at':sh.expires_at.isoformat(),'max_downloads':data.max_downloads,'permission':data.permission}

@app.get('/api/shares/links')
def list_share_links(user:User=Depends(current_user),db:Session=Depends(get_db)):
    shares=db.scalars(select(FileShare).where(FileShare.owner_id==user.id).order_by(FileShare.id.desc())).all(); output=[]
    for sh in shares:
        f=db.get(StoredFile,sh.file_id); policy=db.scalar(select(SharePolicy).where(SharePolicy.share_id==sh.id))
        expired=sh.expires_at.replace(tzinfo=timezone.utc)<datetime.now(timezone.utc)
        output.append({'id':sh.id,'file_id':sh.file_id,'file_name':f.original_name if f else None,'expires_at':sh.expires_at.isoformat(),'revoked':sh.revoked,'expired':expired,'download_count':policy.download_count if policy else 0,'max_downloads':policy.max_downloads if policy else None,'permission':policy.permission if policy else 'download'})
    return output

@app.get('/share/{token}')
def public_share(token:str,db:Session=Depends(get_db)):
    sh=db.scalar(select(FileShare).where(FileShare.token_hash==hashlib.sha256(token.encode()).hexdigest()))
    now=datetime.now(timezone.utc)
    if not sh or sh.revoked or sh.expires_at.replace(tzinfo=timezone.utc)<now: raise HTTPException(404,'Share expired, revoked, or invalid')
    policy=db.scalar(select(SharePolicy).where(SharePolicy.share_id==sh.id))
    if policy and policy.permission!='view': 
        if policy.max_downloads is not None and policy.download_count>=policy.max_downloads: raise HTTPException(410,'Share download limit reached')
    if policy and policy.permission=='download' and policy.max_downloads is not None and policy.download_count>=policy.max_downloads:
        raise HTTPException(410,'Share download limit reached')
    f=db.get(StoredFile,sh.file_id)
    if not f: raise HTTPException(404,'File not found')
    if not object_exists(f.stored_name,STORAGE): raise HTTPException(404,'Stored file is missing')
    try:
        key=db.scalar(select(FileKey).where(FileKey.file_id==f.id))
        if not key: raise HTTPException(409,'This legacy file is not encrypted yet. Run the encryption migration first.')
        blob=get_bytes(f.stored_name,STORAGE)
        content=decrypt_bytes(blob,f.stored_name,key.wrapped_key,key.wrap_nonce,key.key_version)
    except HTTPException:
        raise
    except Exception:
        log_event('shared_file_decryption_failed',None,{'file_id':f.id,'share_id':sh.id})
        raise HTTPException(500,'Unable to decrypt file')
    if policy and policy.permission=='download':
        query=update(SharePolicy).where(SharePolicy.id==policy.id)
        if policy.max_downloads is not None: query=query.where(SharePolicy.download_count<policy.max_downloads)
        result=db.execute(query.values(download_count=SharePolicy.download_count+1)); db.commit()
        if result.rowcount!=1: raise HTTPException(410,'Share download limit reached')
    log_event('shared_file_accessed',None,{'file_id':f.id,'share_id':sh.id,'permission':policy.permission if policy else 'download'})
    mode='inline' if policy and policy.permission=='view' else 'attachment'
    disposition_name=Path(f.original_name).name.replace('\\r','').replace('\\n','').replace('"','')
    return Response(content=content,media_type=f.content_type,headers={'Content-Disposition':f'{mode}; filename="{disposition_name}"','X-Content-Type-Options':'nosniff','Cache-Control':'no-store','Referrer-Policy':'no-referrer'})

@app.post('/api/shares/{share_id}/revoke')
def revoke_share(share_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    sh=db.scalar(select(FileShare).where(FileShare.id==share_id,FileShare.owner_id==user.id))
    if not sh: raise HTTPException(404,'Share not found')
    sh.revoked=True; db.commit(); log_event('share_revoked',user.id,{'share_id':share_id,'file_id':sh.file_id})
    return {'message':'Share revoked'}

@app.post('/api/files/{file_id}/direct-shares',status_code=201)
def direct_share(file_id:int,data:DirectShareIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    f=db.scalar(select(StoredFile).where(StoredFile.id==file_id,StoredFile.owner_id==user.id))
    if not f: raise HTTPException(404,'File not found')
    recipient=db.scalar(select(User).where(User.email==data.email.lower().strip()))
    if not recipient: raise HTTPException(404,'Recipient account not found')
    if recipient.id==user.id: raise HTTPException(400,'You already own this file')
    grant=db.scalar(select(FileGrant).where(FileGrant.file_id==file_id,FileGrant.recipient_id==recipient.id))
    if grant: grant.permission=data.permission
    else: db.add(FileGrant(file_id=file_id,owner_id=user.id,recipient_id=recipient.id,permission=data.permission))
    db.commit(); log_event('direct_share_created',user.id,{'file_id':file_id,'recipient_id':recipient.id,'permission':data.permission})
    return {'message':'File shared with recipient','recipient':recipient.email,'permission':data.permission}

@app.get('/api/shares/direct')
def list_direct_shares(user:User=Depends(current_user),db:Session=Depends(get_db)):
    received=db.scalars(select(FileGrant).where(FileGrant.recipient_id==user.id).order_by(FileGrant.id.desc())).all(); sent=db.scalars(select(FileGrant).where(FileGrant.owner_id==user.id).order_by(FileGrant.id.desc())).all()
    def pack(grant,direction):
        f=db.get(StoredFile,grant.file_id); owner=db.get(User,grant.owner_id); recipient=db.get(User,grant.recipient_id)
        return {'grant_id':grant.id,'file_id':grant.file_id,'file_name':f.original_name if f else None,'owner_email':owner.email if owner else None,'recipient_email':recipient.email if recipient else None,'permission':grant.permission,'direction':direction,'created_at':grant.created_at.isoformat()}
    return {'shared_with_me':[pack(x,'received') for x in received],'shared_by_me':[pack(x,'sent') for x in sent]}

@app.delete('/api/shares/direct/{grant_id}')
def revoke_direct_share(grant_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    grant=db.scalar(select(FileGrant).where(FileGrant.id==grant_id,FileGrant.owner_id==user.id))
    if not grant: raise HTTPException(404,'Share not found')
    file_id=grant.file_id; db.delete(grant); db.commit(); log_event('direct_share_revoked',user.id,{'grant_id':grant_id,'file_id':file_id})
    return {'message':'Share revoked'}

@app.get('/api/files/{file_id}/preview')
def preview_file(file_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    f=db.get(StoredFile,file_id); grant=db.scalar(select(FileGrant).where(FileGrant.file_id==file_id,FileGrant.recipient_id==user.id))
    if not f or (f.owner_id!=user.id and grant is None): raise HTTPException(404,'File not found')
    key=db.scalar(select(FileKey).where(FileKey.file_id==file_id))
    if not key: raise HTTPException(409,'This legacy file is not encrypted yet. Run the encryption migration first.')
    try:
        blob=get_bytes(f.stored_name,STORAGE); content=decrypt_bytes(blob,f.stored_name,key.wrapped_key,key.wrap_nonce,key.key_version)
    except HTTPException:
        raise
    except Exception:
        log_event('file_decryption_failed',user.id,{'file_id':file_id}); raise HTTPException(500,'Could not preview file')
    return Response(content=content,media_type=f.content_type,headers={'Content-Disposition':f'inline; filename="{f.original_name}"','X-Content-Type-Options':'nosniff','Cache-Control':'no-store'})

@app.get('/api/dashboard/user')
def user_dashboard(user:User=Depends(current_user),db:Session=Depends(get_db)):
    files=db.scalars(select(StoredFile).where(StoredFile.owner_id==user.id)).all(); shares=db.scalars(select(FileShare).where(FileShare.owner_id==user.id)).all(); grants=db.scalars(select(FileGrant).where(FileGrant.owner_id==user.id)).all()
    vault_count=db.scalar(select(func.count()).select_from(VaultFile).where(VaultFile.user_id==user.id)) or 0
    return {'stats':{'files':len(files),'storage_bytes':sum(x.size for x in files),'shares_total':len(shares),'direct_shares':len(grants),'vault_files':vault_count,'role':user.role}}

@app.get('/api/dashboard/admin')
def admin_dashboard(user:User=Depends(require_roles('admin')),db:Session=Depends(get_db)):
    files=db.scalars(select(StoredFile)).all(); users=db.scalars(select(User)).all(); shares=db.scalars(select(FileShare)).all(); events=audit_events_for(user,days=7,admin=True)
    return {'stats':{'users_total':len(users),'files_total':len(files),'storage_bytes':sum(x.size for x in files),'shares_total':len(shares),'active_shares':sum(not sh.revoked and sh.expires_at.replace(tzinfo=timezone.utc)>datetime.now(timezone.utc) for sh in shares),'database_backend':db_backend,'mongo_available':mongo_available,'redis_available':cache is not None,'storage_writable':os.access(STORAGE,os.W_OK)},'recent_events':events[:30]}

@app.get('/api/dashboard/security')
def security_dashboard(hours:int=24,user:User=Depends(current_user)):
    if hours not in (24,168,720): raise HTTPException(422,'Invalid time window')
    events=[]
    if mongo_available and mdb is not None:
        try:
            cutoff=datetime.now(timezone.utc)-timedelta(hours=hours); query={'timestamp':{'$gte':cutoff}}
            if user.role!='admin': query['user_id']=user.id
            events=[{k:(v.isoformat() if isinstance(v,datetime) else v) for k,v in row.items()} for row in mdb.activity.find(query,{'_id':0}).sort('timestamp',-1).limit(200)]
        except Exception: pass
    return {'stats':{'events_in_window':len(events),'failed_logins':sum(x.get('event')=='login_failed' for x in events),'blocked_requests':sum(x.get('event')=='request_blocked' for x in events),'downloads':sum(x.get('event') in ('file_downloaded','shared_file_downloaded') for x in events),'vault_alerts':sum('vault' in x.get('event','') and 'locked' in x.get('event','') for x in events)},'events':events}

@app.get('/api/analytics/files')
def file_analytics(days:int=30,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if days not in (7,30,90): raise HTTPException(422,'days must be 7, 30, or 90')
    files=db.scalars(select(StoredFile).where(StoredFile.owner_id==user.id)).all(); events=audit_events_for(user,days); today=datetime.now(timezone.utc).date(); timeline={}
    for i in range(days):
        day=(today-timedelta(days=days-1-i)).isoformat(); timeline[day]={'date':day,'uploads':0,'downloads':0,'shares':0}
    for event in events:
        stamp=event.get('timestamp')
        if not stamp: continue
        day=str(stamp)[:10]
        if day not in timeline: continue
        name=event.get('event','')
        if name=='file_uploaded': timeline[day]['uploads']+=1
        elif name in ('file_downloaded','shared_file_downloaded'): timeline[day]['downloads']+=1
        elif 'share_created' in name: timeline[day]['shares']+=1
    types={}
    for item in files:
        ext=Path(item.original_name).suffix.lower() or 'no extension'; types.setdefault(ext,{'type':ext,'files':0,'bytes':0}); types[ext]['files']+=1; types[ext]['bytes']+=item.size
    stats={'file_count':len(files),'storage_bytes':sum(x.size for x in files),'uploads_in_period':sum(x['uploads'] for x in timeline.values()),'downloads_in_period':sum(x['downloads'] for x in timeline.values()),'share_events_in_period':sum(x['shares'] for x in timeline.values()),'tracked_events':len(events)}
    return {'days':days,'stats':stats,'storage_by_type':sorted(types.values(),key=lambda x:x['bytes'],reverse=True),'activity':list(timeline.values()),'activity_logging':'mongodb' if mongo_available else 'unavailable'}

@app.get('/api/admin/reports/sharing')
def admin_sharing_report(user:User=Depends(require_roles('admin')),db:Session=Depends(get_db)):
    shares=db.scalars(select(FileShare).order_by(FileShare.id.desc())).all(); rows=[]
    for share in shares:
        f=db.get(StoredFile,share.file_id); owner=db.get(User,share.owner_id); policy=db.scalar(select(SharePolicy).where(SharePolicy.share_id==share.id)); expired=share.expires_at.replace(tzinfo=timezone.utc)<datetime.now(timezone.utc)
        rows.append({'share_id':share.id,'file_id':share.file_id,'file_name':f.original_name if f else None,'owner_email':owner.email if owner else None,'expires_at':share.expires_at.isoformat(),'revoked':share.revoked,'expired':expired,'downloads':policy.download_count if policy else 0,'max_downloads':policy.max_downloads if policy else None,'permission':policy.permission if policy else 'download'})
    return {'total':len(rows),'active':sum(not x['revoked'] and not x['expired'] for x in rows),'revoked':sum(x['revoked'] for x in rows),'shares':rows}

def _csv_safe(value):
    value='' if value is None else str(value)
    if value.lstrip().startswith(('=','+','-','@','\\t','\\r')): return "'"+value
    return value

@app.get('/api/admin/audit.csv')
def export_audit_csv(user:User=Depends(require_roles('admin'))):
    rows=audit_events_for(user,days=90,admin=True); out=io.StringIO(); writer=csv.DictWriter(out,fieldnames=['timestamp','event','user_id','details']); writer.writeheader()
    for row in rows: writer.writerow({'timestamp':_csv_safe(row.get('timestamp')),'event':_csv_safe(row.get('event')),'user_id':_csv_safe(row.get('user_id')),'details':_csv_safe(json.dumps(row.get('details',{}),ensure_ascii=False))})
    log_event('admin_audit_export',user.id,{'row_count':len(rows),'days':90})
    return Response(content=out.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="trustshare-audit.csv"','Cache-Control':'no-store'})

def _vault_key(user:User,password:str,db:Session):
    vault=db.scalar(select(Vault).where(Vault.user_id==user.id))
    if not vault: raise HTTPException(404,'Secure Vault has not been configured')
    now=datetime.now(timezone.utc)
    if vault.locked_until and vault.locked_until.replace(tzinfo=timezone.utc)>now: raise HTTPException(423,'Vault is temporarily locked')
    key=hashlib.scrypt(password.encode(),salt=base64.b64decode(vault.salt),n=2**15,r=8,p=1,dklen=32)
    verifier=hmac.new(key,b'trustshare-vault-verifier',hashlib.sha256).hexdigest()
    if not hmac.compare_digest(verifier,vault.verifier):
        vault.failed_attempts+=1
        if vault.failed_attempts>=5: vault.locked_until=now+timedelta(minutes=15); vault.failed_attempts=0; log_event('vault_locked',user.id,{'severity':'high'})
        db.commit(); raise HTTPException(401,'Incorrect vault password')
    vault.failed_attempts=0; vault.locked_until=None; db.commit(); return key

def _vault_seal_name(key:bytes,user_id:int,stored_name:str,name:str):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce=secrets.token_bytes(12); value=AESGCM(key).encrypt(nonce,name.encode(),f'trustshare:vault-name:{user_id}:{stored_name}'.encode())
    return base64.b64encode(nonce+value).decode()

def _vault_open_name(key:bytes,user_id:int,stored_name:str,sealed_name:str):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    raw=base64.b64decode(sealed_name); return AESGCM(key).decrypt(raw[:12],raw[12:],f'trustshare:vault-name:{user_id}:{stored_name}'.encode()).decode()

@app.post('/api/vault/setup',status_code=201)
def vault_setup(data:VaultSetupIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if bcrypt.checkpw(data.password.encode(),user.password_hash.encode()): raise HTTPException(422,'Vault password must differ from account password')
    if db.scalar(select(Vault).where(Vault.user_id==user.id)): raise HTTPException(409,'Vault is already configured')
    salt=secrets.token_bytes(16); key=hashlib.scrypt(data.password.encode(),salt=salt,n=2**15,r=8,p=1,dklen=32); verifier=hmac.new(key,b'trustshare-vault-verifier',hashlib.sha256).hexdigest()
    db.add(Vault(user_id=user.id,salt=base64.b64encode(salt).decode(),verifier=verifier)); db.commit(); log_event('vault_created',user.id)
    return {'message':'Vault created. If you forget its password, files cannot be recovered.'}

@app.get('/api/vault/status')
def vault_status(user:User=Depends(current_user),db:Session=Depends(get_db)):
    vault=db.scalar(select(Vault).where(Vault.user_id==user.id))
    count=db.scalar(select(func.count()).select_from(VaultFile).where(VaultFile.user_id==user.id)) or 0
    return {'configured':vault is not None,'file_count':count,'locked_until':vault.locked_until.isoformat() if vault and vault.locked_until else None}

@app.get('/api/vault/files')
def vault_list(x_vault_password:str=Header(...),user:User=Depends(current_user),db:Session=Depends(get_db)):
    key=_vault_key(user,x_vault_password,db); rows=db.scalars(select(VaultFile).where(VaultFile.user_id==user.id).order_by(VaultFile.created_at.desc())).all(); out=[]
    for row in rows:
        try: name=_vault_open_name(key,user.id,row.stored_name,row.sealed_name)
        except Exception: raise HTTPException(500,'Vault metadata could not be decrypted')
        out.append({'id':row.id,'name':name,'size':row.size,'content_type':row.content_type,'created_at':row.created_at.isoformat()})
    log_event('vault_listed',user.id,{'count':len(out)}); return out

@app.post('/api/vault/files/upload',status_code=201)
def vault_upload(file:UploadFile=File(...),x_vault_password:str=Header(...),user:User=Depends(current_user),db:Session=Depends(get_db)):
    key=_vault_key(user,x_vault_password,db); name=Path(file.filename or 'upload').name
    if Path(name).suffix.lower() not in ALLOWED: raise HTTPException(415,'File type not allowed')
    content=file.file.read(MAX_UPLOAD_BYTES+1); dest=None
    try:
        if not content: raise HTTPException(400,'Empty files are not allowed')
        if len(content)>MAX_UPLOAD_BYTES: raise HTTPException(413,'File is too large')
        validate_file_content(name,content)
        quota=int(os.getenv('USER_STORAGE_QUOTA_MB','100'))*1024*1024
        regular=db.scalar(select(func.coalesce(func.sum(StoredFile.size),0)).where(StoredFile.owner_id==user.id)) or 0; secure=db.scalar(select(func.coalesce(func.sum(VaultFile.size),0)).where(VaultFile.user_id==user.id)) or 0
        if regular+secure+len(content)>quota: raise HTTPException(413,'Your storage quota would be exceeded')
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        stored='vault-'+uuid.uuid4().hex+'.enc'; nonce=secrets.token_bytes(12); encrypted=AESGCM(key).encrypt(nonce,content,f'trustshare:vault-file:{user.id}:{stored}'.encode())
        sealed=_vault_seal_name(key,user.id,stored,name); dest=STORAGE/stored; put_bytes(stored,encrypted,STORAGE)
        row=VaultFile(user_id=user.id,stored_name=stored,sealed_name=sealed,nonce=base64.b64encode(nonce).decode(),content_type=file.content_type or 'application/octet-stream',size=len(content))
        db.add(row); db.commit(); db.refresh(row)
    except Exception:
        if dest is not None: delete_object(dest.name,STORAGE)
        db.rollback(); raise
    finally: file.file.close()
    log_event('vault_file_uploaded',user.id,{'vault_file_id':row.id,'size':len(content)})
    return {'id':row.id,'name':name,'size':len(content),'created_at':row.created_at.isoformat()}

@app.get('/api/vault/files/{vault_file_id}/download')
def vault_download(vault_file_id:int,x_vault_password:str=Header(...),user:User=Depends(current_user),db:Session=Depends(get_db)):
    key=_vault_key(user,x_vault_password,db); row=db.scalar(select(VaultFile).where(VaultFile.id==vault_file_id,VaultFile.user_id==user.id))
    if not row: raise HTTPException(404,'Vault file not found')
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    try:
        content=AESGCM(key).decrypt(base64.b64decode(row.nonce),get_bytes(row.stored_name,STORAGE),f'trustshare:vault-file:{user.id}:{row.stored_name}'.encode()); name=_vault_open_name(key,user.id,row.stored_name,row.sealed_name)
    except Exception:
        log_event('vault_decryption_failed',user.id,{'vault_file_id':vault_file_id,'severity':'high'}); raise HTTPException(500,'Vault file could not be decrypted')
    log_event('vault_file_downloaded',user.id,{'vault_file_id':vault_file_id})
    return Response(content=content,media_type=row.content_type,headers={'Content-Disposition':f'attachment; filename="{name}"','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

@app.get('/api/vault/files/{vault_file_id}/preview')
def vault_preview(vault_file_id:int,x_vault_password:str=Header(...),user:User=Depends(current_user),db:Session=Depends(get_db)):
    key=_vault_key(user,x_vault_password,db)
    row=db.scalar(select(VaultFile).where(VaultFile.id==vault_file_id,VaultFile.user_id==user.id))
    if not row: raise HTTPException(404,'Vault file not found')
    if row.content_type not in {'application/pdf','image/png','image/jpeg','image/webp','text/plain'}:
        raise HTTPException(415,'Preview is not supported for this file type')
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    try:
        content=AESGCM(key).decrypt(base64.b64decode(row.nonce),get_bytes(row.stored_name,STORAGE),f'trustshare:vault-file:{user.id}:{row.stored_name}'.encode())
        name=_vault_open_name(key,user.id,row.stored_name,row.sealed_name)
    except Exception:
        log_event('vault_decryption_failed',user.id,{'vault_file_id':vault_file_id,'severity':'high'})
        raise HTTPException(500,'Vault file could not be previewed')
    safe_name=Path(name).name.replace('\\r','').replace('\\n','').replace('"','')
    log_event('vault_file_previewed',user.id,{'vault_file_id':vault_file_id})
    return Response(content=content,media_type=row.content_type,headers={'Content-Disposition':f'inline; filename="{safe_name}"','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; sandbox"})

@app.patch('/api/vault/files/{vault_file_id}')
def vault_rename(vault_file_id:int,data:VaultRenameIn,x_vault_password:str=Header(...),user:User=Depends(current_user),db:Session=Depends(get_db)):
    key=_vault_key(user,x_vault_password,db)
    row=db.scalar(select(VaultFile).where(VaultFile.id==vault_file_id,VaultFile.user_id==user.id))
    if not row: raise HTTPException(404,'Vault file not found')
    name=Path(data.name.strip()).name
    if not name or len(name)>255 or name in {'.','..'}: raise HTTPException(422,'Invalid vault file name')
    suffix=Path(name).suffix.lower()
    if suffix not in ALLOWED: raise HTTPException(415,'File type not allowed')
    sealed=_vault_seal_name(key,user.id,row.stored_name,name)
    row.sealed_name=sealed
    db.commit()
    log_event('vault_file_renamed',user.id,{'vault_file_id':vault_file_id})
    return {'id':row.id,'name':name,'size':row.size,'content_type':row.content_type,'created_at':row.created_at.isoformat()}

@app.delete('/api/vault/files/{vault_file_id}')
def vault_delete(vault_file_id:int,x_vault_password:str=Header(...),user:User=Depends(current_user),db:Session=Depends(get_db)):
    _vault_key(user,x_vault_password,db); row=db.scalar(select(VaultFile).where(VaultFile.id==vault_file_id,VaultFile.user_id==user.id))
    if not row: raise HTTPException(404,'Vault file not found')
    delete_object(row.stored_name,STORAGE)
    db.delete(row); db.commit(); log_event('vault_file_deleted',user.id,{'vault_file_id':vault_file_id})
    return {'message':'Vault file permanently deleted'}

@app.post('/api/vault/change-password')
def vault_change_password(data:VaultPasswordChangeIn,x_vault_password:str=Header(...),user:User=Depends(current_user),db:Session=Depends(get_db)):
    old_key=_vault_key(user,x_vault_password,db)
    if len(data.new_password)<12: raise HTTPException(422,'Vault password must be at least 12 characters')
    if bcrypt.checkpw(data.new_password.encode(),user.password_hash.encode()): raise HTTPException(422,'Vault password must differ from account password')
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    rows=db.scalars(select(VaultFile).where(VaultFile.user_id==user.id)).all()
    vault=db.scalar(select(Vault).where(Vault.user_id==user.id))
    if not vault: raise HTTPException(404,'Secure Vault has not been configured')
    new_salt=secrets.token_bytes(16)
    new_key=hashlib.scrypt(data.new_password.encode(),salt=new_salt,n=2**15,r=8,p=1,dklen=32)
    staged=[]
    for row in rows:
        old_blob=get_bytes(row.stored_name,STORAGE)
        old_nonce=row.nonce
        old_sealed=row.sealed_name
        aad=f'trustshare:vault-file:{user.id}:{row.stored_name}'.encode()
        plain=AESGCM(old_key).decrypt(base64.b64decode(old_nonce),old_blob,aad)
        nonce=secrets.token_bytes(12)
        new_blob=AESGCM(new_key).encrypt(nonce,plain,aad)
        name=_vault_open_name(old_key,user.id,row.stored_name,old_sealed)
        sealed=_vault_seal_name(new_key,user.id,row.stored_name,name)
        staged.append((row,old_blob,old_nonce,old_sealed,new_blob,base64.b64encode(nonce).decode(),sealed))
    applied=[]
    try:
        for row,old_blob,old_nonce,old_sealed,new_blob,nonce,sealed in staged:
            put_bytes(row.stored_name,new_blob,STORAGE)
            applied.append((row,old_blob,old_nonce,old_sealed))
            row.nonce=nonce
            row.sealed_name=sealed
        vault.salt=base64.b64encode(new_salt).decode()
        vault.verifier=hmac.new(new_key,b'trustshare-vault-verifier',hashlib.sha256).hexdigest()
        db.commit()
    except Exception:
        for row,old_blob,old_nonce,old_sealed in reversed(applied):
            try:
                put_bytes(row.stored_name,old_blob,STORAGE)
            except Exception:
                logger.exception('Could not restore vault object during password-change rollback')
            row.nonce=old_nonce
            row.sealed_name=old_sealed
        db.rollback()
        raise HTTPException(500,'Vault password change failed; stored files were restored where possible')
    log_event('vault_password_changed',user.id,{'file_count':len(rows)})
    return {'message':'Vault password changed'}

@app.post('/api/vault/reset')
def vault_reset(data:ConfirmAccountPasswordIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if not bcrypt.checkpw(data.password.encode(),user.password_hash.encode()): raise HTTPException(401,'Account password confirmation failed')
    rows=db.scalars(select(VaultFile).where(VaultFile.user_id==user.id)).all()
    for row in rows:
        delete_object(row.stored_name,STORAGE)
        db.delete(row)
    vault=db.scalar(select(Vault).where(Vault.user_id==user.id))
    if vault: db.delete(vault)
    db.commit(); log_event('vault_reset',user.id,{'deleted_files':len(rows),'severity':'high'})
    return {'message':'Vault reset; encrypted files were permanently deleted.'}

class MfaCodeIn(BaseModel):
    code:str=Field(min_length=6,max_length=32)
class MfaDisableIn(BaseModel):
    password:str=Field(min_length=1,max_length=128)
    code:str=Field(min_length=6,max_length=32)

def _verify_totp_or_backup(user:User,code:str,mfa:UserMfa,db:Session,consume_backup:bool=True):
    valid=False
    try:
        secret=decrypt_secret(mfa.encrypted_secret,mfa.nonce,mfa.key_version,f'trustshare:mfa:{user.id}')
        import pyotp
        valid=pyotp.TOTP(secret).verify(code.strip(),valid_window=1)
    except Exception as exc:
        logger.warning(f'MFA verification error: {type(exc).__name__}')
    if valid: return True
    hashes=json.loads(mfa.backup_hashes or '[]')
    supplied=hashlib.sha256(code.strip().upper().encode()).hexdigest()
    if supplied in hashes:
        if consume_backup:
            hashes.remove(supplied); mfa.backup_hashes=json.dumps(hashes); db.commit()
        return True
    return False

@app.get('/api/auth/mfa/status')
def mfa_status(user:User=Depends(current_user),db:Session=Depends(get_db)):
    mfa=db.scalar(select(UserMfa).where(UserMfa.user_id==user.id))
    return {'configured':mfa is not None,'enabled':bool(mfa and mfa.enabled),'backup_codes_remaining':len(json.loads(mfa.backup_hashes or '[]')) if mfa else 0}

@app.post('/api/auth/mfa/setup')
def mfa_setup(user:User=Depends(current_user),db:Session=Depends(get_db)):
    existing=db.scalar(select(UserMfa).where(UserMfa.user_id==user.id))
    if existing and existing.enabled: raise HTTPException(409,'MFA is already enabled. Disable it before setting up again.')
    import pyotp
    secret=pyotp.random_base32()
    encrypted,nonce,version=encrypt_secret(secret,f'trustshare:mfa:{user.id}')
    if existing:
        existing.encrypted_secret=encrypted; existing.nonce=nonce; existing.key_version=version; existing.enabled=False; existing.backup_hashes='[]'
    else:
        db.add(UserMfa(user_id=user.id,encrypted_secret=encrypted,nonce=nonce,key_version=version,enabled=False,backup_hashes='[]'))
    db.commit(); log_event('mfa_setup_started',user.id)
    return {'secret':secret,'otpauth_url':pyotp.TOTP(secret).provisioning_uri(name=user.email,issuer_name='TrustShare'),'message':'Add this account to your authenticator, then confirm with a current code. The secret is shown once.'}

@app.post('/api/auth/mfa/confirm')
def mfa_confirm(data:MfaCodeIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    mfa=db.scalar(select(UserMfa).where(UserMfa.user_id==user.id))
    if not mfa: raise HTTPException(404,'Start MFA setup first')
    if mfa.enabled: raise HTTPException(409,'MFA is already enabled')
    try:
        secret=decrypt_secret(mfa.encrypted_secret,mfa.nonce,mfa.key_version,f'trustshare:mfa:{user.id}')
        import pyotp
        if not pyotp.TOTP(secret).verify(data.code.strip(),valid_window=1): raise HTTPException(400,'Authenticator code is invalid')
    except HTTPException: raise
    except Exception: raise HTTPException(500,'MFA setup could not be verified')
    backup=[secrets.token_hex(5).upper() for _ in range(10)]
    mfa.enabled=True; mfa.backup_hashes=json.dumps([hashlib.sha256(code.encode()).hexdigest() for code in backup]); db.commit()
    log_event('mfa_enabled',user.id)
    return {'enabled':True,'backup_codes':backup,'warning':'Save these backup codes now. They are shown only once.'}

@app.post('/api/auth/mfa/disable')
def mfa_disable(data:MfaDisableIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if not bcrypt.checkpw(data.password.encode(),user.password_hash.encode()): raise HTTPException(401,'Password confirmation failed')
    mfa=db.scalar(select(UserMfa).where(UserMfa.user_id==user.id))
    if not mfa or not mfa.enabled: raise HTTPException(409,'MFA is not enabled')
    if not _verify_totp_or_backup(user,data.code,mfa,db): raise HTTPException(401,'Authenticator or backup code is invalid')
    mfa.enabled=False; mfa.backup_hashes='[]'; db.commit(); log_event('mfa_disabled',user.id)
    return {'enabled':False,'message':'MFA disabled'}

@app.get('/api/auth/sessions')
def list_auth_sessions(creds:HTTPAuthorizationCredentials=Depends(bearer),user:User=Depends(current_user),db:Session=Depends(get_db)):
    current_hash=hashlib.sha256(creds.credentials.encode()).hexdigest() if creds else ''
    rows=db.scalars(select(AuthSession).where(AuthSession.user_id==user.id,AuthSession.revoked==False).order_by(AuthSession.last_active_at.desc())).all()
    return [{'id':row.id,'current':row.token_hash==current_hash,'ip_address':row.ip_address,'user_agent':row.user_agent,'created_at':row.created_at.isoformat(),'last_active_at':row.last_active_at.isoformat()} for row in rows]

@app.post('/api/auth/sessions/{session_id}/revoke')
def revoke_auth_session(session_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.scalar(select(AuthSession).where(AuthSession.id==session_id,AuthSession.user_id==user.id,AuthSession.revoked==False))
    if not row: raise HTTPException(404,'Active session not found')
    row.revoked=True
    if cache:
        try: cache.delete(f'session:{user.id}:{row.token_hash[:16]}')
        except Exception as exc: logger.warning(f'Redis session revocation failed: {type(exc).__name__}')
    db.commit(); log_event('session_revoked',user.id,{'session_id':session_id})
    return {'message':'Session revoked'}

@app.post('/api/auth/sessions/revoke-all')
def revoke_all_auth_sessions(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(AuthSession).where(AuthSession.user_id==user.id,AuthSession.revoked==False)).all()
    for row in rows:
        row.revoked=True
        if cache:
            try: cache.delete(f'session:{user.id}:{row.token_hash[:16]}')
            except Exception as exc: logger.warning(f'Redis session revocation failed: {type(exc).__name__}')
    db.commit(); log_event('sessions_revoked_all',user.id,{'count':len(rows)})
    return {'message':'All sessions revoked','count':len(rows)}
