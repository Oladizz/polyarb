"""
Web Dashboard & REST API Server for PolyArb.
Deployable on Render, Railway, Docker, or VPS.
"""
import io
import time
from dataclasses import asdict

from flask import Flask, jsonify, render_template_string, request, send_file

from app.core.config import PORT
from app.execution.trader import AutonomousTrader
from app.ingestor.gamma_client import GammaClient
from app.research.dossier_generator import DossierGenerator
from app.research.quant_researcher import QuantResearcher
from app.scanner.maker_rewards import MakerRewardScanner
from app.scanner.negative_risk import NegativeRiskScanner
from app.scanner.resolution_lag import ResolutionLagScanner
from app.simulation.paper_trader import PaperTrader

app = Flask(__name__)

gamma_client = GammaClient()
neg_risk_scanner = NegativeRiskScanner()
res_lag_scanner = ResolutionLagScanner()
maker_reward_scanner = MakerRewardScanner()
paper_trader = PaperTrader()
auto_trader = AutonomousTrader()
quant_researcher = QuantResearcher()
dossier_generator = DossierGenerator()

# Cache latest research report
CACHED_REPORT = {"markdown": "", "timestamp": 0}


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "polyarb-engine",
        "version": "1.0.0",
        "paper_balance": auto_trader.balance_usdc
    })


@app.route("/api/scan")
def api_scan():
    events = gamma_client.get_events(limit=40)
    markets = gamma_client.get_markets(limit=60)
    neg_opps = neg_risk_scanner.scan_all(events)
    res_discounts = res_lag_scanner.scan_all(markets)
    rewards = maker_reward_scanner.scan_all(markets)

    return jsonify({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "events_scanned": len(events),
        "markets_scanned": len(markets),
        "negative_risk": [asdict(o) for o in neg_opps],
        "resolution_lag": [asdict(d) for d in res_discounts],
        "rewards": [asdict(r) for r in rewards]
    })


@app.route("/api/paper")
@app.route("/api/portfolio")
def api_paper():
    auto_trader._load_state()
    summary = auto_trader.get_summary()
    return jsonify(summary)


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    events = gamma_client.get_events(limit=30)
    opps = neg_risk_scanner.scan_all(events)
    if opps:
        trade = paper_trader.execute_arbitrage(opps[0], amount_usdc=250.0)
        return jsonify({"status": "executed", "strategy": "NEGATIVE_RISK", "trade": asdict(trade)})

    markets = gamma_client.get_markets(limit=40)
    discounts = res_lag_scanner.scan_all(markets)
    if discounts:
        trade = paper_trader.execute_resolution_lag(discounts[0], amount_usdc=250.0)
        return jsonify({"status": "executed", "strategy": "RESOLUTION_LAG", "trade": asdict(trade)})

    return jsonify({"status": "no_opportunities"}), 404


@app.route("/api/research", methods=["POST"])
def api_research():
    data = request.get_json() or {}
    topic = data.get("topic", "polymarket arbitrage loopholes")
    results = quant_researcher.run_investigation(topic)
    report_md = dossier_generator.compile_markdown(results)
    CACHED_REPORT["markdown"] = report_md
    CACHED_REPORT["timestamp"] = time.time()
    return jsonify({
        "status": "completed",
        "topic": topic,
        "markdown": report_md,
        "pdf_download_url": "/api/research/pdf"
    })


@app.route("/api/research/pdf")
def api_research_pdf():
    if not CACHED_REPORT["markdown"]:
        # Run default
        results = quant_researcher.run_investigation("polymarket arbitrage loopholes")
        CACHED_REPORT["markdown"] = dossier_generator.compile_markdown(results)

    pdf_bytes = dossier_generator.generate_pdf(CACHED_REPORT["markdown"])
    if not pdf_bytes:
        return jsonify({"error": "Failed to generate PDF"}), 500

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="PolyArb_Quant_Dossier.pdf"
    )


