#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request


DEFAULT_BASE_URL = "https://api.anycrawler.com"
SKILL_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = SKILL_ROOT / "VERSION"


def _load_skill_version() -> str:
    try:
        version = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Failed to read skill version from {VERSION_FILE}.") from exc

    if not version:
        raise RuntimeError(f"Skill version file is empty: {VERSION_FILE}")

    return version


SKILL_VERSION = _load_skill_version()
DEFAULT_SKILL_USER_AGENT = f"Anycrawler Agent Skill v{SKILL_VERSION}"


def _parse_optional_number(value: str | None) -> int | None:
    if value in (None, ""):
        return None

    try:
        return int(value)
    except ValueError:
        try:
            return int(float(value))
        except ValueError:
            return None


def _build_meta(status: int, headers: Any) -> dict[str, Any]:
    return {
        "status": status,
        "requestId": headers.get("x-request-id"),
        "creditsReserved": _parse_optional_number(headers.get("x-credits-reserved")),
        "creditsUsed": _parse_optional_number(headers.get("x-credits-used")),
        "browserMsUsed": _parse_optional_number(headers.get("x-browser-ms-used")),
    }


def _parse_json(text: str) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _resolve_api_key(explicit_key: str | None, env_name: str) -> str:
    if explicit_key:
        return explicit_key

    env_value = os.getenv(env_name)
    if env_value:
        return env_value

    raise SystemExit(f"Missing API key. Pass --api-key or set {env_name}.")


def _write_text_file(path: str | Path, content: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def _write_json_file(path: str | Path, payload: Any) -> None:
    _write_text_file(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _download_file(url: str, path: str | Path, timeout: float) -> None:
    request = urllib_request.Request(
        url,
        headers={
            "Accept": "*/*",
            "User-Agent": DEFAULT_SKILL_USER_AGENT,
        },
        method="GET",
    )
    try:
        with urllib_request.urlopen(request, timeout=timeout) as response:
            output_path = Path(path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("wb") as output_file:
                shutil.copyfileobj(response, output_file)
    except urllib_error.HTTPError as exc:
        message = f"Snapshot download failed with HTTP {exc.code} {exc.reason} for {url}"
        raise SystemExit(message) from exc
    except urllib_error.URLError as exc:
        message = f"Snapshot download failed before receiving an HTTP response: {exc.reason}"
        raise SystemExit(message) from exc


def _perform_request(
    *,
    api_key: str,
    base_url: str,
    pathname: str,
    payload: dict[str, Any],
    timeout: float,
) -> tuple[dict[str, Any], int]:
    request = urllib_request.Request(
        f"{_normalize_base_url(base_url)}{pathname}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": DEFAULT_SKILL_USER_AGENT,
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=timeout) as response:
            status = response.getcode()
            body = response.read().decode("utf-8")
            return {
                "data": _parse_json(body),
                "meta": _build_meta(status, response.headers),
            }, status
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "data": _parse_json(body),
            "meta": _build_meta(exc.code, exc.headers),
        }, exc.code
    except urllib_error.URLError as exc:
        message = f"AnyCrawler request failed before receiving an HTTP response: {exc.reason}"
        raise SystemExit(message) from exc


def _page_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "url": args.url,
        "method": args.method,
        "accept_cache": args.accept_cache,
        "include_metadata": args.include_metadata,
        "include_links": args.include_links,
        "include_media": args.include_media,
        "markdown_variant": args.markdown_variant,
    }
    if args.method == "render" and args.browser_wait_until is not None:
        payload["browser_wait_until"] = args.browser_wait_until
    if args.user_agent is not None:
        payload["user_agent"] = args.user_agent
    return payload


def _screenshot_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "url": args.url,
        "full_page": args.full_page,
    }
    if args.aspect_ratio is not None:
        payload["aspect_ratio"] = args.aspect_ratio
    if args.user_agent is not None:
        payload["user_agent"] = args.user_agent
    return payload


def _write_markdown_output(wrapper: dict[str, Any], path: str | Path) -> None:
    data = wrapper.get("data")
    if not isinstance(data, dict):
        raise SystemExit("Cannot write markdown because the response body is not a JSON object.")

    results = data.get("results")
    if not isinstance(results, dict):
        raise SystemExit("Cannot write markdown because the response does not contain results.")

    markdown = results.get("markdown")
    if not isinstance(markdown, str):
        raise SystemExit("Cannot write markdown because results.markdown is missing.")

    _write_text_file(path, markdown)


