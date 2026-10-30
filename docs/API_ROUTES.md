# Mapa de Vistas (GUI) y Rutas API
**Proyecto:** Condominio App
**Fase de Diseño:** 1.0

Este documento integra la navegación del Frontend (Vue 3), el diseño de la Interfaz Gráfica (UI/UX) y los Endpoints del Backend (FastAPI) requeridos para cada pantalla.

*Nota de Diseño General:* El layout principal en móviles utilizará una **Bottom Navigation Bar** para acceso rápido. En escritorio, mutará a un **Sidebar** lateral.

---

## 1. Módulo de Autenticación y Registro

### 🖥️ Vista: Pantalla de Inicio de Sesión y Registro
* **Ruta Vue:** `/login` | `/register`
* **Diseño GUI (Registro):** 
  * Formulario público: Nombre, Cédula, Correo, Teléfono.
  * Selectores: Buscador de Unidad (Ej. "A-42") y un selector de estatus inicial ("Soy Propietario" / "Soy Inquilino").
  * **Pantalla de Bloqueo:** Al completar el registro, el usuario es redirigido a `/espera-aprobacion` con un mensaje fijo: *"Registro completado. Esperando validación de la Junta"*.
* **Endpoints FastAPI:**
  * `POST /api/auth/login`: Devuelve JWT en Cookie `HttpOnly`.
  * `POST /api/auth/register`: Crea usuario "Fantasma". *[Header: Idempotency-Key]* -> Dispara notificación por correo.
  * `GET /api/auth/me`: Verifica rol y estado de activación del usuario.

---

## 2. Dashboard Financiero (Inicio)

### 🖥️ Vista: Resumen y Cartelera
* **Ruta Vue:** `/` o `/dashboard`
* **Diseño GUI:**
  * **Cabecera:** Logo, saludo al usuario y **Tasa de Cambio del Día**.
  * **Banner Condicional:** Si el día actual es entre el 1 y el 10, muestra una tarjeta destacada: *"📊 Cierre Financiero disponible"*.
  * **Carrusel de Comunicados:** Deslizable horizontalmente con los anuncios de la junta (soporta enlaces a WhatsApp/Webs).
  * **Cuerpo Central (Tabs):**
    * *Tab 1 (Estado de Cobranza):* Lista tipo semáforo (Verde: solventes, Rojo: deudores). La unidad del usuario aparece de primera.
    * *Tab 2 (Relación de Gastos):* Gráfica de dona dividida por categorías y lista de facturas.
  * **Botón Flotante (FAB):** Botón principal para `"Pagar / Reportar"`.
* **Endpoints FastAPI:**
  * `GET /api/finanzas/resumen`: Devuelve la deuda global, gráfica de gastos y estado de cobranza del mes.
  * `GET /api/comunicados/recientes`: Lista los comunicados activos de la cartelera.

---

## 3. Flujo de Reporte de Pagos

### 🖥️ Vista: Wizard de Pago
* **Ruta Vue:** `/finanzas/reportar-pago`
* **Diseño GUI (Proceso Paso a Paso):**
  * **Paso 1:** Teclado numérico grande. Selector USD/VES (muestra conversión automática en texto pequeño según la tasa del día).
  * **Paso 2:** Selección de Método (Zelle, Efectivo, Pago Móvil, Transferencia). *Regla UI: Si es Zelle, Pago Móvil o Transferencia, aparece un campo de texto obligatorio para el Número de Referencia.*
  * **Paso 3:** Subida de captura de pantalla (Cámara/Galería).
  * **Botón Final:** "Enviar Reporte". Al pulsar, muestra un *spinner* y se bloquea visualmente para evitar doble envío.
* **Endpoints FastAPI:**
  * `POST /api/pagos/reportar`: Registra el pago y la tasa del día exacto. **Requiere campo `numero_referencia` en el payload si el método no es efectivo.** *[Header: Idempotency-Key]* -> Worker convierte imagen a AVIF.

---

## 4. Panel de Tesorería (Aprobaciones y Cierre)

