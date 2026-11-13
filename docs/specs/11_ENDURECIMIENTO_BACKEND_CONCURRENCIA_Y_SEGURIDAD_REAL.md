# 🛡️ Especificación 11: Endurecimiento Backend (`--no-dev`), Seguridad Real, Concurrencia Financiera LPH y Corrección de Sesión/Modales en Frontend

**Estado:** Especificación Formal Activa (Hito 17 — Sub-tareas 17.1 y 17.2 completadas; Sub-tareas 17.3–17.5 planificadas)  
**Ecosistema:** FastAPI + SQLAlchemy 2.0 Async + PostgreSQL 17 + KeyDB Multi-Hilo + Vue 3 / Pinia  
**Origen de Auditoría:** Diagnóstico integral código ↔ especificaciones (2026-11-13) y estándar QA Nivel 11X

---

## 1. Empaquetado Productivo `--no-dev`, Fail-Fast en Producción y KDF Estricto (Sub-tarea 17.1)

### 1.1. Dependencias Productivas Reales (`backend/pyproject.toml`)
- `prometheus-fastapi-instrumentator>=7.0.0` y `prometheus-client>=0.20.0` son importados en `backend/src/main.py` durante el arranque del servicio; por lo tanto deben residir en `[project].dependencies` y no únicamente en el grupo `dev`, garantizando el arranque limpio bajo `uv sync --frozen --no-dev`.
- Se retira la dependencia no utilizada `passlib[bcrypt]` para reducir superficie de ataque y complejidad de auditoría de CVEs.

### 1.2. Validación Fail-Fast en `APP_ENV=production` (`backend/src/security.py`, `backend/src/main.py`)
- Se define `DEFAULT_INSECURE_SECRET_KEY = "qa-blueprint-11x-secret-key-super-secure-32bytes"` y lectura dinámica de `SECRET_KEY` mediante `_get_secret_key()` para operaciones de firma JWT/CSRF (manteniendo `SECRET_KEY` exportado para retrocompatibilidad con módulos que lo consumen).
- La función `validate_production_security_settings()` invocada al inicio de `lifespan(app)` aborta el arranque con `RuntimeError` si `APP_ENV=production` y ocurre cualquiera de estas condiciones:
  1. `SECRET_KEY` no fue configurada explícitamente, coincide con `DEFAULT_INSECURE_SECRET_KEY` o posee menos de `32` caracteres.
  2. `DATABASE_URL` no está definida o apunta a SQLite en memoria (`:memory:`).

### 1.3. Eliminación de Hashes Legacy sin Sal (`verify_password`)
- `verify_password(plain_password, hashed_password)` rechaza categóricamente todo hash que no cumpla el formato `pbkdf2_sha256$<sal>$<digest>` (eliminando la verificación de hashes `SHA-256` planos sin sal).
- Ante formato inválido, ejecuta una derivación dummy `PBKDF2-HMAC-SHA256` (`100.000` iteraciones) y `hmac.compare_digest` antes de retornar `False`, evitando oráculos de temporización.

---

## 2. Ciclo de Sesión Completo, CSRF Real, Rate-Limiting y KeyDB Fail-Closed (Sub-tarea 17.2)

### 2.1. Endpoints de Sesión y Protección CSRF en Producción
- **Nuevos endpoints en `backend/src/routers/auth.py`:**
  - `POST /api/auth/logout`: revoca el identificador de sesión `sid` (`revoke_session_id`) y quema el `jti` del `refresh_token` (`mark_refresh_jti_used`) en KeyDB, elimina las cookies `access_token`, `refresh_token` y `csrf_token` (`delete_cookie`) y emite `Clear-Site-Data: "cookies", "storage", "cache"`.
  - `POST /api/auth/refresh`: valida `refresh_token` (`decode_refresh_token`), verifica que el `sid` siga vigente, rota el par de tokens con periodo de gracia de `5s` (`rotate_refresh_token_with_grace_period`) y, ante reuso tardío de un `jti` ya consumido, revoca toda la sesión `sid` respondiendo `401 Unauthorized`; retorna además un nuevo `X-CSRF-Token`.