def _download_snapshot_output(wrapper: dict[str, Any], path: str | Path, timeout: float) -> None:
    data = wrapper.get("data")
    if not isinstance(data, dict):
        raise SystemExit("Cannot download snapshot because the response body is not a JSON object.")

    results = data.get("results")
    if not isinstance(results, dict):
        raise SystemExit("Cannot download snapshot because the response does not contain results.")

    snapshot_url = results.get("snapshot_url")
    if not isinstance(snapshot_url, str):
        raise SystemExit("Cannot download snapshot because results.snapshot_url is missing.")

    _download_file(snapshot_url, path, timeout)


def _request_succeeded(wrapper: dict[str, Any], status: int) -> bool:
    data = wrapper.get("data")
    return status < 400 and not (isinstance(data, dict) and data.get("ok") is False)


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--api-key",
        help="API key to send in the Authorization header. Defaults to the env var from --api-key-env.",
    )
    parser.add_argument(
        "--api-key-env",
        default="ANYCRAWLER_API_KEY",
        help="Environment variable name that stores the API key. Default: ANYCRAWLER_API_KEY.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("ANYCRAWLER_BASE_URL", DEFAULT_BASE_URL),
        help=f"AnyCrawler base URL. Default: {DEFAULT_BASE_URL} or ANYCRAWLER_BASE_URL when set.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="HTTP timeout in seconds. Default: 60.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to save the full JSON wrapper {data, meta}. Use --silent to suppress stdout JSON.",
    )
    parser.add_argument(
        "-s",
        "--silent",
        action="store_true",
        help="Do not print the JSON wrapper to stdout.",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Call AnyCrawler public crawl APIs with the stable documented contract.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {SKILL_VERSION}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    page = subparsers.add_parser("page", help="Call POST /v1/crawl/page.")
    _add_common_arguments(page)
    page.add_argument("--url", required=True, help="Target URL.")
    page.add_argument(
        "--method",
        choices=("render", "fetch"),
        default="fetch",
        help="Crawl method. Default: fetch.",
    )
    page.add_argument("--accept-cache", action="store_true", help="Set accept_cache=true.")
    page.add_argument("--include-metadata", action="store_true", help="Set include_metadata=true.")
    page.add_argument("--include-links", action="store_true", help="Set include_links=true.")
    page.add_argument("--include-media", action="store_true", help="Set include_media=true.")
    page.add_argument("--markdown-variant", choices=("markdown", "readability"), default="markdown")
    page.add_argument(
        "--browser-wait-until",
        choices=("domcontentloaded", "load", "networkidle0", "networkidle2"),
        help="Set browser_wait_until. Only meaningful when --method render.",
    )
    page.add_argument("--user-agent", help="Paid-plan-only user_agent override.")
    page.add_argument(
        "--write-markdown",
        help="Optional path to save response.data.results.markdown.",
    )

    screenshot = subparsers.add_parser("screenshot", help="Call POST /v1/crawl/screenshot.")
    _add_common_arguments(screenshot)
    screenshot.add_argument("--url", required=True, help="Target URL.")
    screenshot.add_argument(
        "--full-page",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Capture a full-page screenshot. Use --no-full-page for viewport mode.",
    )
    screenshot.add_argument(
        "--aspect-ratio",
        choices=("16:9", "9:16", "1:1", "4:3"),
        help="Paid-plan-only aspect_ratio override.",
    )
    screenshot.add_argument("--user-agent", help="Paid-plan-only user_agent override.")
    screenshot.add_argument(
        "--download-snapshot",
        help="Optional path to download response.data.results.snapshot_url.",
    )

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    api_key = _resolve_api_key(args.api_key, args.api_key_env)

    if args.command == "page":
        wrapper, status = _perform_request(
            api_key=api_key,
            base_url=args.base_url,
            pathname="/v1/crawl/page",
            payload=_page_payload(args),
            timeout=args.timeout,
        )
    else:
        wrapper, status = _perform_request(
            api_key=api_key,
            base_url=args.base_url,
            pathname="/v1/crawl/screenshot",
            payload=_screenshot_payload(args),
            timeout=args.timeout,
        )

    if args.output:
        _write_json_file(args.output, wrapper)

    if not args.silent:
        json.dump(wrapper, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")

    if _request_succeeded(wrapper, status):
        if args.command == "page" and args.write_markdown:
            _write_markdown_output(wrapper, args.write_markdown)
        if args.command == "screenshot" and args.download_snapshot:
            _download_snapshot_output(wrapper, args.download_snapshot, args.timeout)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
