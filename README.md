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

### Search for shows

```bash
radiofrance-dl search "meurice"
radiofrance-dl search "terre au carré"
```

### List episodes

```bash
radiofrance-dl episodes SHOW_ID
radiofrance-dl episodes SHOW_ID --page 2
```

### Download episodes

```bash
# Download the latest episode
radiofrance-dl download SHOW_ID --latest 1

# Download the 5 latest episodes
radiofrance-dl download SHOW_ID --latest 5

# Download all episodes
radiofrance-dl download SHOW_ID --all

# Specify output directory
radiofrance-dl download SHOW_ID --latest 3 -o ~/my-podcasts
```

Files are saved to `~/Podcasts/RadioFrance/<show-name>/` by default. Already downloaded episodes are skipped.

### View configuration

```bash
radiofrance-dl config show
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

## License

MIT
