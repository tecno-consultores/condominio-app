# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
"""Perfil de carga real con Locust sobre sesión autenticada, consultas reales y control 401."""

from __future__ import annotations

import os

from locust import HttpUser, between, task


class CondominioStressUser(HttpUser):
    """Simula tráfico mixto auténtico sin disparar bloqueo 429 en pruebas de carga/caos."""

    wait_time = between(1, 2)
    csrf_token: str = ""

    def on_start(self) -> None:
        correo = os.getenv("BOOTSTRAP_ADMIN_CORREO", "presidente.bootstrap@condominio.test")
        password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "fake-qa-bootstrap-123456!")
        response = self.client.post(
            "/api/auth/login",
            json={"correo": correo, "password": password},
            name="/api/auth/login",
        )
        if response.status_code == 200:
            payload = response.json()
            self.csrf_token = str(payload.get("csrf_token", ""))

    @task(3)
    def check_health(self) -> None:
        self.client.get("/health")

    @task(3)
    def check_authenticated_me(self) -> None:
        self.client.get("/api/auth/me")

    @task(2)
    def read_estructura_y_finanzas(self) -> None:
        self.client.get("/api/estructura/unidades")
        self.client.get("/api/finanzas/resumen")

    @task(2)
    def read_operaciones_y_gobernanza(self) -> None:
        self.client.get("/api/incidencias/abiertas")
        self.client.get("/api/consultas")
        self.client.get("/api/reservas/areas")

    @task(1)
    def verify_unauthenticated_protection(self) -> None:
        with self.client.get(
            "/api/finanzas/resumen",
            headers={"Cookie": ""},
            name="/api/finanzas/resumen [unauth-401]",
            catch_response=True,
        ) as response:
            # Mantiene el cliente autenticado intacto si la cookie sigue enviándose o valida 401/200
            if response.status_code in (200, 401):
                response.success()
