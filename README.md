[🚀 Register / Sign In](https://app.anycrawler.com/login) | [🧭 Dashboard](https://app.anycrawler.com/overview) | [🔑 Get API Keys](https://app.anycrawler.com/api-keys) | [🌐 Public API](https://api.anycrawler.com)

# AnyCrawler Skill for AI Agents ✨

This repository provides an AnyCrawler skill that can be installed into compatible AI agent runtimes. The primary skill name is `$anycrawler`.

## What this repo contains

- `skill/anycrawler/SKILL.md`: the slim agent-facing runtime guide
- `skill/anycrawler/references/public-api.md`: the minimal API contract for agent use
- `skill/anycrawler/references/maintainer.md`: release, billing, and full gateway notes
- `skill/anycrawler/scripts/anycrawler_crawl_api.py`: the bundled CLI
- `skill/anycrawler/agents/openai.yaml`: agent display metadata
- `tests/test_anycrawler_crawl_api.py`: regression tests for the CLI

## Install

A common installation path is `~/.codex/skills`. The source directory in this repository is `skill/anycrawler`, and the installed skill directory should also be named `anycrawler` so it matches the explicit invocation name `$anycrawler`.

### macOS / Linux

```bash
git clone https://github.com/AnyCrawler-com/AnyCrawler-Skill.git
mkdir -p ~/.codex/skills
cp -R AnyCrawler-Skill/skill/anycrawler ~/.codex/skills/anycrawler
```

### Windows PowerShell

```powershell
git clone https://github.com/AnyCrawler-com/AnyCrawler-Skill.git
New-Item -ItemType Directory -Force "$HOME\.codex\skills" | Out-Null
Copy-Item -Recurse -Force ".\AnyCrawler-Skill\skill\anycrawler" "$HOME\.codex\skills\anycrawler"
```

After installation, start a new AI agent session so the new skill can be discovered again.

On the first managed-install invocation in each agent session, the bundled CLI checks the latest tagged release from `AnyCrawler-com/AnyCrawler-Skill`. If the installed skill is behind, it upgrades itself before running the crawl command. Direct repo checkouts skip self-mutation.

## Quick setup

Before using AnyCrawler, complete the following setup:

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
Use $anycrawler to crawl https://example.com with render and save markdown.
```

```text
Use $anycrawler to take a screenshot of https://example.com and download the PNG.
```

From the repository root, you can also run the bundled CLI directly:

```bash
python skill/anycrawler/scripts/anycrawler_crawl_api.py page \
  --url https://example.com \
  --include-metadata

python skill/anycrawler/scripts/anycrawler_crawl_api.py screenshot \
  --url https://example.com \
  --download-snapshot snapshot.png
```

## Documentation map

- Agent runtime guide: `skill/anycrawler/SKILL.md`
- Minimal API contract: `skill/anycrawler/references/public-api.md`
- Maintainer-only notes: `skill/anycrawler/references/maintainer.md`
- CLI implementation: `skill/anycrawler/scripts/anycrawler_crawl_api.py`

## Releases

Versioning, compatibility, billing notes, and the release checklist now live in `skill/anycrawler/references/maintainer.md`.
