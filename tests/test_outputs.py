from valuation_engine import calc_forward_growth, calc_trailing_growth, run_valuation
from tests.test_engine import sample


def test_growth_calculation():
    assert round(calc_trailing_growth(400, 200), 2) == 100.00
    assert round(calc_forward_growth(500, 400), 2) == 25.00


def test_multiple_clamp_max():
    result = run_valuation(sample(prior_arr=100_000, current_arr=4_000_000, forward_arr=10_000_000, nrr_pct=200, grr_pct=99, gross_margin_pct=90, ebitda_margin_pct=50, cac_payback_months=2, acv=200_000, sales_cycle_days=10, billing_profile="multi_year_common", founder_dependence="fully_management_led", product_differentiation="strong_moat_or_category_leader", reporting_quality="very_strong_and_diligence_ready", largest_customer_arr_pct=1, top5_customer_arr_pct=5))
    assert result["valuation"]["final_arr_multiple"] <= 12.0


def test_multiple_clamp_min():
    result = run_valuation(sample(prior_arr=3_900_000, forward_arr=3_700_000, nrr_pct=60, grr_pct=60, gross_margin_pct=30, ebitda_margin_pct=-80, cac_payback_months=80, acv=500, sales_cycle_days=300, billing_profile="mostly_monthly", founder_dependence="very_dependent", product_differentiation="weak_or_commoditized", reporting_quality="basic_or_messy", largest_customer_arr_pct=80, top5_customer_arr_pct=95))
    assert result["valuation"]["final_arr_multiple"] >= 1.0


def test_warnings_expected():
    result = run_valuation(sample(nrr_pct=80, grr_pct=90, logo_churn_pct=0, cac_payback_months=70))
    assert len(result["warnings"]) >= 2


def test_recommendations_align_with_weak_areas():
    result = run_valuation(sample(cac_payback_months=50, sales_cycle_days=250))
    assert any("CAC payback" in rec for rec in result["recommendations"])


def test_waterfall_orders_positive_then_negative_drivers():
    result = run_valuation(sample())
    steps = result["waterfall_steps"]
    component_steps = [step for step in steps[1:-1]]
    positives = [step for step in component_steps if step["delta"] > 0]
    negatives = [step for step in component_steps if step["delta"] < 0]

    if positives and negatives:
        assert component_steps.index(positives[-1]) < component_steps.index(negatives[0])


def test_subscore_writeups_present_for_each_area():
    result = run_valuation(sample())
    assert set(result["subscore_details"].keys()) == set(result["subscores"].keys())
    assert all(detail["writeup"] for detail in result["subscore_details"].values())
