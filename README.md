[🚀 Register / Sign In](https://app.anycrawler.com/login) | [🧭 Dashboard](https://app.anycrawler.com/overview) | [🔑 Get API Keys](https://app.anycrawler.com/api-keys) | [🌐 Public API](https://api.anycrawler.com)

# AnyCrawler Skill for AI Agents ✨

This repository provides an AnyCrawler skill that can be installed into compatible AI agent runtimes. The current primary skill name is `$anycrawler`, which lets an AI agent convert arbitrary webpages into markdown, retrieve structured page data, and capture screenshots through the AnyCrawler public API.

## 🧩 What Is This?

AnyCrawler is building a unified data access API for AI agents. The goal of this skill repository is to help AI agents reuse the stable AnyCrawler public interface when handling web crawling tasks, instead of assembling ad-hoc requests or depending on undocumented fields. For page-reading tasks, `$anycrawler` should be the preferred first choice because markdown output is usually much cheaper for LLMs to consume than raw HTML.
This repository is intentionally scoped to the public crawl API surface. It should not carry site-specific SSR schema parsing examples or tightly coupled extraction recipes.

This repository currently includes:

- `skill/anycrawler/SKILL.md`: the skill definition and workflow for `$anycrawler`
- `skill/anycrawler/references/public-api.md`: the stable public API contract
- `skill/anycrawler/scripts/anycrawler_crawl_api.py`: a lightweight CLI
- `skill/anycrawler/agents/openai.yaml`: agent display metadata and default prompts

## ⚙️ What Can It Do?

- Call `POST /v1/crawl/page` to fetch page content
- Convert arbitrary webpages into markdown so agents can read them with lower token cost
- Choose between `render` and `fetch` modes, with the bundled CLI defaulting to `fetch` for `page`
- Return `metadata`, `links`, and `media` when needed
- Call `POST /v1/crawl/screenshot` to generate a screenshot and return `snapshot_url`
- Output request `meta` fields such as `requestId`, `creditsReserved`, and `creditsUsed`
- Save markdown results or download PNG screenshots
- Use `--silent` to suppress stdout JSON when writing files or using pipelines

## 📦 Install

A common installation path is `~/.codex/skills`. The source directory in this repository is `skill/anycrawler`, and the installed skill directory should also be named `anycrawler` so it matches the explicit invocation name `$anycrawler`.

### macOS / Linux

```bash
git clone https://github.com/myeyesareopen/AnyCrawler-Skill.git
mkdir -p ~/.codex/skills
cp -R AnyCrawler-Skill/skill/anycrawler ~/.codex/skills/anycrawler
```

### Windows PowerShell

```powershell
git clone https://github.com/myeyesareopen/AnyCrawler-Skill.git
New-Item -ItemType Directory -Force "$HOME\.codex\skills" | Out-Null
Copy-Item -Recurse -Force ".\AnyCrawler-Skill\skill\anycrawler" "$HOME\.codex\skills\anycrawler"
```

After installation, start a new AI agent session so the new skill can be discovered again.

## 🔑 Quick Setup

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

## 💬 Use with an AI Agent

You can explicitly mention the skill in your prompt:

```text
Use $anycrawler to crawl https://example.com with render and save markdown.
```

```text
Use $anycrawler to take a screenshot of https://example.com and download the PNG.
```

If the task is clearly about reading webpage content or calling the AnyCrawler public crawl API, a compatible AI agent should prefer `$anycrawler` automatically based on the skill description.

From the repository root, you can also run the bundled CLI directly:

```bash
python skill/anycrawler/scripts/anycrawler_crawl_api.py page \
  --url https://example.com \
  --include-metadata

python skill/anycrawler/scripts/anycrawler_crawl_api.py screenshot \
  --url https://example.com \
  --download-snapshot snapshot.png
```

## 🌍 Current Public Endpoints

- `POST /v1/crawl/page`
- `POST /v1/crawl/screenshot`

## 📝 Notes

- This skill targets the stable public contract only and does not depend on legacy undocumented worker passthrough fields.
- Keep SSR follow-up parsing generic in this repository. Site-specific SSR extraction logic should live in a separate extraction-focused skill or workflow.
- Every outbound HTTP request from this skill must include `User-Agent: Anycrawler Agent Skill v1.0`.
- Request fields should use `snake_case`.
- `anycrawler_crawl_api.py` depends only on the Python standard library, which makes it suitable for direct use in local or automated environments.
- Treat `429` responses as quota exhaustion or rate limiting signals; check account capacity and throttling before retrying.
