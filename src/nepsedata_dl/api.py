"""Thin wrapper around api.nepsetrading.com endpoints."""

from __future__ import annotations

import time

import requests

BASE_URL = "https://api.nepsetrading.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Referer": "https://nepsetrading.com/",
    "Origin": "https://nepsetrading.com",
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def fetch_sectors(session: requests.Session | None = None) -> list[dict]:
    """Return all symbols with their sector from the sectors endpoint."""
    s = session or _session()
    r = s.get(f"{BASE_URL}/historical-chart/sectors", timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_ohlcv(
    symbol: str,
    from_date: str = "1970-01-01",
    to_date: str = "2026-12-31",
    session: requests.Session | None = None,
) -> dict:
    """Return raw OHLCV JSON for a single symbol."""
    s = session or _session()
    r = s.get(
        f"{BASE_URL}/historical-chart/daily/adjusted",
        params={"code": symbol, "from": from_date, "to": to_date},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()
