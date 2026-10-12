# 🏢 Condominio App

**Condominio App** es una solución de código abierto (MIT) diseñada para modernizar y transparentar la administración de condominios, edificios y urbanizaciones.

Construida bajo una arquitectura de microservicios ligera y pensada para ser **Mobile-First**, la plataforma resuelve los problemas más comunes de la vida en condominio: control de pagos multimoneda, auditoría inmutable de fondos, gestión de tareas del personal, y un embudo eficiente para reportes de incidencias vecinales.

### 🚀 Tecnologías Principales
* **Backend:** FastAPI (Python) + PostgreSQL
* **Frontend:** Vue 3 (Mobile-First)
* **Infraestructura:** Despliegue 100% Dockerizado + Nginx Proxy Manager
* **Almacenamiento:** MinIO (S3 Compatible) con procesamiento asíncrono a formato AVIF.

---

## 📁 Estructura del Repositorio

```
condominio-app/
├── backend/            # API FastAPI (Fase 1)
│   ├── src/            # Código fuente (models, schemas, routers, finanzas, seguridad)
│   ├── tests/          # Suites unitarias con mocking (test_*.unit.py)
│   ├── test/           # Escenarios BDD Gherkin (Karate)
│   ├── alembic/        # Migraciones de base de datos
│   ├── Makefile        # Orquestación de la QA efímera en Docker
│   ├── docker-compose.qa.yml
│   └── TESTING.md      # Bitácora viva de pruebas
├── docs/               # Arquitectura, rutas API y manual de QA Nivel 11X
├── ROADMAP.md          # Control de hitos y tareas
├── LICENSE             # MIT
└── README.md
```

---

## 🧪 Calidad y Pruebas (Estándar Nivel 11X)

Toda validación corre en **contenedores Docker efímeros** (imágenes `sinfallas/*`), sin instalar nada en el host y sin `docker build` locales. El piso de calidad es innegociable: **cobertura ≥ 95%**, complejidad grado A/B, y cero hallazgos SAST.

Pila: `ruff`, `mypy --strict`, `bandit`, `radon`, `pytest` + `pytest-cov` + `pytest-mock` + `TestClient`, `mutmut`, `schemathesis`, `OWASP ZAP`, `Karate Labs`, `Locust` + `Pumba` + `Prometheus`.

Backend (desde `backend/`):

```bash
make qa-unit         # Pruebas unitarias + cobertura (>=95%)
make qa-lint         # Ruff + Mypy (strict) + Bandit (SAST)
make qa-complexity   # Radon (complejidad ciclomática e índice de mantenibilidad)
make qa-mutation     # Pruebas de mutación (mutmut)
make qa-contracts    # Fuzzing de contratos OpenAPI (schemathesis)
make qa-dast         # Seguridad dinámica (OWASP ZAP)
make qa-chaos        # Resiliencia y caos (Pumba + Locust + Prometheus)
make qa-all          # Pipeline integral
```

> Requisito: Docker (y Docker Compose) disponibles; el contenedor de trabajo necesita acceso a `/var/run/docker.sock`.

---

## 📊 Estado del Proyecto

- **Fase 1 — Backend Base y Estructura (FastAPI)**
  - Hito 1: Setup Base y Modelos de Datos — ✅ Completado
  - Hito 2: Autenticación y JWT — ✅ Completado
  - Hito 3: Finanzas y Cobranzas (Core Matemático) — ✅ Completado
  - Hito 4: Módulos Operativos y Tareas Asíncronas — ⏳ Pendiente
- **Fase 2 — Frontend Base (Vue 3)** — ⏳ Pendiente
- **Fase 3 — Integración y Caos (Nivel 11X)** — ⏳ Pendiente

Detalle completo en [`ROADMAP.md`](./ROADMAP.md).

---

## 📚 Documentación

* [`ROADMAP.md`](./ROADMAP.md) — Hitos y tareas.
* [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — Stack, roles y máquinas de estado.
* [`docs/API_ROUTES.md`](./docs/API_ROUTES.md) — Mapa de vistas (GUI) y endpoints.
* [`docs/qa/README.md`](./docs/qa/README.md) — Centro de documentación de QA Nivel 11X.
* [`backend/TESTING.md`](./backend/TESTING.md) — Bitácora de pruebas del backend.

---

## 📄 Licencia

Distribuido bajo licencia **MIT**. Ver [`LICENSE`](./LICENSE) para más detalles.
