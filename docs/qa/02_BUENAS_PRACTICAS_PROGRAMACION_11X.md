# 🛡️ Buenas Prácticas de Programación y Arquitectura (Nivel 11X)

> **PROPÓSITO:**  
> Este manual recopila las lecciones aplicadas en **Condominio App** sobre desarrollo seguro, arquitectura resiliente y diseño de interfaces operativas Mobile-First en Vue 3 + FastAPI.

---

## 1. Anti-Mock Blindness (Erradicación de la Ceguera de Mocks)

### El Problema
El aislamiento mediante mocks (`pytest-mock`, `AsyncMock`) permite obtener >95% de cobertura en milisegundos, pero no valida por sí solo que las migraciones SQL coincidan con los modelos ORM.

### La Solución 11X en Condominio App
1. **Cero Deriva de Esquema (Schema Drift):**
   - Todo cambio en `backend/src/models.py` requiere una migración versionada inmediata en `backend/alembic/versions/`.
   - El script `.agents/scripts/verify_alembic_orm_parity.py` audita automáticamente que el 100% de las tablas `__tablename__` tengan su `op.create_table()` en Alembic.
2. **Verificación en Motor Real PostgreSQL 17:**
   - La meta `make -C backend qa-parity` levanta `postgres:17-alpine` en `backend/docker-compose.qa.yml` y ejecuta `alembic upgrade head && alembic downgrade base && alembic upgrade head`.

---

## 2. Geometría Visual y Anti-JSDOM (Ceguera de Layout en la GUI)

### El Problema
Entornos como **JSDOM** simulan nodos HTML en Node.js pero **no calculan renderizado CSS, modelos de caja (Flexbox/Grid), coordenadas (`getBoundingClientRect()`) ni colisiones visuales**:
- Un pie de página fijo (`position: fixed; bottom: 0`) o la **Bottom Navigation Bar** móvil puede tapar el botón flotante (FAB `"Pagar / Reportar"`) o el botón `"Enviar Reporte"` del Wizard de Pagos.
- En Vitest con JSDOM la prueba pasa porque el nodo existe en el DOM, pero el propietario no puede hacer clic en su teléfono móvil.

### La Solución 11X para el Frontend Vue 3
1. **Ergonomía In-Flow (Anti-Sticky Footer):**
   - Prohibir pies de página flotantes fijos superpuestos.
   - El contenedor `<main>` debe usar `display: flex; flex-direction: column; min-height: 100dvh;` con espacio reservado seguro (`padding-bottom: calc(4.5rem + env(safe-area-inset-bottom))`) en vistas móviles con Bottom Navigation Bar, y el footer informativo debe usar `margin-top: auto` dentro del flujo natural del documento.
2. **Validación en Navegador Real:**
   - Utilizar **Karate UI** (`frontend/test/ui_business_flow.feature`) y **Playwright** (`frontend/e2e/*.e2e.ts`) con Chromium headless para certificar que todos los botones e inputs sean geométricamente clicables tanto en viewport móvil (`iPhone 13`) como en escritorio.

---

## 3. Seguridad por Diseño (Security-by-Design)

1. **Prevención de Asignación Masiva (`extra="forbid"`):** Todos los DTOs de entrada en `backend/src/schemas.py` rechazan atributos no declarados con HTTP 422.
2. **Defensa Anti-SSRF (`validate_safe_outgoing_url`):** Validación estricta de esquemas `http`/`https`, bloqueo de contenedores internos (`localhost`, `api`, `postgres`, `keydb`, `redis`, `minio`) y resolución DNS previa contra rangos privados RFC 1918 y link-local (`169.254.169.254`).
3. **Hashing Criptográfico con Sal (`PBKDF2-HMAC-SHA256`):** Contraseñas protegidas con sal aleatoria de 16 bytes, 100.000 iteraciones y comparación en tiempo constante (`hmac.compare_digest`).
4. **Llaves de Idempotencia Aisladas por Ámbito (`Idempotency-Key`):** Espacio de nombres `idemp:{scope}:{key}` en KeyDB Multi-Hilo para evitar colisiones cruzadas entre usuarios.
5. **Cuotas de Archivos Anti-DoS (`read_uploaded_file_safely`):** Lectura en streaming con límite estricto de 2 MB (`HTTP 413`).
6. **Sanitización 422 y Ocultamiento de OpenAPI en Producción:** Cuando `APP_ENV=production`, se desactivan `/docs`, `/redoc` y `/openapi.json` y se devuelven mensajes 422 genéricos sin exponer detalles internos.

---

## 4. Paridad Terminal ↔ Frontend y Manejo de Errores No Destructivo

1. **Cero Endpoints Huérfanos:** Cada ruta en FastAPI tiene su vista y flujo interactivo mapeado en `docs/API_ROUTES.md` y `docs/specs/05_ARQUITECTURA_GUI_VUE3_MOBILE_FIRST.md`.
2. **Cero Componentes UI Huérfanos:** Cada archivo `.vue` debe contar con su suite `.unit.ts` verificada por `verify_zero_orphan_vue_components.py`.
3. **Manejo de Errores No Destructivo en Pinia:**
   ```typescript
   // ✔️ PATRÓN 11X: Preserva el último estado válido conocido ante micro-cortes de red móvil
   try {
     const data = await api.getResumenFinanciero();
     resumen.value = data;
     isStale.value = false;
   } catch (error) {
     isStale.value = true;
     lastErrorMessage.value = 'Sin conexión temporal. Mostrando últimos datos sincronizados.';
   }
   ```
