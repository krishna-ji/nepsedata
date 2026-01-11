import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download all NEPSE OHLCV data, organized by sector."
    )
    parser.add_argument(
        "-o", "--out-dir",
        type=Path,
        default=Path("data"),
        help="Output directory (default: data/)",
    )
    parser.add_argument(
        "--from-date",
        default="2010-01-01",
        help="Start date (default: 2010-01-01)",
    )
    parser.add_argument(
        "--to-date",
        default="2026-12-31",
        help="End date (default: 2026-12-31)",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=4,
        help="Concurrent downloads (default: 4)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="Delay between submissions in seconds (default: 0.3)",
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="API base URL",
    )
    args = parser.parse_args()

    from .download import download_all

    download_all(
        base_url=args.base_url,
        out_dir=args.out_dir,
        from_date=args.from_date,
        to_date=args.to_date,
        max_workers=args.workers,
        delay=args.delay,
    )
