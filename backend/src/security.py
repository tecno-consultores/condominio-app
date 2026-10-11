import os
import hashlib
from datetime import datetime, timedelta

# PyJWT se requiere para la generación estándar de tokens
try:
    import jwt
except ImportError:
    # Fallback temporal si no se encuentra PyJWT, pero en QA Nivel 11X fallaría
    pass

SECRET_KEY = os.getenv("SECRET_KEY", "qa-blueprint-11x-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def get_password_hash(password: str) -> str:
    """Implementación básica de hashing para QA. 
    En producción real integraríamos passlib con bcrypt."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_password_hash(plain_password) == hashed_password

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire.timestamp()})
    # Asume que PyJWT está instalado en el entorno
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