### 🖥️ Vistas: Pagos Pendientes y Cierre de Mes
* **Ruta Vue:** `/tesoreria/pagos`, `/tesoreria/cierre`
* **Diseño GUI:**
  * **Pagos Pendientes:** Lista de Tarjetas (Cards) expandibles (Acordeón). Al expandir, muestra mitad foto (AVIF), mitad cálculos. Dos botones grandes: `[ APROBAR ]` y `[ RECHAZAR ]`.
  * *Flujo de Rechazo:* Si pulsa rechazar, se oculta la foto y aparece un Modal exigiendo escribir el "Motivo" para habilitar el botón de confirmación.
  * **Cierre de Mes:** Muestra una vista previa del PDF preliminar y un botón crítico de `"Cerrar Mes"`.
* **Endpoints FastAPI:**
  * `GET /api/pagos/revision`: Lista de pagos pendientes.
  * `PUT /api/pagos/{id}/aprobar`: Cambia estado y audita.
  * `PUT /api/pagos/{id}/rechazar`: Requiere `motivo`.
  * `POST /api/finanzas/cierre-mensual`: Acción inmutable. Bloquea registros del mes y oficializa el PDF.

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
* **Ruta Vue:** `/admin/estructura`, `/admin/usuarios`, `/admin/junta`
* **Diseño GUI:**
  * **Constructor:** Formulario para añadir Edificio o Calle. Configuración de identificador (Ej. `A-42` o `42`). Autogenera las unidades. Campo de texto extra para número de **Puesto de Estacionamiento** (en edificios).
  * **Bandeja de Usuarios:** Tarjetas de registros nuevos. Ficha con toggle para elegir `[ Ocupado Propietario / Inquilino / Vacío ]` y quién es el responsable de pagar el condominio.
  * **Composición de Junta:** Tabla de cargos (Presidente, Tesorero, Vocero, etc.) con interruptor de activación y buscador para asignar propietarios.
* **Endpoints FastAPI:**
  * `POST /api/estructura/generar`: Crea sectores y unidades con su identificador.
  * `GET /api/usuarios/pendientes`: Lista "Fantasmas".
  * `PUT /api/usuarios/{id}/asignar`: Asigna unidad, rol y activa al usuario.
  * `PUT /api/junta/cargos`: Actualiza la composición de la junta.

---

## 7. Módulo de Operaciones (Conserjería y Voceros)

### 🖥️ Vistas: Tablero de Tareas y Galerías
* **Ruta Vue:** `/operaciones/tareas`, `/voceros/galeria`
* **Diseño GUI:**
  * **Gestión Tareas (Presidente):** Creador con botones tipo pastilla para frecuencia (`Única`, `Diaria`, `Semanal`, `Mensual`).
  * **App Conserje:** Checklist diario ultra minimalista. Círculos grandes para hacer *check-off*. Permite adjuntar foto (AVIF) como evidencia de cumplimiento.
  * **Vista Tareas (Propietarios):** Panel de solo lectura para ver el avance del conserje.
  * **Galería Voceros (Modo Subida):** Botón gigante y contador *"X / 30 fotos este mes"*.
  * **Galería Voceros (Modo Público):** Cuadrícula de fotos (Grid) agrupada por áreas para que los propietarios vean el estado físico del conjunto.
* **Endpoints FastAPI:**
  * `POST /api/tareas/plantillas`: Presidente crea asignaciones periódicas.
  * `GET /api/tareas/diarias`: Checklist del día en curso.
  * `PUT /api/tareas/{id}/completar`: Conserje marca como lista (acepta URL de foto opcional).
  * `POST /api/voceros/fotos`: Sube AVIFs (Límite: 30).
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

---

## 9. Motor de Alícuotas, Facturación Mensual LPH y Solvencia Digital (Fase 4 — Spec 07)

