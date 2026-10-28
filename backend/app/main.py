import os, uuid, shutil, hashlib, logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt
import redis
from app.security_crypto import encrypt_bytes, decrypt_bytes
from jose import jwt, JWTError
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
ALLOWED={'.pdf','.docx','.xlsx','.csv','.txt','.png','.jpg','.jpeg','.webp'}

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

@app.get('/health')
def health():
    return {
        'status':'ok',
        'database':db_backend,
        'postgres':'connected' if db_backend=='postgres' else 'fallback_sqlite',
        'mongodb':'connected' if mongo_available else 'unavailable',
        'redis':'connected' if cache else 'unavailable'
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
    return [file_dict(f) for f in db.scalars(stmt.order_by(StoredFile.uploaded_at.desc())).all()]

@app.get('/api/files/{file_id}/metadata')
def get_file_metadata(file_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    record=db.scalar(select(StoredFile).where(StoredFile.id==file_id))
    if not record: raise HTTPException(404,'File not found')
    if record.owner_id!=user.id and user.role!='admin':
        raise HTTPException(403,'Insufficient permissions to view file metadata')
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
        encrypted,wrapped_key,wrap_nonce,key_version=encrypt_bytes(b''.join(chunks),stored)
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
def download_file(file_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    record=db.scalar(select(StoredFile).where(StoredFile.id==file_id,StoredFile.owner_id==user.id))
    if not record: raise HTTPException(404,'File not found')
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
    log_event('file_downloaded',user.id,{'file_id':file_id})
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
    expires_in_hours:int=Field(default=24,ge=1,le=168)

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
