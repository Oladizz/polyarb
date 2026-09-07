"""
Negative-Risk & Combinatorial Arbitrage Scanner for Multi-Outcome Polymarket Events.
"""

from app.core.config import ESTIMATED_FEE_SLIPPAGE_PCT, MIN_ARBITRAGE_SPREAD_PCT
from app.core.models import ArbitrageOpportunity, Event


class NegativeRiskScanner:
    """Detects combinatorial mispricings where the sum of outcome prices deviates from 1.00."""

    def __init__(
        self,
        min_spread_pct: float = MIN_ARBITRAGE_SPREAD_PCT,
        slippage_buffer_pct: float = ESTIMATED_FEE_SLIPPAGE_PCT
    ):
        self.min_spread_pct = min_spread_pct
        self.slippage_buffer_pct = slippage_buffer_pct

    def scan_event(self, event: Event) -> list[ArbitrageOpportunity]:
        """Analyzes an event with 2+ markets for pricing discrepancies."""
        opportunities = []
        if len(event.markets) < 2:
            return opportunities
        # Strict check: events with >2 markets must be true NegRisk adapter markets
        if len(event.markets) > 2 and not event.neg_risk:
            return opportunities

        # Collect YES price for each mutually exclusive outcome
        outcome_data = []
        sum_prices = 0.0

        for m in event.markets:
            if not m.outcomes or len(m.outcomes) == 0:
                continue
            yes_outcome = m.outcomes[0]
            price = yes_outcome.price
            if price > 0:
                sum_prices += price
                outcome_data.append({
                    "market_id": m.id,
                    "question": m.question,
                    "outcome_name": yes_outcome.name,
                    "price": price,
                    "token_id": yes_outcome.token_id,
                    "volume_24h": m.volume_24h
                })

        if len(outcome_data) < 2 or sum_prices <= 0:
            return opportunities

        # Calculate deviation from 1.00
        spread_pct = (sum_prices - 1.0) * 100.0

        # Check for underpriced basket (Sum < 1.00) -> Buy all outcomes
        if spread_pct <= -self.min_spread_pct:
            gross_profit = abs(spread_pct)
            net_profit = max(0.0, gross_profit - self.slippage_buffer_pct)
            if net_profit > 0:
                opportunities.append(ArbitrageOpportunity(
                    event_id=event.id,
                    event_title=event.title,
                    strategy_type="MINT_DISCOUNT",
                    outcomes_count=len(outcome_data),
                    sum_of_prices=round(sum_prices, 4),
                    spread_pct=round(spread_pct, 2),
                    net_profit_pct=round(net_profit, 2),
                    target_outcomes=outcome_data
                ))

        # Check for overpriced basket (Sum > 1.00) -> Mint complete set, sell all
        elif spread_pct >= self.min_spread_pct:
            gross_profit = spread_pct
            net_profit = max(0.0, gross_profit - self.slippage_buffer_pct)
            if net_profit > 0:
                opportunities.append(ArbitrageOpportunity(
                    event_id=event.id,
                    event_title=event.title,
                    strategy_type="OVERPRICED_BASKET",
                    outcomes_count=len(outcome_data),
                    sum_of_prices=round(sum_prices, 4),
                    spread_pct=round(spread_pct, 2),
                    net_profit_pct=round(net_profit, 2),
                    target_outcomes=outcome_data
                ))

        return opportunities

    def scan_all(self, events: list[Event]) -> list[ArbitrageOpportunity]:
        """Scans a batch of events and returns sorted opportunities by net profit."""
        all_opps = []
        for ev in events:
            opps = self.scan_event(ev)
            all_opps.extend(opps)
        all_opps.sort(key=lambda x: x.net_profit_pct, reverse=True)
        return all_opps
