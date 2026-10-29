"""Utilidades de seguridad Nivel 11X: KDF con sal, JWT, CSRF HMAC, Anti-SSRF, Anti-CSWSH y cuotas de archivos."""

import hashlib
import hmac
import ipaddress
import os
import secrets
import socket
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Protocol
from urllib.parse import urlparse

import jwt
from fastapi import HTTPException, status

SECRET_KEY = os.getenv("SECRET_KEY", "qa-blueprint-11x-secret-key-super-secure-32bytes")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
PBKDF2_ITERATIONS = 100_000
MAX_UPLOAD_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB (Patrón 6 Anti-DoS / OOM)
UPLOAD_CHUNK_SIZE = 64 * 1024  # 64 KB

FORBIDDEN_CONTAINER_HOSTS = frozenset(
    {
        "localhost",
        "api",
        "postgres",
        "keydb",
        "redis",
        "worker",
        "minio",
        "condominio_backend_api",
        "condominio_backend_redis",
        "condominio_backend_postgres",
    }
)


class AsyncChunkReader(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


def _pbkdf2_digest(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()


def get_password_hash(password: str) -> str:
    """Genera un hash PBKDF2-HMAC-SHA256 con sal criptográfica aleatoria."""
    salt = secrets.token_hex(16)
    digest = _pbkdf2_digest(password, salt)
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica la contraseña en tiempo constante (hmac.compare_digest)."""
    if hashed_password.startswith("pbkdf2_sha256$"):
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        _, salt, expected_digest = parts
        computed = _pbkdf2_digest(plain_password, salt)
        return hmac.compare_digest(computed, expected_digest)
    legacy_digest = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy_digest, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    delta = expires_delta if expires_delta is not None else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + delta
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return str(encoded_jwt)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica y valida la firma y expiración del token JWT."""
    payload: dict[str, Any] = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload


def generate_csrf_token(session_id: str) -> str:
    """Genera un token CSRF firmado con HMAC-SHA256 (Patrón 8)."""
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        session_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def validate_csrf_token(token: str, session_id: str) -> bool:
    """Valida un token CSRF en tiempo constante (Patrón 8)."""
    if not token or not session_id:
        return False
    expected = generate_csrf_token(session_id)
    return hmac.compare_digest(token, expected)


def _is_forbidden_ip(ip_addr_str: str) -> bool:
    ip = ipaddress.ip_address(ip_addr_str)
    return bool(
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified
    )


def _resolve_and_validate_ips(hostname: str) -> None:
    try:
        resolved_items = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"No se pudo resolver el host: {hostname}") from exc

    for item in resolved_items:
        ip_str = str(item[4][0])
        if _is_forbidden_ip(ip_str):
            raise ValueError(f"Destino prohibido en red privada o reservada ({ip_str})")


def validate_safe_outgoing_url(url_str: str) -> str:
    """Defensa Anti-SSRF estricta con resolución DNS previa (Patrón 4)."""
    parsed = urlparse(url_str.strip())
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Esquema no permitido: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL sin hostname válido")

    if hostname.lower() in FORBIDDEN_CONTAINER_HOSTS:
        raise ValueError("Acceso prohibido a recursos internos de infraestructura")

    _resolve_and_validate_ips(hostname)
    return url_str.strip()


async def read_uploaded_file_safely(
    file: AsyncChunkReader,
    max_bytes: int = MAX_UPLOAD_SIZE_BYTES,
) -> bytes:
    """Lee un archivo en streaming aplicando cuota estricta Anti-DoS/OOM (Patrón 6)."""
    total_bytes = 0
    buffer = bytearray()

    while chunk := await file.read(UPLOAD_CHUNK_SIZE):
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="El archivo excede el tamaño máximo permitido de 2 MB.",
            )
        buffer.extend(chunk)

    return bytes(buffer)


def verify_websocket_origin(origin: str | None, allowed_origins: set[str] | None = None) -> bool:
    """Protección Anti-CSWSH validando cabecera Origin antes de aceptar WebSocket (Patrón 2)."""
    if not origin:
        return os.getenv("APP_ENV", "development") != "production"
    whitelist = allowed_origins
    if whitelist is None:
        raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080,http://localhost:5173")
        whitelist = {item.strip() for item in raw.split(",") if item.strip()}
    return origin in whitelist
