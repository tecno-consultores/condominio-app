# Mapa de Vistas (GUI) y Rutas API
**Proyecto:** Condominio App
**Versión:** 1.0.0 (Lanzamiento Oficial)
**Inventario Verificado:** `23` rutas nombradas Vue 3 (`frontend/src/router/index.ts`, más redirección `/` $\to$ `/dashboard` y `6` alias) · `61` endpoints REST FastAPI (`59` rutas en `backend/src/routers/*.py` + `GET /health` + `GET /metrics`)

Este documento integra la navegación del Frontend (Vue 3), el diseño de la Interfaz Gráfica (UI/UX) y los Endpoints del Backend (FastAPI) requeridos para cada pantalla.

*Nota de Diseño General:* El layout principal en móviles utiliza una **Bottom Navigation Bar** y un cajón lateral `<dialog>` (`MobileNavDrawer`) con botón **Salir** en `< 768px`. En escritorio, muta a un **Sidebar** lateral. Toda mutación protegida por `IdempotentAPIRoute` (`Idempotency-Key` `8..128` caracteres, scope `idemp:{condominio_id}:{usuario_id}:{scope}:{key}`) aplica *replay* determinista en `2xx` (`X-Idempotency-Replayed: true`), rechaza cambios de cuerpo (`409`) y libera la clave en `4xx`/`5xx`. Todos los listados `GET` soportan paginación acotada (`limit=1..100`, `offset=0..1_000_000`).

*(Las rutas futuras de Spec 13 Fase 8 —recuperación de clave, multi-inmueble, estacionamientos/maleteros, exportación PDF y `WS /ws/notificaciones`— se detallan como hoja de ruta en `docs/specs/13_*` y `docs/ARCHITECTURE.md`, y no forman parte de los `61` endpoints activos de `v1.0.0`.)*

---

## 1. Módulo de Autenticación y Registro

### 🖥️ Vista: Pantalla de Inicio de Sesión y Registro
* **Ruta Vue:** `/login` | `/register`
* **Diseño GUI (Registro):** 
  * Formulario público: Nombre, Cédula, Correo, Teléfono.
  * Selectores: Buscador de Unidad (Ej. "A-42") y un selector de estatus inicial ("Soy Propietario" / "Soy Inquilino").
  * **Pantalla de Bloqueo:** Al completar el registro, el usuario es redirigido a `/espera-aprobacion` con un mensaje fijo: *"Registro completado. Esperando validación de la Junta"*.
* **Endpoints FastAPI:**
  * `POST /api/auth/login`: Autentica con lockout Lua atómico (`5` fallos / IP y `10` globales / cuenta en `15m` -> `429`), preservación de revocaciones administrativas activas (`403`), mitigación anti-timing (`DUMMY_PASSWORD_HASH`) y entrega JWT (`access_token` + `refresh_token` con claims `typ`/`iat`/`iss`/`aud`/`condominio_id`) en cookies `HttpOnly` junto con `csrf_token` (`X-CSRF-Token`).
  * `POST /api/auth/register`: Crea usuario "Fantasma" verificando existencia de la unidad solicitada (`404 Not Found`). *[Header: `Idempotency-Key` `8..128` caracteres, TTL `86400s`]* -> Dispara notificación por correo.
  * `POST /api/auth/refresh`: Rota el par `access_token` / `refresh_token` con periodo de gracia concurrente de `5s`, revoca el `sid` completo ante reuso tardío (`401`) y rota `X-CSRF-Token`.
  * `POST /api/auth/logout`: Revoca individualmente la sesión activa del dispositivo (`sid` y `jti`) en KeyDB, purga cookies y emite `Clear-Site-Data: "cookies", "storage", "cache"`.
  * `GET /api/auth/me`: Retorna perfil DTO completo (`id`, `nombre`, `cedula`, `correo`, `telefono`, `es_activo`, `rol`, `unidad_activa_id`) y rehidrata la cookie/cabecera `X-CSRF-Token`.

---

## 2. Dashboard Financiero (Inicio)

