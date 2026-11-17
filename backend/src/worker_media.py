"""Procesamiento multimedia AVIF y carga autenticada AWS SigV4 a MinIO/S3 (Hito 21)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import UTC, datetime
from io import BytesIO
from typing import Any
from urllib.parse import parse_qsl, quote, unquote, urlparse

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_PIXELS = 16_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def env_flag(name: str, default: bool = False) -> bool:
    """Evalúa una variable de entorno booleana con valor por defecto."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def normalize_minio_endpoint(endpoint: str, use_ssl: bool) -> str:
    """Normaliza el endpoint MinIO aplicando esquema HTTPS cuando MINIO_USE_SSL está activo."""
    cleaned = endpoint.strip().rstrip("/")
    if not cleaned or cleaned.startswith("s3://"):
        return cleaned
    if cleaned.startswith("http://"):
        return f"https://{cleaned[7:]}" if use_ssl else cleaned
    if cleaned.startswith("https://"):
        return cleaned
    scheme = "https" if use_ssl else "http"
    return f"{scheme}://{cleaned}"


def _hmac_sha256(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def _signing_key_sigv4(secret_key: str, date_stamp: str, region: str, service: str) -> bytes:
    k_date = _hmac_sha256(f"AWS4{secret_key}".encode("utf-8"), date_stamp)
    k_region = _hmac_sha256(k_date, region)
    k_service = _hmac_sha256(k_region, service)
    return _hmac_sha256(k_service, "aws4_request")


def _encode_sigv4_uri(raw_path: str) -> str:
    return quote(unquote(raw_path), safe="/-_.~")


def _encode_sigv4_query(raw_query: str) -> str:
    if not raw_query:
        return ""
    pairs = [(quote(k, safe="-_.~"), quote(v, safe="-_.~")) for k, v in parse_qsl(raw_query, keep_blank_values=True)]
    pairs.sort()
    return "&".join(f"{k}={v}" for k, v in pairs)


def _build_sigv4_headers(
    host: str,
    canonical_uri: str,
    payload_hash: str,
    access_key: str,
    secret_key: str,
    region: str = "us-east-1",
    *,
    canonical_query: str = "",
    content_type: str = "image/avif",
) -> dict[str, str]:
    now_utc = datetime.now(UTC)
    amz_date = now_utc.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now_utc.strftime("%Y%m%d")
    encoded_uri = _encode_sigv4_uri(canonical_uri)
    canonical_headers = f"host:{host}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amz_date}\n"
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = f"PUT\n{encoded_uri}\n{canonical_query}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
    request_digest = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = f"AWS4-HMAC-SHA256\n{amz_date}\n{credential_scope}\n{request_digest}"
    signing_key = _signing_key_sigv4(secret_key, date_stamp, region, "s3")
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return {
        "Host": host,
        "Content-Type": content_type,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
        "Authorization": authorization,
    }


def codificar_imagen_avif(contenido: bytes, *, strict_image: bool = False) -> bytes:
    """Transcodifica bytes de imagen a formato AVIF corrigiendo orientación EXIF y bloqueando bombardeo de píxeles."""
    if not contenido:
        raise ValueError("El archivo de imagen no puede estar vacío.")
    try:
        with Image.open(BytesIO(contenido)) as img:
            normalized = ImageOps.exif_transpose(img).convert("RGB")
            salida = BytesIO()
            normalized.save(salida, format="AVIF", quality=60)
            return salida.getvalue()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        if strict_image:
            raise ValueError("Contenido de imagen inválido para conversión AVIF.") from exc
        return contenido


def resolver_bucket_minio(bucket_name: str | None = None) -> str:
    """Resuelve el nombre del bucket S3/MinIO configurado."""
    raw_bucket = (
        bucket_name
        if bucket_name is not None and bucket_name.strip()
        else (os.getenv("MINIO_BUCKET_NAME") or os.getenv("MINIO_BUCKET") or "condominio-media")
    )
    return raw_bucket.strip() or "condominio-media"


def construir_clave_evidencia(contenido: bytes, prefijo: str, mime_origen: str) -> tuple[str, str]:
    """Calcula la ruta determinista S3 y MIME final para una evidencia subida."""
    ext = "pdf" if mime_origen == "application/pdf" else "avif"
    destino_mime = "application/pdf" if ext == "pdf" else "image/avif"
    digest = hashlib.sha256(contenido).hexdigest()[:24]
    ruta_limpia = prefijo.strip("/") or "general"
    return f"{ruta_limpia}/{digest}.{ext}", destino_mime


def subir_objeto_minio_s3(
    datos_binarios: bytes,
    objeto_key: str,
    minio_endpoint: str,
    *,
    bucket_name: str | None = None,
    http_client: httpx.Client | None = None,
    content_type: str = "image/avif",
) -> str:
    """Sube bytes a MinIO mediante HTTP PUT autenticado con AWS SigV4 (RFC 3986)."""
    access_key = os.getenv("MINIO_ROOT_USER", "").strip()
    secret_key = os.getenv("MINIO_ROOT_PASSWORD", "")
    if not access_key or not secret_key:
        raise ValueError("Credenciales MinIO no configuradas para carga S3.")

    bucket = resolver_bucket_minio(bucket_name)
    base_url = minio_endpoint.rstrip("/")
    parsed = urlparse(base_url)
    base_path = parsed.path.rstrip("/")
    canonical_uri = _encode_sigv4_uri(f"{base_path}/{bucket}/{objeto_key}")
    canonical_query = _encode_sigv4_query(parsed.query)
    origin_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else base_url
    upload_url = f"{origin_url}{canonical_uri}" + (f"?{canonical_query}" if canonical_query else "")
    payload_hash = hashlib.sha256(datos_binarios).hexdigest()
    headers = _build_sigv4_headers(
        parsed.netloc,
        canonical_uri,
        payload_hash,
        access_key,
        secret_key,
        canonical_query=canonical_query,
        content_type=content_type,
    )

    if http_client is not None:
        resp = http_client.put(upload_url, content=datos_binarios, headers=headers, timeout=15.0)
        resp.raise_for_status()
    else:
        with httpx.Client(timeout=15.0) as client:
            resp = client.put(upload_url, content=datos_binarios, headers=headers)
            resp.raise_for_status()
    return f"s3://{bucket}/{objeto_key}"


def convertir_y_subir_avif(
    contenido: bytes,
    prefijo: str,
    minio_endpoint: str = "s3://condominio-media",
    *,
    strict_image: bool = False,
    http_client: httpx.Client | None = None,
    minio_use_ssl: bool | None = None,
    objeto_key_override: str | None = None,
) -> str:
    """Convierte el binario recibido a formato AVIF y lo carga en MinIO si hay endpoint HTTP(S)."""
    datos_avif = codificar_imagen_avif(contenido, strict_image=strict_image)
    digest = hashlib.sha256(datos_avif).hexdigest()[:24]
    ruta_limpia = prefijo.strip("/") or "general"
    objeto_key = objeto_key_override.strip("/") if objeto_key_override else f"{ruta_limpia}/{digest}.avif"
    use_ssl = env_flag("MINIO_USE_SSL", False) if minio_use_ssl is None else minio_use_ssl
    base_limpia = normalize_minio_endpoint(minio_endpoint, use_ssl)
    if base_limpia.startswith(("http://", "https://")):
        return subir_objeto_minio_s3(datos_avif, objeto_key, base_limpia, http_client=http_client)
    return f"{base_limpia}/{objeto_key}"


def ejecutar_subida_media_bytes(evento: dict[str, Any], minio_endpoint: str, minio_use_ssl: bool) -> str:
    """Decodifica payload multimedia base64 y ejecuta subida PDF directa o transcodificación AVIF."""
    raw_b64 = evento.get("content_base64")
    if not isinstance(raw_b64, str) or not raw_b64:
        raise ValueError("Tarea media sin contenido base64.")
    raw_bytes = base64.b64decode(raw_b64, validate=True)
    mime_origen = str(evento.get("mime_origen") or "")
    prefijo = str(evento.get("prefijo") or "general")
    objeto_key = str(evento.get("objeto_key") or "").strip("/")
    endpoint = minio_endpoint or "s3://condominio-media"
    if mime_origen == "application/pdf":
        base_limpia = normalize_minio_endpoint(endpoint, minio_use_ssl)
        if base_limpia.startswith(("http://", "https://")):
            return subir_objeto_minio_s3(raw_bytes, objeto_key, base_limpia, content_type="application/pdf")
        return f"{base_limpia}/{objeto_key}"
    return convertir_y_subir_avif(
        raw_bytes,
        prefijo,
        minio_endpoint=endpoint,
        strict_image=True,
        minio_use_ssl=minio_use_ssl,
        objeto_key_override=objeto_key or None,
    )
