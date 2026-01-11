# nepsedata-dl

Download all NEPSE OHLCV data organized by sector.

## Install

```bash
uv sync          # inside this directory
# or
pip install -e .
```

## Usage

```bash
# Download everything into data/
nepsedata-dl

# Custom output dir and date range
nepsedata-dl -o ../data --from-date 2015-01-01 --to-date 2026-06-23

# More concurrent workers
nepsedata-dl -w 8 --delay 0.2
```

## Output layout

```
data/
  sectors.json              # sector -> [symbols] mapping
  ohlcv/1D/
    commercial_banks/
      ADBL.csv
      NABIL.csv
      ...
    hydro_power/
      AHPC.csv
      ...
    microfinance/
      ...
```

Each CSV has columns: `Timestamp, Open, High, Low, Close, Volume`

## As a library

```python
from nepsedata_dl.api import fetch_sectors, fetch_ohlcv
from nepsedata_dl.download import build_sector_map, download_all
from pathlib import Path

# Get sector -> symbols map
sector_map = build_sector_map(fetch_sectors())

# Download one symbol
data = fetch_ohlcv("NABIL", from_date="2020-01-01")

# Download everything
download_all(out_dir=Path("data"))
```
