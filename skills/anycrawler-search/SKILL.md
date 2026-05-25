---
name: anycrawler-search
description: Use AnyCrawler for public search across web pages, images, news, videos, and scholar results. Use when Codex needs current search results, source discovery, media discovery, news lookup, or scholarly search before reading specific pages.
---

# AnyCrawler Search

Use this skill when an agent needs public search results with low context overhead.
Prefer the bundled CLI in `scripts/anycrawler_search_api.py`.
The public API uses one search endpoint, `POST /v1/search`; select the result type with the `channel` body field.

## Preconditions

1. `ANYCRAWLER_API_KEY` must be available.
2. `ANYCRAWLER_BASE_URL` is optional; default is `https://api.anycrawler.com`.
3. Use documented snake_case fields only.

## Choose the channel

- Use `page` for general web search and source discovery.
- Use `images` when the task needs image results or visual source candidates.
- Use `news` when the task needs recent news coverage.
- Use `videos` when the task needs video results.
- Use `scholar` when the task needs scholarly or academic search results.

## Common commands

```bash
python scripts/anycrawler_search_api.py page \
  --query "site reliability engineering"

python scripts/anycrawler_search_api.py news \
  --query "AnyCrawler launch" \
  --country us \
  --language en \
  --results-per-page 20
```

## Request rules

- All CLI subcommands send `POST /v1/search` with `channel` set to the subcommand name.
- The request body supports `channel`, `query`, `country`, `language`, `location`, `page`, and `results_per_page`.
- `channel` is required and must be one of `page`, `images`, `news`, `videos`, or `scholar`.
- `query` is required and must be at most 512 characters.
- `country`, `language`, and `location` are optional locale hints.
- `page` must be between `1` and `100`; default is `1`.
- `results_per_page` must be between `1` and `100`; default is `10`.
- Billing is `ceil(results_per_page / 10) * 20` credits.
- Requests are cached for 1 hour by channel, query, page, locale fields, and results count, but cache hits do not change pricing.
- Do not rely on undocumented passthrough fields.

## Response handling

Inspect both `data` and `meta`.

- Success path:
  - Check `data.ok`.
  - Read `data.results.search_parameters` to confirm the effective channel and request fields.
  - For `page`, read `data.results.organic`.
  - For `images`, read `data.results.images`.
  - For `news`, read `data.results.news`.
  - For `videos`, read `data.results.videos`.
  - For `scholar`, read `data.results.organic` first, then other populated collections.
  - Use optional `data.results.knowledge_graph`, `answer_box`, `people_also_ask`, and `related_searches` when present.
- Failure path:
  - Record `meta.requestId`.
  - Check `data.error_code`, `data.error_message`, and `data.retryable`.

## Retry rules

- Do not blindly retry `400`, `401`, `402`, `403`, or `413`.
- `409`, `429`, `502`, and `504` are the main backoff-and-retry cases.
- For `429`, treat it as quota, rate-limit, or upstream provider pressure first; back off before retrying.
- For `503`, check service configuration before retrying.

## References

- Read `references/public-api.md` for the minimal public search contract.
- Read `references/maintainer.md` only for release, billing, and full gateway details.
