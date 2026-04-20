#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request


DEFAULT_BASE_URL = "https://api.anycrawler.com"
DEFAULT_UPDATE_REPOSITORY = "AnyCrawler-com/AnyCrawler-Skill"
DEFAULT_UPDATE_TIMEOUT = 5.0
AUTO_UPDATE_DISABLE_VALUES = {"0", "false", "no", "off"}
AUTO_UPDATE_SESSION_ENV_NAMES = (
    "OMX_SESSION_ID",
    "CODEX_SESSION_ID",
    "OPENAI_CODEX_SESSION_ID",
    "CHATGPT_SESSION_ID",
)
SESSION_STATE_FILE_NAME = "session-checks.json"
SESSION_HISTORY_LIMIT = 40
REQUIRED_SKILL_FILES = (
    Path("SKILL.md"),
    Path("VERSION"),
    Path("agents/openai.yaml"),
    Path("references/public-api.md"),
    Path("scripts/anycrawler_crawl_api.py"),
)
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
DEFAULT_SKILL_USER_AGENT = f"Anycrawler Agent Skill v{SKILL_VERSION}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _emit_update_debug(message: str) -> None:
    if os.getenv("ANYCRAWLER_AUTO_UPDATE_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}:
        print(f"[anycrawler-auto-update] {message}", file=sys.stderr)


def _normalize_version(version: str) -> str:
    normalized = version.strip()
    if normalized.startswith("v"):
        return normalized[1:]
    return normalized


def _parse_version_tuple(version: str) -> tuple[int, ...] | None:
    normalized = _normalize_version(version)
    if not normalized:
        return None

    pieces = normalized.split(".")
    parsed: list[int] = []
    for piece in pieces:
        if not piece.isdigit():
            return None
        parsed.append(int(piece))
    return tuple(parsed)


def _is_newer_version(remote_version: str, local_version: str) -> bool:
    remote_tuple = _parse_version_tuple(remote_version)
    local_tuple = _parse_version_tuple(local_version)
    if remote_tuple is None or local_tuple is None:
        return False
    return remote_tuple > local_tuple


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


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    return payload if isinstance(payload, dict) else {}


def _download_bytes(url: str, timeout: float, *, accept: str) -> bytes:
    request = urllib_request.Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": DEFAULT_SKILL_USER_AGENT,
        },
        method="GET",
    )
    with urllib_request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _download_file(url: str, path: str | Path, timeout: float) -> None:
    try:
        body = _download_bytes(url, timeout, accept="*/*")
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(body)
    except urllib_error.HTTPError as exc:
        message = f"Snapshot download failed with HTTP {exc.code} {exc.reason} for {url}"
        raise SystemExit(message) from exc
    except urllib_error.URLError as exc:
        message = f"Snapshot download failed before receiving an HTTP response: {exc.reason}"
        raise SystemExit(message) from exc


def _resolve_update_timeout() -> float:
    raw = os.getenv("ANYCRAWLER_UPDATE_TIMEOUT")
    if raw is None:
        return DEFAULT_UPDATE_TIMEOUT

    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_UPDATE_TIMEOUT

    return value if value > 0 else DEFAULT_UPDATE_TIMEOUT


def _resolve_update_repository() -> str:
    repository = os.getenv("ANYCRAWLER_UPDATE_REPOSITORY", DEFAULT_UPDATE_REPOSITORY).strip()
    return repository or DEFAULT_UPDATE_REPOSITORY


def _is_auto_update_enabled() -> bool:
    raw = os.getenv("ANYCRAWLER_AUTO_UPDATE", "1").strip().lower()
    return raw not in AUTO_UPDATE_DISABLE_VALUES


def _should_run_auto_update(argv: list[str]) -> bool:
    if not argv:
        return False

    return all(flag not in {"--version", "-h", "--help"} for flag in argv)


def _expected_managed_skill_root() -> Path:
    override = os.getenv("ANYCRAWLER_MANAGED_INSTALL_ROOT")
    if override:
        return Path(override).expanduser().resolve()

    codex_home = os.getenv("CODEX_HOME")
    if codex_home:
        return (Path(codex_home).expanduser() / "skills" / "anycrawler").resolve()

    return (Path.home() / ".codex" / "skills" / "anycrawler").resolve()


def _is_managed_skill_install(skill_root: Path = SKILL_ROOT) -> bool:
    try:
        return skill_root.resolve() == _expected_managed_skill_root()
    except OSError:
        return False


