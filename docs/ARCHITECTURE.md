# Sistema de Administración de Condominios - Arquitectura y Especificaciones
**Fecha de Documento:** Octubre 2026
**Licencia:** MIT

## 1. Stack Tecnológico y Arquitectura
- **Estructura del Proyecto:** Monorepo (Frontend, Backend, Worker, Docker, Docs, QA x11).
- **Backend:** FastAPI (Python). Oculto dentro de la red de Docker, sin exposición directa.
- **Frontend:** Vue 3, diseño Mobile-First.
- **Base de Datos:** PostgreSQL. Migraciones automatizadas vía Alembic en el entrypoint del contenedor.
- **Proxy / Gateway:** Nginx Proxy Manager (NPM).
- **Almacenamiento de Archivos:** MinIO (S3 Compatible) desplegado en Docker. Uso exclusivo de URLs firmadas temporales; las imágenes no transitan por FastAPI.
- **Procesamiento de Imágenes:** Worker Asíncrono (ej. Celery + Redis). Todas las imágenes subidas (comprobantes, fotos de áreas, logos) se convierten obligatoriamente a formato **AVIF**.
- **Control de Estado en Red:** Redis (usado para colas del Worker y para Idempotencia).

## 2. Seguridad y Autenticación
- **Tokens:** JWT almacenados y transmitidos exclusivamente mediante Cookies `HttpOnly` y `Secure`.
- **Registro de Usuarios:** Sistema de "Usuario Fantasma". El registro es abierto, pero el usuario no tiene acceso a ningún panel del sistema hasta que un Administrador/Presidente aprueba la cuenta y le asigna una Unidad (Casa/Apartamento) en el sistema.
- **Notificación de Registro:** El Worker asíncrono envía un email al Presidente y Administrador cuando hay un nuevo registro.
- **Idempotencia:** Implementada en el Frontend (generación de UUID) y Backend (validación contra Redis) para prevenir duplicidad de registros (ej. evitar reportar el mismo pago dos veces por problemas de red).

## 3. Modelo de Entidades (Core)
- **Estructura Polimórfica:** Soporta edificios (Pisos -> Apartamentos) y Urbanizaciones (Calles -> Casas). Permite condominios mixtos.
- **Historial de Ocupación:** Los inquilinos/propietarios no se sobrescriben. Se mantiene un histórico (`Contratos_Ocupacion`) para saber quién ocupaba una unidad en una fecha determinada.
- **Propiedad Múltiple:** Un usuario puede poseer/ocupar múltiples unidades.

## 4. Roles y Permisos (RBAC)
*Condición estricta: Solo los propietarios registrados y con unidades asignadas pueden ser miembros de la Junta de Condominio.*

- **Presidente / Vicepresidente:** Gestión de usuarios (aprobación/asignación). Asignación de tareas al conserje. Gestión de reportes de incidencias. *No manipulan ingresos, egresos ni cobranza.*
- **Tesorero:** Control absoluto sobre Finanzas (ingresos, egresos, cierre de mes).
- **Secretario:** Registro de bitácoras, minutas y comunicados.
- **Voceros:** Supervisión de áreas comunes. Pueden subir reportes fotográficos (límite: 30 fotos por mes, limpieza programada anual).
- **Conserje:** Visualización y check-off de tareas asignadas.
- **Propietarios/Inquilinos:** Visualización de deuda, reporte de pagos, visualización de dashboard financiero público (Gastos vs Ingresos), creación y adhesión a reportes de incidencias.

## 5. Finanzas y Cobranzas
- **Multimoneda Base:** Contabilidad referenciada en USD. Se registra diariamente la tasa de cambio USD/VES.
- **Cobros:** Configurable por Cuota Fija o Alícuota (Porcentaje de participación).
- **Reporte de Pagos:** Permite pagos parciales y en divisas distintas. *Regla crítica: El sistema guarda la Tasa de Cambio del día exacto en que se realiza el reporte de pago.*
- **Egresos:** El tesorero registra gastos por categoría y sube el comprobante/factura en AVIF.
- **Cierre de Mes (El Candado Contable):**
  - **Día 1:** El cronjob genera un reporte PDF *preliminar* (FastAPI) visible solo para el Tesorero.
  - **Cierre Manual:** El Tesorero aprueba y pulsa "Cerrar Mes". El mes queda bloqueado (Read-Only absoluto).
  - **Publicación:** El PDF definitivo se publica. Del día 1 al 10, se muestra en el inicio de la app mediante un Banner destacado.
- **Pista de Auditoría (Audit Trail):** Tabla inmutable que registra cualquier cambio de estado en un pago/recibo (Quién, Cuándo, Estado Viejo, Estado Nuevo, Motivo obligatorio).

