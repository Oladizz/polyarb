"""
Polymarket CLOB REST Client for Order Books, Midpoints, and Fee Schedules.
"""
from typing import Any

import requests

from app.core.config import CLOB_API_URL


class ClobClient:
    """Client for interacting with Polymarket's Central Limit Order Book (CLOB)."""

    def __init__(self, base_url: str = CLOB_API_URL, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {"User-Agent": "PolyArb/1.0", "Accept": "application/json"}

    def get_orderbook(self, token_id: str) -> dict[str, Any] | None:
        """Retrieves bids and asks for a specific ERC-1155 outcome token."""
        url = f"{self.base_url}/book"
        params = {"token_id": token_id}
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            print(f"ClobClient get_orderbook error for {token_id}: {e}")
            return None

    def get_fee_schedule(self) -> dict[str, Any]:
        """Fetches maker and taker fee schedules."""
        url = f"{self.base_url}/fee-schedule"
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            return {"maker_fee": 0.0, "taker_fee": 0.0}
        except Exception:
            return {"maker_fee": 0.0, "taker_fee": 0.0}

    def get_midpoint(self, token_id: str) -> float | None:
        """Fetches the midpoint price for a token."""
        url = f"{self.base_url}/midpoint"
        params = {"token_id": token_id}
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                return float(data.get("mid", 0))
            return None
        except Exception:
            return None
