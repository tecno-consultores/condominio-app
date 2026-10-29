# 🏢 Condominio App

**Condominio App** es una plataforma de código abierto (MIT) diseñada para modernizar y transparentar la administración de condominios, edificios y urbanizaciones bajo el estándar corporativo **Gobernanza y Calidad Nivel 11X**.

Construida con una arquitectura modular **Mobile-First**, resuelve los problemas críticos de la gestión condominal: control de pagos multimoneda (USD / VES con tasa BCV), inmutabilidad del **Candado Contable**, auditoría forense de rechazos, activación controlada de residentes (**Usuarios Fantasma**), embudo vecinal de incidencias ("¡Me sumo!") y checklist diario de conserjería.

---

## 🚀 Tecnologías Principales

- **Backend:** FastAPI (Python 3.12+) + SQLAlchemy 2.0 Async + Alembic + PostgreSQL 17
- **Motor en Memoria (Idempotencia, Rate-Limiting & Colas):** KeyDB Multi-Hilo (`eqalpha/keydb:alpine --server-threads 2`)
- **Frontend:** Vue 3 (`<script setup lang="ts">`) + Pinia + Vue Router + Tailwind CSS (Mobile-First, Anti-JSDOM Layout & WCAG 2.1 AA)
- **Almacenamiento Multimedia:** MinIO (S3 Compatible) con conversión asíncrona a formato AVIF y lectura segura por chunks ($\le 2\text{ MB}$)
- **Gobernanza IA & QA 11X:** Ecosistema `.agents/` (`Rule Zero`: 100% contenedores Docker efímeros `sinfallas/*`)

---

## 📁 Estructura del Repositorio

```text
condominio-app/
├── .agents/                # Gobernanza IA Nivel 11X (rules, skills y scripts de certificación)
├── backend/                # API FastAPI + Seguridad 11X (Fase 1)
│   ├── src/                # Código fuente (models, schemas, routers, finanzas, security, redis_client)
│   ├── tests/              # Suites unitarias aisladas (test_*.unit.py, cobertura >= 95%)
│   ├── test/               # Escenarios BDD Gherkin (Karate Labs: api_test.feature)
│   ├── alembic/            # Migraciones verificadas contra PostgreSQL 17 real
│   ├── Makefile            # Orquestación de gates QA efímeros en Docker
│   ├── docker-compose.qa.yml
│   └── TESTING.md          # Bitácora detallada de pruebas del backend
├── docs/
│   ├── specs/              # Especificaciones técnicas de Dominio, Seguridad 11X y GUI Vue 3
│   ├── qa/                 # Manuales maestros de Arquitectura, Buenas Prácticas, QA y Seguridad 11X
│   ├── ARCHITECTURE.md     # Visión general de roles y máquinas de estado
│   └── API_ROUTES.md       # Mapa de vistas (GUI) y endpoints REST
├── scripts/
│   └── verificar-secretos.sh # Escáner global de credenciales y llaves privadas
├── AGENTS.md               # Directivas supremas para agentes de IA y desarrolladores
├── SECURITY.md             # Política de seguridad y arquitectura defensiva 11X
├── ROADMAP.md              # Plan maestro de hitos y sub-tareas (Backend, GUI Vue 3 y Caos)
├── TESTING.md              # Resumen ejecutivo de certificación QA 11X
├── CHANGELOG.md            # Historial semántico de cambios
└── README.md
```

---

## 🧪 Calidad y Seguridad (Estándar Nivel 11X — `Rule Zero`)

Toda validación corre en **contenedores Docker efímeros** (`sinfallas/*`), sin instalar herramientas en el host.

```bash
# Gates del Backend (desde la raíz o backend/)
make -C backend qa-lint         # Ruff + Mypy (--strict) + Bandit (SAST)
make -C backend qa-complexity   # Radon (Complejidad Ciclomática e Índice de Mantenibilidad <= B)
make -C backend qa-deps         # Auditoría de vulnerabilidades en dependencias (uv audit)
make -C backend qa-unit         # Pruebas unitarias + cobertura (>= 95%)
make -C backend qa-parity       # Paridad real Alembic <-> ORM contra PostgreSQL 17
make -C backend qa-bdd          # Escenarios BDD en Gherkin (Karate Labs)
make -C backend qa-contracts    # Fuzzing de contratos OpenAPI (Schemathesis)
make -C backend qa-dast         # Seguridad dinámica (OWASP ZAP)
make -C backend qa-chaos        # Resiliencia y caos (Pumba + Locust + Prometheus)

# Gate Integral de Certificación de Cierre (.agents)
./.agents/scripts/certify_task_completion.sh
```

---

## 📚 Documentación y Especificaciones (`docs/specs/`)

1. **[`docs/specs/README.md`](./docs/specs/README.md)** — Índice maestro de especificaciones técnicas y trazabilidad.
2. **[`docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md`](./docs/specs/01_ARQUITECTURA_Y_SEGURIDAD_11X.md)** — Arquitectura de contenedores, KeyDB Multi-Hilo y las 13 defensas de seguridad híbrida SPA + API.
3. **[`docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md`](./docs/specs/02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md)** — Ciclo de vida de Usuarios Fantasma, Estructura, Unidades, Contratos y matriz RBAC.
4. **[`docs/specs/03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md`](./docs/specs/03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md)** — Core matemático multimoneda, pagos parciales/totales, auditoría de rechazos y Candado Contable.
5. **[`docs/specs/04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md`](./docs/specs/04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md)** — Embudo de incidencias ("¡Me sumo!"), cuota de 30 fotos/mes, conserjería y worker AVIF.
6. **[`docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md)** — Especificación completa de la GUI Vue 3 Mobile-First, ergonomía Anti-JSDOM, stores Pinia no destructivos y paridad 1:1 API ↔ GUI.

---

## 📄 Licencia

Distribuido bajo licencia **MIT**. Ver [`LICENSE`](./LICENSE) para más detalles.
