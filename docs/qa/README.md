# 🛡️ Guía Maestra de Calidad y Gobernanza Nivel 11X (Thin-Repo)

**Proyecto:** Condominio App  
**Estándar Corporativo:** QA Nivel 11X (`@sinfallas/mcp-qa-11x` `v3.1.0`)  
**Ejecución:** `Rule Zero` — 100% contenedores Docker efímeros (`sinfallas/*`)

---

## 1. Arquitectura Thin-Repo y Gobernanza Global

Siguiendo la arquitectura **Thin-Repo**, este repositorio **no duplica** manuales ni directivas genéricas dentro de `docs/qa/`. Las reglas canónicas de ingeniería, la matriz de clasificación (`DOCS_ONLY` / `MICRO_CHANGE` / `FULL_11X`) y las 11 skills corporativas se consumen directamente desde el paquete global **`@sinfallas/mcp-qa-11x` (`v3.1.0`)**:

- **Gobernanza de Dominio Local:** Limitada exclusivamente a [`.agents/rules/domain_condominio_app_rules.md`](../../.agents/rules/domain_condominio_app_rules.md) (*Anti-Mock Blindness*, fixtures trimodales, aislamiento paralelo Karate Labs por UUID, `Rule Zero` y reglas Vue 3).
- **Arquitectura FINOS CALM `1.2`:** Modelada en [`architecture/qa-11x.calm.json`](../../architecture/qa-11x.calm.json) con **7 controles obligatorios 11X**, validados determinísticamente mediante `./.agents/scripts/validate_calm_architecture.sh` (`make qa-calm`).
- **Grafo Semántico AST Graphify (`--code-only`):** Generado de forma local sin daemons en segundo plano con `./scripts/actualizar-grafos-graphify.sh` (`sinfallas/remote-graphify`). Permite consultar `graphify-out/GRAPH_REPORT.md`, auditar el radio de impacto previo al cambio (`.agents/scripts/inspect_blast_radius.py`) y validar `0` acoplamientos inversos entre capas (`.agents/scripts/verify_topological_health.py`).

---

## 2. Pirámide de Calidad de 13 Capas (`Rule Zero`)

Ninguna herramienta de prueba, linter o migración se ejecuta sobre el sistema operativo anfitrión. Todas las capas operan en contenedores Docker efímeros orquestados desde el [`Makefile`](../../Makefile) raíz y los sub-proyectos:

| Capa | Dominio / Propósito | Comando Canónico (`Rule Zero`) | Umbral / Gate 11X |
| :--- | :--- | :--- | :--- |
| **1. Secretos** | Detección preventiva de credenciales y llaves privadas | `make qa-secrets` (`./scripts/verificar-secretos.sh`) | `0` hallazgos en todo el árbol |
| **2. Infraestructura IaC/FS** | Escaneo Trivy de manifiestos Docker, compose y dependencias | `make qa-infra` (`./scripts/auditar-infra.sh`) | `0` hallazgos `HIGH`/`CRITICAL` |
| **3. Scripts Bash** | Formato, análisis estático y pruebas shell BATS | `make qa-bash` (`shfmt -i 2 -ci`, `ShellCheck`, `kcov`) | Cobertura `kcov >= 95%`, `0` alertas |
| **4. Arquitectura CALM** | Validación estructural FINOS CALM `1.2` | `make qa-calm` (`validate_calm_architecture.sh`) | `7/7` controles obligatorios |
| **5. Topología AST** | Grafo `--code-only` y frontera estricta de capas | `./scripts/actualizar-grafos-graphify.sh` | `0` nodos `.md` y `0` violaciones |
| **6. Lint, SAST & CVEs** | Estilo, tipado estricto, SAST y auditoría de paquetes | `make -C backend qa-lint`, `qa-deps`, `make -C frontend qa-lint` | `0` errores (`ruff`, `mypy --strict`, `bandit`, `uv audit`, `vue-tsc`, `eslint`) |
| **7. Complejidad** | Complejidad ciclomática y mantenibilidad | `make -C backend qa-complexity` (`radon_gates.py`), `SonarJS` | Backend **Grado A** (`CC <= 5`, `MI >= A`); Frontend `CC <= 15` |
| **8. Componentes UI** | Paridad 1:1 de componentes Vue con suites unitarias | `make -C frontend qa-orphans` | `0` componentes `.vue` huérfanos |
| **9. Pruebas Unitarias** | Suites aisladas sin red ni estado compartido | `make -C backend qa-unit`, `make -C frontend qa-unit` | Cobertura `>= 95%` (`pytest` / `Vitest V8` + build Vite) |
| **10. Paridad Real BD** | Migraciones Alembic ↔ ORM y aislamiento RLS en PostgreSQL 17 | `make -C backend qa-parity` | Ciclo `upgrade -> downgrade -> upgrade` + `27/27` tablas RLS |
| **11. Mutación AST** | Calidad real de aserciones contra mutantes sintéticos | `make -C backend qa-mutation`, `make -C frontend qa-mutation` | `MSI >= 80%` (`Mutmut` / `Stryker`) |
| **12. BDD, E2E & UX** | Flujos Gherkin, Screenplay, WCAG 2.1/2.2 AA y Lighthouse CI | `make qa-bdd`, `make qa-ui-bdd`, `make qa-e2e`, `make qa-perf` | `100%` pass, `0` violaciones a11y, `CLS = 0` |
| **13. Fuzzing, DAST & Caos** | Contratos OpenAPI, seguridad dinámica y resiliencia bajo carga | `make -C backend qa-contracts`, `qa-dast`, `qa-chaos` | `0` fallos 5xx (`Schemathesis`), `0` `FAIL-NEW` (`ZAP`), `Pumba + Locust` |

---

## 3. Compuerta Final de Certificación y Limpieza Segura

Al concluir cualquier tarea de código o documentación, se exige ejecutar la compuerta de cierre de 10 etapas (`QA-GIT-GATE-01`) y purgar exclusivamente la infraestructura temporal QA:

```bash
./.agents/scripts/certify_task_completion.sh --strict   # Compuerta 10/10 en sinfallas/base-python-uv:3.13
./scripts/limpieza.sh --quiet                           # Purga únicamente docker-compose*.qa.yml (preserva volúmenes prod y SBOM/AST)
```

---

## 4. Referencias Oficiales del Repositorio

- **[`AGENTS.md`](../../AGENTS.md)** — Directivas operativas de gobernanza Thin-Repo, rutas de ejecución y protocolo `QA-GIT-GATE-01`.
- **[`TESTING.md`](../../TESTING.md)** — Bitácora maestra consolidada con métricas y evidencias de certificación 11X.
- **[`backend/TESTING.md`](../../backend/TESTING.md)** — Detalle de suites unitarias, integración PostgreSQL 17 RLS, mutación, Karate API, Schemathesis, ZAP y caos.
- **[`frontend/TESTING.md`](../../frontend/TESTING.md)** — Detalle de cobertura Vitest, Stryker, Playwright Screenplay, WCAG 2.1/2.2 AA, Lighthouse CI y Karate UI.
- **[`SECURITY.md`](../../SECURITY.md)** — Política de divulgación responsable, defensa en profundidad y catálogo de los **22 vectores** de ataque mitigados.
