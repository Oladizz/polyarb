"""
Resolution Lag & Settlement Discount Scanner.
Finds markets with >97.5% certainty trading at a discount prior to UMA settlement.
"""

from app.core.config import (
    MAX_RESOLUTION_PROBABILITY,
    MIN_RESOLUTION_PROBABILITY,
    MIN_VOLUME_USD,
)
from app.core.models import Market, ResolutionDiscount


class ResolutionLagScanner:
    """Scans for markets nearing resolution trading at a mathematical discount."""

    def __init__(
        self,
        min_prob: float = MIN_RESOLUTION_PROBABILITY,
        max_prob: float = MAX_RESOLUTION_PROBABILITY,
        min_volume: float = MIN_VOLUME_USD
    ):
        self.min_prob = min_prob
        self.max_prob = max_prob
        self.min_volume = min_volume

    def scan_market(self, market: Market) -> list[ResolutionDiscount]:
        """Evaluates a single market for resolution lag discounting."""
        discounts = []
        if market.volume_24h < self.min_volume or not market.outcomes:
            return discounts

        for outcome in market.outcomes:
            price = outcome.price
            if self.min_prob <= price <= self.max_prob:
                discount_pct = (1.0 - price) * 100.0
                # Assuming typical 24-48h UMA settlement window (average 36 hours = 1.5 days)
                # Annualized APY = (discount% / 1.5 days) * 365
                annualized_apy = (discount_pct / 1.5) * 365.0

                discounts.append(ResolutionDiscount(
                    market_id=market.id,
                    question=market.question,
                    winning_side=outcome.name,
                    current_price=round(price, 4),
                    settlement_discount_pct=round(discount_pct, 2),
                    annualized_apy_pct=round(annualized_apy, 1),
                    end_date=market.end_date,
                    volume_24h=market.volume_24h,
                    uma_bond=market.uma_bond
                ))

        return discounts

    def scan_all(self, markets: list[Market]) -> list[ResolutionDiscount]:
        """Scans all markets and ranks opportunities by settlement discount percentage."""
        all_discounts = []
        for m in markets:
            all_discounts.extend(self.scan_market(m))
        all_discounts.sort(key=lambda x: x.settlement_discount_pct, reverse=True)
        return all_discounts
