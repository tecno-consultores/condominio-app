# 🔐 Especificación 01: Arquitectura de Sistema y Seguridad Nivel 11X

**Estado:** Activo (Implementado en Backend / Obligatorio para Frontend)  
**Estándar:** QA Testing Blueprints Nivel 11X

---

## 1. Topología de Servicios en Contenedores

```mermaid
flowchart LR
    User["📱 Propietario / Junta (Mobile & Desktop)"] --> NPM["🛡️ Nginx / Proxy Reverso"]
    NPM -->|"/ (SPA Estática)"| UI["🟢 Frontend Vue 3 (Nginx Non-Root)"]
    NPM -->|"/api/* (REST)"| API["⚡ Backend FastAPI (Python 3.13)"]
    API --> PG[("🐘 PostgreSQL 17 (Alembic)")]
    API --> KDB[("⚡ KeyDB Multi-Hilo (Idempotencia & Colas)")]
    API --> MINIO[("🪣 MinIO S3 (URLs Firmadas / AVIF)")]
    KDB --> WORKER["⚙️ Worker Asíncrono (Conversión AVIF & Email)"]
    WORKER --> MINIO
    WORKER --> PG
```

---

## 2. Invariantes de Infraestructura y Persistencia

1. **Base de Datos Relacional (`PostgreSQL 17`):**
   - Esquema gestionado exclusivamente por migraciones versionadas en `backend/alembic/versions/`.
   - Verificación obligatoria sin mocks (`make -C backend qa-parity`) mediante `.agents/scripts/verify_alembic_orm_parity.py` y ejecución real de `alembic upgrade head && alembic downgrade base && alembic upgrade head`.
2. **Motor en Memoria (`KeyDB Multi-Hilo`):**
   - Imagen oficial `eqalpha/keydb:alpine` configurada con `--server-threads 2 --appendonly no --save "" --maxmemory 256mb --maxmemory-policy volatile-lru`.
   - 100% compatible con `redis.asyncio`, triplicando el rendimiento en bloqueos atómicos `SET NX EX` de `Idempotency-Key` y rotación de sesiones.
3. **Almacenamiento de Objetos (`MinIO` + Formato `AVIF`):**
   - Toda imagen subida (comprobantes de pago, facturas de egresos, evidencias de conserjería, fotos de voceros e incidencias) se procesa hacia formato **AVIF** con cuota máxima de entrada de **2 MB** (`HTTP 413`).

---

## 3. Contratos de Seguridad por Diseño (13 Vectores Mitigados)

| # | Vector de Ataque | Mitigación Técnica en Condominio App | Ubicación en Código |
| :--- | :--- | :--- | :--- |
| 1 | **Mass Assignment (Over-posting)** | `model_config = ConfigDict(extra="forbid")` en todos los esquemas de entrada. | `backend/src/schemas.py`, `backend/src/routers/auth.py` |
| 2 | **Cross-Site WebSocket Hijacking (CSWSH)** | Validación de cabecera `Origin` contra `ALLOWED_ORIGINS` antes de `ws.accept()`. | `backend/src/security.py` (`verify_websocket_origin`) |
| 3 | **Fuga de Esquemas en Errores 422** | Respuesta opaca genérica cuando `APP_ENV=production` y registro interno en logs. | `backend/src/main.py` (`validation_exception_handler`) |
| 4 | **Server-Side Request Forgery (SSRF)** | Resolución DNS previa y bloqueo de hosts internos y rangos RFC 1918 / loopback / link-local. | `backend/src/security.py` (`validate_safe_outgoing_url`) |
| 5 | **Inyección SQL** | Consultas parametrizadas tipadas con SQLAlchemy 2.0 (`select`, `where`). | `backend/src/routers/*.py` |
| 6 | **Denegación de Servicio por Subida (OOM)** | Lectura por chunks de 64 KB con corte en 2 MB (`HTTP 413`). | `backend/src/security.py` (`read_uploaded_file_safely`) |
| 7 | **Cabeceras HTTP Inseguras** | Middleware inyectando `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`. | `backend/src/main.py` (`security_headers_middleware`) |
| 8 | **CSRF y Autenticación Híbrida** | Tokens `HMAC-SHA256` (`generate_csrf_token`, `validate_csrf_token`) y soporte dual Cookie `HttpOnly` + `Authorization: Bearer`. | `backend/src/security.py`, `backend/src/dependencies.py` |
| 9 | **XSS y Prototype Pollution en SPA** | `escapeHtml()` y `sanitizeObject()` con `Object.create(null)` filtrando `__proto__`, `constructor`, `prototype`. | `frontend/src/utils/security.ts` |
| 10 | **Race Condition en Refresh Multi-Pestaña** | Ventana de cortesía (*grace period*) de 5s en KeyDB al rotar tokens. | `backend/src/redis_client.py` (`rotate_refresh_token_with_grace_period`) |
| 11 | **Colisión de Claves de Idempotencia** | Aislamiento por ámbito/usuario: `idemp:{scope}:{key}`. | `backend/src/redis_client.py` (`build_idempotency_key`) |
| 12 | **Exposición de OpenAPI en Producción** | `docs_url=None`, `redoc_url=None`, `openapi_url=None` si `APP_ENV=production`. | `backend/src/main.py` |
| 13 | **CVEs en Cadena de Suministro** | `uv.lock`, `pnpm-lock.yaml`, `.npmrc` (`ignore-scripts=true`), `uv audit` y Trivy (`auditar-infra.sh`). | `backend/Makefile`, `auditar-infra.sh` |
