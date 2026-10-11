import os
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt

SECRET_KEY = os.getenv("SECRET_KEY", "qa-blueprint-11x-secret-key-super-secure-32bytes")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def get_password_hash(password: str) -> str:
    """Implementación de hashing SHA-256 para validación"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_password_hash(plain_password) == hashed_password

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return str(encoded_jwt)

def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodifica y valida la firma y expiración del token JWT"""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
