# 🛠️ Especificación 04: Dominio de Operaciones, Incidencias y Tareas Asíncronas (Hito 4 y Hito 7)

**Estado:** Completado y Certificado en Backend (Hito 4 ✅) y GUI (Hito 7 ✅)

---

## 1. Embudo de Incidencias con Adhesión ("Me Sumo")

### 1.1. Propósito UX y Modelo de Datos
Evitar que 30 vecinos creen 30 tickets duplicados por la misma avería (ej. ascensor detenido o filtración en pasillo).
- **Tabla `incidencias`:**
  - `id`: `Integer` PK
  - `usuario_creador_id`: `ForeignKey("usuarios.id")`
  - `area`: `String` (ej. `"Ascensor Torre A"`, `"Piscina"`, `"Portón Principal"`)
  - `descripcion`: `String`
  - `url_foto`: `String | None` (AVIF en MinIO)
  - `estado`: `String` (`ABIERTO`, `EN_PROCESO`, `CERRADO`)
  - `adhesiones_count`: `Integer` (inicia en `1`)
  - `creado_en`: `DateTime(timezone=True)`
- **Tabla `incidencias_adhesiones`:**
  - `id`: `Integer` PK
  - `incidencia_id`: `ForeignKey("incidencias.id")`
  - `usuario_id`: `ForeignKey("usuarios.id")`
  - Restricción única `(incidencia_id, usuario_id)` para garantizar que un usuario solo pueda sumarse una vez por incidencia (`HTTP 409 Conflict` si intenta sumarse de nuevo).

### 1.2. Flujo de Interacción
1. `GET /api/incidencias/abiertas`: Lista las incidencias en estado `ABIERTO` o `EN_PROCESO` de los últimos 7 días, ordenadas por mayor número de `adhesiones_count` (prioridad comunitaria).
2. `POST /api/incidencias/{id}/adherir`: Registra la adhesión del vecino actual e incrementa `adhesiones_count`.
3. `POST /api/incidencias/crear` (requiere `Idempotency-Key`): Crea una nueva incidencia y dispara tarea asíncrona de notificación por correo al Presidente y Vicepresidente.

---

## 2. Gestión de Tareas de Conserjería (Plantillas y Checklist Diario)

- **Tabla `plantillas_tareas`:**
  - `id`, `titulo`, `area`, `frecuencia` (`UNICA`, `DIARIA`, `SEMANAL`, `MENSUAL`), `activa` (`Boolean`).
- **Tabla `tareas_diarias`:**
  - `id`, `plantilla_id` (nullable), `incidencia_id` (nullable, cuando una tarea nace de una incidencia), `titulo`, `fecha` (`Date`), `completada` (`Boolean`), `url_evidencia` (`String | None`), `completada_en` (`DateTime | None`).
- **Regla de Cierre Automático:** Cuando el conserje ejecuta `PUT /api/tareas/{id}/completar` sobre una tarea vinculada a una `incidencia_id`, el estado de la incidencia pasa automáticamente a `CERRADO`.

---

## 3. Galería de Voceros (Cuota Estricta de 30 Fotos/Mes)

- **Tabla `fotos_voceros`:**
  - `id`, `usuario_id`, `periodo` (`YYYY-MM`), `area`, `comentario`, `url_foto` (AVIF), `creado_en`.
- **Invariante de Cuota Mensual:**
  - Antes de aceptar `POST /api/voceros/fotos`, el backend cuenta las fotos subidas en el `periodo` actual (`YYYY-MM`).
  - Si el conteo es `>= 30`, rechaza la petición con `HTTP 429 Too Many Requests` (o `409 Conflict`: `"Límite mensual de 30 fotografías alcanzado"`).
  - La GUI en `/voceros/galeria` muestra el indicador reactivo `"X / 30 fotos este mes"` y deshabilita el botón de subida al llegar a `30/30`.

---

## 4. Bitácora del Secretario y Cartelera de Comunicados

- **Tabla `bitacora_actas`:**
  - `id`, `fecha` (`Date`), `hora` (`String`), `ubicacion` (`String`), `contenido` (`String`), `autor_id` (`ForeignKey("usuarios.id")`), `creado_en`.
  - Endpoints: `POST /api/bitacora/acta` (rol `SECRETARIO` o `PRESIDENTE`) y `GET /api/bitacora/historial` (lectura para residentes activos).
- **Tabla `comunicados`:**
  - `id`, `titulo`, `contenido`, `enlace_externo` (`String | None`, validado con `validate_safe_outgoing_url`), `activo` (`Boolean`), `creado_en`.
  - Endpoints: `GET /api/comunicados/recientes` (alimenta el carrusel del Dashboard).