- **DTO completo e hidratación CSRF en `GET /api/auth/me`:** retorna adicionalmente `cedula`, `telefono` y `unidad_activa_id` para cumplir al 100% la interfaz `UsuarioPerfil` en `frontend/src/stores/authStore.ts`, re-hidratando la cookie y cabecera `X-CSRF-Token` cuando hay sesión activa por cookie.
- **Middleware CSRF real (`X-CSRF-Token` en `backend/src/main.py`):** en mutaciones (`POST`, `PUT`, `PATCH`, `DELETE`) autenticadas mediante cookie `HttpOnly` cuando `is_csrf_enforced()` está activo (`APP_ENV=production` o `CSRF_ENFORCE=true`), valida `validate_csrf_token(header_token, sid)` devolviendo `403 Forbidden` si falta o es inválido, eximiendo peticiones `Authorization: Bearer` (M2M/MCP); el cliente `apiClient.ts` lee `csrf_token` de cookie/cabecera/cuerpo y sincroniza `setCsrfToken`.
- **Cookie `secure` adaptable (`should_use_secure_cookie()`):** prioriza la variable `COOKIE_SECURE` si se define explícitamente y en su ausencia usa `APP_ENV == "production"`, manteniendo `secure=True` por defecto en producción HTTPS sin bloquear pruebas HTTP locales en contenedor.

### 2.2. Rate-Limiting Anti-Fuerza Bruta y KeyDB Fail-Closed
- **Lockout en `/api/auth/login`:** máximo `5` intentos fallidos por `(ip, correo)` en ventana de `15 minutos` vía KeyDB (`is_login_locked_out` / `record_login_failure` -> `HTTP 429 Too Many Requests`), ejecutando verificación dummy `PBKDF2-HMAC-SHA256` (`DUMMY_PASSWORD_HASH`) cuando el correo no existe para mitigar enumeración de usuarios por tiempo de respuesta.
- **Fail-Closed en KeyDB (`backend/src/redis_client.py`):** en `APP_ENV=production`, una indisponibilidad de KeyDB durante `is_user_session_revoked`, `is_session_id_revoked`, `is_qr_nonce_burned` o verificación de llaves críticas falla cerrado (`HTTP 503 Service Unavailable`) en vez de permitir sesiones revocadas o pases QR potencialmente reutilizados.
- **TTL de Idempotencia Canónico:** elevado `IDEMPOTENCY_TTL_SECONDS` de `120s` a `86400s` (24 horas) y validación estricta `min_length=8, max_length=128` en el header `Idempotency-Key` en todos los endpoints mutantes (`auth.py`, `pagos.py`, `finanzas.py`, `administracion.py`, `incidencias.py`, `consultas.py`, `accesos.py`, `reservas.py`).

### 2.3. Corrección de Sesión, Stores, RBAC Desktop y Top-Layer `<dialog>` en Frontend
- **Hidratación inicial de sesión (`frontend/src/router/index.ts`):** rastrea `sessionHydrated` en `authStore` para ejecutar `await authStore.fetchProfile()` antes de resolver rutas protegidas evitando pérdida de sesión al recargar (`F5`), y publica `rbacNotice` contextual al redirigir por falta de rol hacia `#rbac-notice-banner` en `AppShellLayout.vue`.
- **Refresh single-flight, manejo uniforme de `401` y `StaleDataBanner`:** `apiClient.ts` realiza refresh único concurrente (`POST /api/auth/refresh`) ante `401` (excluyendo `/api/auth/*`) propagando `refreshAttempted`; todo `ApiError` con `status === 401` en los 5 stores (`authStore`, `financeStore`, `operationsStore`, `governanceStore`, `accessAmenitiesStore`) ejecuta `handleUnauthorizedError` (limpiando sesión sin marcar falso `isStale = true` y redirigiendo a `/login`). En `AppShellLayout.vue`, `<StaleDataBanner>` se enlaza al OR reactivo del `isStale` de los 5 stores.
- **Menú `SidebarNav.vue` y `authStore.logout()`:** `logout()` invoca `POST /api/auth/logout`; `SidebarNav.vue` añade `/tesoreria/pagos` (`#side-revision-pagos`) y `/tesoreria/cierre` (`#side-cierre-mensual`) filtrando estrictamente por rol en sintonía con `router/index.ts`.
- **Verdadero Top-Layer en los 4 `<dialog>` (`ContextualHelpModal.vue`, `VoteReceiptModal.vue`, `RejectPaymentModal.vue`, `ReceiptBreakdownModal.vue`):** eliminado el atributo estático `open` / `:open`, controlando apertura/cierre exclusivamente vía `showModal()` / `close()` y acotando reglas `display` al selector `dialog[open]` con `dialog:modal { overscroll-behavior: contain }`.
- **Dashboard dinámico (`DashboardView.vue`):** calcula dinámicamente el periodo actual (`YYYY-MM` actual) y pasa `:own-unit-id="authStore.data?.unidad_activa_id ?? null"` a `CollectionTrafficLight.vue`.

