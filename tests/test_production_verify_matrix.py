#!/usr/bin/env python3
"""Unit tests for production verification transport/rollback decisions."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "tools" / "verify_seo_production.py"


def load_verify_module():
    spec = importlib.util.spec_from_file_location("verify_seo_production_test", VERIFY_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load production verifier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.TARGET_RETRY_DELAY_SECONDS = 0
    module.STARTED_AT = module.time.monotonic()
    return module


class ProductionVerifyMatrixTest(unittest.TestCase):
    def setUp(self):
        self.verify = load_verify_module()

    def result(self, status: int, curl_exit: int = 0):
        return self.verify.FetchResult(status, {}, b"", curl_exit, 1)

    def test_target_only_failure_retries_three_times_then_requests_rollback(self):
        responses = iter((self.result(0, 28), self.result(200), self.result(0, 28), self.result(0, 28)))
        calls = []

        def fake_fetch(path, *, purpose, attempt):
            calls.append((path, purpose, attempt))
            return next(responses)

        with mock.patch.object(self.verify, "_fetch_once", side_effect=fake_fetch):
            with self.assertRaises(self.verify.TargetUnavailable):
                self.verify.fetch("/contact.html")

        self.assertEqual(
            calls,
            [
                ("/contact.html", "target", 1),
                ("/robots.txt", "control-after-target-failure", 1),
                ("/contact.html", "target-retry", 2),
                ("/contact.html", "target-retry", 3),
            ],
        )

    def test_target_and_control_transport_failure_requires_manual_check_without_rollback(self):
        responses = iter((self.result(0, 28), self.result(0, 28)))
        with mock.patch.object(self.verify, "_fetch_once", side_effect=lambda *args, **kwargs: next(responses)):
            with self.assertRaises(self.verify.ManualCheckRequired):
                self.verify.fetch("/business.html")

    def test_reachable_control_allows_single_target_recovery(self):
        responses = iter((self.result(0, 28), self.result(200), self.result(200)))
        with mock.patch.object(self.verify, "_fetch_once", side_effect=lambda *args, **kwargs: next(responses)):
            result = self.verify.fetch("/works.html")
        self.assertEqual(result.status, 200)

    def test_primary_page_4xx_or_5xx_is_an_immediate_rollback_decision(self):
        with mock.patch.object(self.verify, "fetch", return_value=self.result(503)):
            with self.assertRaises(self.verify.ContentVerificationFailure):
                self.verify.verify_html("/contact.html", "/contact.html")

    def test_initial_control_and_target_both_unreachable_requires_manual_check(self):
        responses = iter((self.result(0, 28), self.result(0, 28), self.result(0, 28)))
        with mock.patch.object(self.verify, "_fetch_once", side_effect=lambda *args, **kwargs: next(responses)):
            with self.assertRaises(self.verify.ManualCheckRequired):
                self.verify.establish_initial_control()

    def test_curl_probe_records_http_status_exit_code_and_duration(self):
        def fake_run(command, **_kwargs):
            Path(command[command.index("--output") + 1]).write_bytes(b"ok")
            Path(command[command.index("--dump-header") + 1]).write_bytes(b"HTTP/1.1 200 OK\r\nX-Test: yes\r\n\r\n")
            return subprocess.CompletedProcess(command, 0, stdout="200", stderr="")

        captured = io.StringIO()
        with mock.patch.object(self.verify.subprocess, "run", side_effect=fake_run):
            with contextlib.redirect_stdout(captured):
                result = self.verify._fetch_once("/robots.txt", purpose="test", attempt=1)

        self.assertEqual((result.status, result.curl_exit, result.payload), (200, 0, b"ok"))
        self.assertEqual(result.headers["x-test"], "yes")
        self.assertIn('"http_status": 200', captured.getvalue())
        self.assertIn('"curl_exit": 0', captured.getvalue())
        self.assertIn('"duration_ms":', captured.getvalue())


if __name__ == "__main__":
    unittest.main()
