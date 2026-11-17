# 🚀 Especificación 13: Remediación Integral Post-Auditoría, Completitud Funcional PropTech y Distribución Docker Hub (`v1.1.0` – `v1.2.0`)

**Estado:** En Ejecución Activa — **Hitos 19 y 20 ✅ Completados** (Hitos 21 al 26 pendientes de ejecución)  
**Ecosistema:** FastAPI + SQLAlchemy 2.0 Async + PostgreSQL 17 (RLS) + KeyDB Multi-Hilo + Vue 3 / Pinia + Docker Hub Multi-Arch + `@sinfallas/mcp-qa-11x` `v3.1.0`  
**Origen de Auditoría:** Auditoría integral de solo lectura sobre los 306 archivos del repositorio (`2026-11-17`) y definiciones de alcance productivas aprobadas  

---

## 1. Decisiones Arquitectónicas Rectoras

### 1.1. Política Oficial de Distribución (Cero `npmjs.com` — Docker Hub Multi-Arquitectura)
- **No publicación en `npmjs.com`:** Todos los manifiestos JavaScript/TypeScript del repositorio (`package.json` raíz y `frontend/package.json`) permanecen estrictamente con `"private": true` y sin artefactos publicables en el registro npm.
- **Distribución en Docker Hub (`linux/amd64`, `linux/arm64`):** El producto se empaqueta y distribuye exclusivamente como **2 imágenes Docker multi-arquitectura** no-root endurecidas (`Trivy HIGH/CRITICAL = 0`), firmadas con SBOM CycloneDX (`artifacts/sbom/`):
  1. **`sinfallas/condominio-backend`:** Imagen única Python 3.13 (`--no-dev`) que opera como servidor HTTP (`CONTAINER_ROLE=api`, Uvicorn + FastAPI) o como trabajador asíncrono (`CONTAINER_ROLE=worker`, `python -m src.worker`) mediante entrypoint y `HEALTHCHECK` conscientes del rol (`QA-HEALTH-01`).
  2. **`sinfallas/condominio-frontend`:** Imagen Nginx no-root (`UID 101:101`, puerto `8080`) con el bundle SPA Vue 3 compilado, compresión `gzip`, cabeceras OSHP/STIG preservadas en todos los bloques `location`, proxy hacia `/api/`, `/health` y `/ws/`.
- **Orquestación de Despliegue sin Código Fuente:** Se incorporará un manifiesto `docker-compose.prod.yml` orientado a operadores de condominios para desplegar las imágenes publicadas de Docker Hub sin clonar código ni compilar localmente.

### 1.2. Modelo Operativo de Aislamiento: Un Condominio por Despliegue + PG17 RLS
- **Despliegue de Condominio Único (*Single-Condo Instance*):** Cada comunidad opera en su propia instancia Docker aislada (PostgreSQL 17 + KeyDB + MinIO + API + Worker + Frontend), evitando la superficie de ataque y complejidad de una consola SaaS multi-tenant compartida.
- **Defensa en Profundidad con PostgreSQL 17 RLS:** Pese al despliegue por instancia, todas las tablas mantienen `ENABLE` + `FORCE ROW LEVEL SECURITY` sobre `condominio_id` con conexión runtime mediante rol **no-superusuario** (`NOBYPASSRLS` + `SET LOCAL ROLE condominio_app_runtime`), inyección de sesión fail-closed (`tenant_id = ""` por defecto hasta validar contexto autenticado/bootstrap) y claves `UNIQUE` compuestas por `(condominio_id, ...)` para impedir regresiones o fugas ante inyecciones o corrupción de consultas.

---

## 2. FASE 7: Remediación Integral Post-Auditoría `v1.0.0` (Hitos 19 al 23)

