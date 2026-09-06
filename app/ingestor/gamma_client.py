"""
Polymarket Gamma API Client for market metadata, events, and outcome prices.
"""
import json
from typing import Any

import requests

from app.core.config import GAMMA_API_URL
from app.core.models import Event, Market, MarketOutcome


class GammaClient:
    """Client for Polymarket's Gamma REST API."""

    def __init__(self, base_url: str = GAMMA_API_URL, timeout: int = 12):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {
            "User-Agent": "PolyArb/1.0 (Autonomous Quant Intelligence)",
            "Accept": "application/json"
        }

    def _parse_market(self, m_dict: dict[str, Any]) -> Market:
        """Parses a raw market dict into a strongly typed Market object."""
        outcomes_list = []
        outcomes_names = json.loads(m_dict.get("outcomes", '["Yes", "No"]')) if isinstance(m_dict.get("outcomes"), str) else (m_dict.get("outcomes") or ["Yes", "No"])
        prices_raw = json.loads(m_dict.get("outcomePrices", '["0", "0"]')) if isinstance(m_dict.get("outcomePrices"), str) else (m_dict.get("outcomePrices") or [0, 0])
        token_ids_raw = json.loads(m_dict.get("clobTokenIds", '[]')) if isinstance(m_dict.get("clobTokenIds"), str) else (m_dict.get("clobTokenIds") or [])

        for i, name in enumerate(outcomes_names):
            p = float(prices_raw[i]) if i < len(prices_raw) and prices_raw[i] is not None else 0.0
            tid = str(token_ids_raw[i]) if i < len(token_ids_raw) else None
            outcomes_list.append(MarketOutcome(name=str(name), price=p, token_id=tid))

        return Market(
            id=str(m_dict.get("id", "")),
            question=m_dict.get("question", "Unknown Market"),
            condition_id=str(m_dict.get("conditionId", "")),
            slug=m_dict.get("slug", ""),
            resolution_source=m_dict.get("resolutionSource"),
            end_date=m_dict.get("endDate"),
            volume_24h=float(m_dict.get("volume24hr", 0) or 0),
            liquidity=float(m_dict.get("liquidity", 0) or 0),
            spread=float(m_dict.get("spread", 0) or 0),
            neg_risk=bool(m_dict.get("negRisk", False)),
            outcomes=outcomes_list,
            uma_bond=str(m_dict.get("umaBond")) if m_dict.get("umaBond") is not None else None,
            rewards_max_spread=float(m_dict.get("rewardsMaxSpread", 0) or 0),
            rewards_min_size=float(m_dict.get("rewardsMinSize", 0) or 0)
        )

    def get_events(self, limit: int = 50, closed: bool = False, order: str = "volume24hr") -> list[Event]:
        """Fetches active events and nested multi-outcome markets."""
        url = f"{self.base_url}/events"
        params = {
            "closed": str(closed).lower(),
            "limit": limit,
            "order": order,
            "ascending": "false"
        }
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            events = []
            for item in data:
                markets = [self._parse_market(m) for m in item.get("markets", [])]
                events.append(Event(
                    id=str(item.get("id", "")),
                    title=item.get("title", "Untitled Event"),
                    slug=item.get("slug", ""),
                    volume_24h=float(item.get("volume24hr", 0) or 0),
                    markets=markets,
                    neg_risk=any(m.neg_risk for m in markets)
                ))
            return events
        except Exception as e:
            print(f"GammaClient get_events error: {e}")
            return []

    def get_markets(self, limit: int = 100, closed: bool = False, order: str = "volume24hr") -> list[Market]:
        """Fetches active individual markets."""
        url = f"{self.base_url}/markets"
        params = {
            "closed": str(closed).lower(),
            "limit": limit,
            "order": order,
            "ascending": "false"
        }
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return [self._parse_market(m) for m in data]
        except Exception as e:
            print(f"GammaClient get_markets error: {e}")
            return []

    def get_market_by_slug(self, slug: str) -> Market | None:
        """Retrieves a single market by slug."""
        url = f"{self.base_url}/markets"
        params = {"slug": slug}
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if data and len(data) > 0:
                return self._parse_market(data[0])
            return None
        except Exception as e:
            print(f"GammaClient get_market_by_slug error: {e}")
            return None