def _resolve_state_dir() -> Path:
    override = os.getenv("ANYCRAWLER_STATE_DIR")
    if override:
        return Path(override).expanduser()

    codex_home = os.getenv("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "skills" / ".anycrawler-state"

    return Path.home() / ".codex" / "skills" / ".anycrawler-state"


def _session_state_path(state_dir: Path | None = None) -> Path:
    return (state_dir or _resolve_state_dir()) / SESSION_STATE_FILE_NAME


def _load_session_state(state_dir: Path | None = None) -> dict[str, Any]:
    return _read_json_file(_session_state_path(state_dir))


def _save_session_state(payload: dict[str, Any], state_dir: Path | None = None) -> None:
    path = _session_state_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _session_was_checked(session_key: str, *, state_dir: Path | None = None) -> bool:
    payload = _load_session_state(state_dir)
    sessions = payload.get("sessions")
    return isinstance(sessions, dict) and session_key in sessions


def _mark_session_checked(
    session_key: str,
    *,
    state_dir: Path | None = None,
    local_version: str,
    latest_version: str | None,
    outcome: str,
) -> None:
    payload = _load_session_state(state_dir)
    sessions = payload.setdefault("sessions", {})
    if not isinstance(sessions, dict):
        sessions = {}
        payload["sessions"] = sessions

    sessions[session_key] = {
        "checked_at": _utc_now(),
        "local_version": local_version,
        "latest_version": latest_version,
        "outcome": outcome,
    }

    ordered = sorted(
        sessions.items(),
        key=lambda item: item[1].get("checked_at", ""),
        reverse=True,
    )
    payload["sessions"] = dict(ordered[:SESSION_HISTORY_LIMIT])
    _save_session_state(payload, state_dir)


def _session_key_from_env() -> str | None:
    for env_name in AUTO_UPDATE_SESSION_ENV_NAMES:
        value = os.getenv(env_name)
        if value:
            return f"env:{env_name}:{value}"
    return None


def _session_key_from_nearby_omx(start_path: Path) -> str | None:
    for candidate in (start_path, *start_path.parents):
        session_file = candidate / ".omx" / "state" / "session.json"
        if not session_file.is_file():
            continue

        payload = _read_json_file(session_file)
        for key in ("native_session_id", "session_id"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return f"omx:{value}"
    return None


def _discover_session_key(skill_root: Path = SKILL_ROOT) -> str:
    from_env = _session_key_from_env()
    if from_env:
        return from_env

    for start_path in (Path.cwd().resolve(), skill_root.resolve()):
        from_omx = _session_key_from_nearby_omx(start_path)
        if from_omx:
            return from_omx

    return f"fallback:{os.getppid()}:{Path.cwd().resolve()}"


def _fetch_json(url: str, timeout: float) -> Any:
    body = _download_bytes(url, timeout, accept="application/vnd.github+json")
    return json.loads(body.decode("utf-8"))


def _fetch_latest_release_tag(*, timeout: float, repository: str | None = None) -> tuple[str, str] | None:
    repo = repository or _resolve_update_repository()
    payload = _fetch_json(f"https://api.github.com/repos/{repo}/tags?per_page=100", timeout)
    if not isinstance(payload, list):
        raise RuntimeError("GitHub tags API returned an unexpected payload.")

    latest: tuple[tuple[int, ...], str, str] | None = None
    for item in payload:
        if not isinstance(item, dict):
            continue
        raw_tag = item.get("name")
        if not isinstance(raw_tag, str):
            continue

        version_tuple = _parse_version_tuple(raw_tag)
        if version_tuple is None:
            continue

        version = _normalize_version(raw_tag)
        if latest is None or version_tuple > latest[0]:
            latest = (version_tuple, raw_tag, version)

    if latest is None:
        return None

    return latest[1], latest[2]


def _find_extracted_skill_root(extract_dir: Path) -> Path:
    matches = list(extract_dir.glob("*/skill/anycrawler"))
    if len(matches) != 1:
        raise RuntimeError("Failed to locate skill/anycrawler in the downloaded release archive.")
    return matches[0]


def _validate_skill_tree(skill_root: Path, *, expected_version: str | None = None) -> str:
    for relative_path in REQUIRED_SKILL_FILES:
        candidate = skill_root / relative_path
        if not candidate.exists():
            raise RuntimeError(f"Downloaded skill is missing required path: {relative_path}")

    version = _load_skill_version_from(skill_root / "VERSION")
    if expected_version is not None and version != expected_version:
        raise RuntimeError(
            f"Downloaded skill version mismatch: expected {expected_version}, received {version}."
        )

    return version


def _stage_latest_skill_release(
    *,
    tag: str,
    version: str,
    repository: str,
    timeout: float,
    temp_dir: Path,
) -> Path:
    archive_path = temp_dir / f"{tag}.zip"
    archive_path.write_bytes(
        _download_bytes(
            f"https://github.com/{repository}/archive/refs/tags/{tag}.zip",
            timeout,
            accept="application/zip",
        )
    )

    extract_dir = temp_dir / "extract"
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extract_dir)

    extracted_skill_root = _find_extracted_skill_root(extract_dir)
    _validate_skill_tree(extracted_skill_root, expected_version=version)

    staged_skill_root = temp_dir / "staged-anycrawler"
    shutil.copytree(extracted_skill_root, staged_skill_root)
    return staged_skill_root


def _replace_managed_skill_root(*, skill_root: Path, staged_skill_root: Path, state_dir: Path) -> Path:
    state_dir.mkdir(parents=True, exist_ok=True)
    backups_dir = state_dir / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    current_version = _load_skill_version_from(skill_root / "VERSION")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = backups_dir / f"anycrawler-{current_version}-{timestamp}"
    replacement_root = skill_root.parent / f".anycrawler-replacement-{timestamp}"

    if replacement_root.exists():
        shutil.rmtree(replacement_root)

    shutil.move(str(staged_skill_root), str(replacement_root))

    try:
        shutil.move(str(skill_root), str(backup_root))
        try:
            shutil.move(str(replacement_root), str(skill_root))
        except Exception:
            if skill_root.exists():
                shutil.rmtree(skill_root, ignore_errors=True)
            shutil.move(str(backup_root), str(skill_root))
            raise
    finally:
        if replacement_root.exists():
            shutil.rmtree(replacement_root, ignore_errors=True)

    return backup_root


def _perform_skill_self_update(
    *,
    skill_root: Path,
    state_dir: Path,
    tag: str,
    version: str,
    repository: str,
    timeout: float,
) -> None:
    with tempfile.TemporaryDirectory(dir=skill_root.parent) as temp_dir:
        staged_skill_root = _stage_latest_skill_release(
            tag=tag,
            version=version,
            repository=repository,
            timeout=timeout,
            temp_dir=Path(temp_dir),
        )
        _replace_managed_skill_root(
            skill_root=skill_root,
            staged_skill_root=staged_skill_root,
            state_dir=state_dir,
        )


def _run_auto_update_preflight(argv: list[str], *, skill_root: Path = SKILL_ROOT) -> bool:
    if not _is_auto_update_enabled() or not _should_run_auto_update(argv):
        return False

    if not _is_managed_skill_install(skill_root):
        _emit_update_debug("Skipping auto-update preflight outside the managed install path.")
        return False

    session_key = _discover_session_key(skill_root)
    state_dir = _resolve_state_dir()
    if _session_was_checked(session_key, state_dir=state_dir):
        _emit_update_debug(f"Session {session_key} already completed AnyCrawler auto-update preflight.")
        return False

    local_version = _load_skill_version_from(skill_root / "VERSION")
    repository = _resolve_update_repository()
    timeout = _resolve_update_timeout()

    try:
        latest = _fetch_latest_release_tag(timeout=timeout, repository=repository)
        if latest is None:
            _mark_session_checked(
                session_key,
                state_dir=state_dir,
                local_version=local_version,
                latest_version=None,
                outcome="no-valid-tag",
            )
            return False

        latest_tag, latest_version = latest
        if not _is_newer_version(latest_version, local_version):
            _mark_session_checked(
                session_key,
                state_dir=state_dir,
                local_version=local_version,
                latest_version=latest_version,
                outcome="current",
            )
            return False

        _emit_update_debug(
            f"Updating managed skill install from {local_version} to {latest_version} using {latest_tag}."
        )
        _perform_skill_self_update(
            skill_root=skill_root,
            state_dir=state_dir,
            tag=latest_tag,
            version=latest_version,
            repository=repository,
            timeout=timeout,
        )
        _mark_session_checked(
            session_key,
            state_dir=state_dir,
            local_version=local_version,
            latest_version=latest_version,
            outcome="updated",
        )
        return True
    except Exception as exc:  # noqa: BLE001 - degrade gracefully on update-preflight failures
        _emit_update_debug(f"Auto-update preflight failed: {exc}")
        _mark_session_checked(
            session_key,
            state_dir=state_dir,
            local_version=local_version,
            latest_version=None,
            outcome="error",
        )
        return False


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


def main(argv: list[str] | None = None) -> int:
    active_argv = list(sys.argv[1:] if argv is None else argv)
    if _run_auto_update_preflight(active_argv):
        os.execv(sys.executable, [sys.executable, str(SCRIPT_FILE), *active_argv])
        raise RuntimeError("os.execv returned unexpectedly during AnyCrawler self-update re-exec.")

    parser = _build_parser()
    args = parser.parse_args(active_argv)
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
