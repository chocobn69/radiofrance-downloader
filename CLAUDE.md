# CLAUDE.md

## Project

Python CLI tool + library for downloading Radio France podcasts.
Entry point: `radiofrance-dl` (click CLI with Rich output).

## Commands

```bash
# Run tests
uv run pytest tests/ -v

# Lint
uv run ruff check src/ tests/

# Auto-fix lint
uv run ruff check --fix src/ tests/

# Install in dev mode
uv pip install -e . && uv pip install pytest pytest-cov responses ruff

# CLI smoke test
uv run radiofrance-dl list
```

## Architecture

- `src/radiofrance_downloader/` — 8 modules
  - `api.py` — GraphQL API client (POST to openapi.radiofrance.fr/v1/graphql, requires API key)
  - `scraper.py` — Web scraping fallback (no API key needed)
  - `rss.py` — RSS feed parser fallback
  - `downloader.py` — Streaming MP3 download engine
  - `cli.py` — Click CLI with Rich tables/progress (search, list, episodes, download, config set-api-key, config set-output-dir, config show)
  - `models.py` — Frozen dataclasses (Station, Show, Episode, DownloadResult)
  - `config.py` — JSON config at `~/.config/radiofrance-downloader/config.json`
  - `exceptions.py` — Exception hierarchy

## Testing patterns

- All HTTP is blocked by default via autouse `_block_http` fixture in `conftest.py` (uses `responses.start()/stop()/reset()`)
- Register mocks with `responses.post(GRAPHQL_URL, ...)` directly in tests — do NOT use `@responses.activate` decorator (conflicts with autouse fixture)
- `Config.load()` must be patched in CLI tests to avoid filesystem reads
- Rich `Progress` must be replaced with `_NoOpProgress` dummy in CLI download tests to avoid live refresh thread hanging in CliRunner
