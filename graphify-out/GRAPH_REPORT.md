# Graph Report - app  (2026-10-30)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1240 nodes · 3040 edges · 64 communities (48 shown, 16 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 180 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- test_finanzas_core.unit.py
- pagos.py
- inspect_blast_radius.py
- test_hito4_operaciones.unit.py
- vitest
- routers/finanzas.py
- main.py
- test_pagos.unit.py
- auth.py
- schemas.py
- AppShellLayout.vue
- RegisterView.vue
- administracion.py
- test_finanzas_router.unit.py
- test_schemas.unit.py
- operationsStore.ts
- Usuario
- test_auth.unit.py
- security.ts
- authStore.ts
- test_security_11x.unit.py
- vue
- security.py
- PaymentWizardView.vue
- devDependencies
- frontend/package.json
- BillingGeneratorView.vue
- compilerOptions
- financeStore.ts
- TreasuryClosingView.vue
- test_dependencies.unit.py
- AdminStructureView.vue
- LoginView.vue
- package.json
- os
- read_uploaded_file_safely
- scripts
- verificar_usuario_activo
- SolvencyCertificateView.vue
- sqlalchemy
- RejectPaymentModal.vue
- stryker.conf.json
- Redis
- register_user
- CondominioStressUser
- test_main.unit.py
- CollectionTrafficLight.vue
- ReceiptBreakdownModal.unit.ts
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
1. `Usuario` - 53 edges
2. `vitest` - 39 edges
3. `Unidad` - 33 edges
4. `@vue/test-utils` - 31 edges
5. `vue` - 29 edges
6. `verificar_roles()` - 28 edges
7. `Recibo` - 27 edges
8. `_mock_session()` - 27 edges
9. `_setup()` - 27 edges
10. `Base` - 26 edges

## Surprising Connections (you probably didn't know these)
- `facturar_periodo()` --uses--> `ErrorFinanciero`  [INFERRED]
  backend/src/routers/finanzas.py → backend/src/finanzas.py
- `registrar_egreso()` --uses--> `ErrorFinanciero`  [INFERRED]
  backend/src/routers/finanzas.py → backend/src/finanzas.py
- `reportar_pago()` --uses--> `ErrorFinanciero`  [INFERRED]
  backend/src/routers/pagos.py → backend/src/finanzas.py
- `test_error_financiero_es_value_error()` --uses--> `ErrorFinanciero`  [INFERRED]
  backend/tests/test_finanzas_core.unit.py → backend/src/finanzas.py
- `_cargar_contexto_facturacion()` --uses--> `FondoCondominio`  [INFERRED]
  backend/src/routers/finanzas.py → backend/src/models.py

## Import Cycles
- None detected.

## Communities (64 total, 16 thin omitted)

### Community 0 - "test_finanzas_core.unit.py"
Cohesion: 0.06
Nodes (56): aplicar_credito_disponible(), aplicar_pago(), calcular_deuda_total(), calcular_excedente_pago(), calcular_saldo_pendiente(), _construir_payload_solvencia(), construir_qr_token_solvencia(), convertir_a_usd() (+48 more)

### Community 1 - "pagos.py"
Cohesion: 0.07
Nodes (41): AuditoriaRecibo, FondoCondominio, PagoReportado, Recibo, ReciboItem, Unidad, _crear_recibo_e_items_unidad(), _persistir_lote_facturacion() (+33 more)

### Community 2 - "inspect_blast_radius.py"
Cohesion: 0.07
Nodes (23): assess_risk_level(), compute_blast_radius(), find_graph_files(), find_matching_nodes(), inspect_symbol(), load_graph(), main(), get_migrated_tables() (+15 more)

### Community 3 - "test_hito4_operaciones.unit.py"
Cohesion: 0.10
Nodes (27): Base, BitacoraActa, Comunicado, ContratoOcupacion, FotoVocero, Incidencia, IncidenciaAdhesion, PlantillaTarea (+19 more)

### Community 4 - "vitest"
Cohesion: 0.12
Nodes (16): apiClient, ApiError, apiRequest(), extractErrorDetail(), getCsrfToken(), MUTATING_METHODS, RequestOptions, setCsrfToken() (+8 more)

