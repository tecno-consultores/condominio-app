# Graph Report - workspace  (2026-10-30)

## Corpus Check
- 187 files · ~91,632 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 6, .ini 2, .feature 2)

## Summary
- 1618 nodes · 3367 edges · 113 communities (92 shown, 21 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 265 edges (avg confidence: 0.95)
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
- Community 54
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
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107

## God Nodes (most connected - your core abstractions)
1. `Usuario` - 47 edges
2. `Added` - 46 edges
3. `vitest` - 39 edges
4. `@vue/test-utils` - 31 edges
5. `Unidad` - 29 edges
6. `vue` - 29 edges
7. `_mock_session()` - 27 edges
8. `_setup()` - 27 edges
9. `pinia` - 26 edges
10. `verificar_roles()` - 25 edges

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

## Communities (113 total, 21 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (56): AlicuotaUpdateRequest, BitacoraActaCreate, BitacoraActaResponse, CertificadoSolvenciaResponse, CierreMensualRequest, ComunicadoCreate, ComunicadoResponse, EgresoCreate (+48 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (27): assess_risk_level(), compute_blast_radius(), find_graph_files(), find_matching_nodes(), inspect_symbol(), load_graph(), main(), get_migrated_tables() (+19 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (40): emit, links, emit, emit, AuthGuardState, RolUsuario, UsuarioPerfil, AlicuotaUpdateDTO (+32 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (37): 1. Terminal ↔ Frontend Parity Invariants, 2. Proactive Vulnerability Audit, 3. Mandatory Task Closure Protocol, Copyright (C) 2026 Condominio App Contributors, SPDX-License-Identifier: MIT, Terminal ↔ Frontend Parity & Task Closure Protocol, 1. Topología de Servicios en Contenedores, 2. Invariantes de Infraestructura y Persistencia (+29 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (37): emit, sampleDesglose, CertificadoSolvenciaDTO, CierreMensualDTO, EgresoCreateDTO, EstadoPago, EstadoRecibo, FacturarPeriodoRequestDTO (+29 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (25): pushMock, app, buildAppRouter(), evaluateNavigationGuard(), routes, AsyncStoreState, RegistroPayload, useAuthStore (+17 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (17): apiClient, ApiError, apiRequest(), extractErrorDetail(), getCsrfToken(), MUTATING_METHODS, RequestOptions, setCsrfToken() (+9 more)

### Community 7 - "Community 7"
Cohesion: 0.23
Nodes (32): FakeUser, _mock_session(), _pago(), _recibo(), _result(), _result_list(), _setup(), _tasa() (+24 more)

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (20): FotoVocero, Incidencia, IncidenciaAdhesion, PlantillaTarea, adherir_a_incidencia(), crear_incidencia(), listar_incidencias_abiertas(), FakeUser (+12 more)

### Community 9 - "Community 9"
Cohesion: 0.11
Nodes (14): Comunicado, Usuario, asignar_tarea_directa(), completar_tarea_diaria(), crear_acta_bitacora(), crear_plantilla_tarea(), ejecutar_cronjob_tareas_diarias(), listar_comunicados_recientes() (+6 more)

### Community 10 - "Community 10"
Cohesion: 0.10
Nodes (12): test_login_invalid_credentials(), test_login_set_httponly_cookie(), test_me_with_expired_token(), test_me_with_invalid_token(), test_me_with_valid_token_success(), test_me_without_cookie_fails(), test_register_missing_idempotency_key(), test_register_user_already_registered() (+4 more)

### Community 11 - "Community 11"
Cohesion: 0.25
Nodes (23): _egreso(), FakeUser, _mock_session(), _recibo(), _result(), _result_list(), _setup(), _tasa() (+15 more)

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (18): AsyncChunkReader, generate_csrf_token(), read_uploaded_file_safely(), validate_csrf_token(), validate_file_magic_bytes(), validate_safe_outgoing_url(), verify_websocket_origin(), 1. Cobertura de Negocio en Pruebas Unitarias (+10 more)

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (24): convertVesToUsd(), determinePaymentCoverage(), MetodoPago, coverageType, { currentKey, isSubmitting, executeWithIdempotency }, currentStep, equivalentUsd, financeStore (+16 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (13): _DummyUpload, test_bearer_token_authentication_and_production_422_sanitization(), test_get_redis_client_singleton(), test_mass_assignment_extra_forbid_on_all_input_schemas(), test_read_uploaded_file_safely_exceeds_quota_raises_413(), test_read_uploaded_file_safely_within_quota(), test_validate_file_magic_bytes_and_upload_enforcement(), test_validate_safe_outgoing_url_dns_failure() (+5 more)

### Community 16 - "Community 16"
Cohesion: 0.16
Nodes (18): convertir_a_usd(), validar_referencia(), test_aplicar_credito_disponible(), test_convertir_moneda_no_soportada_falla(), test_convertir_usd_es_identidad(), test_convertir_usd_minusculas(), test_convertir_usd_no_exige_tasa_positiva(), test_convertir_ves_a_usd() (+10 more)

### Community 17 - "Community 17"
Cohesion: 0.09
Nodes (21): 1. Auditoría de Consistencia Código ↔ Specs y Endurecimiento Aplicado, 2. Investigación de Mercado y Marco Legal: ¿Qué debe tener un Sistema Moderno de Administración de Condominios?, 3.2. Módulo B: Carta Consulta Electrónica y Asambleas Virtuales (Art. 23 LPH), 3.3. Módulo C: Control de Acceso con Pases QR Firmados y Bitácora de Portería / Paquetería, 3.4. Módulo D: Reserva de Áreas Comunes (Amenidades) Vinculada a Solvencia, 3.5. Módulo E: Certificado Digital de Solvencia de Condominio Verificable, 3. ¿Qué Falta en Condominio App y Cómo Debe Diseñarse (Arquitectura 11X)?, 📊 Especificación 06: Informe de Investigación PropTech (Propiedad Horizontal), Auditoría de Consistencia Código ↔ Specs y Hoja de Ruta Evolutiva (Nivel 11X) (+13 more)

### Community 18 - "Community 18"
Cohesion: 0.09
Nodes (12): authStore, route, router, actionMessage, financeStore, rejectModalOpen, selectedPagoId, area (+4 more)

### Community 19 - "Community 19"
Cohesion: 0.34
Nodes (16): FakeUser, _mock_session(), _result(), _result_list(), _setup(), test_actualizar_alicuota_unidad_exito_y_errores(), test_aprobar_pago_con_sobrepago_acredita_saldo_a_favor_unidad(), test_crear_y_listar_fondos_condominio() (+8 more)

### Community 20 - "Community 20"
Cohesion: 0.09
Nodes (22): devDependencies, @axe-core/playwright, eslint, eslint-config-prettier, eslint-plugin-sonarjs, eslint-plugin-vue, jsdom, @lhci/cli (+14 more)

### Community 21 - "Community 21"
Cohesion: 0.10
Nodes (16): formatVes(), props, sortedItems, CategorySlice, PALETTE, props, slices, convertUsdToVes() (+8 more)

### Community 22 - "Community 22"
Cohesion: 0.10
Nodes (20): description, name, private, type, version, eslint, eslint-config-prettier, eslint-plugin-sonarjs (+12 more)

### Community 23 - "Community 23"
Cohesion: 0.10
Nodes (14): props, shouldRender, emit, items, NavItem, props, contenido, fecha (+6 more)

### Community 24 - "Community 24"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, allowSyntheticDefaultImports, esModuleInterop, isolatedModules, jsx, lib, module (+12 more)

### Community 25 - "Community 25"
Cohesion: 0.13
Nodes (20): ContratoOcupacion, Estructura, Unidad, _crear_recibo_e_items_unidad(), _persistir_lote_facturacion(), 1.1. `Usuario` (`usuarios`), 1.2. `Estructura` (`estructuras`) y `Unidad` (`unidades`), 1.3. `ContratoOcupacion` (`contratos_ocupacion`) (+12 more)

### Community 26 - "Community 26"
Cohesion: 0.15
Nodes (7): decode_access_token(), get_password_hash(), _is_forbidden_ip(), _pbkdf2_digest(), _resolve_and_validate_ips(), verify_password(), test_pbkdf2_password_hash_and_verify()

### Community 27 - "Community 27"
Cohesion: 0.25
Nodes (16): 1. Active Rules in `.agents/rules/`, _validar_url_evidencia_segura(), Added, 3. Contratos de Seguridad por Diseño (18 Vectores Mitigados y Especificados), ALLOWED_PROOF_MIME_TYPES, DANGEROUS_KEYS, escapeHtml(), FileValidationResult (+8 more)

### Community 28 - "Community 28"
Cohesion: 0.15
Nodes (13): Base, AuditoriaRecibo, Egreso, Recibo, ReporteMensual, TasaCambio, 1. Principios del Core Matemático (`backend/src/finanzas.py`), 2. Flujo de Aprobación, Rechazo y Pista de Auditoría (`AuditoriaRecibo`) (+5 more)

### Community 29 - "Community 29"
Cohesion: 0.13
Nodes (7): check_and_set_idempotency_key(), actualizar_alicuota_unidad(), asignar_cargo_junta(), asignar_y_activar_usuario(), generar_estructura(), listar_unidades(), listar_usuarios_pendientes()

### Community 30 - "Community 30"
Cohesion: 0.11
Nodes (18): 1. Módulo de Autenticación y Registro, 2. Dashboard Financiero (Inicio), 3. Flujo de Reporte de Pagos, 4. Panel de Tesorería (Aprobaciones y Cierre), 5. Embudo de Incidencias ("Me Sumo"), 6. Panel de Administración y Configuración, 7. Módulo de Operaciones (Conserjería y Voceros), 8. Bitácora del Secretario (+10 more)

### Community 31 - "Community 31"
Cohesion: 0.11
Nodes (8): test_modelo_auditoria_recibo_instanciacion(), test_modelo_contrato_ocupacion_instanciacion(), test_modelo_egreso_instanciacion(), test_modelo_estructura_instanciacion(), test_modelo_recibo_instanciacion(), test_modelo_reporte_mensual_instanciacion(), test_modelo_tasa_cambio_instanciacion(), test_modelo_unidad_instanciacion()

### Community 32 - "Community 32"
Cohesion: 0.12
Nodes (14): MonedaPago, cierrePeriodo, closeClosingModal(), confirmModalOpen, confirmMonthlyClosing(), dialogRef, egresoCategoria, egresoDescripcion (+6 more)

### Community 33 - "Community 33"
Cohesion: 0.11
Nodes (17): 1. Versiones Soportadas, 2. Reporte Responsable de Vulnerabilidades, 3. Pilares de Seguridad por Diseño (Defensa en Profundidad), 4.11. Aislamiento por Usuario y Ámbito en Llaves de Idempotencia, 4.12. Ocultación de Swagger / ReDoc / OpenAPI en Producción, 4.13. Gobernanza Shift-Left de Lockfiles (`uv.lock` y `pnpm-lock.yaml`), 4.14. Saneamiento de Esquemas en URLs de Evidencia (`UrlEvidenciaSegura`), 4.16. Revocación Instantánea de Sesiones en KeyDB Multi-Hilo (+9 more)

### Community 34 - "Community 34"
Cohesion: 0.12
Nodes (12): 1. Multi-Layer Testing & Anti-Mock Blindness, 2. Security-by-Design Directives, Copyright (C) 2026 Condominio App Contributors, Mandatory Directive: Security-by-Design & Multi-Layer Testing Guidelines, SPDX-License-Identifier: MIT, build_idempotency_key(), get_refresh_token_from_grace_period(), rotate_refresh_token_with_grace_period() (+4 more)

### Community 35 - "Community 35"
Cohesion: 0.22
Nodes (13): 🔄 Sub-Tareas del Hito 10 (Checkpoints de Recuperación), CertificadoSolvencia, FondoCondominio, ReciboItem, 🖥️ Vistas: Facturación Trimodal y Certificado de Solvencia, 4. Extensión Fase 4: Alícuotas, Facturación LPH, Saldo a Favor y Solvencia Digital, 2.3. Nuevas Entidades ORM, 5. Contratos de Endpoints REST e Idempotencia (`backend/src/routers/finanzas.py`) (+5 more)

### Community 36 - "Community 36"
Cohesion: 0.18
Nodes (5): do_run_migrations(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), _es_produccion()

### Community 37 - "Community 37"
Cohesion: 0.17
Nodes (7): extract_bearer_or_cookie_token(), get_current_user(), clear_user_session_revocation(), get_redis_client(), is_user_session_revoked(), revoke_user_session(), test_redis_user_session_revocation_and_dependency_gate()

### Community 38 - "Community 38"
Cohesion: 0.27
Nodes (8): _anexar_cuota_extraordinaria(), _calcular_cargos_modalidad(), _cargar_contexto_facturacion(), _cargos_cuota_fija(), facturar_periodo(), _fin_de_mes(), _verificar_periodo_facturable(), FacturarPeriodoRequest

### Community 39 - "Community 39"
Cohesion: 0.23
Nodes (7): aprobar_pago(), listar_pagos_en_revision(), _obtener_pago(), _obtener_recibo(), obtener_tasa_del_dia(), rechazar_pago(), reportar_pago()

### Community 40 - "Community 40"
Cohesion: 0.27
Nodes (10): create_access_token(), FakeUser, _result(), _session(), test_endpoint_protegido_sin_cookie(), test_token_expirado(), test_token_invalido(), test_token_sin_identificacion() (+2 more)

### Community 41 - "Community 41"
Cohesion: 0.13
Nodes (9): convertir_y_subir_avif(), encolar_notificacion_correo(), generar_tareas_diarias_desde_plantillas(), test_convertir_y_subir_avif_exitoso_y_vacio(), test_encolar_notificacion_correo_con_y_sin_redis(), 🏗️ FASE 1: Backend Base, Seguridad 11X y Dominios Core (`backend/`), Hito 2: Autenticación, Ciclo de Vida JWT e Idempotencia `[COMPLETADO]`, Hito 3: Finanzas, Cobranzas y Candado Contable `[COMPLETADO]` (+1 more)

### Community 42 - "Community 42"
Cohesion: 0.13
Nodes (14): authStore, cedula, correo, errorBanner, { isSubmitting, executeWithIdempotency, rotateKey }, nombre, onFieldChange(), password (+6 more)

### Community 43 - "Community 43"
Cohesion: 0.23
Nodes (6): _construir_payload_solvencia(), construir_qr_token_solvencia(), generar_firma_solvencia(), verificar_firma_solvencia(), verificar_certificado_solvencia(), test_firmar_y_verificar_solvencia_hmac()

### Community 44 - "Community 44"
Cohesion: 0.16
Nodes (9): aplicar_credito_disponible(), ErrorFinanciero, prorratear_partes_iguales(), prorratear_por_alicuotas(), _cargos_variables(), test_prorratear_por_alicuotas_metodo_hamilton_exacto(), 3.1. El Problema del Redondeo en Prorrateo Contable, 3.2. Algoritmo Determinista `prorratear_por_alicuotas` (Penny Allocation) (+1 more)

### Community 45 - "Community 45"
Cohesion: 0.14
Nodes (13): description, devDependencies, @commitlint/cli, @commitlint/config-conventional, @evilmartians/lefthook, name, private, scripts (+5 more)

### Community 46 - "Community 46"
Cohesion: 0.27
Nodes (7): verificar_usuario_activo(), emitir_certificado_solvencia(), listar_fondos_condominio(), obtener_desglose_recibo(), obtener_tasa(), resumen_financiero(), _verificar_acceso_unidad()

### Community 47 - "Community 47"
Cohesion: 0.23
Nodes (8): calcular_deuda_total(), calcular_excedente_pago(), calcular_saldo_pendiente(), cuantizar(), _validar_entradas_prorrateo(), test_calcular_deuda_total_lista_vacia(), test_calcular_deuda_total_suma_saldos(), test_calcular_excedente_pago()

### Community 49 - "Community 49"
Cohesion: 0.15
Nodes (13): scripts, audit:deps, build, dev, format, format:check, lint, mutate (+5 more)

### Community 50 - "Community 50"
Cohesion: 0.24
Nodes (3): upgrade(), upgrade(), upgrade()

### Community 51 - "Community 51"
Cohesion: 0.20
Nodes (11): BitacoraActa, 10. Gobernanza Digital: Cartas Consulta (Art. 23 LPH) y Asambleas (Fase 4 — Spec 08), 🖥️ Vistas: Cartas Consulta y Votación Ponderada por Alícuota, 8.6. Gobernanza Digital y Carta Consulta — Art. 23 LPH (Spec 08), 1. Propósito y Fundamento Legal (Art. 22, 23 y 24 LPH), 3.1. Invariante de "Una Unidad = Un Voto Ponderado por su Alícuota", 3.2. Recibo Criptográfico de Votación (`HMAC-SHA256`), 3.3. Cierre Idempotente y Generación Automática de Acta en `BitacoraActa` (+3 more)

### Community 52 - "Community 52"
Cohesion: 0.20
Nodes (4): get_me(), login(), LoginData, register_user()

### Community 53 - "Community 53"
Cohesion: 0.17
Nodes (11): 1. Reglas de Ejecución Efímera en Docker, 2. Pila Tecnológica de QA (11 Capas Transversales), 3. Requisito de Observabilidad en Código (`src/main.py`), 4. Archivo de Configuración del Proyecto: `pyproject.toml`, 5. Orquestador Docker Efímero: `docker-compose.qa.yml`, 6. Comandos Operativos: `Makefile`, 7. Ejemplos de Implementación de Pruebas, A. Prueba Unitaria con Mocking Estricto (`tests/test_auth.unit.py`) (+3 more)

### Community 54 - "Community 54"
Cohesion: 0.17
Nodes (12): 10. Seguridad Zero-Trust en Dependencias, 11. Fronteras Estrictas de Herramientas (Tool Boundaries), 1. La Cobertura del 95% es un Piso, no una Meta, 2. Paranoia Positiva: Pruebas de Mutación, 3. Efimeridad Absoluta (Cero `docker build` Local), 4. Aislamiento Estricto de Red (Mocking Obligatorio), 5. Prevención de Deuda Técnica (Complejidad Ciclomática y Profiling), 6. Barreras Fronterizas Locales (Lefthook) (+4 more)

### Community 55 - "Community 55"
Cohesion: 0.20
Nodes (10): TareaDiaria, 11. Control de Acceso QR, Paquetería en Garita y Reserva de Áreas Sociales (Fase 4 — Spec 09), 🖥️ Vistas: Pases de Visita QR, Escáner de Garita, Paquetería y Reservas, 8.7. Control de Acceso QR, Paquetería y Reservas con Solvencia (Spec 09), 1. Propósito Operativo y de Seguridad Física, 3.1. Construcción del Token QR Compacto, 3. Arquitectura Criptográfica de Pases QR y Anti-Replay en KeyDB, 4. Regla de Solvencia Estricta en Reserva de Áreas Sociales (+2 more)

### Community 56 - "Community 56"
Cohesion: 0.18
Nodes (9): { currentKey, rotateKey }, financeStore, handleEmitSolvency(), operationsStore, selectedUnidadId, successBanner, validationError, verifyFolio (+1 more)

### Community 57 - "Community 57"
Cohesion: 0.22
Nodes (3): http_exception_handler(), _metodos_permitidos(), validation_exception_handler()

### Community 58 - "Community 58"
Cohesion: 0.20
Nodes (8): PagoReportado, test_modelo_pago_reportado_instanciacion(), 1. Propósito, Modalidades de Cobro y Fundamento Legal (Art. 7, 11 y 14 LPH), 2.1. Extensión de `Unidad` (`unidades`) y `Egreso` (`egresos`), 2.2. Índice Único Anti-Fraude en `PagoReportado` (`pagos_reportados`), 2. Evolución del Modelo de Datos (SQLAlchemy 2.0 + PostgreSQL 17), 6. Especificación de Esquemas Pydantic (`ConfigDict(extra="forbid")`), 💰 Especificación 07: Dominio de Alícuotas, Facturación Mensual (Recibo LPH), Fondos y Solvencia Digital

### Community 59 - "Community 59"
Cohesion: 0.20
Nodes (5): 🔐 Guía de Desarrollo Seguro y Mitigación de Vulnerabilidades (Estándar 11X), 2. Compuerta de Cierre de Tarea (Task Closure Gate), 🧠 Master Prompt de Calidad: Condominio App (Nivel 11X), 🛡️ QA Testing & Calidad Nivel 11X - Condominio App, 📚 Índice de Documentación de QA y Seguridad 11X

### Community 60 - "Community 60"
Cohesion: 0.20
Nodes (9): 1. Reglas de Ejecución Efímera en Docker y Zero-Trust, 2. Pila Tecnológica y Separación de Responsabilidades, 3. Configuración de Referencia: `package.json`, 5. Orquestador Docker Efímero: `docker-compose.qa.yml`, 6. Comandos Operativos: `Makefile`, 7. Ejemplos de Pruebas de Frontend, A. Prueba Unitaria de Store Pinia (`src/stores/auth.unit.ts`), B. Accesibilidad WCAG 2.1 AA y Regresión Visual (`e2e/accessibility.e2e.ts`) (+1 more)

### Community 61 - "Community 61"
Cohesion: 0.33
Nodes (8): useIdempotency(), executeWithIdempotency(), rotateKey(), UseIdempotencyReturn, generateIdempotencyKey(), onSubmit(), submitPayment(), handleCreateIncident()

### Community 62 - "Community 62"
Cohesion: 0.39
Nodes (5): verificar_roles(), cierre_mensual(), crear_fondo_condominio(), registrar_egreso(), registrar_tasa()

### Community 63 - "Community 63"
Cohesion: 0.25
Nodes (6): requiere_referencia(), test_calcular_saldo_pendiente(), test_cuantizar_redondeo_half_up(), test_requiere_referencia_efectivo_no_la_exige(), test_requiere_referencia_es_case_insensitive(), test_requiere_referencia_metodos_que_la_exigen()

### Community 64 - "Community 64"
Cohesion: 0.22
Nodes (7): 2. Pruebas BDD, Paridad PostgreSQL 17, Caos y Resiliencia, 3. Ejecución Efímera en Docker, Bitácora de Pruebas y Validación (TESTING.md) - Backend, 1. Resumen Ejecutivo de Métricas QA 11X, 3. Escenarios BDD Karate Labs (`backend/test/api_test.feature`), 4. Comandos de Certificación Efímera (`Rule Zero`), 🧪 Bitácora General de Calidad y Certificación 11X (TESTING.md)

### Community 65 - "Community 65"
Cohesion: 0.28
Nodes (3): test_health_check(), test_options_405_incluye_allow_completo(), test_respuestas_no_cacheables()

### Community 66 - "Community 66"
Cohesion: 0.22
Nodes (8): 1. Anti-Mock Blindness (Erradicación de la Ceguera de Mocks), 2. Geometría Visual y Anti-JSDOM (Ceguera de Layout en la GUI), 4. Paridad Terminal ↔ Frontend y Manejo de Errores No Destructivo, 🛡️ Buenas Prácticas de Programación y Arquitectura (Nivel 11X), El Problema, El Problema, La Solución 11X en Condominio App, La Solución 11X para el Frontend Vue 3

### Community 67 - "Community 67"
Cohesion: 0.28
Nodes (8): dialogRef, emit, handleCancel(), handleConfirm(), isMotivoValid, motivo, props, touched

### Community 68 - "Community 68"
Cohesion: 0.22
Nodes (8): mutate, reporters, $schema, testRunner, thresholds, break, high, low

### Community 69 - "Community 69"
Cohesion: 0.25
Nodes (7): 2. Rule Zero: Ephemeral Docker Execution, 3. Skills Catalog in `.agents/skills/`, 4. Automation Scripts in `.agents/scripts/`, 5. Mandatory Task Closure Protocol, 🤖 AI Agent Directives & Technical Governance — Condominio App (Standard 11X), Copyright (C) 2026 Condominio App Contributors, SPDX-License-Identifier: MIT

### Community 70 - "Community 70"
Cohesion: 0.25
Nodes (7): 1. Supreme Directive: Mandatory 11X Test Creation, 2. Rule Zero: Ephemeral Docker Execution, 3. Continuous Mandatory Documentation Sync, 4. Pre-Conclusion Verification Gate, Copyright (C) 2026 Condominio App Contributors, Mandatory Directive: QA 11X Pyramid & Continuous Documentation Sync, SPDX-License-Identifier: MIT

### Community 72 - "Community 72"
Cohesion: 0.25
Nodes (8): 1. Stack Tecnológico y Arquitectura, 2. Seguridad y Autenticación, 3. Modelo de Entidades (Core), 4. Roles y Permisos (RBAC), 5. Finanzas y Cobranzas, 6. Operaciones y Mantenimiento, 7. Despliegue, DevOps y Estándar QA (Nivel 11X), Sistema de Administración de Condominios - Arquitectura y Especificaciones

### Community 73 - "Community 73"
Cohesion: 0.25
Nodes (7): 1. Filosofía de CI/CD: Paridad Absoluta, 2. Pipeline de GitHub Actions (`.github/workflows/qa-pipeline.yml`), 3. Barrera de Entrada Local: `lefthook.yml`, 4. Script de Instalación de Hooks: `instalar-hooks.sh`, CI/CD Pipelines y Git Hooks Locales - Condominio App, El Anti-Patrón Tradicional, El Enfoque Blueprint Nivel 11X

### Community 74 - "Community 74"
Cohesion: 0.25
Nodes (8): 1.1. Propósito UX y Modelo de Datos, 1.2. Flujo de Interacción, 1. Embudo de Incidencias con Adhesión ("Me Sumo"), 2. Gestión de Tareas de Conserjería (Plantillas y Checklist Diario), 3. Galería de Voceros (Cuota Estricta de 30 Fotos/Mes), 4. Bitácora del Secretario y Cartelera de Comunicados, 5. Extensiones Operativas de Fase 4 (Trazabilidad Contable, Cartas Consulta, Garita QR y Reservas), 🛠️ Especificación 04: Dominio de Operaciones, Incidencias y Tareas Asíncronas (Hito 4 y Hito 7)

### Community 75 - "Community 75"
Cohesion: 0.25
Nodes (4): activeIndex, currentItem, props, ComunicadoDTO

### Community 76 - "Community 76"
Cohesion: 0.25
Nodes (6): area, descripcion, { isSubmitting, executeWithIdempotency }, operationsStore, showNewForm, statusBanner

### Community 77 - "Community 77"
Cohesion: 0.29
Nodes (6): 1. Pre-Modification Impact & Blast-Radius Analysis, 2. Strict Pre-Build Static Analysis (Zero Missing Imports), 3. Frontend Anti-Degradation (No Destructive Catch), Copyright (C) 2026 Condominio App Contributors, Mandatory Directive: Anti-Regression & Side-Effects Guardrail, SPDX-License-Identifier: MIT

### Community 78 - "Community 78"
Cohesion: 0.29
Nodes (6): 1. The Mock Blindness Anti-Pattern, 2. Universal Trimodal Ground-Truth Fixture Matrix, 3. Negative Invariant Enforcement, Copyright (C) 2026 Condominio App Contributors, Mandatory Directive: Ground-Truth Fixtures & Negative Invariants Governance, SPDX-License-Identifier: MIT

### Community 79 - "Community 79"
Cohesion: 0.29
Nodes (6): aplicar_pago(), test_aplicar_pago_cero_queda_pendiente(), test_aplicar_pago_con_excedente(), test_aplicar_pago_parcial(), test_aplicar_pago_parcial_acumula_pagos_previos(), test_aplicar_pago_total_frontera_exacta()

### Community 80 - "Community 80"
Cohesion: 0.29
Nodes (6): Backend (`backend/Makefile`), Compuerta Universal Pre-Commit, Frontend (`frontend/Makefile`), 🏛️ La Pirámide de Calidad Nivel 11X, Resumen de Comandos de Ejecución Efímera (`Rule Zero`), 🧪 Tipos de Pruebas en el Estándar QA 11X y Cómo Utilizarlos

### Community 81 - "Community 81"
Cohesion: 0.33
Nodes (5): 1. The Autonomous Evolution Mandate, 2. Guardrails for Agent Modifications, Continuous Agent & System Prompt Evolution Directive, Copyright (C) 2026 Condominio App Contributors, SPDX-License-Identifier: MIT

### Community 82 - "Community 82"
Cohesion: 0.33
Nodes (5): determinar_estado_recibo(), test_determinar_estado_pagado_con_excedente(), test_determinar_estado_pagado_frontera_exacta(), test_determinar_estado_parcial(), test_determinar_estado_pendiente()

### Community 83 - "Community 83"
Cohesion: 0.33
Nodes (6): 8.1. Registro y Asignación ("Flujo Fantasma"), 8.2. Reporte y Aprobación de Pagos, 8.3. Embudo de Incidencias (UX y Adhesiones), 8.4. Cierre Financiero de Mes (Candado Contable), 8.5. Facturación Mensual por Alícuota y Certificado de Solvencia (Spec 07), 8. Flujos Críticos y Máquinas de Estado

### Community 84 - "Community 84"
Cohesion: 0.33
Nodes (5): 1. De la Asistencia Pasiva a la Gobernanza Activa, 2. La Estructura de Gobernanza `.agents/`, 3. Estrategia Lingüística y Optimización de Tokens ($\approx 35\%$ de Ahorro), 4. El Protocolo de Cierre Obligatorio (Closure Gate), 🤖 Arquitectura y Gobernanza de Agentes de Inteligencia Artificial (Nivel 11X)

### Community 85 - "Community 85"
Cohesion: 0.33
Nodes (6): 2.1. Tabla `PaseVisita` (`pases_visita`), 2.2. Tabla `PaqueteRecibido` (`paquetes_recibidos`), 2.3. Tablas `AreaSocial` (`areas_sociales`) y `ReservaAreaSocial` (`reservas_areas_sociales`), 2. Modelo de Datos Relacional (SQLAlchemy 2.0 + PostgreSQL 17), A. `AreaSocial` (`areas_sociales`), B. `ReservaAreaSocial` (`reservas_areas_sociales`)

### Community 86 - "Community 86"
Cohesion: 0.40
Nodes (4): 🤖 Carpeta `.agents/` — Gobernanza de Inteligencia Artificial y Reglas de Calidad 11X (Condominio App), 🚀 Cómo Usar las Automatizaciones, 🌐 Estrategia Lingüística y Optimización de Tokens (Inglés Técnico vs. Español Humano), 📂 Estructura del Directorio

### Community 87 - "Community 87"
Cohesion: 0.40
Nodes (4): 1. Rule Zero: Total Isolation in Docker Containers, 2. Strict QA 11X Approval Thresholds, 3. Repository Hygiene & RAM Conservation, QA 11X Corporate Standard Certifier (Ephemeral Docker Execution)

### Community 89 - "Community 89"
Cohesion: 0.40
Nodes (5): 4. Archivos de Configuración de Calidad, A. `vitest.config.ts` (Pruebas Unitarias y Cobertura 95%), B. `playwright.config.ts` (Regresión Visual, E2E y Accesibilidad), C. `stryker.conf.json` (Mutación de Frontend), D. `lighthouserc.js` (Rendimiento Core Web Vitals)

### Community 90 - "Community 90"
Cohesion: 0.40
Nodes (5): 2.1. Extensión de `ContratoOcupacion` (`contratos_ocupacion`), 2.2. Tabla `ConsultaComunitaria` (`consultas_comunitarias`), 2.3. Tabla `OpcionConsulta` (`opciones_consulta`), 2.4. Tabla `VotoConsulta` (`votos_consulta`) — Inmutable y Firmada, 2. Modelo de Datos Relacional (SQLAlchemy 2.0 + PostgreSQL 17)

### Community 91 - "Community 91"
Cohesion: 0.50
Nodes (3): 📋 Active Task Journal — RoSGrid, ✅ Hitos Completados Previamente, 🎯 Tarea Actual en Ejecución — Condominio App

### Community 92 - "Community 92"
Cohesion: 0.50
Nodes (3): 1. Container Hardening Checklist (Trivy Target = 0), 2. In-Memory Engine: KeyDB Multi-Threaded, Docker Trivy Hardening & KeyDB Performance Skill

### Community 93 - "Community 93"
Cohesion: 0.50
Nodes (3): 1. CLI-First Execution Rule, 2. Blast Radius Assessment Matrix, Graphify AST Navigator & Blast Radius Skill

### Community 95 - "Community 95"
Cohesion: 0.50
Nodes (3): Fixed, 📜 Historial de Cambios (CHANGELOG) — Condominio App, [Unreleased]

### Community 97 - "Community 97"
Cohesion: 0.50
Nodes (4): dependencies, pinia, vue, vue-router

## Knowledge Gaps
- **18 isolated node(s):** `@lhci/cli`, `@stryker-mutator/core`, `@stryker-mutator/vitest-runner`, `@typescript-eslint/eslint-plugin`, `@typescript-eslint/parser` (+13 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 752 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Added` connect `Community 27` to `Community 8`, `Community 9`, `Community 13`, `Community 14`, `Community 21`, `Community 25`, `Community 28`, `Community 35`, `Community 37`, `Community 41`, `Community 43`, `Community 44`, `Community 46`, `Community 47`, `Community 51`, `Community 55`, `Community 61`, `Community 95`, `Community 99`?**
  _High betweenness centrality (0.328) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Usuario` (e.g. with `1. Cobertura de Negocio en Pruebas Unitarias` and `1.1. `Usuario` (`usuarios`)`) actually correct?**
  _`Usuario` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `@lhci/cli`, `@stryker-mutator/core`, `@stryker-mutator/vitest-runner` to the rest of the system?**
  _18 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05200341005967604 - nodes in this community are weakly interconnected._
- **Why does `useIdempotency()` connect `Community 61` to `Community 4`, `Community 42`, `Community 76`, `Community 14`, `Community 17`, `Community 56`, `Community 27`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `Added` (e.g. with `get_current_user()` and `verificar_usuario_activo()`) actually correct?**
  _`Added` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.06298701298701298 - nodes in this community are weakly interconnected._