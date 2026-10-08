"""Unit tests for the Memory Monitoring and Process Inspection Engine."""

import unittest
from src.monitor import MemoryMonitor, format_bytes, SYSTEM_PROTECTED_PROCESSES


class TestMemoryMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = MemoryMonitor(max_history_points=10)

    def test_format_bytes(self):
        self.assertEqual(format_bytes(0), "0 B")
        self.assertEqual(format_bytes(1024), "1 KB")
        self.assertEqual(format_bytes(1048576), "1.00 MB")
        self.assertEqual(format_bytes(1073741824), "1.00 GB")
        self.assertEqual(format_bytes(16849256448), "15.69 GB")

    def test_get_system_summary(self):
        summary = self.monitor.get_system_summary()
        self.assertIn("system", summary)
        self.assertIn("ram", summary)
        self.assertIn("swap", summary)
        self.assertIn("health", summary)

        # RAM validation
        ram = summary["ram"]
        self.assertGreater(ram["total_bytes"], 0)
        self.assertGreater(ram["used_bytes"], 0)
        self.assertGreaterEqual(ram["free_bytes"], 0)
        self.assertGreaterEqual(ram["available_bytes"], 0)
        self.assertGreaterEqual(ram["percent"], 0.0)
        self.assertLessEqual(ram["percent"], 100.0)

        # Health status
        health = summary["health"]
        self.assertIn(health["status"], ["Optimal", "Moderate", "High Pressure", "Critical"])

    def test_get_raw_processes(self):
        procs = self.monitor.get_raw_processes()
        self.assertIsInstance(procs, list)
        self.assertGreater(len(procs), 0)

        # Verify attributes on first process
        first = procs[0]
        self.assertIn("pid", first)
        self.assertIn("name", first)
        self.assertIn("rss_bytes", first)
        self.assertIn("memory_percent", first)
        self.assertIn("is_protected", first)

    def test_get_processes_grouped(self):
        grouped = self.monitor.get_processes(grouped=True)
        self.assertIsInstance(grouped, list)
        self.assertGreater(len(grouped), 0)

        for app in grouped[:5]:
            self.assertIn("instance_count", app)
            self.assertGreaterEqual(app["instance_count"], 1)
            self.assertIn("rss_bytes", app)
            self.assertGreaterEqual(app["rss_bytes"], 0)
            self.assertIn("display_name", app)

    def test_search_and_min_mb_filter(self):
        all_procs = self.monitor.get_processes(grouped=False)
        self.assertGreater(len(all_procs), 0)

        # Filter by min_mb
        filtered = self.monitor.get_processes(grouped=False, min_mb=100.0)
        for p in filtered:
            self.assertGreaterEqual(p["rss_mb"], 100.0)

    def test_system_protection_guard(self):
        # PID 0 (Idle) and PID 4 (System) must be protected
        res_idle = self.monitor.terminate_process(0)
        self.assertFalse(res_idle["success"])
        self.assertIn("Cannot terminate", res_idle["error"])

        res_sys = self.monitor.terminate_process(4)
        self.assertFalse(res_sys["success"])
        self.assertIn("Cannot terminate", res_sys["error"])

    def test_history_recording(self):
        history = self.monitor.get_history()
        self.assertGreaterEqual(len(history), 1)
        point = history[0]
        self.assertIn("timestamp", point)
        self.assertIn("ram_percent", point)
        self.assertIn("ram_used_gb", point)

    def test_recommendations(self):
        recs = self.monitor.get_recommendations()
        self.assertIn("ram_percent", recs)
        self.assertIn("top_hogs", recs)
        self.assertIn("recommendations", recs)
        self.assertIsInstance(recs["top_hogs"], list)


if __name__ == "__main__":
    unittest.main()
