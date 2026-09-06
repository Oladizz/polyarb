import pytest

from app.core.models import Event, Market, MarketOutcome


@pytest.fixture
def sample_negative_risk_event():
    m1 = Market(
        id="m1", question="Candidate A", condition_id="c1", slug="cand-a",
        volume_24h=50000, outcomes=[MarketOutcome("Yes", 0.40), MarketOutcome("No", 0.60)]
    )
    m2 = Market(
        id="m2", question="Candidate B", condition_id="c2", slug="cand-b",
        volume_24h=40000, outcomes=[MarketOutcome("Yes", 0.35), MarketOutcome("No", 0.65)]
    )
    m3 = Market(
        id="m3", question="Candidate C", condition_id="c3", slug="cand-c",
        volume_24h=30000, outcomes=[MarketOutcome("Yes", 0.20), MarketOutcome("No", 0.80)]
    )
    # Sum of YES = 0.40 + 0.35 + 0.20 = 0.95 -> 5% discount
    return Event(
        id="ev_test",
        title="Mayor Election 2026",
        slug="mayor-election-2026",
        volume_24h=120000,
        markets=[m1, m2, m3],
        neg_risk=True
    )


@pytest.fixture
def sample_overpriced_event():
    m1 = Market(
        id="m1", question="Team 1", condition_id="c1", slug="t1",
        volume_24h=50000, outcomes=[MarketOutcome("Yes", 0.55), MarketOutcome("No", 0.45)]
    )
    m2 = Market(
        id="m2", question="Team 2", condition_id="c2", slug="t2",
        volume_24h=50000, outcomes=[MarketOutcome("Yes", 0.52), MarketOutcome("No", 0.48)]
    )
    # Sum of YES = 0.55 + 0.52 = 1.07 -> 7% overpriced
    return Event(
        id="ev_over",
        title="Tournament Winner",
        slug="tournament-winner",
        volume_24h=100000,
        markets=[m1, m2],
        neg_risk=True
    )


@pytest.fixture
def sample_resolution_lag_market():
    return Market(
        id="m_res",
        question="Did Candidate A win the election?",
        condition_id="c_res",
        slug="candidate-a-win",
        volume_24h=85000,
        end_date="2026-09-07T00:00:00Z",
        uma_bond="5000",
        outcomes=[
            MarketOutcome("Yes", 0.985),
            MarketOutcome("No", 0.015)
        ]
    )