### Community 5 - "routers/finanzas.py"
Cohesion: 0.12
Nodes (22): CertificadoSolvencia, Egreso, _anexar_cuota_extraordinaria(), _calcular_cargos_modalidad(), _cargar_contexto_facturacion(), _cargos_cuota_fija(), _cargos_variables(), cierre_mensual() (+14 more)

### Community 6 - "main.py"
Cohesion: 0.06
Nodes (8): _es_produccion(), health_check(), http_exception_handler(), lifespan(), _metodos_permitidos(), security_headers_middleware(), validation_exception_handler(), client()

### Community 7 - "test_pagos.unit.py"
Cohesion: 0.23
Nodes (32): FakeUser, _mock_session(), _pago(), _recibo(), _result(), _result_list(), _setup(), _tasa() (+24 more)

### Community 8 - "auth.py"
Cohesion: 0.12
Nodes (7): get_db(), extract_bearer_or_cookie_token(), get_current_user(), get_redis_client(), is_user_session_revoked(), get_me(), decode_access_token()

### Community 9 - "schemas.py"
Cohesion: 0.12
Nodes (27): crear_plantilla_tarea(), BitacoraActaCreate, BitacoraActaResponse, CertificadoSolvenciaResponse, ComunicadoCreate, ComunicadoResponse, FondoCondominioResponse, FotoVoceroCreate (+19 more)

### Community 10 - "AppShellLayout.vue"
Cohesion: 0.07
Nodes (23): authStore, route, router, emit, items, NavItem, props, emit (+15 more)

### Community 11 - "RegisterView.vue"
Cohesion: 0.08
Nodes (28): useIdempotency(), executeWithIdempotency(), rotateKey(), UseIdempotencyReturn, generateIdempotencyKey(), authStore, cedula, correo (+20 more)

### Community 12 - "administracion.py"
Cohesion: 0.10
Nodes (14): Estructura, check_and_set_idempotency_key(), clear_user_session_revocation(), actualizar_alicuota_unidad(), asignar_cargo_junta(), asignar_y_activar_usuario(), generar_estructura(), listar_unidades() (+6 more)

### Community 13 - "test_finanzas_router.unit.py"
Cohesion: 0.20
Nodes (25): ReporteMensual, TasaCambio, _egreso(), FakeUser, _mock_session(), _recibo(), _result(), _result_list() (+17 more)

### Community 14 - "test_schemas.unit.py"
Cohesion: 0.11
Nodes (24): CierreMensualRequest, EgresoCreate, PagoRechazo, PagoReportar, ReciboCreate, TasaCambioCreate, UsuarioCreate, test_cierre_mensual_request_periodo_invalido() (+16 more)

### Community 15 - "operationsStore.ts"
Cohesion: 0.07
Nodes (25): emit, UsuarioPerfil, AlicuotaUpdateDTO, BitacoraActaCreateDTO, BitacoraActaDTO, EstadoIncidencia, EstructuraGenerarRequestDTO, EstructuraGenerarResponseDTO (+17 more)

### Community 16 - "Usuario"
Cohesion: 0.13
Nodes (13): verificar_roles(), Usuario, registrar_tasa(), asignar_tarea_directa(), completar_tarea_diaria(), crear_acta_bitacora(), ejecutar_cronjob_tareas_diarias(), listar_comunicados_recientes() (+5 more)

### Community 17 - "test_auth.unit.py"
Cohesion: 0.10
Nodes (12): test_login_invalid_credentials(), test_login_set_httponly_cookie(), test_me_with_expired_token(), test_me_with_invalid_token(), test_me_with_valid_token_success(), test_me_without_cookie_fails(), test_register_missing_idempotency_key(), test_register_user_already_registered() (+4 more)

### Community 18 - "security.ts"
Cohesion: 0.09
Nodes (22): emit, IncidenciaDTO, ALLOWED_PROOF_MIME_TYPES, DANGEROUS_KEYS, escapeHtml(), FileValidationResult, MAX_UPLOAD_BYTES, sanitizeUntrustedText() (+14 more)

