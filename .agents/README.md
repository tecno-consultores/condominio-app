# 🤖 Carpeta `.agents/` — Gobernanza de Inteligencia Artificial y Reglas de Calidad 11X (Condominio App)

Bienvenido a la carpeta de configuración y gobernanza para **Agentes de Inteligencia Artificial** y **Desarrolladores Humanos** del repositorio **Condominio App**.

Este directorio implementa el estándar corporativo **Nivel 11X** derivado de `qa-testing-blueprints` para agentes autónomos (Google Antigravity, Anthropic Claude Code / Claude Desktop, Hermes Agent de Nous Research, Cursor, Windsurf, etc.), proporcionando el contexto técnico, las restricciones de seguridad y las compuertas de calidad necesarias para mantener el proyecto bajo certificación continua.

---

## 📂 Estructura del Directorio

```text
.agents/
├── README.md                                         # Este documento explicativo
├── rules/                                            # Reglas y directivas de comportamiento forzadas
│   ├── mandatory_qa_pyramid_and_doc_sync.md          # Pirámide de pruebas multi-capa y sync documental
│   ├── secure_development_and_testing_guidelines.md  # Anti-Mocks ciegos, SSRF, CSRF, extra=forbid y geometría visual
│   ├── frontend_parity_and_closure.md                # Paridad terminal-UI, tablas mutables y protocolo de cierre
│   ├── continuous_agent_evolution.md                 # Evolución y actualización autónoma y continua de .agents/
│   ├── anti_regression_and_side_effects_guardrail.md # Blindaje contra regresiones y control de radio de impacto
│   └── ground_truth_fixtures_and_negative_invariants.md # Fixtures trimodales e invariantes negativos
├── skills/                                           # Habilidades y Playbooks de dominio
│   ├── qa-11x-docker-certifier/                      # Certificación 11X en Docker efímero (95% cobertura)
│   ├── docker-trivy-keydb-hardening/                 # Endurecimiento Docker, Trivy = 0 y KeyDB multi-hilo
│   └── graphify-ast-navigator/                       # Navegación AST, radio de impacto (Blast Radius) y servidor MCP
└── scripts/                                          # Scripts de automatización y compuertas de calidad
    ├── verify_alembic_orm_parity.py                  # Auditoría estricta: modelos ORM vs migraciones Alembic
    ├── verify_json_no_duplicate_keys.py              # Auditoría estricta anti-colisión de claves duplicadas en JSON
    ├── verify_topological_health.py                  # Auditoría estricta de salud topológica y límites de capas AST
    ├── inspect_blast_radius.py                       # Análisis de radio de impacto pre-refactorización (aristas entrantes)
    ├── verify_zero_orphan_vue_components.py          # Auditoría estricta: paridad y cobertura de componentes UI (0 huérfanos)
    └── certify_task_completion.sh                    # Compuerta de certificación pre-commit automatizada (7 etapas)
```

---

## 🌐 Estrategia Lingüística y Optimización de Tokens (Inglés Técnico vs. Español Humano)

> **PREMISA DE DISEÑO ARQUITECTÓNICO:**  
> Las instrucciones destinadas al consumo interno de los modelos de IA (`rules/` y `skills/`) están redactadas en **inglés técnico compacto de alta densidad**, mientras que toda la interacción con desarrolladores humanos, respuestas en el chat y documentación del proyecto (`docs/`, `docs/specs/`, `CHANGELOG.md`, `ROADMAP.md`, `README.md`, `TESTING.md`, `SECURITY.md`) se mantiene estrictamente en **español**.

1. **Economía de Tokens en la Ventana de Contexto ($\approx 35\%$ de Ahorro):**
   - Redactar las reglas y habilidades en inglés técnico de alta densidad reduce el consumo de tokens BPE en el prompt de sistema en cada interacción, dejando mayor espacio disponible para código fuente, esquemas y trazas de pruebas.
2. **Garantía Inviolable de Salida en Español (`OUTPUT LANGUAGE CONSTRAINT`):**
   - Cada archivo en `.agents/rules/` y `.agents/skills/` incluye la directiva forzada de comunicarse y documentar siempre en español.

---

## 🚀 Cómo Usar las Automatizaciones

Para certificar que una tarea cumple con todos los requisitos antes de hacer commit:

```bash
# Ejecutar compuerta integral de certificación 11X
./.agents/scripts/certify_task_completion.sh

# Auditar paridad 100% de componentes Vue sin huérfanos
python3 ./.agents/scripts/verify_zero_orphan_vue_components.py

# Auditar que no existen modelos ORM huérfanos sin migración Alembic
python3 ./.agents/scripts/verify_alembic_orm_parity.py
```
