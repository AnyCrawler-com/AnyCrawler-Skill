from __future__ import annotations

import argparse
import importlib.util
import json
import os
import tempfile
import unittest
import sys
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "skills" / "anycrawler-read" / "scripts" / "anycrawler_crawl_api.py"
SPEC = importlib.util.spec_from_file_location("anycrawler_crawl_api", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class AnyCrawlerCrawlApiTests(unittest.TestCase):
    def _write_skill_tree(self, root: Path, version: str, *, extra_files: dict[str, str] | None = None) -> None:
        files = {
            "SKILL.md": "---\nname: anycrawler-read\n---\n",
            "VERSION": version + "\n",
            "agents/openai.yaml": "interface: {}\n",
            "references/public-api.md": "# Public API\n",
            "scripts/anycrawler_crawl_api.py": "#!/usr/bin/env python3\n",
        }
        if extra_files:
            files.update(extra_files)

        for relative_path, content in files.items():
            path = root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def test_user_agent_uses_version_file(self) -> None:
        version = (MODULE.SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()

        self.assertEqual(MODULE.SKILL_VERSION, version)
        self.assertEqual(MODULE.DEFAULT_SKILL_USER_AGENT, f"Anycrawler Agent Skill v{version}")

    def test_page_payload_omits_render_only_fields_for_fetch(self) -> None:
        args = argparse.Namespace(
            url="https://example.com",
            method="fetch",
            accept_cache=True,
            include_metadata=False,
            include_links=False,
            include_media=False,
            markdown_variant="markdown",
            browser_wait_until="networkidle2",
            user_agent=None,
        )

        payload = MODULE._page_payload(args)

        self.assertNotIn("browser_wait_until", payload)
        self.assertNotIn("accept_cache", payload)

    def test_page_payload_keeps_render_cache_fields_for_render(self) -> None:
        args = argparse.Namespace(
            url="https://example.com",
            method="render",
            accept_cache=True,
            include_metadata=False,
            include_links=False,
            include_media=False,
            markdown_variant="markdown",
            browser_wait_until="networkidle2",
            user_agent=None,
        )

        payload = MODULE._page_payload(args)

        self.assertEqual(payload["accept_cache"], True)
        self.assertEqual(payload["browser_wait_until"], "networkidle2")

    def test_main_writes_output_and_returns_nonzero_on_failed_free_fetch_request(self) -> None:
        wrapper = {
            "data": {
                "ok": False,
                "status_code": 403,
                "error": {
                    "code": "ROBOTS_DISALLOWED",
                    "message": "Crawling is disallowed by robots.txt for this URL.",
                },
            },
            "meta": {
                "status": 403,
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "wrapper.json"
            markdown_path = Path(temp_dir) / "out.md"
            argv = [
                "page",
                "--url",
                "https://example.com",
                "--output",
                str(output_path),
                "--write-markdown",
                str(markdown_path),
                "--silent",
            ]

            with mock.patch.object(MODULE, "_run_auto_update_preflight", return_value=False):
                with mock.patch.object(MODULE, "_perform_free_fetch_request", return_value=(wrapper, 403)):
                    exit_code = MODULE.main(argv)

            self.assertEqual(exit_code, 1)
            self.assertTrue(output_path.exists())
            self.assertFalse(markdown_path.exists())
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), wrapper)

    def test_free_fetch_request_uses_free_endpoint_without_authorization(self) -> None:
        class FakeResponse:
            headers = {
                "x-edge-cache": "MISS",
            }

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def getcode(self) -> int:
                return 200

            def read(self) -> bytes:
                return b'{"ok": true, "results": {"markdown": "# Example"}}'

        captured_request = None

        def fake_urlopen(request: object, timeout: float) -> FakeResponse:
            nonlocal captured_request
            captured_request = request
            self.assertEqual(timeout, 12.5)
            return FakeResponse()

        with mock.patch.object(MODULE.urllib_request, "urlopen", side_effect=fake_urlopen):
            wrapper, status = MODULE._perform_free_fetch_request(
                base_url="https://api.anycrawler.test/",
                target_url="https://example.com/path?a=1&b=2",
                timeout=12.5,
            )

        self.assertEqual(status, 200)
        self.assertEqual(wrapper["data"], {"ok": True, "results": {"markdown": "# Example"}})
        self.assertIsNotNone(captured_request)
        self.assertEqual(captured_request.get_method(), "GET")
        self.assertEqual(
            captured_request.full_url,
            "https://api.anycrawler.test/free/v1/crawl?url=https%3A%2F%2Fexample.com%2Fpath%3Fa%3D1%26b%3D2",
        )
        self.assertIsNone(captured_request.get_header("Authorization"))

    def test_main_fetch_uses_free_endpoint_without_api_key(self) -> None:
        wrapper = {
            "data": {
                "ok": True,
                "results": {
                    "markdown": "# Example",
                },
            },
            "meta": {
                "status": 200,
            },
        }

        with mock.patch.dict(MODULE.os.environ, {}, clear=True):
            with mock.patch.object(MODULE, "_run_auto_update_preflight", return_value=False):
                with mock.patch.object(MODULE, "_perform_free_fetch_request", return_value=(wrapper, 200)) as free_fetch:
                    with mock.patch.object(MODULE, "_perform_request") as public_request:
                        exit_code = MODULE.main(["page", "--url", "https://example.com", "--silent"])

        self.assertEqual(exit_code, 0)
        free_fetch.assert_called_once()
        public_request.assert_not_called()

    def test_parser_supports_version_flag(self) -> None:
        parser = MODULE._build_parser()

        with self.assertRaises(SystemExit) as exc:
            parser.parse_args(["--version"])

        self.assertEqual(exc.exception.code, 0)

    def test_parse_version_tuple_accepts_tag_prefix(self) -> None:
        self.assertEqual(MODULE._parse_version_tuple("v1.2.3"), (1, 2, 3))
        self.assertEqual(MODULE._parse_version_tuple("1.2.3"), (1, 2, 3))
        self.assertIsNone(MODULE._parse_version_tuple("v1.2.3-rc1"))

    def test_fetch_latest_release_tag_picks_highest_semver(self) -> None:
        tags_payload = [
            {"name": "v0.1.9"},
            {"name": "docs-refresh"},
            {"name": "v0.10.0"},
            {"name": "v0.2.0"},
        ]

        with mock.patch.object(MODULE, "_fetch_json", return_value=tags_payload):
            self.assertEqual(
                MODULE._fetch_latest_release_tag(timeout=5.0, repository="AnyCrawler-com/AnyCrawler-Skill"),
                ("v0.10.0", "0.10.0"),
            )

    def test_replace_managed_skill_root_swaps_in_staged_tree_and_keeps_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            skill_root = temp_path / ".codex" / "skills" / "anycrawler-read"
            state_dir = temp_path / ".codex" / "skills" / ".anycrawler-read-state"
            staged_skill_root = temp_path / "staged-anycrawler-read"

            self._write_skill_tree(skill_root, "0.1.0", extra_files={"obsolete.txt": "old\n"})
            self._write_skill_tree(staged_skill_root, "0.1.1", extra_files={"fresh.txt": "new\n"})

            backup_root = MODULE._replace_managed_skill_root(
                skill_root=skill_root,
                staged_skill_root=staged_skill_root,
                state_dir=state_dir,
            )

            self.assertEqual((skill_root / "VERSION").read_text(encoding="utf-8").strip(), "0.1.1")
            self.assertTrue((skill_root / "fresh.txt").exists())
            self.assertFalse((skill_root / "obsolete.txt").exists())
            self.assertEqual((backup_root / "VERSION").read_text(encoding="utf-8").strip(), "0.1.0")
            self.assertTrue((backup_root / "obsolete.txt").exists())

    def test_auto_update_preflight_runs_once_per_session_when_current(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            skill_root = temp_path / ".codex" / "skills" / "anycrawler-read"
            state_dir = temp_path / ".codex" / "skills" / ".anycrawler-read-state"
            self._write_skill_tree(skill_root, "0.1.1")

            with mock.patch.dict(
                os.environ,
                {
                    "ANYCRAWLER_MANAGED_INSTALL_ROOT": str(skill_root),
                    "ANYCRAWLER_STATE_DIR": str(state_dir),
                },
                clear=False,
            ):
                with mock.patch.object(MODULE, "_discover_session_key", return_value="session-1"):
                    with mock.patch.object(
                        MODULE,
                        "_fetch_latest_release_tag",
                        return_value=("v0.1.1", "0.1.1"),
                    ) as fetch_latest:
                        argv = ["page", "--url", "https://example.com"]
                        self.assertFalse(MODULE._run_auto_update_preflight(argv, skill_root=skill_root))
                        self.assertFalse(MODULE._run_auto_update_preflight(argv, skill_root=skill_root))

            self.assertEqual(fetch_latest.call_count, 1)
            state = json.loads((state_dir / MODULE.SESSION_STATE_FILE_NAME).read_text(encoding="utf-8"))
            self.assertEqual(state["sessions"]["session-1"]["outcome"], "current")

    def test_auto_update_preflight_skips_non_managed_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            skill_root = Path(temp_dir) / "repo-copy" / "skills" / "anycrawler-read"
            self._write_skill_tree(skill_root, "0.1.0")

            with mock.patch.object(MODULE, "_fetch_latest_release_tag") as fetch_latest:
                result = MODULE._run_auto_update_preflight(["page", "--url", "https://example.com"], skill_root=skill_root)

            self.assertFalse(result)
            fetch_latest.assert_not_called()

    def test_auto_update_preflight_updates_outdated_managed_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            skill_root = temp_path / ".codex" / "skills" / "anycrawler-read"
            state_dir = temp_path / ".codex" / "skills" / ".anycrawler-read-state"
            self._write_skill_tree(skill_root, "0.1.0")

            with mock.patch.dict(
                os.environ,
                {
                    "ANYCRAWLER_MANAGED_INSTALL_ROOT": str(skill_root),
                    "ANYCRAWLER_STATE_DIR": str(state_dir),
                },
                clear=False,
            ):
                with mock.patch.object(MODULE, "_discover_session_key", return_value="session-2"):
                    with mock.patch.object(
                        MODULE,
                        "_fetch_latest_release_tag",
                        return_value=("v0.1.1", "0.1.1"),
                    ):
                        with mock.patch.object(MODULE, "_perform_skill_self_update") as perform_update:
                            result = MODULE._run_auto_update_preflight(
                                ["page", "--url", "https://example.com"],
                                skill_root=skill_root,
                            )

            self.assertTrue(result)
            perform_update.assert_called_once()
            state = json.loads((state_dir / MODULE.SESSION_STATE_FILE_NAME).read_text(encoding="utf-8"))
            self.assertEqual(state["sessions"]["session-2"]["outcome"], "updated")

    def test_auto_update_preflight_degrades_on_remote_check_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            skill_root = temp_path / ".codex" / "skills" / "anycrawler-read"
            state_dir = temp_path / ".codex" / "skills" / ".anycrawler-read-state"
            self._write_skill_tree(skill_root, "0.1.0")

            with mock.patch.dict(
                os.environ,
                {
                    "ANYCRAWLER_MANAGED_INSTALL_ROOT": str(skill_root),
                    "ANYCRAWLER_STATE_DIR": str(state_dir),
                },
                clear=False,
            ):
                with mock.patch.object(MODULE, "_discover_session_key", return_value="session-3"):
                    with mock.patch.object(
                        MODULE,
                        "_fetch_latest_release_tag",
                        side_effect=RuntimeError("network unavailable"),
                    ):
                        result = MODULE._run_auto_update_preflight(
                            ["page", "--url", "https://example.com"],
                            skill_root=skill_root,
                        )

            self.assertFalse(result)
            state = json.loads((state_dir / MODULE.SESSION_STATE_FILE_NAME).read_text(encoding="utf-8"))
            self.assertEqual(state["sessions"]["session-3"]["outcome"], "error")

    def test_main_rejects_missing_api_key_for_render(self) -> None:
        with mock.patch.dict(MODULE.os.environ, {}, clear=True):
            with mock.patch.object(MODULE, "_run_auto_update_preflight", return_value=False):
                with self.assertRaises(SystemExit) as exc:
                    MODULE.main(["page", "--method", "render", "--url", "https://example.com", "--silent"])

        self.assertIn("Missing API key", str(exc.exception))

    def test_main_reexecs_after_successful_auto_update(self) -> None:
        argv = ["page", "--url", "https://example.com", "--api-key", "test-key"]

        with mock.patch.object(MODULE, "_run_auto_update_preflight", return_value=True):
            with mock.patch.object(MODULE.os, "execv", side_effect=SystemExit(0)) as execv:
                with self.assertRaises(SystemExit) as exc:
                    MODULE.main(argv)

        self.assertEqual(exc.exception.code, 0)
        execv.assert_called_once_with(
            sys.executable,
            [sys.executable, str(MODULE.SCRIPT_FILE), *argv],
        )


if __name__ == "__main__":
    unittest.main()
