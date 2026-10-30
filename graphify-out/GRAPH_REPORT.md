# Graph Report - app  (2026-10-30)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1081 nodes · 2491 edges · 61 communities (45 shown, 16 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 125 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- test_hito4_operaciones.unit.py
- os
- test_finanzas_core.unit.py
- main.py
- vitest
- RegisterView.vue
- authStore.ts
- test_pagos.unit.py
- operaciones.py
- operationsStore.ts
- schemas.py
- test_auth.unit.py
- test_schemas.unit.py
- test_finanzas_router.unit.py
- AppShellLayout.vue
- security.ts
- security.py
- PaymentWizardView.vue
- administracion.py
- devDependencies
- frontend/package.json
- auth.py
- compilerOptions
- TreasuryClosingView.vue
- test_security_11x.unit.py
- pagos.py
- generar_estructura
- test_dependencies.unit.py
- package.json
- scripts
- redis_client.py
- financeStore.ts
- routers/finanzas.py
- crear_incidencia
- read_uploaded_file_safely
- RejectPaymentModal.vue
- stryker.conf.json
- CondominioStressUser
- test_main.unit.py
- CollectionTrafficLight.vue
- TreasuryPaymentsView.vue
- AnnouncementsCarousel.vue
- DashboardView.vue
- vue
- ExpensesDonutChart.vue
- @playwright/test
- dependencies
- @vitejs/plugin-vue
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
4. `_mock_session()` - 27 edges
5. `_setup()` - 27 edges
6. `vue` - 27 edges
7. `verificar_roles()` - 25 edges
8. `pinia` - 24 edges
9. `Base` - 23 edges
10. `_result()` - 19 edges

## Surprising Connections (you probably didn't know these)
- `lifespan()` --uses--> `Base`  [INFERRED]
  backend/src/main.py → backend/src/database.py
- `aprobar_pago()` --uses--> `AuditoriaRecibo`  [INFERRED]
  backend/src/routers/pagos.py → backend/src/models.py
- `rechazar_pago()` --uses--> `AuditoriaRecibo`  [INFERRED]
  backend/src/routers/pagos.py → backend/src/models.py
- `crear_acta_bitacora()` --uses--> `BitacoraActa`  [INFERRED]
  backend/src/routers/operaciones.py → backend/src/models.py
- `listar_historial_bitacora()` --uses--> `BitacoraActa`  [INFERRED]
  backend/src/routers/operaciones.py → backend/src/models.py

## Import Cycles
- None detected.

## Communities (61 total, 16 thin omitted)

### Community 0 - "test_hito4_operaciones.unit.py"
Cohesion: 0.05
Nodes (45): Base, AuditoriaRecibo, BitacoraActa, Comunicado, ContratoOcupacion, Egreso, Estructura, FotoVocero (+37 more)

### Community 1 - "os"
Cohesion: 0.05
Nodes (24): assess_risk_level(), compute_blast_radius(), find_graph_files(), find_matching_nodes(), inspect_symbol(), load_graph(), main(), audit_json_file() (+16 more)

### Community 2 - "test_finanzas_core.unit.py"
Cohesion: 0.08
Nodes (39): aplicar_pago(), calcular_deuda_total(), calcular_saldo_pendiente(), convertir_a_usd(), cuantizar(), determinar_estado_recibo(), ErrorFinanciero, requiere_referencia() (+31 more)

### Community 3 - "main.py"
Cohesion: 0.05
Nodes (14): get_migrated_tables(), get_orm_tables(), main(), _resolve_migrations_dir(), _resolve_model_files(), _es_produccion(), health_check(), http_exception_handler() (+6 more)

### Community 4 - "vitest"
Cohesion: 0.12
Nodes (16): apiClient, ApiError, apiRequest(), extractErrorDetail(), getCsrfToken(), MUTATING_METHODS, RequestOptions, setCsrfToken() (+8 more)

### Community 5 - "RegisterView.vue"
Cohesion: 0.06
Nodes (37): useIdempotency(), executeWithIdempotency(), rotateKey(), UseIdempotencyReturn, TipoEstructura, generateIdempotencyKey(), { currentKey, rotateKey }, handleGenerateStructure() (+29 more)

### Community 6 - "authStore.ts"
Cohesion: 0.08
Nodes (28): pushMock, app, buildAppRouter(), evaluateNavigationGuard(), routes, AsyncStoreState, RegistroPayload, PERFIL_ACTIVO (+20 more)

### Community 7 - "test_pagos.unit.py"
Cohesion: 0.23
Nodes (32): FakeUser, _mock_session(), _pago(), _recibo(), _result(), _result_list(), _setup(), _tasa() (+24 more)

### Community 8 - "operaciones.py"
Cohesion: 0.14
Nodes (14): verificar_roles(), verificar_usuario_activo(), Usuario, asignar_tarea_directa(), completar_tarea_diaria(), crear_acta_bitacora(), crear_plantilla_tarea(), ejecutar_cronjob_tareas_diarias() (+6 more)

