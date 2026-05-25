# AnyCrawler Search Public API

This reference keeps only the minimum contract an agent needs at runtime.

## Base setup

- Base URL: `https://api.anycrawler.com`
- API key env var: `ANYCRAWLER_API_KEY`
- Optional base URL env var: `ANYCRAWLER_BASE_URL`
- Preferred client: `scripts/anycrawler_search_api.py`
- Webpage reading and screenshots belong in the separate `anycrawler-read` skill.

## Endpoint

Use `POST /v1/search` for every public search request. Set the request body's
`channel` field to choose the search vertical.

| Need | `channel` | Primary collection |
| --- | --- | --- |
| General web search | `page` | `results.organic` |
| Image search | `images` | `results.images` |
| News search | `news` | `results.news` |
| Video search | `videos` | `results.videos` |
| Scholar search | `scholar` | `results.organic` |

## Search request fields

| Field | Notes |
| --- | --- |
| `channel` | Required search channel: `page`, `images`, `news`, `videos`, or `scholar` |
| `query` | Required search query, maximum 512 characters |
| `country` | Optional country code mapped to upstream `gl` |
| `language` | Optional language code mapped to upstream `hl` |
| `location` | Optional precise location string forwarded upstream |
| `page` | Optional integer from `1` to `100`; default `1` |
| `results_per_page` | Optional integer from `1` to `100`; default `10` |

## Billing and caching

- Billing formula: `ceil(results_per_page / 10) * 20` credits.
- Requests are cached for 1 hour by `channel`, `query`, `page`, locale fields, and `results_per_page`.
- Search cache hits do not change pricing.

## Response fields to care about

### Shared

- `data.ok`
- `data.query`
- `data.cache_timestamp`
- `data.credits_used`
- `data.status_code`
- `data.title`
- `data.final_url`
- `data.error_code`
- `data.error_message`
- `data.retryable`
- `meta.requestId`

### `results`

- `data.results.search_parameters`
- `data.results.organic`
- `data.results.images`
- `data.results.news`
- `data.results.videos`
- `data.results.knowledge_graph`
- `data.results.people_also_ask`
- `data.results.related_searches`
- `data.results.answer_box`

## Error handling

| Status | Handling |
| --- | --- |
| `400` | Invalid request; fix input before retry |
| `401` | Invalid or missing API key |
| `402` | Account capacity issue; do not blind retry |
| `403` | Account exists but is not active |
| `409` | Retryable after backoff |
| `413` | Request body exceeds the public gateway size limit |
| `429` | Retryable after backoff; also check quota, rate limiting, or upstream limits |
| `502` | Retryable after backoff |
| `503` | Database or search provider is not configured |
| `504` | Retryable after backoff |

## Retry rules

1. Record `meta.requestId` on every failure.
2. Check `data.retryable` before retrying.
3. Prefer changing the request for `400`, `401`, `402`, `403`, and `413` responses.
4. Back off before retrying `409`, `429`, `502`, and `504`.

Advanced release, billing, headers, and full gateway notes live in `maintainer.md`.
