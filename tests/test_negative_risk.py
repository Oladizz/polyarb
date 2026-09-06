from app.core.models import Event, Market, MarketOutcome
from app.scanner.negative_risk import NegativeRiskScanner


def test_detect_mint_discount_arbitrage(sample_negative_risk_event):
    scanner = NegativeRiskScanner(min_spread_pct=1.5, slippage_buffer_pct=0.5)
    opps = scanner.scan_event(sample_negative_risk_event)

    assert len(opps) == 1
    opp = opps[0]
    assert opp.strategy_type == "MINT_DISCOUNT"
    assert opp.sum_of_prices == 0.95
    assert opp.spread_pct == -5.0
    assert opp.net_profit_pct == 4.5  # 5.0 - 0.5 buffer


def test_detect_overpriced_basket_arbitrage(sample_overpriced_event):
    scanner = NegativeRiskScanner(min_spread_pct=1.5, slippage_buffer_pct=0.5)
    opps = scanner.scan_event(sample_overpriced_event)

    assert len(opps) == 1
    opp = opps[0]
    assert opp.strategy_type == "OVERPRICED_BASKET"
    assert opp.sum_of_prices == 1.07
    assert opp.spread_pct == 7.0
    assert opp.net_profit_pct == 6.5


def test_fair_priced_event_no_arbitrage():
    m1 = Market(id="m1", question="Fair 1", condition_id="c1", slug="f1", outcomes=[MarketOutcome("Yes", 0.50)])
    m2 = Market(id="m2", question="Fair 2", condition_id="c2", slug="f2", outcomes=[MarketOutcome("Yes", 0.50)])
    event = Event(id="ev_fair", title="Fair Event", slug="fair", volume_24h=10000, markets=[m1, m2])

    scanner = NegativeRiskScanner(min_spread_pct=1.5)
    opps = scanner.scan_event(event)
    assert len(opps) == 0
