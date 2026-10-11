Control de Tareas y Roadmap - Condominio App
FASE 1: Backend Base y Estructura (FastAPI)

Hito 1: Setup Base y Modelos de Datos. [COMPLETADO]
La Tarea para la IA: Crear el src/main.py (inyectando Prometheus), configurar la conexión a PostgreSQL con SQLAlchemy y Alembic, y modelar la Entidad Usuario y Estructura (Sectores/Unidades), incluyendo la tabla histórica Contratos_Ocupacion.
Pruebas a exigirle: Un test que mockee la base de datos y verifique que main.py responde al Healthcheck, y pruebas unitarias de los esquemas Pydantic y modelos.

Hito 2: Autenticación y JWT. [COMPLETADO]
La Tarea para la IA: Crear las rutas de Login y Registro (/api/auth) exigiendo Idempotency-Key. Generación de JWT en cookies HttpOnly y creación de Usuarios Fantasmas. Endpoint /api/auth/me.
Pruebas a exigirle: Simular fallos de base de datos (pytest-mock). Verificar validaciones Pydantic. Validar idempotencia con Redis y ciclo de vida de tokens JWT (válido, expirado, inválido).
Hito 3: Finanzas y Cobranzas (El Core Matemático).
La Tarea para la IA: Modelar recibos, deuda, egresos multimoneda (Tasa del día) y el flujo idempotente de reportar pago. Implementar la inmutabilidad del "Candado Contable" (POST /api/finanzas/cierre-mensual) y la Pista de Auditoría (Audit Trail) con motivos obligatorios de rechazo.
Pruebas a exigirle: Pruebas de Mutación (mutmut) súper estrictas en la matemática de "pago parcial vs total". Verificación de la tasa del día.
Hito 4: Módulos Operativos y Tareas Asíncronas.
La Tarea para la IA: Aprobación de Usuarios (Presidente asignando unidad), Incidencias ("Me sumo"), y Cronjob de Tareas (generación automática desde plantillas para el conserje). Validar límite estricto de 30 fotos/mes para Voceros. Integrar Celery/Worker para conversión a AVIF y envío de correos.
Pruebas a exigirle: Mockear MinIO, Redis y el Cronjob. (Entre cada Hito, tú corres make qa-unit y make qa-mutation. Si algo falla, se lo devuelves a la IA para que lo arregle).

FASE 2: Frontend Base (Vue 3)

Hito 5: Setup de Pinia, Vue Router y Componentes Base.
La Tarea para la IA: Crear el cascarón de la app, el layout general (Bottom bar / Sidebar), implementar la vista de Login/Registro y la Pantalla de Bloqueo (/espera-aprobacion) para usuarios fantasma.
Pruebas a exigirle: Vitest con jsdom puro (sin navegador). Cobertura >95% en los stores de Pinia.
Hito 6: Vistas Financieras y Tesorería.
La Tarea para la IA: El Wizard de pagos (los 3 pasos, con id de idempotencia), Dashboards condicionales (Banner de Cierre, Carrusel de Comunicados, Semáforo de Cobranza), y el UX de Rechazo de Pagos (Modal obligatorio de motivo).
Pruebas a exigirle: Complejidad cognitiva baja en los componentes (SonarJS).
Hito 7: Vistas Administrativas y Conserjería.
La Tarea para la IA: Constructor de estructuras, asignación de usuarios, UI del Embudo de Incidencias (estilo Feed de Instagram con lógica "Me Sumo"), y checklist del conserje.

FASE 3: Integración y Caos (Nivel 11X)

Hito 8: End-to-End y Accesibilidad.
La Tarea para la IA: Escribir los scripts de Playwright (.e2e.ts) interceptando la API (mocking de rutas) para validar el flujo visual completo (Accessibility / Snapshots).
Hito 9: Resiliencia Extrema.
Tú, como arquitecto, levantas la app viva y corres docker compose --profile chaos up. Observas Prometheus mientras Pumba inyecta latencia y Locust ataca.

