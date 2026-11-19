"""Utilidades de seguridad Nivel 11X: HKDF-SHA256, KDF con sal, JWT, CSRF HMAC, Anti-SSRF, Anti-CSWSH y cuotas."""

import asyncio
import hashlib
import hmac
import ipaddress
import os
import secrets
import socket
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from urllib.parse import urlparse, urlunparse

import jwt
from fastapi import HTTPException, status

# Valor centinela solo para desarrollo/QA efímero; rechazado en Fail-Fast para APP_ENV=production.
_FALLBACK_DEV_SENTINEL = "qa-blueprint-11x-secret-key-super-secure-32bytes"
DEFAULT_INSECURE_SECRET_KEY = _FALLBACK_DEV_SENTINEL
SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_INSECURE_SECRET_KEY)
ALGORITHM = "HS256"
JWT_ISSUER = "condominio-app"
JWT_AUDIENCE = "condominio-app-client"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
PBKDF2_ITERATIONS = 600_000
MAX_UPLOAD_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB (Patrón 6 Anti-DoS / OOM)
UPLOAD_CHUNK_SIZE = 64 * 1024  # 64 KB
_HKDF_SALT = b"condominio-app-hkdf-v1"


def _get_secret_key() -> str:
    """Resuelve dinámicamente la clave HMAC/JWT vigente."""
    return os.getenv("SECRET_KEY") or SECRET_KEY


def _hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    return hmac.new(salt, ikm, hashlib.sha256).digest()


def _hkdf_expand(prk: bytes, info: bytes, length: int = 32) -> bytes:
    okm = bytearray()
    block = b""
    counter = 1
    while len(okm) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        okm.extend(block)
        counter += 1
    return bytes(okm[:length])


def derive_subkey(purpose: str, master_secret: str | None = None) -> str:
    """Deriva una subclave criptográfica independiente de 256 bits vía HKDF-SHA256 (RFC 5869)."""
    ikm = (master_secret if master_secret is not None else _get_secret_key()).encode("utf-8")
    prk = _hkdf_extract(_HKDF_SALT, ikm)
    return _hkdf_expand(prk, purpose.encode("utf-8"), 32).hex()


def get_solvency_signing_key() -> str:
    """Subclave HKDF-SHA256 exclusiva para certificados de solvencia."""
    return derive_subkey("solvency-hmac")


def get_vote_signing_key() -> str:
    """Subclave HKDF-SHA256 exclusiva para votos e IP-hash de consultas."""
    return derive_subkey("vote-hmac")


def get_qr_signing_key() -> str:
    """Subclave HKDF-SHA256 exclusiva para tokens QR de acceso."""
    return derive_subkey("qr-pass-hmac")


def get_worm_signing_key(master_secret: str | None = None) -> str:
    """Subclave HKDF-SHA256 exclusiva para encadenamiento WORM de auditoría."""
    return derive_subkey("worm-audit-hmac", master_secret=master_secret)


def compute_worm_record_hash(prev_hash: str, payload: str, master_secret: str | None = None) -> str:
    """Calcula el sello HMAC-SHA256 encadenado para registros WORM inmutables."""
    key = get_worm_signing_key(master_secret=master_secret).encode("utf-8")
    return hmac.new(key, f"{prev_hash}|{payload}".encode("utf-8"), hashlib.sha256).hexdigest()


def should_use_secure_cookie() -> bool:
    """Determina si las cookies de sesión deben marcarse con Secure=True."""
    explicit = os.getenv("COOKIE_SECURE")
    if explicit is not None:
        return explicit.strip().lower() == "true"
    return os.getenv("APP_ENV", "development").strip().lower() == "production"


def is_csrf_enforced() -> bool:
    """Indica si se exige validación real de X-CSRF-Token para mutaciones con cookie."""
    is_prod = os.getenv("APP_ENV", "development").strip().lower() == "production"
    explicit = os.getenv("CSRF_ENFORCE", "false").strip().lower() == "true"
    return is_prod or explicit


def _validate_production_secret() -> None:
    secret = _get_secret_key().strip()
    if not secret or secret == DEFAULT_INSECURE_SECRET_KEY or len(secret) < 32:
        raise RuntimeError(
            "Configuración insegura en APP_ENV=production: defina SECRET_KEY criptográfica (>= 32 caracteres)."
        )


def _validate_production_db_url() -> None:
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url or ":memory:" in db_url:
        raise RuntimeError(
            "Configuración insegura en APP_ENV=production: DATABASE_URL no puede estar vacía ni usar SQLite :memory:."
        )


def validate_production_security_settings() -> None:
    """Falla de inmediato (Fail-Fast) si producción usa secretos por defecto o DB en memoria."""
    if os.getenv("APP_ENV", "development").strip().lower() != "production":
        return
    _validate_production_secret()
    _validate_production_db_url()


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


