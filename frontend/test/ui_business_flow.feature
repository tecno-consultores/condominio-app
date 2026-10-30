# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors

Feature: Cobertura Funcional y Flujos BDD de Identidad, Finanzas, Operaciones, Administración, Facturación LPH, Gobernanza Digital y Accesos QR / Paquetería (Hitos 5, 6, 7, 10, 11 y 12)

  Background:
    * configure driver = { type: 'chrome', headless: true, addOptions: ['--no-sandbox', '--disable-dev-shm-usage'] }
    * def envBaseUrl = java.lang.System.getenv('UI_BASE_URL')
    * def baseUrl = karate.properties['UI_BASE_URL'] || envBaseUrl || 'http://ui-prod:80'

  Scenario: 1. El residente navega a /login, valida campos obligatorios y alterna visibilidad de contraseña
    Given driver baseUrl + '/login'
    And waitFor('#login-correo')
    And waitFor('#login-password')
    When click('#btn-login-submit')
    Then waitFor('.banner--error')
    When input('#login-correo', 'vecino@condominio.test')
    And input('#login-password', 'Password123!')
    And click('#btn-toggle-password')
    Then match attribute('#login-password', 'type') == 'text'

  Scenario: 2. El nuevo residente navega a /register y verifica el formulario de solicitud con selector de unidad
    Given driver baseUrl + '/register'
    And waitFor('#reg-nombre')
    And waitFor('#reg-cedula')
    And waitFor('#reg-correo')
    And waitFor('#reg-telefono')
    And waitFor('#reg-password')
    And waitFor('#reg-unidad')
    And waitFor('#reg-tipo-ocupante')
    When click('#btn-register-submit')
    Then waitFor('.banner--error')

  Scenario: 3. Redirección automática de rutas protegidas financieras (/dashboard, /finanzas/reportar-pago, /tesoreria/pagos, /tesoreria/cierre) hacia /login sin sesión
    Given driver baseUrl + '/dashboard'
    Then waitFor('#login-form')
    Given driver baseUrl + '/finanzas/reportar-pago'
    Then waitFor('#login-form')
    Given driver baseUrl + '/tesoreria/pagos'
    Then waitFor('#login-form')
    Given driver baseUrl + '/tesoreria/cierre'
    Then waitFor('#login-form')

  Scenario: 4. Redirección automática de rutas operativas y administrativas de Hito 7 (/incidencias, /operaciones/tareas, /voceros/galeria, /secretaria/bitacora, /admin/estructura, /admin/usuarios, /admin/junta) hacia /login sin sesión
    Given driver baseUrl + '/incidencias'
    Then waitFor('#login-form')
    Given driver baseUrl + '/operaciones/tareas'
    Then waitFor('#login-form')
    Given driver baseUrl + '/voceros/galeria'
    Then waitFor('#login-form')
    Given driver baseUrl + '/secretaria/bitacora'
    Then waitFor('#login-form')
    Given driver baseUrl + '/admin/estructura'
    Then waitFor('#login-form')
    Given driver baseUrl + '/admin/usuarios'
    Then waitFor('#login-form')
    Given driver baseUrl + '/admin/junta'
    Then waitFor('#login-form')

  Scenario: 5. Redirección automática de rutas protegidas de Hito 10 (/tesoreria/facturacion y /finanzas/solvencia) hacia /login sin sesión autenticada
    Given driver baseUrl + '/tesoreria/facturacion'
    Then waitFor('#login-form')
    Given driver baseUrl + '/finanzas/solvencia'
    Then waitFor('#login-form')

  Scenario: 6. Redirección automática de rutas de Gobernanza Digital y Cartas Consulta de Hito 11 (/consultas y /consultas/1) hacia /login sin sesión autenticada
    Given driver baseUrl + '/consultas'
    Then waitFor('#login-form')
    Given driver baseUrl + '/consultas/1'
    Then waitFor('#login-form')

  Scenario: 7. Redirección automática de rutas de Accesos QR y Paquetería en Garita de Hito 12 (/accesos/pases, /operaciones/garita-qr y /operaciones/paqueteria) hacia /login sin sesión autenticada
    Given driver baseUrl + '/accesos/pases'
    Then waitFor('#login-form')
    Given driver baseUrl + '/operaciones/garita-qr'
    Then waitFor('#login-form')
    Given driver baseUrl + '/operaciones/paqueteria'
    Then waitFor('#login-form')
