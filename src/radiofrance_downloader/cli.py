"""CLI interface for radiofrance-downloader."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, TransferSpeedColumn
from rich.table import Table

from radiofrance_downloader import __version__
from radiofrance_downloader.api import STATIONS, RadioFranceAPI
from radiofrance_downloader.config import Config
from radiofrance_downloader.downloader import EpisodeDownloader
from radiofrance_downloader.exceptions import RadioFranceError

console = Console()
err_console = Console(stderr=True)


def _get_api(config: Config) -> RadioFranceAPI:
    """Get an API client, raising a helpful error if no key is set."""
    if not config.api_key:
        raise click.ClickException(
            "No API key configured. Run: radiofrance-dl config set-api-key <key>"
        )
    return RadioFranceAPI(config.api_key)


@click.group()
@click.version_option(version=__version__, prog_name="radiofrance-dl")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Download Radio France podcasts."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = Config.load()


@main.command()
@click.argument("query")
@click.pass_context
def search(ctx: click.Context, query: str) -> None:
    """Search for shows by name."""
    config = ctx.obj["config"]
    api = _get_api(config)

    try:
        shows = api.search_shows(query)
    except RadioFranceError as e:
        raise click.ClickException(str(e)) from e

    if not shows:
        console.print("[yellow]No shows found.[/yellow]")
        return

    table = Table(title=f"Search results for '{query}'")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Station", style="green")
    table.add_column("Description", max_width=50)

    for show in shows:
        station_name = show.station.name if show.station else "—"
        desc = (show.description[:47] + "...") if len(show.description) > 50 else show.description
        table.add_row(show.id, show.title, station_name, desc)

    console.print(table)


@main.command("list")
@click.argument("station", required=False)
@click.pass_context
def list_cmd(ctx: click.Context, station: str | None) -> None:
    """List stations, or shows for a station."""
    if station is None:
        table = Table(title="Radio France Stations")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="bold")
        table.add_column("URL")

        for sid, st in STATIONS.items():
            table.add_row(str(sid), st.name, st.url)

        console.print(table)
        return

    # If station is provided, search for shows on that station
    config = ctx.obj["config"]
    api = _get_api(config)

    try:
        shows = api.search_shows(station)
    except RadioFranceError as e:
        raise click.ClickException(str(e)) from e

    if not shows:
        console.print(f"[yellow]No shows found for '{station}'.[/yellow]")
        return

    table = Table(title=f"Shows matching '{station}'")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Description", max_width=60)

    for show in shows:
        desc = (show.description[:57] + "...") if len(show.description) > 60 else show.description
        table.add_row(show.id, show.title, desc)

    console.print(table)


@main.command()
@click.argument("show_id")
@click.option("--page", default=0, help="Page offset.")
@click.pass_context
def episodes(ctx: click.Context, show_id: str, page: int) -> None:
    """List episodes for a show."""
    config = ctx.obj["config"]
    api = _get_api(config)

    try:
        eps, next_page = api.get_show_episodes(show_id, page=page)
    except RadioFranceError as e:
        raise click.ClickException(str(e)) from e

    if not eps:
        console.print("[yellow]No episodes found.[/yellow]")
        return

    table = Table(title=f"Episodes for show {show_id}")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Date", style="green")
    table.add_column("Duration", justify="right")

    for ep in eps:
        date_str = ep.published_at.strftime("%Y-%m-%d") if ep.published_at else "—"
        dur = f"{ep.duration // 60}:{ep.duration % 60:02d}" if ep.duration else "—"
        table.add_row(ep.id, ep.title, date_str, dur)

    console.print(table)

    if next_page is not None:
        console.print(f"\n[dim]Next page: --page {next_page}[/dim]")


@main.command()
@click.argument("show_id")
@click.option("--latest", "latest_n", type=int, default=None, help="Download latest N episodes.")
@click.option("--all", "fetch_all", is_flag=True, help="Download all available episodes.")
@click.option("-o", "--output", "output_dir", type=click.Path(), default=None, help="Output dir.")
@click.pass_context
def download(
    ctx: click.Context,
    show_id: str,
    latest_n: int | None,
    fetch_all: bool,
    output_dir: str | None,
) -> None:
    """Download episodes for a show."""
    config = ctx.obj["config"]
    api = _get_api(config)

    out = Path(output_dir) if output_dir else Path(config.output_dir)

    try:
        eps, _ = api.get_show_episodes(show_id, fetch_all=fetch_all)
    except RadioFranceError as e:
        raise click.ClickException(str(e)) from e

    if latest_n is not None:
        eps = eps[:latest_n]

    if not eps:
        console.print("[yellow]No episodes to download.[/yellow]")
        return

    console.print(f"Downloading {len(eps)} episode(s) to [bold]{out}[/bold]\n")

    downloader = EpisodeDownloader(output_dir=out)

    with Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        console=console,
        disable=not console.is_terminal,
    ) as progress:
        for ep in eps:
            task = progress.add_task(
                f"[cyan]{ep.title[:50]}",
                total=None,
            )

            def on_progress(downloaded: int, total: int, _task=task) -> None:
                if total:
                    progress.update(_task, total=total, completed=downloaded)
                else:
                    progress.update(_task, completed=downloaded)

            try:
                result = downloader.download_episode(ep, progress_callback=on_progress)
            except RadioFranceError as e:
                progress.update(task, description=f"[red]FAILED: {ep.title[:40]}")
                err_console.print(f"[red]Error downloading {ep.title}: {e}[/red]")
                continue

            if result.already_existed:
                progress.update(
                    task,
                    description=f"[dim]SKIPPED: {ep.title[:40]}[/dim]",
                    completed=result.file_size,
                    total=result.file_size,
                )
            elif result.success:
                progress.update(
                    task,
                    description=f"[green]OK: {ep.title[:40]}[/green]",
                    completed=result.file_size,
                    total=result.file_size,
                )


@main.group()
def config() -> None:
    """Manage configuration."""


@config.command("set-api-key")
@click.argument("key")
def set_api_key(key: str) -> None:
    """Store your Radio France API key."""
    cfg = Config.load()
    cfg.api_key = key
    cfg.save()
    console.print("[green]API key saved.[/green]")


@config.command("show")
def show_config() -> None:
    """Display current configuration."""
    cfg = Config.load()
    table = Table(title="Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    api_key_display = cfg.api_key[:8] + "..." if len(cfg.api_key) > 8 else cfg.api_key or "—"
    table.add_row("api_key", api_key_display)
    table.add_row("output_dir", cfg.output_dir)
    table.add_row("default_station", cfg.default_station or "—")

    console.print(table)
