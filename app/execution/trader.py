"""
Autonomous Quant Execution Engine for PolyArb (Strict Real-Life Experience).
Features authentic microstructure modeling:
1. Dynamic capital allocation (max 20-25% per market).
2. Minimum order threshold enforcement ($5.00 CLOB floor).
3. Realistic order book slippage scaled by trade size vs 24h volume.
4. On-chain Polygon gas fee deductions ($0.025 entry, $0.025 exit).
5. Protocol taker fee deductions (0.2%).
6. UMA Optimistic Oracle 24h dispute time-lock (no premature instant settlement).
7. UMA challenge dispute simulation for ambiguous markets.
"""
import json
import logging
import os
import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from app.core.config import (
    MAX_POSITION_SIZE_USDC,
    MIN_POSITION_SIZE_USDC,
    MIN_UMA_LIVENESS_HOURS,
    MIN_VOLUME_USD,
    PAPER_STARTING_BALANCE_USDC,
    PROTOCOL_TAKER_FEE_PCT,
    SIMULATED_POLYGON_GAS_USDC,
)
from app.core.models import ResolutionDiscount
from app.ingestor.gamma_client import GammaClient
from app.scanner.oracle_audit import OracleAuditor
from app.scanner.resolution_lag import ResolutionLagScanner

logger = logging.getLogger("polyarb.trader")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class AutonomousTrader:
    """Strict real-life autonomous execution engine."""

    def __init__(
        self,
        mode: str = "paper",
        data_dir: str = "data",
        starting_balance: float = PAPER_STARTING_BALANCE_USDC,
        max_position_size: float = MAX_POSITION_SIZE_USDC,
        min_position_size: float = MIN_POSITION_SIZE_USDC,
        max_active_positions: int = 5,
        min_discount_pct: float = 1.0,
        min_volume_usd: float = MIN_VOLUME_USD,
        gas_fee_usdc: float = SIMULATED_POLYGON_GAS_USDC,
        protocol_fee_pct: float = PROTOCOL_TAKER_FEE_PCT,
        min_liveness_hours: float = MIN_UMA_LIVENESS_HOURS,
    ):
        self.mode = mode.lower()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data_dir / "portfolio.json"

        self.starting_balance = starting_balance
        self.balance_usdc = starting_balance
        self.max_position_size = max_position_size
        self.min_position_size = min_position_size
        self.max_active_positions = max_active_positions
        self.min_discount_pct = min_discount_pct
        self.min_volume_usd = min_volume_usd
        self.gas_fee_usdc = gas_fee_usdc
        self.protocol_fee_pct = protocol_fee_pct
        self.min_liveness_hours = min_liveness_hours

        self.total_gas_spent_usdc: float = 0.0
        self.active_positions: list[dict[str, Any]] = []
        self.trade_history: list[dict[str, Any]] = []

        self.gamma_client = GammaClient()
        self.scanner = ResolutionLagScanner(min_volume=self.min_volume_usd)
        self.oracle_auditor = OracleAuditor()

        self._load_state()

    def reset_portfolio(self, new_balance: float = 100.0):
        """Resets portfolio state to a fresh balance for clean realistic testing."""
        self.starting_balance = new_balance
        self.balance_usdc = new_balance
        self.total_gas_spent_usdc = 0.0
        self.active_positions = []
        self.trade_history = []
        self._save_state()
        logger.info("Portfolio reset to strict real-life starting balance: $%.2f USDC", new_balance)

    def _load_state(self):
        """Loads persistent portfolio and history from disk if exists."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.balance_usdc = float(data.get("cash_balance_usdc", data.get("balance_usdc", self.starting_balance)))
                    self.starting_balance = float(data.get("starting_balance", self.starting_balance))
                    self.total_gas_spent_usdc = float(data.get("total_gas_spent_usdc", 0.0))
                    self.active_positions = data.get("active_positions", [])
                    self.trade_history = data.get("trade_history", [])
                logger.info("Loaded portfolio: $%.2f cash | $%.2f invested (%d active) | $%.2f gas paid",
                            self.balance_usdc, sum(p.get("size_usdc", 0) for p in self.active_positions),
                            len(self.active_positions), self.total_gas_spent_usdc)
            except Exception as e:
                logger.error("Failed to load portfolio state: %s", e)

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
            "total_gas_spent_usdc": round(self.total_gas_spent_usdc, 4),
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
        """Executes a buy order with strict real-world slippage, gas, and sizing."""
        existing_ids = {p["market_id"] for p in self.active_positions}
        if discount.market_id in existing_ids:
            return None

        if len(self.active_positions) >= self.max_active_positions:
            return None

        # 1. Real-life position sizing: max 25% of current equity or max_position_size
        total_equity = self.balance_usdc + sum(p.get("size_usdc", 0) for p in self.active_positions)
        target_size = min(self.max_position_size, round(total_equity * 0.25, 2))
        size_usdc = round(min(target_size, max(0.0, self.balance_usdc - self.gas_fee_usdc)), 2)

        # 2. Strict minimum order check ($5.00 Polymarket CLOB requirement)
        if size_usdc < self.min_position_size:
            logger.info("Skipping trade: available cash ($%.2f) below minimum order size ($%.2f)",
                        self.balance_usdc, self.min_position_size)
            return None

        # 3. Realistic order book slippage based on trade size vs 24h volume
        slippage_rate = max(0.001, min(0.012, (size_usdc / max(discount.volume_24h, 2000.0)) * 0.1))
        effective_fill_price = round(min(0.994, discount.current_price * (1.0 + slippage_rate)), 4)

        # If slippage eliminates the edge (< 0.5% discount), abort
        if (1.0 - effective_fill_price) * 100.0 < 0.5:
            logger.info("Skipping market '%s': slippage reduced discount below threshold.", discount.question[:35])
            return None

        shares = round(size_usdc / effective_fill_price, 2)
        trade_id = f"pos_{uuid.uuid4().hex[:6]}"
        now = datetime.now(timezone.utc)

        # 4. Strict UMA settlement time-lock (24 hours minimum liveness window)
        min_settle_after = (now + timedelta(hours=self.min_liveness_hours)).isoformat()

        # 5. Check if market has medium risk for possible dispute simulation
        market_audit = {}
        if hasattr(self, "oracle_auditor"):
            target_market = next((m for m in self.gamma_client.get_markets(limit=75) if m.id == discount.market_id), None)
            if target_market:
                market_audit = self.oracle_auditor.audit_market(target_market)
        is_disputed = False
        if market_audit and market_audit.get("risk_level") == "MEDIUM":
            # 5% chance of real-world UMA challenge delay (adding 5 days)
            if random.random() < 0.05:
                is_disputed = True
                min_settle_after = (now + timedelta(hours=self.min_liveness_hours + 120)).isoformat()
                logger.warning("⚠️ Market '%s' encountered an simulated UMA challenge! Dispute delay: +120h", discount.question[:35])

        position = {
            "trade_id": trade_id,
            "market_id": discount.market_id,
            "question": discount.question,
            "side": discount.winning_side,
            "quoted_price": discount.current_price,
            "entry_price": effective_fill_price,
            "slippage_paid_pct": round(slippage_rate * 100.0, 2),
            "size_usdc": size_usdc,
            "shares": shares,
            "entry_gas_usdc": self.gas_fee_usdc,
            "opened_at": now.isoformat(),
            "min_settle_after": min_settle_after,
            "is_disputed": is_disputed,
            "status": "LOCKED_IN_DISPUTE_WINDOW",
            "mode": self.mode,
            "est_discount_pct": round((1.0 - effective_fill_price) * 100.0, 2),
            "est_apy_pct": discount.annualized_apy_pct,
        }

        # Deduct capital and entry gas fee from cash balance
        self.balance_usdc = round(max(0.0, self.balance_usdc - size_usdc - self.gas_fee_usdc), 2)
        self.total_gas_spent_usdc = round(self.total_gas_spent_usdc + self.gas_fee_usdc, 4)
        self.active_positions.append(position)
        self._save_state()

        logger.info("🚀 [%s] BOUGHT: %s | Size: $%.2f (%.1f shares @ $%.3f, slip: %.2f%%) | Gas: -$%.3f | Settle after: %s",
                    self.mode.upper(), discount.question[:35], size_usdc, shares,
                    effective_fill_price, position["slippage_paid_pct"], self.gas_fee_usdc, min_settle_after[:16])
        return position

    def check_resolutions(self) -> list[dict[str, Any]]:
        """Settles positions only when the strict real-world UMA liveness window has elapsed."""
        resolved: list[dict[str, Any]] = []
        still_active: list[dict[str, Any]] = []

        markets = self.gamma_client.get_markets(limit=75)
        market_by_id = {m.id: m for m in markets}
        now = datetime.now(timezone.utc)

        for pos in self.active_positions:
            m = market_by_id.get(pos["market_id"])
            min_settle_time = datetime.fromisoformat(pos["min_settle_after"])
            liveness_expired = now >= min_settle_time

            # In real life, funds CANNOT be redeemed before the oracle liveness window passes
            should_settle = False
            settle_price = 1.0

            if m:
                outcome_dict = {o.name: o.price for o in m.outcomes}
                current_p = outcome_dict.get(pos["side"], pos["entry_price"])
                # If market trading at 1.0 or closed AND liveness window has expired
                if (current_p >= 0.995 or getattr(m, "closed", False)) and liveness_expired:
                    should_settle = True
            elif liveness_expired:
                # Market concluded and removed from active list + liveness passed
                should_settle = True

            if should_settle:
                gross_proceeds = pos["shares"] * settle_price
                protocol_fee = gross_proceeds * (self.protocol_fee_pct / 100.0)
                exit_gas = self.gas_fee_usdc
                net_proceeds = round(gross_proceeds - protocol_fee - exit_gas, 2)
                pnl = round(net_proceeds - pos["size_usdc"] - pos.get("entry_gas_usdc", 0.0), 2)

                self.balance_usdc = round(self.balance_usdc + net_proceeds, 2)
                self.total_gas_spent_usdc = round(self.total_gas_spent_usdc + exit_gas, 4)

                pos["status"] = "RESOLVED_WIN" if pnl >= 0 else "RESOLVED_LOSS"
                pos["closed_at"] = now.isoformat()
                pos["exit_gas_usdc"] = exit_gas
                pos["protocol_fee_usdc"] = round(protocol_fee, 4)
                pos["net_proceeds_usdc"] = net_proceeds
                pos["pnl_usdc"] = pnl

                self.trade_history.append(pos)
                resolved.append(pos)
                logger.info("✅ [%s] SETTLED: %s | Net PnL: +$%.2f (Gross: $%.2f, Fee: -$%.2f, Gas: -$%.3f)",
                            self.mode.upper(), pos["question"][:35], pnl, gross_proceeds, protocol_fee, exit_gas)
            else:
                # Update status label for UI
                if not liveness_expired:
                    hours_remaining = round((min_settle_time - now).total_seconds() / 3600.0, 1)
                    pos["status"] = f"LOCKED_UMA_LIVENESS ({hours_remaining}h left)"
                still_active.append(pos)

        if resolved:
            self.active_positions = still_active
            self._save_state()

        return resolved

    def run_cycle(self) -> dict[str, Any]:
        """Runs a complete scanning, settling, and execution iteration."""
        logger.info("--- Starting PolyArb Cycle [%s] (Real-Life Engine) ---", self.mode.upper())
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
            "cash_balance_usdc": summary["cash_balance_usdc"],
            "current_balance_usdc": summary["cash_balance_usdc"],
            "total_gas_spent_usdc": summary["total_gas_spent_usdc"],
            "total_pnl_usdc": summary["total_pnl_usdc"],
            "roi_pct": summary["roi_pct"],
        }

    def run_daemon(self, interval_seconds: int = 30, max_cycles: Optional[int] = None):
        """Continuously runs the trading loop at specified interval."""
        logger.info("🦅 PolyArb Autonomous Trader started in %s mode (Interval: %ds, Bankroll: $%.2f)",
                    self.mode.upper(), interval_seconds, self.starting_balance)
        cycle_count = 0
        try:
            while True:
                cycle_count += 1
                cycle_result = self.run_cycle()
                logger.info("Cycle %d: Cash $%.2f | Invested $%.2f | PnL +$%.2f | Open: %d",
                            cycle_count, cycle_result["cash_balance_usdc"],
                            sum(p.get("size_usdc", 0) for p in self.active_positions),
                            cycle_result["total_pnl_usdc"], cycle_result["active_positions_count"])

                if max_cycles and cycle_count >= max_cycles:
                    break

                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Autonomous Trader stopped gracefully by user.")

    def get_summary(self) -> dict[str, Any]:
        """Returns institutional-grade portfolio metrics with complete fee/gas breakdown."""
        wins = [t for t in self.trade_history if t.get("pnl_usdc", 0) > 0]
        losses = [t for t in self.trade_history if t.get("pnl_usdc", 0) < 0]
        realized_pnl = round(sum(t.get("pnl_usdc", 0) for t in self.trade_history), 2)

        invested_usdc = round(sum(p.get("size_usdc", 0) for p in self.active_positions), 2)
        est_unrealized_pnl = round(
            sum(
                (p.get("shares", 0) * 1.0 * (1.0 - self.protocol_fee_pct / 100.0) - self.gas_fee_usdc) - p.get("size_usdc", 0) - p.get("entry_gas_usdc", 0.0)
                for p in self.active_positions
            ),
            2
        )
        total_equity = round(self.balance_usdc + invested_usdc + est_unrealized_pnl, 2)
        total_roi_pct = round(((total_equity - self.starting_balance) / self.starting_balance) * 100.0, 2) if self.starting_balance > 0 else 0.0
        win_rate = round(len(wins) / len(self.trade_history) * 100.0, 1) if self.trade_history else 0.0

        return {
            "mode": self.mode,
            "starting_balance_usdc": self.starting_balance,
            "cash_balance_usdc": round(self.balance_usdc, 2),
            "current_balance_usdc": round(self.balance_usdc, 2),
            "invested_usdc": invested_usdc,
            "total_gas_spent_usdc": round(self.total_gas_spent_usdc, 4),
            "est_unrealized_pnl_usdc": est_unrealized_pnl,
            "total_portfolio_equity_usdc": total_equity,
            "realized_pnl_usdc": realized_pnl,
            "total_pnl_usdc": round(realized_pnl + est_unrealized_pnl, 2),
            "roi_pct": total_roi_pct,
            "active_positions_count": len(self.active_positions),
            "active_positions": self.active_positions,
            "total_completed_trades": len(self.trade_history),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate_pct": win_rate,
            "recent_trades": self.trade_history[-10:],
        }
