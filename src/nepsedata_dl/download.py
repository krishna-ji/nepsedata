"""Download all NEPSE stocks sector-wise into data/ directory.

Layout:
    data/
        sectors.json           # full sector→symbol mapping
        ohlcv/1D/
            commercial_banks/
                NABIL.csv
                ...
            hydro_power/
                AHPC.csv
                ...
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
)

from .api import _session, fetch_ohlcv, fetch_sectors

console = Console()

# Normalise sector names to filesystem-safe directory names
SECTOR_ALIASES: dict[str, str] = {
    "NEPSE": "_index",
}


def _slugify(sector: str) -> str:
    """Turn 'COMMERCIAL BANKS' → 'commercial_banks'."""
    if sector.upper() in SECTOR_ALIASES:
        return SECTOR_ALIASES[sector.upper()]
    return sector.strip().lower().replace(" ", "_").replace("&", "and")


def build_sector_map(
    raw: list[dict],
    *,
    exclude: set[str] | None = None,
) -> dict[str, list[str]]:
    """Group symbols by sector slug, cleaning the 'exchange' field."""
    exclude = exclude or set()
    sector_map: dict[str, list[str]] = defaultdict(list)
    for item in raw:
        sector_raw = (
            item.get("exchange", "")
            .replace(" src:NepseTrading.com", "")
            .replace(" src:NEPSE", "")
            .strip()
        )
        slug = _slugify(sector_raw)
        symbol = item["symbol"]
        if slug in exclude:
            continue
        sector_map[slug].append(symbol)
    # sort symbols within each sector
    for symbols in sector_map.values():
        symbols.sort()
    return dict(sorted(sector_map.items()))


def _download_one(
    symbol: str,
    out_path: Path,
    session,
    from_date: str,
    to_date: str,
) -> tuple[str, int, str | None]:
    """Download OHLCV for a single symbol. Returns (symbol, rows, error)."""
    try:
        data = fetch_ohlcv(symbol, from_date, to_date, session=session)

        if isinstance(data, dict):
            if data.get("s") != "ok":
                return symbol, 0, f"status={data.get('s')}"
            ts = pd.to_datetime(pd.Series(data["t"], dtype="int64"), unit="s", utc=True)
            df = pd.DataFrame(
                {
                    "Timestamp": ts,
                    "Open": pd.array(data["o"], dtype="float32"),
                    "High": pd.array(data["h"], dtype="float32"),
                    "Low": pd.array(data["l"], dtype="float32"),
                    "Close": pd.array(data["c"], dtype="float32"),
                    "Volume": pd.array(data["v"], dtype="float32"),
                }
            )
        elif isinstance(data, list):
            if not data:
                return symbol, 0, "empty list"
            df = pd.DataFrame(data)
            df = df.rename(
                columns={
                    "date": "Timestamp",
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                }
            )
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True)
        else:
            return symbol, 0, f"unexpected type {type(data)}"

        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")
        df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
        df = df.sort_values("Timestamp").reset_index(drop=True)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path, index=False)
        return symbol, len(df), None

    except Exception as e:
        return symbol, 0, str(e)


def download_all(
    out_dir: Path = Path("data"),
    from_date: str = "2010-01-01",
    to_date: str = "2026-12-31",
    max_workers: int = 4,
    exclude_sectors: set[str] | None = None,
    delay: float = 0.3,
) -> None:
    """Download all stocks, organized by sector."""
    exclude_sectors = exclude_sectors or {"_index"}

    console.rule("[bold]NEPSE Sector-wise Download")

    # 1. Fetch sector listing
    session = _session()
    console.print("Fetching sector listing…")
    raw = fetch_sectors(session)
    sector_map = build_sector_map(raw, exclude=exclude_sectors)

    # Save sector map
    out_dir.mkdir(parents=True, exist_ok=True)
    sectors_path = out_dir / "sectors.json"
    sectors_path.write_text(json.dumps(sector_map, indent=2), encoding="utf-8")
    console.print(f"Saved sector map → [cyan]{sectors_path}[/]")

    total = sum(len(v) for v in sector_map.values())
    console.print(
        f"[green]{len(sector_map)}[/] sectors, [green]{total}[/] symbols total"
    )

    # 2. Download OHLCV per symbol
    errors: list[tuple[str, str]] = []
    succeeded = 0

    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading", total=total)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {}
            for sector_slug, symbols in sector_map.items():
                for sym in symbols:
                    csv_path = out_dir / "ohlcv" / "1D" / sector_slug / f"{sym}.csv"
                    fut = pool.submit(
                        _download_one, sym, csv_path, session, from_date, to_date
                    )
                    futures[fut] = (sector_slug, sym)
                    time.sleep(delay)  # stagger submissions

            for fut in as_completed(futures):
                sector_slug, sym = futures[fut]
                symbol, rows, err = fut.result()
                if err:
                    errors.append((symbol, err))
                else:
                    succeeded += 1
                progress.advance(task)

    # 3. Summary
    console.rule("[bold]Summary")
    console.print(f"  [green]OK[/]:     {succeeded}")
    console.print(f"  [red]Failed[/]: {len(errors)}")
    if errors:
        console.print("\n[bold red]Failures:[/]")
        for sym, err in sorted(errors):
            console.print(f"  {sym}: {err}")
