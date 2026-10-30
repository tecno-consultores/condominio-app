# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors

# Mandatory Directive: Security-by-Design & Multi-Layer Testing Guidelines

> **CORE GOVERNANCE DIRECTIVE:**
> Applies to all AI agents and developers. Any code failing security or testing guidelines must be immediately rejected and refactored.
> **OUTPUT LANGUAGE CONSTRAINT:** Always communicate with the user and write final explanations in Spanish.

---

## 1. Multi-Layer Testing & Anti-Mock Blindness

Unit test isolation using mocks measures quick code execution paths, but introduces severe blind spots if disconnected from reality:

1. **ORM vs Database Schema Invariant:**
   - **Zero Schema Drift:** Modifying ORM models never alters the database automatically.
   - **Mandatory Migrations:** Any new model, table, constraint, or column type change requires an immediate versioned Alembic migration script in `backend/alembic/versions/`.
   - **Real Database Engine Verification:** Always verify tables, column types, and indices in a real PostgreSQL container (`make -C backend qa-parity`). Never assume passing mocks guarantee SQL syntax execution.
2. **Visual Geometry & Anti-JSDOM Testing:**
   - JSDOM does NOT calculate CSS Flexbox/Grid layouts, element coordinates, or viewport bounding boxes (always returns `0x0`).
   - Prevent overlapping elements (e.g. fixed footers or mobile bottom navigation bars collapsing over forms or FAB buttons) by enforcing in-flow layouts (`margin-top: auto` inside `<main>` and safe bottom padding for mobile nav), validating DOM hierarchy, and inspecting real browser viewports in Karate UI or Playwright.
3. **Trimodal Ground-Truth Fixtures:**
   - Test state and integrations against 3 raw fixtures:
     - **Fixture A (Virgin / Unconfigured / Ghost User):** Assert negative invariant (`es_activo=False`, `rol="FANTASMA"`, blocked access to operational panels).
     - **Fixture B (Nominal Configured):** Assert positive invariant (`es_activo=True`, nominal financial/operational telemetry).
     - **Fixture C (Degraded / Closed Period):** Assert graceful degradation and immutability (`bloqueado=True` returns HTTP 409 without unhandled 500 errors).

---

## 2. Security-by-Design Directives

Apply these non-negotiable security directives before writing any code:

1. **Mass Assignment Prevention (`extra="forbid"`):**
   - Enforce `model_config = ConfigDict(extra="forbid")` in all input Pydantic models (`backend/src/schemas.py`). Strictly decouple input DTOs from ORM models.
2. **Strict SSRF Prevention (`validate_safe_outgoing_url`):**
   - Any user-supplied URL (e.g. receipt proof `url_comprobante`, invoice `url_factura`, webhooks) must pass strict validation before storage or outbound network calls.
   - Reject: non-HTTP(S) schemes, loopback (`127.0.0.0/8`, `::1`, `localhost`), link-local (`169.254.0.0/16`), RFC 1918 private ranges, and internal container hostnames (`api`, `postgres`, `keydb`, `redis`, `worker`, `minio`).
3. **Zero Plaintext Secrets & Salted Password Hashing:**
   - Passwords must use salted cryptographic KDFs (`PBKDF2-HMAC-SHA256` / `Argon2id`) verified with constant-time comparison (`hmac.compare_digest`).
4. **Scoped Idempotency for Mutating Operations:**
   - State-mutating requests (`POST /api/auth/register`, `POST /api/pagos/reportar`, `POST /api/incidencias/crear`) require an `Idempotency-Key` header, managed via KeyDB/Redis with scoped namespacing (`idemp:{scope}:{key}`) via `build_idempotency_key`.
5. **CSRF & Hardened Session Cookies:**
   - Session cookies: `HttpOnly; Secure; SameSite=Lax; Path=/`.
   - Support HMAC-SHA256 CSRF token validation (`X-CSRF-Token`) for cookie-authenticated browser mutations, while excluding M2M calls utilizing `Authorization: Bearer` headers per OWASP guidelines.
