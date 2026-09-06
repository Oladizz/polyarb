from app.core.models import Market, MarketOutcome
from app.scanner.resolution_lag import ResolutionLagScanner


def test_detect_resolution_lag_discount(sample_resolution_lag_market):
    scanner = ResolutionLagScanner(min_prob=0.975, max_prob=0.995, min_volume=5000)
    discounts = scanner.scan_market(sample_resolution_lag_market)

    assert len(discounts) == 1
    d = discounts[0]
    assert d.winning_side == "Yes"
    assert d.current_price == 0.985
    assert d.settlement_discount_pct == 1.5
    assert d.annualized_apy_pct == 365.0  # (1.5 / 1.5) * 365


def test_skip_low_probability_market():
    m = Market(
        id="m_low", question="Toss up", condition_id="c_low", slug="toss",
        volume_24h=50000, outcomes=[MarketOutcome("Yes", 0.55), MarketOutcome("No", 0.45)]
    )
    scanner = ResolutionLagScanner(min_prob=0.975)
    assert len(scanner.scan_market(m)) == 0


def test_skip_low_volume_market():
    m = Market(
        id="m_vol", question="Small match", condition_id="c_vol", slug="small",
        volume_24h=100, outcomes=[MarketOutcome("Yes", 0.985)]
    )
    scanner = ResolutionLagScanner(min_volume=5000)
    assert len(scanner.scan_market(m)) == 0