@app.route("/")
def dashboard():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🦅 PolyArb | Polymarket Quant & Arbitrage Dashboard</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>
            body { background: #090d16; color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
            .card { background: #131b2e; border: 1px solid #1e293b; border-radius: 12px; }
            .stat-card { border-left: 4px solid #0d9488; }
            .badge-teal { background: #0d9488; }
            .badge-amber { background: #f59e0b; color: #000; }
            .btn-teal { background: #0d9488; color: #fff; font-weight: 600; border: none; }
            .btn-teal:hover { background: #0f766e; color: #fff; }
            pre { background: #070a10; padding: 16px; border-radius: 8px; color: #94a3b8; max-height: 400px; }
        </style>
    </head>
    <body class="py-4">
        <div class="container" style="max-width: 1080px;">
            <!-- Header -->
            <div class="d-flex justify-content-between align-items-center mb-4 pb-3 border-bottom border-secondary">
                <div>
                    <h2 class="fw-bold mb-0">🦅 PolyArb Terminal</h2>
                    <p class="text-secondary small mb-0">Real-Time Polymarket Combinatorial Arbitrage & Quant Intelligence</p>
                </div>
                <div>
                    <button class="btn btn-teal btn-sm me-2" onclick="runLiveScan()">⚡ Refresh Scan</button>
                    <button class="btn btn-outline-info btn-sm" onclick="runSimulateTrade()">🧪 Simulate Trade</button>
                </div>
            </div>

            <!-- Stats Bar -->
            <div class="row g-3 mb-4">
                <div class="col-md-3">
                    <div class="card p-3 stat-card">
                        <small class="text-secondary">Paper Portfolio</small>
                        <h4 class="fw-bold mb-0" id="paperBalance">$10,000.00</h4>
                        <small class="text-success" id="paperRoi">+0.0% ROI</small>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-3 stat-card" style="border-left-color: #3b82f6;">
                        <small class="text-secondary">Paper Win Rate</small>
                        <h4 class="fw-bold mb-0" id="paperWinRate">0.0%</h4>
                        <small class="text-secondary" id="paperTrades">0 Trades</small>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-3 stat-card" style="border-left-color: #f59e0b;">
                        <small class="text-secondary">Negative Risk Spreads</small>
                        <h4 class="fw-bold mb-0" id="negRiskCount">Scanning...</h4>
                        <small class="text-warning">∑P ≠ 1.00 Mispricings</small>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-3 stat-card" style="border-left-color: #10b981;">
                        <small class="text-secondary">Resolution Lag Yields</small>
                        <h4 class="fw-bold mb-0" id="resLagCount">Scanning...</h4>
                        <small class="text-success">Decided Tokens ≥ 98¢</small>
                    </div>
                </div>
            </div>

            <!-- Live Arbitrage Table -->
            <div class="card p-4 shadow-sm mb-4">
                <h5 class="fw-bold mb-3">⚡ Live Combinatorial Arbitrage (Negative Risk)</h5>
                <div class="table-responsive">
                    <table class="table table-dark table-hover mb-0">
                        <thead>
                            <tr class="text-secondary small">
                                <th>Event</th>
                                <th>Outcomes</th>
                                <th>Sum YES</th>
                                <th>Spread %</th>
                                <th>Est. Net Profit</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody id="arbTableBody">
                            <tr><td colspan="6" class="text-center text-secondary">Loading live order books...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Research Dossier Trigger -->
            <div class="card p-4 shadow-sm mb-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5 class="fw-bold mb-0">🔬 Quant Research & Loophole Dossier</h5>
                    <a href="/api/research/pdf" target="_blank" class="btn btn-outline-teal btn-sm">📄 Download Full PDF</a>
                </div>
                <button class="btn btn-teal w-100 mb-3" id="researchBtn" onclick="generateDossier()">Generate Fresh Deep Dossier</button>
                <div id="reportBox" class="d-none">
                    <pre id="reportContent" style="white-space: pre-wrap;"></pre>
                </div>
            </div>
        </div>

        <script>
            async function loadPaperData() {
                try {
                    const res = await fetch('/api/paper');
                    const data = await res.json();
                    const eq = data.total_portfolio_equity_usdc !== undefined ? data.total_portfolio_equity_usdc : data.current_balance_usdc;
                    document.getElementById('paperBalance').innerText = '$' + eq.toLocaleString(undefined, {minimumFractionDigits: 2});
                    document.getElementById('paperRoi').innerText = (data.roi_pct >= 0 ? '+' : '') + data.roi_pct + '% ROI';
                    document.getElementById('paperWinRate').innerText = data.win_rate_pct + '%';
                    const trades = data.total_completed_trades !== undefined ? data.total_completed_trades : (data.total_trades || 0);
                    document.getElementById('paperTrades').innerText = trades + ' Closed (' + (data.active_positions_count || 0) + ' Active)';
                } catch(e) {}
            }

            async function runLiveScan() {
                try {
                    const res = await fetch('/api/scan');
                    const data = await res.json();
                    document.getElementById('negRiskCount').innerText = data.negative_risk.length + ' Active';
                    document.getElementById('resLagCount').innerText = data.resolution_lag.length + ' Active';

                    const tbody = document.getElementById('arbTableBody');
                    if (data.negative_risk.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-secondary py-3">No active events currently exceed the 1.5% net arbitrage threshold.</td></tr>';
                    } else {
                        tbody.innerHTML = data.negative_risk.map(o => `
                            <tr>
                                <td class="fw-bold">${o.event_title}</td>
                                <td><span class="badge bg-secondary">${o.outcomes_count}</span></td>
                                <td>$${o.sum_of_prices}</td>
                                <td><span class="badge ${o.spread_pct > 0 ? 'badge-amber' : 'badge-teal'}">${o.spread_pct}%</span></td>
                                <td class="text-success fw-bold">+${o.net_profit_pct}%</td>
                                <td><span class="badge bg-dark border border-teal text-teal">${o.strategy_type}</span></td>
                            </tr>
                        `).join('');
                    }
                } catch(e) {}
            }

            async function runSimulateTrade() {
                const res = await fetch('/api/simulate', {method: 'POST'});
                const data = await res.json();
                if (data.status === 'executed') {
                    alert('Simulated trade executed! PnL: +$' + data.trade.pnl_usdc);
                    loadPaperData();
                } else {
                    alert('No qualifying opportunities meeting criteria right now.');
                }
            }

            async function generateDossier() {
                const btn = document.getElementById('researchBtn');
                btn.disabled = true;
                btn.innerText = "Compiling Quant Research & Telemetry...";
                const res = await fetch('/api/research', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({})});
                const data = await res.json();
                document.getElementById('reportBox').classList.remove('d-none');
                document.getElementById('reportContent').innerText = data.markdown;
                btn.disabled = false;
                btn.innerText = "Generate Fresh Deep Dossier";
            }

            loadPaperData();
            runLiveScan();
        </script>
    </body>
    </html>
    """
    return render_template_string(html)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
