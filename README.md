[🔌 Register / Sign In](https://app.anycrawler.com/login) | [🛋 Dashboard](https://app.anycrawler.com/overview) | [🌓 Get API Keys](https://app.anycrawler.com/api-keys) | [🕪 Public API](https://api.anycrawler.com)

# AnyCrawler Skills for AI Agents ✅

This repository provides AnyCrawler skills that can be installed into compatible AI agent runtimes. Use `$anycrawler-read` for webpage reading and screenshots, and `$anycrawler-search` for public search across web pages, images, news, videos, and scholar results.

## What this repo contains

- `skills/anycrawler-read/SKILL.md`: the slim agent-facing runtime guide for crawling, reading, and screenshots
- `skills/anycrawler-read/references/public-api.md`: the minimal crawl API contract for agent use
- `skills/anycrawler-read/references/maintainer.md`: read-skill release, billing, and gateway notes
- `skills/anycrawler-read/scripts/anycrawler_crawl_api.py`: the bundled read CLI
- `skills/anycrawler-read/agents/openai.yaml`: read-skill agent display metadata
- `skills/anycrawler-search/SKILL.md`: the slim agent-facing runtime guide for public search
- `skills/anycrawler-search/references/public-api.md`: the minimal search API contract for agent use
- `skills/anycrawler-search/references/maintainer.md`: search-skill release, billing, and gateway notes
- `skills/anycrawler-search/scripts/anycrawler_search_api.py`: the bundled search CLI
- `skills/anycrawler-search/agents/openai.yaml`: search-skill agent display metadata
- `tests/test_anycrawler_crawl_api.py`: regression tests for the CLI
- `tests/test_anycrawler_search_api.py`: regression tests for the search CLI

## Install

A common installation path is `~/.codex/skills`. The source directories in this repository are under `skills/`, and each installed skill directory should keep the same name so it matches its explicit invocation name.

### macOS / Linux

```bash
git clone https://github.com/AnyCrawler-com/AnyCrawler-Skill.git
mkdir -p ~/.codex/skills
cp -R AnyCrawler-Skill/skills/anycrawler-read ~/.codex/skills/anycrawler-read
cp -R AnyCrawler-Skill/skills/anycrawler-search ~/.codex/skills/anycrawler-search
```

### Windows PowerShell

```powershell
git clone https://github.com/AnyCrawler-com/AnyCrawler-Skill.git
New-Item -ItemType Directory -Force "$HOME\.codex\skills" | Out-Null
Copy-Item -Recurse -Force ".\AnyCrawler-Skill\skills\anycrawler-read" "$HOME\.codex\skills\anycrawler-read"
Copy-Item -Recurse -Force ".\AnyCrawler-Skill\skills\anycrawler-search" "$HOME\.codex\skills\anycrawler-search"
```

After installation, start a new AI agent session so the new skill can be discovered again.

On the first managed-install invocation of `$anycrawler-read` in each agent session, its bundled CLI checks the latest tagged release from `AnyCrawler-com/AnyCrawler-Skill`. If the installed skill is behind, it upgrades itself before running the crawl command. Direct repo checkouts and the search CLI skip self-mutation.

## Quick setup

The default `$anycrawler-read` fetch path does not require setup or an API key.
Before using authenticated render, screenshot, or search requests, complete the following setup:

1. [Register or sign in to AnyCrawler](https://app.anycrawler.com/login)
2. [Create or copy an API key from the dashboard](https://app.anycrawler.com/api-keys)
3. Set `ANYCRAWLER_API_KEY` in your environment variables

### Bash

```bash
export ANYCRAWLER_API_KEY="sk-your-key"
```

### PowerShell

```powershell
$env:ANYCRAWLER_API_KEY = "sk-your-key"
```

Optional environment variables:

- `ANYCRAWLER_BASE_URL`: defaults to `https://api.anycrawler.com`

## Use with an AI agent

You can explicitly mention the skill in your prompt:

```text
Use $anycrawler-read to crawl https://example.com with render and save markdown.
```

```text
Use $anycrawler-read to take a screenshot of https://example.com and download the PNG.
```

```text
Use $anycrawler-search to search recent news about AnyCrawler.
```

From the repository root, you can also run the bundled CLI directly:

```bash
python skills/anycrawler-read/scripts/anycrawler_crawl_api.py page \
  --url https://example.com \
  --write-markdown out.md

python skills/anycrawler-read/scripts/anycrawler_crawl_api.py screenshot \
  --url https://example.com \
  --download-snapshot snapshot.png

python skills/anycrawler-search/scripts/anycrawler_search_api.py page \
  --query "site reliability engineering"

python skills/anycrawler-search/scripts/anycrawler_search_api.py news \
  --query "AnyCrawler launch" \
  --country us
```

For the stable public crawl API contract, read `skills/anycrawler-read/references/public-api.md`.
For the stable public search API contract, read `skills/anycrawler-search/references/public-api.md`.

## Documentation map

- Read runtime guide: `skills/anycrawler-read/SKILL.md`
- Read API contract: `skills/anycrawler-read/references/public-api.md`
- Read maintainer notes: `skills/anycrawler-read/references/maintainer.md`
- Read CLI implementation: `skills/anycrawler-read/scripts/anycrawler_crawl_api.py`
- Search runtime guide: `skills/anycrawler-search/SKILL.md`
- Search API contract: `skills/anycrawler-search/references/public-api.md`
- Search maintainer notes: `skills/anycrawler-search/references/maintainer.md`
- Search CLI implementation: `skills/anycrawler-search/scripts/anycrawler_search_api.py`

## Stable public endpoints

- `GET /free/v1/crawl?url={url}` for default unauthenticated fetch
- `POST /v1/crawl/page`
- `POST /v1/crawl/screenshot`
- `POST /v1/search` with `channel` set to `page`, `images`, `news`, `videos`, or `scholar`

## Notes

- This repository targets the stable public contract only and does not depend on undocumented worker passthrough fields.
- Read and search workflows are split into separate skills so invocation stays precise.
- Keep SSR follow-up parsing generic here. Site-specific extraction logic should live in a separate extraction-focused skill or workflow.

## Releases

Versioning, compatibility, billing notes, and release checklists live in each skill's `references/maintainer.md`.
