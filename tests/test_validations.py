import pytest

from valuation_engine import ValidationError, run_valuation
from tests.test_engine import sample


def test_new_company_prior_arr_zero_allowed_with_warning():
    result = run_valuation(sample(prior_arr=0, forward_arr=800_0000))
    assert any("fallback" in w.lower() for w in result["warnings"])


def test_net_debt_possible_negative_equity():
    result = run_valuation(sample(net_cash=-50_000_000, current_arr=1_000_000, prior_arr=900_000, forward_arr=1_100_000))
    assert result["valuation"]["base_equity_value"] < 0


def test_invalid_current_arr_blocks():
    with pytest.raises(ValidationError):
        run_valuation(sample(current_arr=0))


def test_invalid_concentration_blocks():
    with pytest.raises(ValidationError):
        run_valuation(sample(largest_customer_arr_pct=30, top5_customer_arr_pct=20))
