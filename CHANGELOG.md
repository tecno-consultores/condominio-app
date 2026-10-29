# 📜 Historial de Cambios (CHANGELOG) — Condominio App

Todos los cambios notables en este proyecto son documentados en este archivo siguiendo [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y [Semantic Versioning](https://semver.org/lang/es/).

---

## [Unreleased]

### Added
- **Gobernanza de Agentes IA Nivel 11X (`.agents/` y `AGENTS.md`):**
  - Incorporado ecosistema `.agents/rules/` con 6 directivas de ingeniería (`mandatory_qa_pyramid_and_doc_sync.md`, `secure_development_and_testing_guidelines.md`, `frontend_parity_and_closure.md`, `continuous_agent_evolution.md`, `anti_regression_and_side_effects_guardrail.md`, `ground_truth_fixtures_and_negative_invariants.md`).
  - Incorporado catálogo `.agents/skills/` (`qa-11x-docker-certifier`, `docker-trivy-keydb-hardening`, `graphify-ast-navigator`).
  - Incorporados scripts de certificación y guardarraíles en `.agents/scripts/` (`certify_task_completion.sh`, `verify_alembic_orm_parity.py`, `verify_zero_orphan_vue_components.py`, `verify_json_no_duplicate_keys.py`, `verify_topological_health.py`, `inspect_blast_radius.py`) y escáner global de secretos `scripts/verificar-secretos.sh`.
- **Seguridad Híbrida SPA + API y Endurecimiento Backend (`backend/src/`):**
  - Hashing de contraseñas con `PBKDF2-HMAC-SHA256` (100.000 iteraciones, sal criptográfica de 16 bytes) y comparación en tiempo constante (`hmac.compare_digest`), manteniendo compatibilidad hacia atrás con hashes SHA-256 heredados.
  - Generación y validación de tokens CSRF firmados con `HMAC-SHA256` (`generate_csrf_token`, `validate_csrf_token`).
  - Validador Anti-SSRF (`validate_safe_outgoing_url`) con pre-resolución DNS y bloqueo de rangos RFC 1918, loopback, link-local y hosts internos de contenedores.
  - Lector seguro de archivos por chunks (`read_uploaded_file_safely`) con límite estricto de 2 MB (HTTP 413) para prevenir agotamiento de RAM/disco.
  - Validador Anti-CSWSH de encabezado `Origin` para conexiones WebSocket (`verify_websocket_origin`).
  - Aislamiento de claves de idempotencia por alcance (`idemp:{scope}:{key}`) y periodo de gracia de 5 segundos para rotación concurrente de refresh tokens en `backend/src/redis_client.py`.
  - Bloqueo de Mass Assignment mediante `ConfigDict(extra="forbid")` en todos los esquemas Pydantic de entrada (`backend/src/schemas.py`, `backend/src/routers/auth.py`).
  - Soporte dual de autenticación (`Cookie HttpOnly` + encabezado `Authorization: Bearer`) en `backend/src/dependencies.py`.
  - Ocultamiento automático de `/docs`, `/redoc` y `/openapi.json` y sanitización de errores `422` cuando `APP_ENV=production` en `backend/src/main.py`.
- **Infraestructura Efímera QA y Paridad PostgreSQL 17 + KeyDB Multi-Hilo:**
  - Migración del servicio en memoria a **KeyDB Multi-Hilo** (`eqalpha/keydb:alpine --server-threads 2`) e incorporación de `postgres:17-alpine` en `backend/docker-compose.qa.yml`.
  - Nuevos targets `make qa-parity` (paridad Alembic ↔ ORM contra PostgreSQL 17 real) y `make qa-bdd` (Karate Labs BDD) en `backend/Makefile`.
  - Nuevas pruebas unitarias `backend/tests/test_security_11x.unit.py` y 7 escenarios BDD en `backend/test/api_test.feature`.
- **Especificaciones de Dominio y Manuales QA 11X (`docs/specs/` y `docs/qa/`):**
  - Creadas las 6 especificaciones técnicas en `docs/specs/` (`01_ARQUITECTURA_Y_SEGURIDAD_11X.md`, `02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md`, `03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md`, `04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md`, `05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md` y `README.md`).
  - Creados los 4 manuales maestros en `docs/qa/01..04` y `SECURITY.md`.
  - Reestructurado `ROADMAP.md` con sub-tareas detalladas para el Hito 4 y los Hitos 5, 6, 7 y 8 de la GUI Vue 3 Mobile-First.
