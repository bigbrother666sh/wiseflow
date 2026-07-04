#!/usr/bin/env python3
"""Unit tests for login_manager.py (Phase 4.5.2 camoufox-cli path).

Covers:
- CLI exit codes (0/1/2) per documented contract
- Central storage IO at ~/.openclaw/logins/{platform}.json
- camoufox-cli invocation patterns (mocked)
- Platform validation against VALID_PLATFORMS
- status-all aggregation
- stdin/stdout JSON contract

All camoufox-cli and HTTP probe calls are mocked — these are unit tests,
integration tests are deferred to the post-deployment phase.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

# Add the scripts/ dir to import path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import login_manager  # noqa: E402


class TestPlatformValidation(unittest.TestCase):
    def test_valid_platforms_contains_required_set(self):
        for p in ("xhs-publish", "xhs-browse", "douyin", "bilibili",
                  "kuaishou", "weibo", "zhihu", "wechat-channels"):
            self.assertIn(p, login_manager.VALID_PLATFORMS)

    def test_validate_platform_raises_for_unknown(self):
        with self.assertRaises(SystemExit) as ctx:
            login_manager.validate_platform("not-a-platform")
        self.assertEqual(ctx.exception.code, 1)

    def test_validate_platform_passes_for_known(self):
        # Should not raise
        login_manager.validate_platform("xhs-browse")


class TestCentralStorage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.logins_dir = Path(self.tmp.name) / "logins"
        self.logins_dir.mkdir()
        self.patch = mock.patch.object(
            login_manager, "LOGINS_DIR", self.logins_dir
        )
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_storage_path_returns_json_file(self):
        path = login_manager.storage_path("xhs-browse")
        self.assertEqual(path, self.logins_dir / "xhs-browse.json")

    def test_read_missing_returns_none(self):
        self.assertIsNone(login_manager.read_storage("xhs-browse"))

    def test_write_then_read_roundtrip(self):
        payload = {"platform": "xhs-browse", "cookies": [{"name": "a", "value": "b"}]}
        login_manager.write_storage("xhs-browse", payload)
        out = login_manager.read_storage("xhs-browse")
        self.assertEqual(out, payload)

    def test_atomic_write_does_not_leave_partial_file(self):
        # If write fails, the file should not be partially updated
        target = login_manager.storage_path("xhs-browse")
        target.write_text('{"old": true}')
        with mock.patch("pathlib.Path.write_text", side_effect=OSError("boom")):
            with self.assertRaises(OSError):
                login_manager.write_storage("xhs-browse", {"new": True})
        # Original content preserved
        self.assertEqual(json.loads(target.read_text()), {"old": True})


class TestCheckCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.logins_dir = Path(self.tmp.name) / "logins"
        self.logins_dir.mkdir()
        self.patch = mock.patch.object(
            login_manager, "LOGINS_DIR", self.logins_dir
        )
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_check_missing_file_exits_2(self):
        with self.assertRaises(SystemExit) as ctx:
            login_manager.cmd_check("xhs-browse")
        self.assertEqual(ctx.exception.code, 2)

    @mock.patch("login_manager.probe_platform")
    def test_check_valid_session_exits_0(self, mock_probe):
        login_manager.write_storage("xhs-browse", {
            "platform": "xhs-browse",
            "cookies": [{"name": "web_session", "value": "xxx", "domain": ".xiaohongshu.com"}],
        })
        mock_probe.return_value = True
        out = StringIO()
        with mock.patch("sys.stdout", out):
            login_manager.cmd_check("xhs-browse")
        result = json.loads(out.getvalue())
        self.assertTrue(result["ok"])
        self.assertEqual(result["platform"], "xhs-browse")
        self.assertGreaterEqual(result["cookie_count"], 1)

    @mock.patch("login_manager.probe_platform")
    def test_check_invalid_session_exits_2(self, mock_probe):
        login_manager.write_storage("xhs-browse", {"platform": "xhs-browse", "cookies": []})
        mock_probe.return_value = False
        with self.assertRaises(SystemExit) as ctx:
            login_manager.cmd_check("xhs-browse")
        self.assertEqual(ctx.exception.code, 2)


class TestReadCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.logins_dir = Path(self.tmp.name) / "logins"
        self.logins_dir.mkdir()
        self.patch = mock.patch.object(
            login_manager, "LOGINS_DIR", self.logins_dir
        )
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_read_missing_exits_2(self):
        with self.assertRaises(SystemExit) as ctx:
            login_manager.cmd_read("xhs-browse")
        self.assertEqual(ctx.exception.code, 2)

    def test_read_existing_outputs_json(self):
        payload = {"platform": "xhs-browse", "cookies": []}
        login_manager.write_storage("xhs-browse", payload)
        out = StringIO()
        with mock.patch("sys.stdout", out):
            login_manager.cmd_read("xhs-browse")
        self.assertEqual(json.loads(out.getvalue()), payload)


class TestWriteCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.logins_dir = Path(self.tmp.name) / "logins"
        self.logins_dir.mkdir()
        self.patch = mock.patch.object(
            login_manager, "LOGINS_DIR", self.logins_dir
        )
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_write_from_stdin(self):
        payload = '{"platform": "xhs-browse", "cookies": [{"name": "a"}]}'
        with mock.patch("sys.stdin", StringIO(payload)):
            login_manager.cmd_write("xhs-browse")
        stored = login_manager.read_storage("xhs-browse")
        self.assertEqual(stored["platform"], "xhs-browse")
        self.assertEqual(stored["cookies"], [{"name": "a"}])

    def test_write_invalid_json_exits_1(self):
        with mock.patch("sys.stdin", StringIO("not-json{")):
            with self.assertRaises(SystemExit) as ctx:
                login_manager.cmd_write("xhs-browse")
        self.assertEqual(ctx.exception.code, 1)


class TestStatusAllCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.logins_dir = Path(self.tmp.name) / "logins"
        self.logins_dir.mkdir()
        self.patch = mock.patch.object(
            login_manager, "LOGINS_DIR", self.logins_dir
        )
        self.patch.start()
        self.addCleanup(self.patch.stop)

    @mock.patch("login_manager.probe_platform")
    def test_status_all_aggregates(self, mock_probe):
        # Two platforms stored, one valid, one invalid, one missing
        login_manager.write_storage("xhs-browse", {"platform": "xhs-browse", "cookies": []})
        login_manager.write_storage("douyin", {"platform": "douyin", "cookies": []})

        def probe_side_effect(platform, payload=None):
            return platform == "xhs-browse"
        mock_probe.side_effect = probe_side_effect

        out = StringIO()
        with mock.patch("sys.stdout", out):
            login_manager.cmd_status_all()
        # Output should be valid JSON listing each platform
        result = json.loads(out.getvalue())
        self.assertIn("platforms", result)
        platforms = {p["platform"]: p for p in result["platforms"]}
        self.assertTrue(platforms["xhs-browse"]["ok"])
        self.assertFalse(platforms["douyin"]["ok"])
        # xhs-publish was never written, not in result
        self.assertNotIn("xhs-publish", platforms)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["valid"], 1)
        self.assertEqual(result["expired"], 1)


class TestCamoufoxInvocation(unittest.TestCase):
    """Verify the camoufox-cli call shapes (mocked subprocess)."""

    @mock.patch("login_manager.subprocess.run")
    def test_open_persistent_session_uses_correct_flags(self, mock_run):
        mock_run.return_value = mock.Mock(
            returncode=0, stdout='{"success": true, "data": {}}'
        )
        login_manager.camoufox_open(
            session="xhs-browse-login",
            url="https://www.xiaohongshu.com/login",
            headless=True,
            persistent=True,
        )
        args, kwargs = mock_run.call_args
        cmd = args[0]
        # Verify command structure
        self.assertIn("camoufox-cli", cmd[0])
        self.assertIn("--session", cmd)
        self.assertIn("xhs-browse-login", cmd)
        self.assertIn("--persistent", cmd)
        self.assertIn("open", cmd)
        self.assertIn("https://www.xiaohongshu.com/login", cmd)

    @mock.patch("login_manager.subprocess.run")
    def test_cookies_export_writes_to_central_storage(self, mock_run):
        cookies = [
            {"name": "web_session", "value": "xyz", "domain": ".xiaohongshu.com",
             "path": "/", "expires": -1, "httpOnly": True, "secure": False,
             "sameSite": "Lax"},
        ]

        # The export-cookies call writes a tmp file at the path the impl computes.
        # We capture the cmd and write the cookies to that path, so the impl can
        # read it back. Return rc=0 with empty stdout (cli prints nothing on success).
        def run_side_effect(cmd, **kwargs):
            out_arg = None
            for i, a in enumerate(cmd):
                if a == "export" and i + 1 < len(cmd):
                    out_arg = cmd[i + 1]
                    break
            if out_arg:
                Path(out_arg).write_text(json.dumps(cookies))
            return mock.Mock(returncode=0, stdout="", stderr="")
        mock_run.side_effect = run_side_effect

        with tempfile.TemporaryDirectory() as tmp:
            logins_dir = Path(tmp) / "logins"
            logins_dir.mkdir()
            with mock.patch.object(login_manager, "LOGINS_DIR", logins_dir):
                login_manager.camoufox_export_cookies("xhs-browse", "xhs-browse-login")
                stored = json.loads((logins_dir / "xhs-browse.json").read_text())
        self.assertEqual(stored["platform"], "xhs-browse")
        self.assertEqual(stored["cookies"], cookies)
        self.assertIn("updated_at", stored)

    @mock.patch("login_manager.subprocess.run")
    def test_cookies_import_passes_storage_json(self, mock_run):
        mock_run.return_value = mock.Mock(returncode=0, stdout='{"success": true}')
        with tempfile.TemporaryDirectory() as tmp:
            logins_dir = Path(tmp) / "logins"
            logins_dir.mkdir()
            (logins_dir / "xhs-browse.json").write_text(json.dumps({
                "platform": "xhs-browse",
                "cookies": [{"name": "a", "value": "b"}],
            }))
            with mock.patch.object(login_manager, "LOGINS_DIR", logins_dir):
                login_manager.camoufox_import_cookies("xhs-browse", "agent-session-xyz")
        args, kwargs = mock_run.call_args
        cmd = args[0]
        self.assertIn("cookies", cmd)
        self.assertIn("import", cmd)
        self.assertIn("agent-session-xyz", cmd)
        # The temp file path should appear in the command
        self.assertTrue(any("xhs-browse" in str(c) for c in cmd))


class TestQrHeadlessCommand(unittest.TestCase):
    @mock.patch("login_manager.camoufox_open")
    @mock.patch("login_manager.snapshot_qr_to_file")
    def test_qr_headless_returns_png_path(self, mock_snapshot, mock_open):
        mock_open.return_value = '{"success": true}'
        mock_snapshot.return_value = "/tmp/qr-xhs-browse-XYZ.png"
        out = StringIO()
        with mock.patch("sys.stdout", out):
            login_manager.cmd_qr_headless(
                "xhs-browse", "https://www.xiaohongshu.com/login"
            )
        result = json.loads(out.getvalue())
        # Path comes from snapshot_qr_to_file (mocked); test that it round-trips
        self.assertEqual(result["qr_path"], "/tmp/qr-xhs-browse-XYZ.png")
        # Session name follows the {platform}-{purpose}-{nonce} pattern
        self.assertTrue(result["session"].startswith("xhs-browse-login-"))
        self.assertGreater(len(result["session"]), len("xhs-browse-login-"))


class TestQrConfirmCommand(unittest.TestCase):
    @mock.patch("login_manager.camoufox_export_cookies")
    @mock.patch("login_manager.poll_login_success")
    def test_qr_confirm_success(self, mock_poll, mock_export):
        mock_poll.return_value = True
        mock_export.return_value = None
        out = StringIO()
        with mock.patch("sys.stdout", out):
            login_manager.cmd_qr_confirm("xhs-browse", session="xhs-browse-login", timeout=5)
        result = json.loads(out.getvalue())
        self.assertTrue(result["ok"])
        mock_export.assert_called_once()

    @mock.patch("login_manager.poll_login_success")
    def test_qr_confirm_timeout_exits_2(self, mock_poll):
        mock_poll.return_value = False
        with self.assertRaises(SystemExit) as ctx:
            login_manager.cmd_qr_confirm("xhs-browse", session="xhs-browse-login", timeout=1)
        self.assertEqual(ctx.exception.code, 2)


class TestSessionNaming(unittest.TestCase):
    def test_session_name_format(self):
        name = login_manager.session_name("xhs-browse", "login")
        self.assertTrue(name.startswith("xhs-browse-login-"))
        # Suffix should be a non-empty nonce
        suffix = name[len("xhs-browse-login-"):]
        self.assertGreater(len(suffix), 0)


class TestCookieHeaderCompat(unittest.TestCase):
    """兼容旧 CDP 路径的 cookies 字符串格式（Phase 4.5 前的中央 JSON）"""

    def test_old_string_cookies_passthrough(self):
        payload = {"cookies": "abRequestId=x; webId=y; web_session=z"}
        out = login_manager._cookie_header_from_payload(payload, "xiaohongshu.com")
        self.assertEqual(out, "abRequestId=x; webId=y; web_session=z")

    def test_new_list_cookies_filtered_by_domain(self):
        payload = {
            "cookies": [
                {"name": "a", "value": "1", "domain": ".xiaohongshu.com"},
                {"name": "b", "value": "2", "domain": ".douyin.com"},
            ]
        }
        out = login_manager._cookie_header_from_payload(payload, "xiaohongshu.com")
        self.assertIn("a=1", out)
        self.assertNotIn("b=2", out)

    def test_empty_cookies_returns_empty(self):
        self.assertEqual(login_manager._cookie_header_from_payload({}, "x.com"), "")
        self.assertEqual(login_manager._cookie_header_from_payload({"cookies": []}, "x.com"), "")
        self.assertEqual(login_manager._cookie_header_from_payload({"cookies": None}, "x.com"), "")


if __name__ == "__main__":
    unittest.main()
