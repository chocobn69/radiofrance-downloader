# radiofrance-downloader

Download Radio France podcasts from the command line.

Supports **France Inter**, **France Culture**, **France Musique**, **FIP**, **Mouv'**, **franceinfo**, and **France Bleu**.

## Installation

```bash
# With uv (recommended)
uv pip install radiofrance-downloader

# From source
git clone https://github.com/chocobn69/radiofrance-downloader.git
cd radiofrance-downloader
uv pip install -e .
```

## API Key Setup

This tool uses the [Radio France API](https://developers.radiofrance.fr/). You need a free API key.

1. Create an account at https://developers.radiofrance.fr/
2. Generate an API key
3. Configure it:

```bash
radiofrance-dl config set-api-key YOUR_API_KEY
```

The key is stored in `~/.config/radiofrance-downloader/config.json`.

## Usage

### List stations

```bash
radiofrance-dl list
```

### List shows for a station

```bash
radiofrance-dl list FRANCEINTER
radiofrance-dl list FRANCECULTURE
```

### Search for shows

```bash
radiofrance-dl search "terre au carré"
radiofrance-dl search "jeu des 1000" --station FRANCEINTER
```

### List episodes

```bash
radiofrance-dl episodes SHOW_URL
radiofrance-dl episodes "https://www.franceinter.fr/franceinter/podcasts/la-terre-au-carre"
```

### Download episodes

```bash
SHOW_URL="https://www.franceinter.fr/franceinter/podcasts/la-terre-au-carre"

# Download the latest episode
radiofrance-dl download "$SHOW_URL" --latest 1

# Download the 5 latest episodes
radiofrance-dl download "$SHOW_URL" --latest 5

# Download all episodes
radiofrance-dl download "$SHOW_URL" --all

# Specify output directory
radiofrance-dl download "$SHOW_URL" --latest 3 -o ~/my-podcasts
```

Files are saved to `~/Podcasts/RadioFrance/<show-name>/` by default. Already downloaded episodes are skipped.

### Configure

```bash
# View current configuration
radiofrance-dl config show

# Set API key
radiofrance-dl config set-api-key YOUR_API_KEY

# Set default output directory
radiofrance-dl config set-output-dir ~/my-podcasts
```

## Development

```bash
git clone https://github.com/chocobn69/radiofrance-downloader.git
cd radiofrance-downloader
uv venv && uv pip install -e . && uv pip install pytest pytest-cov responses ruff

# Run tests
uv run pytest tests/ -v

# Lint
uv run ruff check src/ tests/
```

## Disclaimer

This tool was built using AI-assisted "vibe coding" with [Claude Code](https://claude.ai/claude-code). The code, tests, and documentation were generated through conversational prompts and iterative refinement with Claude (Anthropic).

## License

GNU v3
