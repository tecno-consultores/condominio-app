# Graph Report - workspace  (2026-10-30)

## Corpus Check
- 198 files · ~100,809 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 6, .ini 2, .feature 2)

## Summary
- 1745 nodes · 4105 edges · 109 communities (89 shown, 20 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 477 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103

## God Nodes (most connected - your core abstractions)
1. `Usuario` - 64 edges
2. `Unidad` - 47 edges
3. `Added` - 46 edges
4. `vitest` - 43 edges
5. `Recibo` - 34 edges
6. `@vue/test-utils` - 34 edges
7. `vue` - 33 edges
8. `verificar_roles()` - 32 edges
9. `ContratoOcupacion` - 30 edges
10. `pinia` - 30 edges

## Surprising Connections (you probably didn't know these)
- `2. Proactive Vulnerability Audit` --references--> `escapeHtml()`  [INFERRED]
  .agents/rules/frontend_parity_and_closure.md → frontend/src/utils/security.ts
- `3. Escenarios BDD Karate Labs (`backend/test/api_test.feature`)` --references--> `FondoCondominio`  [INFERRED]
  TESTING.md → backend/src/models.py
- `1.1. `Usuario` (`usuarios`)` --references--> `Usuario`  [INFERRED]
  docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md → backend/src/models.py
- `2.1. Extensión de `ContratoOcupacion` (`contratos_ocupacion`)` --references--> `ContratoOcupacion`  [INFERRED]
  docs/specs/08_DOMINIO_GOBERNANZA_CARTAS_CONSULTA_Y_ASAMBLEAS.md → backend/src/models.py
- `3.1. Invariante de "Una Unidad = Un Voto Ponderado por su Alícuota"` --references--> `ContratoOcupacion`  [INFERRED]
  docs/specs/08_DOMINIO_GOBERNANZA_CARTAS_CONSULTA_Y_ASAMBLEAS.md → backend/src/models.py

## Import Cycles
- None detected.

## Communities (109 total, 20 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (46): Base, BitacoraActa, Comunicado, FotoVocero, Incidencia, IncidenciaAdhesion, PlantillaTarea, TareaDiaria (+38 more)

### Community 1 - "Community 1"
Cohesion: 0.09
Nodes (38): evaluar_escrutinio_consulta(), ConsultaComunitaria, OpcionConsulta, VotoConsulta, _armar_detalle_consulta(), _calcular_metricas_consulta(), _cargar_opciones_y_votos(), cerrar_consulta() (+30 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (45): dialogRef, emit, handleBackdropClick(), props, CerrarConsultaDTO, ConsultaCreateDTO, ConsultaDetalleDTO, ConsultaResumenDTO (+37 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (18): pushMock, apiClient, ApiError, apiRequest(), extractErrorDetail(), getCsrfToken(), MUTATING_METHODS, RequestOptions (+10 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (40): emit, emit, UsuarioPerfil, AlicuotaUpdateDTO, BitacoraActaCreateDTO, BitacoraActaDTO, EstadoIncidencia, EstructuraGenerarRequestDTO (+32 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (37): emit, sampleDesglose, CertificadoSolvenciaDTO, CierreMensualDTO, EgresoCreateDTO, EstadoPago, EstadoRecibo, FacturarPeriodoRequestDTO (+29 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (37): useIdempotency(), executeWithIdempotency(), rotateKey(), UseIdempotencyReturn, handleGenerateStructure(), authStore, cedula, correo (+29 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (29): emit, links, app, AuthGuardState, buildAppRouter(), evaluateNavigationGuard(), routes, AsyncStoreState (+21 more)

### Community 8 - "Community 8"
Cohesion: 0.23
Nodes (32): FakeUser, _mock_session(), _pago(), _recibo(), _result(), _result_list(), _setup(), _tasa() (+24 more)

### Community 9 - "Community 9"
Cohesion: 0.10
Nodes (26): get_refresh_token_from_grace_period(), CierreMensualRequest, EgresoCreate, FondoCondominioCreate, PagoRechazo, PagoReportar, ReciboCreate, TasaCambioCreate (+18 more)

### Community 10 - "Community 10"
Cohesion: 0.13
Nodes (15): verificar_roles(), verificar_usuario_activo(), Usuario, asignar_tarea_directa(), completar_tarea_diaria(), crear_acta_bitacora(), crear_plantilla_tarea(), ejecutar_cronjob_tareas_diarias() (+7 more)

### Community 11 - "Community 11"
Cohesion: 0.14
Nodes (19): _anexar_cuota_extraordinaria(), _calcular_cargos_modalidad(), _cargar_contexto_facturacion(), _cargos_cuota_fija(), _cargos_variables(), cierre_mensual(), crear_fondo_condominio(), emitir_certificado_solvencia() (+11 more)

### Community 12 - "Community 12"
Cohesion: 0.11
Nodes (31): AlicuotaUpdateRequest, BitacoraActaCreate, BitacoraActaResponse, CertificadoSolvenciaResponse, ComunicadoCreate, ComunicadoResponse, FacturarPeriodoResponse, FondoCondominioResponse (+23 more)

### Community 13 - "Community 13"
Cohesion: 0.07
Nodes (24): activeIndex, currentItem, props, props, shouldRender, formatVes(), props, sortedItems (+16 more)

### Community 14 - "Community 14"
Cohesion: 0.20
Nodes (25): ReporteMensual, _egreso(), FakeUser, _mock_session(), _recibo(), _result(), _result_list(), _setup() (+17 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (7): get_db(), extract_bearer_or_cookie_token(), get_current_user(), is_user_session_revoked(), get_me(), IncidenciaResponse, decode_access_token()

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (13): check_and_set_idempotency_key(), clear_user_session_revocation(), get_redis_client(), actualizar_alicuota_unidad(), asignar_cargo_junta(), asignar_y_activar_usuario(), generar_estructura(), listar_unidades() (+5 more)

### Community 17 - "Community 17"
Cohesion: 0.09
Nodes (12): test_login_invalid_credentials(), test_login_set_httponly_cookie(), test_me_with_expired_token(), test_me_with_invalid_token(), test_me_with_valid_token_success(), test_me_without_cookie_fails(), test_register_missing_idempotency_key(), test_register_user_already_registered() (+4 more)

### Community 18 - "Community 18"
Cohesion: 0.09
Nodes (20): AuditoriaRecibo, ContratoOcupacion, Estructura, TasaCambio, test_modelo_auditoria_recibo_instanciacion(), test_modelo_contrato_ocupacion_instanciacion(), test_modelo_estructura_instanciacion(), test_modelo_tasa_cambio_instanciacion() (+12 more)

### Community 19 - "Community 19"
Cohesion: 0.07
Nodes (17): authStore, route, router, emit, items, NavItem, props, actionMessage (+9 more)

### Community 20 - "Community 20"
Cohesion: 0.10
Nodes (8): upgrade(), upgrade(), upgrade(), upgrade(), client(), test_health_check(), test_options_405_incluye_allow_completo(), test_respuestas_no_cacheables()

### Community 21 - "Community 21"
Cohesion: 0.08
Nodes (24): convertVesToUsd(), determinePaymentCoverage(), MetodoPago, coverageType, { currentKey, isSubmitting, executeWithIdempotency }, currentStep, equivalentUsd, financeStore (+16 more)

### Community 22 - "Community 22"
Cohesion: 0.13
Nodes (20): aplicar_pago(), convertir_a_usd(), determinar_estado_recibo(), validar_suma_alicuotas(), test_aplicar_pago_cero_queda_pendiente(), test_aplicar_pago_con_excedente(), test_aplicar_pago_parcial(), test_aplicar_pago_parcial_acumula_pagos_previos() (+12 more)

### Community 23 - "Community 23"
Cohesion: 0.35
Nodes (17): Unidad, FakeUser, _mock_session(), _result(), _result_list(), _setup(), test_actualizar_alicuota_unidad_exito_y_errores(), test_aprobar_pago_con_sobrepago_acredita_saldo_a_favor_unidad() (+9 more)

### Community 24 - "Community 24"
Cohesion: 0.09
Nodes (22): 10. Gobernanza Digital: Cartas Consulta (Art. 23 LPH) y Asambleas (Fase 4 — Spec 08 — Implementado en Hito 11), 11. Control de Acceso QR, Paquetería en Garita y Reserva de Áreas Sociales (Fase 4 — Spec 09), 1. Módulo de Autenticación y Registro, 2. Dashboard Financiero (Inicio), 3. Flujo de Reporte de Pagos, 4. Panel de Tesorería (Aprobaciones y Cierre), 5. Embudo de Incidencias ("Me Sumo"), 6. Panel de Administración y Configuración (+14 more)

### Community 25 - "Community 25"
Cohesion: 0.17
Nodes (11): calcular_ip_hash_voto(), construir_mensaje_voto_consulta(), _construir_payload_solvencia(), construir_qr_token_solvencia(), generar_firma_solvencia(), generar_firma_voto_consulta(), verificar_firma_solvencia(), verificar_firma_voto_consulta() (+3 more)

### Community 26 - "Community 26"
Cohesion: 0.14
Nodes (15): aplicar_credito_disponible(), calcular_deuda_total(), calcular_excedente_pago(), calcular_saldo_pendiente(), cuantizar(), prorratear_por_alicuotas(), _validar_entradas_prorrateo(), resumen_financiero() (+7 more)

### Community 27 - "Community 27"
Cohesion: 0.13
Nodes (19): CertificadoSolvencia, FondoCondominio, ReciboItem, _crear_recibo_e_items_unidad(), _persistir_lote_facturacion(), 🖥️ Vistas: Facturación Trimodal y Certificado de Solvencia, 1. Principios del Core Matemático (`backend/src/finanzas.py`), 4. Extensión Fase 4: Alícuotas, Facturación LPH, Saldo a Favor y Solvencia Digital (+11 more)

### Community 28 - "Community 28"
Cohesion: 0.09
Nodes (22): devDependencies, @axe-core/playwright, eslint, eslint-config-prettier, eslint-plugin-sonarjs, eslint-plugin-vue, jsdom, @lhci/cli (+14 more)

### Community 29 - "Community 29"
Cohesion: 0.10
Nodes (20): description, name, private, type, version, eslint, eslint-config-prettier, eslint-plugin-sonarjs (+12 more)

### Community 30 - "Community 30"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, allowSyntheticDefaultImports, esModuleInterop, isolatedModules, jsx, lib, module (+12 more)

### Community 31 - "Community 31"
Cohesion: 0.16
Nodes (14): ErrorFinanciero, prorratear_partes_iguales(), umbral_quorum_por_regla(), validar_referencia(), test_convertir_moneda_no_soportada_falla(), test_convertir_ves_con_tasa_cero_falla(), test_convertir_ves_con_tasa_negativa_falla(), test_prorratear_partes_iguales() (+6 more)

### Community 32 - "Community 32"
Cohesion: 0.19
Nodes (16): 1.3. Seguridad Cliente por Diseño (`frontend/src/utils/security.ts`), ALLOWED_PROOF_MIME_TYPES, DANGEROUS_KEYS, escapeHtml(), FileValidationResult, generateIdempotencyKey(), isSafeRedirectUrl(), MAX_UPLOAD_BYTES (+8 more)

### Community 33 - "Community 33"
Cohesion: 0.16
Nodes (7): get_password_hash(), _is_forbidden_ip(), _pbkdf2_digest(), _resolve_and_validate_ips(), verify_password(), test_pbkdf2_password_hash_and_verify(), test_verify_password_malformed_pbkdf2_and_legacy()

### Community 34 - "Community 34"
Cohesion: 0.12
Nodes (14): MonedaPago, cierrePeriodo, closeClosingModal(), confirmModalOpen, confirmMonthlyClosing(), dialogRef, egresoCategoria, egresoDescripcion (+6 more)

### Community 35 - "Community 35"
Cohesion: 0.16
Nodes (5): do_run_migrations(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), main()

### Community 36 - "Community 36"
Cohesion: 0.24
Nodes (7): aprobar_pago(), listar_pagos_en_revision(), _obtener_pago(), _obtener_recibo(), obtener_tasa_del_dia(), rechazar_pago(), reportar_pago()

### Community 37 - "Community 37"
Cohesion: 0.12
Nodes (14): _validar_url_evidencia_segura(), 1. Auditoría de Consistencia Código ↔ Specs y Endurecimiento Aplicado, TipoEstructura, alicuotaValor, cuotaFijaUnidad, { currentKey: alicuotaKey, rotateKey: rotateAlicuotaKey }, { currentKey, rotateKey }, identificadoresRaw (+6 more)

### Community 38 - "Community 38"
Cohesion: 0.17
Nodes (10): AsyncChunkReader, read_uploaded_file_safely(), validate_file_magic_bytes(), _DummyUpload, test_read_uploaded_file_safely_exceeds_quota_raises_413(), test_read_uploaded_file_safely_within_quota(), test_validate_file_magic_bytes_and_upload_enforcement(), 3. Contratos de Seguridad por Diseño (18 Vectores Mitigados y Especificados) (+2 more)

### Community 39 - "Community 39"
Cohesion: 0.25
Nodes (10): create_access_token(), FakeUser, _result(), _session(), test_endpoint_protegido_sin_cookie(), test_token_expirado(), test_token_invalido(), test_token_sin_identificacion() (+2 more)

### Community 40 - "Community 40"
Cohesion: 0.14
Nodes (12): verify_websocket_origin(), 1. Cobertura de Negocio en Pruebas Unitarias, 2. Pruebas BDD, Paridad PostgreSQL 17, Caos y Resiliencia, 3. Ejecución Efímera en Docker, Bitácora de Pruebas y Validación (TESTING.md) - Backend, 1. Reglas Globales y Leyes de Infraestructura (Innegociables), 4.2. Protección Anti-CSWSH (*Cross-Site WebSocket Hijacking*), 1. Resumen Ejecutivo de Métricas QA 11X (+4 more)

### Community 41 - "Community 41"
Cohesion: 0.13
Nodes (14): 1. Reglas de Ejecución Efímera en Docker y Zero-Trust, 2. Pila Tecnológica y Separación de Responsabilidades, 3. Configuración de Referencia: `package.json`, 4. Archivos de Configuración de Calidad, 5. Orquestador Docker Efímero: `docker-compose.qa.yml`, 6. Comandos Operativos: `Makefile`, 7. Ejemplos de Pruebas de Frontend, A. Prueba Unitaria de Store Pinia (`src/stores/auth.unit.ts`) (+6 more)

### Community 42 - "Community 42"
Cohesion: 0.14
Nodes (13): description, devDependencies, @commitlint/cli, @commitlint/config-conventional, @evilmartians/lefthook, name, private, scripts (+5 more)

### Community 43 - "Community 43"
Cohesion: 0.18
Nodes (10): 1. Multi-Layer Testing & Anti-Mock Blindness, 2. Security-by-Design Directives, Copyright (C) 2026 Condominio App Contributors, Mandatory Directive: Security-by-Design & Multi-Layer Testing Guidelines, SPDX-License-Identifier: MIT, build_idempotency_key(), rotate_refresh_token_with_grace_period(), test_redis_scoped_idempotency_and_grace_period() (+2 more)

### Community 44 - "Community 44"
Cohesion: 0.26
Nodes (6): get_migrated_tables(), get_orm_tables(), main(), _resolve_migrations_dir(), _resolve_model_files(), _metodos_permitidos()

### Community 45 - "Community 45"
Cohesion: 0.18
Nodes (3): http_exception_handler(), security_headers_middleware(), validation_exception_handler()

### Community 46 - "Community 46"
Cohesion: 0.17
Nodes (11): Egreso, test_modelo_egreso_instanciacion(), 2. Investigación de Mercado y Marco Legal: ¿Qué debe tener un Sistema Moderno de Administración de Condominios?, 3.1. Módulo A: Motor de Alícuotas, Facturación Mensual Automatizada y Fondo de Reserva, 3.2. Módulo B: Carta Consulta Electrónica y Asambleas Virtuales (Art. 23 LPH), 3.3. Módulo C: Control de Acceso con Pases QR Firmados y Bitácora de Portería / Paquetería, 3.4. Módulo D: Reserva de Áreas Comunes (Amenidades) Vinculada a Solvencia, 3.5. Módulo E: Certificado Digital de Solvencia de Condominio Verificable (+3 more)

### Community 47 - "Community 47"
Cohesion: 0.19
Nodes (8): validate_safe_outgoing_url(), test_validate_safe_outgoing_url_dns_failure(), test_validate_safe_outgoing_url_rejects_bad_scheme_or_internal_host(), test_validate_safe_outgoing_url_rejects_private_and_metadata_ips(), test_validate_safe_outgoing_url_valid_public_ip(), test_verify_websocket_origin(), 3. Seguridad por Diseño (Security-by-Design), 4.4. Defensa Anti-SSRF Estricta (`validate_safe_outgoing_url`)

### Community 48 - "Community 48"
Cohesion: 0.15
Nodes (13): 1.1. Geometría Visual y Ergonomía In-Flow (Anti-JSDOM), 1.2. Manejo de Errores No Destructivo en Pinia (Anti-Destructive Catch), 1.4. Invariante de Cero Componentes Huérfanos (`make -C frontend qa-orphans`), 1.5. Accesibilidad WCAG 2.1 AA y Selectores Deterministas para BDD/E2E, 1. Principios Arquitectónicos para Empezar la GUI de la Forma Correcta, 2. Estructura de Directorios del Frontend (`frontend/`), 3. Contrato de Guardias de Navegación (`vue-router`), 4. Contrato de Selectores Estables para Karate UI y Playwright (+5 more)

### Community 49 - "Community 49"
Cohesion: 0.15
Nodes (13): scripts, audit:deps, build, dev, format, format:check, lint, mutate (+5 more)

### Community 50 - "Community 50"
Cohesion: 0.32
Nodes (7): assess_risk_level(), compute_blast_radius(), find_graph_files(), find_matching_nodes(), inspect_symbol(), load_graph(), main()

### Community 52 - "Community 52"
Cohesion: 0.17
Nodes (11): 1. Reglas de Ejecución Efímera en Docker, 2. Pila Tecnológica de QA (11 Capas Transversales), 3. Requisito de Observabilidad en Código (`src/main.py`), 4. Archivo de Configuración del Proyecto: `pyproject.toml`, 5. Orquestador Docker Efímero: `docker-compose.qa.yml`, 6. Comandos Operativos: `Makefile`, 7. Ejemplos de Implementación de Pruebas, A. Prueba Unitaria con Mocking Estricto (`tests/test_auth.unit.py`) (+3 more)

### Community 53 - "Community 53"
Cohesion: 0.17
Nodes (12): 10. Seguridad Zero-Trust en Dependencias, 11. Fronteras Estrictas de Herramientas (Tool Boundaries), 1. La Cobertura del 95% es un Piso, no una Meta, 2. Paranoia Positiva: Pruebas de Mutación, 3. Efimeridad Absoluta (Cero `docker build` Local), 4. Aislamiento Estricto de Red (Mocking Obligatorio), 5. Prevención de Deuda Técnica (Complejidad Ciclomática y Profiling), 6. Barreras Fronterizas Locales (Lefthook) (+4 more)

### Community 55 - "Community 55"
Cohesion: 0.17
Nodes (12): 1. Propósito Operativo y de Seguridad Física, 2.1. Tabla `PaseVisita` (`pases_visita`), 2.2. Tabla `PaqueteRecibido` (`paquetes_recibidos`), 2.3. Tablas `AreaSocial` (`areas_sociales`) y `ReservaAreaSocial` (`reservas_areas_sociales`), 2. Modelo de Datos Relacional (SQLAlchemy 2.0 + PostgreSQL 17), 3.1. Construcción del Token QR Compacto, 3. Arquitectura Criptográfica de Pases QR y Anti-Replay en KeyDB, 4. Regla de Solvencia Estricta en Reserva de Áreas Sociales (+4 more)

### Community 56 - "Community 56"
Cohesion: 0.17
Nodes (12): 4.11. Aislamiento por Usuario y Ámbito en Llaves de Idempotencia, 4.12. Ocultación de Swagger / ReDoc / OpenAPI en Producción, 4.13. Gobernanza Shift-Left de Lockfiles (`uv.lock` y `pnpm-lock.yaml`), 4.14. Saneamiento de Esquemas en URLs de Evidencia (`UrlEvidenciaSegura`), 4.16. Revocación Instantánea de Sesiones en KeyDB Multi-Hilo, 4.17. No Repudio y Anti-Replay en Pases QR, Cartas Consulta y Certificados de Solvencia, 4.18. Bloqueo Anti-Fraude de Referencias Bancarias Duplicadas, 4.1. Prevención de Asignación Masiva (*Mass Assignment / Over-posting*) (+4 more)

### Community 57 - "Community 57"
Cohesion: 0.20
Nodes (9): Recibo, test_modelo_recibo_instanciacion(), 1. Propósito, Modalidades de Cobro y Fundamento Legal (Art. 7, 11 y 14 LPH), 3.1. El Problema del Redondeo en Prorrateo Contable, 3. Núcleo Matemático Puro (`src/finanzas.py`): Método del Resto Mayor (Hamilton), 4. Firma Criptográfica de Certificados de Solvencia (`HMAC-SHA256`), 5. Contratos de Endpoints REST e Idempotencia (`backend/src/routers/finanzas.py`), 6. Especificación de Esquemas Pydantic (`ConfigDict(extra="forbid")`) (+1 more)

### Community 58 - "Community 58"
Cohesion: 0.22
Nodes (3): adherir_a_incidencia(), crear_incidencia(), listar_incidencias_abiertas()

### Community 59 - "Community 59"
Cohesion: 0.20
Nodes (5): 🔐 Guía de Desarrollo Seguro y Mitigación de Vulnerabilidades (Estándar 11X), 2. Compuerta de Cierre de Tarea (Task Closure Gate), 🧠 Master Prompt de Calidad: Condominio App (Nivel 11X), 🛡️ QA Testing & Calidad Nivel 11X - Condominio App, 📚 Índice de Documentación de QA y Seguridad 11X

### Community 60 - "Community 60"
Cohesion: 0.22
Nodes (8): 1. Active Rules in `.agents/rules/`, 2. Rule Zero: Ephemeral Docker Execution, 3. Skills Catalog in `.agents/skills/`, 4. Automation Scripts in `.agents/scripts/`, 5. Mandatory Task Closure Protocol, 🤖 AI Agent Directives & Technical Governance — Condominio App (Standard 11X), Copyright (C) 2026 Condominio App Contributors, SPDX-License-Identifier: MIT

### Community 61 - "Community 61"
Cohesion: 0.25
Nodes (6): requiere_referencia(), test_calcular_saldo_pendiente(), test_cuantizar_redondeo_half_up(), test_requiere_referencia_efectivo_no_la_exige(), test_requiere_referencia_es_case_insensitive(), test_requiere_referencia_metodos_que_la_exigen()

### Community 62 - "Community 62"
Cohesion: 0.25
Nodes (3): login(), LoginData, register_user()

### Community 63 - "Community 63"
Cohesion: 0.22
Nodes (8): 1. Anti-Mock Blindness (Erradicación de la Ceguera de Mocks), 2. Geometría Visual y Anti-JSDOM (Ceguera de Layout en la GUI), 4. Paridad Terminal ↔ Frontend y Manejo de Errores No Destructivo, 🛡️ Buenas Prácticas de Programación y Arquitectura (Nivel 11X), El Problema, El Problema, La Solución 11X en Condominio App, La Solución 11X para el Frontend Vue 3

### Community 64 - "Community 64"
Cohesion: 0.28
Nodes (8): dialogRef, emit, handleCancel(), handleConfirm(), isMotivoValid, motivo, props, touched

### Community 65 - "Community 65"
Cohesion: 0.22
Nodes (8): mutate, reporters, $schema, testRunner, thresholds, break, high, low

### Community 66 - "Community 66"
Cohesion: 0.22
Nodes (9): 🗺️ Control de Tareas y Roadmap — Condominio App, 📊 Estado General del Proyecto, 🏗️ FASE 1: Backend Base, Seguridad 11X y Dominios Core (`backend/`), 🛡️ FASE 3: Resiliencia Extrema e Ingeniería del Caos Nivel 11X, 🏆 FASE 5: Certificación Integral E2E, Geometría Visual Anti-JSDOM, WCAG 2.1 AA y Lighthouse CI, Hito 2: Autenticación, Ciclo de Vida JWT e Idempotencia `[COMPLETADO]`, Hito 3: Finanzas, Cobranzas y Candado Contable `[COMPLETADO]`, Hito 8: Certificación E2E, Geometría Visual Anti-JSDOM, WCAG 2.1 AA y Lighthouse CI (Cobertura Total Fases 1..4) `[PENDIENTE]` (+1 more)

### Community 67 - "Community 67"
Cohesion: 0.25
Nodes (7): 1. The Mock Blindness Anti-Pattern, 2. Universal Trimodal Ground-Truth Fixture Matrix, 3. Negative Invariant Enforcement, 4. Parallel BDD Scenario Isolation & Multi-Connection SQLite (`Karate Labs`), Copyright (C) 2026 Condominio App Contributors, Mandatory Directive: Ground-Truth Fixtures & Negative Invariants Governance, SPDX-License-Identifier: MIT

### Community 68 - "Community 68"
Cohesion: 0.25
Nodes (7): 1. Supreme Directive: Mandatory 11X Test Creation, 2. Rule Zero: Ephemeral Docker Execution, 3. Continuous Mandatory Documentation Sync, 4. Pre-Conclusion Verification Gate, Copyright (C) 2026 Condominio App Contributors, Mandatory Directive: QA 11X Pyramid & Continuous Documentation Sync, SPDX-License-Identifier: MIT

### Community 69 - "Community 69"
Cohesion: 0.43
Nodes (4): audit_layers(), find_graph_files(), load_graph(), main()

### Community 70 - "Community 70"
Cohesion: 0.43
Nodes (5): _collect_frontend_files(), _is_referenced_in_unit_suites(), _is_ui_component_file(), main(), _resolve_frontend_src()

### Community 71 - "Community 71"
Cohesion: 0.25
Nodes (4): _es_produccion(), revoke_user_session(), test_bearer_token_authentication_and_production_422_sanitization(), test_redis_user_session_revocation_and_dependency_gate()

### Community 72 - "Community 72"
Cohesion: 0.36
Nodes (5): generate_csrf_token(), validate_csrf_token(), test_csrf_token_generation_and_validation(), Hito 3.5: Gobernanza `.agents/`, Endurecimiento de Seguridad 11X y Especificaciones de Dominio `[COMPLETADO]`, 4.8. Tokens Anti-CSRF HMAC-SHA256 y Exclusión de Tokens Bearer (M2M/MCP)

### Community 74 - "Community 74"
Cohesion: 0.25
Nodes (8): 1. Stack Tecnológico y Arquitectura, 2. Seguridad y Autenticación, 3. Modelo de Entidades (Core), 4. Roles y Permisos (RBAC), 5. Finanzas y Cobranzas, 6. Operaciones y Mantenimiento, 7. Despliegue, DevOps y Estándar QA (Nivel 11X), Sistema de Administración de Condominios - Arquitectura y Especificaciones

### Community 75 - "Community 75"
Cohesion: 0.25
Nodes (8): 8.1. Registro y Asignación ("Flujo Fantasma"), 8.2. Reporte y Aprobación de Pagos, 8.3. Embudo de Incidencias (UX y Adhesiones), 8.4. Cierre Financiero de Mes (Candado Contable), 8.5. Facturación Mensual por Alícuota y Certificado de Solvencia (Spec 07), 8.6. Gobernanza Digital y Carta Consulta — Art. 23 LPH (Spec 08), 8.7. Control de Acceso QR, Paquetería y Reservas con Solvencia (Spec 09), 8. Flujos Críticos y Máquinas de Estado

### Community 76 - "Community 76"
Cohesion: 0.25
Nodes (7): 1. Filosofía de CI/CD: Paridad Absoluta, 2. Pipeline de GitHub Actions (`.github/workflows/qa-pipeline.yml`), 3. Barrera de Entrada Local: `lefthook.yml`, 4. Script de Instalación de Hooks: `instalar-hooks.sh`, CI/CD Pipelines y Git Hooks Locales - Condominio App, El Anti-Patrón Tradicional, El Enfoque Blueprint Nivel 11X

### Community 77 - "Community 77"
Cohesion: 0.29
Nodes (6): 1. Pre-Modification Impact & Blast-Radius Analysis, 2. Strict Pre-Build Static Analysis (Zero Missing Imports), 3. Frontend Anti-Degradation (No Destructive Catch), Copyright (C) 2026 Condominio App Contributors, Mandatory Directive: Anti-Regression & Side-Effects Guardrail, SPDX-License-Identifier: MIT

### Community 78 - "Community 78"
Cohesion: 0.29
Nodes (6): 1. Terminal ↔ Frontend Parity Invariants, 2. Proactive Vulnerability Audit, 3. Mandatory Task Closure Protocol, Copyright (C) 2026 Condominio App Contributors, SPDX-License-Identifier: MIT, Terminal ↔ Frontend Parity & Task Closure Protocol

### Community 79 - "Community 79"
Cohesion: 0.38
Nodes (3): audit_json_file(), detect_duplicate_keys(), main()

### Community 80 - "Community 80"
Cohesion: 0.29
Nodes (5): PagoReportado, test_modelo_pago_reportado_instanciacion(), 2.1. Extensión de `Unidad` (`unidades`) y `Egreso` (`egresos`), 2.2. Índice Único Anti-Fraude en `PagoReportado` (`pagos_reportados`), 2. Evolución del Modelo de Datos (SQLAlchemy 2.0 + PostgreSQL 17)

### Community 81 - "Community 81"
Cohesion: 0.29
Nodes (6): Backend (`backend/Makefile`), Compuerta Universal Pre-Commit, Frontend (`frontend/Makefile`), 🏛️ La Pirámide de Calidad Nivel 11X, Resumen de Comandos de Ejecución Efímera (`Rule Zero`), 🧪 Tipos de Pruebas en el Estándar QA 11X y Cómo Utilizarlos

### Community 82 - "Community 82"
Cohesion: 0.33
Nodes (5): 1. The Autonomous Evolution Mandate, 2. Guardrails for Agent Modifications, Continuous Agent & System Prompt Evolution Directive, Copyright (C) 2026 Condominio App Contributors, SPDX-License-Identifier: MIT

### Community 84 - "Community 84"
Cohesion: 0.33
Nodes (5): 1. De la Asistencia Pasiva a la Gobernanza Activa, 2. La Estructura de Gobernanza `.agents/`, 3. Estrategia Lingüística y Optimización de Tokens ($\approx 35\%$ de Ahorro), 4. El Protocolo de Cierre Obligatorio (Closure Gate), 🤖 Arquitectura y Gobernanza de Agentes de Inteligencia Artificial (Nivel 11X)

### Community 85 - "Community 85"
Cohesion: 0.33
Nodes (6): 🧪 Calidad y Seguridad (Estándar Nivel 11X — `Rule Zero`), 🏢 Condominio App, 📚 Documentación y Especificaciones (`docs/specs/`), 📁 Estructura del Repositorio, 📄 Licencia, 🚀 Tecnologías Principales

### Community 86 - "Community 86"
Cohesion: 0.33
Nodes (5): 1. Versiones Soportadas, 2. Reporte Responsable de Vulnerabilidades, 3. Pilares de Seguridad por Diseño (Defensa en Profundidad), 5. Barreras Automatizadas DevSecOps, 🛡️ Política de Seguridad y Arquitectura de Defensa — Condominio App

### Community 87 - "Community 87"
Cohesion: 0.40
Nodes (4): 🤖 Carpeta `.agents/` — Gobernanza de Inteligencia Artificial y Reglas de Calidad 11X (Condominio App), 🚀 Cómo Usar las Automatizaciones, 🌐 Estrategia Lingüística y Optimización de Tokens (Inglés Técnico vs. Español Humano), 📂 Estructura del Directorio

### Community 88 - "Community 88"
Cohesion: 0.40
Nodes (4): 1. Rule Zero: Total Isolation in Docker Containers, 2. Strict QA 11X Approval Thresholds, 3. Repository Hygiene & RAM Conservation, QA 11X Corporate Standard Certifier (Ephemeral Docker Execution)

### Community 89 - "Community 89"
Cohesion: 0.50
Nodes (3): 1. Container Hardening Checklist (Trivy Target = 0), 2. In-Memory Engine: KeyDB Multi-Threaded, Docker Trivy Hardening & KeyDB Performance Skill

### Community 90 - "Community 90"
Cohesion: 0.50
Nodes (3): 1. CLI-First Execution Rule, 2. Blast Radius Assessment Matrix, Graphify AST Navigator & Blast Radius Skill

### Community 91 - "Community 91"
Cohesion: 0.50
Nodes (4): 1. Topología de Servicios en Contenedores, 2. Invariantes de Infraestructura y Persistencia, 4. Matriz Canónica de Alcances de Idempotencia (`idemp:{scope}:{key}`), 🔐 Especificación 01: Arquitectura de Sistema y Seguridad Nivel 11X

### Community 93 - "Community 93"
Cohesion: 0.50
Nodes (4): dependencies, pinia, vue, vue-router

## Knowledge Gaps
- **18 isolated node(s):** `@lhci/cli`, `@stryker-mutator/core`, `@stryker-mutator/vitest-runner`, `@typescript-eslint/eslint-plugin`, `@typescript-eslint/parser` (+13 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 804 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Added` connect `Community 0` to `Community 2`, `Community 6`, `Community 10`, `Community 13`, `Community 15`, `Community 16`, `Community 21`, `Community 22`, `Community 23`, `Community 25`, `Community 26`, `Community 27`, `Community 31`, `Community 32`, `Community 37`, `Community 38`, `Community 40`, `Community 46`, `Community 47`, `Community 71`, `Community 72`?**
  _High betweenness centrality (0.307) - this node is a cross-community bridge._
- **Are the 50 inferred relationships involving `Usuario` (e.g. with `get_current_user()` and `verificar_roles()`) actually correct?**
  _`Usuario` has 50 INFERRED edges - model-reasoned connections that need verification._
- **What connects `@lhci/cli`, `@stryker-mutator/core`, `@stryker-mutator/vitest-runner` to the rest of the system?**
  _18 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06142410015649452 - nodes in this community are weakly interconnected._
- **Why does `useIdempotency()` connect `Community 6` to `Community 0`, `Community 32`, `Community 37`, `Community 38`, `Community 5`, `Community 21`, `Community 60`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `Unidad` (e.g. with `actualizar_alicuota_unidad()` and `asignar_y_activar_usuario()`) actually correct?**
  _`Unidad` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.08653353814644137 - nodes in this community are weakly interconnected._