### 🖥️ Vistas: Facturación por Alícuota y Certificado de Solvencia
* **Rutas Vue:** `/tesoreria/facturacion`, `/finanzas/solvencia`
* **Diseño GUI:**
  * **Facturación Mensual:** Resumen de egresos comunes del periodo, recargo del Fondo de Reserva Legal (10%), vista previa del prorrateo por alícuota (*Método del Resto Mayor / Hamilton*) y botón idempotente de emisión de recibos.
  * **Solvencia Digital:** Consulta de deuda cero ($0.00\text{ USD}$) y descarga/visualización de Certificado de Solvencia con QR firmado (`HMAC-SHA256`).
* **Endpoints FastAPI:**
  * `PUT /api/estructura/unidades/{id}/alicuota`: Actualiza el porcentaje de participación de la unidad. *[Header: Idempotency-Key]*
  * `POST /api/finanzas/fondos` y `GET /api/finanzas/fondos`: Gestión de fondos patrimoniales y de reserva. *[Header: Idempotency-Key]*
  * `POST /api/finanzas/facturar-periodo`: Prorratea los gastos comunes según la alícuota de cada unidad y aplica saldos a favor (`credito_disponible_usd`). *[Header: Idempotency-Key]*
  * `GET /api/finanzas/recibos/{id}/desglose`: Devuelve las líneas detalladas (`ReciboItem`) del recibo.
  * `POST /api/finanzas/solvencia/{unidad_id}` y `GET /api/finanzas/solvencia/verificar/{folio}`: Emite y verifica certificados digitales de solvencia. *[Header: Idempotency-Key]*

---

## 10. Gobernanza Digital: Cartas Consulta (Art. 23 LPH) y Asambleas (Fase 4 — Spec 08)

### 🖥️ Vistas: Cartas Consulta y Votación Ponderada por Alícuota
* **Rutas Vue:** `/consultas`, `/consultas/:id`
* **Diseño GUI:**
  * **Listado y Detalle:** Muestra el quórum requerido ($66.67\%$ en 1ra consulta o $50.01\%$ en 2da consulta), barra de progreso en tiempo real por alícuota acumulada y opciones de votación.
  * **Recibo Criptográfico:** Al votar, presenta modal (`VoteReceiptModal.vue`) con el hash `HMAC-SHA256` del voto y la alícuota capturada.
* **Endpoints FastAPI:**
  * `POST /api/consultas`, `GET /api/consultas`, `GET /api/consultas/{id}`: Creación y consulta de Cartas Consulta. *[Header: Idempotency-Key]*
  * `POST /api/consultas/{id}/votar`: Registra voto único por unidad ponderado por su alícuota (exclusivo `PROPIETARIO` o apoderado autorizado). *[Header: Idempotency-Key]*
  * `POST /api/consultas/{id}/cerrar`: Cierra el escrutinio y genera automáticamente el acta en `BitacoraActa`. *[Header: Idempotency-Key]*

---

## 11. Control de Acceso QR, Paquetería en Garita y Reserva de Áreas Sociales (Fase 4 — Spec 09)

### 🖥️ Vistas: Pases de Visita QR, Escáner de Garita, Paquetería y Reservas
* **Rutas Vue:** `/accesos/pases`, `/operaciones/garita-qr`, `/operaciones/paqueteria`, `/reservas/areas`
* **Endpoints FastAPI:**
  * `POST /api/accesos/pases`, `GET /api/accesos/pases/mios`, `DELETE /api/accesos/pases/{id}`: Emisión y revocación de pases QR firmados con `HMAC-SHA256`. *[Header: Idempotency-Key]*
  * `POST /api/accesos/verificar-qr`: Verifica firma, vigencia y unicidad (`jti` anti-replay en KeyDB Multi-Hilo). *[Header: Idempotency-Key]*
  * `POST /api/paqueteria/registrar`, `GET /api/paqueteria`, `PUT /api/paqueteria/{id}/entregar`: Cadena de custodia de encomiendas en conserjería. *[Header: Idempotency-Key]*
  * `POST /api/reservas/areas`, `GET /api/reservas/areas`, `POST /api/reservas/solicitar`, `PUT /api/reservas/{id}/inspeccionar`: Reserva de amenidades con bloqueo automático a unidades insolventes y creación automática de `TareaDiaria` de inspección post-evento. *[Header: Idempotency-Key]*
