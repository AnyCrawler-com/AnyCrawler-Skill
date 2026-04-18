# AnyCrawler Maintainer Notes

This file keeps details that are useful for maintainers but unnecessary for most agents at runtime.

## Version and compatibility

- Skill release: `0.1.1`
- API compatibility: `AnyCrawler Public API v1`
- Version source of truth: `skill/anycrawler/VERSION`
- Required outbound header for this release: `User-Agent: Anycrawler Agent Skill v0.1.1`

## Auth details

- Base URL: `https://api.anycrawler.com`
- Supported auth headers:
  - `Authorization: Bearer <apiKey>`
  - `x-api-key: <apiKey>`

## Paid-plan-only fields

- `page.user_agent`
- `screenshot.user_agent`
- `screenshot.aspect_ratio`

## Screenshot billing notes

- `full_page=true` reserves 50 credits
- `full_page=false` reserves 20 credits

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
    "creditsReserved": 11,
    "creditsUsed": 11,
    "browserMsUsed": 842
  }
}
```

## Full gateway error catalog

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

## Release checklist

1. Update `skill/anycrawler/VERSION`
2. Run `python3 -m unittest tests/test_anycrawler_crawl_api.py`
3. Verify docs still match the current `User-Agent` and API compatibility statement
4. Create an annotated tag such as `git tag -a v0.1.1 -m "AnyCrawler skill release"`
5. Push the branch and tag, then create a GitHub Release

## Repository pointers

- Source repository: `https://github.com/myeyesareopen/AnyCrawler-Skill`
- Bundled CLI: `skill/anycrawler/scripts/anycrawler_crawl_api.py`
- Agent metadata: `skill/anycrawler/agents/openai.yaml`
