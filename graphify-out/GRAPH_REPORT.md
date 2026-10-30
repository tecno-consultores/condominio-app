# Graph Report - app  (2026-10-30)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1075 nodes · 2464 edges · 59 communities (40 shown, 19 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 125 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- test_finanzas_router.unit.py
- test_finanzas_core.unit.py
- os
- test_auth.unit.py
- main.py
- RegisterView.vue
- test_hito4_operaciones.unit.py
- test_pagos.unit.py
- vitest
- AppShellLayout.vue
- Usuario
- test_schemas.unit.py
- operationsStore.ts
- operaciones.py
- authStore.ts
- security.ts
- security.py
- devDependencies
- PaymentWizardView.vue
- test_security_11x.unit.py
- frontend/package.json
- compilerOptions
- incidencias.py
- administracion.py
- TreasuryClosingView.vue
- auth.py
- DashboardView.vue
- LoginView.vue
- package.json
- scripts
- register_user
- financeStore.ts
- vue
- read_uploaded_file_safely
- OperationsTasksView.vue
- RejectPaymentModal.vue
- stryker.conf.json
- CondominioStressUser
- TreasuryPaymentsView.vue
- AnnouncementsCarousel.vue
- get_current_user
- listar_galeria_voceros
- @playwright/test
- dependencies
- @vitejs/plugin-vue
- _validar_correo
- certify_task_completion.sh
- auditar-infra.sh
- backend/limpieza.sh
- frontend/limpieza.sh
- instalar-hooks.sh
- scripts/limpieza.sh
- verificar-secretos.sh
- condominio-app-backend

