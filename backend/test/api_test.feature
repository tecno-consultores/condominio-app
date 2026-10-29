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
    And header Idempotency-Key = '018f4a12-8888-7000-8000-000000000099'
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
    Given path '/api/auth/login'
    And request { correo: "inexistente@test.com", password: "PasswordErroneo123!" }
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
    Given path '/api/auth/register'
    And header Idempotency-Key = '018f4a12-9999-7000-8000-000000000404'
    And request
      """
      {
        "nombre": "Fantasma BDD",
        "cedula": "V-40404040",
        "correo": "fantasma.bdd@test.com",
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
    And request { correo: "fantasma.bdd@test.com", password: "Password123!" }
    When method post
    Then status 200

    Given path '/api/incidencias/abiertas'
    When method get
    Then status 403
    And match response.detail contains 'pendiente de aprobación'

    Given path '/api/usuarios/pendientes'
    When method get
    Then status 403