6. **File Upload Quotas (Anti-DoS / OOM):**
   - Enforce strict streaming upload limits (`MAX_UPLOAD_SIZE_BYTES = 2MB`) via `read_uploaded_file_safely`, rejecting oversized payloads with HTTP `413 Payload Too Large`.
7. **Cross-Site WebSocket Hijacking (CSWSH) Defense:**
   - Verify `Origin` header via `verify_websocket_origin` before executing `await ws.accept()`. Close with code `4403` on unlisted origins.
8. **Information Disclosure Prevention:**
   - Sanitize 422 `RequestValidationError` responses in production (`APP_ENV=production`) returning generic messages while logging details to container stdout.
   - Hide Swagger / ReDoc / OpenAPI schemas in production (`docs_url=None`, `redoc_url=None`, `openapi_url=None`).
9. **Front-End XSS & Prototype Pollution Defense:**
   - Compulsory HTML escaping (`escapeHtml`) on dynamic DOM inputs.
   - Sanitize objects against `__proto__`, `constructor`, `prototype`, and instantiate safe records via `Object.create(null)`.
10. **Concurrency Grace Period in Refresh Tokens:**
    - Provide 5s leeway (`rotate_refresh_token_with_grace_period`) on token rotations in KeyDB/Redis to prevent accidental session revocation across multi-tab requests.
11. **Shift-Left Lockfile & Supply-Chain Governance (pnpm v12):**
    - Manage dependencies with strict lockfiles (`uv.lock`, `pnpm-lock.yaml`). Audit with `./auditar-infra.sh` and `make -C backend qa-deps`.
    - In `frontend/`, enforce `dangerously-allow-all-builds=false` in `.npmrc` and explicitly allowlist required native build scripts (`esbuild`, `vue-demi`) inside `pnpm-workspace.yaml` under `allowBuilds` to prevent supply-chain script execution attacks while maintaining compatibility with `pnpm` v12 (`sinfallas/base-node-ionic:26`).
12. **Modern Web Form Ergonomics & Post-Interaction Validation:**
    - Use `autocomplete="username"` on email login inputs, `autocomplete="current-password"` on sign-in passwords, and `autocomplete="new-password"` on sign-up passwords.
    - Place format and password rules/hints **above** the `<input>` element (`aria-describedby`) so mobile virtual keyboards never obscure them, and style validation states with `:user-invalid` and `:user-valid` after user interaction (`blur`).
13. **Safe Evidence URI Validation (`UrlEvidenciaSegura`) & Binary Magic-Byte Inspection:**
    - All attachment/evidence URL fields (`url_comprobante`, `url_factura`, `url_foto`, `url_evidencia`) must use `UrlEvidenciaSegura` to block dangerous URI schemes (`javascript:`, `data:`, `vbscript:`, `file:`).
    - All file uploads must validate binary magic bytes (`%PDF-`, `\x89PNG`, `\xFF\xD8\xFF`, `RIFF....WEBP`, `ftypavif`) inside `read_uploaded_file_safely`.
14. **Penny-Exact Aliquot Prorating (Hamilton Method) & Cryptographic Non-Repudiation (`HMAC-SHA256`):**
    - Condominium expense prorating by unit aliquot (`Unidad.alicuota`) must use `decimal.Decimal` and the **Largest Remainder Method (Hamilton / Hare-Niemeyer)** so that the sum of billed unit receipts strictly equals the total expense pool down to `$0.01`.
    - Solvency Certificates (`CertificadoSolvencia`), Carta Consulta votes (`VotoConsulta`, Art. 23 LPH), and Visitor QR Passes (`PaseVisita`) must carry `HMAC-SHA256` signatures verified via `hmac.compare_digest`, with single-use QR `jti` nonces burned atomically in KeyDB (`SET qr_used:{jti} 1 NX EX {ttl}`).