### 2.1. Hito 19: Contención Operativa, Gobernanza QA 11X `v3.1.0`, Manifiestos y Pipeline Docker Hub Multi-Arch ✅ (`Completado`)
1. **Protección de Volúmenes, Respaldos y Escáner de Secretos:**
   - Restringir `scripts/limpieza.sh` exclusivamente a archivos `docker-compose*.qa.yml`, garantizando que `docker-compose.yml` y los volúmenes productivos `postgres_data` y `minio_data` jamás sean detenidos ni eliminados. Consolidar los wrappers duplicados (`limpieza.sh`, `backend/limpieza.sh`, `frontend/limpieza.sh`, `auditar-infra.sh`) dejando `scripts/*` como única fuente de verdad.
   - Mover la salida de `scripts/generar-sbom-cyclonedx.sh` a `artifacts/sbom/` (añadiendo `-w /workspace`) para evitar que `scripts/limpieza.sh` elimine los manifiestos SBOM recién generados.
   - Endurecer `scripts/backup-diario.sh` eliminando `|| true` en `mc mirror`, verificando que los respaldos generados superen `0 bytes`, purgando artefactos parciales/truncados en `trap`, respetando `MINIO_USE_SSL` y propagando `MINIO_USE_SSL` al servicio `worker` en `docker-compose.yml`.
   - Corregir `scripts/verificar-secretos.sh` para ejecutar siempre desde la raíz del repositorio y escanear la totalidad del árbol de trabajo incluyendo `.env.example` y suites de prueba.
2. **Actualización de Gobernanza Thin-Repo a `@sinfallas/mcp-qa-11x` `v3.1.0`:**
   - Sincronizar `.agents/` y `AGENTS.md` con `v3.1.0` (`QA-GIT-GATE-01` prohibiendo `git push` automático, referencia a las 10 skills globales, corrección de numeración e idioma inglés técnico conciso en `.agents/**` y `.agents/rules/domain_condominio_app_rules.md`, e inclusión de `scripts/backup-diario.sh`).
   - Corregir `.agents/scripts/certify_task_completion.sh` para cumplir `Rule Zero` (ejecución en contenedor `sinfallas/base-python-uv:3.13` en lugar de host o etiqueta `:3.15` inexistente, sin suprimir `stdout` al fallar `verify_docs_invariants.py`).
   - Reparar los falsos positivos ciegos en los validadores de compuerta:
     - `verify_no_orphan_api_endpoints.py`: reconocer `apiClient.apiRequest(...)` y rutas `/api/*` sin prefijo `/v1`.
     - `verify_topological_health.py`: auditar módulos planos `backend/src/models.py`, `backend/src/schemas.py` y controladores en `backend/src/routers/`.
     - `verify_docs_invariants.py`, `.trivy.yaml` y `commitlint.config.js`: purgar rutas residuales de plantillas externas y apuntar a `docs/qa/*.md`, `docs/specs/*.md` y directorios reales de `condominio-app`.
   - Crear `architecture/qa-11x.calm.json` cumpliendo validación estructural y los 7 controles obligatorios FINOS CALM, y regenerar limpiamente en modo `--code-only` los 3 grafos AST (`graphify-out/`, `backend/graphify-out/`, `frontend/graphify-out/`) purgando los 333 nodos Markdown heredados y el archivo vacío de `frontend/graphify-out/graph.json`.
3. **Estandarización de Manifiestos, Hooks Efímeros y CI/CD hacia Docker Hub:**
   - Completar metadatos (`license: "MIT"`, `repository`, `homepage`, `bugs`, `author`, `engines`, `packageManager`) en `package.json`, `frontend/package.json` y `backend/pyproject.toml`; unificar la atribución corporativa entre `LICENSE`, `AUTHORS.md`, `README.md` y `AGENTS.md`; unificar Python `3.13` y deduplicar grupos `dev` en `backend/pyproject.toml` y `pyrightconfig.json`.
   - Reparar `lefthook.yml`, `instalar-hooks.sh` y `commitlint.config.js` ejecutando `commitlint` dentro de contenedor efímero bajo `Rule Zero`; incorporar `--frozen` / `--frozen-lockfile` en Makefiles y fijar digests/tags inmutables en imágenes auxiliares y de base.
   - Fijar todas las acciones en `.github/workflows/00..02.yml` mediante hash SHA-40 (`SEC-CI-ACTION-REF`), añadir `concurrency` y `timeout-minutes`, compartir artefactos de compilación UI en `02-ci-frontend.yml`, ejecutar `certify_task_completion.sh` y `verificar-secretos.sh` en CI, y crear workflow de publicación Docker Hub multi-arch (`linux/amd64,linux/arm64`) con smoke test `--no-dev` y Trivy `0 HIGH/CRITICAL`.
   - Incorporar suites BATS con cobertura `kcov >= 95%` para todos los scripts Bash (`scripts/*.sh`, `.agents/scripts/certify_task_completion.sh`, `instalar-hooks.sh`) y validación de pinning SHA-40 en `test/ci_workflows.bats`.

