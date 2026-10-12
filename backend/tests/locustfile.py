from locust import HttpUser, task, between


class CondominioStressUser(HttpUser):
    wait_time = between(1, 2)

    @task(3)
    def check_health(self) -> None:
        self.client.get("/health")

    @task(2)
    def check_unauthenticated_me(self) -> None:
        with self.client.get("/api/auth/me", catch_response=True) as response:
            if response.status_code == 401:
                response.success()

    @task(1)
    def invalid_login(self) -> None:
        payload: dict[str, str] = {"correo": "inexistente@correo.com", "password": "wrong"}
        self.client.post("/api/auth/login", json=payload)
