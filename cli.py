"""
Interactive Command-Line Interface for PolyArb.
"""
import argparse

try:
    from tabulate import tabulate
except ImportError:
    def tabulate(rows, headers, **kwargs):
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, val in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(val)))
        header_line = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
        sep_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
        row_lines = [
            " | ".join(f"{str(val):<{col_widths[i]}}" for i, val in enumerate(row))
            for row in rows
        ]
        return f"{header_line}\n{sep_line}\n" + "\n".join(row_lines)

from app.ingestor.gamma_client import GammaClient
from app.research.dossier_generator import DossierGenerator
from app.research.quant_researcher import QuantResearcher
from app.scanner.negative_risk import NegativeRiskScanner
from app.scanner.resolution_lag import ResolutionLagScanner
from app.simulation.paper_trader import PaperTrader


def cmd_scan():
    print("\n🔍 Scanning Polymarket live markets...")
    gamma = GammaClient()
    events = gamma.get_events(limit=50)
    markets = gamma.get_markets(limit=70)

    neg_scanner = NegativeRiskScanner()
    res_scanner = ResolutionLagScanner()

    neg_opps = neg_scanner.scan_all(events)
    res_discounts = res_scanner.scan_all(markets)

    print(f"\n📊 Evaluated {len(events)} Events and {len(markets)} Markets.")

    if neg_opps:
        print("\n⚡ Combinatorial / Negative-Risk Arbitrage (∑P ≠ 1.00):")
        table = []
        for o in neg_opps[:8]:
            table.append([o.event_title[:40], o.outcomes_count, f"${o.sum_of_prices}", f"{o.spread_pct:+}%", f"+{o.net_profit_pct}%", o.strategy_type])
        print(tabulate(table, headers=["Event", "Outcomes", "Sum YES", "Spread", "Net Profit", "Strategy"], tablefmt="fancy_grid"))
    else:
        print("\n⚡ Negative-Risk: No multi-outcome markets currently exceed 1.5% net profit threshold.")

    if res_discounts:
        print("\n⏳ Resolution Lag Settlement Discounts (Decided Markets):")
        table = []
        for d in res_discounts[:8]:
            table.append([d.question[:40], d.winning_side, f"${d.current_price}", f"{d.settlement_discount_pct}%", f"{d.annualized_apy_pct}%", f"${d.volume_24h:,.0f}"])
        print(tabulate(table, headers=["Market", "Side", "Price", "Discount", "Est. APY", "24h Vol"], tablefmt="fancy_grid"))
    else:
        print("\n⏳ Resolution Lag: No high-probability tokens currently trading at target discount.")


def cmd_research(topic: str):
    print(f"\n🔬 Running Quant Research Investigation: '{topic}'...")
    researcher = QuantResearcher()
    generator = DossierGenerator()

    data = researcher.run_investigation(topic)
    report_md = generator.compile_markdown(data)

    print("\n" + "="*70)
    print(report_md[:2000])
    print("\n... (truncated for console output) ...")
    print("="*70)

    # Save Markdown
    with open("polyarb_research_report.md", "w") as f:
        f.write(report_md)
    print("📝 Saved full Markdown report to: polyarb_research_report.md")

    # Generate PDF
    pdf_bytes = generator.generate_pdf(report_md)
    if pdf_bytes:
        with open("polyarb_research_report.pdf", "wb") as f:
            f.write(pdf_bytes)
        print(f"📄 Generated publication-grade PDF dossier: polyarb_research_report.pdf ({len(pdf_bytes)/1024:.1f} KB)")


def cmd_paper():
    trader = PaperTrader()
    summary = trader.get_summary()
    print("\n📈 PolyArb Paper Trading Summary:")
    print(f"• Current Balance: ${summary['current_balance_usdc']:,.2f} USDC")
    print(f"• Realized PnL:    ${summary['total_pnl_usdc']:+,.2f}")
    print(f"• ROI:             {summary['roi_pct']:+}%")
    print(f"• Total Trades:    {summary['total_trades']} (Win Rate: {summary['win_rate_pct']}%)")


def main():
    parser = argparse.ArgumentParser(description="PolyArb: Polymarket Quant Scanner & Intelligence Bot")
    parser.add_argument("--scan", action="store_true", help="Run live arbitrage scan")
    parser.add_argument("--research", type=str, nargs="?", const="polymarket arbitrage loopholes", help="Generate quant research dossier")
    parser.add_argument("--paper", action="store_true", help="View paper trading summary")
    parser.add_argument("--server", action="store_true", help="Start Web Dashboard & REST API server")
    parser.add_argument("--daemon", action="store_true", help="Start Telegram Bot daemon")

    args = parser.parse_args()

    if args.scan:
        cmd_scan()
    elif args.research is not None:
        cmd_research(args.research)
    elif args.paper:
        cmd_paper()
    elif args.server:
        from app.api.server import PORT, app
        print(f"🚀 Starting PolyArb Dashboard on port {PORT}...")
        app.run(host="0.0.0.0", port=PORT)
    elif args.daemon:
        from app.bot.telegram_daemon import PolyArbTelegramDaemon
        daemon = PolyArbTelegramDaemon()
        daemon.poll_forever()
    else:
        cmd_scan()


if __name__ == "__main__":
    main()