### 2.2. Hito 20: Defensa PG17 RLS Real, HKDF/JWT, KeyDB Fail-Closed, Nginx OSHP y RBAC/IDOR (Migración `0010`) ✅ (Completado)
1. **Aislamiento Real PostgreSQL 17 RLS y Paridad SQLite (`backend/src/database.py`, `backend/src/dependencies.py`, `0010`):**
   - Separar credenciales en `.env.example` y `docker-compose.yml`: usuario administrador de migraciones (`condominio_admin`) vs usuario runtime no-superusuario (`condominio_app`) sujeto a `SET LOCAL ROLE condominio_app_runtime` en `apply_rls_session_settings`.
   - Establecer fail-closed por defecto (`tenant_id = ""`) en `database.py`, incorporar `condominio_id` en los claims JWT e inyectarlo en `session.sync_session.info["tenant_id"]` dentro de `get_current_user` y `get_optional_active_user`, asegurar `condominio_id` explícito en `facturacion_lph.py` y activar `pool_pre_ping`, límites de pool y `PRAGMA foreign_keys=ON` en motores SQLite.
   - **Migración `0010_rls_multitenant_worm_checks.py`:** Convertir restricciones `UNIQUE` globales de dominio en claves compuestas con `condominio_id`, añadir índices sobre claves foráneas calientes, remover índices duplicados sobre PK, agregar `CheckConstraint` contables (`monto_usd >= 0`, `alicuota BETWEEN 0 AND 100`), aplicar `ALTER DEFAULT PRIVILEGES` para `condominio_app_runtime` y revocar `UPDATE, DELETE` sobre `auditoria_recibos` y `votos_consulta` con hash-chain WORM.
2. **Criptografía, Sesiones JWT, KeyDB Fail-Closed y Anti-SSRF (`security.py`, `redis_client.py`, `auth.py`, `schemas.py`):**
   - Derivar subclaves criptográficas independientes vía `HKDF-SHA256` para acceso, refresco, CSRF, solvencia, voto y QR; exigir `"typ": "access"`, `iat`, `iss` y `aud` al decodificar tokens de acceso; elevar `PBKDF2_ITERATIONS >= 600_000` (o `Argon2id`) ejecutado en `asyncio.to_thread` con contraseñas acotadas (`min_length=8`, `max_length=128`); usar `_get_secret_key()` y `hmac.compare_digest` en todas las verificaciones.
   - Alinear el TTL de revocación en KeyDB con `REFRESH_TOKEN_EXPIRE_DAYS` (`>= 7 días`), aplicar política fail-closed (`_raise_if_prod`) en todas las funciones de revocación/idempotencia/QR eliminando la fuga de memoria infinita en `_local_revoked_*`, separar revocación por dispositivo (`logout` revoca `sid` individual) sin borrar bloqueos administrativos en `login`, y corregir `bootstrap.py` para no reactivar cuentas revocadas ni exponer `--password` en CLI.
   - Hacer atómico el contador de intentos fallidos mediante script Lua (`INCR` + `EXPIRE`) agregando cuota global por `correo` además de IP confiable; normalizar minúsculas en `accesos.py` antes de `validate_safe_outgoing_url`, usar resolución DNS asíncrona (`getaddrinfo` en event loop + pin de IP), y bloquear `javascript:`, `data:` y `//` en `ComunicadoCreate.enlace_externo` y `_validar_url_evidencia_segura`.
