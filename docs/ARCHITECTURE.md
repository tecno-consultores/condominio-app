# Sistema de Administración de Condominios - Arquitectura y Especificaciones
**Versión:** 1.0.0  
**Fecha de Documento:** Noviembre 2026
**Licencia:** MIT

## 1. Stack Tecnológico y Arquitectura
- **Estructura del Proyecto:** Monorepo (`backend/`, `frontend/`, `scripts/`, `docs/`, `architecture/`).
- **Backend y Worker Unificados (`CONTAINER_ROLE=api|worker`):** Imagen productiva única en Python 3.13 multi-stage (`--no-dev`, sin `pip`/`ensurepip`, `UID/GID 10001:10001`, `--read-only`) controlada por `backend/docker-entrypoint.sh`:
  - `CONTAINER_ROLE=api`: FastAPI + Uvicorn (`--proxy-headers --no-server-header`) con `61` endpoints REST (`59` en `routers/*.py` + `/health` + `/metrics`), oculto en las redes internas `backend_net` y `frontend_net`.
  - `CONTAINER_ROLE=worker`: Worker asíncrono (`backend/src/worker.py`, `worker_media.py`, `worker_scheduler.py`) con conversión `Pillow` a **AVIF**, carga autenticada `AWS4-HMAC-SHA256` a MinIO (`MINIO_USE_SSL`), colas KeyDB `BLMOVE` + DLQ acotado, envío SMTP `STARTTLS`, scheduler diario de tareas y heartbeat físico `QA-HEALTH-01`.
- **Frontend:** Vue 3 (`<script setup lang="ts">`) + Pinia + Vue Router (`23` rutas bajo `<AppShellLayout>` + `404`) + CSS Nativo con tokens `OKLCH` y `light-dark()`, diseño Mobile-First, servido por Nginx no-root (`UID/GID 101:101`, puerto `8080`) con `gzip on` y cabeceras OWASP OSHP / DISA STIG.
- **Base de Datos:** PostgreSQL 17 (`27` tablas ORM, migraciones Alembic `0001..0010`), aritmética `NUMERIC(12,2)`/`Decimal`, separación de rol migrador (`condominio_admin`) frente a usuario runtime no-superusuario (`condominio_app`) sujeto a `SET LOCAL ROLE condominio_app_runtime` con `ENABLE` + `FORCE ROW LEVEL SECURITY` (*fail-closed* sobre `condominio_id`) y sellado WORM hash-chain en `auditoria_recibos` y `votos_consulta`.
- **Proxy / Gateway:** Nginx reverso (`frontend/nginx.conf` en puerto `8080`, `127.0.0.1:${FRONTEND_PORT:-8080}:8080`) + terminación TLS frontal.
- **Almacenamiento de Archivos:** MinIO (S3 Compatible) en `backend_net` con validación binaria de *Magic Bytes*, límite `2 MB` y `Image.MAX_IMAGE_PIXELS`.
- **Control de Estado en Red:** **KeyDB Multi-Hilo** (`eqalpha/keydb:alpine`, política *fail-closed*) para idempotencia por ámbito (`idemp:{condominio_id}:{usuario_id}:{scope}:{key}`), lockout atómico Lua, revocación de sesiones (`sid`/`jti`) y usuarios (`7d`), *grace period* de `5s` y quemado atómico de nonces QR `qr_used:{jti}`.

## 2. Seguridad y Autenticación
- **Criptografía y Tokens:** Subclaves independientes derivadas vía `HKDF-SHA256` (acceso, refresco, CSRF, solvencia, voto, QR y auditoría WORM), hashing `PBKDF2-HMAC-SHA256` (`>= 600_000` iteraciones vía `asyncio.to_thread`), JWT estrictos (`typ`/`iat`/`iss`/`aud`/`condominio_id`) en cookies `HttpOnly` + `X-CSRF-Token` `HMAC-SHA256` para SPA, y `Authorization: Bearer` para integraciones M2M/MCP.
- **Arranque Fail-Fast:** `validate_production_security_settings` en `lifespan` aborta si `APP_ENV=production` arranca con `SECRET_KEY` débil/placeholder o `DATABASE_URL` vacía/SQLite `:memory:`.
- **Registro de Usuarios ("Usuario Fantasma"):** El registro público (`POST /api/auth/register`) crea cuentas inactivas (`es_activo = False`, `rol = "FANTASMA"`), aisladas con `HTTP 403` por `verificar_usuario_activo` hasta validación y asignación de unidad por `PRESIDENTE` o `VICEPRESIDENTE`.
- **Perímetro y Protección Web:** Validación `ALLOWED_HOSTS`, `TRUSTED_PROXY_IPS`, protección de `/metrics` con `METRICS_AUTH_TOKEN`, Fetch Metadata pre-auth, Anti-SSRF DNS asíncrono y `verify_websocket_origin` preparado para canales en vivo.
- **Idempotencia:** Generación criptográfica en Frontend (`useIdempotency` con `crypto.getRandomValues`) y dependencia unificada `IdempotentAPIRoute` en Backend con *replay* determinista en `2xx` y liberación en `4xx`/`5xx`.

