# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors

Feature: Cobertura Funcional y Flujos BDD de Identidad, Contención Fantasma y Layout Mobile-First (Hito 5)

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

  Scenario: 3. Redirección automática de rutas protegidas hacia /login cuando no existe sesión activa
    Given driver baseUrl + '/dashboard'
    Then waitFor('#login-form')
