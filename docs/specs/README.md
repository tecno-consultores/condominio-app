# 📐 Especificaciones Técnicas y de Dominio (`docs/specs/`) — Condominio App

Bienvenido al directorio de especificaciones técnicas formales (**Specs**) de **Condominio App**. Estos documentos constituyen la fuente de verdad canónica para el desarrollo del Backend (FastAPI), el Worker Asíncrono y la Interfaz Gráfica de Usuario (GUI Mobile-First en Vue 3) bajo el estándar corporativo **Nivel 11X**.

---

## 📚 Catálogo de Especificaciones

| Documento | Dominio / Alcance | Hitos Asociados | Estado |
| :--- | :--- | :--- | :--- |
| **[`01_ARQUITECTURA_Y_SEGURIDAD_11X.md`](./01_ARQUITECTURA_Y_SEGURIDAD_11X.md)** | Topología de contenedores, KeyDB Multi-Hilo, PostgreSQL 17, MinIO AVIF y los 13 patrones de seguridad híbrida (SPA + API). | Transversal (Fases 1–3) | ✅ Implementado en Backend / Especificado para GUI |
| **[`02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md`](./02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md)** | Autenticación JWT (`HttpOnly` + `Bearer`), Flujo de "Usuario Fantasma", Constructor de Estructuras (Edificios/Calles/Unidades), `Contratos_Ocupacion` y Matriz RBAC. | Hitos 1, 2, 4, 5 y 7 | 🔄 Core en Hitos 1–2 ✅ / Gestión Junta en Hito 4 |
| **[`03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md`](./03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md)** | Contabilidad multimoneda (USD/VES), Tasa del Día, Wizard de Reporte de Pagos idempotente, Aprobación/Rechazo, `Auditoria_Recibos` y Candado Contable. | Hitos 3 y 6 | ✅ Backend Hito 3 Completado / GUI en Hito 6 |
| **[`04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md`](./04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md)** | Embudo de Incidencias ("Me Sumo"), Plantillas y Checklist Diario del Conserje, Galería de Voceros (máx. 30 fotos/mes), Bitácora del Secretario, Comunicados y Worker AVIF/Email. | Hitos 4 y 7 | 📋 Especificado para Hitos 4 y 7 |
| **[`05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md)** | Arquitectura Frontend Vue 3 + TypeScript + Pinia + Vue Router, Sistema de Diseño Mobile-First, Ergonomía In-Flow (Anti-JSDOM), Stores no destructivos, Seguridad Cliente y Contratos de Vistas. | Hitos 5, 6, 7 y 8 | 📋 Especificado para Arranque de GUI (Fase 2) |

---

## 🗺️ Mapa de Trazabilidad: Vistas GUI ↔ Endpoints API ↔ Specs

| Ruta Vue 3 (GUI) | Vista / Componente Principal | Endpoints FastAPI Consumidos | Spec de Referencia |
| :--- | :--- | :--- | :--- |
| `/login`, `/register` | `AuthView.vue` (`LoginForm.vue`, `RegisterForm.vue`) | `POST /api/auth/login`, `POST /api/auth/register`, `GET /api/estructura/unidades` | `02_DOMINIO_IDENTIDAD...`, `05_ARQUITECTURA_GUI...` |
| `/espera-aprobacion` | `PendingApprovalView.vue` | `GET /api/auth/me` | `02_DOMINIO_IDENTIDAD...`, `05_ARQUITECTURA_GUI...` |
| `/` o `/dashboard` | `DashboardView.vue` (`ClosingBanner.vue`, `AnnouncementsCarousel.vue`, `CollectionTrafficLight.vue`, `ExpensesDonutChart.vue`) | `GET /api/finanzas/tasa`, `GET /api/finanzas/resumen`, `GET /api/comunicados/recientes` | `03_DOMINIO_FINANZAS...`, `05_ARQUITECTURA_GUI...` |
| `/finanzas/reportar-pago` | `PaymentWizardView.vue` (3 pasos + `Idempotency-Key`) | `GET /api/finanzas/tasa`, `POST /api/pagos/reportar` | `03_DOMINIO_FINANZAS...`, `05_ARQUITECTURA_GUI...` |
| `/tesoreria/pagos` | `TreasuryPaymentsView.vue` + `RejectPaymentModal.vue` | `GET /api/pagos/revision`, `PUT /api/pagos/{id}/aprobar`, `PUT /api/pagos/{id}/rechazar` | `03_DOMINIO_FINANZAS...`, `05_ARQUITECTURA_GUI...` |
| `/tesoreria/cierre` | `TreasuryClosingView.vue` + `ExpenseFormModal.vue` | `POST /api/finanzas/tasa`, `POST /api/finanzas/egresos`, `POST /api/finanzas/cierre-mensual` | `03_DOMINIO_FINANZAS...`, `05_ARQUITECTURA_GUI...` |
| `/incidencias` | `IncidentsFeedView.vue` + `IncidentCreateModal.vue` | `GET /api/incidencias/abiertas`, `POST /api/incidencias/{id}/adherir`, `POST /api/incidencias/crear` | `04_DOMINIO_OPERACIONES...`, `05_ARQUITECTURA_GUI...` |
| `/admin/estructura` | `AdminStructureView.vue` | `POST /api/estructura/generar`, `GET /api/estructura/unidades` | `02_DOMINIO_IDENTIDAD...`, `05_ARQUITECTURA_GUI...` |
| `/admin/usuarios` | `AdminGhostUsersView.vue` | `GET /api/usuarios/pendientes`, `PUT /api/usuarios/{id}/asignar` | `02_DOMINIO_IDENTIDAD...`, `05_ARQUITECTURA_GUI...` |
| `/admin/junta` | `AdminBoardRolesView.vue` | `GET /api/junta/cargos`, `PUT /api/junta/cargos` | `02_DOMINIO_IDENTIDAD...`, `05_ARQUITECTURA_GUI...` |
| `/operaciones/tareas` | `OperationsTasksView.vue` (Presidente / Conserje / Propietario) | `POST /api/tareas/plantillas`, `GET /api/tareas/diarias`, `PUT /api/tareas/{id}/completar` | `04_DOMINIO_OPERACIONES...`, `05_ARQUITECTURA_GUI...` |
| `/voceros/galeria` | `SpokespersonGalleryView.vue` (Contador `X/30` + Grid) | `POST /api/voceros/fotos`, `GET /api/voceros/galeria` | `04_DOMINIO_OPERACIONES...`, `05_ARQUITECTURA_GUI...` |
| `/secretaria/bitacora` | `SecretaryLogbookView.vue` (Editor + Timeline) | `POST /api/bitacora/acta`, `GET /api/bitacora/historial`, `POST /api/comunicados/crear` | `04_DOMINIO_OPERACIONES...`, `05_ARQUITECTURA_GUI...` |