## 3. Modelo de Entidades (Core)
- **Estructura Polimórfica:** Soporta edificios (Pisos -> Apartamentos) y Urbanizaciones (Calles -> Casas). Permite condominios mixtos.
- **Historial de Ocupación:** Los inquilinos/propietarios no se sobrescriben. Se mantiene un histórico (`Contratos_Ocupacion`) para saber quién ocupaba una unidad en una fecha determinada.
- **Propiedad Múltiple:** Un usuario puede poseer/ocupar múltiples unidades.

## 4. Roles y Permisos (RBAC — `9` Roles Canónicos)
*Condición estatutaria LPH (Art. 18): Solo los `PROPIETARIO` registrados con unidad activa pueden ocupar cargos de Junta Directiva (`PUT /api/junta/cargos`, exclusivo de `PRESIDENTE`).*

1. **`FANTASMA`:** Cuenta recién registrada (`es_activo = False`, sin unidad asignada). Bloqueada con `HTTP 403` en todo módulo operativo/financiero hasta validación por `PRESIDENTE` o `VICEPRESIDENTE`.
2. **`PROPIETARIO`:** Consulta de su propio estado de cuenta, reporte de pagos, emisión de solvencias, voto ponderado por alícuota en Cartas Consulta (`puede_votar_asamblea`), pases QR, paquetería propia, reservas de amenidades, incidencias ("¡Me sumo!") y lectura de bitácora/galería/tareas/comunicados. Elegible para Junta Directiva.
3. **`INQUILINO`:** Operativa residencial equivalente sobre su unidad vigente (pagos, solvencia, pases QR, paquetería propia, reservas e incidencias). Sin derecho a voto en Cartas Consulta salvo habilitación expresa (`puede_votar_asamblea = True`) ni elegibilidad directa a Junta Directiva.
4. **`CONSERJE`:** Ejecución y cierre con evidencia del checklist diario (`/api/tareas/{id}/completar`), verificación de pases QR en garita (`/api/accesos/verificar-qr`), registro/listado/entrega de paquetería (`/api/paqueteria*`), inspección post-evento de áreas sociales (`/api/reservas/{id}/inspeccionar`) y lectura de listado global de reservas. En `GET /api/finanzas/resumen` recibe `estado_cobranza: []`.
5. **`VOCERO`:** Supervisión física y galería fotográfica de áreas comunes (`POST /api/voceros/fotos`, límite `30` fotos/mes con `.with_for_update()`), verificación de pases QR en garita (`_ROLES_GARITA`) y lectura financiera/cobranza de Junta.
6. **`SECRETARIO`:** Redacción de actas en `BitacoraActa`, publicación de comunicados oficiales (`POST /api/comunicados`), apertura y cierre de Cartas Consulta (`POST /api/consultas`, `POST /api/consultas/{id}/cerrar`) y cancelación administrativa de reservas.
7. **`TESORERO`:** Control financiero integral: tasa BCV, egresos, aprobación/rechazo de pagos, facturación trimodal LPH (`ALICUOTA`, `CUOTA_FIJA`, `PARTES_IGUALES`), fondos patrimoniales, ejecución inmutable del Candado Contable (`POST /api/finanzas/cierre-mensual`), gestión de alícuotas, creación/inspección/cancelación de áreas y reservas.
8. **`VICEPRESIDENTE`:** Generación de estructura física, actualización de alícuotas, aprobación de Usuarios Fantasma (`PROPIETARIO`, `INQUILINO` o `CONSERJE`; bloqueado ante escalación a `PRESIDENTE`/Junta), gestión y completado de tareas diarias y cancelación de reservas.
9. **`PRESIDENTE`:** Máxima coordinación ejecutiva: designación exclusiva de cargos de Junta Directiva (`PUT /api/junta/cargos`), aprobación de usuarios, estructura, alícuotas, operaciones de tesorería, gobernanza, garita QR, paquetería y reservas.