### 🖥️ Vista: Resumen y Cartelera
* **Ruta Vue:** `/dashboard` (alias `/inicio`; `/` redirige a `/dashboard`)
* **Diseño GUI:**
  * **Cabecera:** Logo, saludo al usuario y **Tasa de Cambio del Día**.
  * **Banner Condicional:** Si el día actual es entre el 1 y el 10, muestra una tarjeta destacada: *"📊 Cierre Financiero disponible"*.
  * **Carrusel de Comunicados:** Deslizable horizontalmente con los anuncios de la junta (soporta enlaces a WhatsApp/Webs).
  * **Cuerpo Central (Tabs):**
    * *Tab 1 (Estado de Cobranza):* Lista tipo semáforo (Verde: solventes, Rojo: deudores). La unidad del usuario aparece de primera.
    * *Tab 2 (Relación de Gastos):* Gráfica de dona dividida por categorías y lista de facturas.
  * **Botón Flotante (FAB):** Botón principal para `"Pagar / Reportar"`.
* **Endpoints FastAPI:**
  * `GET /api/finanzas/tasa`: Obtiene la tasa de cambio USD/VES vigente del día.
  * `GET /api/finanzas/resumen`: Devuelve deuda y egresos por categoría, con `estado_cobranza` completo para roles de Junta/Cobranza, filtrado a las unidades activas propias para residentes y vacío (`[]`) para `CONSERJE`.
  * `GET /api/comunicados/recientes`: Lista los comunicados activos de la cartelera.

---

## 3. Flujo de Reporte de Pagos

### 🖥️ Vista: Wizard de Pago
* **Ruta Vue:** `/finanzas/reportar-pago` (alias `/pagar`)
* **Diseño GUI (Proceso Paso a Paso):**
  * **Paso 1:** Selección de recibo pendiente, monto y selector `VES`/`USD` (conversión automática según tasa BCV vigente).
  * **Paso 2:** Selección de Método (`PAGO_MOVIL`, `TRANSFERENCIA`, `ZELLE`, `EFECTIVO`). *Regla UI: Si no es `EFECTIVO`, exige Número de Referencia (mínimo 4 caracteres).*
  * **Paso 3:** Subida opcional de comprobante (`AVIF`, `WebP`, `PNG`, `JPG` o `PDF`, $\le 2\text{ MB}$) y confirmación.
  * **Botón Final:** "Confirmar y Enviar Pago". Bloquea el envío concurrente mediante `useIdempotency`.
* **Endpoints FastAPI:**
  * `POST /api/evidencias/subir`: Ingesta previa opcional (`FormData` multipart con `categoria=comprobantes`) antes de reportar.
  * `POST /api/pagos/reportar`: Registra el pago (con campo opcional `url_comprobante` devuelto en `PagoResponse`) y la tasa del día exacto tras verificar titularidad activa en `ContratoOcupacion` (anti-IDOR, salvo roles `TESORERO`/`PRESIDENTE`) y unicidad parcial `uq_pagos_metodo_ref_activo` en `(metodo_pago, numero_referencia)` (`409 Conflict`). **Requiere campo `numero_referencia` en el payload si el método no es efectivo.** *[Header: Idempotency-Key]* -> Worker convierte imagen a AVIF.

---

## 4. Panel de Tesorería (Aprobaciones y Cierre)

### 🖥️ Vistas: Pagos Pendientes y Cierre de Mes
* **Ruta Vue:** `/tesoreria/pagos` (alias `/admin/pagos-revision`), `/tesoreria/cierre` (alias `/admin/finanzas`)
* **Diseño GUI:**
  * **Pagos Pendientes:** Lista de Tarjetas (Cards) expandibles (Acordeón). Al expandir, muestra el comprobante y cálculos. Dos botones grandes: `[ APROBAR ]` y `[ RECHAZAR ]`.
  * *Flujo de Rechazo:* Si pulsa rechazar, se oculta la evidencia y aparece un Modal `<dialog>` exigiendo escribir el "Motivo" para habilitar la confirmación.
  * **Cierre de Mes:** Presenta tres paneles operativos: registro de Tasa Oficial BCV del Día, registro de Gasto / Egreso multimoneda y ejecución inmutable del Candado Contable mediante `<dialog>` de confirmación. *(La exportación PDF del cierre corresponde a Spec 13 Fase 8.)*