### Community 19 - "authStore.ts"
Cohesion: 0.12
Nodes (16): pushMock, app, buildAppRouter(), evaluateNavigationGuard(), routes, AsyncStoreState, RegistroPayload, PERFIL_ACTIVO (+8 more)

### Community 20 - "test_security_11x.unit.py"
Cohesion: 0.12
Nodes (14): revoke_user_session(), AlicuotaUpdateRequest, FondoCondominioCreate, validate_safe_outgoing_url(), verify_websocket_origin(), test_bearer_token_authentication_and_production_422_sanitization(), test_get_redis_client_singleton(), test_redis_user_session_revocation_and_dependency_gate() (+6 more)

### Community 21 - "vue"
Cohesion: 0.09
Nodes (17): activeIndex, currentItem, props, props, shouldRender, CategorySlice, PALETTE, props (+9 more)

### Community 22 - "security.py"
Cohesion: 0.14
Nodes (9): generate_csrf_token(), get_password_hash(), _is_forbidden_ip(), _pbkdf2_digest(), _resolve_and_validate_ips(), validate_csrf_token(), verify_password(), test_csrf_token_generation_and_validation() (+1 more)

### Community 23 - "PaymentWizardView.vue"
Cohesion: 0.09
Nodes (20): convertVesToUsd(), determinePaymentCoverage(), MetodoPago, coverageType, { currentKey, isSubmitting, executeWithIdempotency }, currentStep, equivalentUsd, financeStore (+12 more)

### Community 24 - "devDependencies"
Cohesion: 0.09
Nodes (22): devDependencies, @axe-core/playwright, eslint, eslint-config-prettier, eslint-plugin-sonarjs, eslint-plugin-vue, jsdom, @lhci/cli (+14 more)

### Community 25 - "frontend/package.json"
Cohesion: 0.10
Nodes (20): description, name, private, type, version, eslint, eslint-config-prettier, eslint-plugin-sonarjs (+12 more)

### Community 26 - "BillingGeneratorView.vue"
Cohesion: 0.10
Nodes (17): ModalidadFacturacion, TipoFondoCondominio, cuotaExtraUsd, { currentKey: billingKey, rotateKey: rotateBillingKey }, { currentKey: fundKey, rotateKey: rotateFundKey }, descCuotaExtra, financeStore, incluirFondoReserva (+9 more)

### Community 27 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+10 more)

### Community 28 - "financeStore.ts"
Cohesion: 0.11
Nodes (17): CertificadoSolvenciaDTO, CierreMensualDTO, EgresoCreateDTO, EstadoPago, EstadoRecibo, FacturarPeriodoRequestDTO, FacturarPeriodoResponseDTO, FinanceStateData (+9 more)

### Community 29 - "TreasuryClosingView.vue"
Cohesion: 0.12
Nodes (14): MonedaPago, cierrePeriodo, closeClosingModal(), confirmModalOpen, confirmMonthlyClosing(), dialogRef, egresoCategoria, egresoDescripcion (+6 more)

### Community 30 - "test_dependencies.unit.py"
Cohesion: 0.28
Nodes (10): create_access_token(), FakeUser, _result(), _session(), test_endpoint_protegido_sin_cookie(), test_token_expirado(), test_token_invalido(), test_token_sin_identificacion() (+2 more)

### Community 31 - "AdminStructureView.vue"
Cohesion: 0.13
Nodes (13): TipoEstructura, alicuotaValor, cuotaFijaUnidad, { currentKey: alicuotaKey, rotateKey: rotateAlicuotaKey }, { currentKey, rotateKey }, handleGenerateStructure(), identificadoresRaw, nombre (+5 more)

### Community 32 - "LoginView.vue"
Cohesion: 0.15
Nodes (13): isSafeRedirectUrl(), authStore, correo, errorBanner, onSubmit(), password, route, router (+5 more)

### Community 33 - "package.json"
Cohesion: 0.14
Nodes (13): description, devDependencies, @commitlint/cli, @commitlint/config-conventional, @evilmartians/lefthook, name, private, scripts (+5 more)

### Community 34 - "os"
Cohesion: 0.22
Nodes (4): do_run_migrations(), run_async_migrations(), run_migrations_offline(), run_migrations_online()

