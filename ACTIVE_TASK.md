# 📌 Diario de Tarea Activa (`ACTIVE_TASK.md`) — Condominio App

**Propósito:** Bitácora persistente de estado en curso para recuperación determinista ante interrupciones de sesión o fallos de red/energía (Directiva de Continuidad 11X).

---

## 🎯 Tarea Actual en Ejecución
- **Fase:** **Planeación Arquitectónica, Especificación Exhaustiva (`docs/specs/01..09`), Gobernanza y Actualización de Roadmap (Sin modificar código fuente aún)**
- **Rama Git:** `main`
- **Estado Global:** `COMPLETADO`
- **Siguiente Hito en Cola:** **Hito 10 — Mejoras Core, Motor de Alícuotas, Facturación Mensual LPH, Fondos y Solvencia Digital** (o **Hito 8 — Certificación E2E Playwright, Geometría Visual Anti-JSDOM, WCAG 2.1 AA y Lighthouse CI** según prioridad del usuario)

---

## ✅ Hitos Completados Previamente
- [x] **Hito 1, 2, 3 y 3.5:** Backend Core, Seguridad Híbrida SPA+API 11X, KeyDB Multi-Hilo, Paridad PostgreSQL 17 y Specs (`89fd230`).
- [x] **Hito 4:** Backend Operativo (Estructura, Usuarios Fantasma, Junta, Incidencias "Me Sumo", Conserjería, Galería de Voceros 30 fotos/mes, Bitácora, Comunicados Anti-SSRF y Worker AVIF) (`4a0286e`).
- [x] **Hito 5:** Arquitectura Base Frontend Vue 3 Mobile-First, Seguridad Cliente, Layout Anti-JSDOM y Vistas de Identidad (`3183de2`).
- [x] **Hito 6:** Vistas Financieras, Wizard de Pagos Idempotente en 3 Pasos, Mesa de Tesorería y Candado Contable (`114a49b`).
- [x] **Hito 7:** Vistas Administrativas, Embudo de Incidencias, Conserjería, Grafo AST (`1.075 nodos, 2.464 relaciones, 59 comunidades`) y Gobernanza 11X (`c1e14fc`).
- [x] **Auditoría Código ↔ Specs e Investigación PropTech Inicial:** Endurecimiento RBAC en `finanzas.py` y `pagos.py`, validador `UrlEvidenciaSegura` en `schemas.py`, paridad `TipoEstructura`, 162 tests backend (`99.84%`) e informe `docs/specs/06_INFORME_INVESTIGACION_Y_EVOLUCION_PROPIEDAD_HORIZONTAL.md` (`ab62041`).

---

## 🔄 Sub-Tareas de la Fase de Planeación y Especificación (Checkpoints de Recuperación)
- [x] **CP-P.0:** Inicialización de `ACTIVE_TASK.md` y plan de trabajo en `task.md`.
- [x] **CP-P.1:** Investigación técnica sobre algoritmos de prorrateo exacto con ajuste de residuo (*Largest Remainder Method* / Hamilton), firmas `HMAC-SHA256` para Cartas Consulta / Pases QR / Solvencias y validación de *Magic Bytes*.
- [x] **CP-P.2:** Creación de las nuevas especificaciones exhaustivas:
  - `docs/specs/07_DOMINIO_ALICUOTAS_FACTURACION_Y_SOLVENCIA.md`
  - `docs/specs/08_DOMINIO_GOBERNANZA_CARTAS_CONSULTA_Y_ASAMBLEAS.md`
  - `docs/specs/09_DOMINIO_ACCESOS_QR_PAQUETERIA_Y_AMENIDADES.md`
- [x] **CP-P.3:** Actualización de especificaciones existentes (`docs/specs/01..06`, `docs/specs/README.md`, `docs/ARCHITECTURE.md`, `docs/API_ROUTES.md` y `SECURITY.md`).
- [x] **CP-P.4:** Reestructuración detallada de `ROADMAP.md` con todos los hitos y sub-tareas de mejoras y nuevos módulos (Hitos 10, 11, 12, 13 y 14: Backend + Frontend + Ayuda Contextual en cada pantalla + Manuales Markdown para Admin/Instalador y Usuario + QA 11X).
- [x] **CP-P.5:** Evolución de archivos de gobernanza (`AGENTS.md`, `.agents/rules/`, `scripts/limpieza.sh`, `.gitignore`).
- [x] **CP-P.6:** Actualización de `CHANGELOG.md`, `README.md` y cierre de checkpoints en `ACTIVE_TASK.md`.
- [x] **CP-P.7:** Certificación con `./.agents/scripts/certify_task_completion.sh`.
