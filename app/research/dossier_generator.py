"""
Dossier and PDF Generator for PolyArb Intelligence Reports.
"""
import time
from typing import Any


class DossierGenerator:
    """Compiles research results into structured Markdown and styled PDF documents."""

    def compile_markdown(self, data: dict[str, Any]) -> str:
        """Generates a detailed Markdown report."""
        topic = data.get("topic", "Polymarket Intelligence")
        neg_opps = data.get("negative_risk_opportunities", [])
        res_discounts = data.get("resolution_lag_opportunities", [])
        reward_markets = data.get("reward_markets", [])
        strategies = data.get("strategies", [])
        sources = data.get("web_sources", [])

        lines = [
            "# 🦅 PolyArb: Polymarket Quant Intelligence Dossier",
            f"**Topic:** `{topic}`  ",
            f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}  ",
            "**Engine:** PolyArb Quant Analyzer & Research Engine  \n",
            "---",
            "## 1. Executive Summary: What Actually Works",
            "Polymarket is a hybrid prediction market: an off-chain Central Limit Order Book (CLOB) ",
            "settled on Polygon using Gnosis Conditional Tokens (ERC-1155) and resolved by UMA's Optimistic Oracle.\n",
            "### The 3 Realistic Avenues to Profitability:",
            "1. **Resolution Lag Discounting:** Buying winning shares at 98.0¢–99.0¢ from retail traders seeking instant liquidity.",
            "2. **Liquidity Mining / Maker Rebates:** Collecting daily USDC rewards from Merkl by quoting tight bid/ask spreads.",
            "3. **Negative-Risk Combinatorial Arbitrage:** Exploiting multi-outcome pricing discrepancies when $\\sum P_{YES} \\neq 1.00$.\n",
            "---",
            "## 2. Live Market Telemetry (Real-Time Scan)",
            f"• **Events Evaluated:** {data.get('events_scanned', 0)}  ",
            f"• **Markets Evaluated:** {data.get('markets_scanned', 0)}  \n"
        ]

        # Negative Risk
        lines.append("### ⚡ Live Combinatorial / Negative-Risk Opportunities:")
        if neg_opps:
            for opp in neg_opps[:3]:
                lines.append(f"- **{opp.event_title}** ({opp.outcomes_count} outcomes)")
                lines.append(f"  - Sum of YES Prices: **${opp.sum_of_prices}** (Spread: **{opp.spread_pct}%**)")
                lines.append(f"  - Action: `{opp.strategy_type}` | Net Est. Profit: **{opp.net_profit_pct}%**")
        else:
            lines.append("No active multi-outcome markets currently exceed the 1.5% net arbitrage threshold.\n")

        # Resolution Lag
        lines.append("\n### ⏳ Top Resolution Lag Discount Opportunities (Decided Markets):")
        if res_discounts:
            for d in res_discounts[:4]:
                lines.append(f"- **{d.question}**")
                lines.append(f"  - Price: **${d.current_price}** ({d.winning_side}) | Discount: **{d.settlement_discount_pct}%** | Est. APY: **{d.annualized_apy_pct}%**")
                lines.append(f"  - 24h Volume: ${d.volume_24h:,.0f}")
        else:
            lines.append("No high-certainty (>97.5%) markets currently trading at actionable discounts.\n")

        # Liquidity Rewards
        lines.append("\n### 💰 Active Liquidity Mining Pools:")
        if reward_markets:
            for r in reward_markets[:4]:
                lines.append(f"- **{r.question}**")
                lines.append(f"  - Max Spread: `{r.rewards_max_spread}` | 24h Volume: ${r.volume_24h:,.0f}")
        else:
            lines.append("No active reward pools with spread incentives found.\n")

        # Strategies
        lines.extend([
            "---",
            "## 3. Strategy Feasibility Matrix",
            "| Strategy | Viability | Required Capital | Speed Requirement | Primary Risk |",
            "|---|---|---|---|---|"
        ])
        for s in strategies:
            lines.append(f"| **{s['name']}** | {s['viability']} | {s['capital']} | {s['speed_requirement']} | {s['risk']} |")

        # Solo Developer Blueprint
        lines.extend([
            "\n---",
            "## 4. The Recommended Solo-Developer Blueprint",
            "1. **Never trade real capital without paper-trading first.** Test fill rates, slippage, and adverse selection.",
            "2. **Start with Resolution Lag Harvesting:** Requires no expensive low-latency servers and has the lowest adverse selection.",
            "3. **Combine with Merkl Liquidity Rewards:** Keep neutral inventory on low-volatility pairs to earn passive yield.\n",
            "---",
            "## 5. Verified Quant Resources & Repositories"
        ])
        for src in sources:
            lines.append(f"- [{src}]({src})")

        return "\n".join(lines)

    def generate_pdf(self, markdown_text: str) -> bytes | None:
        """Converts Markdown report to publication-quality PDF bytes via WeasyPrint."""
        try:
            import markdown
            import weasyprint

            html_body = markdown.markdown(markdown_text, extensions=['tables', 'fenced_code'])
            full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>PolyArb Quant Dossier</title>
<style>
    @page {{
        margin: 18mm;
        size: A4;
        @bottom-right {{ content: "Page " counter(page) " of " counter(pages); font-size: 8pt; color: #64748b; }}
    }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.5; color: #0f172a; }}
    h1 {{ color: #0d9488; border-bottom: 2px solid #14b8a6; padding-bottom: 6px; font-size: 20pt; }}
    h2 {{ color: #0f766e; margin-top: 18px; border-bottom: 1px solid #e2e8f0; font-size: 13.5pt; }}
    h3 {{ color: #1e293b; margin-top: 12px; font-size: 11pt; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 9pt; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 6px 8px; text-align: left; }}
    th {{ background: #f1f5f9; font-weight: 600; }}
    code {{ background: #f8fafc; padding: 2px 4px; border-radius: 4px; font-size: 8.5pt; }}
    hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 14px 0; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
            return weasyprint.HTML(string=full_html).write_pdf()
        except Exception as e:
            print(f"DossierGenerator PDF error: {e}")
            return None