* **Endpoints FastAPI:**
  * `POST /api/finanzas/tasa` y `GET /api/finanzas/tasa`: Registra/actualiza y consulta la tasa oficial USD/VES. *[Header: Idempotency-Key]*
  * `POST /api/finanzas/egresos`: Registra gastos operativos y egresos multimoneda (descontando del `FondoCondominio` `RESERVA_LEGAL` cuando `es_gasto_comun=false`) con validación de factura segura y bloqueo `409 Conflict` por Candado Contable (`ReporteMensual.estado == "CERRADO"`). *[Header: Idempotency-Key]*
  * `GET /api/pagos/revision`: Lista paginada (`limit`/`offset`) de pagos pendientes.
  * `PUT /api/pagos/{id}/aprobar`: Cambia estado con bloqueos pesimistas `.with_for_update()` (`PagoReportado`, `Recibo`, `Unidad`) y audita. *[Header: Idempotency-Key]*
  * `PUT /api/pagos/{id}/rechazar`: Requiere `motivo`, `.with_for_update()` y registra `AuditoriaRecibo`. *[Header: Idempotency-Key]*
  * `POST /api/finanzas/cierre-mensual`: Acción inmutable bloqueada con `409` mientras existan pagos `EN_REVISION`. Bloquea registros del mes y oficializa el periodo. *[Header: Idempotency-Key]*

---

## 5. Embudo de Incidencias ("Me Sumo")

### 🖥️ Vista: Feed de Reportes y Adhesión
* **Ruta Vue:** `/incidencias`
* **Diseño GUI:**
  * **Feed de Incidencias:** Estilo Instagram con tarjetas. Muestra foto, área, y un contador de afectados (*"🔥 12 vecinos"*).
  * **Botón Adherir:** Debajo de cada tarjeta, un botón `"Me Sumo"`. Al pulsarlo, el contador sube visualmente.
  * **Nuevo Reporte:** Solo al hacer scroll hasta el final del feed aparece el botón `"Crear nuevo reporte"`. Pide ubicación, descripción y foto.
* **Endpoints FastAPI:**
  * `GET /api/incidencias/abiertas`: Lista reportes de los últimos 7 días.
  * `POST /api/incidencias/{id}/adherir`: Suma el usuario actual al reporte.
  * `POST /api/incidencias/crear`: Nuevo reporte. *[Header: Idempotency-Key]* -> Worker notifica a la Junta.

---

## 6. Panel de Administración y Configuración

### 🖥️ Vistas: Estructura, Usuarios y Junta
* **Ruta Vue:** `/admin/estructura`, `/admin/usuarios` (alias `/admin/usuarios-pendientes`), `/admin/junta`
* **Diseño GUI:**
  * **Constructor:** Formulario para añadir Edificio/Torre/Bloque/Manzana/Calle y autogenerar identificadores (Ej. `A-42` o `42`), además de editar alícuota (%) y cuota fija diferenciada por unidad.
  * **Bandeja de Usuarios:** Tarjetas de Usuarios Fantasma pendientes con asignación de unidad, condición (`PROPIETARIO`/`INQUILINO`) y rol operativo (`PROPIETARIO`, `INQUILINO`, `CONSERJE`; bloqueando escalación directa hacia Junta/`PRESIDENTE`).
  * **Composición de Junta:** Asignación de cargos (`PRESIDENTE`, `VICEPRESIDENTE`, `TESORERO`, `SECRETARIO`, `VOCERO`) exclusiva de `PRESIDENTE`.
* **Endpoints FastAPI:**
  * `GET /api/estructura/unidades`: Lista las unidades con DTO dual: `UnidadResponse` completo (`alicuota`, `cuota_fija_usd`, `credito_disponible_usd`) exclusivo para roles de Junta/Cobranza (`PRESIDENTE`, `VICEPRESIDENTE`, `TESORERO`, `SECRETARIO`, `VOCERO`), y `UnidadPublicaResponse` (`id`, `identificador`, `estructura_id`) para residentes, Usuarios Fantasma y anónimos.
  * `POST /api/estructura/generar`: Crea sectores y unidades con su identificador.
  * `GET /api/usuarios/pendientes`: Lista "Fantasmas".
  * `PUT /api/usuarios/{id}/asignar`: Asigna unidad, rol y activa al usuario.
  * `PUT /api/junta/cargos`: Actualiza la composición de la junta.

---

## 7. Módulo de Operaciones (Conserjería y Voceros)

### 🖥️ Vistas: Tablero de Tareas y Galerías
* **Ruta Vue:** `/operaciones/tareas` (alias `/conserje/tareas`), `/voceros/galeria`
* **Diseño GUI:**
  * **Gestión Tareas (Presidente):** Creador con botones tipo pastilla para frecuencia (`Única`, `Diaria`, `Semanal`, `Mensual`).
  * **App Conserje:** Checklist diario ultra minimalista. Círculos grandes para hacer *check-off*. Permite adjuntar foto (AVIF) como evidencia de cumplimiento.
  * **Vista Tareas (Propietarios):** Panel de solo lectura para ver el avance del conserje.
  * **Galería Voceros (Modo Subida):** Botón gigante y contador *"X / 30 fotos este mes"*.
  * **Galería Voceros (Modo Público):** Cuadrícula de fotos (Grid) agrupada por áreas para que los propietarios vean el estado físico del conjunto.
