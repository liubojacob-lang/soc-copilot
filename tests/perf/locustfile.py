"""Locust performance and load testing suite for SOC Copilot.

Scenarios tested:
1. User Authentication & Token Generation
2. Security Alert Listing with Pagination & Status Filters
3. Security Alert Ingestion
4. AI Analysis Task Triggering
"""

import random
import uuid
from locust import HttpUser, between, task

SAMPLE_IPS = ["192.168.1.10", "10.0.0.15", "172.16.0.22", "203.0.113.55"]
SEVERITIES = ["low", "medium", "high", "critical"]
SOURCES = ["wazuh", "suricata", "falco", "firewall"]


class SOCCopilotLoadTestUser(HttpUser):
    wait_time = between(0.1, 0.5)
    access_token: str | None = None

    def on_start(self):
        """Authenticate user and cache Bearer token."""
        login_payload = {
            "username": "admin",
            "password": "admin123!"
        }
        try:
            resp = self.client.post("/api/auth/token", data=login_payload)
            if resp.status_code == 200:
                self.access_token = resp.json().get("access_token")
                self.client.headers.update({"Authorization": f"Bearer {self.access_token}"})
        except Exception:
            pass

    @task(6)
    def query_alerts_list(self):
        """High-frequency read: Fetch paginated security alerts."""
        severity = random.choice(SEVERITIES)
        self.client.get(
            f"/api/v1/security-alerts/?limit=20&offset=0&severity={severity}",
            name="/api/v1/security-alerts/?severity=[filter]"
        )

    @task(3)
    def ingest_security_alert(self):
        """Medium-frequency write: Ingest security alert from SIEM/EDR."""
        payload = {
            "title": f"Automated Load Test Alert {uuid.uuid4().hex[:8]}",
            "source": random.choice(SOURCES),
            "severity": random.choice(SEVERITIES),
            "source_ip": random.choice(SAMPLE_IPS),
            "description": "Simulated attack event during production readiness load testing",
            "status": "open"
        }
        self.client.post(
            "/api/v1/security-alerts/",
            json=payload,
            name="/api/v1/security-alerts/ [POST]"
        )

    @task(2)
    def check_system_health(self):
        """Healthcheck endpoint polling."""
        self.client.get("/api/health", name="/api/health")

    @task(1)
    def submit_ai_task(self):
        """Resource-heavy task: Trigger AI analysis with circuit breaker fallback."""
        payload = {
            "task_type": "alert_analysis",
            "payload": {
                "alert_id": str(uuid.uuid4()),
                "title": "Suspicious command execution",
                "severity": "high"
            }
        }
        self.client.post(
            "/api/v1/ai/tasks",
            json=payload,
            name="/api/v1/ai/tasks [POST]"
        )
