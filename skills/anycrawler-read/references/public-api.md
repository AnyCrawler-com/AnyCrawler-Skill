# AnyCrawler Public API

This reference keeps only the minimum contract an agent needs at runtime.

## Base setup

- Base URL: `https://api.anycrawler.com`
- API key env var: `ANYCRAWLER_API_KEY` for render and screenshot only
- Optional base URL env var: `ANYCRAWLER_BASE_URL`
- Preferred client: `scripts/anycrawler_crawl_api.py`
- Search workflows belong in the separate `anycrawler-search` skill.

## Endpoint selection

| Need | Use | Notes |
| --- | --- | --- |
| Read or extract webpage content with fetch | `GET /free/v1/crawl?url={url}` | Default path. Does not require an API key. |
| Read or extract dynamic webpage content | `POST /v1/crawl/page` with `method=render` | Requires an API key. Use when free fetch output is incomplete or clearly dynamic. |
| Capture a screenshot | `POST /v1/crawl/screenshot` | Returns screenshot storage metadata only. |

## Crawl request fields

### `page`

| Field | Notes |
| --- | --- |
| `url` | Required target URL; the only field sent for `method=fetch` |
| `method` | `fetch` uses the free endpoint, `render` uses the authenticated public API |
| `accept_cache` | Render-only; do not send for `method=fetch` |
| `include_metadata` | Render-only; enables `results.metadata` |
| `include_links` | Render-only; enables `results.links` |
| `include_media` | Render-only; enables `results.media` |
| `markdown_variant` | Render-only; `markdown` or `readability`; output stays in `results.markdown` |
| `browser_wait_until` | Only for `method=render` |
| `user_agent` | Paid-plan-only field when explicitly set |

### `screenshot`

| Field | Notes |
| --- | --- |
| `url` | Required target URL |
| `full_page` | Full-page by default |
| `aspect_ratio` | Paid-plan-only override |
| `user_agent` | Paid-plan-only field when explicitly set |

## Response fields to care about

### Shared

- `data.ok`
- `data.error_code`
- `data.error_message`
- `data.retryable`
- `meta.requestId`

### `page`

- `data.results.markdown`
- `data.results.metadata` when requested
- `data.results.links` when requested
- `data.results.media` when requested

### `screenshot`

- `data.results.snapshot_url`

## Error handling

| Status | Handling |
| --- | --- |
| `400` | Invalid request; fix input before retry |
| `401` | Invalid or missing API key for render or screenshot |
| `402` | Account capacity issue; do not blind retry |
| `403` | Usually account or paid-plan field issue; remove ineligible fields or fix account state |
| `409` | Retryable after backoff |
| `429` | Retryable after backoff; also check quota, rate limiting, or concurrency pressure |
| `502` | Retryable after backoff |
| `503` | Missing database, worker, or search provider configuration |
| `504` | Retryable after backoff |

## Retry rules

1. Record `meta.requestId` on every failure.
2. Check `data.retryable` before retrying.
3. Prefer changing the request for `400`, `401`, `402`, and most `403` responses.
4. Back off before retrying `409`, `429`, `502`, and `504`.

Advanced release, billing, headers, and full gateway notes live in `maintainer.md`.
