# 👥 Especificación 02: Dominio de Identidad, Estructura Polimórfica y RBAC

**Estado:** Hitos 1, 2 y 4 Completados en Backend (`auth.py`, `administracion.py`) / GUI en Hitos 5 y 7

---

## 1. Modelo de Entidades de Identidad y Estructura

### 1.1. `Usuario` (`usuarios`)
- `id`: `Integer` PK
- `nombre`: `String` (indexado)
- `cedula`: `String` (único, indexado, ej. `V-12345678`)
- `correo`: `String` (único, indexado, validado RFC)
- `telefono`: `String`
- `password_hash`: `String` (`pbkdf2_sha256$<salt>$<digest>`)
- `es_activo`: `Boolean` (`False` por defecto al registrarse como Usuario Fantasma)
- `rol`: `String` (`FANTASMA` por defecto; valores válidos: `FANTASMA`, `PROPIETARIO`, `INQUILINO`, `PRESIDENTE`, `VICEPRESIDENTE`, `TESORERO`, `SECRETARIO`, `VOCERO`, `CONSERJE`)

### 1.2. `Estructura` (`estructuras`) y `Unidad` (`unidades`)
- Soporta condominios verticales (`tipo = "EDIFICIO"`, ej. Torre A -> Apartamento `A-42` + Puesto de Estacionamiento opcional) y horizontales (`tipo = "CALLE"`, ej. Calle Los Pinos -> Casa `42`), o conjuntos mixtos.
- `Unidad.identificador`: `String` único (ej. `A-101`, `C1-12`).

### 1.3. `ContratoOcupacion` (`contratos_ocupacion`)
- Mantiene el historial inmutable de quién habita o posee cada unidad a lo largo del tiempo:
  - `usuario_id`, `unidad_id`, `tipo_ocupante` (`PROPIETARIO` | `INQUILINO`), `es_activo`, `fecha_inicio`, `fecha_fin`.
- Nunca se sobrescribe un ocupante anterior; al cambiar de inquilino o propietario, se cierra el contrato previo (`es_activo = False`, `fecha_fin = now()`) y se inserta uno nuevo.

---

## 2. Máquina de Estados: "Flujo de Usuario Fantasma"

```mermaid
stateDiagram-v2
    [*] --> FANTASMA_INACTIVO: POST /api/auth/register (Idempotency-Key)
    FANTASMA_INACTIVO --> PANTALLA_BLOQUEO: Login -> GET /api/auth/me (es_activo=false)
    PANTALLA_BLOQUEO --> ACTIVO_ASIGNADO: PUT /api/usuarios/{id}/asignar (Presidente activa y asigna Unidad)
    ACTIVO_ASIGNADO --> MIEMBRO_JUNTA: PUT /api/junta/cargos (Solo si tipo_ocupante == PROPIETARIO)
```

### Reglas de Negocio Estrictas
1. **Bloqueo Total del Usuario Fantasma:** Mientras `es_activo == False` o `rol == "FANTASMA"`, el usuario autenticado **solo** puede consultar `GET /api/auth/me` y cerrar sesión. En el Frontend Vue 3, el Navigation Guard global redirige forzosamente cualquier ruta hacia `/espera-aprobacion`.
2. **Condición de Junta de Condominio:** Únicamente usuarios con contrato activo donde `tipo_ocupante == "PROPIETARIO"` pueden ser designados como `PRESIDENTE`, `VICEPRESIDENTE`, `TESORERO`, `SECRETARIO` o `VOCERO`. Los inquilinos no pueden integrar la Junta.
3. **Segregación de Funciones (SoD):**
   - **Presidente / Vicepresidente:** Aprueban usuarios, gestionan estructura, asignan tareas al conserje y atienden incidencias. **No pueden** aprobar/rechazar pagos ni ejecutar el cierre contable.
   - **Tesorero:** Único rol autorizado para registrar tasas/egresos, aprobar/rechazar pagos y ejecutar el cierre mensual (`POST /api/finanzas/cierre-mensual`).

---

## 3. Contratos de Endpoints del Dominio

| Método y Ruta | Rol Requerido | Cabeceras | Descripción y Reglas |
| :--- | :--- | :--- | :--- |
| `POST /api/auth/register` | Público | `Idempotency-Key` | Crea `Usuario` (`es_activo=False`, `rol="FANTASMA"`) y solicitud en `ContratoOcupacion`. Rechaza campos extra (`extra="forbid"`). |
| `POST /api/auth/login` | Público | — | Verifica `PBKDF2-HMAC-SHA256` y emite JWT en cookie `HttpOnly; Secure; SameSite=Lax`. |
| `GET /api/auth/me` | Autenticado | Cookie / Bearer | Devuelve `{id, correo, nombre, rol, es_activo}`. |
| `GET /api/estructura/unidades` | Público / Auth | — | Lista unidades disponibles para el selector de registro y panel de estructura. |
| `POST /api/estructura/generar` | `PRESIDENTE` | `Idempotency-Key` | Crea sector (`EDIFICIO`/`CALLE`) y autogenera sus unidades. |
| `GET /api/usuarios/pendientes` | `PRESIDENTE`, `VICEPRESIDENTE` | Cookie / Bearer | Lista usuarios con `es_activo == False`. |
| `PUT /api/usuarios/{id}/asignar` | `PRESIDENTE`, `VICEPRESIDENTE` | Cookie / Bearer | Activa usuario (`es_activo=True`), asigna rol (`PROPIETARIO`/`INQUILINO`) y activa `ContratoOcupacion`. |
| `PUT /api/junta/cargos` | `PRESIDENTE` | Cookie / Bearer | Asigna cargos de Junta validando que el usuario sea `PROPIETARIO` con unidad activa. |
