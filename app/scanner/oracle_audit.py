"""
UMA Optimistic Oracle Dispute Risk Auditor.
Analyzes market resolution criteria for semantic ambiguity and challenge bond levels.
"""
from typing import Any

from app.core.models import Market


class OracleAuditor:
    """Evaluates UMA dispute and semantic ambiguity risks for a market."""

    RISK_KEYWORDS = [
        "subject to", "sole discretion", "unclear", "unofficial",
        "postponed", "cancelled", "tweet", "social media", "approximate"
    ]

    def audit_market(self, market: Market) -> dict[str, Any]:
        """Audits a market's resolution parameters and text rules."""
        question_lower = market.question.lower()
        matched_flags = [kw for kw in self.RISK_KEYWORDS if kw in question_lower]

        has_source = bool(market.resolution_source and market.resolution_source.startswith("http"))
        risk_level = "LOW"
        if matched_flags:
            risk_level = "HIGH" if len(matched_flags) >= 2 else "MEDIUM"
        elif not has_source:
            risk_level = "MEDIUM"

        return {
            "market_id": market.id,
            "question": market.question,
            "risk_level": risk_level,
            "matched_risk_keywords": matched_flags,
            "has_official_resolution_source": has_source,
            "resolution_source": market.resolution_source,
            "uma_bond": market.uma_bond
        }

    def audit_all(self, markets: list[Market]) -> list[dict[str, Any]]:
        """Audits all markets and returns flagged higher-risk markets."""
        audits = [self.audit_market(m) for m in markets]
        return [a for a in audits if a["risk_level"] in ("MEDIUM", "HIGH")]
