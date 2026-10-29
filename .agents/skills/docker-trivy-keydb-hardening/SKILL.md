---
name: docker-trivy-keydb-hardening
description: >-
  Container hardening guidelines (Trivy HIGH/CRITICAL = 0), KeyDB multi-threaded in-memory engine,
  non-root runtime users, multi-stage Docker builds, and backend performance optimization.
---

# Docker Trivy Hardening & KeyDB Performance Skill

This skill guides the implementation of production-grade Docker containers and ultra-fast in-memory caching engines.
> **OUTPUT LANGUAGE CONSTRAINT:** Always communicate with the user and write final explanations in Spanish.

---

## 1. Container Hardening Checklist (Trivy Target = 0)

1. **Non-Root Execution:**
   - Always run production applications under unprivileged system users (`appuser` with UID 10001 or `node` with UID 1000).
2. **Multi-Stage Builds:**
   - Separate build-time dependencies from the final runtime image to minimize attack surface and image size.
3. **Security Profiles & Capabilities:**
   - Drop unnecessary Linux capabilities (`cap_drop: [ALL]`, keep only required capabilities).
   - Add `no-new-privileges: true` to prevent privilege escalation.
4. **Vulnerability Scans:**
   - Execute `./auditar-infra.sh` ensuring 0 unresolved HIGH/CRITICAL vulnerabilities.

---

## 2. In-Memory Engine: KeyDB Multi-Threaded

When deploying cache, rate-limiting, idempotency locks, or Celery/Worker queues:
- **Default Choice:** `eqalpha/keydb:alpine`
- **Rationale:** KeyDB is a drop-in multi-threaded Redis alternative yielding 3x-5x higher throughput on multi-core servers while remaining 100% compatible with `redis.asyncio`.
- **Recommended Configuration:**
  ```yaml
  redis:
    image: eqalpha/keydb:alpine
    command: >
      keydb-server
      --server-threads 2
      --appendonly no
      --save ""
      --maxmemory 256mb
      --maxmemory-policy volatile-lru
    healthcheck:
      test: ["CMD-SHELL", "keydb-cli ping | grep PONG"]
      interval: 5s
      timeout: 3s
      retries: 10
  ```
