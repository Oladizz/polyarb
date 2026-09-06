"""
Liquidity Mining & Merkl Reward Scanner.
Finds markets with active daily USDC reward pools and calculates optimal spread quoting.
"""

from app.core.config import MIN_VOLUME_USD
from app.core.models import Market, RewardMarket


class MakerRewardScanner:
    """Scans for markets qualifying for daily Polymarket maker reward incentives."""

    def __init__(self, min_volume: float = MIN_VOLUME_USD * 2):
        self.min_volume = min_volume

    def scan_market(self, market: Market) -> list[RewardMarket]:
        """Checks if a market has active liquidity reward parameters."""
        if market.rewards_max_spread > 0 and market.volume_24h >= self.min_volume:
            return [RewardMarket(
                market_id=market.id,
                question=market.question,
                rewards_max_spread=market.rewards_max_spread,
                rewards_min_size=market.rewards_min_size,
                current_spread=market.spread,
                volume_24h=market.volume_24h
            )]
        return []

    def scan_all(self, markets: list[Market]) -> list[RewardMarket]:
        """Ranks rewarded markets by volume and reward spread."""
        reward_markets = []
        for m in markets:
            reward_markets.extend(self.scan_market(m))
        reward_markets.sort(key=lambda x: x.volume_24h, reverse=True)
        return reward_markets
