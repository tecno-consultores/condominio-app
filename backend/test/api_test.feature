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