3. **Middleware HTTP, Nginx Productivo/QA y Control RBAC/IDOR:**
   - Exigir validación `X-CSRF-Token` siempre que la autenticación provenga de cookie `HttpOnly` (eliminando el bypass con `Authorization: Bearer dummy`), proteger `/metrics` con token interno o puerto interno aislado, validar `ALLOWED_HOSTS` / `X-Forwarded-Proto` confiable y asegurar cabeceras OSHP incluso en respuestas `500`.
   - Corregir `frontend/nginx.conf`, `frontend/nginx.qa.conf` y `frontend/Dockerfile`: repetir las cabeceras OSHP/CSP dentro de `location /assets/`, activar `gzip on` en producción, provisionar `/tmp/nginx_{fastcgi,uwsgi,scgi}_temp` para el usuario `101:101` y homogeneizar `client_max_body_size 2M` y `Cache-Control: no-store`.
   - Bloquear la escalación `VICEPRESIDENTE -> PRESIDENTE` en `PUT /api/usuarios/{id}/asignar`, exigir `ContratoOcupacion.fecha_fin.is_(None)` en `_verificar_acceso_unidad`, restringir `GET /api/estructura/unidades`, `GET /api/finanzas/resumen`, `GET /api/paqueteria`, `GET /api/reservas` y `GET /api/accesos/pases/mios` para no filtrar saldos ni datos personales a roles no autorizados, y activar fail-closed en `verificar_usuario_activo`.

### 2.3. Hito 21: Exactitud Contable LPH, Idempotencia con Replay y Worker Productivo
1. **Desacoplo de Cargos Cross-Módulo e Integridad Contable (`facturacion_lph.py`, `finanzas.py`, `reservas.py`, `pagos.py`):**
   - Resolver el deadlock `HTTP 409` en `facturar-periodo`: registrar daños de amenidades (`FINALIZADA_CON_DANOS`) y `AreaSocial.costo_uso_usd > 0` como cargos individuales pendientes o fusionarlos mediante `UPSERT` en `persistir_lote_facturacion` anexando sus `ReciboItem` al recibo mensual de la unidad.
   - Impedir `POST /api/finanzas/cierre-mensual` mientras existan pagos `EN_REVISION`, añadir `with_for_update()` e `Idempotency-Key` en `PUT /api/pagos/{id}/rechazar` y corregir los estados registrados en `AuditoriaRecibo`.
   - Cuadrar `sum(ReciboItem) == Recibo.monto_usd` al aplicar `credito_disponible_usd` al `100%` (dejando traza contable en `AuditoriaRecibo`), validar existencia y no-negatividad de `FondoCondominio`, corregir `Decimal("0.00")` falsy y `recibo.id or idx` en `facturacion_lph.py`, ajustar `MAYORIA_SIMPLE` a `> Decimal("50.0000")`, rechazar montos negativos en `convertir_a_usd`/`aplicar_pago`, y acotar `Decimal` (`allow_inf_nan=False`, techo `le`) y regex de mes `01..12` en `schemas.py`.
2. **Idempotencia Unificada, Contratos API y Worker Productivo (`worker.py`, `routers/*.py`):**
   - Implementar dependencia unificada `idemp:{condominio_id}:{usuario_id}:{scope}:{key}` con *response replay* y liberación automática ante errores `4xx/5xx`, cubriendo las 14 mutaciones faltantes (`operaciones.py`, `administracion.py`, `finanzas.py`, `pagos.py`, `incidencias.py`, `accesos.py`, `reservas.py`).
   - Añadir paginación acotada (`limit`/`offset`) en los 14 listados `GET`, `response_model` en los 7 endpoints faltantes, cierres `with_for_update()` en adhesiones, cuota de 30 fotos/mes, escaneo QR y entrega de paquetes, y validaciones temporales en cierre de consultas y vigencia de pases QR.
   - Conectar subida segura de comprobantes/evidencias (`read_uploaded_file_safely` + `validate_file_magic_bytes`) con la cola media del worker (`convertir_y_subir_avif`), acotar `Image.MAX_IMAGE_PIXELS`, aplicar RFC 3986 en `_build_sigv4_headers`, capturar `RedisError` y JSON no-objeto, migrar `BLPOP` a `BLMOVE` con backoff/DLQ acotado, respetar `PlantillaTarea.frecuencia`, corregir `find_worker.py` y desacoplar el `HEALTHCHECK` por `CONTAINER_ROLE` en `backend/Dockerfile`.

