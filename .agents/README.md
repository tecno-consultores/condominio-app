# 🤖 Carpeta `.agents/` — Gobernanza Thin-Repo y Calidad 11X (Condominio App)

Bienvenido al directorio de gobernanza para **Agentes de Inteligencia Artificial** y **Desarrolladores Humanos** de **Condominio App**.

Este repositorio sigue la arquitectura **Thin-Repo** del estándar **Nivel 11X** (`@sinfallas/mcp-qa-11x` v2.20+): las reglas canónicas y las 5 habilidades corporativas (`qa-11x-architect`, `qa-11x-docker-certifier`, `docker-trivy-keydb-hardening`, `graphify-ast-navigator`, `refactoring-ui`) se consumen directamente desde la instalación global, evitando duplicar archivos en cada proyecto y aislando únicamente las reglas específicas del dominio condominial.

---

## 📂 Estructura del Directorio

```text
.agents/
├── .qa-11x-version                         # Metadatos de versión sincronizada de blueprints
├── ACTIVE_TASK.md                          # Diario local de sesión activa (ignorado en .gitignore)
├── ACTIVE_TASK.md.example                  # Plantilla determinista <= 40 líneas
├── README.md                               # Este documento explicativo
├── rules/
│   └── domain_condominio_app_rules.md      # Reglas de dominio específicas de Condominio App
└── scripts/                                # Compuertas y validadores estáticos locales
    ├── certify_task_completion.sh          # Compuerta integral de certificación (10 etapas)
    ├── inspect_blast_radius.py             # Radio de impacto AST pre-refactorización
    ├── verify_alembic_orm_parity.py        # Paridad ORM ↔ migraciones Alembic y revision <= 32
    ├── verify_docs_invariants.py           # Presupuesto cognitivo e invariantes documentales
    ├── verify_json_no_duplicate_keys.py    # Anti-colisión de claves duplicadas en JSON
    ├── verify_no_orphan_api_endpoints.py   # Paridad bidireccional rutas backend ↔ frontend
    ├── verify_roadmap_consistency.py       # Coherencia bidireccional ROADMAP.md ↔ ACTIVE_TASK.md
    ├── verify_topological_health.py        # Salud topológica y límites de capas AST
    └── verify_zero_orphan_vue_components.py # Cobertura 100% de componentes .vue (0 huérfanos)
```

---

## 🌐 Estrategia Lingüística y Economía Cognitiva

- **Consumo Interno de IA:** `.agents/rules/domain_condominio_app_rules.md` y `AGENTS.md` se redactan en **inglés técnico compacto** para ahorrar ventana de contexto ($\approx 35\%$).
- **Interacción y Documentación Humana:** Toda respuesta al usuario, mensajes de commit y documentación (`docs/`, `docs/specs/`, `CHANGELOG.md`, `ROADMAP.md`, `README.md`, `TESTING.md`, `SECURITY.md`, `.agents/ACTIVE_TASK.md`) se mantiene estrictamente en **español**.

---

## 🚀 Cómo Usar las Automatizaciones

Las validaciones operativas (lint, pruebas, migraciones, DAST, E2E) se ejecutan exclusivamente dentro de contenedores Docker efímeros (`Rule Zero`) mediante el `Makefile` raíz o los `Makefile` de `backend/` y `frontend/`. Para sincronizar scripts o verificar la compuerta de cierre:

```bash
# Sincronizar gobernanza Thin-Repo y scripts desde @sinfallas/mcp-qa-11x
npx -y @sinfallas/mcp-qa-11x@latest install-skill --init-agents --include-scripts --reconcile

# Ejecutar compuerta integral de certificación 11X (10 etapas)
./.agents/scripts/certify_task_completion.sh
```