### Community 9 - "operationsStore.ts"
Cohesion: 0.08
Nodes (25): emit, UsuarioPerfil, BitacoraActaCreateDTO, BitacoraActaDTO, EstadoIncidencia, EstructuraGenerarRequestDTO, EstructuraGenerarResponseDTO, FotoVoceroCreateDTO (+17 more)

### Community 10 - "schemas.py"
Cohesion: 0.12
Nodes (26): BitacoraActaCreate, BitacoraActaResponse, ComunicadoCreate, ComunicadoResponse, EstructuraGenerarRequest, EstructuraGenerarResponse, FotoVoceroCreate, FotoVoceroResponse (+18 more)

### Community 11 - "test_auth.unit.py"
Cohesion: 0.09
Nodes (12): test_login_invalid_credentials(), test_login_set_httponly_cookie(), test_me_with_expired_token(), test_me_with_invalid_token(), test_me_with_valid_token_success(), test_me_without_cookie_fails(), test_register_missing_idempotency_key(), test_register_user_already_registered() (+4 more)

### Community 12 - "test_schemas.unit.py"
Cohesion: 0.13
Nodes (23): CierreMensualRequest, EgresoCreate, PagoRechazo, PagoReportar, ReciboCreate, TasaCambioCreate, test_cierre_mensual_request_periodo_invalido(), test_cierre_mensual_request_valido() (+15 more)

### Community 13 - "test_finanzas_router.unit.py"
Cohesion: 0.25
Nodes (23): _egreso(), FakeUser, _mock_session(), _recibo(), _result(), _result_list(), _setup(), _tasa() (+15 more)

### Community 14 - "AppShellLayout.vue"
Cohesion: 0.09
Nodes (19): authStore, route, router, emit, items, NavItem, props, emit (+11 more)

### Community 15 - "security.ts"
Cohesion: 0.09
Nodes (20): emit, IncidenciaDTO, ALLOWED_PROOF_MIME_TYPES, DANGEROUS_KEYS, escapeHtml(), FileValidationResult, MAX_UPLOAD_BYTES, sanitizeUntrustedText() (+12 more)

### Community 16 - "security.py"
Cohesion: 0.13
Nodes (10): generate_csrf_token(), get_password_hash(), _is_forbidden_ip(), _pbkdf2_digest(), _resolve_and_validate_ips(), validate_csrf_token(), verify_password(), test_csrf_token_generation_and_validation() (+2 more)

### Community 17 - "PaymentWizardView.vue"
Cohesion: 0.09
Nodes (21): convertVesToUsd(), determinePaymentCoverage(), validateProofFileUpload(), coverageType, { currentKey, isSubmitting, executeWithIdempotency }, currentStep, equivalentUsd, financeStore (+13 more)

### Community 18 - "administracion.py"
Cohesion: 0.17
Nodes (3): get_db(), extract_bearer_or_cookie_token(), get_current_user()

### Community 19 - "devDependencies"
Cohesion: 0.09
Nodes (22): devDependencies, @axe-core/playwright, eslint, eslint-config-prettier, eslint-plugin-sonarjs, eslint-plugin-vue, jsdom, @lhci/cli (+14 more)

### Community 20 - "frontend/package.json"
Cohesion: 0.10
Nodes (20): description, name, private, type, version, eslint, eslint-config-prettier, eslint-plugin-sonarjs (+12 more)

### Community 21 - "auth.py"
Cohesion: 0.14
Nodes (6): get_me(), login(), LoginData, register_user(), UsuarioCreate, decode_access_token()

### Community 22 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+10 more)

### Community 23 - "TreasuryClosingView.vue"
Cohesion: 0.12
Nodes (14): MonedaPago, cierrePeriodo, closeClosingModal(), confirmModalOpen, confirmMonthlyClosing(), dialogRef, egresoCategoria, egresoDescripcion (+6 more)

### Community 24 - "test_security_11x.unit.py"
Cohesion: 0.20
Nodes (9): get_redis_client(), validate_safe_outgoing_url(), verify_websocket_origin(), test_get_redis_client_singleton(), test_validate_safe_outgoing_url_dns_failure(), test_validate_safe_outgoing_url_rejects_bad_scheme_or_internal_host(), test_validate_safe_outgoing_url_rejects_private_and_metadata_ips(), test_validate_safe_outgoing_url_valid_public_ip() (+1 more)

### Community 25 - "pagos.py"
Cohesion: 0.24
Nodes (7): aprobar_pago(), listar_pagos_en_revision(), _obtener_pago(), _obtener_recibo(), obtener_tasa_del_dia(), rechazar_pago(), reportar_pago()

### Community 26 - "generar_estructura"
Cohesion: 0.15
Nodes (5): asignar_cargo_junta(), asignar_y_activar_usuario(), generar_estructura(), listar_unidades(), listar_usuarios_pendientes()

### Community 27 - "test_dependencies.unit.py"
Cohesion: 0.28
Nodes (10): create_access_token(), FakeUser, _result(), _session(), test_endpoint_protegido_sin_cookie(), test_token_expirado(), test_token_invalido(), test_token_sin_identificacion() (+2 more)

