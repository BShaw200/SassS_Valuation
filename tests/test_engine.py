from valuation_engine import run_valuation


def sample(**overrides):
    base = {
        "current_arr": 4_000_000,
        "prior_arr": 2_800_000,
        "forward_arr": 5_200_000,
        "recurring_revenue_pct": 92,
        "services_revenue_pct": 8,
        "nrr_pct": 112,
        "grr_pct": 93,
        "logo_churn_pct": 9,
        "acv": 18_000,
        "largest_customer_arr_pct": 7,
        "top5_customer_arr_pct": 22,
        "gross_margin_pct": 82,
        "ebitda_margin_pct": 5,
        "cac_payback_months": 14,
        "sales_cycle_days": 75,
        "billing_profile": "mostly_annual_upfront",
        "founder_dependence": "mostly_independent",
        "product_differentiation": "clearly_differentiated",
        "reporting_quality": "strong_and_board_ready",
        "net_cash": 500_000,
    }
    base.update(overrides)
    return base


def test_healthy_saas_case():
    result = run_valuation(sample())
    assert result["valuation"]["base_ev"] > 0
    assert result["confidence"]["label"] in {"Medium", "High"}


def test_small_slow_growth_founder_dependent():
    result = run_valuation(sample(current_arr=800_000, prior_arr=760_000, founder_dependence="very_dependent", nrr_pct=88, grr_pct=82))
    assert result["valuation"]["final_arr_multiple"] < 6


def test_high_growth_strong_nrr():
    result = run_valuation(sample(prior_arr=1_800_000, nrr_pct=130, forward_arr=8_000_000))
    assert result["valuation"]["final_arr_multiple"] >= 8


def test_services_heavy_penalty():
    result = run_valuation(sample(services_revenue_pct=40, recurring_revenue_pct=60))
    assert result["derived_metrics"]["adjusted_clean_arr"] < result["derived_metrics"]["clean_arr"]


def test_concentrated_customer_base_penalty():
    result = run_valuation(sample(largest_customer_arr_pct=40, top5_customer_arr_pct=70))
    assert any("concentration" in d.lower() for d in result["drivers"]["negative"])
