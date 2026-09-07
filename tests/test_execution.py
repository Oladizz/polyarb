"""
Unit tests for the AutonomousTrader quant execution engine.
"""
from app.core.models import ResolutionDiscount
from app.execution.trader import AutonomousTrader


def test_autonomous_trader_init(tmp_path):
    trader = AutonomousTrader(data_dir=str(tmp_path), starting_balance=5000.0)
    assert trader.balance_usdc == 5000.0
    assert trader.active_positions == []
    summary = trader.get_summary()
    assert summary["starting_balance_usdc"] == 5000.0
    assert summary["cash_balance_usdc"] == 5000.0
    assert summary["total_portfolio_equity_usdc"] == 5000.0
    assert summary["roi_pct"] == 0.0


def test_autonomous_trader_execute_buy(tmp_path):
    trader = AutonomousTrader(data_dir=str(tmp_path), starting_balance=1000.0, max_position_size=200.0)
    opp = ResolutionDiscount(
        market_id="mkt_test_1",
        question="Will Starship reach orbit in 2026?",
        winning_side="Yes",
        current_price=0.98,
        settlement_discount_pct=2.0,
        annualized_apy_pct=486.7,
        end_date="2026-12-31",
        volume_24h=50000.0,
        uma_bond="500"
    )

    pos = trader.execute_buy(opp)
    assert pos is not None
    assert pos["market_id"] == "mkt_test_1"
    assert pos["size_usdc"] == 200.0
    # Balance deducted size + entry gas
    assert round(trader.balance_usdc + trader.gas_fee_usdc, 2) == 800.0
    assert len(trader.active_positions) == 1

    summary = trader.get_summary()
    assert summary["invested_usdc"] == 200.0
    assert round(summary["cash_balance_usdc"] + trader.gas_fee_usdc, 2) == 800.0
    assert summary["active_positions_count"] == 1
    assert summary["total_gas_spent_usdc"] == trader.gas_fee_usdc


def test_autonomous_trader_max_positions(tmp_path):
    trader = AutonomousTrader(data_dir=str(tmp_path), starting_balance=1000.0, max_active_positions=2, max_position_size=100.0)
    for i in range(4):
        opp = ResolutionDiscount(
            market_id=f"mkt_{i}",
            question=f"Test Market {i}",
            winning_side="Yes",
            current_price=0.98,
            settlement_discount_pct=2.0,
            annualized_apy_pct=486.7,
            end_date="2026-12-31",
            volume_24h=50000.0,
            uma_bond="500"
        )
        trader.execute_buy(opp)

    assert len(trader.active_positions) == 2


def test_autonomous_trader_persistence(tmp_path):
    trader1 = AutonomousTrader(data_dir=str(tmp_path), starting_balance=1000.0, max_position_size=200.0)
    opp = ResolutionDiscount(
        market_id="mkt_persist",
        question="Will AI pass benchmark?",
        winning_side="Yes",
        current_price=0.98,
        settlement_discount_pct=2.0,
        annualized_apy_pct=486.7,
        end_date="2026-12-31",
        volume_24h=50000.0,
        uma_bond="500"
    )
    trader1.execute_buy(opp)

    # Reload in a new instance
    trader2 = AutonomousTrader(data_dir=str(tmp_path))
    assert trader2.balance_usdc == trader1.balance_usdc
    assert len(trader2.active_positions) == 1
    assert trader2.active_positions[0]["market_id"] == "mkt_persist"
    assert trader2.total_gas_spent_usdc == trader1.total_gas_spent_usdc
