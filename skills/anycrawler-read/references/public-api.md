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
| Read with authenticated fetch options | `POST /v1/crawl/page` with `method=fetch` | Use CLI flag `--authenticated-fetch`; requires an API key. |
| Read or extract dynamic webpage content | `POST /v1/crawl/page` with `method=render` | Requires an API key. Use when free fetch output is incomplete or clearly dynamic. |
| Capture a screenshot | `POST /v1/crawl/screenshot` | Returns screenshot storage metadata only. |

## Crawl request fields

### `page`

| Field | Notes |
| --- | --- |
| `url` | Required non-empty target URL; the only field sent for the CLI's `method=fetch` |
| `method` | `fetch` uses the free endpoint by default; add `--authenticated-fetch` to send `method=fetch` to the authenticated public API; `render` always uses the authenticated API |
| `accept_cache` | Render-only boolean; default `false`; do not send for the CLI's `method=fetch` |
| `include_metadata` | Authenticated fetch/render boolean; default `false`; enables `results.metadata` |
| `include_links` | Authenticated fetch/render boolean; default `false`; enables `results.links` |
| `include_media` | Authenticated fetch/render boolean; default `false`; enables `results.media` |
| `markdown_variant` | Authenticated fetch/render; `markdown` (default) or `readability`; output stays in `results.markdown` |
| `browser_wait_until` | Render-only; `domcontentloaded`, `load`, `networkidle0`, `networkidle2`, or `null` |
| `user_agent` | Paid-plan-only string override when explicitly set to a non-empty value; `null`, empty, and whitespace-only values are unset |

### `screenshot`

| Field | Notes |
| --- | --- |
| `url` | Required non-empty target URL |
| `full_page` | Optional boolean; default `true` |
| `aspect_ratio` | Paid-plan-only override: `16:9`, `9:16`, `1:1`, or `4:3`; default `4:3` when omitted |
| `user_agent` | Paid-plan-only string override when explicitly set to a non-empty value; `null`, empty, and whitespace-only values are unset |

## Response fields to care about

### Authenticated `page` and `screenshot`

- `data.ok`
- `data.error_code`
- `data.error_message`
- `data.retryable`
- `meta.requestId`

### Free fetch failures

- `data.ok`
- `data.status_code`
- `data.error.code`
- `data.error.message`

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
| `413` | `PAYLOAD_TOO_LARGE`; request body exceeds the public gateway size limit; reduce it before retrying |
| `429` | Retryable after backoff; also check quota, rate limiting, or concurrency pressure |
| `502` | Retryable after backoff |
| `503` | Missing database or worker configuration |
| `504` | Retryable after backoff |

## Retry rules

1. Record `meta.requestId` on every failure.
2. For authenticated failures, check `data.retryable` before retrying.
3. Prefer changing the request for `400`, `401`, `402`, `413`, and most `403` responses.
4. Back off before retrying `409`, `429`, `502`, and `504`.

Advanced release, billing, headers, and full gateway notes live in `maintainer.md`.
