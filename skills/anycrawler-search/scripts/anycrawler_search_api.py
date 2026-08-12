#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request


DEFAULT_BASE_URL = "https://api.anycrawler.com"
SEARCH_CHANNELS = ("page", "images", "news", "videos", "scholar")
SEARCH_MAX_QUERY_LENGTH = 512
SEARCH_MAX_COUNTRY_LENGTH = 128
SCRIPT_FILE = Path(__file__).resolve()
SKILL_ROOT = SCRIPT_FILE.parents[1]
VERSION_FILE = SKILL_ROOT / "VERSION"


def _load_skill_version_from(path: Path) -> str:
    try:
        version = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Failed to read skill version from {path}.") from exc

    if not version:
        raise RuntimeError(f"Skill version file is empty: {path}")

    return version


def _load_skill_version() -> str:
    return _load_skill_version_from(VERSION_FILE)


SKILL_VERSION = _load_skill_version()
DEFAULT_SKILL_USER_AGENT = f"Anycrawler Search Agent Skill v{SKILL_VERSION}"


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


def _bounded_text(field: str, maximum: int):
    def parse(value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise argparse.ArgumentTypeError(f"{field} must be non-empty.")
        if len(normalized) > maximum:
            raise argparse.ArgumentTypeError(f"{field} must be {maximum} characters or fewer.")
        return normalized

    return parse


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


def _perform_request(
    *,
    api_key: str,
    base_url: str,
    payload: dict[str, Any],
    timeout: float,
) -> tuple[dict[str, Any], int]:
    request = urllib_request.Request(
        f"{_normalize_base_url(base_url)}/v1/search",
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
        message = f"AnyCrawler search request failed before receiving an HTTP response: {exc.reason}"
        raise SystemExit(message) from exc


def _search_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "channel": args.channel,
        "query": args.query,
        "page": args.page,
    }
    if args.country is not None:
        payload["country"] = args.country
    return payload


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
    parser.add_argument(
        "--query",
        required=True,
        type=_bounded_text("query", SEARCH_MAX_QUERY_LENGTH),
        help="Non-empty search query, maximum 512 characters.",
    )
    parser.add_argument(
        "--country",
        type=_bounded_text("country", SEARCH_MAX_COUNTRY_LENGTH),
        help="Optional country string mapped to upstream gl, maximum 128 characters.",
    )
    parser.add_argument("--page", type=int, default=1, choices=range(1, 101), metavar="1-100")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Call AnyCrawler public search APIs with the stable documented contract.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {SKILL_VERSION}",
    )
    subparsers = parser.add_subparsers(dest="channel", required=True)

    for channel in SEARCH_CHANNELS:
        channel_parser = subparsers.add_parser(channel, help=f"Call POST /v1/search with channel={channel}.")
        _add_common_arguments(channel_parser)

    return parser


def main(argv: list[str] | None = None) -> int:
    active_argv = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args = parser.parse_args(active_argv)
    api_key = _resolve_api_key(args.api_key, args.api_key_env)

    wrapper, status = _perform_request(
        api_key=api_key,
        base_url=args.base_url,
        payload=_search_payload(args),
        timeout=args.timeout,
    )

    if args.output:
        _write_json_file(args.output, wrapper)

    if not args.silent:
        json.dump(wrapper, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")

    return 0 if _request_succeeded(wrapper, status) else 1


if __name__ == "__main__":
    raise SystemExit(main())
