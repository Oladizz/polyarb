"""
Autonomous Quant Execution Engine for PolyArb.
Performs continuous live market polling, risk filtering via OracleAuditor,
automated position sizing, execution, and settlement tracking.
"""
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.core.config import (
    ESTIMATED_FEE_SLIPPAGE_PCT,
    MAX_POSITION_SIZE_USDC,
    MIN_VOLUME_USD,
    PAPER_STARTING_BALANCE_USDC,
)
from app.core.models import ResolutionDiscount
from app.ingestor.gamma_client import GammaClient
from app.scanner.oracle_audit import OracleAuditor
from app.scanner.resolution_lag import ResolutionLagScanner

logger = logging.getLogger("polyarb.trader")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class AutonomousTrader:
    """Autonomous trading engine managing paper and live execution cycles."""

    def __init__(
        self,
        mode: str = "paper",
        data_dir: str = "data",
        starting_balance: float = PAPER_STARTING_BALANCE_USDC,
        max_position_size: float = MAX_POSITION_SIZE_USDC,
        max_active_positions: int = 5,
        min_discount_pct: float = 1.0,
        min_volume_usd: float = MIN_VOLUME_USD,
        fee_buffer_pct: float = ESTIMATED_FEE_SLIPPAGE_PCT,
    ):
        self.mode = mode.lower()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data_dir / "portfolio.json"

        self.starting_balance = starting_balance
        self.balance_usdc = starting_balance
        self.max_position_size = max_position_size
        self.max_active_positions = max_active_positions
        self.min_discount_pct = min_discount_pct
        self.min_volume_usd = min_volume_usd
        self.fee_buffer_pct = fee_buffer_pct

        self.active_positions: list[dict[str, Any]] = []
        self.trade_history: list[dict[str, Any]] = []

        self.gamma_client = GammaClient()
        self.scanner = ResolutionLagScanner(min_volume=self.min_volume_usd)
        self.oracle_auditor = OracleAuditor()

        self._load_state()

    def _load_state(self):
        """Loads persistent portfolio and history from disk if exists."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.balance_usdc = float(data.get("cash_balance_usdc", data.get("balance_usdc", self.starting_balance)))
                    self.starting_balance = float(data.get("starting_balance", self.starting_balance))
                    self.active_positions = data.get("active_positions", [])
                    self.trade_history = data.get("trade_history", [])
                logger.info("Loaded portfolio state: $%.2f USDC, %d active positions, %d historical trades",
                            self.balance_usdc, len(self.active_positions), len(self.trade_history))
            except Exception as e:
                logger.error("Failed to load portfolio state from %s: %s", self.state_file, e)

    def _save_state(self):
        """Persists portfolio state and trade history to disk atomically."""
        tmp_file = self.state_file.with_suffix(".tmp")
        invested = round(sum(p.get("size_usdc", 0) for p in self.active_positions), 2)
        realized = round(sum(t.get("pnl_usdc", 0) for t in self.trade_history), 2)
        data = {
            "mode": self.mode,
            "starting_balance": self.starting_balance,
            "cash_balance_usdc": round(self.balance_usdc, 2),
            "invested_usdc": invested,
            "realized_pnl_usdc": realized,
            "active_positions": self.active_positions,
            "trade_history": self.trade_history,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with open(tmp_file, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_file, self.state_file)
        except Exception as e:
            logger.error("Failed to save portfolio state: %s", e)

    def scan_opportunities(self) -> list[ResolutionDiscount]:
        """Fetches live markets and filters by yield and UMA Oracle risk."""
        markets = self.gamma_client.get_markets(limit=75)
        raw_discounts = self.scanner.scan_all(markets)

        qualified: list[ResolutionDiscount] = []
        market_by_id = {m.id: m for m in markets}

        for d in raw_discounts:
            market_obj = market_by_id.get(d.market_id)
            if market_obj:
                audit = self.oracle_auditor.audit_market(market_obj)
                if audit.get("risk_level") == "HIGH":
                    logger.warning("Rejecting market '%s' due to HIGH UMA dispute risk flags: %s",
                                   d.question[:40], audit.get("matched_risk_keywords"))
                    continue
            qualified.append(d)

        return qualified

    def execute_buy(self, discount: ResolutionDiscount) -> Optional[dict[str, Any]]:
        """Executes a buy order in either paper or live mode."""
        # 1. Check if already holding this market
        existing_ids = {p["market_id"] for p in self.active_positions}
        if discount.market_id in existing_ids:
            return None

        # 2. Check position limit
        if len(self.active_positions) >= self.max_active_positions:
            logger.info("Max active positions limit (%d) reached. Skipping new entries.", self.max_active_positions)
            return None

        # 3. Size position
        size_usdc = min(self.max_position_size, self.balance_usdc)
        if size_usdc < 20.0:
            logger.warning("Insufficient funds for trade ($%.2f remaining).", self.balance_usdc)
            return None

        shares = round(size_usdc / discount.current_price, 2)
        trade_id = f"pos_{uuid.uuid4().hex[:6]}"

        position = {
            "trade_id": trade_id,
            "market_id": discount.market_id,
            "question": discount.question,
            "side": discount.winning_side,
            "entry_price": discount.current_price,
            "size_usdc": size_usdc,
            "shares": shares,
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "status": "OPEN",
            "mode": self.mode,
            "est_discount_pct": discount.settlement_discount_pct,
            "est_apy_pct": discount.annualized_apy_pct,
        }

        # Deduct capital from cash balance
        self.balance_usdc -= size_usdc
        self.active_positions.append(position)
        self._save_state()

        logger.info("🚀 [%s] ENTERED POSITION: %s | Side: %s | Size: $%.2f (%.1f shares @ $%.3f) | Est APY: %.1f%%",
                    self.mode.upper(), discount.question[:45], discount.winning_side,
                    size_usdc, shares, discount.current_price, discount.annualized_apy_pct)
        return position

    def check_resolutions(self) -> list[dict[str, Any]]:
        """Checks open positions against current market states to settle winners."""
        resolved: list[dict[str, Any]] = []
        still_active: list[dict[str, Any]] = []

        # Fetch latest prices for active markets
        markets = self.gamma_client.get_markets(limit=75)
        market_by_id = {m.id: m for m in markets}

        for pos in self.active_positions:
            m = market_by_id.get(pos["market_id"])
            should_settle = False
            settle_price = 1.0

            if m:
                outcome_dict = {o.name: o.price for o in m.outcomes}
                current_p = outcome_dict.get(pos["side"], pos["entry_price"])
                if current_p >= 0.995:
                    should_settle = True
                    settle_price = 1.0
            else:
                # If market no longer appears in active list, assume resolved
                should_settle = True
                settle_price = 1.0

            if should_settle:
                gross_proceeds = pos["shares"] * settle_price
                fee_deduction = gross_proceeds * (self.fee_buffer_pct / 100.0)
                net_proceeds = round(gross_proceeds - fee_deduction, 2)
                pnl = round(net_proceeds - pos["size_usdc"], 2)

                self.balance_usdc += net_proceeds

                pos["status"] = "RESOLVED_WIN" if pnl >= 0 else "RESOLVED_LOSS"
                pos["closed_at"] = datetime.now(timezone.utc).isoformat()
                pos["net_proceeds_usdc"] = net_proceeds
                pos["pnl_usdc"] = pnl

                self.trade_history.append(pos)
                resolved.append(pos)
                logger.info("✅ [%s] SETTLED TRADE: %s | PnL: %+$%.2f (Proceeds: $%.2f)",
                            self.mode.upper(), pos["question"][:40], pnl, net_proceeds)
            else:
                still_active.append(pos)

        if resolved:
            self.active_positions = still_active
            self._save_state()

        return resolved

    def run_cycle(self) -> dict[str, Any]:
        """Runs a single complete scanning, settling, and execution iteration."""
        logger.info("--- Starting PolyArb Trading Cycle [%s] ---", self.mode.upper())
        resolved = self.check_resolutions()

        opportunities = self.scan_opportunities()
        logger.info("Found %d qualified low-risk discount opportunities.", len(opportunities))

        new_positions = []
        for opp in opportunities:
            pos = self.execute_buy(opp)
            if pos:
                new_positions.append(pos)

        self._save_state()
        summary = self.get_summary()
        return {
            "cycle_timestamp": datetime.now(timezone.utc).isoformat(),
            "resolved_count": len(resolved),
            "new_positions_count": len(new_positions),
            "active_positions_count": len(self.active_positions),
            "current_balance_usdc": summary["current_balance_usdc"],
            "total_pnl_usdc": summary["total_pnl_usdc"],
            "roi_pct": summary["roi_pct"],
        }

    def run_daemon(self, interval_seconds: int = 30, max_cycles: Optional[int] = None):
        """Continuously runs the trading loop at specified interval."""
        logger.info("🦅 PolyArb Autonomous Trader started in %s mode (Interval: %ds)",
                    self.mode.upper(), interval_seconds)
        cycle_count = 0
        try:
            while True:
                cycle_count += 1
                cycle_result = self.run_cycle()
                logger.info("Cycle %d done: Balance $%.2f | PnL %+$%.2f | Open Positions: %d",
                            cycle_count, cycle_result["current_balance_usdc"],
                            cycle_result["total_pnl_usdc"], cycle_result["active_positions_count"])

                if max_cycles and cycle_count >= max_cycles:
                    break

                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Autonomous Trader stopped gracefully by user.")

    def get_summary(self) -> dict[str, Any]:
        """Returns comprehensive performance metrics and active inventory."""
        wins = [t for t in self.trade_history if t.get('pnl_usdc', 0) > 0]
        losses = [t for t in self.trade_history if t.get('pnl_usdc', 0) < 0]
        realized_pnl = round(sum(t.get('pnl_usdc', 0) for t in self.trade_history), 2)

        invested_usdc = round(sum(p.get('size_usdc', 0) for p in self.active_positions), 2)
        est_unrealized_pnl = round(
            sum(
                (p.get('shares', 0) * 1.0 * (1.0 - self.fee_buffer_pct / 100.0)) - p.get('size_usdc', 0)
                for p in self.active_positions
            ),
            2
        )
        total_equity = round(self.balance_usdc + invested_usdc + est_unrealized_pnl, 2)
        total_roi_pct = round(((total_equity - self.starting_balance) / self.starting_balance) * 100.0, 2) if self.starting_balance > 0 else 0.0
        win_rate = round(len(wins) / len(self.trade_history) * 100.0, 1) if self.trade_history else 0.0

        return {
            'mode': self.mode,
            'starting_balance_usdc': self.starting_balance,
            'cash_balance_usdc': round(self.balance_usdc, 2),
            'current_balance_usdc': round(self.balance_usdc, 2),
            'invested_usdc': invested_usdc,
            'est_unrealized_pnl_usdc': est_unrealized_pnl,
            'total_portfolio_equity_usdc': total_equity,
            'realized_pnl_usdc': realized_pnl,
            'total_pnl_usdc': round(realized_pnl + est_unrealized_pnl, 2),
            'roi_pct': total_roi_pct,
            'active_positions_count': len(self.active_positions),
            'active_positions': self.active_positions,
            'total_completed_trades': len(self.trade_history),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate_pct': win_rate,
            'recent_trades': self.trade_history[-10:],
        }
