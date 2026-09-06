"""
Risk-Free Paper Trading & Portfolio Simulation Engine.
Logs theoretical trades, deducts fees and slippage, and tracks strategy PnL.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.config import (
    ESTIMATED_FEE_SLIPPAGE_PCT,
    MAX_POSITION_SIZE_USDC,
    PAPER_STARTING_BALANCE_USDC,
)
from app.core.models import ArbitrageOpportunity, PaperTrade, ResolutionDiscount


class PaperTrader:
    """Simulates trades on Polymarket with zero capital risk."""

    def __init__(
        self,
        starting_balance: float = PAPER_STARTING_BALANCE_USDC,
        max_position: float = MAX_POSITION_SIZE_USDC,
        fee_buffer_pct: float = ESTIMATED_FEE_SLIPPAGE_PCT
    ):
        self.starting_balance = starting_balance
        self.current_balance = starting_balance
        self.max_position = max_position
        self.fee_buffer_pct = fee_buffer_pct
        self.trades: list[PaperTrade] = []

    def execute_arbitrage(self, opp: ArbitrageOpportunity, amount_usdc: float = 200.0) -> PaperTrade:
        """Simulates execution of a negative-risk arbitrage trade."""
        size = min(amount_usdc, self.max_position, self.current_balance)
        trade_id = f"arb_{uuid.uuid4().hex[:6]}"

        if size <= 0:
            return PaperTrade(
                trade_id=trade_id,
                strategy="NEGATIVE_RISK",
                asset=opp.event_title,
                action="REJECTED_NO_FUNDS",
                entry_price=opp.sum_of_prices,
                size_usdc=0.0,
                shares=0.0,
                status="FAILED",
                pnl_usdc=0.0
            )

        # Net profit after slippage
        net_profit_pct = max(0.0, opp.net_profit_pct)
        pnl = round(size * (net_profit_pct / 100.0), 2)

        self.current_balance += pnl
        trade = PaperTrade(
            trade_id=trade_id,
            strategy="NEGATIVE_RISK",
            asset=opp.event_title,
            action="MINT_AND_SELL" if opp.strategy_type == "OVERPRICED_BASKET" else "BUY_BASKET",
            entry_price=opp.sum_of_prices,
            size_usdc=size,
            shares=round(size / opp.sum_of_prices, 2) if opp.sum_of_prices > 0 else 0,
            status="RESOLVED_WIN",
            pnl_usdc=pnl,
            closed_at=datetime.now(timezone.utc).isoformat()
        )
        self.trades.append(trade)
        return trade

    def execute_resolution_lag(self, disc: ResolutionDiscount, amount_usdc: float = 200.0) -> PaperTrade:
        """Simulates buying a discounted decided token and waiting for settlement."""
        size = min(amount_usdc, self.max_position, self.current_balance)
        trade_id = f"lag_{uuid.uuid4().hex[:6]}"

        if size <= 0:
            return PaperTrade(
                trade_id=trade_id,
                strategy="RESOLUTION_LAG",
                asset=disc.question,
                action="REJECTED_NO_FUNDS",
                entry_price=disc.current_price,
                size_usdc=0.0,
                shares=0.0,
                status="FAILED",
                pnl_usdc=0.0
            )

        shares = size / disc.current_price if disc.current_price > 0 else 0
        pnl = round(shares * (1.0 - disc.current_price) * (1.0 - self.fee_buffer_pct / 100.0), 2)

        self.current_balance += pnl
        trade = PaperTrade(
            trade_id=trade_id,
            strategy="RESOLUTION_LAG",
            asset=f"{disc.question} ({disc.winning_side})",
            action="BUY_DISCOUNTED",
            entry_price=disc.current_price,
            size_usdc=size,
            shares=round(shares, 2),
            status="RESOLVED_WIN",
            pnl_usdc=pnl,
            closed_at=datetime.now(timezone.utc).isoformat()
        )
        self.trades.append(trade)
        return trade

    def get_summary(self) -> dict[str, Any]:
        """Returns overall performance statistics."""
        wins = [t for t in self.trades if t.pnl_usdc > 0]
        losses = [t for t in self.trades if t.pnl_usdc < 0]
        total_pnl = round(self.current_balance - self.starting_balance, 2)
        roi_pct = round((total_pnl / self.starting_balance) * 100.0, 2)
        win_rate = round((len(wins) / len(self.trades) * 100.0), 1) if self.trades else 0.0

        return {
            "starting_balance_usdc": self.starting_balance,
            "current_balance_usdc": round(self.current_balance, 2),
            "total_pnl_usdc": total_pnl,
            "roi_pct": roi_pct,
            "total_trades": len(self.trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate_pct": win_rate,
            "recent_trades": [
                {
                    "trade_id": t.trade_id,
                    "strategy": t.strategy,
                    "asset": t.asset[:40],
                    "size_usdc": t.size_usdc,
                    "pnl_usdc": t.pnl_usdc,
                    "status": t.status
                }
                for t in reversed(self.trades[-10:])
            ]
        }
