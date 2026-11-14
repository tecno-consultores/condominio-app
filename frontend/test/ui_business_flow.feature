# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors

@parallel=false
Feature: Cobertura Funcional y Flujos BDD de Identidad, Finanzas, Operaciones, Administración, Facturación LPH, Gobernanza Digital, Accesos QR / Paquetería, Reservas de Áreas Sociales y Ayuda Contextual (Hitos 5 al 15 y 8)

  Background:
    * def cdpUrl = karate.properties['CHROME_CDP_URL'] || java.lang.System.getenv('CHROME_CDP_URL') || 'http://127.0.0.1:9222'
    * url cdpUrl + '/json/new?about:blank'
    * method put
    * status 200
    * configure driver = { type: 'chrome', start: false, host: '127.0.0.1', port: 9222 }
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

  Scenario: 8. Redirección automática de la vista de Reserva de Áreas Sociales de Hito 13 (/reservas/areas) hacia /login sin sesión autenticada
    Given driver baseUrl + '/reservas/areas'
    Then waitFor('#login-form')

  Scenario: 9. El usuario interactúa con la Ayuda Contextual Universal de Hito 14 en /login (#btn-contextual-help), verifica Top Layer (#dialog-contextual-help) y su cierre
    Given driver baseUrl + '/login'
    And waitFor('#btn-contextual-help')
    When click('#btn-contextual-help')
    Then waitFor('#dialog-contextual-help')
    And waitUntil("document.querySelector('#dialog-contextual-help')?.matches(':modal') === true")
    And match text('#help-screen-title') contains 'Inicio de Sesión'
    And waitFor('#help-steps-list')
    And waitFor('#btn-close-help')
    When click('#btn-close-help')
    Then waitUntil("!document.querySelector('#dialog-contextual-help')")

  Scenario: 10. El formulario público de registro consulta unidades sin exponer datos financieros privados (Hito 17.4)
    Given driver baseUrl + '/register'
    And waitFor('#reg-unidad')
    * def bodyText = text('body')
    * assert !bodyText.contains('alicuota')
    * assert !bodyText.contains('credito_disponible_usd')

  Scenario: 11. Conmutación de tema claro/oscuro OKLCH mediante #btn-theme-toggle y actualización de meta color-scheme (Hito 15)
    Given driver baseUrl + '/login'
    And waitFor('#btn-theme-toggle')
    And waitUntil("document.querySelector('meta[name=\"color-scheme\"]')?.getAttribute('content') === 'light dark'")
    When click('#btn-theme-toggle')
    Then waitUntil("document.documentElement.classList.contains('theme-dark') === true")
    And waitUntil("document.querySelector('meta[name=\"color-scheme\"]')?.getAttribute('content') === 'dark'")
    When click('#btn-theme-toggle')
    Then waitUntil("document.documentElement.classList.contains('theme-dark') === false")
    And waitUntil("document.querySelector('meta[name=\"color-scheme\"]')?.getAttribute('content') === 'light dark'")

  Scenario: 12. Validación de geometría responsiva (0 overflow horizontal y touch target >= 44px en /login y /register) (Hito 8)
    Given driver baseUrl + '/login'
    And waitFor('#btn-login-submit')
    Then match script("document.documentElement.scrollWidth <= window.innerWidth") == true
    And match script("document.querySelector('#btn-login-submit').getBoundingClientRect().height >= 44") == true
    Given driver baseUrl + '/register'
    And waitFor('#btn-register-submit')
    Then match script("document.documentElement.scrollWidth <= window.innerWidth") == true
    And match script("document.querySelector('#btn-register-submit').getBoundingClientRect().height >= 44") == true

  Scenario: 13. Validación de theming nativo (accent-color, scrollbar-color) y text-wrap balance en /login y /register
    Given driver baseUrl + '/login'
    And waitFor('#login-heading')
    Then match script("getComputedStyle(document.querySelector('#login-heading')).textWrap") == 'balance'
    And match script("getComputedStyle(document.documentElement).scrollbarColor") != 'auto'
    And match script("getComputedStyle(document.documentElement).accentColor") != 'auto'
    Given driver baseUrl + '/register'
    And waitFor('#register-heading')
    Then match script("getComputedStyle(document.querySelector('#register-heading')).textWrap") == 'balance'