## 5. Finanzas y Cobranzas
- **Multimoneda Base:** Contabilidad referenciada en USD (`NUMERIC(12,2)` / `Decimal`) con registro diario de la tasa oficial USD/VES (`TasaCambio`).
- **Cobros Trimodales:** Facturación LPH por **Alícuotas** (Método del Resto Mayor / Hamilton), **Cuota Fija USD** (conciliación de excedente/déficit hacia `FondoCondominio`) o **Partes Iguales**.
- **Reporte de Pagos:** Permite pagos totales o abonos parciales en `USD` o `VES`. *Regla crítica: El sistema fija la tasa vigente del día al reportar y valida unicidad parcial `(metodo_pago, numero_referencia)` salvo `EFECTIVO`.*
- **Egresos:** `TESORERO` o `PRESIDENTE` registran gastos comunes o con cargo a `RESERVA_LEGAL`, bloqueados con `HTTP 409` si el periodo ya fue cerrado.
- **Cierre de Mes (El Candado Contable — Implementado `v1.0.0`):**
  - `POST /api/finanzas/cierre-mensual` (`TreasuryClosingView.vue`) valida que no existan pagos `EN_REVISION` en el periodo (`HTTP 409`), bloquea con `.with_for_update()` todos los `Recibo` y `Egreso` (`bloqueado = True`) y sella `ReporteMensual.estado = "CERRADO"` (`Read-Only` absoluto).
  - Del día 1 al 10 de cada mes, `ClosingBanner.vue` destaca el cierre publicado en `/dashboard`. *(La generación automática de archivos PDF y su envío por correo SMTP pertenecen a **Spec 13 Fase 8 — Hito 25**).*
- **Pista de Auditoría WORM (`AuditoriaRecibo`):** Tabla inmutable con encadenamiento `prev_hash`/`record_hash` (`HKDF-SHA256`) y `REVOKE UPDATE, DELETE` en PostgreSQL 17 (triggers en SQLite) que registra todo cambio de estado financiero.

## 6. Operaciones y Mantenimiento
- **Gestión de Tareas:** El Presidente define Plantillas de tareas recurrentes (Diarias/Semanales). Un Cronjob (Worker) genera las tareas asignadas reales a medianoche para no saturar la base de datos a futuro.
- **Visibilidad de Tareas:** Los propietarios tienen acceso de solo lectura al estado de las tareas del conserje para verificar su cumplimiento. El conserje puede subir fotos como evidencia de cumplimiento.
- **Embudo de Incidencias (UX/UX):**
  - Al reportar un daño, el usuario debe ver primero las incidencias recientes.
  - **Adhesión ("Me sumo"):** Si el daño ya está reportado, el usuario pulsa "Me sumo", lo cual aumenta la prioridad del reporte existente.
  - **Notificación:** Al crearse un reporte nuevo, el Worker envía un correo al Presidente y Vicepresidente.

## 7. Despliegue, DevOps y Estándar QA (Nivel 11X)
- **CI/CD y Rule Zero:** Toda verificación se ejecuta en contenedores Docker efímeros (`docker-compose.qa.yml` y `sinfallas/base-python-uv:3.13`, sin ejecución directa en host) con acciones fijadas por digest SHA-40 (`SEC-CI-ACTION-REF`).
- **Compuertas de Calidad Innegociables:** Complejidad **Radon Grado A (`CC <= 5`, `MI >= A` en `radon_gates.py`)** y SonarJS (`CC <= 15`); cobertura `>= 95%` en Backend (`pytest-cov`), Frontend (`Vitest`) y Bash (`kcov >= 95%`); mutación `>= 80%` MSI (`mutmut` y `Stryker`); paridad ORM ↔ Alembic contra PostgreSQL 17 real (`make -C backend qa-parity`) + `PRAGMA foreign_keys=ON` en SQLite; E2E Playwright + `@axe-core` WCAG 2.1/2.2 AA; Lighthouse CI; Karate Labs API/UI BDD; Schemathesis; DAST OWASP ZAP no-root; resiliencia Pumba + Locust; validación FINOS CALM `1.2` (`architecture/qa-11x.calm.json`), Graphify AST `--code-only` y `Trivy HIGH/CRITICAL = 0`.
- **Documentación Completa de Pruebas:** Consulta la [Bitácora General de Calidad y Certificación 11X (`TESTING.md`)](../TESTING.md), junto con [`backend/TESTING.md`](../backend/TESTING.md) y [`frontend/TESTING.md`](../frontend/TESTING.md).
- **Distribución e Instalación:** Publicación de imágenes multi-arquitectura (`linux/amd64`, `linux/arm64`) en Docker Hub (`sinfallas/condominio-backend` y `sinfallas/condominio-frontend`) y despliegue sin compilación local mediante `docker-compose.prod.yml` o `docker-compose.yml`.

