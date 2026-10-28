import os, uuid, shutil, hashlib, logging, secrets, csv, io, zipfile, json, hmac, base64
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt
import redis
from app.security_crypto import encrypt_bytes, decrypt_bytes
from jose import jwt, JWTError
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from pymongo import MongoClient
from sqlalchemy import create_engine, String, Integer, DateTime, ForeignKey, Text, Boolean, func, select
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
class LoginIn(BaseModel): email: EmailStr; password: str
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
        'storage':'writable' if STORAGE.exists() and os.access(STORAGE,os.W_OK) else 'unavailable'
    }

@app.post('/api/auth/register',status_code=201)
def register(data:RegisterIn,db:Session=Depends(get_db)):
    email=data.email.lower().strip()
    if db.scalar(select(User).where(User.email==email)): raise HTTPException(409,'Email is already registered')
    user=User(name=data.name.strip(),email=email,password_hash=bcrypt.hashpw(data.password.encode(),bcrypt.gensalt()).decode(),role='user')
    db.add(user); db.commit(); db.refresh(user); log_event('register',user.id,{'email':email})
    token=create_token(user)
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
    token=create_token(user)
    if cache:
        try: cache.setex(f'session:{user.id}:{hashlib.sha256(token.encode()).hexdigest()[:16]}',JWT_EXPIRE_MINUTES*60,'active')
        except Exception as e: logger.warning(f"Redis session write failed on login: {e}")
    log_event('login',user.id)
    return {'user':user_dict(user),'access_token':token,'token_type':'bearer'}

@app.get('/api/auth/me')
def me(user:User=Depends(current_user)): return {'user':user_dict(user)}

@app.post('/api/auth/logout')
def logout(creds: HTTPAuthorizationCredentials=Depends(bearer), user:User=Depends(current_user)):
    if cache and creds:
        try:
            token_hash = hashlib.sha256(creds.credentials.encode()).hexdigest()[:16]
            cache.delete(f'session:{user.id}:{token_hash}')
        except Exception as e:
            logger.warning(f"Redis session deletion failed on logout: {e}")
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
        if current_bytes+size>quota_bytes: raise HTTPException(413,'Your storage quota would be exceeded')
        encrypted,wrapped_key,wrap_nonce,key_version=encrypt_bytes(plaintext,stored)
        with dest.open('wb') as out: out.write(encrypted)
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
        if dest.exists(): dest.unlink()
        db.rollback(); raise
    finally: file.file.close()

@app.get('/api/files/{file_id}/download')
def download_file(file_id:int,request:Request,user:User=Depends(current_user),db:Session=Depends(get_db)):
    record=db.scalar(select(StoredFile).where(StoredFile.id==file_id))
    grant=db.scalar(select(FileGrant).where(FileGrant.file_id==file_id,FileGrant.recipient_id==user.id))
    if not record or (record.owner_id!=user.id and grant is None): raise HTTPException(404,'File not found')
    if grant and grant.permission=='view': raise HTTPException(403,'Download is disabled for this shared file')
    path=STORAGE/record.stored_name
    if not path.is_file(): raise HTTPException(404,'Stored file is missing')
    key_record=db.scalar(select(FileKey).where(FileKey.file_id==record.id))
    try:
        if key_record:
            plaintext=decrypt_bytes(path.read_bytes(),record.stored_name,key_record.wrapped_key,key_record.wrap_nonce,key_record.key_version)
        else:
            plaintext=path.read_bytes()
    except Exception:
        log_event('file_decryption_failed',user.id,{'file_id':file_id})
        raise HTTPException(500,'Could not decrypt stored file')
    log_event('file_downloaded',user.id,{'file_id':file_id,'ip':request.client.host if request.client else None})
    return Response(content=plaintext,media_type=record.content_type,headers={'Content-Disposition':f'attachment; filename="{record.original_name}"'})