* **Endpoints FastAPI:**
  * `POST /api/tareas/plantillas`: Presidente crea asignaciones periódicas.
  * `POST /api/tareas/diarias` y `POST /api/tareas/generar-diarias`: Crea una tarea puntual o genera las tareas diarias a partir de plantillas activas.
  * `GET /api/tareas/diarias`: Checklist del día en curso.
  * `PUT /api/tareas/{id}/completar`: Conserje marca como lista (acepta URL de foto opcional).
  * `POST /api/evidencias/subir`: Ingesta binaria segura (`application/octet-stream` o `multipart/form-data`, $\le 2\text{ MB}$ y verificación de *Magic Bytes* + Pillow) que encola conversión AVIF/S3 en KeyDB (`202 ENCOLADO`; conectado en `PaymentWizardView`, `IncidentsFeedView` y `SpokespersonGalleryView`, Hito 22). *[Header: Idempotency-Key]*
  * `POST /api/voceros/fotos`: Sube AVIFs (Límite: 30 con bloqueo pesimista `.with_for_update()`). *[Header: Idempotency-Key]*
  * `GET /api/voceros/galeria`: Lista fotos del mes en curso organizadas por área.

---

## 8. Bitácora del Secretario

### 🖥️ Vista: Actas y Reuniones
* **Ruta Vue:** `/secretaria/bitacora`
* **Diseño GUI:**
  * **Editor:** Formulario simple (Fecha, Hora, Ubicación) y caja de texto con formato básico (negritas, viñetas).
  * **Vista Pública:** Línea de tiempo (Timeline) vertical con el resumen histórico de actas para lectura de todos los propietarios.
* **Endpoints FastAPI:**
  * `POST /api/bitacora/acta`: Guarda una nueva acta o minuta.
  * `GET /api/bitacora/historial`: Devuelve la lista ordenada por fecha.
  * `POST /api/comunicados`: Publica comunicados oficiales en la cartelera vecinal con validación segura de enlace (`ruta interna` o `https://`).
  * `GET /api/comunicados/recientes`: Lista comunicados activos para la cartelera en `/dashboard`.

---

---

## 9. Motor de Alícuotas, Facturación Mensual LPH y Solvencia Digital (Fase 4 — Spec 07 — Implementado en Hito 10)

### 🖥️ Vistas: Facturación Trimodal y Certificado de Solvencia
* **Rutas Vue:** `/tesoreria/facturacion`, `/finanzas/solvencia`
* **Diseño GUI:**
  * **Facturación Mensual (`BillingGeneratorView.vue`):** Selector de modalidad (`ALICUOTA` mediante el *Método del Resto Mayor / Hamilton*, `CUOTA_FIJA` mensual con conciliación automática de superávit/déficit hacia `FondoCondominio`, y `PARTES_IGUALES`), gestión de fondos patrimoniales, aplicación automática de saldo a favor (`credito_disponible_usd`) y modal de desglose de recibos (`ReceiptBreakdownModal.vue`).
  * **Solvencia Digital (`SolvencyCertificateView.vue`):** Emisión de Certificado Digital de Solvencia para unidades con deuda cero ($0.00\text{ USD}$) con sello QR firmado (`HMAC-SHA256`) y verificador público de autenticidad.
* **Endpoints FastAPI:**
  * `PUT /api/estructura/unidades/{id}/alicuota`: Actualiza el porcentaje de participación (`alicuota`) y la cuota fija diferenciada (`cuota_fija_usd`) de la unidad. *[Header: Idempotency-Key]*
  * `POST /api/finanzas/fondos` y `GET /api/finanzas/fondos`: Gestión de fondos patrimoniales y de reserva. *[Header: Idempotency-Key]*
  * `POST /api/finanzas/facturar-periodo`: Emite o fusiona vía `UPSERT` recibos mensuales únicos por `(unidad_id, periodo)` (`uq_recibo_unidad_periodo`, integrando cargos preliminares `USO_AREA_SOCIAL`/`DANOS_AREA_SOCIAL`) bajo modalidad `ALICUOTA`, `CUOTA_FIJA` o `PARTES_IGUALES`, valida `validar_suma_alicuotas`, prorratea cuotas extraordinarias y aplica saldos a favor (`credito_disponible_usd`). *[Header: Idempotency-Key]*
  * `GET /api/finanzas/recibos/{id}/desglose`: Devuelve las líneas detalladas (`ReciboItem`) del recibo.
  * `POST /api/finanzas/solvencia/{unidad_id}` y `GET /api/finanzas/solvencia/verificar/{folio}`: Emite y verifica certificados digitales de solvencia. *[Header: Idempotency-Key]*