## 8. Flujos Críticos y Máquinas de Estado

### 8.1. Registro y Asignación ("Flujo Fantasma")
1. **Frontend:** Usuario llena datos. Genera `Idempotency-Key` y envía petición.
2. **Backend:** Valida UUID en KeyDB Multi-Hilo (`idemp:register:{key}`). Crea usuario con `Es_Activo = FALSE` (sin unidad asignada).
3. **Worker:** Encola notificación por correo a Presidente y Administrador.
4. **Presidente:** Entra al panel, identifica al usuario, le asigna Unidad y Rol, y lo activa.
5. **Backend:** Crea registro en `Contratos_Ocupacion` (historial) y actualiza el estado del usuario a `Es_Activo = TRUE`.

### 8.2. Reporte y Aprobación de Pagos
1. **Frontend:** Propietario reporta pago y sube comprobante. Vue3 genera `Idempotency-Key` y bloquea el botón visualmente.
2. **Backend:** Valida UUID en KeyDB Multi-Hilo (`idemp:user:{id}:{key}`) evitando duplicados por doble clic.
3. **Worker:** Convierte imagen a AVIF y sube a MinIO.
4. **Backend:** Crea registro en `Pagos_Reportados` en estado `EN_REVISION`. El recibo pasa a estado visual `PAGO_EN_REVISION`.
5. **Tesorero:** Revisa el reporte.
   - **Camino A (Aprobar):** Tesorero aprueba. Backend suma pagos aprobados. Si cubre el total, Recibo pasa a `PAGADO`. Si es menor, pasa a `PAGADO_PARCIAL`. Se crea registro en `Auditoria_Recibos`.
   - **Camino B (Rechazar):** Tesorero rechaza e introduce Motivo obligatorio. Pago pasa a `RECHAZADO`. Recibo vuelve a `PENDIENTE`. Frontend notifica al propietario.

### 8.3. Embudo de Incidencias (UX y Adhesiones)
1. **Frontend:** Propietario inicia reporte. Se muestran incidencias `ABIERTAS` de los últimos 7 días.
2. **Bifurcación:**
   - **Daño Existente:** Propietario pulsa "Me sumo". Backend registra adherencia, aumentando prioridad.
   - **Nuevo Daño:** Propietario crea reporte (Worker convierte imagen a AVIF). Backend guarda en estado `ABIERTO`. Worker notifica por correo a Presidente y VP.
3. **Presidente/VP:** Asigna tarea vinculada al conserje. Estado cambia a `EN_PROCESO`.
4. **Conserje:** Marca tarea como Completada. Reporte pasa automáticamente a `CERRADO`.

### 8.4. Cierre Financiero de Mes (Candado Contable — Implementado `v1.0.0`)
1. **Validación Previa (`POST /api/finanzas/cierre-mensual`):** El backend verifica con `.with_for_update()` que el `ReporteMensual` del periodo no esté `CERRADO` y rechaza con `HTTP 409` si existen `PagoReportado` en estado `EN_REVISION` para ese mes.
2. **Bloqueo Inmutable:** El Tesorero o Presidente confirma el cierre en `TreasuryClosingView.vue` mediante `<dialog>` de confirmación. El backend marca `bloqueado = True` en todos los `Recibo` y `Egreso` del periodo y fija `ReporteMensual.estado = "CERRADO"` (`cerrado_en = UTC`).
3. **Visibilidad:** `ClosingBanner.vue` muestra el banner destacado en `/dashboard` del día 1 al 10 cuando existe un cierre mensual publicado.