### Community 28 - "package.json"
Cohesion: 0.14
Nodes (13): description, devDependencies, @commitlint/cli, @commitlint/config-conventional, @evilmartians/lefthook, name, private, scripts (+5 more)

### Community 29 - "scripts"
Cohesion: 0.15
Nodes (13): scripts, audit:deps, build, dev, format, format:check, lint, mutate (+5 more)

### Community 30 - "redis_client.py"
Cohesion: 0.26
Nodes (5): build_idempotency_key(), check_and_set_idempotency_key(), get_refresh_token_from_grace_period(), rotate_refresh_token_with_grace_period(), test_redis_scoped_idempotency_and_grace_period()

### Community 31 - "financeStore.ts"
Cohesion: 0.17
Nodes (11): CierreMensualDTO, EgresoCreateDTO, EstadoPago, EstadoRecibo, FinanceStateData, MetodoPago, PagoDTO, PagoReportarDTO (+3 more)

### Community 32 - "routers/finanzas.py"
Cohesion: 0.38
Nodes (5): cierre_mensual(), obtener_tasa(), registrar_egreso(), registrar_tasa(), resumen_financiero()

### Community 33 - "crear_incidencia"
Cohesion: 0.22
Nodes (3): adherir_a_incidencia(), crear_incidencia(), listar_incidencias_abiertas()

### Community 34 - "read_uploaded_file_safely"
Cohesion: 0.24
Nodes (5): AsyncChunkReader, read_uploaded_file_safely(), _DummyUpload, test_read_uploaded_file_safely_exceeds_quota_raises_413(), test_read_uploaded_file_safely_within_quota()

### Community 35 - "RejectPaymentModal.vue"
Cohesion: 0.28
Nodes (8): dialogRef, emit, handleCancel(), handleConfirm(), isMotivoValid, motivo, props, touched

### Community 36 - "stryker.conf.json"
Cohesion: 0.22
Nodes (8): mutate, reporters, $schema, testRunner, thresholds, break, high, low

### Community 38 - "test_main.unit.py"
Cohesion: 0.32
Nodes (3): test_health_check(), test_options_405_incluye_allow_completo(), test_respuestas_no_cacheables()

### Community 39 - "CollectionTrafficLight.vue"
Cohesion: 0.29
Nodes (7): formatVes(), props, sortedItems, convertUsdToVes(), EstadoCobranzaItemDTO, deudaTotalVes, equivalentVes

### Community 40 - "TreasuryPaymentsView.vue"
Cohesion: 0.25
Nodes (4): actionMessage, financeStore, rejectModalOpen, selectedPagoId

### Community 41 - "AnnouncementsCarousel.vue"
Cohesion: 0.29
Nodes (4): activeIndex, currentItem, props, ComunicadoDTO

### Community 42 - "DashboardView.vue"
Cohesion: 0.29
Nodes (5): activeTab, authStore, deudaTotalUsd, financeStore, router

### Community 43 - "vue"
Cohesion: 0.33
Nodes (4): props, shouldRender, *.vue, vue

### Community 44 - "ExpensesDonutChart.vue"
Cohesion: 0.40
Nodes (4): CategorySlice, PALETTE, props, slices

### Community 46 - "dependencies"
Cohesion: 0.50
Nodes (4): dependencies, pinia, vue, vue-router

## Knowledge Gaps
- **19 isolated node(s):** `eslint`, `eslint-config-prettier`, `eslint-plugin-sonarjs`, `eslint-plugin-vue`, `jsdom` (+14 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 487 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `vue` connect `vue` to `RejectPaymentModal.vue`, `RegisterView.vue`, `authStore.ts`, `CollectionTrafficLight.vue`, `TreasuryPaymentsView.vue`, `AnnouncementsCarousel.vue`, `operationsStore.ts`, `DashboardView.vue`, `ExpensesDonutChart.vue`, `AppShellLayout.vue`, `security.ts`, `PaymentWizardView.vue`, `frontend/package.json`, `TreasuryClosingView.vue`, `financeStore.ts`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 33 inferred relationships involving `Usuario` (e.g. with `get_current_user()` and `verificar_roles()`) actually correct?**
  _`Usuario` has 33 INFERRED edges - model-reasoned connections that need verification._
- **What connects `eslint`, `eslint-config-prettier`, `eslint-plugin-sonarjs` to the rest of the system?**
  _19 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_hito4_operaciones.unit.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05070028011204482 - nodes in this community are weakly interconnected._
- **Why does `Usuario` connect `operaciones.py` to `test_hito4_operaciones.unit.py`, `routers/finanzas.py`, `crear_incidencia`, `administracion.py`, `auth.py`, `pagos.py`, `generar_estructura`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Should `os` be split into smaller, more focused modules?**
  _Cohesion score 0.05480225988700565 - nodes in this community are weakly interconnected._
- **Why does `create_access_token()` connect `test_dependencies.unit.py` to `main.py`, `test_auth.unit.py`, `security.py`, `auth.py`, `test_security_11x.unit.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._