---

## 10. Gobernanza Digital: Cartas Consulta (Art. 23 LPH) y Asambleas (Fase 4 — Spec 08 — Implementado en Hito 11)

### 🖥️ Vistas: Cartas Consulta y Votación Ponderada por Alícuota
* **Rutas Vue:** `/consultas`, `/consultas/:id`
* **Diseño GUI:**
  * **Listado (`ConsultationsListView.vue`) y Detalle (`ConsultationDetailView.vue`):** Muestra el quórum requerido ($2/3$ racional exacto $\approx 66.6667\%$ en `DOS_TERCIOS`, $> 50.0000\%$ estricto en `MAYORIA_SIMPLE` o $100.0000\%$ en `UNANIMIDAD`), barra nativa `<progress id="quorum-progress-bar">` en tiempo real por alícuota acumulada y opciones de votación.
  * **Recibo Criptográfico (`VoteReceiptModal.vue`):** Al votar, presenta modal `<dialog id="modal-vote-receipt" closedby="any">` con el hash `HMAC-SHA256` del voto, la unidad inmobiliaria y la alícuota capturada.
* **Endpoints FastAPI:**
  * `POST /api/consultas`, `GET /api/consultas`, `GET /api/consultas/{id}`: Creación y consulta de Cartas Consulta y Asambleas. *[Header: Idempotency-Key]*
  * `POST /api/consultas/{id}/votar`: Registra voto único por unidad ponderado por su alícuota (exclusivo `PROPIETARIO` o representante con `puede_votar_asamblea = true`). *[Header: Idempotency-Key]*
  * `POST /api/consultas/{id}/cerrar`: Cierra el escrutinio y genera automáticamente el acuerdo inmutable en `BitacoraActa`. *[Header: Idempotency-Key]*

---

## 11. Control de Acceso QR, Paquetería en Garita y Reserva de Áreas Sociales (Fase 4 — Spec 09 — Hitos 12 y 13 Implementados)

### 🖥️ Vistas: Pases de Visita QR, Escáner de Garita, Paquetería y Reservas
* **Rutas Vue:** `/accesos/pases` (`VisitorPassesView.vue`), `/operaciones/garita-qr` (`GatehouseScannerView.vue`), `/operaciones/paqueteria` (`ParcelsTrackerView.vue`), `/reservas/areas` (`AmenitiesReservationView.vue`)
* **Endpoints FastAPI:**
  * `POST /api/accesos/pases`, `GET /api/accesos/pases/mios`, `DELETE /api/accesos/pases/{pase_id}`: Emisión, listado filtrado exclusivamente por el propietario/residente titular y revocación de pases QR firmados con subclave `HKDF-SHA256`. *[Header: Idempotency-Key]*
  * `POST /api/accesos/verificar-qr`: Verifica firma, vigencia y unicidad (`jti` anti-replay en KeyDB Multi-Hilo). *[Header: Idempotency-Key]*
  * `POST /api/paqueteria/registrar`, `GET /api/paqueteria`, `PUT /api/paqueteria/{paquete_id}/entregar`: Cadena de custodia de encomiendas en conserjería con registro restringido a `CONSERJE` y `PRESIDENTE`, listado global acotado a `CONSERJE` y `PRESIDENTE` (y vista filtrada a sus unidades vigentes para el resto de roles activos) y confirmación de entrega por conserjería o residente destinatario. *[Header: Idempotency-Key]*
  * `POST /api/reservas/areas`, `GET /api/reservas/areas`, `GET /api/reservas`, `POST /api/reservas/solicitar`, `PUT /api/reservas/{reserva_id}/cancelar`, `PUT /api/reservas/{reserva_id}/inspeccionar`: Reserva de amenidades con listado global restringido a `CONSERJE`, `PRESIDENTE`, `VICEPRESIDENTE`, `SECRETARIO` y `TESORERO` (y acotado a unidades propias para residentes/voceros), índice único parcial excluyendo `CANCELADA`, bloqueo a unidades insolventes, cargo automático `USO_AREA_SOCIAL` si `costo_uso_usd > 0`, reverso o crédito al cancelar, inspección post-evento (`CONSERJE`, `PRESIDENTE`, `TESORERO`) y cargo contable `DANOS_AREA_SOCIAL` si concluye `FINALIZADA_CON_DANOS`. *[Header: Idempotency-Key]*

