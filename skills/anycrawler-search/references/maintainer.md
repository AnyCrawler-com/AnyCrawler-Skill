# AnyCrawler Search Maintainer Notes

This file keeps details that are useful for maintainers but unnecessary for most agents at runtime.

## Version and compatibility

- Skill release: `0.2.0`
- API compatibility: `AnyCrawler Public API v1`
- Version source of truth: `skills/anycrawler-search/VERSION`
- Required outbound header for this release: `User-Agent: Anycrawler Search Agent Skill v0.2.0`
- API source of truth: `../app/openapi.json`

## Auth details

- Base URL: `https://api.anycrawler.com`
- Supported auth headers:
  - `Authorization: Bearer <apiKey>`
  - `x-api-key: <apiKey>`

## Search channels

All public search channels use `POST /v1/search` with a `channel` field in the
JSON body:

- `page`
- `images`
- `news`
- `videos`
- `scholar`

## Billing notes

- Every `/v1/search` request reserves 20 credits per block of 10 requested results.
- Billing formula: `ceil(results_per_page / 10) * 20`.
- Cache hits do not change pricing.

## Gateway headers mirrored by the CLI

- `x-request-id`
- `x-credits-reserved`
- `x-credits-used`
- `x-browser-ms-used`

CLI wrapper shape:

```json
{
  "meta": {
    "status": 200,
    "requestId": "req_123",
    "creditsReserved": 20,
    "creditsUsed": 20,
    "browserMsUsed": 0
  }
}
```

## Release checklist

1. Update `skills/anycrawler-search/VERSION`
2. Run `python -m unittest tests/test_anycrawler_search_api.py`
3. Verify docs still match `../app/openapi.json`
4. Verify docs still match the current `User-Agent` and API compatibility statement

## Repository pointers

- Source repository: `https://github.com/AnyCrawler-com/AnyCrawler-Skill`
- Bundled CLI: `skills/anycrawler-search/scripts/anycrawler_search_api.py`
- Agent metadata: `skills/anycrawler-search/agents/openai.yaml`
