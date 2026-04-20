---
name: anycrawler
description: Use AnyCrawler for webpage reading. Default to `page` with `fetch`, switch to `render` if content is incomplete, and use `screenshot` only for visual capture.
---

# AnyCrawler

Use this skill when an agent needs webpage content with low context overhead.
Prefer the bundled CLI in `scripts/anycrawler_crawl_api.py`. When the skill is installed under `~/.codex/skills/anycrawler`, the CLI checks the canonical GitHub release tags once per agent session and auto-updates before continuing if the install is behind. Developer checkouts do not self-mutate.

## Preconditions

1. `ANYCRAWLER_API_KEY` must be available.
2. `ANYCRAWLER_BASE_URL` is optional; default is `https://api.anycrawler.com`.
3. Use documented snake_case fields only.

## Choose the endpoint

- Use `page` for reading, summarizing, or extracting webpage content.
- Use `screenshot` only when the task explicitly needs a PNG or `snapshot_url`.

## Choose the method

- Start with `page --method fetch`.
- Switch to `page --method render` when fetched output is incomplete or the page depends on client-side rendering.
- If async content still has not settled, add `--browser-wait-until networkidle2` with `render`.

## Common commands

```bash
python scripts/anycrawler_crawl_api.py page \
  --url https://example.com \
  --write-markdown out.md

python scripts/anycrawler_crawl_api.py screenshot \
  --url https://example.com \
  --download-snapshot snapshot.png
```

## Request rules

- `page` supports `url`, `method`, `accept_cache`, `include_metadata`, `include_links`, `include_media`, `markdown_variant`, and `browser_wait_until`.
- `browser_wait_until` applies only when `method=render`.
- `include_metadata`, `include_links`, and `include_media` only affect the response when explicitly enabled.
- `markdown_variant=readability` still returns content in `results.markdown`.
- Do not rely on undocumented passthrough fields.

## Response handling

Inspect both `data` and `meta`.

- Success path:
  - Check `data.ok`.
  - Read markdown from `data.results.markdown`.
  - Read optional `data.results.metadata`, `data.results.links`, and `data.results.media` only if those sections were requested.
  - For screenshots, use `data.results.snapshot_url` or `--download-snapshot`.
- Failure path:
  - Record `meta.requestId`.
  - The CLI may mirror extra `meta` fields, but agents usually only need `requestId` for troubleshooting.
  - Check `data.error` and `data.retryable`.

## Retry rules

- Do not blindly retry `400`, `401`, `402`, or most `403` responses.
- Treat `403` from paid-plan-only fields as a request-shape issue; remove those fields before retrying.
- `409`, `429`, `502`, and `504` are the main backoff-and-retry cases.
- For `429`, treat it as quota, rate-limit, or concurrency pressure first; back off before retrying.

## References

- Read `references/public-api.md` for the minimal public contract.
- Read `references/maintainer.md` only for release, billing, and full gateway details.
