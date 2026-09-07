"""
Unit tests for the CombinatorialEngine complete-set minting & arbitrage engine.
"""
from app.core.models import ArbitrageOpportunity
from app.execution.combinatorial_engine import CombinatorialEngine


def test_evaluate_overpriced_basket():
    engine = CombinatorialEngine(contract_gas_usdc=0.04, protocol_fee_pct=0.2, min_net_profit_pct=1.0)
    opp = ArbitrageOpportunity(
        event_id="ev_comb_1",
        event_title="US Open 2026 Tennis Champion",
        strategy_type="OVERPRICED_BASKET",
        outcomes_count=8,
        sum_of_prices=1.06,  # 6% overpriced
        spread_pct=6.0,
        net_profit_pct=5.5,
        target_outcomes=[]
    )

    eval_res = engine.evaluate_opportunity(opp, available_capital=50.0)
    assert eval_res["viable"] is True
    assert eval_res["allocated_size_usdc"] == 50.0
    assert eval_res["gas_usdc"] == 0.04
    assert eval_res["net_instant_profit_usdc"] > 1.0
    assert eval_res["net_roi_pct"] > 2.0


def test_evaluate_insufficient_capital():
    engine = CombinatorialEngine()
    opp = ArbitrageOpportunity(
        event_id="ev_comb_2",
        event_title="Election Winner",
        strategy_type="OVERPRICED_BASKET",
        outcomes_count=4,
        sum_of_prices=1.05,
        spread_pct=5.0,
        net_profit_pct=4.5,
        target_outcomes=[]
    )
    eval_res = engine.evaluate_opportunity(opp, available_capital=5.0)
    assert eval_res["viable"] is False
    assert "Insufficient capital" in eval_res["reason"]


def test_execute_arbitrage_instant_settlement():
    engine = CombinatorialEngine()
    opp = ArbitrageOpportunity(
        event_id="ev_comb_3",
        event_title="Oscars Best Picture 2026",
        strategy_type="OVERPRICED_BASKET",
        outcomes_count=5,
        sum_of_prices=1.08,
        spread_pct=8.0,
        net_profit_pct=7.5,
        target_outcomes=[]
    )

    result = engine.execute_arbitrage(opp, available_capital=100.0, mode="paper")
    assert result["status"] == "SUCCESS"
    assert result["pnl_usdc"] > 0
    trade = result["trade"]
    assert trade["status"] == "INSTANT_SETTLED_WIN"
    assert trade["strategy"] == "COMBINATORIAL_MINT_MERGE"
    assert trade["size_usdc"] == 50.0
    assert trade["gas_paid_usdc"] > 0