@app.delete('/api/files/{file_id}')
def delete_file(file_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    record=db.scalar(select(StoredFile).where(StoredFile.id==file_id,StoredFile.owner_id==user.id))
    if not record: raise HTTPException(404,'File not found')
    path=STORAGE/record.stored_name
    if path.exists(): path.unlink()
    db.delete(record); db.commit()
    if mongo_available and mdb is not None:
        try:
            mdb.files.delete_many({'id':file_id,'owner_id':user.id})
        except Exception as e:
            logger.warning(f"MongoDB file deletion failed: {e}")
    log_event('file_deleted',user.id,{'file_id':file_id}); return {'message':'File deleted'}

class ShareCreateIn(BaseModel):
    expires_in_hours:int=Field(default=24,ge=1,le=720)
    max_downloads:Optional[int]=Field(default=None,ge=1,le=10000)
    permission:str=Field(default='download',pattern='^(view|download)

@app.post('/api/files/{file_id}/shares',status_code=201)
def create_share(file_id:int,request:Request,data:ShareCreateIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    f=db.scalar(select(StoredFile).where(StoredFile.id==file_id,StoredFile.owner_id==user.id))
    if not f: raise HTTPException(404,'File not found')
    token=secrets.token_urlsafe(32)
    sh=FileShare(file_id=file_id,owner_id=user.id,token_hash=hashlib.sha256(token.encode()).hexdigest(),expires_at=datetime.now(timezone.utc)+timedelta(hours=data.expires_in_hours))
    db.add(sh); db.flush()
    db.add(SharePolicy(share_id=sh.id,max_downloads=data.max_downloads,download_count=0,permission=data.permission))
    db.commit(); db.refresh(sh); log_event('share_created',user.id,{'file_id':file_id,'share_id':sh.id,'expires_at':sh.expires_at.isoformat()})
    return {'id':sh.id,'url':str(request.base_url).rstrip('/')+'/share/'+token,'expires_at':sh.expires_at.isoformat(),'max_downloads':data.max_downloads,'permission':data.permission}

@app.get('/share/{token}')
def public_share(token:str,db:Session=Depends(get_db)):
    sh=db.scalar(select(FileShare).where(FileShare.token_hash==hashlib.sha256(token.encode()).hexdigest()))
    if not sh or sh.revoked or sh.expires_at.replace(tzinfo=timezone.utc)<datetime.now(timezone.utc): raise HTTPException(404,'Share expired or revoked')
    policy=db.scalar(select(SharePolicy).where(SharePolicy.share_id==sh.id))
    if policy and policy.max_downloads is not None and policy.download_count>=policy.max_downloads:
        log_event('share_limit_reached',None,{'share_id':sh.id,'file_id':sh.file_id})
        raise HTTPException(410,'Share download limit reached')
    f=db.get(StoredFile,sh.file_id)
    if not f: raise HTTPException(404,'File not found')
    try:
        key_record=db.scalar(select(FileKey).where(FileKey.file_id==f.id))
        stored_bytes=(STORAGE/f.stored_name).read_bytes()
        data=decrypt_bytes(stored_bytes,f.stored_name,key_record.wrapped_key,key_record.wrap_nonce,key_record.key_version) if key_record else stored_bytes
    except Exception:
        log_event('shared_file_decryption_failed',None,{'file_id':f.id})
        raise HTTPException(500,'Unable to decrypt file')
    if policy:
        policy.download_count+=1
        db.commit()
    log_event('shared_file_downloaded',None,{'file_id':f.id,'share_id':sh.id,'permission':policy.permission if policy else 'download'})
    disposition='inline' if policy and policy.permission=='view' else 'attachment'
    return Response(content=data,media_type=f.content_type,headers={'Content-Disposition':f'{disposition}; filename="{f.original_name}"','X-Content-Type-Options':'nosniff'})

@app.post('/api/shares/{share_id}/revoke')
def revoke_share(share_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    sh=db.scalar(select(FileShare).where(FileShare.id==share_id,FileShare.owner_id==user.id))
    if not sh: raise HTTPException(404,'Share not found')
    sh.revoked=True; db.commit(); log_event('share_revoked',user.id,{'share_id':share_id})
    return {'message':'Share revoked'}

@app.get('/api/dashboard/user')
def user_dashboard(user:User=Depends(current_user),db:Session=Depends(get_db)):
    fs=db.scalars(select(StoredFile).where(StoredFile.owner_id==user.id)).all()
    ss=db.scalars(select(FileShare).where(FileShare.owner_id==user.id)).all()
    return {'stats':{'files':len(fs),'storage_bytes':sum(x.size for x in fs),'shares_total':len(ss),'role':user.role}}

@app.get('/api/dashboard/admin')
def admin_dashboard(user:User=Depends(require_roles('admin')),db:Session=Depends(get_db)):
    fs=db.scalars(select(StoredFile)).all(); us=db.scalars(select(User)).all()
    return {'stats':{'users_total':len(us),'files_total':len(fs),'storage_bytes':sum(x.size for x in fs),'shares_total':db.scalar(select(func.count()).select_from(FileShare)) or 0,'database_backend':db_backend,'mongo_available':mongo_available,'redis_available':cache is not None}}

@app.get('/api/dashboard/security')
def security_dashboard(hours:int=24,user:User=Depends(current_user)):
    if hours not in (24,168,720): raise HTTPException(422,'Invalid time window')
    events=[]
    if mongo_available and mdb is not None:
        try:
            cutoff=datetime.now(timezone.utc)-timedelta(hours=hours)
            events=[{k:(v.isoformat() if isinstance(v,datetime) else v) for k,v in e.items()} for e in mdb.activity.find({'timestamp':{'$gte':cutoff}},{'_id':0}).sort('timestamp',-1).limit(100) if e.get('user_id')==user.id or user.role=='admin']
        except Exception: pass
    return {'stats':{'events_in_window':len(events),'failed_logins':sum(e.get('event')=='login_failed' for e in events),'downloads':sum(e.get('event') in ('file_downloaded','shared_file_downloaded') for e in events)},'events':events}
)

@app.post('/api/files/{file_id}/shares',status_code=201)
def create_share(file_id:int,request:Request,data:ShareCreateIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    f=db.scalar(select(StoredFile).where(StoredFile.id==file_id,StoredFile.owner_id==user.id))
    if not f: raise HTTPException(404,'File not found')
    token=secrets.token_urlsafe(32)
    sh=FileShare(file_id=file_id,owner_id=user.id,token_hash=hashlib.sha256(token.encode()).hexdigest(),expires_at=datetime.now(timezone.utc)+timedelta(hours=data.expires_in_hours))
    db.add(sh); db.commit(); db.refresh(sh); log_event('share_created',user.id,{'file_id':file_id})
    return {'id':sh.id,'url':str(request.base_url).rstrip('/')+'/share/'+token,'expires_at':sh.expires_at.isoformat()}

@app.get('/share/{token}')
def public_share(token:str,db:Session=Depends(get_db)):
    sh=db.scalar(select(FileShare).where(FileShare.token_hash==hashlib.sha256(token.encode()).hexdigest()))
    if not sh or sh.revoked or sh.expires_at.replace(tzinfo=timezone.utc)<datetime.now(timezone.utc): raise HTTPException(404,'Share expired or revoked')
    f=db.get(StoredFile,sh.file_id)
    if not f: raise HTTPException(404,'File not found')
    try:
        key_record=db.scalar(select(FileKey).where(FileKey.file_id==f.id))
        stored_bytes=(STORAGE/f.stored_name).read_bytes()
        data=decrypt_bytes(stored_bytes,f.stored_name,key_record.wrapped_key,key_record.wrap_nonce,key_record.key_version) if key_record else stored_bytes
    except Exception:
        log_event('shared_file_decryption_failed',None,{'file_id':f.id})
        raise HTTPException(500,'Unable to decrypt file')
    log_event('shared_file_downloaded',None,{'file_id':f.id})
    return Response(content=data,media_type=f.content_type,headers={'Content-Disposition':f'attachment; filename="{f.original_name}"'})

@app.post('/api/shares/{share_id}/revoke')
def revoke_share(share_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    sh=db.scalar(select(FileShare).where(FileShare.id==share_id,FileShare.owner_id==user.id))
    if not sh: raise HTTPException(404,'Share not found')
    sh.revoked=True; db.commit(); log_event('share_revoked',user.id,{'share_id':share_id})
    return {'message':'Share revoked'}

@app.get('/api/dashboard/user')
def user_dashboard(user:User=Depends(current_user),db:Session=Depends(get_db)):
    fs=db.scalars(select(StoredFile).where(StoredFile.owner_id==user.id)).all()
    ss=db.scalars(select(FileShare).where(FileShare.owner_id==user.id)).all()
    return {'stats':{'files':len(fs),'storage_bytes':sum(x.size for x in fs),'shares_total':len(ss),'role':user.role}}

@app.get('/api/dashboard/admin')
def admin_dashboard(user:User=Depends(require_roles('admin')),db:Session=Depends(get_db)):
    fs=db.scalars(select(StoredFile)).all(); us=db.scalars(select(User)).all()
    return {'stats':{'users_total':len(us),'files_total':len(fs),'storage_bytes':sum(x.size for x in fs),'shares_total':db.scalar(select(func.count()).select_from(FileShare)) or 0,'database_backend':db_backend,'mongo_available':mongo_available,'redis_available':cache is not None}}

@app.get('/api/dashboard/security')
def security_dashboard(hours:int=24,user:User=Depends(current_user)):
    if hours not in (24,168,720): raise HTTPException(422,'Invalid time window')
    events=[]
    if mongo_available and mdb is not None:
        try:
            cutoff=datetime.now(timezone.utc)-timedelta(hours=hours)
            events=[{k:(v.isoformat() if isinstance(v,datetime) else v) for k,v in e.items()} for e in mdb.activity.find({'timestamp':{'$gte':cutoff}},{'_id':0}).sort('timestamp',-1).limit(100) if e.get('user_id')==user.id or user.role=='admin']
        except Exception: pass
    return {'stats':{'events_in_window':len(events),'failed_logins':sum(e.get('event')=='login_failed' for e in events),'downloads':sum(e.get('event') in ('file_downloaded','shared_file_downloaded') for e in events)},'events':events}

class DirectShareIn(BaseModel):
    email:EmailStr
    permission:str=Field(default='view_download',pattern='^(view|view_download)$')

@app.post('/api/files/{file_id}/direct-shares',status_code=201)
def direct_share(file_id:int,data:DirectShareIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    record=db.scalar(select(StoredFile).where(StoredFile.id==file_id,StoredFile.owner_id==user.id))
    if not record: raise HTTPException(404,'File not found')
    recipient=db.scalar(select(User).where(User.email==data.email.lower().strip()))
    if not recipient: raise HTTPException(404,'Recipient account not found')
    if recipient.id==user.id: raise HTTPException(400,'You already own this file')
    existing=db.scalar(select(FileGrant).where(FileGrant.file_id==file_id,FileGrant.recipient_id==recipient.id))
    if existing: existing.permission=data.permission
    else: db.add(FileGrant(file_id=file_id,owner_id=user.id,recipient_id=recipient.id,permission=data.permission))
    db.commit(); log_event('direct_share_created',user.id,{'file_id':file_id,'recipient_id':recipient.id,'permission':data.permission})
    return {'message':'File shared with recipient','recipient':recipient.email,'permission':data.permission}

@app.get('/api/shares/direct')
def list_direct_shares(user:User=Depends(current_user),db:Session=Depends(get_db)):
    received=db.scalars(select(FileGrant).where(FileGrant.recipient_id==user.id)).all()
    sent=db.scalars(select(FileGrant).where(FileGrant.owner_id==user.id)).all()
    def pack(grant,side):
        f=db.get(StoredFile,grant.file_id); owner=db.get(User,grant.owner_id); recipient=db.get(User,grant.recipient_id)
        return {'grant_id':grant.id,'file_id':grant.file_id,'file_name':f.original_name if f else None,'owner_email':owner.email if owner else None,'recipient_email':recipient.email if recipient else None,'permission':grant.permission,'direction':side,'created_at':grant.created_at.isoformat()}
    return {'shared_with_me':[pack(g,'received') for g in received],'shared_by_me':[pack(g,'sent') for g in sent]}

@app.delete('/api/shares/direct/{grant_id}')
def revoke_direct_share(grant_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    grant=db.scalar(select(FileGrant).where(FileGrant.id==grant_id,FileGrant.owner_id==user.id))
    if not grant: raise HTTPException(404,'Share not found')
    file_id=grant.file_id; db.delete(grant); db.commit(); log_event('direct_share_revoked',user.id,{'grant_id':grant_id,'file_id':file_id})
    return {'message':'Direct share revoked'}

@app.get('/api/analytics/files')
def file_analytics(days:int=30,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if days not in (7,30,90): raise HTTPException(422,'days must be 7, 30, or 90')
    files=db.scalars(select(StoredFile).where(StoredFile.owner_id==user.id)).all()
    events=audit_events_for(user,days)
    by_day={}; today=datetime.now(timezone.utc).date()
    for i in range(days):
        day=(today-timedelta(days=days-1-i)).isoformat()
        by_day[day]={'date':day,'uploads':0,'downloads':0,'shares':0}
    for event in events:
        timestamp=event.get('timestamp')
        if not timestamp: continue
        day=str(timestamp)[:10]
        if day not in by_day: continue
        kind=event.get('event','')
        if kind=='file_uploaded': by_day[day]['uploads']+=1
        elif kind in ('file_downloaded','shared_file_downloaded'): by_day[day]['downloads']+=1
        elif 'share_created' in kind: by_day[day]['shares']+=1
    types={}
    for item in files:
        ext=Path(item.original_name).suffix.lower() or 'no extension'
        types.setdefault(ext,{'type':ext,'files':0,'bytes':0})
        types[ext]['files']+=1; types[ext]['bytes']+=item.size
    stats={'file_count':len(files),'storage_bytes':sum(item.size for item in files),'uploads_in_period':sum(item['uploads'] for item in by_day.values()),'downloads_in_period':sum(item['downloads'] for item in by_day.values()),'share_events_in_period':sum(item['shares'] for item in by_day.values()),'tracked_events':len(events)}
    return {'days':days,'stats':stats,'storage_by_type':sorted(types.values(),key=lambda item:item['bytes'],reverse=True),'activity':list(by_day.values()),'activity_logging':'mongodb' if mongo_available else 'unavailable'}

@app.get('/api/admin/reports/sharing')
def admin_sharing_report(user:User=Depends(require_roles('admin')),db:Session=Depends(get_db)):
    shares=db.scalars(select(FileShare).order_by(FileShare.id.desc())).all(); rows=[]
    for sh in shares:
        f=db.get(StoredFile,sh.file_id); owner=db.get(User,sh.owner_id); pol=db.scalar(select(SharePolicy).where(SharePolicy.share_id==sh.id))
        expired=sh.expires_at.replace(tzinfo=timezone.utc)<datetime.now(timezone.utc)
        rows.append({'share_id':sh.id,'file_id':sh.file_id,'file_name':f.original_name if f else None,'owner_email':owner.email if owner else None,'expires_at':sh.expires_at.isoformat(),'revoked':sh.revoked,'expired':expired,'downloads':pol.download_count if pol else 0,'max_downloads':pol.max_downloads if pol else None,'permission':pol.permission if pol else 'download'})
    return {'total':len(rows),'active':sum(not row['revoked'] and not row['expired'] for row in rows),'revoked':sum(row['revoked'] for row in rows),'shares':rows}

def _csv_safe(value):
    text='' if value is None else str(value)
    if text.lstrip().startswith(('=','+','-','@','\t','\r')): return "'"+text
    return text

@app.get('/api/admin/audit.csv')
def export_audit_csv(user:User=Depends(require_roles('admin'))):
    rows=audit_events_for(user,days=90,admin=True); out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=['timestamp','event','user_id','details'],extrasaction='ignore'); writer.writeheader()
    for row in rows:
        writer.writerow({'timestamp':_csv_safe(row.get('timestamp')),'event':_csv_safe(row.get('event')),'user_id':_csv_safe(row.get('user_id')),'details':_csv_safe(json.dumps(row.get('details',{}),ensure_ascii=False))})
    log_event('admin_audit_export',user.id,{'row_count':len(rows),'days':90})
    return Response(content=out.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="trustshare-audit.csv"','Cache-Control':'no-store'})

class VaultSetupIn(BaseModel):
    password:str=Field(min_length=12,max_length=128)
class VaultPasswordChangeIn(BaseModel):
    new_password:str=Field(min_length=12,max_length=128)
class ConfirmAccountPasswordIn(BaseModel):
    password:str=Field(min_length=1,max_length=128)

def _vault_key(user:User,password:str,db:Session):
    vault=db.scalar(select(Vault).where(Vault.user_id==user.id))
    if not vault: raise HTTPException(404,'Secure Vault has not been configured')
    now=datetime.now(timezone.utc)
    if vault.locked_until and vault.locked_until.replace(tzinfo=timezone.utc)>now: raise HTTPException(423,'Vault is temporarily locked')
    key=hashlib.scrypt(password.encode(),salt=base64.b64decode(vault.salt),n=2**15,r=8,p=1,dklen=32)
    expected=hmac.new(key,b'trustshare-vault-verifier',hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,vault.verifier):
        vault.failed_attempts+=1
        if vault.failed_attempts>=5:
            vault.locked_until=now+timedelta(minutes=15); vault.failed_attempts=0
            log_event('vault_locked',user.id,{'severity':'high'})
        db.commit()
        raise HTTPException(401,'Incorrect vault password')
    vault.failed_attempts=0; vault.locked_until=None; db.commit()
    return key

def _vault_seal_name(key:bytes,user_id:int,stored_name:str,name:str):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce=secrets.token_bytes(12)
    sealed=AESGCM(key).encrypt(nonce,name.encode(),f'trustshare:vault-name:{user_id}:{stored_name}'.encode())
    return base64.b64encode(nonce+sealed).decode()

def _vault_open_name(key:bytes,user_id:int,stored_name:str,sealed_name:str):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    raw=base64.b64decode(sealed_name)
    return AESGCM(key).decrypt(raw[:12],raw[12:],f'trustshare:vault-name:{user_id}:{stored_name}'.encode()).decode()

@app.post('/api/vault/setup',status_code=201)
def vault_setup(data:VaultSetupIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if bcrypt.checkpw(data.password.encode(),user.password_hash.encode()): raise HTTPException(422,'Vault password must differ from account password')
    if db.scalar(select(Vault).where(Vault.user_id==user.id)): raise HTTPException(409,'Vault is already configured')
    salt=secrets.token_bytes(16)
    key=hashlib.scrypt(data.password.encode(),salt=salt,n=2**15,r=8,p=1,dklen=32)
    verifier=hmac.new(key,b'trustshare-vault-verifier',hashlib.sha256).hexdigest()
    db.add(Vault(user_id=user.id,salt=base64.b64encode(salt).decode(),verifier=verifier)); db.commit()
    log_event('vault_created',user.id)
    return {'message':'Secure Vault created. The password cannot be recovered if forgotten.'}

@app.get('/api/vault/status')
def vault_status(user:User=Depends(current_user),db:Session=Depends(get_db)):
    vault=db.scalar(select(Vault).where(Vault.user_id==user.id))
    return {'configured':vault is not None,'file_count':db.scalar(select(func.count()).select_from(VaultFile).where(VaultFile.user_id==user.id)) or 0,'locked_until':vault.locked_until.isoformat() if vault and vault.locked_until else None}

@app.get('/api/vault/files')
def vault_list(x_vault_password:str=Header(...),user:User=Depends(current_user),db:Session=Depends(get_db)):
    key=_vault_key(user,x_vault_password,db)
    rows=db.scalars(select(VaultFile).where(VaultFile.user_id==user.id).order_by(VaultFile.created_at.desc())).all()
    output=[]
    for row in rows:
        try: name=_vault_open_name(key,user.id,row.stored_name,row.sealed_name)
        except Exception: raise HTTPException(500,'Vault metadata could not be decrypted')
        output.append({'id':row.id,'name':name,'size':row.size,'content_type':row.content_type,'created_at':row.created_at.isoformat()})
    log_event('vault_listed',user.id,{'count':len(output)})
    return output

@app.post('/api/vault/files/upload',status_code=201)
def vault_upload(file:UploadFile=File(...),x_vault_password:str=Header(...),user:User=Depends(current_user),db:Session=Depends(get_db)):
    key=_vault_key(user,x_vault_password,db)
    original=Path(file.filename or 'upload').name
    if Path(original).suffix.lower() not in ALLOWED: raise HTTPException(415,'File type not allowed')
    content=file.file.read(MAX_UPLOAD_BYTES+1)
    try:
        if not content: raise HTTPException(400,'Empty files are not allowed')
        if len(content)>MAX_UPLOAD_BYTES: raise HTTPException(413,'File is too large')
        validate_file_content(original,content)
        quota_bytes=int(os.getenv('USER_STORAGE_QUOTA_MB','100'))*1024*1024
        regular_bytes=db.scalar(select(func.coalesce(func.sum(StoredFile.size),0)).where(StoredFile.owner_id==user.id)) or 0
        vault_bytes=db.scalar(select(func.coalesce(func.sum(VaultFile.size),0)).where(VaultFile.user_id==user.id)) or 0
        if regular_bytes+vault_bytes+len(content)>quota_bytes: raise HTTPException(413,'Your storage quota would be exceeded')
        stored='vault-'+uuid.uuid4().hex+'.enc'
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce=secrets.token_bytes(12)
        encrypted=AESGCM(key).encrypt(nonce,content,f'trustshare:vault-file:{user.id}:{stored}'.encode())
        sealed_name=_vault_seal_name(key,user.id,stored,original)
        dest=STORAGE/stored; dest.write_bytes(encrypted)
        row=VaultFile(user_id=user.id,stored_name=stored,sealed_name=sealed_name,nonce=base64.b64encode(nonce).decode(),content_type=file.content_type or 'application/octet-stream',size=len(content))
        db.add(row); db.commit(); db.refresh(row)
    except Exception:
        if 'dest' in locals() and dest.exists(): dest.unlink()
        db.rollback(); raise
    finally: file.file.close()
    log_event('vault_file_uploaded',user.id,{'vault_file_id':row.id,'size':len(content)})
    return {'id':row.id,'name':original,'size':len(content),'created_at':row.created_at.isoformat()}

@app.get('/api/vault/files/{vault_file_id}/download')
def vault_download(vault_file_id:int,x_vault_password:str=Header(...),user:User=Depends(current_user),db:Session=Depends(get_db)):
    key=_vault_key(user,x_vault_password,db)
    row=db.scalar(select(VaultFile).where(VaultFile.id==vault_file_id,VaultFile.user_id==user.id))
    if not row: raise HTTPException(404,'Vault file not found')
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    try:
        encrypted=(STORAGE/row.stored_name).read_bytes()
        content=AESGCM(key).decrypt(base64.b64decode(row.nonce),encrypted,f'trustshare:vault-file:{user.id}:{row.stored_name}'.encode())
        name=_vault_open_name(key,user.id,row.stored_name,row.sealed_name)
    except Exception:
        log_event('vault_decryption_failed',user.id,{'vault_file_id':vault_file_id,'severity':'high'})
        raise HTTPException(500,'Vault file could not be decrypted')
    log_event('vault_file_downloaded',user.id,{'vault_file_id':vault_file_id})
    return Response(content=content,media_type=row.content_type,headers={'Content-Disposition':f'attachment; filename="{name}"','Cache-Control':'no-store'})

@app.delete('/api/vault/files/{vault_file_id}')
def vault_delete(vault_file_id:int,x_vault_password:str=Header(...),user:User=Depends(current_user),db:Session=Depends(get_db)):
    _vault_key(user,x_vault_password,db)
    row=db.scalar(select(VaultFile).where(VaultFile.id==vault_file_id,VaultFile.user_id==user.id))
    if not row: raise HTTPException(404,'Vault file not found')
    path=STORAGE/row.stored_name
    if path.exists(): path.unlink()
    db.delete(row); db.commit(); log_event('vault_file_deleted',user.id,{'vault_file_id':vault_file_id})
    return {'message':'Vault file permanently deleted'}

@app.post('/api/vault/change-password')
def vault_change_password(data:VaultPasswordChangeIn,x_vault_password:str=Header(...),user:User=Depends(current_user),db:Session=Depends(get_db)):
    old_key=_vault_key(user,x_vault_password,db)
    if bcrypt.checkpw(data.new_password.encode(),user.password_hash.encode()): raise HTTPException(422,'Vault password must differ from account password')
    rows=db.scalars(select(VaultFile).where(VaultFile.user_id==user.id)).all()
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    vault=db.scalar(select(Vault).where(Vault.user_id==user.id))
    new_salt=secrets.token_bytes(16)
    new_key=hashlib.scrypt(data.new_password.encode(),salt=new_salt,n=2**15,r=8,p=1,dklen=32)
    staged=[]
    for row in rows:
        old_cipher=(STORAGE/row.stored_name).read_bytes()
        plain=AESGCM(old_key).decrypt(base64.b64decode(row.nonce),old_cipher,f'trustshare:vault-file:{user.id}:{row.stored_name}'.encode())
        nonce=secrets.token_bytes(12)
        encrypted=AESGCM(new_key).encrypt(nonce,plain,f'trustshare:vault-file:{user.id}:{row.stored_name}'.encode())
        old_name=_vault_open_name(old_key,user.id,row.stored_name,row.sealed_name)
        staged.append((row,encrypted,base64.b64encode(nonce).decode(),_vault_seal_name(new_key,user.id,row.stored_name,old_name)))
    for row,encrypted,nonce,sealed_name in staged:
        (STORAGE/row.stored_name).write_bytes(encrypted)
        row.nonce=nonce; row.sealed_name=sealed_name
    vault.salt=base64.b64encode(new_salt).decode(); vault.verifier=hmac.new(new_key,b'trustshare-vault-verifier',hashlib.sha256).hexdigest()
    db.commit(); log_event('vault_password_changed',user.id,{'file_count':len(rows)})
    return {'message':'Vault password changed'}

@app.post('/api/vault/reset')
def vault_reset(data:ConfirmAccountPasswordIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if not bcrypt.checkpw(data.password.encode(),user.password_hash.encode()): raise HTTPException(401,'Account password confirmation failed')
    rows=db.scalars(select(VaultFile).where(VaultFile.user_id==user.id)).all()
    for row in rows:
        path=STORAGE/row.stored_name
        if path.exists(): path.unlink()
        db.delete(row)
    vault=db.scalar(select(Vault).where(Vault.user_id==user.id))
    if vault: db.delete(vault)
    db.commit(); log_event('vault_reset',user.id,{'deleted_files':len(rows),'severity':'high'})
    return {'message':'Vault reset; encrypted files were permanently deleted.'}
