from app.core.models import ArbitrageOpportunity, ResolutionDiscount
from app.simulation.paper_trader import PaperTrader


def test_paper_trader_initial_state():
    trader = PaperTrader(starting_balance=10000.0)
    summary = trader.get_summary()

    assert summary["starting_balance_usdc"] == 10000.0
    assert summary["current_balance_usdc"] == 10000.0
    assert summary["total_trades"] == 0
    assert summary["total_pnl_usdc"] == 0.0


def test_paper_trade_arbitrage():
    trader = PaperTrader(starting_balance=10000.0, max_position=500.0, fee_buffer_pct=0.5)
    opp = ArbitrageOpportunity(
        event_id="e1",
        event_title="Test Arb",
        strategy_type="MINT_DISCOUNT",
        outcomes_count=3,
        sum_of_prices=0.96,
        spread_pct=-4.0,
        net_profit_pct=3.5,
        target_outcomes=[]
    )

    trade = trader.execute_arbitrage(opp, amount_usdc=200.0)
    assert trade.status == "RESOLVED_WIN"
    assert trade.size_usdc == 200.0
    # 200 * 3.5% = 7.00 USDC
    assert trade.pnl_usdc == 7.00
    assert trader.current_balance == 10007.00

    summary = trader.get_summary()
    assert summary["total_trades"] == 1
    assert summary["winning_trades"] == 1
    assert summary["win_rate_pct"] == 100.0
    assert summary["total_pnl_usdc"] == 7.00


def test_paper_trade_resolution_lag():
    trader = PaperTrader(starting_balance=1000.0, max_position=500.0, fee_buffer_pct=0.0)
    disc = ResolutionDiscount(
        market_id="m1",
        question="Decided Event",
        winning_side="Yes",
        current_price=0.98,
        settlement_discount_pct=2.0,
        annualized_apy_pct=486.0,
        end_date=None,
        volume_24h=50000,
        uma_bond=None
    )

    trade = trader.execute_resolution_lag(disc, amount_usdc=100.0)
    assert trade.status == "RESOLVED_WIN"
    # shares = 100 / 0.98 = 102.04 shares.
    # PnL = 102.04 * (1.0 - 0.98) = ~2.04 USDC
    assert trade.pnl_usdc > 2.0
    assert trader.current_balance > 1000.0
