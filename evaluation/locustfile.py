"""
Phase 4 — Locust Load Test Script
Run with:
  locust -f evaluation/locustfile.py --headless -u 1 -r 1 --run-time 30s --host http://127.0.0.1:8765 --csv evaluation/load_smoke
  locust -f evaluation/locustfile.py --headless -u 5 -r 1 --run-time 60s --host http://127.0.0.1:8765 --csv evaluation/load_5u
  locust -f evaluation/locustfile.py --headless -u 10 -r 2 --run-time 60s --host http://127.0.0.1:8765 --csv evaluation/load_10u
"""
import random
from locust import HttpUser, between, task


class MeetingAppUser(HttpUser):
    """Simulate a read-heavy authenticated user session."""

    wait_time = between(0.5, 2.0)
    token: str = ""

    def on_start(self):
        """Login once at session start."""
        users = [
            ("chairman", "changeme"),
            ("principal", "changeme"),
            ("teacher", "changeme"),
            ("hod", "changeme"),
        ]
        username, password = random.choice(users)
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
            name="POST /auth/login",
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")

    def _h(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    @task(5)
    def health_check(self):
        self.client.get("/health", name="GET /health")

    @task(4)
    def get_meetings(self):
        self.client.get("/api/v1/meetings", headers=self._h(), name="GET /meetings")

    @task(3)
    def get_rooms(self):
        self.client.get("/api/v1/rooms", headers=self._h(), name="GET /rooms")

    @task(3)
    def get_actions(self):
        self.client.get("/api/v1/actions", headers=self._h(), name="GET /actions")

    @task(2)
    def get_schedule(self):
        self.client.get("/api/v1/schedule", headers=self._h(), name="GET /schedule")

    @task(2)
    def get_me(self):
        self.client.get("/api/v1/auth/me", headers=self._h(), name="GET /auth/me")

    @task(1)
    def get_root(self):
        self.client.get("/", name="GET /")