### Community 35 - "read_uploaded_file_safely"
Cohesion: 0.21
Nodes (7): AsyncChunkReader, read_uploaded_file_safely(), validate_file_magic_bytes(), _DummyUpload, test_read_uploaded_file_safely_exceeds_quota_raises_413(), test_read_uploaded_file_safely_within_quota(), test_validate_file_magic_bytes_and_upload_enforcement()

### Community 36 - "scripts"
Cohesion: 0.15
Nodes (13): scripts, audit:deps, build, dev, format, format:check, lint, mutate (+5 more)

### Community 37 - "verificar_usuario_activo"
Cohesion: 0.21
Nodes (4): verificar_usuario_activo(), adherir_a_incidencia(), crear_incidencia(), listar_incidencias_abiertas()

### Community 38 - "SolvencyCertificateView.vue"
Cohesion: 0.18
Nodes (9): { currentKey, rotateKey }, financeStore, handleEmitSolvency(), operationsStore, selectedUnidadId, successBanner, validationError, verifyFolio (+1 more)

### Community 39 - "sqlalchemy"
Cohesion: 0.27
Nodes (3): upgrade(), upgrade(), upgrade()

### Community 40 - "RejectPaymentModal.vue"
Cohesion: 0.28
Nodes (8): dialogRef, emit, handleCancel(), handleConfirm(), isMotivoValid, motivo, props, touched

### Community 41 - "stryker.conf.json"
Cohesion: 0.22
Nodes (8): mutate, reporters, $schema, testRunner, thresholds, break, high, low

### Community 42 - "Redis"
Cohesion: 0.29
Nodes (4): build_idempotency_key(), get_refresh_token_from_grace_period(), rotate_refresh_token_with_grace_period(), test_redis_scoped_idempotency_and_grace_period()

### Community 43 - "register_user"
Cohesion: 0.29
Nodes (3): login(), LoginData, register_user()

### Community 45 - "test_main.unit.py"
Cohesion: 0.32
Nodes (3): test_health_check(), test_options_405_incluye_allow_completo(), test_respuestas_no_cacheables()

### Community 46 - "CollectionTrafficLight.vue"
Cohesion: 0.29
Nodes (7): formatVes(), props, sortedItems, convertUsdToVes(), EstadoCobranzaItemDTO, deudaTotalVes, equivalentVes

### Community 47 - "ReceiptBreakdownModal.unit.ts"
Cohesion: 0.50
Nodes (3): emit, sampleDesglose, ReciboDesgloseDTO

### Community 49 - "dependencies"
Cohesion: 0.50
Nodes (4): dependencies, pinia, vue, vue-router

## Knowledge Gaps
- **19 isolated node(s):** `eslint`, `eslint-config-prettier`, `eslint-plugin-sonarjs`, `eslint-plugin-vue`, `jsdom` (+14 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 557 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `vue` connect `vue` to `LoginView.vue`, `SolvencyCertificateView.vue`, `RejectPaymentModal.vue`, `AppShellLayout.vue`, `RegisterView.vue`, `CollectionTrafficLight.vue`, `operationsStore.ts`, `security.ts`, `authStore.ts`, `PaymentWizardView.vue`, `frontend/package.json`, `BillingGeneratorView.vue`, `financeStore.ts`, `TreasuryClosingView.vue`, `AdminStructureView.vue`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 40 inferred relationships involving `Usuario` (e.g. with `get_current_user()` and `verificar_roles()`) actually correct?**
  _`Usuario` has 40 INFERRED edges - model-reasoned connections that need verification._
- **What connects `eslint`, `eslint-config-prettier`, `eslint-plugin-sonarjs` to the rest of the system?**
  _19 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_finanzas_core.unit.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05759623861298854 - nodes in this community are weakly interconnected._
- **Why does `Usuario` connect `Usuario` to `pagos.py`, `test_hito4_operaciones.unit.py`, `verificar_usuario_activo`, `routers/finanzas.py`, `auth.py`, `schemas.py`, `register_user`, `administracion.py`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `Unidad` (e.g. with `actualizar_alicuota_unidad()` and `asignar_y_activar_usuario()`) actually correct?**
  _`Unidad` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Should `pagos.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07071455016660497 - nodes in this community are weakly interconnected._