# Hash ficticio calculado al importar para mitigar enumeración temporal en /login
DUMMY_PASSWORD_HASH = get_password_hash(secrets.token_hex(16))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica la contraseña PBKDF2-HMAC-SHA256 en tiempo constante (hmac.compare_digest)."""
    if hashed_password.startswith("pbkdf2_sha256$"):
        parts = hashed_password.split("$")
        if len(parts) == 3:
            _, salt, expected_digest = parts
            computed = _pbkdf2_digest(plain_password, salt)
            return hmac.compare_digest(computed, expected_digest)
    # Cómputo ficticio constante para mitigar enumeración temporal ante hashes inválidos o legacy
    _pbkdf2_digest(plain_password, "0" * 32)
    return False


async def get_password_hash_async(password: str) -> str:
    """Calcula PBKDF2-HMAC-SHA256 sin bloquear el event loop."""
    return await asyncio.to_thread(get_password_hash, password)


async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    """Verifica PBKDF2-HMAC-SHA256 en hilo separado manteniendo tiempo constante."""
    return await asyncio.to_thread(verify_password, plain_password, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Emite un JWT de acceso (typ=access, iss, aud, iat, exp) firmado con subclave HKDF."""
    to_encode = data.copy()
    now = datetime.now(UTC)
    delta = expires_delta if expires_delta is not None else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = now + delta
    to_encode.update(
        {
            "typ": "access",
            "iat": int(now.timestamp()),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "exp": int(expire.timestamp()),
        }
    )
    encoded_jwt = jwt.encode(to_encode, derive_subkey("jwt-access"), algorithm=ALGORITHM)
    return str(encoded_jwt)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica y valida firma HKDF, claims estándar (iss/aud/iat/exp) y typ=access."""
    payload: dict[str, Any] = jwt.decode(
        token,
        derive_subkey("jwt-access"),
        algorithms=[ALGORITHM],
        issuer=JWT_ISSUER,
        audience=JWT_AUDIENCE,
        options={"require": ["exp", "iat", "iss", "aud"]},
    )
    if payload.get("typ") != "access":
        raise jwt.InvalidTokenError("Tipo de token inválido para acceso.")
    return payload


def create_refresh_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Emite un JWT de renovación (typ=refresh) con JTI único y subclave HKDF independiente."""
    to_encode = data.copy()
    now = datetime.now(UTC)
    delta = expires_delta if expires_delta is not None else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    expire = now + delta
    to_encode.update(
        {
            "typ": "refresh",
            "jti": str(to_encode.get("jti") or secrets.token_urlsafe(16)),
            "iat": int(now.timestamp()),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "exp": int(expire.timestamp()),
        }
    )
    return str(jwt.encode(to_encode, derive_subkey("jwt-refresh"), algorithm=ALGORITHM))


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decodifica y valida firma HKDF, expiración, claims y tipo explícito refresh."""
    payload: dict[str, Any] = jwt.decode(
        token,
        derive_subkey("jwt-refresh"),
        algorithms=[ALGORITHM],
        issuer=JWT_ISSUER,
        audience=JWT_AUDIENCE,
        options={"require": ["exp", "iat", "iss", "aud", "jti"]},
    )
    if payload.get("typ") != "refresh":
        raise jwt.InvalidTokenError("Tipo de token inválido para renovación.")
    return payload


def decode_token_unverified_exp(token: str) -> dict[str, Any] | None:
    """Verifica firma HKDF de access o refresh ignorando exp para leer sid/jti al cerrar/refrescar sesión."""
    for purpose, expected_typ in (("jwt-access", "access"), ("jwt-refresh", "refresh")):
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                derive_subkey(purpose),
                algorithms=[ALGORITHM],
                issuer=JWT_ISSUER,
                audience=JWT_AUDIENCE,
                options={"verify_exp": False, "require": ["exp", "iat", "iss", "aud"]},
            )
            if payload.get("typ") == expected_typ:
                return payload
        except jwt.InvalidTokenError:
            continue
    return None


def generate_csrf_token(session_id: str) -> str:
    """Genera un token CSRF firmado con subclave HKDF y HMAC-SHA256 (Patrón 8)."""
    return hmac.new(
        derive_subkey("csrf-hmac").encode("utf-8"),
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
    return any((ip.is_private, ip.is_loopback, ip.is_link_local, ip.is_multicast, ip.is_reserved, ip.is_unspecified))


_DEFAULT_TRUSTED_PROXY_CIDRS: tuple[str, ...] = (
    "127.0.0.1/32",
    "::1/128",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
)


def _host_matches_network(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address, entry: str) -> bool:
    try:
        if "/" in entry:
            return ip_obj in ipaddress.ip_network(entry, strict=False)
        return ip_obj == ipaddress.ip_address(entry)
    except ValueError:
        return False


def _resolve_trusted_proxy_entries(clean_host: str) -> tuple[bool, tuple[str, ...]]:
    raw_cfg = os.getenv("TRUSTED_PROXY_IPS", "").strip()
    if not raw_cfg:
        is_dev_testclient = (
            clean_host == "testclient" and os.getenv("APP_ENV", "development").strip().lower() != "production"
        )
        return is_dev_testclient, _DEFAULT_TRUSTED_PROXY_CIDRS
    entries = tuple(item.strip() for item in raw_cfg.split(",") if item.strip())
    return clean_host in entries, entries


def _ip_in_trusted_entries(clean_host: str, entries: tuple[str, ...]) -> bool:
    try:
        ip_obj = ipaddress.ip_address(clean_host)
    except ValueError:
        return False
    return any(_host_matches_network(ip_obj, entry) for entry in entries)


def is_trusted_proxy_ip(client_host: str | None) -> bool:
    """Determina si la IP directa del socket pertenece a un proxy inverso confiable."""
    clean_host = (client_host or "").strip()
    if not clean_host:
        return False
    direct_match, entries = _resolve_trusted_proxy_entries(clean_host)
    return direct_match or _ip_in_trusted_entries(clean_host, entries)


def _resolve_and_validate_ips(hostname: str) -> None:
    try:
        resolved_items = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"No se pudo resolver el host: {hostname}") from exc

    for item in resolved_items:
        ip_str = str(item[4][0])
        if _is_forbidden_ip(ip_str):
            raise ValueError(f"Destino prohibido en red privada o reservada ({ip_str})")


def _normalizar_url_saliente(url_str: str) -> tuple[str, str]:
    clean_url = url_str.strip()
    parsed = urlparse(clean_url)
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"Esquema no permitido: {scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL sin hostname válido")

    host_lower = hostname.lower()
    if host_lower in FORBIDDEN_CONTAINER_HOSTS or host_lower.endswith((".local", ".internal")):
        raise ValueError("Acceso prohibido a recursos internos de infraestructura")

    normalized_url = urlunparse(parsed._replace(scheme=scheme, netloc=parsed.netloc.lower()))
    return normalized_url, host_lower


def validate_safe_outgoing_url(url_str: str) -> str:
    """Defensa Anti-SSRF estricta con resolución DNS previa (Patrón 4)."""
    normalized_url, host_lower = _normalizar_url_saliente(url_str)
    _resolve_and_validate_ips(host_lower)
    return normalized_url


async def validate_safe_outgoing_url_async(url_str: str) -> str:
    """Versión asíncrona Anti-SSRF sin bloqueo del event loop y con normalización de esquema/host."""
    normalized_url, host_lower = _normalizar_url_saliente(url_str)
    await asyncio.to_thread(_resolve_and_validate_ips, host_lower)
    return normalized_url


_MAGIC_PREFIX_MIMES: tuple[tuple[bytes | tuple[bytes, ...], str], ...] = (
    (b"%PDF-", "application/pdf"),
    ((b"\x89PNG\r\n\x1a\n", b"\x89PNG"), "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
)
_AVIF_BRANDS = (b"ftypavif", b"ftypavis", b"ftypmif1")


def _detect_container_mime(sample: bytes) -> str | None:
    if len(sample) < 12:
        return None
    if (sample[:4], sample[8:12]) == (b"RIFF", b"WEBP"):
        return "image/webp"
    if sample[4:12] in _AVIF_BRANDS:
        return "image/avif"
    return None


def validate_file_magic_bytes(header: bytes) -> str:
    """Inspecciona los primeros 16 bytes binarios del archivo para prevenir falsificación de MIME Type (Patrón 15)."""
    sample = header[:16]
    for prefixes, mime in _MAGIC_PREFIX_MIMES:
        if sample.startswith(prefixes):
            return mime
    container_mime = _detect_container_mime(sample)
    if container_mime:
        return container_mime
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Formato binario de archivo no permitido (Magic Bytes inválidos).",
    )


async def read_uploaded_file_safely(
    file: AsyncChunkReader,
    max_bytes: int = MAX_UPLOAD_SIZE_BYTES,
    verify_magic_bytes: bool = False,
) -> bytes:
    """Lee un archivo en streaming aplicando cuota estricta Anti-DoS/OOM (Patrón 6) y Magic Bytes (Patrón 15)."""
    total_bytes = 0
    buffer = bytearray()

    while chunk := await file.read(UPLOAD_CHUNK_SIZE):
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="El archivo excede el tamaño máximo permitido de 2 MB.",
            )
        buffer.extend(chunk)

    if verify_magic_bytes:
        validate_file_magic_bytes(bytes(buffer[:16]))

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