### 8.5. Facturación Mensual por Alícuota y Certificado de Solvencia (Spec 07)
1. **Prorrateo Exacto (Método del Resto Mayor / Hamilton):** El Tesorero o Presidente ejecuta `POST /api/finanzas/facturar-periodo`. El sistema suma los egresos comunes del mes más el recargo del Fondo de Reserva Legal (10%), los prorratea según la `alicuota` de cada unidad distribuyendo los centavos residuales por resto mayor ($\sum \text{recibos} == \text{total}$) y descuenta automáticamente cualquier saldo a favor (`credito_disponible_usd`).
2. **Solvencia Digital:** Si una unidad tiene deuda cero ($0.00\text{ USD}$), puede emitir un `CertificadoSolvencia` foliado con `jti` y sello criptográfico `HMAC-SHA256` (`HKDF-SHA256`) verificable públicamente.

### 8.6. Gobernanza Digital y Carta Consulta — Art. 23 LPH (Spec 08)
1. **Apertura:** El Presidente o Secretario publica una `ConsultaComunitaria` con regla de quórum (`DOS_TERCIOS` = $66.67\%$, `MAYORIA_SIMPLE` > $50.0000\%$ o `UNANIMIDAD` = $100\%$).
2. **Votación Ponderada:** Cada unidad emite un único voto (`UniqueConstraint("consulta_id", "unidad_id")`) ejercido por su `PROPIETARIO` activo (o representante con `puede_votar_asamblea = True`), cuyo peso es `Unidad.alicuota`, recibiendo un comprobante `HMAC-SHA256` sellado en cadena WORM.
3. **Cierre y Acta Automática:** Al cerrarse la consulta, el backend calcula el escrutinio en `Decimal` y asienta automáticamente el acuerdo inmutable en `BitacoraActa`.

### 8.7. Control de Acceso QR, Paquetería y Reservas con Solvencia (Spec 09)
1. **Pases QR con Anti-Replay:** El residente emite un `PaseVisita` firmado con subclave `HKDF-SHA256` y `jti` único. Al validarse en garita (`POST /api/accesos/verificar-qr` por `CONSERJE`, `PRESIDENTE` o `VOCERO`), el `jti` de pases `UNICO_USO` se quema atómicamente en **KeyDB Multi-Hilo** impidiendo su reutilización.
2. **Reservas Bloqueadas por Morosidad:** Al solicitar una reserva de área social (`POST /api/reservas/solicitar`), el backend verifica en tiempo real que la unidad no tenga deuda (`$0.00 USD`); al confirmarse, agenda automáticamente una `TareaDiaria` de inspección post-evento.

---

## 9. Alcance Implementado (`v1.0.0`) vs. Hoja de Ruta Planificada (Spec 13 Fase 8 — `v1.2.0`)

Para mantener trazabilidad estricta entre el sistema productivo actual y la especificación evolutiva [`docs/specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md`](specs/13_REMEDIACION_INTEGRAL_COMPLETITUD_FUNCIONAL_Y_DOCKERHUB_11X.md):

- **Implementado y Certificado en `v1.0.0` (Hitos 1–23):**
  - `61` endpoints REST FastAPI y `23` rutas Vue 3 bajo `<AppShellLayout>`, PG17 RLS (`27` tablas, `condominio_app_runtime`), WORM hash-chain, KeyDB *fail-closed*, worker AVIF/MinIO/SMTP/scheduler (`CONTAINER_ROLE=api|worker`), Candado Contable inmutable en BD (`ReporteMensual.estado == "CERRADO"`) y pases QR por token firmado.
- **Planificado en Spec 13 Fase 8 (`v1.2.0`, Hitos 24–26 — NO activo en `v1.0.0`):**
  - **Hito 24 (Migración `0011`):** Recuperación de contraseña autoservicio (`/recuperar-clave`), selector global de unidad activa (`PUT /api/auth/unidad-activa`) y CRUD de puestos de estacionamiento / maleteros.
  - **Hito 25 (Motor PDF + QR Gráfico):** Generación determinista de PDF (`GET /api/finanzas/recibos/{id}/pdf` y `GET /api/finanzas/solvencia/{id}/pdf`) + envío SMTP adjunto, renderizado QR SVG/Canvas local en cliente y escáner óptico por cámara en garita.
  - **Hito 26 (Tiempo Real WS):** Endpoint `WS /ws/notificaciones` autenticado sobre Pub/Sub KeyDB y composable SPA `useRealtimeNotifications` (actualmente `verify_websocket_origin` en `security.py` y el bloque `location /ws/` en `frontend/nginx.conf` permanecen preparados de forma preventiva).