---

## 3. Concurrencia Financiera, Candado Contable, Anti-IDOR y Exactitud LPH (Sub-tarea 17.3)

- **Atomicidad en `PUT /api/pagos/{pago_id}/aprobar` (`backend/src/routers/pagos.py`):** exigir cabecera `Idempotency-Key` obligatoria y bloquear con `with_for_update()` las filas `Pago`, `Recibo` y `Unidad` antes de acreditar montos y excedentes, eliminando condiciones de carrera (*lost update* / doble acreditación).
- **Anti-IDOR en `POST /api/pagos/reportar`:** verificar en base de datos que el `recibo_id` corresponda a una unidad donde el usuario autenticado posea un `ContratoOcupacion` activo (o posea rol `TESORERO`/`PRESIDENTE`), y añadir índice único parcial en `Pago(metodo, numero_referencia)` excluyendo `estado == 'RECHAZADO'`.
- **Cierre Inmutable del Candado Contable (`backend/src/routers/finanzas.py`):** bloquear `POST /api/finanzas/egresos` con `HTTP 409 Conflict` cuando el periodo objetivo ya posea `ReporteMensual.bloqueado == True`, exigiendo además `Idempotency-Key`.
- **Unicidad de Facturación (`Recibo` — Migración `0007`):** añadir `UniqueConstraint("unidad_id", "periodo")` en `Recibo` para garantizar un único recibo ordinario por unidad y periodo.
- **Prorrateo Exacto de Cuotas Extraordinarias y Quórum `2/3`:** en `_anexar_cuota_extraordinaria`, respetar la modalidad `ALICUOTA` usando `prorratear_por_alicuotas` en vez de partes iguales, validar `validar_suma_alicuotas` antes de facturar cargos variables, y evaluar `DOS_TERCIOS` con fracción racional exacta (`Decimal(2) / Decimal(3)`).

---

## 4. Integridad en Gobernanza, Reservas, Administración y Consultas SQL (Sub-tareas 17.4–17.5)

- **Cartas Consulta (`backend/src/routers/consultas.py`):** rechazar votos emitidos cuando `datetime.now(UTC) > consulta.fecha_cierre` (`HTTP 409 Conflict`) y adquirir bloqueo pesimista al ejecutar `cerrar_consulta` evitando actas duplicadas; incorporar `jti` en votos y certificados de solvencia y verificar vigencia de deuda actual en `GET /api/finanzas/solvencia/verificar/{folio}`.
- **Reservas de Áreas Sociales (`backend/src/models.py`, `backend/src/routers/reservas.py`):** sustituir `UniqueConstraint("area_id", "fecha_evento")` por índice único parcial excluyendo reservas `CANCELADA`, implementar `PUT /api/reservas/{id}/cancelar` y registrar contablemente el uso/retención de depósito cuando `inspeccionar` concluya `FINALIZADA_CON_DANOS`.
- **Administración y Privacidad (`backend/src/routers/administracion.py`):** restringir `GET /api/estructura/unidades` sin autenticación a un DTO público mínimo (`UnidadPublicaResponse`: `id`, `identificador`, `estructura_id`) sin exponer `credito_disponible_usd` ni `cuota_fija_usd`; preservar histórico de `ContratoOcupacion` en reasignaciones y prohibir cargos de Junta Directiva a usuarios cuyo contrato activo sea únicamente `INQUILINO`.
- **Eliminación de `SELECT *` en RAM y N+1:** reemplazar filtrados en memoria (`finanzas.py`, `accesos.py`, `reservas.py`) y consultas N+1 (`consultas.py`) por cláusulas `WHERE`, `JOIN` y cargas `selectinload` en SQLAlchemy; preparar migración y políticas `FORCE ROW LEVEL SECURITY` (`condominio_id`) en PostgreSQL 17 (`QA-PG17-RLS`) junto con la suite completa de pruebas unitarias, de concurrencia PostgreSQL 17 y escenarios BDD Karate Labs.
