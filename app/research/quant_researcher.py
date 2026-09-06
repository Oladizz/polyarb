"""
Quant Research Orchestrator for Polymarket mechanics, loopholes, and bot design.
"""
from typing import Any

from app.ingestor.gamma_client import GammaClient
from app.research.search_engine import ResearchSearchEngine
from app.scanner.maker_rewards import MakerRewardScanner
from app.scanner.negative_risk import NegativeRiskScanner
from app.scanner.resolution_lag import ResolutionLagScanner


class QuantResearcher:
    """Orchestrates live telemetry scanning and targeted quant web research."""

    def __init__(self):
        self.search_engine = ResearchSearchEngine()
        self.gamma_client = GammaClient()
        self.neg_risk_scanner = NegativeRiskScanner()
        self.res_lag_scanner = ResolutionLagScanner()
        self.maker_reward_scanner = MakerRewardScanner()

    def run_investigation(self, topic: str = "polymarket arbitrage loopholes") -> dict[str, Any]:
        """Runs an end-to-end investigation combining live market data and web research."""
        # 1. Gather live market data
        events = self.gamma_client.get_events(limit=40)
        markets = self.gamma_client.get_markets(limit=60)

        neg_opps = self.neg_risk_scanner.scan_all(events)
        res_discounts = self.res_lag_scanner.scan_all(markets)
        reward_markets = self.maker_reward_scanner.scan_all(markets)

        # 2. Gather quant web references
        search_queries = [
            f"{topic} Gnosis CTF split merge",
            f"{topic} UMA dispute ambiguity",
            f"{topic} CLOB latency WebSocket",
            f"{topic} market maker Merkl rewards"
        ]

        web_sources = []
        for q in search_queries:
            links = self.search_engine.discover(q, target_count=2)
            web_sources.extend(links)

        # 3. Strategy Feasibility Matrix
        strategies = [
            {
                "name": "Resolution Lag Settlement Discounting",
                "viability": "95%",
                "edge": "Capital Liquidity Provision",
                "capital": "$500 - $5,000",
                "speed_requirement": "Low (Minutes)",
                "how": "Buy decided tokens at 98.0¢–99.0¢ during UMA 24-48h settlement window. Redeem for $1.00.",
                "risk": "UMA Oracle dispute delays (funds locked 5-14 days); anomalous voting outcome."
            },
            {
                "name": "Liquidity Mining / Maker Rewards",
                "viability": "88%",
                "edge": "Treasury Subsidy Extraction",
                "capital": "$1,000 - $10,000",
                "speed_requirement": "Medium (Automated quotes)",
                "how": "Quote tight spreads within rewardsMaxSpread on low-volatility pairs. Collect daily USDC rewards.",
                "risk": "Toxic flow: informed traders picking off resting limit orders during breaking news."
            },
            {
                "name": "Negative-Risk Combinatorial Arbitrage",
                "viability": "75%",
                "edge": "Pure Mathematical Inefficiency",
                "capital": "$2,000 - $20,000",
                "speed_requirement": "High (Milliseconds / MEV)",
                "how": "When sum of YES outcomes != $1.00, mint/merge complete sets on Polygon Gnosis CTF.",
                "risk": "Leg-in slippage if one side fills and another moves."
            },
            {
                "name": "UMA Oracle Ambiguity Arbitrage",
                "viability": "60%",
                "edge": "Semantic / Legal Rule Discrepancy",
                "capital": "Variable ($500+ for bonds)",
                "speed_requirement": "Low (Careful rule reading)",
                "how": "Exploiting literal wording in market descriptions that conflicts with popular sentiment, disputing via UMA bond.",
                "risk": "Voter consensus can be unpredictable or subjective; loss of challenge bond."
            }
        ]

        return {
            "topic": topic,
            "events_scanned": len(events),
            "markets_scanned": len(markets),
            "negative_risk_opportunities": neg_opps,
            "resolution_lag_opportunities": res_discounts,
            "reward_markets": reward_markets,
            "strategies": strategies,
            "web_sources": list(set(web_sources))
        }
