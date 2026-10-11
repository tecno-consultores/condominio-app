# Filosofía de Calidad Nivel 11X (QA Philosophy) - Condominio App

Este documento establece los principios de ingeniería de software, arquitectura de pruebas y decisiones estratégicas innegociables que gobiernan el desarrollo del proyecto **Condominio App**.

---

## 1. La Cobertura del 95% es un Piso, no una Meta
Exigir un **95% de cobertura** en `pytest-cov` (Backend) y `Vitest` (Frontend) no es una métrica de vanidad; es la barrera de contención contra regresiones silenciosas.
* Todo bloque de código `try/except`, ramificación condicional, validación de Pydantic o guardián de ruta debe ser cubierto por pruebas.
* Si una suite reporta menos del 95%, el pipeline falla inmediatamente (`Exit Code 1`).

## 2. Paranoia Positiva: Pruebas de Mutación
Una prueba unitaria que siempre pasa puede tener aserciones triviales o falsos positivos. Para validar que las pruebas realmente protegen la lógica de negocio:
* En **Backend**, utilizamos `mutmut`. Altera operadores matemáticos y lógicos en el código fuente (ej. cambia `>` por `>=`, o altera el cálculo de cuotas). Si la prueba no falla ante la mutación, el mutante "sobrevive" y se considera un fallo de calidad en las pruebas.
* En **Frontend**, usamos `Stryker` con el runner de Vitest sobre archivos `.ts` y `.vue`.

## 3. Efimeridad Absoluta (Cero `docker build` Local)
El mayor enemigo de la reproducibilidad es el estado persistente y los entornos de desarrollador "contaminados".
* **Regla estricta:** No se compilan imágenes personalizadas con `docker build` en la máquina host.
* Se consumen exclusivamente imágenes oficiales preconstruidas (familia `sinfallas/*` y herramientas oficiales como OWASP ZAP, Pumba, Prometheus, Playwright).
* Toda la ejecución ocurre dentro de contenedores orquestados al vuelo con Docker Compose, eliminándose al terminar (`run --rm`).
* La aceleración de dependencias se maneja exclusivamente a través de volúmenes persistentes nombrados (`uv-cache` para Python, `pnpm-store` para Node/Vue).

## 4. Aislamiento Estricto de Red (Mocking Obligatorio)
Las pruebas unitarias y de integración temprana tienen **estrictamente prohibido conectarse a servicios reales en internet o bases de datos de producción**:
* **Backend:** Uso riguroso de `pytest-mock` y `AsyncMock` para simular llamadas a PostgreSQL, Redis, MinIO o servicios de correo. Los tests unitarios deben ejecutarse en milisegundos en memoria (vía SQLite ephemeral o mocks puros).
* **Frontend:** Intercepción obligatoria de peticiones HTTP en Vitest y Playwright (`page.route('**/api/**', ...)`), evitando depender de la disponibilidad del backend para validar la interfaz visual.

## 5. Prevención de Deuda Técnica (Complejidad Ciclomática y Profiling)
No basta con que el código cumpla los requerimientos funcionales; debe ser legible, mantenible y eficiente:
* **Backend:** `radon` audita que ningún módulo exceda la complejidad ciclomática de grado B. El índice de mantenibilidad (MI) debe ser **A**. Adicionalmente, `py-spy` genera *Flamegraphs* visuales (`profile.svg`) para detectar si operaciones intensivas bloquean el Event Loop asíncrono de FastAPI.
* **Frontend:** `eslint-plugin-sonarjs` audita la complejidad cognitiva en componentes Vue y funciones TypeScript, rechazando funciones sobrecargadas.

## 6. Barreras Fronterizas Locales (Lefthook)
El código defectuoso o con riesgos de seguridad no debe tener derecho a ingresar al historial de Git.
* Se implementa `Lefthook` como interceptor local:
  * **Pre-commit:** Bloquea commits con código sin formatear (`ruff`, `prettier`) o si detecta patrones de contraseñas/secretos en texto plano.
  * **Commit-msg:** Exige formato Conventional Commits mediante `commitlint`.
  * **Pre-push:** Corre auditoría de infraestructura y vulnerabilidades mediante `Trivy`.

## 7. Seguridad Integral (SAST + DAST + IaC)
Asumimos que el código y la infraestructura son vulnerables por defecto:
* **SAST (Seguridad Estática):** `bandit` y `uv pip audit` en Python; `eslint-plugin-security` y `pnpm audit` en Vue.
* **DAST (Seguridad Dinámica):** `OWASP ZAP` ejecuta ataques en modo Baseline sobre la API viva en Docker para detectar cabeceras HTTP inseguras, CORS indebidos o fugas de información.
* **IaC (Infraestructura como Código):** `aquasec/trivy` escanea archivos de configuración Docker Compose y permisos de contenedores.

## 8. Resiliencia Extrema (Ingeniería del Caos con Pumba)
El sistema no puede asumir redes perfectas ni servidores estables:
* Mediante el perfil `--profile chaos`, la herramienta `Pumba` inyecta latencia aleatoria (jitter) y cortes temporales a nivel del Kernel de Linux directamente sobre el contenedor de FastAPI.
* Simultáneamente, `Locust` bombardea con oleadas masivas de usuarios concurrentes.
* El objetivo es certificar que la arquitectura posee auto-recuperación y no entra en interbloqueo (*deadlock*) cuando fallan PostgreSQL, Redis o la red interna.

## 9. Observabilidad Universal (Métricas RED)
No se puede proteger ni optimizar lo que no se mide:
* La API FastAPI debe exponer obligatoriamente el endpoint `/metrics` utilizando `prometheus-fastapi-instrumentator`.
* En pruebas de estrés y caos, `Prometheus` raspa las métricas en tiempo real cada 2 segundos para monitorear *Rate*, *Errors* y *Duration* (Métricas RED).
* En Frontend, `nginx-prometheus-exporter` monitorea las peticiones que recibe el contenedor web.

## 10. Seguridad Zero-Trust en Dependencias
* Para Node/Vue, se implementa `.npmrc` con `ignore-scripts=true` para mitigar ataques de cadena de suministro (Supply Chain Attacks).
* Para Python, `uv` resuelve y descarga dependencias con verificación de hashes y auditoría de vulnerabilidades con `uv pip audit`.

## 11. Fronteras Estrictas de Herramientas (Tool Boundaries)
Para evitar que las herramientas se interfieran mutuamente, los nombres de archivos siguen convenciones estrictas:
* `*.unit.py` / `*.spec.py`: Pruebas unitarias de backend rápidas y aisladas con mocks.
* `*.unit.ts` / `*.spec.ts`: Pruebas unitarias de componentes y stores en Vue con jsdom.
* `*.e2e.ts`: Pruebas de integración completa y regresión visual con Playwright.
* `*.feature`: Escenarios BDD de caja negra para Karate Labs.
