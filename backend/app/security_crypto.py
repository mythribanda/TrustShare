import base64
import json
import os
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC=b"TSE2"
CHUNK_SIZE=1024*1024

def _keyring():
    raw=os.getenv("MASTER_KEYS","").strip()
    keys={}
    if raw:
        for item in raw.split(","):
            version,key=item.split(":",1)
            decoded=base64.b64decode(key,validate=True)
            if len(decoded)!=32:
                raise RuntimeError("Every MASTER_KEYS value must decode to 32 bytes")
            keys[int(version)]=decoded
    else:
        raw=os.getenv("ENCRYPTION_MASTER_KEY","").strip()
        if not raw or raw.startswith("replace-with-"):
            raise RuntimeError("Configure ENCRYPTION_MASTER_KEY or MASTER_KEYS in the backend environment")
        decoded=base64.b64decode(raw,validate=True)
        if len(decoded)!=32:
            raise RuntimeError("ENCRYPTION_MASTER_KEY must decode to exactly 32 bytes")
        keys[1]=decoded
    return keys

def encrypt_bytes(plaintext:bytes,file_context:str):
    keys=_keyring()
    version=int(os.getenv("ACTIVE_MASTER_KEY_VERSION",str(max(keys))))
    if version not in keys:
        raise RuntimeError("Active master-key version is not present in MASTER_KEYS")
    dek=AESGCM.generate_key(bit_length=256)
    prefix=secrets.token_bytes(8)
    count=(len(plaintext)+CHUNK_SIZE-1)//CHUNK_SIZE
    header=MAGIC+CHUNK_SIZE.to_bytes(4,"big")+prefix+count.to_bytes(4,"big")
    chunks=[]
    cipher=AESGCM(dek)
    context=file_context.encode()
    for index,start in enumerate(range(0,len(plaintext),CHUNK_SIZE)):
        plain=plaintext[start:start+CHUNK_SIZE]
        final=index==count-1
        nonce=prefix+index.to_bytes(4,"big")
        aad=context+index.to_bytes(4,"big")+(b"\x01" if final else b"\x00")
        encrypted=cipher.encrypt(nonce,plain,aad)
        chunks.append(len(encrypted).to_bytes(4,"big")+encrypted)
    wrap_nonce=secrets.token_bytes(12)
    wrap_aad=context+version.to_bytes(4,"big")
    wrapped=AESGCM(keys[version]).encrypt(wrap_nonce,dek,wrap_aad)
    return header+b"".join(chunks),base64.b64encode(wrapped).decode(),base64.b64encode(wrap_nonce).decode(),version

def decrypt_bytes(blob:bytes,file_context:str,wrapped_key:str,wrap_nonce:str,key_version:int):
    keys=_keyring()
    if key_version not in keys:
        raise ValueError("Master-key version is unavailable")
    if len(blob)<20 or blob[:4]!=MAGIC:
        raise ValueError("Encrypted file header is invalid")
    chunk_size=int.from_bytes(blob[4:8],"big")
    prefix=blob[8:16]
    count=int.from_bytes(blob[16:20],"big")
    if chunk_size!=CHUNK_SIZE or count>100000:
        raise ValueError("Encrypted file header is invalid")
    context=file_context.encode()
    dek=AESGCM(keys[key_version]).decrypt(base64.b64decode(wrap_nonce),base64.b64decode(wrapped_key),context+key_version.to_bytes(4,"big"))
    cipher=AESGCM(dek)
    pos=20
    plaintext=[]
    for index in range(count):
        if pos+4>len(blob):
            raise ValueError("Encrypted file is truncated")
        size=int.from_bytes(blob[pos:pos+4],"big")
        pos+=4
        if size<16 or pos+size>len(blob):
            raise ValueError("Encrypted file is truncated")
        encrypted=blob[pos:pos+size]
        pos+=size
        final=index==count-1
        aad=context+index.to_bytes(4,"big")+(b"\x01" if final else b"\x00")
        plaintext.append(cipher.decrypt(prefix+index.to_bytes(4,"big"),encrypted,aad))
    if pos!=len(blob):
        raise ValueError("Encrypted file has trailing data")
    return b"".join(plaintext)


def encrypt_secret(value:str, context:str):
    keys=_keyring()
    version=int(os.getenv("ACTIVE_MASTER_KEY_VERSION",str(max(keys))))
    if version not in keys: raise RuntimeError("Active master-key version is not present in MASTER_KEYS")
    nonce=secrets.token_bytes(12)
    aad=(context+":"+str(version)).encode()
    encrypted=AESGCM(keys[version]).encrypt(nonce,value.encode(),aad)
    return base64.b64encode(encrypted).decode(),base64.b64encode(nonce).decode(),version

def decrypt_secret(encrypted:str, nonce:str, version:int, context:str):
    keys=_keyring()
    if version not in keys: raise ValueError("Master-key version is unavailable")
    aad=(context+":"+str(version)).encode()
    raw=AESGCM(keys[version]).decrypt(base64.b64decode(nonce),base64.b64decode(encrypted),aad)
    return raw.decode()


def rewrap_key(wrapped_key:str,wrap_nonce:str,old_version:int,file_context:str):
    keys=_keyring()
    if old_version not in keys:
        raise ValueError("Old master-key version is unavailable")
    active=int(os.getenv("ACTIVE_MASTER_KEY_VERSION",str(max(keys))))
    if active not in keys:
        raise ValueError("Active master-key version is unavailable")
    if active==old_version:
        return wrapped_key,wrap_nonce,old_version
    context=file_context.encode()
    dek=AESGCM(keys[old_version]).decrypt(
        base64.b64decode(wrap_nonce),
        base64.b64decode(wrapped_key),
        context+old_version.to_bytes(4,"big")
    )
    nonce=secrets.token_bytes(12)
    wrapped=AESGCM(keys[active]).encrypt(
        nonce,
        dek,
        context+active.to_bytes(4,"big")
    )
    return base64.b64encode(wrapped).decode(),base64.b64encode(nonce).decode(),active
