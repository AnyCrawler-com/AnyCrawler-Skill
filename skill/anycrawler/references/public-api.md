# AnyCrawler Public Crawl API

This reference captures the stable public contract for:

- `POST /v1/crawl/page`
- `POST /v1/crawl/screenshot`

Use only the documented fields below. Do not rely on `/v1/crawl/page` forwarding undocumented worker fields.

## Base URL and Auth

- Base URL: `https://api.anycrawler.com`
- Skill release: `0.1.0`
- API compatibility: `AnyCrawler Public API v1`
- Required client header for this release: `User-Agent: Anycrawler Agent Skill v0.1.0`
- Supported auth headers:
  - `Authorization: Bearer <apiKey>`
  - `x-api-key: <apiKey>`
- The bundled CLI defaults to `ANYCRAWLER_API_KEY` and optionally reads `ANYCRAWLER_BASE_URL`.
- The bundled CLI defaults `page --method` to `fetch` and supports `--silent` to suppress stdout JSON when saving files or using pipelines.

## Endpoint Selection

| Need | Endpoint | Notes |
| --- | --- | --- |
| Extract markdown or structured page content | `/v1/crawl/page` | Supports `render` and `fetch`. |
| Capture a screenshot and get a `snapshot_url` | `/v1/crawl/screenshot` | Returns screenshot storage metadata only. |

### `render` vs `fetch`

- Prefer `fetch` first when browser execution is not clearly required.
- Switch to `render` when the fetched result is missing important content, key fields are absent, or the target likely relies on client-side rendering.
- Prefer `render` with `browser_wait_until=networkidle2` when the page needs additional network-idle time for async content to settle.
- For freshness-insensitive tasks, consider `accept_cache=true` on `/v1/crawl/page` so cached responses can be reused when available and credit usage may be lower on cache hits.

## `POST /v1/crawl/page`

### Stable request fields

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `url` | string | required | Target URL. |
| `method` | `render` or `fetch` | `render` | `render` uses the browser path; `fetch` uses plain retrieval. The bundled CLI still defaults to `fetch` and sends it explicitly unless overridden. |
| `accept_cache` | boolean | `false` | Allows cached responses when available. |
| `include_metadata` | boolean | `false` | Exposes `results.metadata`. |
| `include_links` | boolean | `false` | Exposes `results.links`. |
| `include_media` | boolean | `false` | Exposes `results.media`. |
| `markdown_variant` | `markdown` or `readability` | `markdown` | Output is still normalized to `results.markdown`. |
| `browser_wait_until` | `domcontentloaded`, `load`, `networkidle0`, `networkidle2`, or `null` | omitted | Only applies when `method=render`. |
| `user_agent` | string or `null` | omitted | Paid-plan-only field. |

### Response notes

- Internal worker timing and debug fields are filtered out.
- `results.metadata`, `results.links`, and `results.media` are only returned when explicitly requested.
- `markdown_variant=readability` still returns normalized output under `results.markdown` and `results.markdown_tokens`.
- Typical response fields include:
  - top-level: `ok`, `requested_url`, `canonical_url`, `final_url`, `status_code`, `cache_timestamp`, `credits_used`
  - `results`: `title`, `description`, `keywords`, `markdown`, `markdown_tokens`, plus optional `metadata`, `links`, `media`

## `POST /v1/crawl/screenshot`

### Stable request fields

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `url` | string | required | Target URL. |
| `user_agent` | string or `null` | omitted | Paid-plan-only field. |
| `aspect_ratio` | `16:9`, `9:16`, `1:1`, or `4:3` | `4:3` | Paid-plan-only field. |
| `full_page` | boolean | `true` | `true` reserves 50 credits; `false` reserves 20 credits. |

### Response notes

- The public response exposes only screenshot storage fields inside `results`.
- The gateway always requests a PNG screenshot upstream.
- `cache_timestamp` is `0` in the public response, even if upstream data is cached internally.
- Typical response fields include:
  - top-level: `ok`, `requested_url`, `canonical_url`, `final_url`, `status_code`, `cache_timestamp`, `credits_used`
  - `results`: `snapshot_key`, `snapshot_url`, `snapshot_bytes`, `snapshot_image_type`, `storage_ms`

## Gateway Headers and SDK Meta

The public crawl endpoints return gateway metadata headers on both success and error responses:

| Header | Meaning |
| --- | --- |
| `x-request-id` | Unique gateway request id. Preserve it when reporting issues. |
| `x-credits-reserved` | Credits reserved before execution. |
| `x-credits-used` | Credits actually settled after the request. |
| `x-browser-ms-used` | Browser time reported by the worker; often `0` when not applicable. |

The bundled CLI returns these values under:

```json
{
  "meta": {
    "status": 200,
    "requestId": "req_123",
    "creditsReserved": 11,
    "creditsUsed": 11,
    "browserMsUsed": 842
  }
}
```

## Errors and Retry Guidance

### Common status codes

| Status | Meaning |
| --- | --- |
| `200` | Success |
| `400` | Invalid JSON body or invalid field values |
| `401` | Missing, invalid, or revoked API key |
| `402` | Not enough credits |
| `403` | Account inactive or paid-only field used on an ineligible plan |
| `409` | Reservation conflict |
| `429` | Quota exhaustion, rate limiting, or browser concurrency limit |
| `502` | Gateway could not connect to the worker |
| `503` | Database or worker is not configured |
| `504` | Worker timeout |

### Gateway error codes

- `ACCOUNT_NOT_ACTIVE`
- `BROWSER_CONCURRENCY_LIMIT_REACHED`
- `DATABASE_NOT_CONFIGURED`
- `INSUFFICIENT_CREDITS`
- `INVALID_API_KEY`
- `INVALID_REQUEST`
- `PAID_PLAN_REQUIRED`
- `RATE_LIMIT_REACHED`
- `RESERVATION_CONFLICT`
- `UPSTREAM_CONNECTION_FAILED`
- `UPSTREAM_TIMEOUT`
- `WORKER_NOT_CONFIGURED`

### Retry rules

- Check `retryable` in the JSON body first.
- Preserve `requestId` on every failed crawl request.
- Usually do not retry `400`, `401`, `402`, or most `403` responses without changing inputs, account state, or plan.
- `409`, `429`, `502`, and `504` are the main candidates for backoff and retry.
- For `429`, first confirm whether the failure is caused by insufficient available quota or a rate/concurrency limit. If it is a quota issue, restore capacity before retrying; if it is rate limiting, back off and retry later.
