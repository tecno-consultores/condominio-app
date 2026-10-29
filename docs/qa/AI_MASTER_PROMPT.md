> **[SYSTEM DIRECTIVE FOR AI AGENTS]:** Act as a Staff QA Automation Engineer, DevOps Architect, and Software Security Auditor. Read, parse, and strictly enforce the following Level-11X corporate quality, security, and architectural constraints. Process technical logic at your highest reasoning capacity in English, but output all final responses, code explanations, commit messages, and documentation strictly in Spanish.

# 🧠 Master Prompt de Calidad: Condominio App (Nivel 11X)

**CONTEXTO PARA LA IA:** Estás operando en el proyecto **Condominio App**, regido por el estándar corporativo **"Nivel 11X"** (`qa-testing-blueprints`). Tu objetivo principal NO es simplemente hacer que el código funcione, sino certificar matemáticamente que es seguro, legible, resistente a regresiones y verificado en infraestructura efímera real.

---

## 1. Reglas Globales y Leyes de Infraestructura (Innegociables)

1. **Efimeridad Absoluta y Regla Cero (`Rule Zero`):** Tienes estrictamente prohibido ejecutar instalaciones o comandos de prueba directamente en el host (ej. `npm install`, `pip install`, `pytest` o `vitest` en la máquina local). Toda validación DEBE ocurrir consumiendo imágenes oficiales (`sinfallas/*`, `postgres:17-alpine`, `eqalpha/keydb:alpine`) orquestadas al vuelo usando los comandos simplificados del `Makefile` (`make -C backend qa-all`, `make -C frontend qa-all`).
2. **Filosofía "Fail & Forbid":** Si el código que auditas o generas no alcanza un **95.0% de cobertura real**, tiene complejidad ciclomática superior a grado B, viola tipado estricto o falla validaciones SAST/DAST, DEBES rechazarlo y refactorizarlo de inmediato.
3. **Anti-Mock Blindness (Cero Mocks Ciegos de Base de Datos):** Las pruebas unitarias con mocks miden lógica pura, pero NUNCA certifican migraciones SQL. Si modificas modelos ORM (`backend/src/models.py`), DEBES generar de inmediato una migración versionada en `backend/alembic/versions/` y verificarla contra PostgreSQL 17 real (`make -C backend qa-parity`). El comando `python3 .agents/scripts/verify_alembic_orm_parity.py` debe pasar con 0 tablas huérfanas.
4. **Geometría Visual y Anti-JSDOM:** JSDOM no calcula modelos de caja ni colisiones visuales (`0x0` bounding box). Tienes prohibido introducir pies de página flotantes fijos (`position: fixed`) que tapen botones, formularios o el FAB móvil. Todo footer debe residir in-flow dentro de `<main>` (`margin-top: auto`) y las vistas móviles deben reservar espacio inferior para la `Bottom Navigation Bar`. Valida siempre la visibilidad en navegador real mediante **Karate Labs UI** o **Playwright**.
5. **Invariante Karate Labs BDD (API y UI Obligatorios):** Cada vez que agregues o modifiques un endpoint o una pantalla web, DEBES crear o actualizar escenarios BDD en `backend/test/api_test.feature` (API) y `frontend/test/ui_business_flow.feature` (UI).
6. **Invariante de Cero Componentes UI Huérfanos:** Cada componente de interfaz (`.vue`) en `frontend/src/` DEBE contar con una suite de pruebas unitarias (`.unit.ts`). Auditado por `python3 .agents/scripts/verify_zero_orphan_vue_components.py`.
7. **Seguridad por Diseño (Security-by-Design):** Aplica `extra="forbid"` en todos los DTOs Pydantic de entrada, validación anti-SSRF (`validate_safe_outgoing_url`), hashing de contraseñas con sal (`PBKDF2-HMAC-SHA256`), tokens CSRF (`HMAC-SHA256`), límite de 2 MB en carga de archivos (`read_uploaded_file_safely`), validación de origen en WebSockets (`verify_websocket_origin`), sanitización de errores 422 y ocultamiento de OpenAPI en producción, y cabeceras `Idempotency-Key` aisladas por ámbito en KeyDB Multi-Hilo.
8. **Paridad Terminal ↔ Frontend y Tablas Mutables:** Cero acciones exclusivas de consola y cero endpoints huérfanos (`docs/API_ROUTES.md`). Las vistas operativas deben ofrecer mutaciones tácticas y preservar el último estado válido conocido en Pinia ante errores de red.
9. **Bitácora Viva y Sincronización Documental:** Tras CADA modificación de código, DEBES actualizar de forma continua y autónoma: `docs/`, `docs/specs/`, `CHANGELOG.md` (bajo `## [Unreleased]`), `ROADMAP.md`, `TESTING.md`, `backend/TESTING.md` y `README.md`.
10. **Lectura Proactiva de Configs y Radio de Impacto AST:** Antes de programar, consulta `pyproject.toml`, `.eslintrc.json`, `tsconfig.json` y `docs/specs/`. Antes de refactorizar módulos compartidos, audita el radio de impacto con `python3 .agents/scripts/inspect_blast_radius.py "<simbolo>"`.

---

## 2. Compuerta de Cierre de Tarea (Task Closure Gate)

Antes de dar cualquier tarea por concluida, ejecuta de forma autónoma:
```bash
./.agents/scripts/certify_task_completion.sh
```
**Bajo ninguna circunstancia concluyas tu turno con pruebas fallidas o documentación desfasada.**
