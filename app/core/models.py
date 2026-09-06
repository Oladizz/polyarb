"""
Data models and type definitions for PolyArb.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class MarketOutcome:
    name: str
    price: float
    token_id: str | None = None


@dataclass
class Market:
    id: str
    question: str
    condition_id: str
    slug: str
    resolution_source: str | None = None
    end_date: str | None = None
    volume_24h: float = 0.0
    liquidity: float = 0.0
    spread: float = 0.0
    neg_risk: bool = False
    outcomes: list[MarketOutcome] = field(default_factory=list)
    uma_bond: str | None = None
    rewards_max_spread: float = 0.0
    rewards_min_size: float = 0.0


@dataclass
class Event:
    id: str
    title: str
    slug: str
    volume_24h: float
    markets: list[Market] = field(default_factory=list)
    neg_risk: bool = False


@dataclass
class ArbitrageOpportunity:
    event_id: str
    event_title: str
    strategy_type: str  # "MINT_DISCOUNT" or "OVERPRICED_BASKET"
    outcomes_count: int
    sum_of_prices: float
    spread_pct: float
    net_profit_pct: float
    target_outcomes: list[dict[str, Any]]
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ResolutionDiscount:
    market_id: str
    question: str
    winning_side: str
    current_price: float
    settlement_discount_pct: float
    annualized_apy_pct: float
    end_date: str | None
    volume_24h: float
    uma_bond: str | None
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class RewardMarket:
    market_id: str
    question: str
    rewards_max_spread: float
    rewards_min_size: float
    current_spread: float
    volume_24h: float


@dataclass
class PaperTrade:
    trade_id: str
    strategy: str
    asset: str
    action: str  # "BUY", "SELL", "MINT_SPLIT", "REDEEM"
    entry_price: float
    size_usdc: float
    shares: float
    status: str  # "OPEN", "RESOLVED_WIN", "RESOLVED_LOSS"
    pnl_usdc: float = 0.0
    opened_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    closed_at: str | None = None
