<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

# 📘 Manual Maestro de Instalación, Despliegue y Administración Integral

**Condominio App — Sistema Integral de Gestión Residencial y PropTech**  
*Conforme a la Ley de Propiedad Horizontal (LPH) y al Estándar Corporativo de Calidad Nivel 11X*  
**Versión de Documentación:** 3.0 (Hito 18)  
**Fecha de Emisión:** Noviembre 2026

---

## 📑 Tabla de Contenido

- [PARTE I: GUÍA TÉCNICA DE INSTALACIÓN, INFRAESTRUCTURA Y DEVSECOPS](#parte-i-guía-técnica-de-instalación-infraestructura-y-devsecops)
  - [1. Requisitos de Infraestructura y Topología de Red](#1-requisitos-de-infraestructura-y-topología-de-red)
  - [2. Configuración de Variables de Entorno (.env) y Secretos Criptográficos](#2-configuración-de-variables-de-entorno-env-y-secretos-criptográficos)
  - [3. Despliegue con Docker Compose (Rule Zero)](#3-despliegue-con-docker-compose-rule-zero)
  - [4. Servidor Web Reverso, Terminación TLS/SSL y Cabeceras de Seguridad](#4-servidor-web-reverso-terminación-tlsssl-y-cabeceras-de-seguridad)
  - [5. Estrategia de Respaldo, Restauración y Recuperación ante Desastres](#5-estrategia-de-respaldo-restauración-y-recuperación-ante-desastres)
  - [6. Mantenimiento Preventivo, Auditoría y Sanitización](#6-mantenimiento-preventivo-auditoría-y-sanitización)
- [PARTE II: GUÍA OPERATIVA PARA LA JUNTA DE CONDOMINIO Y ADMINISTRADOR](#parte-ii-guía-operativa-para-la-junta-de-condominio-y-administrador)
  - [7. Configuración Inicial de la Comunidad: Torres y Unidades](#7-configuración-inicial-de-la-comunidad-torres-y-unidades)
  - [8. Asignación de Alícuotas (LPH) y Cuotas Fijas Mensuales](#8-asignación-de-alícuotas-lph-y-cuotas-fijas-mensuales)
  - [9. Activación de Usuarios Fantasma y Asignación de Inmuebles](#9-activación-de-usuarios-fantasma-y-asignación-de-inmuebles)
  - [10. Designación Estatutaria de Cargos de la Junta Directiva](#10-designación-estatutaria-de-cargos-de-la-junta-directiva)
  - [11. Gestión de Tesorería, Facturación Trimodal y Aprobación de Pagos](#11-gestión-de-tesorería-facturación-trimodal-y-aprobación-de-pagos)
  - [12. Ejecución Inmutable del Candado Contable Mensual](#12-ejecución-inmutable-del-candado-contable-mensual)
  - [13. Emisión y Verificación de Solvencias Digitales](#13-emisión-y-verificación-de-solvencias-digitales)
  - [14. Cartas Consulta (Art. 23 LPH) y Escrutinio Ponderado](#14-cartas-consulta-art-23-lph-y-escrutinio-ponderado)
  - [15. Bitácora de Secretaría, Asambleas y Minutas Oficiales](#15-bitácora-de-secretaría-asambleas-y-minutas-oficiales)
  - [16. Operaciones de Garita: Control de Acceso QR y Paquetería](#16-operaciones-de-garita-control-de-acceso-qr-y-paquetería)
  - [17. Gestión de Áreas Sociales con Candado por Morosidad](#17-gestión-de-áreas-sociales-con-candado-por-morosidad)
  - [18. Checklist Diario de Conserjería y Mantenimiento de Bombas](#18-checklist-diario-de-conserjería-y-mantenimiento-de-bombas)
- [ANEXO: INSTRUCCIONES PARA EXPORTAR ESTE MANUAL A FORMATO PDF](#anexo-instrucciones-para-exportar-este-manual-a-formato-pdf)

---

# PARTE I: GUÍA TÉCNICA DE INSTALACIÓN, INFRAESTRUCTURA Y DEVSECOPS

Esta sección está destinada al personal técnico de sistemas, DevOps o soporte especializado responsable de instalar, asegurar y mantener en funcionamiento la plataforma sobre servidores Linux (Ubuntu Server 22.04 / 24.04 LTS o Debian 12).

---

## 1. Requisitos de Infraestructura y Topología de Red

### 1.1. Especificaciones de Hardware Recomendadas

| Entorno | N° Unidades / Inmuebles | CPU Cores | Memoria RAM | Almacenamiento SSD | Ancho de Banda |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Pequeño** | Hasta 60 unidades | 2 vCPU | 4 GB | 40 GB NVMe | 20 Mbps simétricos |
| **Mediano** | 61 a 250 unidades | 4 vCPU | 8 GB | 80 GB NVMe | 50 Mbps simétricos |
| **Grande / Complejo** | 251 a 1.000 unidades | 8 vCPU | 16 GB | 200 GB NVMe | 100 Mbps simétricos |

### 1.2. Arquitectura de Servicios y Contenedores

La plataforma se despliega íntegramente mediante contenedores Docker orquestados con Docker Compose:

1. **`postgres` (Motor de Base de Datos Principal):** PostgreSQL versión 17 oficial sobre Alpine Linux (`postgres:17-alpine`), conectado exclusivamente a la red interna `backend_net` con volumen persistente y aritmética `NUMERIC(12,2)`.
2. **`keydb` (Motor de Caché en Memoria, Colas y Bloqueo de Idempotencia):** KeyDB Multi-Threaded (`eqalpha/keydb:alpine`) ejecutado en modo `--read-only` con autenticación `--requirepass`, comandos administrativos peligrosos deshabilitados (`FLUSHALL`, `FLUSHDB`, `CONFIG`, `DEBUG`, `SHUTDOWN`) y soporte de `--server-threads 2`.
3. **`minio` (Almacenamiento de Objetos S3 Compatible):** MinIO Server (`minio/minio:RELEASE.2025-02-18T16-25-55Z`) en red interna para resguardar fotografías AVIF, evidencias de pagos e imágenes de incidencias vecinales.
4. **`api` (API REST y Lógica de Negocio):** FastAPI asíncrono con Python 3.13 construyendo una imagen multi-stage sin dependencias dev (`uv sync --frozen --no-dev`), sin `pip`/`ensurepip`, en modo `--read-only` bajo usuario no privilegiado `UID/GID 10001`.
5. **`worker` (Worker Asíncrono Real `python -m src.worker` y Supervisor `QA-HEALTH-01`):** Contenedor hermano no-root (`10001:10001`, `--read-only`) encargado de conversión real `Pillow` AVIF + carga autenticada `AWS4-HMAC-SHA256` a MinIO, consumidor `BLPOP` SMTP `STARTTLS` con Dead-Letter Queue (`queue:notifications:dlq`), scheduler diario idempotente (`uq_tarea_diaria_plantilla_fecha`) y heartbeat físico verificado por `python -m src.worker --check-health`.
6. **`frontend` (Lienzo Web Progresivo SPA + Proxy Reverso):** Aplicación Vue 3 compilada y servida por `nginx:1.27-alpine` endurecido no-root (`UID/GID 101:101`, `--read-only`, puerto `8080`), único puerto expuesto hacia `127.0.0.1:${FRONTEND_PORT:-8080}:8080`, con proxy inverso hacia `/api/`, `/health` y `/ws/`, `server_tokens off`, cuota `2M` y cabeceras OSHP/STIG.

---

## 2. Configuración de Variables de Entorno (.env) y Secretos Criptográficos

Antes del despliegue, copie la plantilla unificada en la raíz del proyecto, proteja los permisos del archivo y genere las claves criptográficas de producción:

```bash
cd /opt/condominio-app
cp .env.example .env && chmod 600 .env
```

### 2.1. Parámetros Críticos de Seguridad en `.env` (Raíz Unificada)

```ini
# ==============================================================================
# CONFIGURACIÓN DE NÚCLEO Y SEGURIDAD CRIPTOGRÁFICA (Variables Reales en .env)
# ==============================================================================
APP_ENV=production
ALLOWED_ORIGINS="https://condominio.mi-comunidad.com,https://www.condominio.mi-comunidad.com"
COOKIE_SECURE=true
CSRF_ENFORCE=true
FRONTEND_PORT=8080

# Clave secreta simétrica HS256/HMAC-SHA256 para JWT, CSRF, firmas de solvencia, votos LPH y pases QR.
# En APP_ENV=production el arranque aborta (Fail-Fast) si mide < 32 caracteres o conserva el valor placeholder.
SECRET_KEY="CAMBIAR_PLACEHOLDER_GENERAR_CON_OPENSSL_RAND_HEX_32"

# ==============================================================================
# BASE DE DATOS POSTGRESQL 17
# ==============================================================================
POSTGRES_DB=condominio_db
POSTGRES_USER=condominio_admin
POSTGRES_PASSWORD=CAMBIAR_PLACEHOLDER_POSTGRES_PASSWORD
# En APP_ENV=production el arranque aborta si esta variable falta o usa SQLite (:memory:)
DATABASE_URL=postgresql+asyncpg://condominio_admin:CAMBIAR_PLACEHOLDER_POSTGRES_PASSWORD@postgres:5432/condominio_db

# ==============================================================================
# MOTOR KEYDB (MULTI-HILO, PROTOCOLO REDIS)
# ==============================================================================
KEYDB_PASSWORD=CAMBIAR_PLACEHOLDER_KEYDB_PASSWORD
REDIS_URL=redis://:CAMBIAR_PLACEHOLDER_KEYDB_PASSWORD@keydb:6379/0

# ==============================================================================
# ALMACENAMIENTO S3 / MINIO, WORKER Y RESPALDOS
# ==============================================================================
MINIO_ENDPOINT=http://minio:9000
MINIO_ROOT_USER=condominio_minio
MINIO_ROOT_PASSWORD=CAMBIAR_PLACEHOLDER_MINIO_PASSWORD
MINIO_BUCKET=condominio-media
MINIO_USE_SSL=false
WORKER_HEARTBEAT_PATH=/tmp/worker_heartbeat
WORKER_POLL_SECONDS=1
WORKER_MEDIA_ENABLED=false
BACKUP_DIR=/var/backups/condominio
BACKUP_RETENTION_DAYS=30
BACKUP_PASSPHRASE=

# Bootstrap Inicial Día 0 (opcional)
BOOTSTRAP_CONDOMINIO_ID=1
BOOTSTRAP_ADMIN_NOMBRE="Presidente Junta Inicial"
BOOTSTRAP_ADMIN_CEDULA="V-00000001"
BOOTSTRAP_ADMIN_CORREO=
BOOTSTRAP_ADMIN_TELEFONO="+584120000000"
BOOTSTRAP_ADMIN_PASSWORD=
BOOTSTRAP_ADMIN_ROL=PRESIDENTE
```

> [!IMPORTANT]
> **Generación de Secretos Seguros en Consola:**
> Para generar un valor criptográficamente aleatorio para `SECRET_KEY` (mínimo 32 caracteres; recomendado 64 hex) y contraseñas de infraestructura, ejecute en su terminal:
> ```bash
> openssl rand -hex 32
> ```

---

## 3. Despliegue con Docker Compose (Rule Zero)

Siguiendo el estándar de calidad corporativo **QA Nivel 11X**, ningún servicio debe instalarse directamente en el sistema operativo base del host. Todos los procesos corren aislados en Docker.

### 3.1. Arranque en Frío del Sistema de Producción

1. Clone el repositorio oficial en la ruta del servidor de producción:
   ```bash
   git clone https://github.com/tecno-consultores/condominio-app.git /opt/condominio-app
   cd /opt/condominio-app
   ```
2. Ejecute el levantamiento de los contenedores en segundo plano:
   ```bash
   docker compose up -d --build
   ```
3. Ejecute las migraciones automáticas de base de datos Alembic (PostgreSQL 17):
   ```bash
   docker compose exec api alembic upgrade head
   ```
4. Inicialice de forma idempotente el primer usuario administrativo ("Día 0", rol `PRESIDENTE`) evitando pasar la contraseña por argumentos de línea de comandos:
   ```bash
   docker compose exec -e BOOTSTRAP_ADMIN_PASSWORD="SU_CONTRASENA_SEGURA_MIN_12" api \
     python -m src.bootstrap \
       --condominio-id 1 \
       --nombre "Presidente Junta Inicial" \
       --cedula "V-00000001" \
       --correo "presidente@mi-comunidad.com" \
       --telefono "+584120000000" \
       --rol PRESIDENTE
   ```
5. Compruebe la salud y conectividad de todos los servicios (API, Frontend Nginx y Worker `QA-HEALTH-01`):
   ```bash
   curl -i http://127.0.0.1:8080/health
   # Debe responder HTTP/1.1 200 OK con cuerpo JSON: {"status": "healthy"}
   docker compose exec worker python -m src.worker --check-health
   ```

---

## 4. Servidor Web Reverso, Terminación TLS/SSL y Cabeceras de Seguridad

Para exponer la aplicación en Internet con dominio propio y certificado HTTPS de Let's Encrypt, instale **Nginx** como proxy reverso frontal.

### 4.1. Configuración de Nginx (`/etc/nginx/sites-available/condominio.conf`)

```nginx
# Redirección estricta de tráfico HTTP a HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name condominio.mi-comunidad.com api.condominio.mi-comunidad.com;
    return 301 https://$host$request_uri;
}

# Servidor HTTPS Seguro
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name condominio.mi-comunidad.com;

    # Certificados TLS emitidos por Certbot
    ssl_certificate /etc/letsencrypt/live/condominio.mi-comunidad.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/condominio.mi-comunidad.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Cabeceras DISA ASD STIG V6R5 y OWASP v4.2
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; img-src 'self' data: blob: https:; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self' data:; connect-src 'self' https:;" always;

    # Límite máximo de carga de comprobantes (2 MB)
    client_max_body_size 2M;

    # Enrutamiento al Gateway Nginx Unificado del Contenedor Frontend (puerto 8080)
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Enrutamiento explícito al Backend API FastAPI (vía gateway frontend:8080)
    location /api/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Endpoint de salud Liveness (/health -> api:8000 vía gateway)
    location = /health {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket para notificaciones en vivo (vía gateway frontend:8080)
    location /ws/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 5. Estrategia de Respaldo, Restauración y Recuperación ante Desastres

### 5.1. Respaldo Diario Automatizado (Script `scripts/backup-diario.sh`)

Utilice el script certificado [`scripts/backup-diario.sh`](../scripts/backup-diario.sh) desde una tarea programada en `cron` o `systemd timer`. El script lee `.env` de forma segura, verifica capacidad en disco (emitiendo alerta `APSC-DV-001090` si el sistema de archivos supera el `75%` de ocupación), genera volcados de PostgreSQL 17 (`pg_dump --format=custom | gzip -9`) y espejo de MinIO comprimido, calcula sumas `.sha256`, aplica cifrado opcional `AES-256-CBC + PBKDF2` (`100000` iteraciones) cuando se define `BACKUP_PASSPHRASE` y depura respaldos antiguos según `BACKUP_RETENTION_DAYS`:

```bash
# Ejecución diaria estándar (lectura de .env en la raíz del proyecto)
/opt/condominio-app/scripts/backup-diario.sh --retention-days 30

# Ejemplo crontab diario a las 02:30 AM (registrando bitácora operativa)
30 2 * * * /opt/condominio-app/scripts/backup-diario.sh >> /var/log/condominio-backup.log 2>&1
```

### 5.2. Procedimiento de Restauración en Caliente

Para restaurar una base de datos a partir de un respaldo comprimido:

```bash
# 1. Detener el backend para evitar escritura concurrente
docker compose stop backend

# 2. Restaurar la base de datos PostgreSQL
gunzip -c /var/backups/condominio/db_FECHA.dump.gz | docker compose exec -T postgres pg_restore -U condo_admin -d condominio_db --clean --if-exists

# 3. Reiniciar los servicios
docker compose start backend
```

---

## 6. Mantenimiento Preventivo, Auditoría y Sanitización

El repositorio incluye herramientas automáticas de mantenimiento:

- **Limpieza de Archivos Temporales y Caché:**
  ```bash
  ./scripts/limpieza.sh
  ```
  Elimina contenedores detenidos, volúmenes huérfanos, cachés locales de Node y compilados temporales sin afectar los volúmenes persistentes de producción.
- **Auditoría de Seguridad y Escaneo de Secretos:**
  ```bash
  ./scripts/auditar-infra.sh
  ./scripts/verificar-secretos.sh
  ```
  Certifica que no existan puertos innecesarios expuestos ni secretos confidenciales expuestos en el código fuente.

---

# PARTE II: GUÍA OPERATIVA PARA LA JUNTA DE CONDOMINIO Y ADMINISTRADOR

Esta sección explica de manera pedagógica cómo operar las funcionalidades del sistema desde el navegador web o la app móvil, dirigida a los miembros de la Junta de Condominio (Presidente, Vicepresidente, Tesorero, Secretario y Vocero).

---

## 7. Configuración Inicial de la Comunidad: Torres y Unidades

**Ruta en el Sistema:** Menú Lateral $\rightarrow$ **Administración** $\rightarrow$ **Estructura y Unidades** (`/admin/estructura`)  
**Rol Requerido:** `PRESIDENTE` o `VICEPRESIDENTE`

Al instalar el sistema por primera vez en su edificio o conjunto residencial, debe crearse la infraestructura física:

1. **Nombre del Edificio o Bloque:** Ingrese el nombre representativo (ejemplo: `Torre A`, `Edificio Azalea`, `Manzana 3`).
2. **Generación Rápida de Identificadores:** En el campo de identificadores, escriba los números o letras de cada apartamento o casa separados por coma. Ejemplo:  
   `1-A, 1-B, 1-C, 1-D, 2-A, 2-B, 2-C, 2-D, PH-1, PH-2`
3. **Pulsar "Generar Estructura":** El sistema creará en un solo paso todas las unidades habitacionales sin riesgo de duplicarlas gracias a la protección de idempotencia.

---

## 8. Asignación de Alícuotas (LPH) y Cuotas Fijas Mensuales

**Ruta en el Sistema:** Misma pantalla de **Estructura y Unidades** (`/admin/estructura`) en la tabla inferior.

La Ley de Propiedad Horizontal exige que los gastos comunes sean distribuidos de acuerdo al porcentaje de alícuota establecido en el Documento de Condominio registrado. El sistema ofrece flexibilidad total:

- **Alícuota Porcentual (%):** Ingrese el porcentaje exacto de cada apartamento (ejemplo: `2.4560%`). El sistema utiliza el algoritmo matemático de **Hamilton / Resto Mayor** para garantizar que la suma de todos los recibos coincida hasta el último centavo con el total de gastos comunes sin generar centavos perdidos.
- **Cuota Fija Mensual (USD):** Si su comunidad acordó en asamblea cobrar una cuota fija plana en dólares (ejemplo: `$30.00 USD` mensuales por unidad), puede establecer dicho valor. Cuando se facture bajo esta modalidad, el sistema enviará automáticamente cualquier excedente o déficit al **Fondo de Reserva del Condominio**.

---

## 9. Activación de Usuarios Fantasma y Asignación de Inmuebles

**Ruta en el Sistema:** Menú Lateral $\rightarrow$ **Administración** $\rightarrow$ **Usuarios Pendientes** (`/admin/usuarios`)  
**Rol Requerido:** `PRESIDENTE` o `VICEPRESIDENTE`

Por motivos de seguridad, cuando un vecino se registra en la plataforma, su cuenta se crea en estado inactivo denominado **"Usuario Fantasma"**. El vecino no podrá ver balances, cuentas bancarias ni emitir votos hasta ser validado por la Junta:

1. Ingrese a la bandeja de **Usuarios Pendientes**.
2. Revise el nombre completo, cédula de identidad, correo y teléfono del solicitante.
3. Compruebe la **Unidad Inmobiliaria** solicitada. Si hubo un error en la selección del apartamento, corríjalo en el desplegable.
4. Seleccione su condición: `PROPIETARIO`, `INQUILINO` o `CONSERJE`.
5. Presione **"Activar Usuario"**: A partir de ese instante, el vecino tendrá acceso inmediato a su estado de cuenta y utilidades comunitarias.

---

## 10. Designación Estatutaria de Cargos de la Junta Directiva

**Ruta en el Sistema:** Menú Lateral $\rightarrow$ **Administración** $\rightarrow$ **Junta de Condominio** (`/admin/junta`)  
**Rol Requerido:** `PRESIDENTE`

De conformidad con el Artículo 18 de la Ley de Propiedad Horizontal, los cargos directivos deben ser ocupados por copropietarios del inmueble:

1. Seleccione al residente electo en la asamblea de copropietarios.
2. Escoja el cargo asignado:
   - `PRESIDENTE`: Responsable general de la comunidad, apertura de consultas y contratos.
   - `VICEPRESIDENTE`: Apoyo y sustitución de funciones presidenciales.
   - `TESORERO`: Manejo de cuentas bancarias, aprobación de pagos, egresos y cierre contable.
   - `SECRETARIO`: Redacción y custodia de la bitácora de actas y minutas de asamblea.
   - `VOCERO`: Publicación de avances de obras y comunicación directa con la conserjería.
3. Presione **"Asignar Cargo"**: El sistema otorgará los permisos y menús específicos para dicho perfil.

---

## 11. Gestión de Tesorería, Facturación Trimodal y Aprobación de Pagos

La administración financiera es el corazón operativo del condominio.

### 11.1. Mesa de Aprobación de Pagos (`/tesoreria/pagos`)
- En esta pantalla aparecen en tiempo real todos los pagos reportados por los residentes (Pago Móvil, Transferencia bancaria, Zelle o Efectivo en divisas).
- Al pulsar sobre un comprobante, podrá visualizar la captura fotográfica del banco, el monto reportado en Bs o USD, la fecha y el número de referencia.
- **Aprobar:** Si el dinero está efectivo en la cuenta bancaria del condominio, pulse el botón verde "Aprobar". El balance del propietario se actualizará al instante.
- **Rechazar:** Si la referencia no aparece en el extracto bancario o el monto no coincide, pulse el botón rojo "Rechazar". El sistema le solicitará **obligatoriamente un motivo claro** (mínimo 5 caracteres) que notificará al residente para que corrija su reporte.

### 11.2. Facturación Mensual Masiva (`/tesoreria/facturacion`)
Al finalizar el mes, genere los recibos de cobro:
1. Ingrese el período contable (ejemplo: `2026-11`).
2. Seleccione la modalidad de cálculo:
   - **Por Alícuotas (Hamilton):** Distribuye los egresos comunes proporcionalmente al área del inmueble.
   - **Cuota Fija USD:** Factura un monto idéntico en divisas a cada unidad, enviando el saldo a favor a Fondos de Reserva.
   - **Partes Iguales:** Divide el monto total en partes equitativas entre el número total de unidades habitacionales.
3. Presione **"Generar Facturación Masiva"**. Todos los copropietarios recibirán su recibo detallado de forma simultánea.

---

## 12. Ejecución Inmutable del Candado Contable Mensual

**Ruta en el Sistema:** Menú Lateral $\rightarrow$ **Tesorería** $\rightarrow$ **Cierre y Egresos** (`/tesoreria/cierre`)  
**Rol Requerido:** `TESORERO` o `PRESIDENTE`

El **Candado Contable** es una salvaguarda de auditoría corporativa que impide la manipulación retroactiva de las finanzas comunitarias:

1. Registre todos los egresos del mes (facturas de electricidad común, reparaciones de bombas, servicio de conserjería, bolsas de basura, etc.).
2. Establezca la **Tasa Oficial de Cambio BCV** para liquidar pagos mixtos en bolívares.
3. Asegúrese de que no queden pagos sin revisar en la mesa de aprobación.
4. Presione el botón **"Ejecutar Candado Contable"** y confirme en el diálogo de seguridad.
5. **Efecto Jurídico:** A partir de ese momento, la contabilidad de dicho mes queda sellada criptográficamente en modo de solo lectura. Ningún usuario ni administrador podrá alterar, borrar ni reabrir recibos de períodos cerrados.

---

## 13. Emisión y Verificación de Solvencias Digitales

**Ruta en el Sistema:** Menú Lateral $\rightarrow$ **Finanzas** $\rightarrow$ **Certificado de Solvencia** (`/finanzas/solvencia`)

Para trámites de compra-venta, arrendamiento o protocolización notarial ante el Registro Público, los propietarios requieren una carta de no poseer deuda:

1. El sistema evalúa en tiempo real si el inmueble tiene saldo exactamente igual a `$0.00 USD`.
2. Si la unidad es solvente, se genera un **Certificado Digital de Solvencia** que incluye:
   - Folio único e identificador de registro.
   - Código QR legible por cualquier teléfono inteligente.
   - Firma digital en tiempo constante basada en algoritmo criptográfico **HMAC-SHA256**.
3. Cualquier interesado o registrador público puede escanear el QR y verificar instantáneamente la validez jurídica del documento sin necesidad de sellos húmedos tradicionales.

---

## 14. Cartas Consulta (Art. 23 LPH) y Escrutinio Ponderado

**Ruta en el Sistema:** Menú Lateral $\rightarrow$ **Gobernanza** $\rightarrow$ **Cartas Consulta** (`/consultas`)

El Artículo 23 de la Ley de Propiedad Horizontal faculta a la comunidad para tomar decisiones urgentes y acuerdos colectivos sin necesidad de celebrar asambleas presenciales:

1. **Creación de la Consulta:**
   - Ingrese el Título del tema a debatir (ejemplo: *Sustitución de Guayas del Ascensor Torre A*).
   - Redacte la exposición de motivos y adjunte presupuestos.
   - Fije la fecha y hora de vencimiento para la votación.
   - Seleccione la regla de cuórum requerida:
     - `UNANIMIDAD` (100% de las alícuotas para modificaciones al documento de condominio).
     - `DOS_TERCIOS` (66.67% de las alícuotas para obras de mejora o gastos extraordinarios).
     - `MAYORIA_SIMPLE` (50% + 1 de las alícuotas para actos ordinarios de administración).
   - Defina las opciones de voto (ejemplo: *Opción 1: Presupuesto Empresa Alfa ($850)*, *Opción 2: Presupuesto Empresa Beta ($920)*, *Opción 3: Rechazar Obra*).
2. **Escrutinio Transparente:**
   - Cada propietario vota desde su teléfono móvil.
   - El sistema pondera cada voto de acuerdo al porcentaje exacto de su alícuota.
   - Una vez finalizado el lapso, el sistema genera el acta de resultados y archiva de manera inmutable el acuerdo en la **Bitácora de Secretaría**.

---

## 15. Bitácora de Secretaría, Asambleas y Minutas Oficiales

**Ruta en el Sistema:** Menú Lateral $\rightarrow$ **Gobernanza** $\rightarrow$ **Bitácora de Secretaría** (`/secretaria/bitacora`)  
**Rol Requerido:** `SECRETARIO` o `PRESIDENTE`

- Funciona como el libro digital de actas de la asamblea de copropietarios.
- Permite asentar minutas de reuniones de la Junta, llamados de atención por normas de convivencia y acuerdos aprobados.
- Cada entrada queda registrada con sello de tiempo, autor y hash de integridad.

---

## 16. Operaciones de Garita: Control de Acceso QR y Paquetería

Herramientas tácticas diseñadas para personal de vigilancia, vigilantes nocturnos o conserjes.

### 16.1. Lector y Escáner QR de Garita (`/operaciones/garita-qr`)
- Cuando un visitante llega a la garita vehicular o peatonal, presenta el código QR emitido por el residente desde su teléfono.
- El personal de vigilancia escanea el código con la cámara de una tableta o celular, o introduce el código alfanumérico.
- El sistema comprueba en fracciones de segundo la identidad del visitante, cédula, unidad de destino y tiempo de validez.
- **Quemado de Nonce Anti-Reutilización:** Al ingresar, el token se destruye automáticamente en KeyDB, impidiendo que el mismo pase sea compartido o utilizado por otra persona.

### 16.2. Casillero Digital de Paquetería (`/operaciones/paqueteria`)
- **Registro de Encomiendas:** Al recibir un sobre o caja de empresas de encomiendas (Zoom, MRW, Tealca, MercadoLibre), el vigilante anota la unidad destinataria, la empresa y el número de guía.
- **Aviso Inmediato:** El residente recibe una notificación en su teléfono indicando que su paquete está en garita.
- **Entrega Segura:** Al momento de retirar, el vigilante pulsa "Confirmar Entrega", cerrando la custodia del paquete.

---

## 17. Gestión de Áreas Sociales con Candado por Morosidad

**Ruta en el Sistema:** Menú Lateral $\rightarrow$ **Amenidades** $\rightarrow$ **Reservas** (`/reservas/areas`)

- Permite calendarizar el disfrute de áreas comunes (Churuata, Salón de Fiestas, Piscina, Sala de Juegos, Cancha de Pádel o Parrillera).
- **Candado de Solvencia Automático:** El sistema bloquea de inmediato la posibilidad de reservar a cualquier propietario o inquilino cuya unidad mantenga recibos impagos pendientes ($\text{Deuda} > \$0.00$).
- **Anti-Solapamiento:** Garantiza que dos vecinos no puedan reservar el mismo espacio el mismo día.
- **Inspección Post-Evento:** Toda reserva completada genera automáticamente una tarea para que el conserje revise las condiciones de entrega del mobiliario al día siguiente.

---

## 18. Checklist Diario de Conserjería y Mantenimiento de Bombas

**Ruta en el Sistema:** Menú Lateral $\rightarrow$ **Operaciones** $\rightarrow$ **Checklist Diario** (`/operaciones/tareas`)

- Proporciona al conserje un checklist táctil de alta visibilidad para ejecutar en su teléfono móvil.
- Tareas habituales preconfiguradas:
  - Verificación de presión hidroneumática y bombas de agua potable.
  - Encendido y apagado de luminarias perimetrales y pasillos.
  - Limpieza de ascensores y cuartos de basura.
  - Inspección de cuartos de transformadores y portón vehicular.
- **Vinculación con Incidencias:** Si un conserje completa una tarea de reparación vinculada a una avería vecinal (ejemplo: cambiar bombillo del piso 3), la incidencia pública de los vecinos se marca como **Resuelta** de manera automática.

---

# ANEXO: INSTRUCCIONES PARA EXPORTAR ESTE MANUAL A FORMATO PDF

Este manual está redactado en formato Markdown estándar para que cualquier miembro de la comunidad pueda editarlo con un procesador de texto simple y convertirlo en un archivo **PDF profesional** para distribuirlo por WhatsApp o correo electrónico.

### Método 1: Exportar con Pandoc en Linux o macOS (Recomendado)

Si tiene instalada la utilidad `pandoc` y el motor `wkhtmltopdf` o `xelatex`:

```bash
cd /opt/condominio-app/docs
pandoc MANUAL_ADMINISTRADOR_E_INSTALADOR.md \
  -o MANUAL_ADMINISTRADOR_E_INSTALADOR.pdf \
  --pdf-engine=wkhtmltopdf \
  --metadata title="Manual Maestro de Instalación y Administración" \
  --metadata author="Condominio App Contributors" \
  -V geometry:margin=2cm
```

### Método 2: Desde el Navegador Web (Google Chrome / Chromium / Edge)

1. Abra este archivo Markdown en cualquier visualizador de Markdown con soporte de vista previa (ejemplo: Visual Studio Code con extensión *Markdown Preview Enhanced*, GitHub o un visor web local).
2. Pulse la combinación de teclas `Ctrl + P` (o `Cmd + P` en macOS) para abrir el cuadro de impresión del navegador.
3. En **Destino**, elija **"Guardar como PDF"**.
4. En **Márgenes**, elija **"Personalizados"** (20 mm) o **"Predeterminados"**.
5. Asegúrese de marcar la casilla **"Gráficos de fondo"** para que los colores de las tablas y alertas se impriman con fidelidad.
6. Haga clic en **Guardar** para generar el documento `Manual_Administrador_Condominio.pdf`.