---

## 12. Observabilidad, Salud del Sistema y Vista Comodín 404

### 🖥️ Vista Comodín 404 y Shell Autenticado (`AppShellLayout`)
* **Rutas Vue:** Todas las rutas autenticadas viven bajo el padre `<AppShellLayout>` (`/` con redirección vacía hacia `/dashboard`), más la ruta comodín pública `/:pathMatch(.*)*` (`NotFoundView.vue`, `#not-found-card`).
* **Endpoints FastAPI de Sistema:**
  * `GET /health`: Sonda liveness pública (`{"status": "healthy"}`), utilizada por el `HEALTHCHECK` del contenedor `api` y por Nginx (`/health`).
  * `GET /metrics`: Métricas RED de `prometheus_fastapi_instrumentator` (`text/plain`, excluido de `/openapi.json`); protegido en producción mediante `METRICS_AUTH_TOKEN` (`X-Metrics-Token` o `Authorization: Bearer`) y en desarrollo por `TRUSTED_PROXY_IPS`.

---

## 13. Inventario Verificado (`23` Rutas Vue 3 + `61` Endpoints FastAPI)

### 13.1. Catálogo Completo de `23` Rutas Nombradas Vue 3 (`frontend/src/router/index.ts`)

| # | Ruta (`path`) | Nombre (`name`) | Alias | Acceso / Roles (`meta`) |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `/login` | `login` | — | Pública (`public: true`) |
| 2 | `/register` | `register` | — | Pública (`public: true`) |
| 3 | `/espera-aprobacion` | `espera-aprobacion` | — | Solo Fantasma (`ghostOnly: true`) |
| 4 | `/dashboard` | `dashboard` | `/inicio` | Activo (cualquier rol activo; `/` redirige aquí) |
| 5 | `/finanzas/reportar-pago` | `reportar-pago` | `/pagar` | Activo |
| 6 | `/tesoreria/pagos` | `tesoreria-pagos` | `/admin/pagos-revision` | `TESORERO`, `PRESIDENTE` |
| 7 | `/tesoreria/cierre` | `tesoreria-cierre` | `/admin/finanzas` | `TESORERO`, `PRESIDENTE` |
| 8 | `/tesoreria/facturacion` | `tesoreria-facturacion` | — | `TESORERO`, `PRESIDENTE` |
| 9 | `/finanzas/solvencia` | `finanzas-solvencia` | — | Activo |
| 10 | `/incidencias` | `incidencias` | — | Activo |
| 11 | `/operaciones/tareas` | `operaciones-tareas` | `/conserje/tareas` | Activo |
| 12 | `/voceros/galeria` | `voceros-galeria` | — | Activo |
| 13 | `/secretaria/bitacora` | `secretaria-bitacora` | — | Activo |
| 14 | `/consultas` | `consultas-list` | — | Activo |
| 15 | `/consultas/:id` | `consulta-detail` | — | Activo |
| 16 | `/accesos/pases` | `accesos-pases` | — | Activo |
| 17 | `/operaciones/garita-qr` | `operaciones-garita-qr` | — | `CONSERJE`, `PRESIDENTE`, `VOCERO` |
| 18 | `/operaciones/paqueteria` | `operaciones-paqueteria` | — | Activo |
| 19 | `/reservas/areas` | `reservas-areas` | — | Activo |
| 20 | `/admin/estructura` | `admin-estructura` | — | `PRESIDENTE`, `VICEPRESIDENTE` |
| 21 | `/admin/usuarios` | `admin-usuarios` | `/admin/usuarios-pendientes` | `PRESIDENTE`, `VICEPRESIDENTE` |
| 22 | `/admin/junta` | `admin-junta` | — | `PRESIDENTE` |
| 23 | `/:pathMatch(.*)*` | `not-found` | — | Comodín 404 (`publicNotFound: true`) |

### 13.2. Catálogo Completo de `61` Endpoints FastAPI (`backend/src/main.py` + `routers/*.py`)

