# 🔐 Guía de Desarrollo Seguro y Mitigación de Vulnerabilidades (Estándar 11X)

> **PROPÓSITO:**  
> Recetario técnico de los 13 patrones de código seguro implementados en **Condominio App** para proteger la integración entre la SPA (Vue 3) y la API Asíncrona (FastAPI).

---

## Catálogo de los 13 Patrones de Seguridad Implementados

1. **Patrón 1 — Prevención de Asignación Masiva (`extra="forbid"`):**
   - Todos los esquemas de entrada en `backend/src/schemas.py` y `LoginData` en `backend/src/routers/auth.py` configuran `model_config = ConfigDict(extra="forbid")`. Cualquier intento de inyectar `"rol": "TESORERO"` o `"es_activo": true` es rechazado con HTTP 422.
2. **Patrón 2 — Protección Anti-CSWSH en WebSockets (`verify_websocket_origin`):**
   - Implementada en `backend/src/security.py`. Valida la cabecera `Origin` contra la lista blanca `ALLOWED_ORIGINS` antes de aceptar conexiones en tiempo real.
3. **Patrón 3 — Sanitización de Errores 422 en Producción (`validation_exception_handler`):**
   - Implementada en `backend/src/main.py`. Cuando `APP_ENV=production`, devuelve `{"detail": "Los datos proporcionados no cumplen con los requisitos de validación."}` ocultando la estructura interna de validadores.
4. **Patrón 4 — Defensa Anti-SSRF Estricta con Resolución DNS Previa (`validate_safe_outgoing_url`):**
   - Implementada en `backend/src/security.py`. Bloquea esquemas no HTTP(S), hosts de contenedores (`localhost`, `api`, `postgres`, `keydb`, `redis`, `worker`, `minio`) y direcciones IP privadas RFC 1918, loopback o link-local (`169.254.169.254`).
5. **Patrón 5 — Consultas Parametrizadas Seguras en BD:**
   - Uso exclusivo de consultas parametrizadas de SQLAlchemy 2.0 (`select()`, `where()`), prohibiendo interpolación de cadenas SQL.
6. **Patrón 6 — Cuotas y Límites Estrictos de Carga de Archivos (`read_uploaded_file_safely`):**
   - Implementada en `backend/src/security.py`. Lee archivos en bloques de 64 KB y corta la lectura con HTTP `413 Request Entity Too Large` si supera **2 MB** (`MAX_UPLOAD_SIZE_BYTES`).
7. **Patrón 7 — Cabeceras Defensivas HTTP y Proxy Inverso:**
   - Middleware `security_headers_middleware` en `backend/src/main.py` inyectando `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` y `Referrer-Policy: strict-origin-when-cross-origin`.
8. **Patrón 8 — Tokens Anti-CSRF HMAC-SHA256 y Soporte Bearer M2M/MCP:**
   - `generate_csrf_token` y `validate_csrf_token` en `backend/src/security.py` con `hmac.compare_digest`, y `extract_bearer_or_cookie_token` en `backend/src/dependencies.py`.
9. **Patrón 9 — Prevención de XSS y Prototype Pollution en Frontend (`frontend/src/utils/security.ts`):**
   - `escapeHtml(value)` para sanitizar cadenas dinámicas y `sanitizeObject(input)` con `Object.create(null)` bloqueando `__proto__`, `constructor` y `prototype`.
10. **Patrón 10 — Tolerancia a Carreras Concurrentes (*Grace Period* de 5s) en Refresh Tokens:**
    - `rotate_refresh_token_with_grace_period` y `get_refresh_token_from_grace_period` en `backend/src/redis_client.py`.
11. **Patrón 11 — Aislamiento por Ámbito/Usuario en Llaves de Idempotencia (`build_idempotency_key`):**
    - `idemp:{scope}:{key}` en `backend/src/redis_client.py` (ej. `idemp:register:<uuid>` y `idemp:user:{id}:<uuid>`).
12. **Patrón 12 — Ocultación de Swagger / ReDoc / OpenAPI en Producción:**
    - En `backend/src/main.py`, `docs_url`, `redoc_url` y `openapi_url` se establecen en `None` cuando `APP_ENV=production`.
13. **Patrón 13 — Protocolo Shift-Left para Mitigación de CVEs en Lockfiles:**
    - Escaneo preventivo local con `./auditar-infra.sh` (Trivy IaC + FS) y `make -C backend qa-deps` (`uv audit`).