## God Nodes (most connected - your core abstractions)
1. `Usuario` - 46 edges
2. `vitest` - 36 edges
3. `@vue/test-utils` - 28 edges
4. `vue` - 27 edges
5. `_mock_session()` - 26 edges
6. `_setup()` - 26 edges
7. `pinia` - 24 edges
8. `Base` - 23 edges
9. `_result()` - 19 edges
10. `convertir_a_usd()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `lifespan()` --uses--> `Base`  [INFERRED]
  backend/src/main.py → backend/src/database.py
- `aprobar_pago()` --uses--> `AuditoriaRecibo`  [INFERRED]
  backend/src/routers/pagos.py → backend/src/models.py
- `rechazar_pago()` --uses--> `AuditoriaRecibo`  [INFERRED]
  backend/src/routers/pagos.py → backend/src/models.py
- `asignar_cargo_junta()` --uses--> `ContratoOcupacion`  [INFERRED]
  backend/src/routers/administracion.py → backend/src/models.py
- `asignar_y_activar_usuario()` --uses--> `ContratoOcupacion`  [INFERRED]
  backend/src/routers/administracion.py → backend/src/models.py

## Import Cycles
- None detected.

## Communities (59 total, 19 thin omitted)

### Community 0 - "test_finanzas_router.unit.py"
Cohesion: 0.06
Nodes (47): Base, get_db(), AuditoriaRecibo, ContratoOcupacion, Egreso, Estructura, PagoReportado, Recibo (+39 more)

### Community 1 - "test_finanzas_core.unit.py"
Cohesion: 0.06
Nodes (46): aplicar_pago(), calcular_deuda_total(), calcular_saldo_pendiente(), convertir_a_usd(), cuantizar(), determinar_estado_recibo(), ErrorFinanciero, requiere_referencia() (+38 more)

### Community 2 - "os"
Cohesion: 0.05
Nodes (24): assess_risk_level(), compute_blast_radius(), find_graph_files(), find_matching_nodes(), inspect_symbol(), load_graph(), main(), audit_json_file() (+16 more)

### Community 3 - "test_auth.unit.py"
Cohesion: 0.05
Nodes (26): create_access_token(), decode_access_token(), test_login_invalid_credentials(), test_login_set_httponly_cookie(), test_me_with_expired_token(), test_me_with_invalid_token(), test_me_with_valid_token_success(), test_me_without_cookie_fails() (+18 more)

### Community 4 - "main.py"
Cohesion: 0.06
Nodes (12): get_migrated_tables(), get_orm_tables(), main(), _resolve_migrations_dir(), _resolve_model_files(), health_check(), http_exception_handler(), lifespan() (+4 more)

### Community 5 - "RegisterView.vue"
Cohesion: 0.06
Nodes (37): useIdempotency(), executeWithIdempotency(), rotateKey(), UseIdempotencyReturn, TipoEstructura, generateIdempotencyKey(), { currentKey, rotateKey }, handleGenerateStructure() (+29 more)

### Community 6 - "test_hito4_operaciones.unit.py"
Cohesion: 0.11
Nodes (23): BitacoraActa, Comunicado, IncidenciaAdhesion, PlantillaTarea, TareaDiaria, convertir_y_subir_avif(), encolar_notificacion_correo(), generar_tareas_diarias_desde_plantillas() (+15 more)

### Community 7 - "test_pagos.unit.py"
Cohesion: 0.24
Nodes (31): FakeUser, _mock_session(), _pago(), _recibo(), _result(), _result_list(), _setup(), _tasa() (+23 more)

### Community 8 - "vitest"
Cohesion: 0.16
Nodes (15): apiClient, ApiError, apiRequest(), extractErrorDetail(), getCsrfToken(), MUTATING_METHODS, RequestOptions, setCsrfToken() (+7 more)

### Community 9 - "AppShellLayout.vue"
Cohesion: 0.08
Nodes (19): authStore, route, router, emit, items, NavItem, props, emit (+11 more)

### Community 10 - "Usuario"
Cohesion: 0.12
Nodes (13): verificar_roles(), Usuario, asignar_tarea_directa(), completar_tarea_diaria(), crear_acta_bitacora(), crear_plantilla_tarea(), ejecutar_cronjob_tareas_diarias(), listar_comunicados_recientes() (+5 more)

### Community 11 - "test_schemas.unit.py"
Cohesion: 0.14
Nodes (23): CierreMensualRequest, EgresoCreate, PagoRechazo, PagoReportar, ReciboCreate, TasaCambioCreate, UsuarioCreate, test_cierre_mensual_request_periodo_invalido() (+15 more)

### Community 12 - "operationsStore.ts"
Cohesion: 0.09
Nodes (21): emit, UsuarioPerfil, BitacoraActaCreateDTO, BitacoraActaDTO, EstadoIncidencia, EstructuraGenerarRequestDTO, EstructuraGenerarResponseDTO, FotoVoceroCreateDTO (+13 more)

### Community 13 - "operaciones.py"
Cohesion: 0.17
Nodes (23): BitacoraActaCreate, BitacoraActaResponse, ComunicadoCreate, ComunicadoResponse, EstructuraGenerarRequest, EstructuraGenerarResponse, FotoVoceroCreate, FotoVoceroResponse (+15 more)

### Community 14 - "authStore.ts"
Cohesion: 0.12
Nodes (15): pushMock, app, buildAppRouter(), evaluateNavigationGuard(), routes, AsyncStoreState, RegistroPayload, PERFIL_ACTIVO (+7 more)

### Community 15 - "security.ts"
Cohesion: 0.10
Nodes (21): ALLOWED_PROOF_MIME_TYPES, DANGEROUS_KEYS, escapeHtml(), FileValidationResult, MAX_UPLOAD_BYTES, sanitizeObject(), sanitizeUntrustedText(), UploadableFileLike (+13 more)

### Community 16 - "security.py"
Cohesion: 0.13
Nodes (10): generate_csrf_token(), get_password_hash(), _is_forbidden_ip(), _pbkdf2_digest(), _resolve_and_validate_ips(), validate_csrf_token(), verify_password(), test_csrf_token_generation_and_validation() (+2 more)

### Community 17 - "devDependencies"
Cohesion: 0.09
Nodes (22): devDependencies, @axe-core/playwright, eslint, eslint-config-prettier, eslint-plugin-sonarjs, eslint-plugin-vue, jsdom, @lhci/cli (+14 more)

### Community 18 - "PaymentWizardView.vue"
Cohesion: 0.10
Nodes (19): convertVesToUsd(), determinePaymentCoverage(), coverageType, { currentKey, isSubmitting, executeWithIdempotency }, currentStep, equivalentUsd, financeStore, metodoPago (+11 more)

### Community 19 - "test_security_11x.unit.py"
Cohesion: 0.15
Nodes (10): _es_produccion(), validate_safe_outgoing_url(), verify_websocket_origin(), test_bearer_token_authentication_and_production_422_sanitization(), test_get_redis_client_singleton(), test_validate_safe_outgoing_url_dns_failure(), test_validate_safe_outgoing_url_rejects_bad_scheme_or_internal_host(), test_validate_safe_outgoing_url_rejects_private_and_metadata_ips() (+2 more)

### Community 20 - "frontend/package.json"
Cohesion: 0.10
Nodes (20): description, name, private, type, version, eslint, eslint-config-prettier, eslint-plugin-sonarjs (+12 more)

### Community 21 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+10 more)

### Community 22 - "incidencias.py"
Cohesion: 0.17
Nodes (5): verificar_usuario_activo(), Incidencia, adherir_a_incidencia(), crear_incidencia(), listar_incidencias_abiertas()

### Community 23 - "administracion.py"
Cohesion: 0.16
Nodes (6): asignar_cargo_junta(), asignar_y_activar_usuario(), generar_estructura(), listar_unidades(), listar_usuarios_pendientes(), JuntaCargoRequest

### Community 24 - "TreasuryClosingView.vue"
Cohesion: 0.12
Nodes (14): MonedaPago, cierrePeriodo, closeClosingModal(), confirmModalOpen, confirmMonthlyClosing(), dialogRef, egresoCategoria, egresoDescripcion (+6 more)

### Community 25 - "auth.py"
Cohesion: 0.21
Nodes (6): build_idempotency_key(), check_and_set_idempotency_key(), get_redis_client(), get_refresh_token_from_grace_period(), rotate_refresh_token_with_grace_period(), test_redis_scoped_idempotency_and_grace_period()

### Community 26 - "DashboardView.vue"
Cohesion: 0.16
Nodes (12): formatVes(), props, sortedItems, convertUsdToVes(), EstadoCobranzaItemDTO, activeTab, authStore, deudaTotalUsd (+4 more)

### Community 27 - "LoginView.vue"
Cohesion: 0.15
Nodes (13): isSafeRedirectUrl(), authStore, correo, errorBanner, onSubmit(), password, route, router (+5 more)

### Community 28 - "package.json"
Cohesion: 0.14
Nodes (13): description, devDependencies, @commitlint/cli, @commitlint/config-conventional, @evilmartians/lefthook, name, private, scripts (+5 more)

### Community 29 - "scripts"
Cohesion: 0.15
Nodes (13): scripts, audit:deps, build, dev, format, format:check, lint, mutate (+5 more)

### Community 30 - "register_user"
Cohesion: 0.20
Nodes (4): get_me(), login(), LoginData, register_user()

### Community 31 - "financeStore.ts"
Cohesion: 0.17
Nodes (11): CierreMensualDTO, EgresoCreateDTO, EstadoPago, EstadoRecibo, FinanceStateData, MetodoPago, PagoDTO, PagoReportarDTO (+3 more)

### Community 32 - "vue"
Cohesion: 0.18
Nodes (8): props, shouldRender, CategorySlice, PALETTE, props, slices, *.vue, vue

### Community 33 - "read_uploaded_file_safely"
Cohesion: 0.24
Nodes (5): AsyncChunkReader, read_uploaded_file_safely(), _DummyUpload, test_read_uploaded_file_safely_exceeds_quota_raises_413(), test_read_uploaded_file_safely_within_quota()

### Community 34 - "OperationsTasksView.vue"
Cohesion: 0.20
Nodes (6): emit, TareaDiariaDTO, completedTasks, operationsStore, statusBanner, totalTasks

### Community 35 - "RejectPaymentModal.vue"
Cohesion: 0.28
Nodes (8): dialogRef, emit, handleCancel(), handleConfirm(), isMotivoValid, motivo, props, touched

### Community 36 - "stryker.conf.json"
Cohesion: 0.22
Nodes (8): mutate, reporters, $schema, testRunner, thresholds, break, high, low

### Community 38 - "TreasuryPaymentsView.vue"
Cohesion: 0.25
Nodes (4): actionMessage, financeStore, rejectModalOpen, selectedPagoId

### Community 39 - "AnnouncementsCarousel.vue"
Cohesion: 0.29
Nodes (4): activeIndex, currentItem, props, ComunicadoDTO

### Community 43 - "dependencies"
Cohesion: 0.50
Nodes (4): dependencies, pinia, vue, vue-router

## Knowledge Gaps
- **19 isolated node(s):** `eslint`, `eslint-config-prettier`, `eslint-plugin-sonarjs`, `eslint-plugin-vue`, `jsdom` (+14 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 485 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `vue` connect `vue` to `OperationsTasksView.vue`, `RejectPaymentModal.vue`, `RegisterView.vue`, `TreasuryPaymentsView.vue`, `AnnouncementsCarousel.vue`, `AppShellLayout.vue`, `operationsStore.ts`, `authStore.ts`, `security.ts`, `PaymentWizardView.vue`, `frontend/package.json`, `TreasuryClosingView.vue`, `DashboardView.vue`, `LoginView.vue`, `financeStore.ts`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Are the 33 inferred relationships involving `Usuario` (e.g. with `get_current_user()` and `verificar_roles()`) actually correct?**
  _`Usuario` has 33 INFERRED edges - model-reasoned connections that need verification._
- **What connects `eslint`, `eslint-config-prettier`, `eslint-plugin-sonarjs` to the rest of the system?**
  _19 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_finanzas_router.unit.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06302521008403361 - nodes in this community are weakly interconnected._
- **Why does `Usuario` connect `Usuario` to `test_finanzas_router.unit.py`, `test_finanzas_core.unit.py`, `test_hito4_operaciones.unit.py`, `get_current_user`, `listar_galeria_voceros`, `operaciones.py`, `incidencias.py`, `administracion.py`, `auth.py`, `register_user`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Should `test_finanzas_core.unit.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06126331811263318 - nodes in this community are weakly interconnected._
- **Why does `scripts` connect `scripts` to `frontend/package.json`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._