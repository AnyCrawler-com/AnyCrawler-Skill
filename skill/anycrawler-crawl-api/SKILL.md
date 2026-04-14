---
name: anycrawler-crawl-api
description: Call AnyCrawler public crawl endpoints `/v1/crawl/page` and `/v1/crawl/screenshot` to fetch rendered or fetched page content, metadata, links, media, and screenshots. Use when Codex needs to invoke AnyCrawler with an API key, choose between `render`, `fetch`, and screenshot capture, inspect gateway credit and request metadata, save markdown or screenshot outputs, or troubleshoot public API request failures without relying on undocumented worker passthrough fields.
---

# AnyCrawler Crawl API

## Overview

Call the stable AnyCrawler public crawl contract only.
Prefer the bundled CLI in `scripts/anycrawler_crawl_api.py` for repeatable requests, and read `references/public-api.md` before adding fields or interpreting headers and errors.

## Workflow

1. Confirm `ANYCRAWLER_API_KEY` is available. Optionally use `ANYCRAWLER_BASE_URL`; default to `https://api.anycrawler.com`.
2. Choose the endpoint:
   - Use `page` for extracted page content.
   - Use `screenshot` for PNG snapshot capture.
3. Build requests only from documented snake_case fields. Do not depend on undocumented passthrough fields for `/v1/crawl/page`.
4. Run the bundled CLI instead of hand-writing HTTP requests when possible.
5. Inspect both `data` and `meta`. `meta` mirrors gateway headers such as `requestId`, `creditsReserved`, `creditsUsed`, and `browserMsUsed`.
6. On failures, record `meta.requestId`, check `data.retryable`, and treat `400`, `401`, `402`, and most `403` responses as input or account issues rather than retry candidates.

## Endpoint Choice

- Use `page` when the user needs extracted content or structured crawl results.
- Prefer `method=render` when the target page needs browser rendering, JavaScript execution, or explicit DOM readiness control.
- Prefer `method=fetch` for cheaper plain HTTP retrieval when browser execution is not required.
- Use `screenshot` when the user needs `snapshot_url`, screenshot metadata, or a downloaded PNG.

## Request Rules

- Keep request field names in snake_case.
- For `page`, `browser_wait_until` only applies when `method=render`.
- For `page`, `markdown_variant=readability` still returns content in `results.markdown` and `results.markdown_tokens`.
- For `page`, `include_metadata`, `include_links`, and `include_media` must be explicitly true to expose those response sections.
- `user_agent` on `page`, plus `user_agent` and `aspect_ratio` on `screenshot`, are paid-plan-only fields.
- Do not send undocumented worker passthrough fields from older internal integrations.

## Quick Start

```bash
python scripts/anycrawler_crawl_api.py page \
  --url https://example.com \
  --method render \
  --include-metadata

python scripts/anycrawler_crawl_api.py page \
  --url https://example.com/docs \
  --method fetch \
  --accept-cache \
  --write-markdown out.md

python scripts/anycrawler_crawl_api.py screenshot \
  --url https://example.com \
  --no-full-page \
  --download-snapshot snapshot.png
```

## References

- Read [references/public-api.md](./references/public-api.md) for the stable field list, response shape, gateway headers, error codes, and retry guidance.
- Use [scripts/anycrawler_crawl_api.py](./scripts/anycrawler_crawl_api.py) for deterministic requests that can also save markdown or download the returned screenshot URL.
