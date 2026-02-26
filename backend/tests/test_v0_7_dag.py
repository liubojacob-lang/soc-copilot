"""
SOC Copilot v0.7 DAG-Based Playbook Engine - Verification Tests
Python version for Windows compatibility
"""

import requests
import json
import time
from typing import Optional


class DAGTester:
    """Test suite for v0.7 DAG implementation."""

    def __init__(self, api_base: str = "http://localhost:8000", token: str = ""):
        self.api_base = api_base
        self.token = token
        self.session = requests.Session()
        self.results = []

    def log_test(self, test_name: str):
        """Log test start."""
        print(f"\n[TEST] {test_name}")

    def log_info(self, message: str):
        """Log info message."""
        print(f"[INFO] {message}")

    def log_error(self, message: str):
        """Log error message."""
        print(f"[ERROR] {message}")

    def get_headers(self) -> dict:
        """Get request headers with auth."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def test_1_health_check(self) -> bool:
        """Test 1: Health check."""
        self.log_test("Health Check")
        try:
            response = self.session.get(f"{self.api_base}/api/health")
            data = response.json()
            if "v0.7" in data.get("version", ""):
                self.log_info("✓ Health check passed - v0.7 detected")
                return True
            else:
                self.log_error(f"✗ Version mismatch: {data.get('version')}")
                return False
        except Exception as e:
            self.log_error(f"✗ Health check failed: {e}")
            return False

    def test_2_list_definitions(self) -> bool:
        """Test 2: List playbook definitions."""
        self.log_test("List Playbook Definitions")
        try:
            response = self.session.get(
                f"{self.api_base}/api/playbook/definitions",
                headers=self.get_headers()
            )
            data = response.json()
            definitions = data.get("definitions", [])
            self.log_info(f"✓ Listed {len(definitions)} playbook definitions")
            return True
        except Exception as e:
            self.log_error(f"✗ Failed to list definitions: {e}")
            return False

    def test_3_create_definition(self) -> Optional[str]:
        """Test 3: Create DAG definition."""
        self.log_test("Create DAG Definition")
        definition_data = {
            "nodes": [
                {"id": "extract", "step_id": "ioc_extract", "name": "Extract IOCs"},
                {"id": "ti_lookup", "step_id": "ti_lookup_otx", "name": "OTX Lookup"},
                {"id": "enrich", "step_id": "asset_enrich", "name": "Enrich Assets"}
            ],
            "edges": [
                {"source": "extract", "target": "ti_lookup"},
                {"source": "extract", "target": "enrich"}
            ]
        }

        try:
            # Using query params for name/description
            url = f"{self.api_base}/api/playbook/definitions"
            params = {
                "name": "Test DAG Playbook",
                "description": "Test DAG for verification",
                "version": "1.0.0"
            }
            response = self.session.post(
                url,
                params=params,
                json={"definition_json": definition_data},
                headers=self.get_headers()
            )
            data = response.json()
            definition_id = data.get("id")
            if definition_id:
                self.log_info(f"✓ Created DAG definition with ID: {definition_id}")
                return definition_id
            else:
                self.log_error("✗ Failed to create DAG definition")
                return None
        except Exception as e:
            self.log_error(f"✗ Failed to create definition: {e}")
            return None

    def test_4_get_definition(self, definition_id: str) -> bool:
        """Test 4: Get definition by ID."""
        self.log_test(f"Get Definition by ID ({definition_id})")
        try:
            response = self.session.get(
                f"{self.api_base}/api/playbook/definitions/{definition_id}",
                headers=self.get_headers()
            )
            data = response.json()
            if "definition_json" in data:
                self.log_info("✓ Retrieved definition successfully")
                return True
            else:
                self.log_error("✗ Failed to retrieve definition")
                return False
        except Exception as e:
            self.log_error(f"✗ Failed to get definition: {e}")
            return False

    def test_5_execute_dag(self, definition_id: str) -> Optional[str]:
        """Test 5: Execute DAG (dry run)."""
        self.log_test("Execute DAG (Dry Run)")
        try:
            url = f"{self.api_base}/api/playbook/definitions/{definition_id}/run"
            params = {"mode": "dry_run"}
            response = self.session.post(
                url,
                params=params,
                json={"input_json": {}},
                headers=self.get_headers()
            )
            data = response.json()
            run_id = data.get("run_id")
            if run_id:
                self.log_info(f"✓ Started DAG execution with Run ID: {run_id}")
                return run_id
            else:
                self.log_error("✗ Failed to start DAG execution")
                return None
        except Exception as e:
            self.log_error(f"✗ Failed to execute DAG: {e}")
            return None

    def test_6_get_run_nodes(self, run_id: str) -> bool:
        """Test 6: Get run details with nodes."""
        self.log_test(f"Get Run Details with Nodes ({run_id})")
        time.sleep(2)  # Wait for execution to start
        try:
            response = self.session.get(
                f"{self.api_base}/api/playbook/runs/{run_id}/nodes",
                headers=self.get_headers()
            )
            data = response.json()
            nodes = data.get("nodes", [])
            self.log_info(f"✓ Retrieved {len(nodes)} node executions")
            return True
        except Exception as e:
            self.log_error(f"✗ Failed to retrieve node executions: {e}")
            return False

    def test_7_webhook_health(self) -> bool:
        """Test 7: Webhook health check."""
        self.log_test("Webhook Health Check")
        try:
            response = self.session.get(f"{self.api_base}/api/webhooks/health")
            data = response.json()
            if data.get("status") == "ok":
                self.log_info("✓ Webhook module is healthy")
                return True
            else:
                self.log_error("✗ Webhook module health check failed")
                return False
        except Exception as e:
            self.log_error(f"✗ Webhook health check failed: {e}")
            return False

    def test_8_linear_compatibility(self) -> bool:
        """Test 8: Linear playbook compatibility."""
        self.log_test("Execute Linear Playbook (Backward Compatibility)")
        try:
            response = self.session.post(
                f"{self.api_base}/api/playbook/run",
                json={
                    "playbook_name": "phishing_triage",
                    "mode": "dry_run",
                    "input_json": {"raw_log": "test email content"}
                },
                headers=self.get_headers()
            )
            data = response.json()
            if data.get("id"):
                self.log_info("✓ Linear playbook execution still works")
                return True
            else:
                self.log_error("✗ Linear playbook execution failed")
                return False
        except Exception as e:
            self.log_error(f"✗ Linear execution failed: {e}")
            return False

    def test_9_execution_mode_field(self, run_id: str) -> bool:
        """Test 9: Verify execution mode field."""
        self.log_test("Verify Execution Mode Field")
        try:
            response = self.session.get(
                f"{self.api_base}/api/playbook/runs/{run_id}",
                headers=self.get_headers()
            )
            data = response.json()
            if data.get("execution_mode") == "dag":
                self.log_info("✓ Execution mode field present (dag)")
                return True
            else:
                self.log_error(f"✗ Execution mode field not found: {data.get('execution_mode')}")
                return False
        except Exception as e:
            self.log_error(f"✗ Failed to verify execution mode: {e}")
            return False

    def test_10_concurrent_execution(self, definition_id: str) -> bool:
        """Test 10: Concurrent execution test."""
        self.log_test("Execute Multiple DAG Runs (Concurrent Test)")
        run_ids = []
        for i in range(3):
            try:
                url = f"{self.api_base}/api/playbook/definitions/{definition_id}/run"
                response = self.session.post(
                    url,
                    params={"mode": "dry_run"},
                    json={"input_json": {}},
                    headers=self.get_headers()
                )
                data = response.json()
                run_id = data.get("run_id")
                if run_id:
                    run_ids.append(run_id)
            except Exception as e:
                self.log_error(f"Run {i+1} failed: {e}")

        if len(run_ids) == 3:
            self.log_info(f"✓ Successfully started {len(run_ids)} concurrent DAG runs")
            return True
        else:
            self.log_error(f"✗ Only {len(run_ids)}/3 runs started")
            return False

    def run_all_tests(self):
        """Run all verification tests."""
        print("=" * 50)
        print("SOC Copilot v0.7 DAG Verification Tests")
        print("=" * 50)
        print(f"API Base: {self.api_base}")
        print()

        results = []
        results.append(self.test_1_health_check())
        results.append(self.test_2_list_definitions())

        definition_id = self.test_3_create_definition()
        if definition_id:
            results.append(True)
            results.append(self.test_4_get_definition(definition_id))
            run_id = self.test_5_execute_dag(definition_id)
            if run_id:
                results.append(True)
                results.append(self.test_6_get_run_nodes(run_id))
                results.append(self.test_9_execution_mode_field(run_id))
                results.append(self.test_10_concurrent_execution(definition_id))
            else:
                results.append(False)
        else:
            results.append(False)
            results.append(False)

        results.append(self.test_7_webhook_health())
        results.append(self.test_8_linear_compatibility())

        # Summary
        print("\n" + "=" * 50)
        print("Test Summary")
        print("=" * 50)
        passed = sum(results)
        total = len(results)
        print(f"Passed: {passed}/{total}")

        if passed == total:
            print("✓ All tests passed!")
        else:
            print(f"✗ {total - passed} test(s) failed")

        return passed == total


if __name__ == "__main__":
    import os

    api_base = os.getenv("API_BASE", "http://localhost:8000")
    token = os.getenv("TOKEN", "")

    tester = DAGTester(api_base, token)
    success = tester.run_all_tests()
    exit(0 if success else 1)
