from app.research.dossier_generator import DossierGenerator


def test_compile_markdown_report():
    generator = DossierGenerator()
    dummy_data = {
        "topic": "Polymarket Arbitrage Mechanics",
        "events_scanned": 15,
        "markets_scanned": 45,
        "negative_risk_opportunities": [],
        "resolution_lag_opportunities": [],
        "strategies": [
            {
                "name": "Resolution Lag",
                "viability": "95%",
                "capital": "$1k",
                "speed_requirement": "Low",
                "risk": "UMA Dispute"
            }
        ],
        "web_sources": ["https://polymarket.com", "https://umaproject.org"]
    }

    md = generator.compile_markdown(dummy_data)
    assert "# 🦅 PolyArb: Polymarket Quant Intelligence Dossier" in md
    assert "Resolution Lag" in md
    assert "https://umaproject.org" in md


def test_generate_pdf():
    generator = DossierGenerator()
    test_md = "# PolyArb Test Report\n\n- Verified Fact: Arbitrage yield calculated."
    pdf_bytes = generator.generate_pdf(test_md)

    assert pdf_bytes is not None
    assert pdf_bytes.startswith(b"%PDF")
