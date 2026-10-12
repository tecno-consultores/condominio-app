# CI/CD Pipelines y Git Hooks Locales - Condominio App

Este documento detalla la integración continua automatizada y las barreras de entrada locales mediante Git Hooks para garantizar el estándar **Nivel 11X** en el repositorio de Condominio App.

---

## 1. Filosofía de CI/CD: Paridad Absoluta

### El Anti-Patrón Tradicional
Instalar dependencias del lenguaje directamente en el runner de GitHub Actions (`actions/setup-python`, `actions/setup-node`) introduce discrepancias: librerías preinstaladas en el runner ocultan bugs que luego explotan en producción o en los servidores reales de despliegue.

### El Enfoque Blueprint Nivel 11X
* El runner de CI se trata como un host genérico con Docker instalado.
* **Se ejecutan exactamente los mismos comandos de los Makefiles que en local** (`make qa-lint`, `make qa-unit`, `make qa-mutation`, etc.).
* Si una suite pasa en la máquina del desarrollador dentro de los contenedores efímeros, pasará idénticamente en el runner de GitHub Actions.

---

## 2. Pipeline de GitHub Actions (`.github/workflows/qa-pipeline.yml`)

```yaml
name: QA Pipeline Condominio App (Nivel 11X)

on:
  push:
    branches: [ "main", "develop" ]
  pull_request:
    branches: [ "main", "develop" ]

jobs:
  auditoria-y-pruebas:
    name: 🛡️ Auditoría Estricta (95% Cobertura), Seguridad y Caos
    runs-on: ubuntu-latest

    steps:
      - name: 1️⃣ Checkout del código
        uses: actions/checkout@v4

      - name: 2️⃣ Auditoría de Seguridad de Infraestructura (Trivy IaC & FS)
        run: |
          docker run --rm -v "${PWD}:/app:ro" -w /app aquasec/trivy:latest config . --severity HIGH,CRITICAL --exit-code 1
          docker run --rm -v "${PWD}:/app:ro" -w /app aquasec/trivy:latest fs . --severity CRITICAL --exit-code 1

      - name: 3️⃣ Análisis Estático, Tipado y Complejidad (Backend)
        run: make -C backend qa-lint qa-complexity

      - name: 4️⃣ Pruebas Unitarias Aisladas (Backend >= 95% Cobertura)
        # Si la cobertura cae por debajo del 95%, pytest-cov aborta con exit code 1
        run: make -C backend qa-unit

      - name: 5️⃣ Pruebas de Mutación Backend (Mutmut)
        run: make -C backend qa-mutation

      - name: 6️⃣ Seguridad Dinámica DAST (OWASP ZAP)
        run: |
          docker compose -f backend/docker-compose.qa.yml up -d api
          docker compose -f backend/docker-compose.qa.yml run --rm zap zap-baseline.py -t http://api:8000 -r zap-report.html

      - name: 7️⃣ Ingeniería del Caos y Resiliencia (Pumba + Locust)
        run: docker compose -f backend/docker-compose.qa.yml --profile chaos up --abort-on-container-exit stress_test

      - name: 8️⃣ Archivar Artefactos de Calidad
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: reportes-calidad-qa
          path: |
            backend/htmlcov/
            backend/coverage.xml
            backend/zap-report.html
            backend/chaos-report.html
          retention-days: 7

      - name: 9️⃣ Limpieza de Cachés y Redes
        if: always()
        run: make -C backend clean-cache
```

---

## 3. Barrera de Entrada Local: `lefthook.yml`

Para impedir que código defectuoso, sin formato o con secretos expuestos ingrese a Git, se implementa `Lefthook` en la raíz del proyecto:

```yaml
# LEFTHOOK - BARRERA DE ENTRADA (Pre-commit, Commit-msg & Pre-push)
pre-commit:
  parallel: true
  commands:
    # --------------------------------------------------------------------------
    # BACKEND: PYTHON / FASTAPI
    # --------------------------------------------------------------------------
    python-lint:
      glob: "backend/**/*.py"
      run: docker compose -f backend/docker-compose.qa.yml run --rm qa-backend bash -c "uv sync -q && ruff check {staged_files} && ruff format --check {staged_files}"

    # --------------------------------------------------------------------------
    # FRONTEND: VUE 3 / TS
    # --------------------------------------------------------------------------
    vue-lint:
      glob: "frontend/**/*.{js,ts,vue}"
      run: docker compose -f frontend/docker-compose.qa.yml run --rm qa-vue3 bash -c "pnpm install --silent && npx prettier --check {staged_files} && npx eslint {staged_files}"

    # --------------------------------------------------------------------------
    # DETECCIÓN DE SECRETOS HARDCODEADOS (GLOBAL)
    # --------------------------------------------------------------------------
    leaks-check:
      glob: "**/*"
      run: if grep -qiE "(password|secret|api_key|token)[=:] *[\"'][a-zA-Z0-9]{8,}[\"']" {staged_files}; then echo "🚨 ERROR: Posible secreto hardcodeado detectado en staged files."; exit 1; fi

commit-msg:
  commands:
    conventional-commits:
      # Exige respetar el formato de Conventional Commits ejecutándose efímeramente
      # en la imagen oficial de Node (sinfallas/base-node-ionic) sin Node local.
      # El paquete bloquea npm: las dependencias se instalan con pnpm.
      # node_modules/ queda cacheado (gitignored) entre commits.
      run: docker run --rm -v "${PWD}:/repo" -w /repo sinfallas/base-node-ionic:26 sh -c "pnpm install --ignore-scripts --silent && ./node_modules/.bin/commitlint --edit {1}"

pre-push:
  commands:
    trivy-iac-scan:
      # Escanea configuraciones de Docker Compose antes de permitir el push
      run: docker run --rm -v "${PWD}:/app:ro" -w /app aquasec/trivy:latest config . --severity HIGH,CRITICAL --exit-code 1 --skip-dirs backend/.venv
```

---

## 4. Script de Instalación de Hooks: `instalar-hooks.sh`

```bash
#!/usr/bin/env bash
# Licencia: MIT
# Propósito: Inicializar la barrera de entrada de Lefthook en local.

LC_ALL=C
set -e

echo "🛡️ Configurando Barrera de Entrada Corporativa (Lefthook)..."

if command -v npm &> /dev/null; then
    echo "Instalando Lefthook vía NPM..."
    npm install -g @evilmartians/lefthook
else
    echo "Descargando binario de Lefthook..."
    curl -1sLf 'https://dl.cloudsmith.io/public/evilmartians/lefthook/setup.deb.sh' | sudo -E bash
    sudo apt install lefthook
fi

lefthook install
echo "✅ ¡Barrera activada! Los commits serán interceptados y validados efímeramente."
```
