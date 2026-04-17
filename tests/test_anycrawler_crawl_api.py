from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "skill" / "anycrawler" / "scripts" / "anycrawler_crawl_api.py"
SPEC = importlib.util.spec_from_file_location("anycrawler_crawl_api", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class AnyCrawlerCrawlApiTests(unittest.TestCase):
    def test_user_agent_uses_version_file(self) -> None:
        version = (MODULE.SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()

        self.assertEqual(MODULE.SKILL_VERSION, version)
        self.assertEqual(MODULE.DEFAULT_SKILL_USER_AGENT, f"Anycrawler Agent Skill v{version}")

    def test_page_payload_omits_browser_wait_until_for_fetch(self) -> None:
        args = argparse.Namespace(
            url="https://example.com",
            method="fetch",
            accept_cache=False,
            include_metadata=False,
            include_links=False,
            include_media=False,
            markdown_variant="markdown",
            browser_wait_until="networkidle2",
            user_agent=None,
        )

        payload = MODULE._page_payload(args)

        self.assertNotIn("browser_wait_until", payload)

    def test_main_writes_output_and_returns_nonzero_on_failed_page_request(self) -> None:
        wrapper = {
            "data": {
                "ok": False,
                "error": "INVALID_REQUEST",
                "retryable": False,
            },
            "meta": {
                "status": 400,
                "requestId": "req_test",
                "creditsReserved": 0,
                "creditsUsed": 0,
                "browserMsUsed": 0,
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "wrapper.json"
            markdown_path = Path(temp_dir) / "out.md"
            argv = [
                "anycrawler_crawl_api.py",
                "page",
                "--url",
                "https://example.com",
                "--api-key",
                "test-key",
                "--output",
                str(output_path),
                "--write-markdown",
                str(markdown_path),
                "--silent",
            ]

            with mock.patch.object(MODULE, "_perform_request", return_value=(wrapper, 400)):
                with mock.patch("sys.argv", argv):
                    exit_code = MODULE.main()

            self.assertEqual(exit_code, 1)
            self.assertTrue(output_path.exists())
            self.assertFalse(markdown_path.exists())
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), wrapper)

    def test_parser_supports_version_flag(self) -> None:
        parser = MODULE._build_parser()

        with self.assertRaises(SystemExit) as exc:
            parser.parse_args(["--version"])

        self.assertEqual(exc.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
