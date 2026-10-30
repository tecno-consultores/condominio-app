# 📐 Especificaciones Técnicas y de Dominio (`docs/specs/`) — Condominio App

Bienvenido al directorio de especificaciones técnicas formales (**Specs**) de **Condominio App**. Estos documentos constituyen la fuente de verdad canónica para el desarrollo del Backend (FastAPI), el Worker Asíncrono y la Interfaz Gráfica de Usuario (GUI Mobile-First en Vue 3) bajo el estándar corporativo **Nivel 11X**.

---

## 📚 Catálogo de Especificaciones

| Documento | Dominio / Alcance | Hitos Asociados | Estado |
| :--- | :--- | :--- | :--- |
| **[`01_ARQUITECTURA_Y_SEGURIDAD_11X.md`](./01_ARQUITECTURA_Y_SEGURIDAD_11X.md)** | Topología de contenedores, KeyDB Multi-Hilo, PostgreSQL 17, MinIO AVIF y los 18 patrones de seguridad híbrida (SPA + API) e idempotencia. | Transversal (Fases 1–4) | ✅ Implementado y Certificado (Backend + GUI) |
| **[`02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md`](./02_DOMINIO_IDENTIDAD_ESTRUCTURA_Y_RBAC.md)** | Autenticación JWT (`HttpOnly` + `Bearer`), Flujo de "Usuario Fantasma", Constructor de Estructuras (`EDIFICIO`/`TORRE`/`BLOQUE`/`MANZANA`/`CALLE`), `Contratos_Ocupacion` y Matriz RBAC. | Hitos 1, 2, 4, 5 y 7 | ✅ Completado en Backend y GUI (Hitos 1, 2, 4, 5 y 7) |
| **[`03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md`](./03_DOMINIO_FINANZAS_COBRANZAS_Y_CANDADO.md)** | Contabilidad multimoneda (USD/VES), Tasa del Día, Wizard de Reporte de Pagos idempotente, Aprobación/Rechazo, `Auditoria_Recibos` y Candado Contable. | Hitos 3 y 6 | ✅ Completado en Backend (Hito 3) y GUI (Hito 6) |
| **[`04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md`](./04_DOMINIO_OPERACIONES_INCIDENCIAS_Y_WORKER.md)** | Embudo de Incidencias ("Me Sumo"), Plantillas y Checklist Diario del Conserje, Galería de Voceros (máx. 30 fotos/mes), Bitácora del Secretario, Comunicados y Worker AVIF/Email. | Hitos 4 y 7 | ✅ Completado en Backend (Hito 4) y GUI (Hito 7) |
| **[`05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`](./05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md)** | Arquitectura Frontend Vue 3 + TypeScript + Pinia + Vue Router, Sistema de Diseño Mobile-First, Ergonomía In-Flow (Anti-JSDOM), Stores no destructivos, Seguridad Cliente y Contratos de Vistas. | Hitos 5, 6, 7, 8 y Fase 4 | ✅ Hitos 5, 6, 7, 10 y 11 Completados / Hitos 12–14 y Hito 8 Especificados |
| **[`06_INFORME_INVESTIGACION_Y_EVOLUCION_PROPIEDAD_HORIZONTAL.md`](./06_INFORME_INVESTIGACION_Y_EVOLUCION_PROPIEDAD_HORIZONTAL.md)** | Auditoría de consistencia Código ↔ Specs e investigación del estado del arte PropTech LATAM + Ley de Propiedad Horizontal (Venezuela). | Evolución Fase 4 | 📋 Especificado y Auditado |
| **[`07_DOMINIO_ALICUOTAS_FACTURACION_Y_SOLVENCIA.md`](./07_DOMINIO_ALICUOTAS_FACTURACION_Y_SOLVENCIA.md)** | Motor de Alícuotas ($\sum = 100\%$), Método del Resto Mayor (Hamilton), `FondoCondominio`, `ReciboItem`, Saldo a Favor (`credito_disponible_usd`), Anti-Fraude de Referencias y `CertificadoSolvencia` (`HMAC-SHA256`). | Hito 10 (Fase 4) | ✅ Implementado y Certificado en Backend y GUI (Hito 10) |
| **[`08_DOMINIO_GOBERNANZA_CARTAS_CONSULTA_Y_ASAMBLEAS.md`](./08_DOMINIO_GOBERNANZA_CARTAS_CONSULTA_Y_ASAMBLEAS.md)** | Gobernanza Digital (Art. 23 y 24 LPH), Cartas Consulta y Asambleas, Voto Ponderado por Alícuota, Recibo Criptográfico (`HMAC-SHA256`), Quórum $2/3$ y Acta Automática en `BitacoraActa`. | Hito 11 (Fase 4) | ✅ Implementado y Certificado en Backend y GUI (Hito 11) |
| **[`09_DOMINIO_ACCESOS_QR_PAQUETERIA_Y_AMENIDADES.md`](./09_DOMINIO_ACCESOS_QR_PAQUETERIA_Y_AMENIDADES.md)** | Pases de Visita QR (`HMAC-SHA256` + `jti` anti-replay en KeyDB), Paquetería en Garita (`PaqueteRecibido`) y Reserva de Áreas Sociales bloqueada a morosos con inspección post-evento. | Hitos 12 y 13 (Fase 4) | 📋 Especificación Detallada Lista para Implementación |