## 6. Operaciones y Mantenimiento
- **Gestión de Tareas:** El Presidente define Plantillas de tareas recurrentes (Diarias/Semanales). Un Cronjob (Worker) genera las tareas asignadas reales a medianoche para no saturar la base de datos a futuro.
- **Visibilidad de Tareas:** Los propietarios tienen acceso de solo lectura al estado de las tareas del conserje para verificar su cumplimiento. El conserje puede subir fotos como evidencia de cumplimiento.
- **Embudo de Incidencias (UX/UX):**
  - Al reportar un daño, el usuario debe ver primero las incidencias recientes.
  - **Adhesión ("Me sumo"):** Si el daño ya está reportado, el usuario pulsa "Me sumo", lo cual aumenta la prioridad del reporte existente.
  - **Notificación:** Al crearse un reporte nuevo, el Worker envía un correo al Presidente y Vicepresidente.

## 7. Despliegue y Distribución (DevOps)
- **CI/CD:** Github Actions integrado con el estándar de pruebas *QA Blueprint x11*.
- **Publicación:** Compilación automática y empuje (push) a Docker Hub de imágenes bajo licencia MIT.
- **Instalación de Usuario Final:** Despliegue mediante un archivo `docker-compose.yml` preconfigurado.

## 8. Flujos Críticos y Máquinas de Estado

### 8.1. Registro y Asignación ("Flujo Fantasma")
1. **Frontend:** Usuario llena datos. Genera `Idempotency-Key` y envía petición.
2. **Backend:** Valida UUID en Redis. Crea usuario con `Es_Activo = FALSE` (sin unidad asignada).
3. **Worker:** Envía notificación por correo a Presidente y Administrador.
4. **Presidente:** Entra al panel, identifica al usuario, le asigna Unidad y Rol, y lo activa.
5. **Backend:** Crea registro en `Contratos_Ocupacion` (historial) y actualiza el estado del usuario a `Es_Activo = TRUE`.

### 8.2. Reporte y Aprobación de Pagos
1. **Frontend:** Propietario reporta pago y sube comprobante. Vue3 genera `Idempotency-Key` y bloquea el botón visualmente.
2. **Backend:** Valida UUID en Redis (previene doble clic).
3. **Worker:** Convierte imagen a AVIF y sube a MinIO.
4. **Backend:** Crea registro en `Pagos_Reportados` en estado `EN_REVISION`. El recibo pasa a estado visual `PAGO_EN_REVISION`.
5. **Tesorero:** Revisa el reporte.
   - **Camino A (Aprobar):** Tesorero aprueba. Backend suma pagos aprobados. Si cubre el total, Recibo pasa a `PAGADO`. Si es menor, pasa a `PAGADO_PARCIAL`. Se crea registro en `Auditoria_Recibos`.
   - **Camino B (Rechazar):** Tesorero rechaza e introduce Motivo obligatorio. Pago pasa a `RECHAZADO`. Recibo vuelve a `PENDIENTE`. Frontend notifica al propietario.

### 8.3. Embudo de Incidencias (UX y Adhesiones)
1. **Frontend:** Propietario inicia reporte. Se muestran incidencias `ABIERTAS` de los últimos 7 días.
2. **Bifurcación:**
   - **Daño Existente:** Propietario pulsa "Me sumo". Backend registra adherencia, aumentando prioridad.
   - **Nuevo Daño:** Propietario crea reporte (Worker convierte imagen a AVIF). Backend guarda en estado `ABIERTO`. Worker notifica por correo a Presidente y VP.
3. **Presidente/VP:** Asigna tarea vinculada al conserje. Estado cambia a `EN_PROCESO`.
4. **Conserje:** Marca tarea como Completada. Reporte pasa automáticamente a `CERRADO`.

### 8.4. Cierre Financiero de Mes (Candado Contable)
1. **Cronjob (Día 1):** Backend detecta nuevo mes. Genera PDF preliminar en `Reportes_Mensuales` (estado `PRELIMINAR`, visible solo para el Tesorero).
2. **Día 1-3:** Tesorero revisa, cuadra banco, ingresa egresos faltantes. El PDF preliminar se regenera silenciosamente con cada cambio.
3. **Cierre (Acción Inmutable):** Tesorero pulsa "Cerrar Mes".
4. **Backend:** Estado del reporte pasa a `CERRADO`. Todos los recibos, pagos y gastos del mes se bloquean (`Read-Only`).
5. **Frontend:** Muestra Banner destacado a todos los usuarios desde el día 1 hasta el 10: "📊 *Cierre Financiero Disponible*".
