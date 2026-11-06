"""Offline tests for organization profile badges."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import update_profile_metrics as metrics


class ProfileMetricsTests(unittest.TestCase):
    def test_merged_pr_count(self):
        with patch.object(metrics, "api", side_effect=[
            {"total_count": 12, "incomplete_results": False},
            {"total_count": 34, "incomplete_results": False},
        ]) as api:
            self.assertEqual(metrics.merged_pr_count(), 46)
            self.assertEqual(api.call_count, 2)

    def test_incomplete_search(self):
        with patch.object(metrics, "api", return_value={"total_count": 10, "incomplete_results": True}):
            with self.assertRaises(ValueError):
                metrics.merged_pr_count()

    def test_public_size_only(self):
        def fake_api(path):
            if "/users/trvny/repos" in path:
                return [
                    {"owner": {"login": "trvny"}, "visibility": "public", "size": 1024},
                    {"owner": {"login": "trvny"}, "visibility": "private", "size": 9999},
                ]
            return [{"owner": {"login": "travnie"}, "visibility": "public", "size": 2048}]
        with patch.object(metrics, "api", side_effect=fake_api):
            self.assertEqual(metrics.repository_sizes(), (3072, 2))

    def test_github_host_is_fixed(self):
        with patch.object(metrics.http.client, "HTTPSConnection") as constructor:
            fake = constructor.return_value
            fake.getresponse.return_value.status = 200
            fake.getresponse.return_value.read.return_value = b'{"total_count": 5}'
            self.assertEqual(metrics.api("/search/issues?q=x&per_page=1")["total_count"], 5)
            constructor.assert_called_once_with("api.github.com", timeout=20)

    def test_api_path_allowlist(self):
        with self.assertRaises(ValueError):
            metrics.api("//evil.example/path")

    def test_endpoint_schema(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(metrics, "OUT", Path(tmp)):
            metrics.badge("pr.json", "merged PRs", "46", "8250df", "pr")
            result = json.loads(Path(tmp, "pr.json").read_text(encoding="utf-8"))
            self.assertEqual(result["schemaVersion"], 1)
            self.assertEqual(result["message"], "46")
            self.assertIn("<svg", result["logoSvg"])


if __name__ == "__main__":
    unittest.main()
