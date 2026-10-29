# 🛡️ QA Testing & Calidad Nivel 11X - Condominio App

Bienvenido al centro de documentación del estándar de calidad, desarrollo seguro, pruebas automatizadas y resiliencia para el proyecto **Condominio App**.

Este repositorio sigue rigurosamente el estándar corporativo **Nivel 11X (`qa-testing-blueprints`)**, garantizando que todo el software producido (Backend en FastAPI y Frontend en Vue 3) esté matemáticamente probado, ejecutado en contenedores efímeros (`Rule Zero`), verificado contra motores reales de base de datos y protegido por diseño contra los 13 vectores de ataque en plataformas híbridas.

---

## 📚 Índice de Documentación de QA y Seguridad 11X

1. **[Arquitectura y Gobernanza de Agentes de IA (`01_ARQUITECTURA_Y_GOBERNANZA_AGENTES_IA.md`)](./01_ARQUITECTURA_Y_GOBERNANZA_AGENTES_IA.md):**
   * Estructura `.agents/` (`rules/`, `skills/`, `scripts/`), estrategia bimodal de ahorro de tokens (~35%) y compuerta de cierre `certify_task_completion.sh`.
2. **[Buenas Prácticas de Programación 11X (`02_BUENAS_PRACTICAS_PROGRAMACION_11X.md`)](./02_BUENAS_PRACTICAS_PROGRAMACION_11X.md):**
   * Erradicación de la ceguera de mocks (*Anti-Mock Blindness*), Geometría Visual *Anti-JSDOM*, ergonomía in-flow en móviles y manejo de errores no destructivo en Pinia.
3. **[Tipos de Pruebas y Pirámide de 13 Capas (`03_TIPOS_DE_PRUEBAS_Y_COMO_UTILIZARLOS.md`)](./03_TIPOS_DE_PRUEBAS_Y_COMO_UTILIZARLOS.md):**
   * Desglose de las 13 capas de aseguramiento y comandos de los `Makefiles`.
4. **[Guía de Desarrollo Seguro y Mitigación de Vulnerabilidades (`04_GUIA_DESARROLLO_SEGURO_Y_MITIGACION_DE_VULNERABILIDADES.md`)](./04_GUIA_DESARROLLO_SEGURO_Y_MITIGACION_DE_VULNERABILIDADES.md):**
   * Catálogo de los 13 patrones defensivos implementados (Prevención de Asignación Masiva `extra="forbid"`, Anti-SSRF, PBKDF2-HMAC-SHA256, CSRF HMAC, Cuota 2MB Anti-DoS, Anti-CSWSH, Idempotencia aislada en KeyDB Multi-Hilo, Anti-XSS y Anti-Prototype Pollution).
5. **[Filosofía y Principios Nivel 11X (`QA_PHILOSOPHY_11X.md`)](./QA_PHILOSOPHY_11X.md):**
   * Los pilares innegociables de calidad, piso de cobertura del 95%, mutación y observabilidad RED.
6. **[Guía de Pruebas para Backend FastAPI (`BACKEND_FASTAPI_QA.md`)](./BACKEND_FASTAPI_QA.md):**
   * Pila tecnológica del Backend con `PostgreSQL 17`, `KeyDB Multi-Hilo`, `Karate Labs API`, `Schemathesis`, `OWASP ZAP` y `Pumba + Locust`.
7. **[Guía de Pruebas para Frontend Vue 3 (`FRONTEND_VUE3_QA.md`)](./FRONTEND_VUE3_QA.md):**
   * Pila tecnológica del Frontend con `Vitest`, `qa-orphans`, `Stryker`, `Playwright + @axe-core`, `Lighthouse CI` y `Karate Labs UI`.
8. **[CI/CD Pipelines y Git Hooks Locales (`CI_CD_AND_HOOKS.md`)](./CI_CD_AND_HOOKS.md):**
   * Workflows de GitHub Actions, `auditar-infra.sh`, `scripts/verificar-secretos.sh` y barrera `Lefthook`.
9. **[Directivas de Sistema para Inteligencia Artificial (`AI_MASTER_PROMPT.md`)](./AI_MASTER_PROMPT.md):**
   * Master Prompt operativo actualizado con las 10 leyes de infraestructura y la compuerta de certificación de 7 pasos.