---

## 🗺️ Mapa de Trazabilidad: Vistas GUI ↔ Endpoints API ↔ Specs

| Ruta Vue 3 (GUI) | Vista / Componente Principal | Endpoints FastAPI Consumidos | Spec de Referencia |
| :--- | :--- | :--- | :--- |
| `/login`, `/register` | `LoginView.vue`, `RegisterView.vue` | `POST /api/auth/login`, `POST /api/auth/register`, `GET /api/estructura/unidades` | `02_DOMINIO_IDENTIDAD...`, `05_ARQUITECTURA_GUI...` |
| `/espera-aprobacion` | `PendingApprovalView.vue` | `GET /api/auth/me` | `02_DOMINIO_IDENTIDAD...`, `05_ARQUITECTURA_GUI...` |
| `/` o `/dashboard` | `DashboardView.vue` (`ClosingBanner.vue`, `AnnouncementsCarousel.vue`, `CollectionTrafficLight.vue`, `ExpensesDonutChart.vue`) | `GET /api/finanzas/tasa`, `GET /api/finanzas/resumen`, `GET /api/comunicados/recientes` | `03_DOMINIO_FINANZAS...`, `05_ARQUITECTURA_GUI...` |
| `/finanzas/reportar-pago` | `PaymentWizardView.vue` (3 pasos + `Idempotency-Key`) | `GET /api/finanzas/tasa`, `POST /api/pagos/reportar` | `03_DOMINIO_FINANZAS...`, `05_ARQUITECTURA_GUI...` |
| `/tesoreria/pagos` | `TreasuryPaymentsView.vue` + `RejectPaymentModal.vue` | `GET /api/pagos/revision`, `PUT /api/pagos/{id}/aprobar`, `PUT /api/pagos/{id}/rechazar` | `03_DOMINIO_FINANZAS...`, `05_ARQUITECTURA_GUI...` |
| `/tesoreria/cierre` | `TreasuryClosingView.vue` | `POST /api/finanzas/tasa`, `POST /api/finanzas/egresos`, `POST /api/finanzas/cierre-mensual` | `03_DOMINIO_FINANZAS...`, `05_ARQUITECTURA_GUI...` |
| `/tesoreria/facturacion` | `BillingGeneratorView.vue` + `ReceiptBreakdownModal.vue` | `POST /api/finanzas/fondos`, `GET /api/finanzas/fondos`, `POST /api/finanzas/facturar-periodo`, `GET /api/finanzas/recibos/{id}/desglose` | `07_DOMINIO_ALICUOTAS...`, `05_ARQUITECTURA_GUI...` |
| `/finanzas/solvencia` | `SolvencyCertificateView.vue` | `POST /api/finanzas/solvencia/{unidad_id}`, `GET /api/finanzas/solvencia/verificar/{folio}` | `07_DOMINIO_ALICUOTAS...`, `05_ARQUITECTURA_GUI...` |
| `/incidencias` | `IncidentsFeedView.vue` + `IncidentCard.vue` | `GET /api/incidencias/abiertas`, `POST /api/incidencias/{id}/adherir`, `POST /api/incidencias/crear` | `04_DOMINIO_OPERACIONES...`, `05_ARQUITECTURA_GUI...` |
| `/admin/estructura` | `AdminStructureView.vue` | `POST /api/estructura/generar`, `GET /api/estructura/unidades`, `PUT /api/estructura/unidades/{id}/alicuota` | `02_DOMINIO_IDENTIDAD...`, `07_DOMINIO_ALICUOTAS...` |
| `/admin/usuarios` | `AdminGhostUsersView.vue` | `GET /api/usuarios/pendientes`, `PUT /api/usuarios/{id}/asignar` | `02_DOMINIO_IDENTIDAD...`, `05_ARQUITECTURA_GUI...` |
| `/admin/junta` | `AdminBoardRolesView.vue` | `PUT /api/junta/cargos` | `02_DOMINIO_IDENTIDAD...`, `05_ARQUITECTURA_GUI...` |
| `/operaciones/tareas` | `OperationsTasksView.vue` + `TaskChecklistItem.vue` | `POST /api/tareas/plantillas`, `GET /api/tareas/diarias`, `PUT /api/tareas/{id}/completar` | `04_DOMINIO_OPERACIONES...`, `05_ARQUITECTURA_GUI...` |
| `/voceros/galeria` | `SpokespersonGalleryView.vue` (Contador `X/30` + Grid) | `POST /api/voceros/fotos`, `GET /api/voceros/galeria` | `04_DOMINIO_OPERACIONES...`, `05_ARQUITECTURA_GUI...` |
| `/secretaria/bitacora` | `SecretaryLogbookView.vue` (Editor + Timeline) | `POST /api/bitacora/acta`, `GET /api/bitacora/historial`, `POST /api/comunicados` | `04_DOMINIO_OPERACIONES...`, `05_ARQUITECTURA_GUI...` |
| `/consultas`, `/consultas/:id` | `ConsultationsListView.vue`, `ConsultationDetailView.vue`, `VoteReceiptModal.vue` | `POST /api/consultas`, `GET /api/consultas`, `GET /api/consultas/{id}`, `POST /api/consultas/{id}/votar`, `POST /api/consultas/{id}/cerrar` | `08_DOMINIO_GOBERNANZA...`, `05_ARQUITECTURA_GUI...` |
| `/accesos/pases`, `/operaciones/garita-qr` | `VisitorPassesView.vue`, `GatehouseScannerView.vue` | `POST /api/accesos/pases`, `GET /api/accesos/pases/mios`, `DELETE /api/accesos/pases/{id}`, `POST /api/accesos/verificar-qr` | `09_DOMINIO_ACCESOS_QR...`, `05_ARQUITECTURA_GUI...` |
| `/operaciones/paqueteria` | `ParcelsTrackerView.vue` | `POST /api/paqueteria/registrar`, `GET /api/paqueteria`, `PUT /api/paqueteria/{id}/entregar` | `09_DOMINIO_ACCESOS_QR...`, `05_ARQUITECTURA_GUI...` |
| `/reservas/areas` | `AmenitiesReservationView.vue` | `POST /api/reservas/areas`, `GET /api/reservas/areas`, `POST /api/reservas/solicitar`, `PUT /api/reservas/{id}/inspeccionar` | `09_DOMINIO_ACCESOS_QR...`, `05_ARQUITECTURA_GUI...` |