| # | Método | Ruta | Origen | RBAC / Idempotencia |
| :---: | :---: | :--- | :--- | :--- |
| 1 | `GET` | `/health` | `main.py` | Público (liveness) |
| 2 | `GET` | `/metrics` | `main.py` | `METRICS_AUTH_TOKEN` / `TRUSTED_PROXY_IPS` (fuera de OpenAPI) |
| 3 | `POST` | `/api/auth/register` | `auth.py` | Público + `Idempotency-Key` anónima |
| 4 | `POST` | `/api/auth/login` | `auth.py` | Público + lockout Lua (`5` IP / `10` cuenta en `15m`) |
| 5 | `POST` | `/api/auth/logout` | `auth.py` | Sesión activa / cookie; revoca `sid`/`jti` |
| 6 | `POST` | `/api/auth/refresh` | `auth.py` | Cookie `refresh_token` (`5s` grace period) |
| 7 | `GET` | `/api/auth/me` | `auth.py` | Autenticado (incluye `FANTASMA`) |
| 8 | `GET` | `/api/estructura/unidades` | `administracion.py` | Público/Autenticado (DTO dual Junta vs Público) |
| 9 | `POST` | `/api/estructura/generar` | `administracion.py` | `PRESIDENTE`, `VICEPRESIDENTE` + `Idempotency-Key` |
| 10 | `GET` | `/api/usuarios/pendientes` | `administracion.py` | `PRESIDENTE`, `VICEPRESIDENTE` |
| 11 | `PUT` | `/api/usuarios/{usuario_id}/asignar` | `administracion.py` | `PRESIDENTE`, `VICEPRESIDENTE` + `Idempotency-Key` |
| 12 | `PUT` | `/api/junta/cargos` | `administracion.py` | `PRESIDENTE` + `Idempotency-Key` |
| 13 | `PUT` | `/api/estructura/unidades/{unidad_id}/alicuota` | `administracion.py` | `PRESIDENTE`, `VICEPRESIDENTE`, `TESORERO` + `Idempotency-Key` |
| 14 | `POST` | `/api/pagos/reportar` | `pagos.py` | Activo (titular o `TESORERO`/`PRESIDENTE`) + `Idempotency-Key` |
| 15 | `GET` | `/api/pagos/revision` | `pagos.py` | `TESORERO`, `PRESIDENTE` |
| 16 | `PUT` | `/api/pagos/{pago_id}/aprobar` | `pagos.py` | `TESORERO`, `PRESIDENTE` + `Idempotency-Key` |
| 17 | `PUT` | `/api/pagos/{pago_id}/rechazar` | `pagos.py` | `TESORERO`, `PRESIDENTE` + `Idempotency-Key` |
| 18 | `POST` | `/api/finanzas/tasa` | `finanzas.py` | `TESORERO`, `PRESIDENTE` + `Idempotency-Key` |
| 19 | `GET` | `/api/finanzas/tasa` | `finanzas.py` | Activo |
| 20 | `POST` | `/api/finanzas/egresos` | `finanzas.py` | `TESORERO`, `PRESIDENTE` + `Idempotency-Key` |
| 21 | `GET` | `/api/finanzas/resumen` | `finanzas.py` | Activo (Junta global; residente propio; `CONSERJE` `[]`) |
| 22 | `POST` | `/api/finanzas/cierre-mensual` | `finanzas.py` | `TESORERO`, `PRESIDENTE` + `Idempotency-Key` |
| 23 | `POST` | `/api/finanzas/fondos` | `finanzas.py` | `TESORERO`, `PRESIDENTE` + `Idempotency-Key` |
| 24 | `GET` | `/api/finanzas/fondos` | `finanzas.py` | Activo |
| 25 | `POST` | `/api/finanzas/facturar-periodo` | `finanzas.py` | `TESORERO`, `PRESIDENTE` + `Idempotency-Key` |
| 26 | `GET` | `/api/finanzas/recibos/{recibo_id}/desglose` | `finanzas.py` | Activo (titular o Junta) |
| 27 | `POST` | `/api/finanzas/solvencia/{unidad_id}` | `finanzas.py` | Activo (titular o Junta) + `Idempotency-Key` |
| 28 | `GET` | `/api/finanzas/solvencia/verificar/{folio}` | `finanzas.py` | Público (`?sig=...`) |
| 29 | `GET` | `/api/incidencias/abiertas` | `incidencias.py` | Activo |
| 30 | `POST` | `/api/incidencias/crear` | `incidencias.py` | Activo + `Idempotency-Key` |
| 31 | `POST` | `/api/incidencias/{incidencia_id}/adherir` | `incidencias.py` | Activo + `Idempotency-Key` |
| 32 | `POST` | `/api/tareas/plantillas` | `operaciones.py` | `PRESIDENTE`, `VICEPRESIDENTE` + `Idempotency-Key` |
| 33 | `POST` | `/api/tareas/diarias` | `operaciones.py` | `PRESIDENTE`, `VICEPRESIDENTE` + `Idempotency-Key` |
| 34 | `POST` | `/api/tareas/generar-diarias` | `operaciones.py` | `PRESIDENTE`, `VICEPRESIDENTE` |
| 35 | `GET` | `/api/tareas/diarias` | `operaciones.py` | Activo |
| 36 | `PUT` | `/api/tareas/{tarea_id}/completar` | `operaciones.py` | `CONSERJE`, `PRESIDENTE`, `VICEPRESIDENTE` + `Idempotency-Key` |
| 37 | `POST` | `/api/voceros/fotos` | `operaciones.py` | `VOCERO`, `PRESIDENTE` + `Idempotency-Key` |
| 38 | `GET` | `/api/voceros/galeria` | `operaciones.py` | Activo |
| 39 | `POST` | `/api/bitacora/acta` | `operaciones.py` | `SECRETARIO`, `PRESIDENTE` + `Idempotency-Key` |
| 40 | `GET` | `/api/bitacora/historial` | `operaciones.py` | Activo |
| 41 | `POST` | `/api/comunicados` | `operaciones.py` | `SECRETARIO`, `PRESIDENTE` + `Idempotency-Key` |
| 42 | `GET` | `/api/comunicados/recientes` | `operaciones.py` | Activo |
| 43 | `POST` | `/api/evidencias/subir` | `operaciones.py` | Activo + `Idempotency-Key` (`hash_body=False`) |
| 44 | `POST` | `/api/consultas` | `consultas.py` | `PRESIDENTE`, `SECRETARIO` + `Idempotency-Key` |
| 45 | `GET` | `/api/consultas` | `consultas.py` | Activo |
| 46 | `GET` | `/api/consultas/{consulta_id}` | `consultas.py` | Activo |
| 47 | `POST` | `/api/consultas/{consulta_id}/votar` | `consultas.py` | Activo (`PROPIETARIO` / representante habilitado) + `Idempotency-Key` |
| 48 | `POST` | `/api/consultas/{consulta_id}/cerrar` | `consultas.py` | `PRESIDENTE`, `SECRETARIO` + `Idempotency-Key` |
| 49 | `POST` | `/api/accesos/pases` | `accesos.py` | Activo (titular o Junta) + `Idempotency-Key` |
| 50 | `GET` | `/api/accesos/pases/mios` | `accesos.py` | Activo (acotado al usuario/unidades propias) |
| 51 | `DELETE` | `/api/accesos/pases/{pase_id}` | `accesos.py` | Activo (creador o `PRESIDENTE`) |
| 52 | `POST` | `/api/accesos/verificar-qr` | `accesos.py` | `CONSERJE`, `PRESIDENTE`, `VOCERO` + `Idempotency-Key` |
| 53 | `POST` | `/api/paqueteria/registrar` | `accesos.py` | `CONSERJE`, `PRESIDENTE` + `Idempotency-Key` |
| 54 | `GET` | `/api/paqueteria` | `accesos.py` | Activo (`CONSERJE`/`PRESIDENTE` global; residentes propio) |
| 55 | `PUT` | `/api/paqueteria/{paquete_id}/entregar` | `accesos.py` | Activo (`CONSERJE`/`PRESIDENTE` o unidad destinataria) + `Idempotency-Key` |
| 56 | `POST` | `/api/reservas/areas` | `reservas.py` | `PRESIDENTE`, `TESORERO` + `Idempotency-Key` |
| 57 | `GET` | `/api/reservas/areas` | `reservas.py` | Activo |
| 58 | `GET` | `/api/reservas` | `reservas.py` | Activo (`CONSERJE`/`PRESIDENTE`/`VICEPRESIDENTE`/`SECRETARIO`/`TESORERO` global; resto propio) |
| 59 | `POST` | `/api/reservas/solicitar` | `reservas.py` | Activo (titular solvente `$0.00`) + `Idempotency-Key` |
| 60 | `PUT` | `/api/reservas/{reserva_id}/cancelar` | `reservas.py` | Activo (titular o Junta) + `Idempotency-Key` |
| 61 | `PUT` | `/api/reservas/{reserva_id}/inspeccionar` | `reservas.py` | `CONSERJE`, `PRESIDENTE`, `TESORERO` + `Idempotency-Key` |