### 2.4. Hito 22: Rescate Frontend Vue 3 Mobile-First, Shell Unificado y Accesibilidad WCAG 2.2 AA
1. **Aislamiento de Sesión SPA, Cliente HTTP y Contratos Tipados:**
   - Limpiar `financeStore`, `governanceStore`, `operationsStore`, `accessAmenitiesStore` y `activeCsrfToken` al ejecutar `clearSession`/`logout`/`401`, corregir ruta `/register` en `authStore.ts:175` y `await authStore.logout()` en `PendingApprovalView.vue`.
   - Endurecer `isSafeRedirectUrl` frente a caracteres de control (`\t`, `\r`, `\n`), sustituir `Math.random()` por `crypto.getRandomValues()` en `generateIdempotencyKey`, soportar `FormData` + `.delete()`/`.patch()` + `try/catch` en `apiClient.ts`, conservar la misma `Idempotency-Key` entre reintentos de una misma acción y eliminar el doble escapado HTML de `sanitizeUntrustedText()` en interpolaciones `{{ ... }}`.
   - Alinear el 100% de DTOs en stores con `backend/src/schemas.py` (`TasaCambioDTO`, `url_comprobante`, `ComunicadoDTO.enlace_externo`, `UsuarioAsignarRequestDTO`, `EgresoCreateDTO`, `PaseVisitaCreateDTO`, `jti`, consumo real de `/api/comunicados`), y separar errores de mutación (`isStale = false` salvo error de red en `GET`).
2. **Arquitectura de Rutas `<AppShellLayout>` y Navegación Móvil Completa:**
   - Definir una ruta padre con `<AppShellLayout>` en `frontend/src/router/index.ts` para todas las rutas autenticadas (corrigiendo automáticamente las 6 vistas huérfanas), agregar ruta catch-all `404`, ejecutar `fetchProfile()` en recarga fría de `/login` y `/register` con `?redirect=` validado, migrar vistas a `() => import(...)` y añadir cajón móvil completo más botón accesible de **Cerrar sesión** en `< 768px`.
3. **Corrección de Vistas Críticas, tokens OKLCH e Invariantes 11X:**
   - Desacoplar `GET /api/finanzas/tasa` con `Promise.allSettled` en `financeStore.ts` para evitar el apagón diario por `404` y jamás mostrar `✓ Solvente / Al día` cuando `resumen` es `null`.
   - Reemplazar `fetchAdminData()` por `fetchUnidades()` en `SolvencyCertificateView.vue` (eliminando el `403` universal), poblar recibos reales y subida real de comprobantes en `PaymentWizardView.vue`, renderizar `<img>` en `SpokespersonGalleryView.vue` e `IncidentCard.vue`, mostrar errores de mutación en vistas admin y ocultar formularios/acciones restringidas según RBAC.
   - Aplicar `String(val.value ?? '').trim()` en todos los `<input type="number">` y eliminar `v-model.number` sin guarda; eliminar UUIDs/JTIs/PKs crudos de la UI (`UI-11X-02`) usando selectores legibles y `authStore.data?.unidad_activa_id`; reemplazar badges catch-all invertidos (`✓ CERRADA_RECHAZADA`, fondo verde en solvencia inválida); corregir `contain-intrinsic-size` en `tokens.css:555`, `ExpensesDonutChart.vue`, `CollectionTrafficLight.vue` (`PAGADO_PARCIAL`), aritmética decimal `ROUND_HALF_UP`, `<dialog>` Top-Layer con composable único, colores hex residuales a `OKLCH`/`light-dark()`, `ThemeToggleButton`, tabs ARIA, áreas táctiles `>= 44px` e implementar `useDualRefresh` (`setInterval` + `clearInterval` + `[ 🔄 Refrescar ]`) en todas las bandejas operativas/financieras.

