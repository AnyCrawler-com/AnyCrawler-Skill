# AnyCrawler Public API

This reference keeps only the minimum contract an agent needs at runtime.

## Base setup

- Base URL: `https://api.anycrawler.com`
- API key env var: `ANYCRAWLER_API_KEY`
- Optional base URL env var: `ANYCRAWLER_BASE_URL`
- Preferred client: `scripts/anycrawler_crawl_api.py`
- The bundled CLI remains crawl-first. Search endpoints are documented here for stable integration reference.

## Endpoint selection

| Need | Use | Notes |
| --- | --- | --- |
| Read or extract webpage content | `POST /v1/crawl/page` | Default to `fetch` first and escalate to `render` when content is incomplete or clearly dynamic. |
| Capture a screenshot | `POST /v1/crawl/screenshot` | Returns screenshot storage metadata only. |
| Search the public web | `POST /v1/search/page` | Returns normalized search results such as `organic`. |
| Search recent news | `POST /v1/search/news` | Returns normalized search results such as `news`. |

## Crawl request fields

### `page`

| Field | Notes |
| --- | --- |
| `url` | Required target URL |
| `method` | `fetch` first, `render` for dynamic or incomplete pages |
| `accept_cache` | Use when freshness is not critical |
| `include_metadata` | Enables `results.metadata` |
| `include_links` | Enables `results.links` |
| `include_media` | Enables `results.media` |
| `markdown_variant` | `markdown` or `readability`; output stays in `results.markdown` |
| `browser_wait_until` | Only for `method=render` |
| `user_agent` | Paid-plan-only field when explicitly set |

### `screenshot`

| Field | Notes |
| --- | --- |
| `url` | Required target URL |
| `full_page` | Full-page by default |
| `aspect_ratio` | Paid-plan-only override |
| `user_agent` | Paid-plan-only field when explicitly set |

## Search request fields

### Shared stable fields for `/v1/search/page` and `/v1/search/news`

| Field | Notes |
| --- | --- |
| `query` | Required search query |
| `country` | Optional country code mapped to upstream `gl` |
| `language` | Optional language code mapped to upstream `hl` |
| `page` | Optional integer between `1` and `100` |
| `results_per_page` | Optional integer between `1` and `100`; billed in blocks of 10 results |
| `date_range` | Optional `past_hour`, `past_day`, `past_week`, `past_month`, or `past_year` |

### Search response notes

- Search responses use a normalized envelope with `ok`, `query`, `status_code`, `cache_timestamp`, `credits_used`, `title`, `final_url`, and `results`.
- `results.search_parameters` mirrors the stable public request fields.
- `results.organic` is the primary list for `/v1/search/page`.
- `results.news` is the primary list for `/v1/search/news`.
- Search cache hits do not change pricing.

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

### Search

- `data.results.search_parameters`
- `data.results.organic` for `/v1/search/page`
- `data.results.news` for `/v1/search/news`

## Error handling

| Status | Handling |
| --- | --- |
| `400` | Invalid request; fix input before retry |
| `401` | Invalid or missing API key |
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
