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
| `query` | Required non-empty search query, maximum 512 characters after trimming |
| `country` | Optional string or `null`, maximum 128 characters after trimming; mapped to upstream `gl` |
| `page` | Optional integer from `1` to `100`; default `1`; forwarded directly to Serper, which determines the actual result count |

Unknown request fields are rejected with `400 INVALID_REQUEST`.

## Billing

- Each page request costs `20` credits.

## Response fields to care about

### Shared

- `data.ok`
- `data.query`
- `data.credits_used`
- `data.status_code`
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
| `413` | `PAYLOAD_TOO_LARGE`; request body exceeds the public gateway size limit |
| `429` | Retryable after backoff; also check quota, rate limiting, or upstream limits |
| `502` | Retryable after backoff |
| `503` | Database or search provider is not configured |
| `504` | Retryable after backoff |

## Retry rules

1. Record `meta.requestId` on every failure.
2. Check `data.retryable` before retrying.
3. Prefer changing the request for `400`, `401`, `402`, `403`, and `413 PAYLOAD_TOO_LARGE` responses.
4. Back off before retrying `409`, `429`, `502`, and `504`.

Advanced release, billing, headers, and full gateway notes live in `maintainer.md`.