### 2.5. Hito 23: Erradicación de `Anti-Mock Blindness` QA 11X y Saneamiento Documental Thin-Repo
1. **Fortalecimiento Real de QA Backend (`backend/tests/`, `api_test.feature`, `locustfile.py`):**
   - Crear suites `.unit.py` para `database.py`, `facturacion_lph.py`, `redis_client.py`, `administracion.py` e `incidencias.py`; cubrir las 27 tablas en `test_models.unit.py` y todos los esquemas dinámicamente en `test_schemas.unit.py` y `test_security_11x.unit.py`.
   - Activar `PRAGMA foreign_keys=ON` en fixtures SQLite, migrar suites de `_mock_session` a base de datos real con `try...finally: app.dependency_overrides.clear()`, eliminar roles ficticios (`RESIDENTE`), ejecutar pruebas HTTP end-to-end y de concurrencia (`asyncio.gather`) contra PostgreSQL 17 real en `make qa-parity`.
   - Endurecer `radon_gates.py` a Grado A (`MAX_GRADE = 1`), corregir `mutmut_gates.py` (sin contar `timeout`/`SIGKILL` como mutantes matados, cubriendo todos los módulos de `src/`), conectar `zap.yaml` en `make qa-dast` (fallando en `WARN-NEW` sin `user: root`), reparar `locustfile.py` + `make qa-profile` y ampliar `backend/test/api_test.feature` con flujos nominales `2xx` aislados por UUID para los 9 routers.
2. **Fortalecimiento Real de QA Frontend (`unit.ts`, `e2e/`, `ui_business_flow.feature`):**
   - Añadir `navIcons.unit.ts` y `main.unit.ts`, mover Stryker a `qa-vue3` ampliando cobertura a stores/router/composables, aislar `vitest/globals` en `tsconfig.json` respecto a `e2e/`, incluir `e2e/` y `tokens.css` en ESLint/Prettier (planificando migración a ESLint 9 flat config) y configurar Lighthouse multi-corrida (`CLS = 0`).
   - Sincronizar `condominioApiMock.ts` 1:1 con los esquemas OpenAPI y RBAC reales (incluyendo `403` y `404` matutino de tasa), cubrir `22/22` vistas en `accessibility.e2e.ts` (incluyendo `best-practice`), añadir `consultation-detail-dark` y viewport Tablet `768x1024` en Playwright, eliminar selectores crudos fuera de Screenplay e incorporar flujos autenticados punta a punta por rol en `frontend/test/ui_business_flow.feature`.
3. **Saneamiento Documental Integral (`DOCS_ONLY` / Sincronización):**
   - Corregir los comandos de restauración (`api`/`worker`, `condominio_admin`, `pg17_${FECHA}.dump.gz[.enc]`) y guías de `MANUAL_ADMINISTRADOR_E_INSTALADOR.md` y `MANUAL_USUARIO_RESIDENTE.md`; sincronizar las rutas reales en `API_ROUTES.md`, roles en `ARCHITECTURE.md`, conteo exacto de `22` vectores en `SECURITY.md` y consolidar `CHANGELOG.md` / `TESTING.md` / `frontend/TESTING.md` / `backend/TESTING.md`.
   - Podar y adelgazar `docs/qa/*` bajo arquitectura Thin-Repo eliminando duplicados obsoletos y referencias rotas; actualizar metadatos y enlaces en `docs/specs/01..12` (añadiendo trazabilidad de enmiendas); rediseñar `README.md` raíz con badges, *Quickstart* Docker Hub y crear `backend/README.md` y `frontend/README.md`.

---

## 3. FASE 8: Completitud Funcional PropTech Prometida (`v1.2.0` — Hitos 24 al 26)

### 3.1. Hito 24: Recuperación de Contraseña, Selector Multi-Inmueble y Estacionamientos/Maleteros (Migración `0011`)
1. **Recuperación de Contraseña Autoservicio y Reseteo Temporal por Junta:**
   - Backend (`auth.py`, `administracion.py`, `redis_client.py`, `worker.py`): endpoints `POST /api/auth/forgot-password` y `POST /api/auth/reset-password` con respuesta uniforme anti-enumeración, token aleatorio de un solo uso (`>= 256 bits`, `TTL <= 900s` en KeyDB, envío SMTP vía worker), más endpoint `POST /api/usuarios/{id}/reset-password-temporal` para Junta Directiva con bandera `debe_cambiar_password = True` y revocación inmediata de todas las sesiones activas al cambiar clave.
   - Frontend: rutas `/recuperar-clave` y cambio obligatorio tras login temporal integradas al flujo de autenticación.
2. **Selector de Unidad Activa (`unidad_activa_id`) para Propietarios Multi-Inmueble:**
   - Backend: endpoint `PUT /api/auth/unidad-activa` validando `ContratoOcupacion` vigente (`fecha_fin IS NULL`) y retornando perfil actualizado con todas las unidades ocupadas del usuario.
   - Frontend: selector global de inmueble activo en `AppShellLayout.vue` / `SidebarNav.vue` que refresca `authStore`, `financeStore`, `accessAmenitiesStore` y `governanceStore` para filtrar recibos, solvencias, pases QR y votos por la unidad seleccionada.
