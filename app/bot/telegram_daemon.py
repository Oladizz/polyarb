"""
Interactive Telegram Bot Daemon for PolyArb.
Provides live scans, paper trade management, and direct PDF quant dossier delivery.
"""
import time

import requests

from app.core.config import TELEGRAM_BOT_TOKEN
from app.ingestor.gamma_client import GammaClient
from app.research.dossier_generator import DossierGenerator
from app.research.quant_researcher import QuantResearcher
from app.scanner.maker_rewards import MakerRewardScanner
from app.scanner.negative_risk import NegativeRiskScanner
from app.scanner.resolution_lag import ResolutionLagScanner
from app.simulation.paper_trader import PaperTrader


class PolyArbTelegramDaemon:
    """Telegram Bot Daemon for PolyArb alerts, scans, and research."""

    def __init__(self, token: str | None = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        self.offset = 0

        self.gamma_client = GammaClient()
        self.neg_risk_scanner = NegativeRiskScanner()
        self.res_lag_scanner = ResolutionLagScanner()
        self.maker_reward_scanner = MakerRewardScanner()
        self.paper_trader = PaperTrader()
        self.quant_researcher = QuantResearcher()
        self.dossier_generator = DossierGenerator()

    def is_configured(self) -> bool:
        return bool(self.token and len(self.token) > 10)

    def send_message(self, chat_id: int | str, text: str, parse_mode: str = "Markdown") -> bool:
        """Sends text message to chat."""
        if not self.is_configured():
            return False
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {"chat_id": chat_id, "text": text[:4096], "parse_mode": parse_mode, "disable_web_page_preview": True}
            resp = requests.post(url, json=payload, timeout=12)
            if resp.status_code != 200:
                payload["parse_mode"] = ""
                requests.post(url, json=payload, timeout=12)
            return resp.status_code == 200
        except Exception:
            return False

    def send_document(self, chat_id: int | str, file_bytes: bytes, filename: str, caption: str = "") -> bool:
        """Sends PDF dossier to chat."""
        if not self.is_configured():
            return False
        try:
            url = f"{self.base_url}/sendDocument"
            files = {"document": (filename, file_bytes, "application/pdf")}
            data = {"chat_id": chat_id, "caption": caption[:1024]}
            resp = requests.post(url, data=data, files=files, timeout=30)
            return resp.status_code == 200
        except Exception:
            return False

    def handle_command(self, chat_id: int | str, text: str):
        """Processes incoming bot commands."""
        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/start", "/help"):
            msg = (
                "🦅 *PolyArb: Polymarket Quant & Arbitrage Bot*\n\n"
                "I scan Polymarket in real time for structural mathematical mispricings, "
                "settlement discounts, and generate quantitative research dossiers.\n\n"
                "⚡ *Live Commands:*\n"
                "• `/scan` — Comprehensive live scan across all strategies\n"
                "• `/negrisk` — Multi-outcome combinatorial mispricings (∑P ≠ 1.00)\n"
                "• `/reslag` — Resolution lag discount yields (high probability >= 98¢)\n"
                "• `/rewards` — High-paying Merkl liquidity mining pools\n"
                "• `/research [topic]` — Compile & deliver full PDF Quant Dossier\n"
                "• `/paper` — View simulated trading portfolio & PnL\n"
                "• `/simulate` — Automatically paper-trade the best active opportunity\n"
            )
            self.send_message(chat_id, msg)

        elif cmd == "/scan":
            self.send_message(chat_id, "🔍 *Scanning Polymarket live order books...*")
            events = self.gamma_client.get_events(limit=40)
            markets = self.gamma_client.get_markets(limit=60)

            neg_opps = self.neg_risk_scanner.scan_all(events)
            res_discounts = self.res_lag_scanner.scan_all(markets)

            lines = [f"📊 *PolyArb Live Scan Results ({len(events)} Events, {len(markets)} Markets)*\n"]

            if neg_opps:
                lines.append(f"⚡ *Combinatorial Arbitrage ({len(neg_opps)} found):*")
                for o in neg_opps[:3]:
                    lines.append(f"• `{o.event_title[:35]}`")
                    lines.append(f"  Sum: `${o.sum_of_prices}` | Net Profit: *+{o.net_profit_pct}%*")
                lines.append("")
            else:
                lines.append("⚡ *Combinatorial Arbitrage:* None currently >= 1.5% spread.\n")

            if res_discounts:
                lines.append(f"⏳ *Resolution Lag Discounts ({len(res_discounts)} found):*")
                for d in res_discounts[:3]:
                    lines.append(f"• `{d.question[:35]}`")
                    lines.append(f"  Price: `${d.current_price}` | Discount: *{d.settlement_discount_pct}%* (APY: {d.annualized_apy_pct}%)")
            else:
                lines.append("⏳ *Resolution Lag:* No high-probability discounted shares active.")

            lines.append("\n👉 Run `/simulate` to execute a paper trade on the top opportunity.")
            self.send_message(chat_id, "\n".join(lines))

        elif cmd == "/negrisk":
            events = self.gamma_client.get_events(limit=50)
            opps = self.neg_risk_scanner.scan_all(events)
            if not opps:
                self.send_message(chat_id, "ℹ️ No negative-risk mispricings currently meet the minimum 1.5% spread.")
                return

            lines = ["⚡ *Live Negative-Risk Multi-Outcome Arbitrage:*\n"]
            for o in opps[:5]:
                lines.append(f"• *{o.event_title}*")
                lines.append(f"  Outcomes: {o.outcomes_count} | Sum: `${o.sum_of_prices}`")
                lines.append(f"  Action: `{o.strategy_type}` | Net Yield: *+{o.net_profit_pct}%*\n")
            self.send_message(chat_id, "\n".join(lines))

        elif cmd == "/reslag":
            markets = self.gamma_client.get_markets(limit=70)
            discounts = self.res_lag_scanner.scan_all(markets)
            if not discounts:
                self.send_message(chat_id, "ℹ️ No active resolution lag opportunities meeting criteria.")
                return

            lines = ["⏳ *Live Resolution Lag Settlement Discounts:*\n"]
            for d in discounts[:5]:
                lines.append(f"• *{d.question}*")
                lines.append(f"  Side: `{d.winning_side}` at `${d.current_price}`")
                lines.append(f"  Discount: *{d.settlement_discount_pct}%* | Est. Annualized APY: *{d.annualized_apy_pct}%*\n")
            self.send_message(chat_id, "\n".join(lines))

        elif cmd == "/rewards":
            markets = self.gamma_client.get_markets(limit=70)
            rewards = self.maker_reward_scanner.scan_all(markets)
            if not rewards:
                self.send_message(chat_id, "ℹ️ No rewarded markets found with active spread parameters.")
                return

            lines = ["💰 *Top Liquidity Mining Reward Markets:*\n"]
            for r in rewards[:5]:
                lines.append(f"• *{r.question}*")
                lines.append(f"  Max Reward Spread: `{r.rewards_max_spread}` | 24h Vol: `${r.volume_24h:,.0f}`\n")
            self.send_message(chat_id, "\n".join(lines))

        elif cmd == "/research":
            topic = args or "polymarket arbitrage loopholes"
            self.send_message(chat_id, f"🔬 *Compiling Quant Research Dossier on:* `{topic}`...\nAnalyzing live order books and dev archives.")

            data = self.quant_researcher.run_investigation(topic)
            report_md = self.dossier_generator.compile_markdown(data)

            # Send preview text
            preview = report_md[:1200] + "\n\n*(Full report in attached PDF...)*"
            self.send_message(chat_id, preview, parse_mode="")

            pdf_bytes = self.dossier_generator.generate_pdf(report_md)
            if pdf_bytes:
                self.send_document(
                    chat_id,
                    pdf_bytes,
                    filename=f"PolyArb_Report_{int(time.time())}.pdf",
                    caption=f"📄 Verified PolyArb Quant Dossier: {topic}"
                )

        elif cmd == "/paper":
            summary = self.paper_trader.get_summary()
            lines = [
                "📈 *PolyArb Paper Trading Portfolio*\n",
                f"• *Current Balance:* `${summary['current_balance_usdc']:,.2f} USDC`",
                f"• *Total Realized PnL:* `${summary['total_pnl_usdc']:+,.2f}`",
                f"• *ROI:* `{summary['roi_pct']:+}%`",
                f"• *Trades:* `{summary['total_trades']}` (Wins: {summary['winning_trades']}, Losses: {summary['losing_trades']})",
                f"• *Win Rate:* `{summary['win_rate_pct']}%`\n"
            ]
            if summary["recent_trades"]:
                lines.append("*Recent Executions:*")
                for t in summary["recent_trades"][:4]:
                    lines.append(f"• [{t['strategy']}] {t['asset']} -> PnL: *${t['pnl_usdc']:+,.2f}*")
            self.send_message(chat_id, "\n".join(lines))

        elif cmd == "/simulate":
            events = self.gamma_client.get_events(limit=30)
            opps = self.neg_risk_scanner.scan_all(events)
            if opps:
                trade = self.paper_trader.execute_arbitrage(opps[0], amount_usdc=250.0)
                self.send_message(
                    chat_id,
                    f"✅ *Paper Trade Executed!*\n\n"
                    f"• *Strategy:* Negative-Risk Arbitrage\n"
                    f"• *Asset:* {trade.asset}\n"
                    f"• *Size:* ${trade.size_usdc:.2f} USDC\n"
                    f"• *Simulated Net PnL:* *+${trade.pnl_usdc:.2f} USDC*\n\n"
                    f"Check `/paper` to see updated balance."
                )
            else:
                markets = self.gamma_client.get_markets(limit=40)
                discounts = self.res_lag_scanner.scan_all(markets)
                if discounts:
                    trade = self.paper_trader.execute_resolution_lag(discounts[0], amount_usdc=250.0)
                    self.send_message(
                        chat_id,
                        f"✅ *Paper Trade Executed!*\n\n"
                        f"• *Strategy:* Resolution Lag Discount\n"
                        f"• *Asset:* {trade.asset}\n"
                        f"• *Size:* ${trade.size_usdc:.2f} USDC\n"
                        f"• *Simulated PnL at Settlement:* *+${trade.pnl_usdc:.2f} USDC*\n\n"
                        f"Check `/paper` to see updated balance."
                    )
                else:
                    self.send_message(chat_id, "No qualifying opportunities active right now to simulate.")
        else:
            self.send_message(chat_id, "Unknown command. Type `/help` for list of options.")

    def poll_once(self):
        """Polls for pending Telegram updates."""
        if not self.is_configured():
            return
        try:
            url = f"{self.base_url}/getUpdates"
            params = {"offset": self.offset, "timeout": 10}
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                for item in resp.json().get("result", []):
                    self.offset = item["update_id"] + 1
                    msg = item.get("message") or item.get("channel_post")
                    if msg and "text" in msg:
                        self.handle_command(msg["chat"]["id"], msg["text"])
        except Exception:
            pass

    def poll_forever(self):
        """Runs the long-polling loop."""
        if not self.is_configured():
            print("Telegram Bot Token not configured. Export TELEGRAM_BOT_TOKEN to start.")
            return
        print("🤖 PolyArb Telegram Bot daemon started... (Press Ctrl+C to stop)")
        while True:
            try:
                self.poll_once()
                time.sleep(1)
            except KeyboardInterrupt:
                break
            except Exception:
                time.sleep(5)
