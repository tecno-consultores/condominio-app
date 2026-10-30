# Graph Report - app  (2026-10-30)

## Corpus Check
- 178 files · ~91,360 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 6, .ini 2, .feature 2)

## Summary
- 1613 nodes · 3669 edges · 102 communities (80 shown, 22 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 425 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- test_finanzas_core.unit.py
- test_hito10_alicuotas_solvencia.unit.py
- inspect_blast_radius.py
- test_hito4_operaciones.unit.py
- vitest
- routers/finanzas.py
- main.py
- test_pagos.unit.py
- pagos.py
- schemas.py
- AppShellLayout.vue
- RegisterView.vue
- administracion.py
- test_finanzas_router.unit.py
- test_schemas.unit.py
- operationsStore.ts
- Usuario
- test_auth.unit.py
- Added
- authStore.ts
- test_security_11x.unit.py
- vue
- security.py
- PaymentWizardView.vue
- devDependencies
- frontend/package.json
- financeStore.ts
- compilerOptions
- models.py
- TreasuryClosingView.vue
- test_dependencies.unit.py
- 3. ¿Qué Falta en Condominio App y Cómo Debe Diseñarse (Arquitectura 11X)?
- LoginView.vue
- package.json
- env.py
- validate_file_magic_bytes
- scripts
- src/finanzas.py
- SolvencyCertificateView.vue
- FondoCondominio
- RejectPaymentModal.vue
- stryker.conf.json
- validate_safe_outgoing_url
- get_me
- CondominioStressUser
- test_main.unit.py
- 4. Mitigación Integral de los 13 Vectores de Ataque Híbridos (SPA + API)
- Mapa de Vistas (GUI) y Rutas API
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
- qa/README.md
- validation_exception_handler
- 1. Cobertura de Negocio en Pruebas Unitarias
- 🎨 Especificación 05: Arquitectura GUI Vue 3 Mobile-First y Ergonomía Nivel 11X
- BitacoraActa
- Filosofía de Calidad Nivel 11X (QA Philosophy) - Condominio App
- Guía de Pruebas y Validación para Backend (FastAPI) - Condominio App
- Recibo
- Guía de Pruebas y QA para Frontend (Vue 3) - Condominio App
- Sistema de Administración de Condominios - Arquitectura y Especificaciones
- 🛡️ Buenas Prácticas de Programación y Arquitectura (Nivel 11X)
- 🤖 AI Agent Directives & Technical Governance — Condominio App (Standard 11X)
- Mandatory Directive: QA 11X Pyramid & Continuous Documentation Sync
- CI/CD Pipelines y Git Hooks Locales - Condominio App
- 🛠️ Especificación 04: Dominio de Operaciones, Incidencias y Tareas Asíncronas (Hito 4 y Hito 7)
- TreasuryPaymentsView.vue
- 🗺️ Control de Tareas y Roadmap — Condominio App
- Mandatory Directive: Anti-Regression & Side-Effects Guardrail
- frontend_parity_and_closure.md
- Mandatory Directive: Ground-Truth Fixtures & Negative Invariants Governance
- 8. Flujos Críticos y Máquinas de Estado
- Resumen de Comandos de Ejecución Efímera (`Rule Zero`)
- continuous_agent_evolution.md
- 🏢 Condominio App
- 🤖 Carpeta `.agents/` — Gobernanza de Inteligencia Artificial y Reglas de Calidad 11X (Condominio App)
- QA 11X Corporate Standard Certifier (Ephemeral Docker Execution)
- 4. Archivos de Configuración de Calidad
- 2. Modelo de Datos Relacional (SQLAlchemy 2.0 + PostgreSQL 17)
- Docker Trivy Hardening & KeyDB Performance Skill
- Graphify AST Navigator & Blast Radius Skill
- 🔐 Especificación 01: Arquitectura de Sistema y Seguridad Nivel 11X
- secure_development_and_testing_guidelines.md
- 📜 Historial de Cambios (CHANGELOG) — Condominio App
- 👥 Especificación 02: Dominio de Identidad, Estructura Polimórfica y RBAC
- 🧪 Bitácora de Pruebas y Validación (TESTING.md) — Frontend Vue 3
- 7. Módulo de Operaciones (Conserjería y Voceros)
- 📐 Especificaciones Técnicas y de Dominio (`docs/specs/`) — Condominio App

## God Nodes (most connected - your core abstractions)
1. `Usuario` - 58 edges
2. `Added` - 46 edges
3. `Unidad` - 40 edges
4. `vitest` - 39 edges
5. `Recibo` - 34 edges
6. `@vue/test-utils` - 31 edges
7. `verificar_roles()` - 29 edges
8. `vue` - 29 edges
9. `_mock_session()` - 27 edges
10. `_setup()` - 27 edges

## Surprising Connections (you probably didn't know these)
- `1.1. `Usuario` (`usuarios`)` --references--> `Usuario`  [INFERRED]
  docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md → backend/src/models.py
- `2.1. Extensión de `ContratoOcupacion` (`contratos_ocupacion`)` --references--> `ContratoOcupacion`  [INFERRED]
  docs/specs/08_DOMINIO_GOBERNANZA_CARTAS_CONSULTA_Y_ASAMBLEAS.md → backend/src/models.py
- `3.1. Invariante de "Una Unidad = Un Voto Ponderado por su Alícuota"` --references--> `ContratoOcupacion`  [INFERRED]
  docs/specs/08_DOMINIO_GOBERNANZA_CARTAS_CONSULTA_Y_ASAMBLEAS.md → backend/src/models.py
- `4. Firma Criptográfica de Certificados de Solvencia (`HMAC-SHA256`)` --references--> `Recibo`  [INFERRED]
  docs/specs/07_DOMINIO_ALICUOTAS_FACTURACION_Y_SOLVENCIA.md → backend/src/models.py
- `2.2. Índice Único Anti-Fraude en `PagoReportado` (`pagos_reportados`)` --references--> `PagoReportado`  [INFERRED]
  docs/specs/07_DOMINIO_ALICUOTAS_FACTURACION_Y_SOLVENCIA.md → backend/src/models.py

## Import Cycles
- None detected.

## Communities (102 total, 22 thin omitted)

### Community 0 - "test_finanzas_core.unit.py"
Cohesion: 0.05
Nodes (50): aplicar_pago(), convertir_a_usd(), determinar_estado_recibo(), ErrorFinanciero, requiere_referencia(), validar_referencia(), validar_suma_alicuotas(), aprobar_pago() (+42 more)

### Community 1 - "test_hito10_alicuotas_solvencia.unit.py"
Cohesion: 0.35
Nodes (17): Unidad, FakeUser, _mock_session(), _result(), _result_list(), _setup(), test_actualizar_alicuota_unidad_exito_y_errores(), test_aprobar_pago_con_sobrepago_acredita_saldo_a_favor_unidad() (+9 more)

### Community 2 - "inspect_blast_radius.py"
Cohesion: 0.07
Nodes (26): assess_risk_level(), compute_blast_radius(), find_graph_files(), find_matching_nodes(), inspect_symbol(), load_graph(), main(), get_migrated_tables() (+18 more)

### Community 3 - "test_hito4_operaciones.unit.py"
Cohesion: 0.06
Nodes (41): Incidencia, IncidenciaAdhesion, PlantillaTarea, TareaDiaria, adherir_a_incidencia(), crear_incidencia(), listar_incidencias_abiertas(), convertir_y_subir_avif() (+33 more)

### Community 4 - "vitest"
Cohesion: 0.13
Nodes (15): apiClient, ApiError, apiRequest(), extractErrorDetail(), getCsrfToken(), MUTATING_METHODS, RequestOptions, setCsrfToken() (+7 more)

### Community 5 - "routers/finanzas.py"
Cohesion: 0.12
Nodes (25): calcular_deuda_total(), calcular_saldo_pendiente(), cuantizar(), _anexar_cuota_extraordinaria(), _calcular_cargos_modalidad(), _cargar_contexto_facturacion(), _cargos_cuota_fija(), _cargos_variables() (+17 more)

### Community 6 - "main.py"
Cohesion: 0.09
Nodes (5): main(), _es_produccion(), health_check(), lifespan(), client()

### Community 7 - "test_pagos.unit.py"
Cohesion: 0.23
Nodes (32): FakeUser, _mock_session(), _pago(), _recibo(), _result(), _result_list(), _setup(), _tasa() (+24 more)

### Community 8 - "pagos.py"
Cohesion: 0.15
Nodes (4): get_db(), extract_bearer_or_cookie_token(), get_current_user(), decode_access_token()

### Community 9 - "schemas.py"
Cohesion: 0.15
Nodes (24): BitacoraActaCreate, BitacoraActaResponse, CertificadoSolvenciaResponse, ComunicadoCreate, ComunicadoResponse, FacturarPeriodoResponse, FondoCondominioResponse, FotoVoceroCreate (+16 more)

### Community 10 - "AppShellLayout.vue"
Cohesion: 0.10
Nodes (13): authStore, route, router, emit, items, NavItem, props, contenido (+5 more)

### Community 11 - "RegisterView.vue"
Cohesion: 0.05
Nodes (40): useIdempotency(), executeWithIdempotency(), rotateKey(), UseIdempotencyReturn, alicuotaValor, cuotaFijaUnidad, { currentKey: alicuotaKey, rotateKey: rotateAlicuotaKey }, { currentKey, rotateKey } (+32 more)

### Community 12 - "administracion.py"
Cohesion: 0.11
Nodes (12): actualizar_alicuota_unidad(), asignar_cargo_junta(), asignar_y_activar_usuario(), generar_estructura(), listar_unidades(), listar_usuarios_pendientes(), AlicuotaUpdateRequest, EstructuraGenerarRequest (+4 more)

### Community 13 - "test_finanzas_router.unit.py"
Cohesion: 0.25
Nodes (23): _egreso(), FakeUser, _mock_session(), _recibo(), _result(), _result_list(), _setup(), _tasa() (+15 more)

### Community 14 - "test_schemas.unit.py"
Cohesion: 0.10
Nodes (27): CierreMensualRequest, EgresoCreate, FondoCondominioCreate, PagoRechazo, PagoReportar, ReciboCreate, TasaCambioCreate, UsuarioBase (+19 more)

### Community 15 - "operationsStore.ts"
Cohesion: 0.05
Nodes (40): emit, emit, UsuarioPerfil, AlicuotaUpdateDTO, BitacoraActaCreateDTO, BitacoraActaDTO, EstadoIncidencia, EstructuraGenerarRequestDTO (+32 more)

### Community 16 - "Usuario"
Cohesion: 0.10
Nodes (18): verificar_roles(), verificar_usuario_activo(), Comunicado, FotoVocero, Usuario, asignar_tarea_directa(), completar_tarea_diaria(), crear_acta_bitacora() (+10 more)

### Community 17 - "test_auth.unit.py"
Cohesion: 0.09
Nodes (12): test_login_invalid_credentials(), test_login_set_httponly_cookie(), test_me_with_expired_token(), test_me_with_invalid_token(), test_me_with_valid_token_success(), test_me_without_cookie_fails(), test_register_missing_idempotency_key(), test_register_user_already_registered() (+4 more)

### Community 18 - "Added"
Cohesion: 0.21
Nodes (19): _validar_url_evidencia_segura(), Added, 3. Contratos de Seguridad por Diseño (18 Vectores Mitigados y Especificados), 1.3. Seguridad Cliente por Diseño (`frontend/src/utils/security.ts`), ALLOWED_PROOF_MIME_TYPES, DANGEROUS_KEYS, escapeHtml(), FileValidationResult (+11 more)

### Community 19 - "authStore.ts"
Cohesion: 0.09
Nodes (22): pushMock, emit, links, app, AuthGuardState, buildAppRouter(), evaluateNavigationGuard(), routes (+14 more)

### Community 20 - "test_security_11x.unit.py"
Cohesion: 0.10
Nodes (16): check_and_set_idempotency_key(), clear_user_session_revocation(), get_redis_client(), get_refresh_token_from_grace_period(), is_user_session_revoked(), revoke_user_session(), rotate_refresh_token_with_grace_period(), test_bearer_token_authentication_and_production_422_sanitization() (+8 more)

### Community 21 - "vue"
Cohesion: 0.07
Nodes (24): activeIndex, currentItem, props, props, shouldRender, formatVes(), props, sortedItems (+16 more)

### Community 22 - "security.py"
Cohesion: 0.17
Nodes (7): get_password_hash(), _is_forbidden_ip(), _pbkdf2_digest(), _resolve_and_validate_ips(), verify_password(), test_pbkdf2_password_hash_and_verify(), test_verify_password_malformed_pbkdf2_and_legacy()

### Community 23 - "PaymentWizardView.vue"
Cohesion: 0.09
Nodes (21): convertVesToUsd(), determinePaymentCoverage(), MetodoPago, coverageType, { currentKey, isSubmitting, executeWithIdempotency }, currentStep, equivalentUsd, financeStore (+13 more)

### Community 24 - "devDependencies"
Cohesion: 0.09
Nodes (22): devDependencies, @axe-core/playwright, eslint, eslint-config-prettier, eslint-plugin-sonarjs, eslint-plugin-vue, jsdom, @lhci/cli (+14 more)

### Community 25 - "frontend/package.json"
Cohesion: 0.10
Nodes (20): description, name, private, type, version, eslint, eslint-config-prettier, eslint-plugin-sonarjs (+12 more)

### Community 26 - "financeStore.ts"
Cohesion: 0.05
Nodes (37): emit, sampleDesglose, CertificadoSolvenciaDTO, CierreMensualDTO, EgresoCreateDTO, EstadoPago, EstadoRecibo, FacturarPeriodoRequestDTO (+29 more)

### Community 27 - "compilerOptions"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, allowSyntheticDefaultImports, esModuleInterop, isolatedModules, jsx, lib, module (+12 more)

### Community 28 - "models.py"
Cohesion: 0.08
Nodes (26): Base, AuditoriaRecibo, ContratoOcupacion, Egreso, Estructura, PagoReportado, ReporteMensual, TasaCambio (+18 more)

### Community 29 - "TreasuryClosingView.vue"
Cohesion: 0.12
Nodes (14): MonedaPago, cierrePeriodo, closeClosingModal(), confirmModalOpen, confirmMonthlyClosing(), dialogRef, egresoCategoria, egresoDescripcion (+6 more)

### Community 30 - "test_dependencies.unit.py"
Cohesion: 0.28
Nodes (10): create_access_token(), FakeUser, _result(), _session(), test_endpoint_protegido_sin_cookie(), test_token_expirado(), test_token_invalido(), test_token_sin_identificacion() (+2 more)

### Community 31 - "3. ¿Qué Falta en Condominio App y Cómo Debe Diseñarse (Arquitectura 11X)?"
Cohesion: 0.20
Nodes (9): 1. Auditoría de Consistencia Código ↔ Specs y Endurecimiento Aplicado, 2. Investigación de Mercado y Marco Legal: ¿Qué debe tener un Sistema Moderno de Administración de Condominios?, 3.2. Módulo B: Carta Consulta Electrónica y Asambleas Virtuales (Art. 23 LPH), 3.3. Módulo C: Control de Acceso con Pases QR Firmados y Bitácora de Portería / Paquetería, 3.4. Módulo D: Reserva de Áreas Comunes (Amenidades) Vinculada a Solvencia, 3.5. Módulo E: Certificado Digital de Solvencia de Condominio Verificable, 3. ¿Qué Falta en Condominio App y Cómo Debe Diseñarse (Arquitectura 11X)?, 📊 Especificación 06: Informe de Investigación PropTech (Propiedad Horizontal), Auditoría de Consistencia Código ↔ Specs y Hoja de Ruta Evolutiva (Nivel 11X) (+1 more)

### Community 32 - "LoginView.vue"
Cohesion: 0.20
Nodes (10): authStore, correo, errorBanner, onSubmit(), password, route, router, showPassword (+2 more)

### Community 33 - "package.json"
Cohesion: 0.14
Nodes (13): description, devDependencies, @commitlint/cli, @commitlint/config-conventional, @evilmartians/lefthook, name, private, scripts (+5 more)

### Community 34 - "env.py"
Cohesion: 0.12
Nodes (7): do_run_migrations(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), upgrade(), upgrade(), upgrade()

### Community 35 - "validate_file_magic_bytes"
Cohesion: 0.25
Nodes (5): validate_file_magic_bytes(), _DummyUpload, test_read_uploaded_file_safely_exceeds_quota_raises_413(), test_read_uploaded_file_safely_within_quota(), test_validate_file_magic_bytes_and_upload_enforcement()

### Community 36 - "scripts"
Cohesion: 0.15
Nodes (13): scripts, audit:deps, build, dev, format, format:check, lint, mutate (+5 more)

### Community 37 - "src/finanzas.py"
Cohesion: 0.13
Nodes (13): aplicar_credito_disponible(), calcular_excedente_pago(), _construir_payload_solvencia(), construir_qr_token_solvencia(), generar_firma_solvencia(), prorratear_partes_iguales(), prorratear_por_alicuotas(), _validar_entradas_prorrateo() (+5 more)

### Community 38 - "SolvencyCertificateView.vue"
Cohesion: 0.20
Nodes (8): { currentKey, rotateKey }, financeStore, operationsStore, selectedUnidadId, successBanner, validationError, verifyFolio, verifySig

### Community 39 - "FondoCondominio"
Cohesion: 0.13
Nodes (19): CertificadoSolvencia, FondoCondominio, ReciboItem, 🖥️ Vistas: Facturación Trimodal y Certificado de Solvencia, 4. Extensión Fase 4: Alícuotas, Facturación LPH, Saldo a Favor y Solvencia Digital, 1. Propósito, Modalidades de Cobro y Fundamento Legal (Art. 7, 11 y 14 LPH), 2.1. Extensión de `Unidad` (`unidades`) y `Egreso` (`egresos`), 2.2. Índice Único Anti-Fraude en `PagoReportado` (`pagos_reportados`) (+11 more)

### Community 40 - "RejectPaymentModal.vue"
Cohesion: 0.28
Nodes (8): dialogRef, emit, handleCancel(), handleConfirm(), isMotivoValid, motivo, props, touched

### Community 41 - "stryker.conf.json"
Cohesion: 0.22
Nodes (8): mutate, reporters, $schema, testRunner, thresholds, break, high, low

### Community 42 - "validate_safe_outgoing_url"
Cohesion: 0.11
Nodes (20): 1. Active Rules in `.agents/rules/`, 1. Multi-Layer Testing & Anti-Mock Blindness, 2. Security-by-Design Directives, Mandatory Directive: Security-by-Design & Multi-Layer Testing Guidelines, build_idempotency_key(), AsyncChunkReader, read_uploaded_file_safely(), validate_safe_outgoing_url() (+12 more)

### Community 43 - "get_me"
Cohesion: 0.20
Nodes (4): get_me(), login(), LoginData, register_user()

### Community 45 - "test_main.unit.py"
Cohesion: 0.32
Nodes (3): test_health_check(), test_options_405_incluye_allow_completo(), test_respuestas_no_cacheables()

### Community 46 - "4. Mitigación Integral de los 13 Vectores de Ataque Híbridos (SPA + API)"
Cohesion: 0.10
Nodes (19): 1. Versiones Soportadas, 2. Reporte Responsable de Vulnerabilidades, 3. Pilares de Seguridad por Diseño (Defensa en Profundidad), 4.10. Tolerancia a Carreras Concurrentes (*Grace Period* de 5s) en Refresh Tokens, 4.11. Aislamiento por Usuario y Ámbito en Llaves de Idempotencia, 4.12. Ocultación de Swagger / ReDoc / OpenAPI en Producción, 4.13. Gobernanza Shift-Left de Lockfiles (`uv.lock` y `pnpm-lock.yaml`), 4.14. Saneamiento de Esquemas en URLs de Evidencia (`UrlEvidenciaSegura`) (+11 more)

### Community 47 - "Mapa de Vistas (GUI) y Rutas API"
Cohesion: 0.11
Nodes (18): 11. Control de Acceso QR, Paquetería en Garita y Reserva de Áreas Sociales (Fase 4 — Spec 09), 1. Módulo de Autenticación y Registro, 2. Dashboard Financiero (Inicio), 3. Flujo de Reporte de Pagos, 4. Panel de Tesorería (Aprobaciones y Cierre), 5. Embudo de Incidencias ("Me Sumo"), 6. Panel de Administración y Configuración, 8. Bitácora del Secretario (+10 more)

### Community 49 - "dependencies"
Cohesion: 0.50
Nodes (4): dependencies, pinia, vue, vue-router

### Community 64 - "qa/README.md"
Cohesion: 0.12
Nodes (10): 1. De la Asistencia Pasiva a la Gobernanza Activa, 2. La Estructura de Gobernanza `.agents/`, 3. Estrategia Lingüística y Optimización de Tokens ($\approx 35\%$ de Ahorro), 4. El Protocolo de Cierre Obligatorio (Closure Gate), 🤖 Arquitectura y Gobernanza de Agentes de Inteligencia Artificial (Nivel 11X), 🔐 Guía de Desarrollo Seguro y Mitigación de Vulnerabilidades (Estándar 11X), 2. Compuerta de Cierre de Tarea (Task Closure Gate), 🧠 Master Prompt de Calidad: Condominio App (Nivel 11X) (+2 more)

### Community 65 - "validation_exception_handler"
Cohesion: 0.15
Nodes (4): http_exception_handler(), _metodos_permitidos(), security_headers_middleware(), validation_exception_handler()

### Community 66 - "1. Cobertura de Negocio en Pruebas Unitarias"
Cohesion: 0.19
Nodes (9): generate_csrf_token(), validate_csrf_token(), 1. Cobertura de Negocio en Pruebas Unitarias, 2. Pruebas BDD, Paridad PostgreSQL 17, Caos y Resiliencia, 3. Ejecución Efímera en Docker, Bitácora de Pruebas y Validación (TESTING.md) - Backend, test_csrf_token_generation_and_validation(), Hito 3.5: Gobernanza `.agents/`, Endurecimiento de Seguridad 11X y Especificaciones de Dominio `[COMPLETADO]` (+1 more)

### Community 67 - "🎨 Especificación 05: Arquitectura GUI Vue 3 Mobile-First y Ergonomía Nivel 11X"
Cohesion: 0.15
Nodes (13): 1.1. Geometría Visual y Ergonomía In-Flow (Anti-JSDOM), 1.2. Manejo de Errores No Destructivo en Pinia (Anti-Destructive Catch), 1.4. Invariante de Cero Componentes Huérfanos (`make -C frontend qa-orphans`), 1.5. Accesibilidad WCAG 2.1 AA y Selectores Deterministas para BDD/E2E, 1. Principios Arquitectónicos para Empezar la GUI de la Forma Correcta, 2. Estructura de Directorios del Frontend (`frontend/`), 3. Contrato de Guardias de Navegación (`vue-router`), 4. Contrato de Selectores Estables para Karate UI y Playwright (+5 more)

### Community 68 - "BitacoraActa"
Cohesion: 0.20
Nodes (11): BitacoraActa, 10. Gobernanza Digital: Cartas Consulta (Art. 23 LPH) y Asambleas (Fase 4 — Spec 08), 🖥️ Vistas: Cartas Consulta y Votación Ponderada por Alícuota, 8.6. Gobernanza Digital y Carta Consulta — Art. 23 LPH (Spec 08), 1. Propósito y Fundamento Legal (Art. 22, 23 y 24 LPH), 3.1. Invariante de "Una Unidad = Un Voto Ponderado por su Alícuota", 3.2. Recibo Criptográfico de Votación (`HMAC-SHA256`), 3.3. Cierre Idempotente y Generación Automática de Acta en `BitacoraActa` (+3 more)

### Community 69 - "Filosofía de Calidad Nivel 11X (QA Philosophy) - Condominio App"
Cohesion: 0.17
Nodes (12): 10. Seguridad Zero-Trust en Dependencias, 11. Fronteras Estrictas de Herramientas (Tool Boundaries), 1. La Cobertura del 95% es un Piso, no una Meta, 2. Paranoia Positiva: Pruebas de Mutación, 3. Efimeridad Absoluta (Cero `docker build` Local), 4. Aislamiento Estricto de Red (Mocking Obligatorio), 5. Prevención de Deuda Técnica (Complejidad Ciclomática y Profiling), 6. Barreras Fronterizas Locales (Lefthook) (+4 more)

### Community 70 - "Guía de Pruebas y Validación para Backend (FastAPI) - Condominio App"
Cohesion: 0.18
Nodes (11): 1. Reglas de Ejecución Efímera en Docker, 2. Pila Tecnológica de QA (11 Capas Transversales), 3. Requisito de Observabilidad en Código (`src/main.py`), 4. Archivo de Configuración del Proyecto: `pyproject.toml`, 5. Orquestador Docker Efímero: `docker-compose.qa.yml`, 6. Comandos Operativos: `Makefile`, 7. Ejemplos de Implementación de Pruebas, A. Prueba Unitaria con Mocking Estricto (`tests/test_auth.unit.py`) (+3 more)

### Community 72 - "Recibo"
Cohesion: 0.20
Nodes (8): Recibo, test_modelo_recibo_instanciacion(), 3.1. Módulo A: Motor de Alícuotas, Facturación Mensual Automatizada y Fondo de Reserva, 🏛️ FASE 4: Evolución Funcional PropTech, Ley de Propiedad Horizontal y Experiencia de Usuario (Hitos 10 al 14), Hito 11: Gobernanza Digital, Cartas Consulta (Art. 23 LPH) y Asambleas con Voto Criptográfico `[PENDIENTE — ESPECIFICADO]`, Hito 12: Control de Acceso Peatonal/Vehicular (Pases QR Firmados) y Paquetería en Garita `[PENDIENTE — ESPECIFICADO]`, Hito 13: Reserva de Áreas Sociales Vinculada a Solvencia e Inspección Post-Evento `[PENDIENTE — ESPECIFICADO]`, Hito 14: Ayuda Contextual en Cada Pantalla y Manuales Editables en Markdown (Admin/Instalador y Usuario) `[PENDIENTE — ESPECIFICADO]`

### Community 73 - "Guía de Pruebas y QA para Frontend (Vue 3) - Condominio App"
Cohesion: 0.20
Nodes (9): 1. Reglas de Ejecución Efímera en Docker y Zero-Trust, 2. Pila Tecnológica y Separación de Responsabilidades, 3. Configuración de Referencia: `package.json`, 5. Orquestador Docker Efímero: `docker-compose.qa.yml`, 6. Comandos Operativos: `Makefile`, 7. Ejemplos de Pruebas de Frontend, A. Prueba Unitaria de Store Pinia (`src/stores/auth.unit.ts`), B. Accesibilidad WCAG 2.1 AA y Regresión Visual (`e2e/accessibility.e2e.ts`) (+1 more)

### Community 74 - "Sistema de Administración de Condominios - Arquitectura y Especificaciones"
Cohesion: 0.22
Nodes (8): 1. Stack Tecnológico y Arquitectura, 2. Seguridad y Autenticación, 3. Modelo de Entidades (Core), 4. Roles y Permisos (RBAC), 5. Finanzas y Cobranzas, 6. Operaciones y Mantenimiento, 7. Despliegue, DevOps y Estándar QA (Nivel 11X), Sistema de Administración de Condominios - Arquitectura y Especificaciones

### Community 75 - "🛡️ Buenas Prácticas de Programación y Arquitectura (Nivel 11X)"
Cohesion: 0.22
Nodes (8): 1. Anti-Mock Blindness (Erradicación de la Ceguera de Mocks), 2. Geometría Visual y Anti-JSDOM (Ceguera de Layout en la GUI), 4. Paridad Terminal ↔ Frontend y Manejo de Errores No Destructivo, 🛡️ Buenas Prácticas de Programación y Arquitectura (Nivel 11X), El Problema, El Problema, La Solución 11X en Condominio App, La Solución 11X para el Frontend Vue 3

### Community 76 - "🤖 AI Agent Directives & Technical Governance — Condominio App (Standard 11X)"
Cohesion: 0.25
Nodes (7): 2. Rule Zero: Ephemeral Docker Execution, 3. Skills Catalog in `.agents/skills/`, 4. Automation Scripts in `.agents/scripts/`, 5. Mandatory Task Closure Protocol, 🤖 AI Agent Directives & Technical Governance — Condominio App (Standard 11X), Copyright (C) 2026 Condominio App Contributors, SPDX-License-Identifier: MIT

### Community 77 - "Mandatory Directive: QA 11X Pyramid & Continuous Documentation Sync"
Cohesion: 0.25
Nodes (7): 1. Supreme Directive: Mandatory 11X Test Creation, 2. Rule Zero: Ephemeral Docker Execution, 3. Continuous Mandatory Documentation Sync, 4. Pre-Conclusion Verification Gate, Copyright (C) 2026 Condominio App Contributors, Mandatory Directive: QA 11X Pyramid & Continuous Documentation Sync, SPDX-License-Identifier: MIT

### Community 78 - "CI/CD Pipelines y Git Hooks Locales - Condominio App"
Cohesion: 0.25
Nodes (7): 1. Filosofía de CI/CD: Paridad Absoluta, 2. Pipeline de GitHub Actions (`.github/workflows/qa-pipeline.yml`), 3. Barrera de Entrada Local: `lefthook.yml`, 4. Script de Instalación de Hooks: `instalar-hooks.sh`, CI/CD Pipelines y Git Hooks Locales - Condominio App, El Anti-Patrón Tradicional, El Enfoque Blueprint Nivel 11X

### Community 79 - "🛠️ Especificación 04: Dominio de Operaciones, Incidencias y Tareas Asíncronas (Hito 4 y Hito 7)"
Cohesion: 0.25
Nodes (8): 1.1. Propósito UX y Modelo de Datos, 1.2. Flujo de Interacción, 1. Embudo de Incidencias con Adhesión ("Me Sumo"), 2. Gestión de Tareas de Conserjería (Plantillas y Checklist Diario), 3. Galería de Voceros (Cuota Estricta de 30 Fotos/Mes), 4. Bitácora del Secretario y Cartelera de Comunicados, 5. Extensiones Operativas de Fase 4 (Trazabilidad Contable, Cartas Consulta, Garita QR y Reservas), 🛠️ Especificación 04: Dominio de Operaciones, Incidencias y Tareas Asíncronas (Hito 4 y Hito 7)

### Community 80 - "TreasuryPaymentsView.vue"
Cohesion: 0.25
Nodes (4): actionMessage, financeStore, rejectModalOpen, selectedPagoId

### Community 81 - "🗺️ Control de Tareas y Roadmap — Condominio App"
Cohesion: 0.25
Nodes (8): 🗺️ Control de Tareas y Roadmap — Condominio App, 📊 Estado General del Proyecto, 📱 FASE 2: Frontend Vue 3 Mobile-First (`frontend/`), 🛡️ FASE 3: Resiliencia Extrema e Ingeniería del Caos Nivel 11X, 🏆 FASE 5: Certificación Integral E2E, Geometría Visual Anti-JSDOM, WCAG 2.1 AA y Lighthouse CI, Hito 7: Vistas Administrativas, Embudo de Incidencias y Conserjería `[COMPLETADO]`, Hito 8: Certificación E2E, Geometría Visual Anti-JSDOM, WCAG 2.1 AA y Lighthouse CI (Cobertura Total Fases 1..4) `[PENDIENTE]`, Hito 9: Ingeniería del Caos y Resiliencia Extrema `[COMPLETADO]`

### Community 82 - "Mandatory Directive: Anti-Regression & Side-Effects Guardrail"
Cohesion: 0.29
Nodes (6): 1. Pre-Modification Impact & Blast-Radius Analysis, 2. Strict Pre-Build Static Analysis (Zero Missing Imports), 3. Frontend Anti-Degradation (No Destructive Catch), Copyright (C) 2026 Condominio App Contributors, Mandatory Directive: Anti-Regression & Side-Effects Guardrail, SPDX-License-Identifier: MIT

### Community 83 - "frontend_parity_and_closure.md"
Cohesion: 0.29
Nodes (6): 1. Terminal ↔ Frontend Parity Invariants, 2. Proactive Vulnerability Audit, 3. Mandatory Task Closure Protocol, Copyright (C) 2026 Condominio App Contributors, SPDX-License-Identifier: MIT, Terminal ↔ Frontend Parity & Task Closure Protocol

### Community 84 - "Mandatory Directive: Ground-Truth Fixtures & Negative Invariants Governance"
Cohesion: 0.29
Nodes (6): 1. The Mock Blindness Anti-Pattern, 2. Universal Trimodal Ground-Truth Fixture Matrix, 3. Negative Invariant Enforcement, Copyright (C) 2026 Condominio App Contributors, Mandatory Directive: Ground-Truth Fixtures & Negative Invariants Governance, SPDX-License-Identifier: MIT

### Community 85 - "8. Flujos Críticos y Máquinas de Estado"
Cohesion: 0.29
Nodes (7): 8.1. Registro y Asignación ("Flujo Fantasma"), 8.2. Reporte y Aprobación de Pagos, 8.3. Embudo de Incidencias (UX y Adhesiones), 8.4. Cierre Financiero de Mes (Candado Contable), 8.5. Facturación Mensual por Alícuota y Certificado de Solvencia (Spec 07), 8.7. Control de Acceso QR, Paquetería y Reservas con Solvencia (Spec 09), 8. Flujos Críticos y Máquinas de Estado

### Community 86 - "Resumen de Comandos de Ejecución Efímera (`Rule Zero`)"
Cohesion: 0.29
Nodes (6): Backend (`backend/Makefile`), Compuerta Universal Pre-Commit, Frontend (`frontend/Makefile`), 🏛️ La Pirámide de Calidad Nivel 11X, Resumen de Comandos de Ejecución Efímera (`Rule Zero`), 🧪 Tipos de Pruebas en el Estándar QA 11X y Cómo Utilizarlos

### Community 87 - "continuous_agent_evolution.md"
Cohesion: 0.33
Nodes (5): 1. The Autonomous Evolution Mandate, 2. Guardrails for Agent Modifications, Continuous Agent & System Prompt Evolution Directive, Copyright (C) 2026 Condominio App Contributors, SPDX-License-Identifier: MIT

### Community 88 - "🏢 Condominio App"
Cohesion: 0.33
Nodes (6): 🧪 Calidad y Seguridad (Estándar Nivel 11X — `Rule Zero`), 🏢 Condominio App, 📚 Documentación y Especificaciones (`docs/specs/`), 📁 Estructura del Repositorio, 📄 Licencia, 🚀 Tecnologías Principales

### Community 89 - "🤖 Carpeta `.agents/` — Gobernanza de Inteligencia Artificial y Reglas de Calidad 11X (Condominio App)"
Cohesion: 0.40
Nodes (4): 🤖 Carpeta `.agents/` — Gobernanza de Inteligencia Artificial y Reglas de Calidad 11X (Condominio App), 🚀 Cómo Usar las Automatizaciones, 🌐 Estrategia Lingüística y Optimización de Tokens (Inglés Técnico vs. Español Humano), 📂 Estructura del Directorio

### Community 90 - "QA 11X Corporate Standard Certifier (Ephemeral Docker Execution)"
Cohesion: 0.40
Nodes (4): 1. Rule Zero: Total Isolation in Docker Containers, 2. Strict QA 11X Approval Thresholds, 3. Repository Hygiene & RAM Conservation, QA 11X Corporate Standard Certifier (Ephemeral Docker Execution)

### Community 91 - "4. Archivos de Configuración de Calidad"
Cohesion: 0.40
Nodes (5): 4. Archivos de Configuración de Calidad, A. `vitest.config.ts` (Pruebas Unitarias y Cobertura 95%), B. `playwright.config.ts` (Regresión Visual, E2E y Accesibilidad), C. `stryker.conf.json` (Mutación de Frontend), D. `lighthouserc.js` (Rendimiento Core Web Vitals)

### Community 92 - "2. Modelo de Datos Relacional (SQLAlchemy 2.0 + PostgreSQL 17)"
Cohesion: 0.40
Nodes (5): 2.1. Extensión de `ContratoOcupacion` (`contratos_ocupacion`), 2.2. Tabla `ConsultaComunitaria` (`consultas_comunitarias`), 2.3. Tabla `OpcionConsulta` (`opciones_consulta`), 2.4. Tabla `VotoConsulta` (`votos_consulta`) — Inmutable y Firmada, 2. Modelo de Datos Relacional (SQLAlchemy 2.0 + PostgreSQL 17)

### Community 93 - "Docker Trivy Hardening & KeyDB Performance Skill"
Cohesion: 0.50
Nodes (3): 1. Container Hardening Checklist (Trivy Target = 0), 2. In-Memory Engine: KeyDB Multi-Threaded, Docker Trivy Hardening & KeyDB Performance Skill

### Community 94 - "Graphify AST Navigator & Blast Radius Skill"
Cohesion: 0.50
Nodes (3): 1. CLI-First Execution Rule, 2. Blast Radius Assessment Matrix, Graphify AST Navigator & Blast Radius Skill

### Community 95 - "🔐 Especificación 01: Arquitectura de Sistema y Seguridad Nivel 11X"
Cohesion: 0.50
Nodes (4): 1. Topología de Servicios en Contenedores, 2. Invariantes de Infraestructura y Persistencia, 4. Matriz Canónica de Alcances de Idempotencia (`idemp:{scope}:{key}`), 🔐 Especificación 01: Arquitectura de Sistema y Seguridad Nivel 11X

### Community 98 - "👥 Especificación 02: Dominio de Identidad, Estructura Polimórfica y RBAC"
Cohesion: 0.67
Nodes (3): 2. Máquina de Estados: "Flujo de Usuario Fantasma", 👥 Especificación 02: Dominio de Identidad, Estructura Polimórfica y RBAC, Reglas de Negocio Estrictas

## Knowledge Gaps
- **19 isolated node(s):** `condominio-app-backend`, `@lhci/cli`, `@stryker-mutator/core`, `@stryker-mutator/vitest-runner`, `@typescript-eslint/eslint-plugin` (+14 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 748 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Added` connect `Added` to `test_finanzas_core.unit.py`, `test_hito10_alicuotas_solvencia.unit.py`, `1. Cobertura de Negocio en Pruebas Unitarias`, `test_hito4_operaciones.unit.py`, `BitacoraActa`, `src/finanzas.py`, `validate_file_magic_bytes`, `FondoCondominio`, `pagos.py`, `📜 Historial de Cambios (CHANGELOG) — Condominio App`, `validate_safe_outgoing_url`, `RegisterView.vue`, `Usuario`, `test_security_11x.unit.py`, `vue`, `PaymentWizardView.vue`, `models.py`?**
  _High betweenness centrality (0.261) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `Usuario` (e.g. with `get_current_user()` and `verificar_roles()`) actually correct?**
  _`Usuario` has 45 INFERRED edges - model-reasoned connections that need verification._
- **What connects `condominio-app-backend`, `@lhci/cli`, `@stryker-mutator/core` to the rest of the system?**
  _19 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_finanzas_core.unit.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05472837022132797 - nodes in this community are weakly interconnected._
- **Why does `useIdempotency()` connect `RegisterView.vue` to `SolvencyCertificateView.vue`, `validate_safe_outgoing_url`, `Added`, `PaymentWizardView.vue`, `financeStore.ts`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `Added` (e.g. with `get_current_user()` and `verificar_usuario_activo()`) actually correct?**
  _`Added` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Should `inspect_blast_radius.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06821480406386067 - nodes in this community are weakly interconnected._