from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import unittest
import sys
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "skills" / "anycrawler-search" / "scripts" / "anycrawler_search_api.py"
SPEC = importlib.util.spec_from_file_location("anycrawler_search_api", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class AnyCrawlerSearchApiTests(unittest.TestCase):
    def test_search_docs_exclude_removed_fields_and_cache_discussion(self) -> None:
        search_root = MODULE.SKILL_ROOT
        checked_paths = (
            search_root / "SKILL.md",
            search_root / "references" / "public-api.md",
            search_root / "references" / "maintainer.md",
        )

        for path in checked_paths:
            content = path.read_text(encoding="utf-8").lower()
            with self.subTest(path=path):
                self.assertNotIn("cache", content)
                self.assertNotIn("`language`", content)
                self.assertNotIn("`location`", content)
                self.assertIn("results_per_page", content)

    def test_user_agent_uses_version_file(self) -> None:
        version = (MODULE.SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()

        self.assertEqual(MODULE.SKILL_VERSION, version)
        self.assertEqual(MODULE.DEFAULT_SKILL_USER_AGENT, f"Anycrawler Search Agent Skill v{version}")

    def test_search_payload_omits_empty_optional_locale_fields(self) -> None:
        args = argparse.Namespace(
            channel="page",
            query="site reliability engineering",
            country=None,
            page=1,
            results_per_page=10,
        )

        payload = MODULE._search_payload(args)

        self.assertEqual(
            payload,
            {
                "channel": "page",
                "query": "site reliability engineering",
                "page": 1,
                "results_per_page": 10,
            },
        )

    def test_search_payload_includes_only_supported_optional_country(self) -> None:
        args = argparse.Namespace(
            channel="news",
            query="AnyCrawler",
            country="us",
            page=2,
            results_per_page=25,
        )

        payload = MODULE._search_payload(args)

        self.assertEqual(payload["channel"], "news")
        self.assertEqual(payload["country"], "us")
        self.assertEqual(payload["page"], 2)
        self.assertEqual(payload["results_per_page"], 25)
        self.assertEqual(
            set(payload),
            {"channel", "query", "country", "page", "results_per_page"},
        )

    def test_parser_supports_all_search_channels(self) -> None:
        parser = MODULE._build_parser()

        for channel in MODULE.SEARCH_CHANNELS:
            args = parser.parse_args([channel, "--query", "example"])
            self.assertEqual(args.channel, channel)
            self.assertEqual(args.query, "example")

    def test_parser_rejects_removed_search_fields(self) -> None:
        parser = MODULE._build_parser()

        for field in ("--language", "--location"):
            with self.subTest(field=field), self.assertRaises(SystemExit) as exc:
                parser.parse_args(["page", "--query", "example", field, "value"])

            self.assertEqual(exc.exception.code, 2)

    def test_parser_enforces_results_per_page_bounds(self) -> None:
        parser = MODULE._build_parser()

        self.assertEqual(
            parser.parse_args(["page", "--query", "example"]).results_per_page,
            10,
        )
        for value in ("0", "101"):
            with self.subTest(value=value), self.assertRaises(SystemExit) as exc:
                parser.parse_args(
                    ["page", "--query", "example", "--results-per-page", value]
                )

            self.assertEqual(exc.exception.code, 2)

    def test_parser_enforces_search_text_contract(self) -> None:
        parser = MODULE._build_parser()

        invalid_argv = (
            ["page", "--query", "   "],
            ["page", "--query", "x" * 513],
            ["page", "--query", "example", "--country", "x" * 129],
        )
        for argv in invalid_argv:
            with self.subTest(argv=argv), self.assertRaises(SystemExit) as exc:
                parser.parse_args(argv)

            self.assertEqual(exc.exception.code, 2)

        args = parser.parse_args(["page", "--query", "  example  ", "--country", " us "])
        self.assertEqual(args.query, "example")
        self.assertEqual(args.country, "us")

    def test_parser_supports_version_flag(self) -> None:
        parser = MODULE._build_parser()

        with self.assertRaises(SystemExit) as exc:
            parser.parse_args(["--version"])

        self.assertEqual(exc.exception.code, 0)

    def test_main_writes_output_and_returns_nonzero_on_failed_request(self) -> None:
        wrapper = {
            "data": {
                "ok": False,
                "error_code": "INVALID_REQUEST",
                "error_message": "Invalid request",
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
            argv = [
                "page",
                "--query",
                "example",
                "--api-key",
                "test-key",
                "--output",
                str(output_path),
                "--silent",
            ]

            with mock.patch.object(MODULE, "_perform_request", return_value=(wrapper, 400)) as perform_request:
                exit_code = MODULE.main(argv)

            self.assertEqual(exit_code, 1)
            self.assertTrue(output_path.exists())
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), wrapper)
            perform_request.assert_called_once()
            call_kwargs = perform_request.call_args.kwargs
            self.assertEqual(call_kwargs["payload"]["channel"], "page")
            self.assertEqual(call_kwargs["payload"]["query"], "example")
            self.assertEqual(call_kwargs["payload"]["results_per_page"], 10)

    def test_perform_request_posts_to_single_search_endpoint_with_channel_payload(self) -> None:
        class FakeResponse:
            headers = {
                "x-request-id": "req_test",
                "x-credits-reserved": "20",
                "x-credits-used": "20",
                "x-browser-ms-used": "0",
            }

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def getcode(self) -> int:
                return 200

            def read(self) -> bytes:
                return b'{"ok": true}'

        captured_request = None

        def fake_urlopen(request: object, timeout: float) -> FakeResponse:
            nonlocal captured_request
            captured_request = request
            self.assertEqual(timeout, 12.5)
            return FakeResponse()

        payload = {
            "channel": "images",
            "query": "example",
            "page": 1,
        }

        with mock.patch.object(MODULE.urllib_request, "urlopen", side_effect=fake_urlopen):
            wrapper, status = MODULE._perform_request(
                api_key="test-key",
                base_url="https://api.anycrawler.test/",
                payload=payload,
                timeout=12.5,
            )

        self.assertEqual(status, 200)
        self.assertEqual(wrapper["data"], {"ok": True})
        self.assertIsNotNone(captured_request)
        self.assertEqual(captured_request.full_url, "https://api.anycrawler.test/v1/search")
        self.assertEqual(json.loads(captured_request.data.decode("utf-8")), payload)

    def test_main_rejects_missing_api_key(self) -> None:
        with mock.patch.dict(MODULE.os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as exc:
                MODULE.main(["page", "--query", "example", "--silent"])

        self.assertIn("Missing API key", str(exc.exception))


if __name__ == "__main__":
    unittest.main()
