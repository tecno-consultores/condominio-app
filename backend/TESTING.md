# Bitácora de Pruebas y Validación (TESTING.md) - Backend

**Proyecto:** Condominio App  
**Estándar:** QA Blueprint Nivel 11X

---

## 1. Cobertura de Negocio en Pruebas Unitarias

La suite unitaria actual cubre de forma completamente aislada (sin red ni base de datos real):

- `tests/test_main.unit.py`:
  - Healthcheck HTTP `/health` respondiendo con estado 200 y JSON `{"status": "healthy"}`.
- `tests/test_schemas.unit.py`:
  - Validación de esquemas Pydantic `UsuarioCreate` (datos válidos, rechazo de correo malformado con `EmailStr`, campos requeridos).
  - Validación de serialización de respuesta en `UsuarioResponse` (`from_attributes`).
- `tests/test_models.unit.py`:
  - Modelado SQLAlchemy de `Usuario` (campos, defaults, flag fantasma `es_activo = False`).
  - Modelado de `Estructura` (Torres, Calles, Edificios).
  - Modelado de `Unidad` con identificador único.
  - Modelado de `ContratoOcupacion` (histórico de inquilinos y propietarios).
- `tests/test_auth.unit.py`:
  - Registro de usuarios fantasma (`POST /api/auth/register`) con mocking asíncrono de sesión DB y Redis.
  - Validación de unicidad de clave de idempotencia (`Idempotency-Key` en Redis devolviendo 409 Conflict si está repetida).
  - Rechazo de petición sin encabezado de idempotencia (código 422).
  - Validación de usuario duplicado (correo o cédula) retornando 400.
  - Manejo y rollback ante fallos inesperados de base de datos (código 500).
  - Inicio de sesión (`POST /api/auth/login`) con verificación de credenciales y creación de cookie `HttpOnly` `access_token`.
  - Rechazo de inicio de sesión con credenciales inválidas (código 401).
  - Endpoint `/api/auth/me`: rechazo sin cookie (401), validación de firma y expiración de token JWT (401 en caso de token expirado o inválido), y retorno exitoso de perfil autenticado.

---

## 2. Ejecución Efímera en Docker

Todas las pruebas se ejecutan utilizando el contenedor efímero `sinfallas/base-python-uv:3.13` a través de los siguientes comandos definidos en `backend/Makefile`:

### Pruebas Unitarias y Cobertura (mínimo 95%):
```bash
make qa-unit
```

### Linters, Tipado y SAST:
```bash
make qa-lint
```

### Verificación de Complejidad Ciclomática (Radon):
```bash
make qa-complexity
```

### Pruebas de Mutación (Mutmut):
```bash
make qa-mutation
```

### Ejecución Integral de Calidad:
```bash
make qa-all
```