3. **Puestos de Estacionamiento y Maleteros en Constructor de Estructura (Migración `0011`):**
   - ORM/Alembic (`0011_funcionalidad_proptech_complementaria.py`): modelado de unidades accesorias o atributos vinculados (`PuestoEstacionamiento` / `Maletero` asignables a `Unidad` con opción de alícuota/tarifa asociada) y endpoints CRUD bajo `administracion.py`.
   - Frontend: extensión de `AdminStructureView.vue` para asignar/editar puestos de estacionamiento y maleteros, reflejándolos en la ficha de la unidad, desglose de recibos y certificados de solvencia.

### 3.2. Hito 25: Motor PDF Determinista + Envío SMTP y Código QR Gráfico Real con Escáner de Cámara
1. **Generación de Documentos PDF Deterministas y Distribución SMTP:**
   - Motor PDF ligero compatible con imagen productiva `--no-dev` no-root (`read_only: true`, generación en `/tmp` y almacenamiento opcional en MinIO): generación de **Recibo de Condominio** (`PRELIMINAR` al emitir facturación/Día 1 y `OFICIAL` tras cierre mensual) y **Certificado de Solvencia Digital**.
   - Endpoints `GET /api/finanzas/recibos/{recibo_id}/pdf` y `GET /api/finanzas/solvencia/{certificado_id}/pdf` (con `Content-Disposition: attachment` y validación estricta RBAC/titularidad), además de cola en `worker.py` para envío automático por correo SMTP al aprobar cierre o emitir certificado.
   - Botones de descarga y solicitud de envío por correo en `DashboardView.vue`, `ReceiptBreakdownModal.vue` y `SolvencyCertificateView.vue`.
2. **Código QR Gráfico Real (SVG/Canvas) y Escáner Óptico por Cámara:**
   - Generación local determinista en cliente (SVG/Canvas sin llamadas a APIs externas, respetando CSP estricto) del código QR firmado en `VisitorPassesView.vue` y `SolvencyCertificateView.vue`, con opción de descarga/impresión del pase.
   - Escáner en tiempo real mediante cámara web en `GatehouseScannerView.vue` (`MediaDevices.getUserMedia` + `BarcodeDetector` / decodificador local puro en bundle) manteniendo el campo manual `#input-scan-qr-token` como fallback accesible, y ajuste acotado `Permissions-Policy: camera=(self)` en `frontend/nginx.conf` / `nginx.qa.conf`.

### 3.3. Hito 26: Notificaciones en Vivo por WebSocket (`/ws/`) Autenticado y Cierre `v1.2.0`
1. **Servidor WebSocket FastAPI + Pub/Sub KeyDB:**
   - Endpoint `WS /ws/notificaciones` autenticado mediante sesión/cookie verificada al handshake, validando `verify_websocket_origin` (`ALLOWED_ORIGINS`), rechazo ante sesiones revocadas, heartbeat `ping/pong` y distribución multi-worker vía canales Pub/Sub en KeyDB por condominio/rol/unidad ante eventos de comunicados, aprobación de pagos, llegada de paquetes, uso de pase QR, apertura/cierre de consultas e incidencias.
2. **Proxy Nginx/Vite, Composable SPA y Certificación `v1.2.0`:**
   - Habilitación del proxy `/ws/` con soporte `Upgrade`/`Connection` en `frontend/vite.config.ts` y `frontend/nginx.conf` / `nginx.qa.conf` respetando `connect-src 'self' ws: wss:`.
   - Composable `useRealtimeNotifications` con reconexión con backoff exponencial integrando actualizaciones en vivo junto a `useDualRefresh` (`[ 🔄 Refrescar ]` siempre disponible como respaldo).
   - Certificación integral de los 13 niveles QA 11X (incluyendo pruebas E2E WebSocket, caos Pumba sobre desconexiones WS, `Trivy HIGH/CRITICAL = 0`, actualización de manuales y tag de lanzamiento multi-arch `v1.2.0` en Docker Hub).
