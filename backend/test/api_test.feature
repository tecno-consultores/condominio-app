# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors

Feature: Validación BDD de Caja Negra y Seguridad Nivel 11X de la API Condominio App (Karate Labs)

  Background:
    * url 'http://api:8000'
    * configure headers = { 'Content-Type': 'application/json' }

  # ==============================================================================
  # Grupo 1: Observabilidad, Salud y Cabeceras Defensivas HTTP
  # ==============================================================================

  Scenario: 1. Healthcheck responde con status healthy y cabeceras de seguridad
    Given path '/health'
    When method get
    Then status 200
    And match response == { status: 'healthy' }
    And match header Cache-Control == 'no-store'
    And match header X-Content-Type-Options == 'nosniff'
    And match header X-Frame-Options == 'DENY'
    And match header Content-Security-Policy contains "frame-ancestors 'none'"
    And match header Cross-Origin-Opener-Policy == 'same-origin-allow-popups'
    And match header Cross-Origin-Resource-Policy == 'same-origin'
    And match header Permissions-Policy contains 'camera=()'
    And match header Vary contains 'Sec-Fetch-Site'

  Scenario: 2. Métricas del sistema expuestas en formato Prometheus (/metrics)
    Given path '/metrics'
    When method get
    Then status 401

    Given path '/metrics'
    And header Authorization = 'Bearer fake-qa-metrics-token-11x'
    When method get
    Then status 200
    And match response contains 'http_'

  # ==============================================================================
  # Grupo 2: Autenticación, Idempotencia y Prevención de Asignación Masiva
  # ==============================================================================

  Scenario: 3. Consulta de /api/auth/me sin sesión devuelve 401
    Given path '/api/auth/me'
    When method get
    Then status 401
    And match response.detail == 'No autenticado'

  Scenario: 4. Registro sin Idempotency-Key devuelve error 422 de validación
    Given path '/api/auth/register'
    And request { nombre: "Sin Clave", correo: "test@test.com" }
    When method post
    Then status 422
    And match response.detail[0].loc contains 'Idempotency-Key'

  Scenario: 5. Intento de Asignación Masiva (extra=forbid) en registro es rechazado con 422
    Given path '/api/auth/register'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request
      """
      {
        "nombre": "Atacante Overposting",
        "cedula": "V-90000001",
        "correo": "atacante@test.com",
        "telefono": "+584140000001",
        "password": "Password123!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO",
        "rol": "TESORERO",
        "es_activo": true
      }
      """
    When method post
    Then status 422

  Scenario: 6. Login con credenciales inválidas devuelve 401
    * def badEmail = 'inexistente.' + java.util.UUID.randomUUID() + '@test.com'
    Given path '/api/auth/login'
    And request { correo: "#(badEmail)", password: "PasswordErroneo123!" }
    When method post
    Then status 401
    And match response.detail == 'Credenciales inválidas'

  Scenario: 7. Consulta de endpoints financieros sin autenticación devuelve 401
    Given path '/api/finanzas/resumen'
    When method get
    Then status 401
    And match response.detail == 'No autenticado'

  # ==============================================================================
  # Grupo 3: Estructura, Operaciones e Invariante de Bloqueo de Usuario Fantasma (Hito 4)
  # ==============================================================================

  Scenario: 8. Listado público de unidades disponibles devuelve 200 y un arreglo JSON
    Given path '/api/estructura/unidades'
    When method get
    Then status 200
    And match response == '#[]'

  Scenario: 9. Acceso a incidencias y conserjería sin autenticación devuelve 401
    Given path '/api/incidencias/abiertas'
    When method get
    Then status 401
    And match response.detail == 'No autenticado'

  Scenario: 10. Usuario Fantasma autenticado recibe 403 Forbidden al intentar acceder a módulos operativos
    * def uid = (java.util.UUID.randomUUID() + '').substring(0, 8)
    * def email = 'fantasma.' + uid + '@test.com'
    Given path '/api/auth/register'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request
      """
      {
        "nombre": "Fantasma BDD",
        "cedula": "#('V-' + uid)",
        "correo": "#(email)",
        "telefono": "+584144040404",
        "password": "Password123!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201
    And match response.es_activo == false
    And match response.rol == 'FANTASMA'

    Given path '/api/auth/login'
    And request { correo: "#(email)", password: "Password123!" }
    When method post
    Then status 200

    Given path '/api/incidencias/abiertas'
    When method get
    Then status 403
    And match response.detail contains 'pendiente de aprobación'

    Given path '/api/usuarios/pendientes'
    When method get
    Then status 403

    Given path '/api/finanzas/resumen'
    When method get
    Then status 403

    Given path '/api/pagos/revision'
    When method get
    Then status 403

  # ==============================================================================
  # Grupo 4: Facturación Mensual LPH, Alícuotas, Fondos y Solvencia Digital (Hito 10)
  # ==============================================================================

  Scenario: 11. Consulta de fondos patrimoniales y desglose de recibos sin sesión devuelve 401
    Given path '/api/finanzas/fondos'
    When method get
    Then status 401
    And match response.detail == 'No autenticado'

    Given path '/api/finanzas/recibos/1/desglose'
    When method get
    Then status 401
    And match response.detail == 'No autenticado'

  Scenario: 12. Usuario Fantasma recibe 403 Forbidden en endpoints de Alícuotas, Fondos, Facturación y Solvencia
    * def uid = (java.util.UUID.randomUUID() + '').substring(0, 8)
    * def email = 'fantasma.hito10.' + uid + '@test.com'
    Given path '/api/auth/register'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request
      """
      {
        "nombre": "Fantasma Hito 10 BDD",
        "cedula": "#('V-10' + uid)",
        "correo": "#(email)",
        "telefono": "+584144040410",
        "password": "Password123!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201

    Given path '/api/auth/login'
    And request { correo: "#(email)", password: "Password123!" }
    When method post
    Then status 200

    Given path '/api/estructura/unidades/1/alicuota'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { alicuota: "25.0000", cuota_fija_usd: "30.00" }
    When method put
    Then status 403

    Given path '/api/finanzas/fondos'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { nombre: "Fondo BDD", tipo: "RESERVA_LEGAL", porcentaje_recargo: "10.00" }
    When method post
    Then status 403

    Given path '/api/finanzas/facturar-periodo'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { periodo: "2026-10", modalidad: "CUOTA_FIJA", monto_cuota_fija_usd: "25.00" }
    When method post
    Then status 403

    Given path '/api/finanzas/solvencia/1'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request {}
    When method post
    Then status 403

  Scenario: 13. Verificación pública de Certificado de Solvencia inexistente devuelve 404
    Given path '/api/finanzas/solvencia/verificar/SOLV-202610-9999-XXXX'
    And param sig = 'firma_prueba_hmac_sha256'
    When method get
    Then status 404
    And match response.detail contains 'no encontrado'

  # ==============================================================================
  # Grupo 5: Gobernanza Digital, Cartas Consulta (Art. 23 LPH) y Asambleas (Hito 11)
  # ==============================================================================

  Scenario: 14. Listado y detalle de Cartas Consulta sin sesión devuelve 401 Unauthorized
    Given path '/api/consultas'
    When method get
    Then status 401
    And match response.detail == 'No autenticado'

    Given path '/api/consultas/1'
    When method get
    Then status 401
    And match response.detail == 'No autenticado'

  Scenario: 15. Usuario Fantasma recibe 403 Forbidden al listar, crear, votar o cerrar Cartas Consulta LPH
    * def uid = (java.util.UUID.randomUUID() + '').substring(0, 8)
    * def email = 'fantasma.hito11.' + uid + '@test.com'
    Given path '/api/auth/register'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request
      """
      {
        "nombre": "Fantasma Hito 11 BDD",
        "cedula": "#('V-11' + uid)",
        "correo": "#(email)",
        "telefono": "+584144040411",
        "password": "Password123!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201

    Given path '/api/auth/login'
    And request { correo: "#(email)", password: "Password123!" }
    When method post
    Then status 200

    Given path '/api/consultas'
    When method get
    Then status 403

    Given path '/api/consultas'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { titulo: "Carta Consulta BDD", descripcion_legal: "Sustento legal Art. 23 LPH", tipo_consulta: "CARTA_CONSULTA_1RA", regla_quorum: "DOS_TERCIOS", fecha_cierre: "2026-12-31T23:59:00Z", opciones: [{ etiqueta: "APROBAR", es_opcion_aprobatoria: true }, { etiqueta: "RECHAZAR", es_opcion_aprobatoria: false }] }
    When method post
    Then status 403

    Given path '/api/consultas/1/votar'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { unidad_id: 1, opcion_id: 1 }
    When method post
    Then status 403

    Given path '/api/consultas/1/cerrar'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request {}
    When method post
    Then status 403

  # ==============================================================================
  # Grupo 6: Control de Acceso QR (HMAC-SHA256 + KeyDB Anti-Replay) y Paquetería (Hito 12)
  # ==============================================================================

  Scenario: 16. Endpoints de Pases de Visita QR y Paquetería en Garita sin sesión devuelven 401 Unauthorized
    Given path '/api/accesos/pases/mios'
    When method get
    Then status 401
    And match response.detail == 'No autenticado'

    Given path '/api/paqueteria'
    When method get
    Then status 401
    And match response.detail == 'No autenticado'

  Scenario: 17. Usuario Fantasma recibe 403 Forbidden al emitir pases QR, verificar en garita o gestionar paquetería
    * def uid = (java.util.UUID.randomUUID() + '').substring(0, 8)
    * def email = 'fantasma.hito12.' + uid + '@test.com'
    Given path '/api/auth/register'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request
      """
      {
        "nombre": "Fantasma Hito 12 BDD",
        "cedula": "#('V-12' + uid)",
        "correo": "#(email)",
        "telefono": "+584144040412",
        "password": "Password123!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201

    Given path '/api/auth/login'
    And request { correo: "#(email)", password: "Password123!" }
    When method post
    Then status 200

    Given path '/api/accesos/pases/mios'
    When method get
    Then status 403

    Given path '/api/accesos/pases'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { unidad_id: 1, nombre_visitante: "Visitante BDD", cedula_visitante: "V-19888777", modalidad: "UNICO_USO", horas_validez: 12 }
    When method post
    Then status 403

    Given path '/api/accesos/verificar-qr'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { qr_token: "UVJ8djF8anRpfDF8VU5JQ09fVVNPfDE4MDAwMDAwMDA.0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef" }
    When method post
    Then status 403

    Given path '/api/paqueteria'
    When method get
    Then status 403

    Given path '/api/paqueteria/registrar'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { unidad_id: 1, empresa_envio: "ZOOM", descripcion: "Caja BDD" }
    When method post
    Then status 403

  # ==============================================================================
  # Grupo 7: Reserva de Áreas Sociales Vinculada a Solvencia e Inspección Post-Evento (Hito 13)
  # ==============================================================================

  Scenario: 18. Endpoints de Reserva de Áreas Sociales e Inspección Post-Evento sin sesión devuelven 401 Unauthorized
    Given path '/api/reservas/areas'
    When method get
    Then status 401
    And match response.detail == 'No autenticado'

    Given path '/api/reservas'
    When method get
    Then status 401
    And match response.detail == 'No autenticado'

  Scenario: 19. Usuario Fantasma recibe 403 Forbidden al consultar o reservar áreas sociales e inspeccionar post-evento
    * def uid = (java.util.UUID.randomUUID() + '').substring(0, 8)
    * def email = 'fantasma.hito13.' + uid + '@test.com'
    Given path '/api/auth/register'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request
      """
      {
        "nombre": "Fantasma Hito 13 BDD",
        "cedula": "#('V-13' + uid)",
        "correo": "#(email)",
        "telefono": "+584144040413",
        "password": "Password123!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201

    Given path '/api/auth/login'
    And request { correo: "#(email)", password: "Password123!" }
    When method post
    Then status 200

    Given path '/api/reservas/areas'
    When method get
    Then status 403

    Given path '/api/reservas/areas'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { nombre: "Salón BDD", aforo_maximo: 60, costo_uso_usd: "25.00", deposito_garantia_usd: "80.00", requiere_solvencia_estricta: true }
    When method post
    Then status 403

    Given path '/api/reservas'
    When method get
    Then status 403

    Given path '/api/reservas/solicitar'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { area_id: 1, unidad_id: 1, fecha_evento: "2026-12-25", motivo_evento: "Reserva BDD Hito 13" }
    When method post
    Then status 403

    Given path '/api/reservas/1/inspeccionar'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { estado: "FINALIZADA_SIN_DANOS", observaciones_inspeccion: "Inspección BDD" }
    When method put
    Then status 403

  Scenario: 20. Ciclo completo de sesión Hito 17.2 (DTO /me, rotación /refresh, /logout Clear-Site-Data, Idempotency-Key < 8 y Lockout 429)
    * def uid = java.util.UUID.randomUUID() + ''
    * def shortUid = uid.substring(0, 8)
    * def cedula = 'V-20' + shortUid
    * def email = 'bdd20_' + uid + '@condominio.com'

    # Idempotency-Key menor a 8 caracteres es rechazada con 422
    Given path '/api/auth/register'
    And header Idempotency-Key = 'abc'
    And request { nombre: "Corto BDD", cedula: "#(cedula)", correo: "#(email)", telefono: "+584145550020", password: "Password123!", unidad_solicitada_id: 1, tipo_ocupante_solicitado: "PROPIETARIO" }
    When method post
    Then status 422

    # Registro con Idempotency-Key válida
    Given path '/api/auth/register'
    And header Idempotency-Key = uid
    And request
      """
      {
        "nombre": "Usuario BDD Hito 17.2",
        "cedula": "#(cedula)",
        "correo": "#(email)",
        "telefono": "+584145550020",
        "password": "Password123!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201

    Given path '/api/auth/login'
    And request { correo: "#(email)", password: "Password123!" }
    When method post
    Then status 200
    And match response.csrf_token == '#string'
    * def csrfTok = response.csrf_token

    Given path '/api/auth/me'
    When method get
    Then status 200
    And match response contains { id: '#number', nombre: 'Usuario BDD Hito 17.2', cedula: '#(cedula)', correo: '#(email)', telefono: '+584145550020', es_activo: false, rol: 'FANTASMA', unidad_activa_id: null }
    * def meCsrf = karate.response.header('X-CSRF-Token')
    And match meCsrf == '#string'

    Given path '/api/auth/refresh'
    And header X-CSRF-Token = csrfTok
    When method post
    Then status 200
    And match response.csrf_token == '#string'

    Given path '/api/auth/logout'
    And header X-CSRF-Token = response.csrf_token
    When method post
    Then status 200
    And match response.message == 'Sesión cerrada exitosamente'
    * def clearSite = karate.response.header('Clear-Site-Data')
    And match clearSite == '"cookies", "storage", "cache"'

    # Tras logout la sesión queda revocada en KeyDB/cookie purgada -> 401
    Given path '/api/auth/me'
    When method get
    Then status 401

    # Lockout por fuerza bruta en login: 5 fallos (401) -> 6to intento bloqueado (429)
    * def lockEmail = 'lock_' + uid + '@condominio.com'
    Given path '/api/auth/login'
    And request { correo: "#(lockEmail)", password: "WrongPassword1!" }
    When method post
    Then status 401
    Given path '/api/auth/login'
    And request { correo: "#(lockEmail)", password: "WrongPassword1!" }
    When method post
    Then status 401
    Given path '/api/auth/login'
    And request { correo: "#(lockEmail)", password: "WrongPassword1!" }
    When method post
    Then status 401
    Given path '/api/auth/login'
    And request { correo: "#(lockEmail)", password: "WrongPassword1!" }
    When method post
    Then status 401
    Given path '/api/auth/login'
    And request { correo: "#(lockEmail)", password: "WrongPassword1!" }
    When method post
    Then status 401
    Given path '/api/auth/login'
    And request { correo: "#(lockEmail)", password: "WrongPassword1!" }
    When method post
    Then status 429

  Scenario: 21. Rechazo temprano Fetch Metadata para solicitudes cross-site no navegables antes de autenticación y aceptación same-origin
    Given path '/api/auth/me'
    And header Sec-Fetch-Site = 'cross-site'
    And header Sec-Fetch-Mode = 'cors'
    When method get
    Then status 403
    And match header X-Frame-Options == 'DENY'
    And match header Vary contains 'Sec-Fetch-Site'

    Given path '/health'
    And header Sec-Fetch-Site = 'same-origin'
    And header Sec-Fetch-Mode = 'cors'
    When method get
    Then status 200
    And match header Content-Security-Policy contains "frame-ancestors 'none'"

  Scenario: 22. Obligatoriedad de Idempotency-Key (422) y control RBAC/anti-IDOR (403) en pagos y egresos (Hito 17.3)
    * def uid = (java.util.UUID.randomUUID() + '').substring(0, 8)
    * def email = 'hito173.' + uid + '@condominio.com'
    Given path '/api/auth/register'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request
      """
      {
        "nombre": "Usuario BDD Hito 17.3",
        "cedula": "#('V-173' + uid)",
        "correo": "#(email)",
        "telefono": "+584145550030",
        "password": "Password123!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201

    Given path '/api/auth/login'
    And request { correo: "#(email)", password: "Password123!" }
    When method post
    Then status 200
    * def csrfTok = response.csrf_token

    # Aprobar pago y registrar egreso exigen cabecera Idempotency-Key -> 422 sin ella
    Given path '/api/pagos/1/aprobar'
    And header X-CSRF-Token = csrfTok
    When method put
    Then status 422
    And match response.detail[0].loc contains 'Idempotency-Key'

    Given path '/api/finanzas/egresos'
    And header X-CSRF-Token = csrfTok
    And request { periodo: "2026-10", categoria: "MANTENIMIENTO", descripcion: "Prueba BDD 17.3", monto: "25.00", moneda: "USD" }
    When method post
    Then status 422
    And match response.detail[0].loc contains 'Idempotency-Key'

    # Con Idempotency-Key + X-CSRF-Token válidos, usuario sin privilegios/contrato activo recibe 403
    Given path '/api/pagos/1/aprobar'
    And header X-CSRF-Token = csrfTok
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    When method put
    Then status 403

    Given path '/api/finanzas/egresos'
    And header X-CSRF-Token = csrfTok
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { periodo: "2026-10", categoria: "MANTENIMIENTO", descripcion: "Prueba BDD 17.3", monto: "25.00", moneda: "USD" }
    When method post
    Then status 403

    Given path '/api/pagos/reportar'
    And header X-CSRF-Token = csrfTok
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { recibo_id: 1, monto: "25.00", moneda: "USD", metodo_pago: "EFECTIVO" }
    When method post
    Then status 403

  Scenario: 23. Privacidad DTO en unidades públicas y contratos de cancelación de reservas (Hito 17.4)
    # 1. Endpoint público de unidades para registro no expone datos financieros privados
    Given path '/api/estructura/unidades'
    When method get
    Then status 200
    And match response == '#array'

    # 2. Contrato OpenAPI expone UnidadPublicaResponse sin campos financieros y registra /cancelar
    Given path '/openapi.json'
    When method get
    Then status 200
    * def publicSchema = response.components.schemas.UnidadPublicaResponse
    * def propKeys = karate.keysOf(publicSchema.properties)
    * match propKeys contains only ['id', 'identificador', 'estructura_id']
    * match response.paths['/api/reservas/{reserva_id}/cancelar'].put != null

    # 3. Verificación pública de solvencia inexistente retorna 404
    Given path '/api/finanzas/solvencia/verificar/SOLV-BDD174-NOEXISTE'
    And param sig = '0000'
    When method get
    Then status 404

    # 4. Usuario Fantasma aislado verifica 422 sin Idempotency-Key y 403 con Idempotency-Key en cancelación
    * def uid = (java.util.UUID.randomUUID() + '').substring(0, 8)
    * def email = 'hito174.' + uid + '@condominio.com'
    Given path '/api/auth/register'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request
      """
      {
        "nombre": "Usuario BDD Hito 17.4",
        "cedula": "#('V-174' + uid)",
        "correo": "#(email)",
        "telefono": "+584145550031",
        "password": "Password123!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201

    Given path '/api/auth/login'
    And request { correo: "#(email)", password: "Password123!" }
    When method post
    Then status 200
    * def csrfTok = response.csrf_token

    Given path '/api/reservas/1/cancelar'
    And header X-CSRF-Token = csrfTok
    When method put
    Then status 422
    And match response.detail[0].loc contains 'Idempotency-Key'

    Given path '/api/reservas/1/cancelar'
    And header X-CSRF-Token = csrfTok
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    When method put
    Then status 403

  Scenario: 24. Contrato productivo /health, ocultamiento de /metrics y RBAC de scheduler diario (Hito 18)
    # 1. Endpoint /health saludable con cabeceras OSHP y /metrics fuera de OpenAPI público
    Given path '/health'
    When method get
    Then status 200
    And match response.status == 'healthy'
    And match header X-Content-Type-Options == 'nosniff'
    And match header X-Frame-Options == 'DENY'
    And match header Content-Security-Policy contains "frame-ancestors 'none'"

    Given path '/openapi.json'
    When method get
    Then status 200
    * match response.paths['/api/tareas/generar-diarias'].post != null
    * match response.paths['/metrics'] == '#notpresent'

    # 2. Disparo manual del cronjob de tareas diarias exige autenticación y rol directiva
    Given path '/api/tareas/generar-diarias'
    When method post
    Then status 401

    * def uid = (java.util.UUID.randomUUID() + '').substring(0, 8)
    * def email = 'hito18.' + uid + '@condominio.com'
    Given path '/api/auth/register'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request
      """
      {
        "nombre": "Usuario BDD Hito 18",
        "cedula": "#('V-180' + uid)",
        "correo": "#(email)",
        "telefono": "+584145550088",
        "password": "Password123!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201

    Given path '/api/auth/login'
    And request { correo: "#(email)", password: "Password123!" }
    When method post
    Then status 200
    * def csrfTok = response.csrf_token

    Given path '/api/tareas/generar-diarias'
    And header X-CSRF-Token = csrfTok
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    When method post
    Then status 403

  Scenario: 25. Bootstrap Día 0 de Presidente inicial, generación de estructura y activación de residente Fantasma
    # 1. Login con el Presidente creado por python -m src.bootstrap --from-env
    Given path '/api/auth/login'
    And request { correo: 'presidente.bootstrap@condominio.test', password: 'fake-qa-bootstrap-123456!' }
    When method post
    Then status 200
    And match response.rol == 'PRESIDENTE'
    * def presCsrf = response.csrf_token

    Given path '/api/auth/me'
    When method get
    Then status 200
    And match response.correo == 'presidente.bootstrap@condominio.test'
    And match response.es_activo == true
    And match response.rol == 'PRESIDENTE'

    # 2. Presidente crea torre y unidad con Idempotency-Key dinámico
    * def uid = (java.util.UUID.randomUUID() + '').substring(0, 8)
    * def unidadIdent = 'D0-' + uid
    Given path '/api/estructura/generar'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { nombre: "#('Torre Día0 ' + uid)", tipo: 'TORRE', identificadores: ["#('' + unidadIdent)"] }
    When method post
    Then status 201
    And match response.unidades_creadas == 1
    * def unidadId = response.unidades[0].id

    # 3. Nuevo vecino se registra como Fantasma en la unidad creada
    * def vecinoEmail = 'vecino.dia0.' + uid + '@condominio.test'
    * def vecinoCedula = 'V-25' + uid
    Given path '/api/auth/register'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request
      """
      {
        "nombre": "Vecino Día Cero",
        "cedula": "#(vecinoCedula)",
        "correo": "#(vecinoEmail)",
        "telefono": "+584145550025",
        "password": "fake-qa-vecino-123456!",
        "unidad_solicitada_id": #(unidadId),
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201
    And match response.es_activo == false
    And match response.rol == 'FANTASMA'
    * def vecinoId = response.id

    # 4. Presidente aprueba al Usuario Fantasma y lo asigna como PROPIETARIO activo
    Given path '/api/usuarios/' + vecinoId + '/asignar'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { unidad_id: #(unidadId), tipo_ocupante: 'PROPIETARIO', rol: 'PROPIETARIO' }
    When method put
    Then status 200
    And match response.es_activo == true
    And match response.rol == 'PROPIETARIO'

    # 5. El vecino recién activado inicia sesión y accede al resumen financiero (HTTP 200)
    Given path '/api/auth/login'
    And request { correo: "#(vecinoEmail)", password: 'fake-qa-vecino-123456!' }
    When method post
    Then status 200
    And match response.rol == 'PROPIETARIO'

    Given path '/api/finanzas/resumen'
    When method get
    Then status 200

  # ==============================================================================
  # Grupo 12: Verificación de Contratos Operativos Día 1 tras Hito 19
  # ==============================================================================

  Scenario: 26. Rechazo 401/403 aislado de endpoints operativos sin credenciales válidas (Hito 19)
    * def ghostEmail = 'hito19.fantasma.' + java.util.UUID.randomUUID() + '@test.com'
    * def ghostCedula = 'V-' + ('' + java.lang.System.nanoTime()).substring(0, 8)
    * def regKey = 'hito19-reg-' + java.util.UUID.randomUUID()

    Given path '/api/auth/register'
    And header Idempotency-Key = regKey
    And request
      """
      {
        "nombre": "Residente Hito 19",
        "cedula": "#(ghostCedula)",
        "correo": "#(ghostEmail)",
        "telefono": "+584141190019",
        "password": "fake-qa-hito19-123456!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201
    And match response.es_activo == false

    Given path '/api/auth/login'
    And request { correo: "#(ghostEmail)", password: 'fake-qa-hito19-123456!' }
    When method post
    Then status 200

    Given path '/api/tareas/diarias'
    When method get
    Then status 403

  Scenario: 27. Blindaje Hito 20: bloqueo de escalación Vicepresidente->Presidente y ocultación horizontal en unidades
    # 1. Login con Presidente bootstrap
    Given path '/api/auth/login'
    And request { correo: 'presidente.bootstrap@condominio.test', password: 'fake-qa-bootstrap-123456!' }
    When method post
    Then status 200
    * def presCsrf = response.csrf_token

    # 2. Registrar dos usuarios aislados por UUID (futuro VICEPRESIDENTE y objetivo FANTASMA)
    * def uid = (java.util.UUID.randomUUID() + '').substring(0, 8)
    * def vpEmail = 'vp.h20.' + uid + '@condominio.test'
    * def vpCedula = 'V-201' + uid
    Given path '/api/auth/register'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request
      """
      {
        "nombre": "Vicepresidente H20",
        "cedula": "#(vpCedula)",
        "correo": "#(vpEmail)",
        "telefono": "+584145550201",
        "password": "fake-qa-vp-h20-123456!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201
    * def vpId = response.id

    * def objEmail = 'obj.h20.' + uid + '@condominio.test'
    * def objCedula = 'V-202' + uid
    Given path '/api/auth/register'
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request
      """
      {
        "nombre": "Objetivo H20",
        "cedula": "#(objCedula)",
        "correo": "#(objEmail)",
        "telefono": "+584145550202",
        "password": "fake-qa-obj-h20-123456!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201
    * def objId = response.id

    # 3. Presidente activa al VICEPRESIDENTE y luego activa al objetivo como PROPIETARIO
    Given path '/api/usuarios/' + vpId + '/asignar'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { unidad_id: 1, tipo_ocupante: 'PROPIETARIO', rol: 'VICEPRESIDENTE' }
    When method put
    Then status 200
    And match response.rol == 'VICEPRESIDENTE'

    Given path '/api/usuarios/' + objId + '/asignar'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { unidad_id: 1, tipo_ocupante: 'PROPIETARIO', rol: 'PROPIETARIO' }
    When method put
    Then status 200

    # 4. VICEPRESIDENTE intenta promover a objetivo (o a sí mismo) a PRESIDENTE -> 403 Forbidden
    Given path '/api/auth/login'
    And request { correo: "#(vpEmail)", password: 'fake-qa-vp-h20-123456!' }
    When method post
    Then status 200
    * def vpCsrf = response.csrf_token

    Given path '/api/usuarios/' + objId + '/asignar'
    And header X-CSRF-Token = vpCsrf
    And header Idempotency-Key = java.util.UUID.randomUUID() + ''
    And request { unidad_id: 1, tipo_ocupante: 'PROPIETARIO', rol: 'PRESIDENTE' }
    When method put
    Then status 403

    # 5. Propietario consulta /api/estructura/unidades y NO recibe campos financieros de terceros
    Given path '/api/auth/login'
    And request { correo: "#(objEmail)", password: 'fake-qa-obj-h20-123456!' }
    When method post
    Then status 200

    Given path '/api/estructura/unidades'
    When method get
    Then status 200
    And match response[0].alicuota == '#notpresent'
    And match response[0].credito_disponible_usd == '#notpresent'

  # ==============================================================================
  # Grupo 14: Exactitud Contable LPH, Idempotencia con Replay y Evidencias (Hito 21)
  # ==============================================================================

  Scenario: 28. Idempotencia con replay 2xx (X-Idempotency-Replayed), conflicto por body y liberación en error 4xx (Hito 21)
    Given path '/api/auth/login'
    And request { correo: 'presidente.bootstrap@condominio.test', password: 'fake-qa-bootstrap-123456!' }
    When method post
    Then status 200
    * def presCsrf = response.csrf_token

    * def tasaKey = 'tasa-replay-' + java.util.UUID.randomUUID()
    Given path '/api/finanzas/tasa'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = tasaKey
    And request { fecha: '2099-01-15', tasa_usd_ves: '41.2500' }
    When method post
    Then status 201
    * def firstBody = response

    # Reintento con misma clave y mismo cuerpo -> Replay 201 + X-Idempotency-Replayed: true
    Given path '/api/finanzas/tasa'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = tasaKey
    And request { fecha: '2099-01-15', tasa_usd_ves: '41.2500' }
    When method post
    Then status 201
    And match header X-Idempotency-Replayed == 'true'
    And match response == firstBody

    # Reintento con misma clave y cuerpo distinto -> 409 Conflict
    Given path '/api/finanzas/tasa'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = tasaKey
    And request { fecha: '2099-01-15', tasa_usd_ves: '42.0000' }
    When method post
    Then status 409

    # Error 400 libera la Idempotency-Key para permitir reintento exitoso posterior
    * def retryKey = 'cons-retry-' + java.util.UUID.randomUUID()
    Given path '/api/consultas'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = retryKey
    And request
      """
      {
        "titulo": "Consulta Fallida H21",
        "descripcion_legal": "Prueba de liberación en error 400",
        "tipo_consulta": "CARTA_CONSULTA_1RA",
        "regla_quorum": "DOS_TERCIOS",
        "fecha_cierre": "2020-01-01T00:00:00Z",
        "opciones": [
          { "etiqueta": "Aprobar", "es_opcion_aprobatoria": true },
          { "etiqueta": "Rechazar", "es_opcion_aprobatoria": false }
        ]
      }
      """
    When method post
    Then status 400

    Given path '/api/consultas'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = retryKey
    And request
      """
      {
        "titulo": "Consulta Corregida H21",
        "descripcion_legal": "Prueba de reintento tras liberación",
        "tipo_consulta": "CARTA_CONSULTA_1RA",
        "regla_quorum": "DOS_TERCIOS",
        "fecha_cierre": "2099-12-31T23:59:00Z",
        "opciones": [
          { "etiqueta": "Aprobar", "es_opcion_aprobatoria": true },
          { "etiqueta": "Rechazar", "es_opcion_aprobatoria": false }
        ]
      }
      """
    When method post
    Then status 201

  Scenario: 29. Subida segura /api/evidencias/subir acepta PNG (202 ENCOLADO) y rechaza binario EXE (415) (Hito 21)
    Given path '/api/auth/login'
    And request { correo: 'presidente.bootstrap@condominio.test', password: 'fake-qa-bootstrap-123456!' }
    When method post
    Then status 200
    * def presCsrf = response.csrf_token

    * configure headers = null
    * def pngBytes = java.util.Base64.getDecoder().decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
    * def exeBytes = java.util.Base64.getDecoder().decode('TVqQAAMAAAA=')

    Given path '/api/evidencias/subir'
    And param categoria = 'comprobantes'
    And header Content-Type = 'application/octet-stream'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'evid-ok-' + java.util.UUID.randomUUID()
    And request pngBytes
    When method post
    Then status 202
    And match response.estado == 'ENCOLADO'
    And match response.formato_destino == 'image/avif'

    Given path '/api/evidencias/subir'
    And param categoria = 'comprobantes'
    And header Content-Type = 'application/octet-stream'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'evid-exe-' + java.util.UUID.randomUUID()
    And request exeBytes
    When method post
    Then status 415

  @parallel=false
  Scenario: 30. Fusión UPSERT Reserva Área Social + Facturar Periodo y bloqueo de Cierre Mensual con pago EN_REVISION (Hito 21)
    Given path '/api/auth/login'
    And request { correo: 'presidente.bootstrap@condominio.test', password: 'fake-qa-bootstrap-123456!' }
    When method post
    Then status 200
    * def presCsrf = response.csrf_token

    # Asegura tasa de cambio del día para reporte de pagos
    Given path '/api/finanzas/tasa'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h21-tasa-' + java.util.UUID.randomUUID()
    And request { tasa_usd_ves: '42.0000' }
    When method post
    Then status 201

    * def uid = (java.util.UUID.randomUUID() + '').substring(0, 8)
    * def unidadIdent = 'H21-' + uid
    Given path '/api/estructura/generar'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h21-est-' + java.util.UUID.randomUUID()
    And request { nombre: "#('Torre H21 ' + uid)", tipo: 'TORRE', identificadores: ["#('' + unidadIdent)"] }
    When method post
    Then status 201
    * def unidadId = response.unidades[0].id

    # Registrar y activar propietario aislado sobre unidadId
    * def propEmail = 'prop.h21.' + uid + '@condominio.test'
    * def propCedula = 'V-21' + uid
    Given path '/api/auth/register'
    And header Idempotency-Key = 'h21-reg-' + java.util.UUID.randomUUID()
    And request
      """
      {
        "nombre": "Propietario H21",
        "cedula": "#(propCedula)",
        "correo": "#(propEmail)",
        "telefono": "+584145552100",
        "password": "fake-qa-h21-123456!",
        "unidad_solicitada_id": #(unidadId),
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201
    * def propId = response.id

    Given path '/api/usuarios/' + propId + '/asignar'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h21-asg-' + java.util.UUID.randomUUID()
    And request { unidad_id: #(unidadId), tipo_ocupante: 'PROPIETARIO', rol: 'PROPIETARIO' }
    When method put
    Then status 200

    # Crear área social con costo de uso $15.00 y reservar en 2097-06-15 -> genera recibo preliminar 2097-06
    Given path '/api/reservas/areas'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h21-area-' + java.util.UUID.randomUUID()
    And request { nombre: "#('Salón H21 ' + uid)", aforo_maximo: 25, costo_uso_usd: '15.00', deposito_garantia_usd: '0.00', requiere_solvencia_estricta: false }
    When method post
    Then status 201
    * def areaId = response.id

    Given path '/api/reservas/solicitar'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h21-res-' + java.util.UUID.randomUUID()
    And request { area_id: #(areaId), unidad_id: #(unidadId), fecha_evento: '2097-06-15', motivo_evento: 'Asamblea y brindis H21' }
    When method post
    Then status 201

    # Facturar periodo 2097-06 (PARTES_IGUALES) debe fusionar vía UPSERT sin chocar con el recibo preliminar
    Given path '/api/finanzas/facturar-periodo'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h21-fact-' + java.util.UUID.randomUUID()
    And request { periodo: '2097-06', modalidad: 'PARTES_IGUALES', incluir_fondo_reserva: false, cuota_extraordinaria_total_usd: '20.00' }
    When method post
    Then status 201

    # Propietario consulta su recibo 2097-06 y reporta pago EN_REVISION
    Given path '/api/auth/login'
    And request { correo: "#(propEmail)", password: 'fake-qa-h21-123456!' }
    When method post
    Then status 200
    * def propCsrf = response.csrf_token

    Given path '/api/finanzas/resumen'
    And param periodo = '2097-06'
    When method get
    Then status 200
    * def recibosProp = karate.filter(response.estado_cobranza, function(x){ return x.unidad_id == unidadId })
    * def reciboId = recibosProp[0].recibo_id

    Given path '/api/pagos/reportar'
    And header X-CSRF-Token = propCsrf
    And header Idempotency-Key = 'h21-pag-' + java.util.UUID.randomUUID()
    And request { recibo_id: #(reciboId), monto: '5.00', moneda: 'USD', metodo_pago: 'ZELLE', numero_referencia: "#('REF-H21-' + uid)" }
    When method post
    Then status 201
    And match response.estado == 'EN_REVISION'
    * def pagoId = response.id

    # Presidente intenta cierre mensual 2097-06 -> 409 bloqueado por pago EN_REVISION
    Given path '/api/auth/login'
    And request { correo: 'presidente.bootstrap@condominio.test', password: 'fake-qa-bootstrap-123456!' }
    When method post
    Then status 200
    * def presCsrf2 = response.csrf_token

    Given path '/api/finanzas/cierre-mensual'
    And header X-CSRF-Token = presCsrf2
    And header Idempotency-Key = 'h21-cierre-blq-' + java.util.UUID.randomUUID()
    And request { periodo: '2097-06' }
    When method post
    Then status 409
    And match response.detail contains 'revisión'

    # Limpieza obligatoria: rechazar pago EN_REVISION y cerrar periodo 2097-06 -> 200
    Given path '/api/pagos/' + pagoId + '/rechazar'
    And header X-CSRF-Token = presCsrf2
    And header Idempotency-Key = 'h21-rech-' + java.util.UUID.randomUUID()
    And request { motivo: 'Limpieza controlada de escenario BDD Hito 21' }
    When method put
    Then status 200

    Given path '/api/finanzas/cierre-mensual'
    And header X-CSRF-Token = presCsrf2
    And header Idempotency-Key = 'h21-cierre-ok-' + java.util.UUID.randomUUID()
    And request { periodo: '2097-06' }
    When method post
    Then status 200
    And match response.estado == 'CERRADO'

  # ==============================================================================
  # Grupo 13: Flujos Nominales 2xx Aislados por UUID de los 9 Routers (Hito 23.1)
  # ==============================================================================

  @parallel=false
  Scenario: 31. Flujos nominales 2xx de Finanzas, Pagos y Administración (fondos, egresos, solvencia, alícuota y aprobación)
    Given path '/api/auth/login'
    And request { correo: 'presidente.bootstrap@condominio.test', password: 'fake-qa-bootstrap-123456!' }
    When method post
    Then status 200
    * def presCsrf = response.csrf_token

    Given path '/api/usuarios/pendientes'
    When method get
    Then status 200
    And match response == '#[]'

    * def uid = (java.util.UUID.randomUUID() + '').substring(0, 8)
    Given path '/api/estructura/generar'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h23-f-est-' + java.util.UUID.randomUUID()
    And request { nombre: "#('Torre F31 ' + uid)", tipo: 'TORRE', identificadores: ["#('F31-' + uid)"] }
    When method post
    Then status 201
    * def unidadId = response.unidades[0].id

    Given path '/api/estructura/unidades/' + unidadId + '/alicuota'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h23-f-ali-' + java.util.UUID.randomUUID()
    And request { alicuota: '12.5000' }
    When method put
    Then status 200

    Given path '/api/finanzas/tasa'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h23-f-tasa-' + java.util.UUID.randomUUID()
    And request { tasa_usd_ves: '44.5000' }
    When method post
    Then status 201

    Given path '/api/finanzas/tasa'
    When method get
    Then status 200

    Given path '/api/finanzas/fondos'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h23-f-fondo-' + java.util.UUID.randomUUID()
    And request { nombre: "#('Fondo Especial ' + uid)", tipo: 'ESPECIAL', porcentaje_recargo: '5.00' }
    When method post
    Then status 201

    Given path '/api/finanzas/fondos'
    When method get
    Then status 200
    And match response == '#[]'

    * def propEmail = 'prop.f31.' + uid + '@condominio.test'
    Given path '/api/auth/register'
    And header Idempotency-Key = 'h23-f-reg-' + java.util.UUID.randomUUID()
    And request
      """
      {
        "nombre": "Propietario Finanzas 31",
        "cedula": "#('V-31' + uid)",
        "correo": "#(propEmail)",
        "telefono": "+584145553100",
        "password": "fake-qa-f31-123456!",
        "unidad_solicitada_id": #(unidadId),
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201
    * def propId = response.id

    Given path '/api/usuarios/' + propId + '/asignar'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h23-f-asg-' + java.util.UUID.randomUUID()
    And request { unidad_id: #(unidadId), tipo_ocupante: 'PROPIETARIO', rol: 'PROPIETARIO' }
    When method put
    Then status 200

    # Emisión y verificación pública de Certificado de Solvencia con deuda $0.00 antes de facturar 2091-03
    Given path '/api/auth/login'
    And request { correo: "#(propEmail)", password: 'fake-qa-f31-123456!' }
    When method post
    Then status 200
    * def propCsrf = response.csrf_token

    Given path '/api/finanzas/solvencia/' + unidadId
    And header X-CSRF-Token = propCsrf
    And header Idempotency-Key = 'h23-f-solv-' + java.util.UUID.randomUUID()
    When method post
    Then status 201
    * def solvFolio = response.folio
    * def solvSig = response.firma_hmac

    Given path '/api/finanzas/solvencia/verificar/' + solvFolio
    And param sig = solvSig
    When method get
    Then status 200
    And match response.valido == true
    And match response.vigente == true

    # Egreso y facturación de periodo futuro aislado 2091-03 + reporte y aprobación de pago
    Given path '/api/auth/login'
    And request { correo: 'presidente.bootstrap@condominio.test', password: 'fake-qa-bootstrap-123456!' }
    When method post
    Then status 200
    * def presCsrf2 = response.csrf_token

    Given path '/api/finanzas/egresos'
    And header X-CSRF-Token = presCsrf2
    And header Idempotency-Key = 'h23-f-egr-' + java.util.UUID.randomUUID()
    And request { periodo: '2091-03', categoria: 'MANTENIMIENTO', descripcion: "#('Bomba agua ' + uid)", monto: '20.00', moneda: 'USD', es_gasto_comun: true }
    When method post
    Then status 201

    Given path '/api/finanzas/facturar-periodo'
    And header X-CSRF-Token = presCsrf2
    And header Idempotency-Key = 'h23-f-fact-' + java.util.UUID.randomUUID()
    And request { periodo: '2091-03', modalidad: 'PARTES_IGUALES', incluir_fondo_reserva: false, cuota_extraordinaria_total_usd: '0.00' }
    When method post
    Then status 201

    Given path '/api/auth/login'
    And request { correo: "#(propEmail)", password: 'fake-qa-f31-123456!' }
    When method post
    Then status 200
    * def propCsrf2 = response.csrf_token

    Given path '/api/finanzas/resumen'
    And param periodo = '2091-03'
    When method get
    Then status 200
    * def recs = karate.filter(response.estado_cobranza, function(x){ return x.unidad_id == unidadId })
    * def reciboId = recs[0].recibo_id
    * def montoPagar = recs[0].monto_usd

    Given path '/api/finanzas/recibos/' + reciboId + '/desglose'
    When method get
    Then status 200
    And match response.recibo_id == reciboId

    Given path '/api/pagos/reportar'
    And header X-CSRF-Token = propCsrf2
    And header Idempotency-Key = 'h23-f-pag-' + java.util.UUID.randomUUID()
    And request { recibo_id: #(reciboId), monto: #(montoPagar), moneda: 'USD', metodo_pago: 'TRANSFERENCIA', numero_referencia: "#('REF31-' + uid)" }
    When method post
    Then status 201
    * def pagoId = response.id

    Given path '/api/auth/login'
    And request { correo: 'presidente.bootstrap@condominio.test', password: 'fake-qa-bootstrap-123456!' }
    When method post
    Then status 200
    * def presCsrf3 = response.csrf_token

    Given path '/api/pagos/revision'
    When method get
    Then status 200
    * def pagosVisibles = karate.filter(response, function(x){ return x.id == pagoId })
    And match pagosVisibles == '#[1]'

    Given path '/api/pagos/' + pagoId + '/aprobar'
    And header X-CSRF-Token = presCsrf3
    And header Idempotency-Key = 'h23-f-apr-' + java.util.UUID.randomUUID()
    When method put
    Then status 200
    And match response.estado == 'APROBADO'

    Given path '/api/finanzas/cierre-mensual'
    And header X-CSRF-Token = presCsrf3
    And header Idempotency-Key = 'h23-f-cie-' + java.util.UUID.randomUUID()
    And request { periodo: '2091-03' }
    When method post
    Then status 200
    And match response.estado == 'CERRADO'

  Scenario: 32. Flujos nominales 2xx de Consultas LPH y Reservas de Áreas Sociales (votar, cerrar, listar, cancelar e inspeccionar)
    Given path '/api/auth/login'
    And request { correo: 'presidente.bootstrap@condominio.test', password: 'fake-qa-bootstrap-123456!' }
    When method post
    Then status 200
    * def presCsrf = response.csrf_token

    * def uid = (java.util.UUID.randomUUID() + '').substring(0, 8)
    Given path '/api/estructura/generar'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h23-cr-est-' + java.util.UUID.randomUUID()
    And request { nombre: "#('Torre CR32 ' + uid)", tipo: 'TORRE', identificadores: ["#('CR32-' + uid)"] }
    When method post
    Then status 201
    * def unidadId = response.unidades[0].id

    * def propEmail = 'prop.cr32.' + uid + '@condominio.test'
    Given path '/api/auth/register'
    And header Idempotency-Key = 'h23-cr-reg-' + java.util.UUID.randomUUID()
    And request
      """
      {
        "nombre": "Copropietario Consultas 32",
        "cedula": "#('V-32' + uid)",
        "correo": "#(propEmail)",
        "telefono": "+584145553200",
        "password": "fake-qa-c32-123456!",
        "unidad_solicitada_id": #(unidadId),
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201
    * def propId = response.id

    Given path '/api/usuarios/' + propId + '/asignar'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h23-cr-asg-' + java.util.UUID.randomUUID()
    And request { unidad_id: #(unidadId), tipo_ocupante: 'PROPIETARIO', rol: 'PROPIETARIO' }
    When method put
    Then status 200

    Given path '/api/estructura/unidades/' + unidadId + '/alicuota'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h23-cr-ali-' + java.util.UUID.randomUUID()
    And request { alicuota: '100.0000' }
    When method put
    Then status 200

    Given path '/api/consultas'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h23-cr-con-' + java.util.UUID.randomUUID()
    And request
      """
      {
        "titulo": "#('Consulta Pintura ' + uid)",
        "descripcion_legal": "Aprobación nominal LPH Art. 23 aislada por UUID.",
        "tipo_consulta": "CARTA_CONSULTA_1RA",
        "regla_quorum": "DOS_TERCIOS",
        "fecha_cierre": "2099-12-31T23:59:59Z",
        "opciones": [
          { "etiqueta": "Sí, aprobar", "es_opcion_aprobatoria": true },
          { "etiqueta": "No aprobar", "es_opcion_aprobatoria": false }
        ]
      }
      """
    When method post
    Then status 201
    * def consultaId = response.id
    * def opcionId = response.opciones[0].id

    Given path '/api/reservas/areas'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h23-cr-area-' + java.util.UUID.randomUUID()
    And request { nombre: "#('Salón Nominal ' + uid)", aforo_maximo: 30, costo_uso_usd: '0.00', deposito_garantia_usd: '0.00', requiere_solvencia_estricta: false }
    When method post
    Then status 201
    * def areaId = response.id

    Given path '/api/auth/login'
    And request { correo: "#(propEmail)", password: 'fake-qa-c32-123456!' }
    When method post
    Then status 200
    * def propCsrf = response.csrf_token

    Given path '/api/consultas'
    When method get
    Then status 200
    And match response == '#[]'

    Given path '/api/consultas/' + consultaId
    When method get
    Then status 200
    And match response.id == consultaId

    Given path '/api/consultas/' + consultaId + '/votar'
    And header X-CSRF-Token = propCsrf
    And header Idempotency-Key = 'h23-cr-vot-' + java.util.UUID.randomUUID()
    And request { unidad_id: #(unidadId), opcion_id: #(opcionId) }
    When method post
    Then status 201
    And match response.firma_hmac == '#string'

    Given path '/api/reservas/areas'
    When method get
    Then status 200

    Given path '/api/reservas/solicitar'
    And header X-CSRF-Token = propCsrf
    And header Idempotency-Key = 'h23-cr-r1-' + java.util.UUID.randomUUID()
    And request { area_id: #(areaId), unidad_id: #(unidadId), fecha_evento: '2098-04-10', motivo_evento: 'Cumpleaños vecinal 32' }
    When method post
    Then status 201
    * def reservaId1 = response.id

    Given path '/api/reservas/solicitar'
    And header X-CSRF-Token = propCsrf
    And header Idempotency-Key = 'h23-cr-r2-' + java.util.UUID.randomUUID()
    And request { area_id: #(areaId), unidad_id: #(unidadId), fecha_evento: '2098-04-11', motivo_evento: 'Reunión educativa 32' }
    When method post
    Then status 201
    * def reservaId2 = response.id

    Given path '/api/reservas'
    When method get
    Then status 200

    Given path '/api/reservas/' + reservaId2 + '/cancelar'
    And header X-CSRF-Token = propCsrf
    And header Idempotency-Key = 'h23-cr-canc-' + java.util.UUID.randomUUID()
    When method put
    Then status 200
    And match response.estado == 'CANCELADA'

    Given path '/api/auth/login'
    And request { correo: 'presidente.bootstrap@condominio.test', password: 'fake-qa-bootstrap-123456!' }
    When method post
    Then status 200
    * def presCsrf2 = response.csrf_token

    Given path '/api/reservas/' + reservaId1 + '/inspeccionar'
    And header X-CSRF-Token = presCsrf2
    And header Idempotency-Key = 'h23-cr-insp-' + java.util.UUID.randomUUID()
    And request { estado: 'FINALIZADA_SIN_DANOS', observaciones_inspeccion: 'Salón entregado limpio sin novedades' }
    When method put
    Then status 200
    And match response.estado == 'FINALIZADA_SIN_DANOS'

    Given path '/api/consultas/' + consultaId + '/cerrar'
    And header X-CSRF-Token = presCsrf2
    And header Idempotency-Key = 'h23-cr-cls-' + java.util.UUID.randomUUID()
    When method post
    Then status 200

  Scenario: 33. Flujos nominales 2xx de Incidencias, Operaciones, Accesos QR, Paquetería y Cargos de Junta
    Given path '/api/auth/login'
    And request { correo: 'presidente.bootstrap@condominio.test', password: 'fake-qa-bootstrap-123456!' }
    When method post
    Then status 200
    * def presCsrf = response.csrf_token

    * def uid = (java.util.UUID.randomUUID() + '').substring(0, 8)
    Given path '/api/estructura/generar'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h23-oa-est-' + java.util.UUID.randomUUID()
    And request { nombre: "#('Torre OA33 ' + uid)", tipo: 'TORRE', identificadores: ["#('OA33-' + uid)"] }
    When method post
    Then status 201
    * def unidadId = response.unidades[0].id

    * def propEmail = 'prop.oa33.' + uid + '@condominio.test'
    Given path '/api/auth/register'
    And header Idempotency-Key = 'h23-oa-regp-' + java.util.UUID.randomUUID()
    And request
      """
      {
        "nombre": "Propietario OA33",
        "cedula": "#('V-33A' + uid.substring(0, 5))",
        "correo": "#(propEmail)",
        "telefono": "+584145553301",
        "password": "fake-qa-oa33-123456!",
        "unidad_solicitada_id": #(unidadId),
        "tipo_ocupante_solicitado": "PROPIETARIO"
      }
      """
    When method post
    Then status 201
    * def propId = response.id

    Given path '/api/usuarios/' + propId + '/asignar'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h23-oa-asgp-' + java.util.UUID.randomUUID()
    And request { unidad_id: #(unidadId), tipo_ocupante: 'PROPIETARIO', rol: 'PROPIETARIO' }
    When method put
    Then status 200

    * def consEmail = 'cons.oa33.' + uid + '@condominio.test'
    Given path '/api/auth/register'
    And header Idempotency-Key = 'h23-oa-regc-' + java.util.UUID.randomUUID()
    And request
      """
      {
        "nombre": "Conserje OA33",
        "cedula": "#('V-33B' + uid.substring(0, 5))",
        "correo": "#(consEmail)",
        "telefono": "+584145553302",
        "password": "fake-qa-co33-123456!",
        "unidad_solicitada_id": #(unidadId),
        "tipo_ocupante_solicitado": "INQUILINO"
      }
      """
    When method post
    Then status 201
    * def consId = response.id

    Given path '/api/usuarios/' + consId + '/asignar'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h23-oa-asgc-' + java.util.UUID.randomUUID()
    And request { unidad_id: #(unidadId), tipo_ocupante: 'INQUILINO', rol: 'CONSERJE' }
    When method put
    Then status 200

    # Promoción de Junta y operaciones administrativas del Presidente
    Given path '/api/junta/cargos'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h23-oa-junta-' + java.util.UUID.randomUUID()
    And request { usuario_id: #(propId), cargo: 'SECRETARIO' }
    When method put
    Then status 200
    And match response.rol == 'SECRETARIO'

    Given path '/api/tareas/plantillas'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h23-oa-tpl-' + java.util.UUID.randomUUID()
    And request { titulo: "#('Ronda Garita ' + uid)", area: 'Garita', frecuencia: 'DIARIA' }
    When method post
    Then status 201

    Given path '/api/tareas/generar-diarias'
    And header X-CSRF-Token = presCsrf
    When method post
    Then status 200

    Given path '/api/tareas/diarias'
    And header X-CSRF-Token = presCsrf
    And header Idempotency-Key = 'h23-oa-td-' + java.util.UUID.randomUUID()
    And request { titulo: "#('Revisión Bombas ' + uid)", area: 'Sótano' }
    When method post
    Then status 201

    Given path '/api/tareas/diarias'
    When method get
    Then status 200

    Given path '/api/voceros/galeria'
    When method get
    Then status 200

    # Secretario asienta acta en Bitácora, emite Comunicado y reporta Incidencia
    Given path '/api/auth/login'
    And request { correo: "#(propEmail)", password: 'fake-qa-oa33-123456!' }
    When method post
    Then status 200
    * def secCsrf = response.csrf_token

    Given path '/api/bitacora/acta'
    And header X-CSRF-Token = secCsrf
    And header Idempotency-Key = 'h23-oa-acta-' + java.util.UUID.randomUUID()
    And request { fecha: '2026-11-18', hora: '19:30', ubicacion: "#('Salón ' + uid)", contenido: 'Verificación periódica de convivencia y mantenimiento.' }
    When method post
    Then status 201

    Given path '/api/bitacora/historial'
    When method get
    Then status 200

    Given path '/api/comunicados'
    And header X-CSRF-Token = secCsrf
    And header Idempotency-Key = 'h23-oa-com-' + java.util.UUID.randomUUID()
    And request { titulo: "#('Aviso General ' + uid)", contenido: 'Corte programado de agua de 09:00 a 11:00 AM por limpieza.' }
    When method post
    Then status 201

    Given path '/api/comunicados/recientes'
    When method get
    Then status 200

    Given path '/api/incidencias/crear'
    And header X-CSRF-Token = secCsrf
    And header Idempotency-Key = 'h23-oa-inc-' + java.util.UUID.randomUUID()
    And request { area: "#('Ascensor ' + uid)", descripcion: 'Luminaria intermitente en cabina principal' }
    When method post
    Then status 201
    * def incidenciaId = response.id

    Given path '/api/incidencias/abiertas'
    When method get
    Then status 200

    # Pases QR de visita (emisión + listado + revocación del segundo pase)
    Given path '/api/accesos/pases'
    And header X-CSRF-Token = secCsrf
    And header Idempotency-Key = 'h23-oa-p1-' + java.util.UUID.randomUUID()
    And request { unidad_id: #(unidadId), nombre_visitante: 'Visitante Nominal', cedula_visitante: 'V-33112233', modalidad: 'UNICO_USO' }
    When method post
    Then status 201
    * def qrToken = response.qr_token

    Given path '/api/accesos/pases'
    And header X-CSRF-Token = secCsrf
    And header Idempotency-Key = 'h23-oa-p2-' + java.util.UUID.randomUUID()
    And request { unidad_id: #(unidadId), nombre_visitante: 'Visitante Revocable', cedula_visitante: 'V-33112244', modalidad: 'VENTANA_TEMPORAL' }
    When method post
    Then status 201
    * def paseRevId = response.id

    Given path '/api/accesos/pases/mios'
    When method get
    Then status 200

    Given path '/api/accesos/pases/' + paseRevId
    And header X-CSRF-Token = secCsrf
    When method delete
    Then status 200

    # Conserje se adhiere a incidencia, valida QR en garita, registra y lista paquetería
    Given path '/api/auth/login'
    And request { correo: "#(consEmail)", password: 'fake-qa-co33-123456!' }
    When method post
    Then status 200
    * def consCsrf = response.csrf_token

    Given path '/api/incidencias/' + incidenciaId + '/adherir'
    And header X-CSRF-Token = consCsrf
    And header Idempotency-Key = 'h23-oa-adh-' + java.util.UUID.randomUUID()
    When method post
    Then status 200
    And match response.adhesiones_count == 2

    Given path '/api/accesos/verificar-qr'
    And header X-CSRF-Token = consCsrf
    And header Idempotency-Key = 'h23-oa-vqr-' + java.util.UUID.randomUUID()
    And request { qr_token: #(qrToken) }
    When method post
    Then status 200
    And match response.autorizado == true

    Given path '/api/paqueteria/registrar'
    And header X-CSRF-Token = consCsrf
    And header Idempotency-Key = 'h23-oa-paq-' + java.util.UUID.randomUUID()
    And request { unidad_id: #(unidadId), empresa_envio: 'MRW', descripcion: "#('Sobre certificado ' + uid)" }
    When method post
    Then status 201
    * def paqueteId = response.id

    Given path '/api/paqueteria'
    When method get
    Then status 200

    Given path '/api/paqueteria/' + paqueteId + '/entregar'
    And header X-CSRF-Token = consCsrf
    And header Idempotency-Key = 'h23-oa-ent-' + java.util.UUID.randomUUID()
    When method put
    Then status 200
    And match response.estado == 'ENTREGADO'







