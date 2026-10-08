"""Integration tests for FastAPI endpoints."""

import unittest
from starlette.testclient import TestClient
from src.app import app


class TestAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_serves_html(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("RAMPulse", response.text)

    def test_api_system(self):
        response = self.client.get("/api/system")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("ram", data)
        self.assertIn("swap", data)
        self.assertIn("health", data)
        self.assertIn("system", data)

    def test_api_processes_flat(self):
        response = self.client.get("/api/processes?grouped=false&limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["grouped"], False)
        self.assertLessEqual(len(data["processes"]), 5)

    def test_api_processes_grouped(self):
        response = self.client.get("/api/processes?grouped=true&limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["grouped"], True)
        self.assertLessEqual(len(data["processes"]), 5)

    def test_api_history(self):
        response = self.client.get("/api/history")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("history", data)
        self.assertIsInstance(data["history"], list)

    def test_api_recommendations(self):
        response = self.client.get("/api/recommendations")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("recommendations", data)
        self.assertIn("top_hogs", data)

    def test_api_kill_protected_process_blocked(self):
        # Attempting to kill PID 4 (System) must return 400 Bad Request
        response = self.client.post("/api/processes/4/kill", json={"force": False})
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())


if __name__ == "__main__":
    unittest.main()
