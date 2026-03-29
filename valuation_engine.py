from __future__ import annotations

from typing import Any

from helpers import average, clamp, normalize_score, safe_add

LABELS = {
    "scale_adjustment": "Scale",
    "nrr_adjustment": "Net revenue retention",
    "grr_adjustment": "Gross revenue retention",
    "gross_margin_adjustment": "Gross margin",
    "rule_of_40_adjustment": "Rule of 40",
    "cac_payback_adjustment": "CAC payback",
    "largest_customer_adjustment": "Largest-customer concentration",
    "top5_adjustment": "Top-5 customer concentration",
    "billing_adjustment": "Billing profile",
    "founder_dependence_adjustment": "Founder dependence",
    "product_adjustment": "Product differentiation",
    "reporting_adjustment": "Reporting quality",
    "sales_cycle_adjustment": "Sales cycle",
    "acv_adjustment": "ACV quality",
    "forward_growth_overlay": "Forward growth outlook",
}


class ValidationError(ValueError):
    pass


def bucket(value: float, thresholds: list[tuple[float, float]]) -> float:
    for max_v, out in thresholds:
        if value < max_v:
            return out
    return thresholds[-1][1]


def calc_trailing_growth(current_arr: float, prior_arr: float) -> float | None:
    if prior_arr == 0:
        return None
    return ((current_arr - prior_arr) / prior_arr) * 100


def calc_forward_growth(forward_arr: float, current_arr: float) -> float:
    if current_arr <= 0:
        raise ValidationError("Current ARR must be greater than 0.")
    return ((forward_arr - current_arr) / current_arr) * 100


def get_services_penalty(services_revenue_pct: float) -> float:
    if services_revenue_pct < 15:
        return 0.0
    if services_revenue_pct <= 30:
        return 0.05
    return 0.10


def get_base_growth_multiple(trailing_growth: float | None, forward_growth: float) -> float:
    if trailing_growth is None:
        if forward_growth < 20:
            return 3.0
        if forward_growth < 50:
            return 4.5
        return 6.0
    if trailing_growth < 10:
        return 2.0
    if trailing_growth < 20:
        return 3.0
    if trailing_growth < 40:
        return 4.5
    if trailing_growth < 70:
        return 6.0
    return 8.0


def get_scale_adjustment(current_arr: float) -> float:
    if current_arr < 1_000_000:
        return -0.75
    if current_arr < 3_000_000:
        return -0.25
    if current_arr < 10_000_000:
        return 0.25
    if current_arr < 30_000_000:
        return 0.75
    return 1.25


def validate_inputs(inputs: dict[str, Any]) -> None:
    if inputs.get("current_arr", 0) <= 0:
        raise ValidationError("Current ARR must be greater than 0.")
    ranges = {
        "prior_arr": (0, None), "forward_arr": (0, None), "recurring_revenue_pct": (0, 100),
        "services_revenue_pct": (0, 100), "nrr_pct": (0, 300), "grr_pct": (0, 100), "logo_churn_pct": (0, 100),
        "acv": (0, None), "largest_customer_arr_pct": (0, 100), "top5_customer_arr_pct": (0, 100),
        "gross_margin_pct": (-100, 100), "ebitda_margin_pct": (-100, 100), "cac_payback_months": (0, 120),
        "sales_cycle_days": (0, 730),
    }
    for k, (min_v, max_v) in ranges.items():
        value = float(inputs[k])
        if value < min_v or (max_v is not None and value > max_v):
            raise ValidationError(f"{k} is out of range.")
    if inputs["top5_customer_arr_pct"] < inputs["largest_customer_arr_pct"]:
        raise ValidationError("Top-5 concentration must be >= largest customer concentration.")
    if inputs["recurring_revenue_pct"] + inputs["services_revenue_pct"] > 105:
        raise ValidationError("Recurring revenue % plus services revenue % is implausibly high.")


def generate_soft_warnings(inputs: dict[str, Any], trailing_growth: float | None = None, forward_growth: float | None = None) -> list[str]:
    warnings: list[str] = []
    if inputs["nrr_pct"] < inputs["grr_pct"]:
        warnings.append("Your inputs appear slightly inconsistent. NRR is normally at least as high as GRR.")
    if inputs["logo_churn_pct"] == 0 and inputs["grr_pct"] < 90:
        warnings.append("Logo churn appears optimistic relative to GRR.")
    if inputs["gross_margin_pct"] > 95 or inputs["gross_margin_pct"] < 0:
        warnings.append("Gross margin appears unusual; please double-check.")
    if inputs["cac_payback_months"] > 60:
        warnings.append("CAC payback is very long and may indicate go-to-market inefficiency.")
    if inputs["acv"] >= 100_000 and inputs["sales_cycle_days"] < 30:
        warnings.append("Very high ACV with an extremely short sales cycle is uncommon.")
    if trailing_growth is not None and trailing_growth > 70 and inputs["nrr_pct"] < 90:
        warnings.append("High growth with very low NRR may be hard to sustain.")
    if inputs["nrr_pct"] > 150:
        warnings.append("NRR is unusually high; please confirm methodology.")
    if forward_growth is not None and forward_growth > 200:
        warnings.append("Forward growth is unusually high and may reduce estimate certainty.")
    if inputs["prior_arr"] == 0:
        warnings.append("Prior ARR is zero; valuation uses forward-growth fallback and lower confidence.")
    return warnings


def _adj_map() -> dict[str, dict[Any, float] | Any]:
    return {
        "nrr": lambda x: -1.0 if x < 90 else -0.5 if x < 100 else 0.25 if x < 110 else 0.75 if x < 120 else 1.25,
        "grr": lambda x: -0.75 if x < 80 else -0.25 if x < 90 else 0.10 if x <= 95 else 0.35,
        "gross_margin": lambda x: -1.0 if x < 60 else -0.5 if x < 70 else 0.0 if x < 80 else 0.25 if x <= 85 else 0.5,
        "rule_of_40": lambda x: -1.0 if x < 0 else -0.5 if x < 20 else 0.0 if x < 40 else 0.5 if x < 60 else 1.0,
        "cac": lambda x: -0.75 if x > 24 else -0.25 if x >= 18 else 0.0 if x >= 12 else 0.5 if x >= 6 else 0.75,
        "largest": lambda x: -1.0 if x > 30 else -0.5 if x >= 20 else 0.0 if x >= 10 else 0.25,
        "top5": lambda x: -0.75 if x > 60 else -0.25 if x >= 40 else 0.0 if x >= 20 else 0.25,
        "billing": {"mostly_monthly": 0.0, "mixed_monthly_annual": 0.1, "mostly_annual_upfront": 0.3, "multi_year_common": 0.5},
        "founder": {"very_dependent": -0.75, "somewhat_dependent": -0.25, "mostly_independent": 0.1, "fully_management_led": 0.35},
        "product": {"weak_or_commoditized": -0.5, "somewhat_differentiated": 0.0, "clearly_differentiated": 0.35, "strong_moat_or_category_leader": 0.75},
        "reporting": {"basic_or_messy": -0.5, "decent_but_incomplete": 0.0, "strong_and_board_ready": 0.25, "very_strong_and_diligence_ready": 0.5},
        "sales_cycle": lambda x: -0.35 if x > 180 else -0.1 if x >= 90 else 0.0 if x >= 30 else 0.1,
        "acv": lambda x: -0.2 if x < 2500 else 0.0 if x < 10000 else 0.1 if x < 50000 else 0.25,
        "forward": lambda x: -0.2 if x < 10 else 0.0 if x < 25 else 0.15 if x < 50 else 0.3,
    }


def calculate_subscores(inputs: dict[str, Any], trailing_growth: float | None, forward_growth: float, rule_of_40: float) -> dict[str, int]:
    growth = average([clamp((trailing_growth if trailing_growth is not None else forward_growth) + 30, 0, 100), clamp(forward_growth + 40, 0, 100)])
    retention = average([clamp(inputs["nrr_pct"] - 20, 0, 100), clamp(inputs["grr_pct"], 0, 100), clamp(100 - inputs["logo_churn_pct"], 0, 100)])
    profitability = average([clamp(inputs["gross_margin_pct"], 0, 100), clamp(inputs["ebitda_margin_pct"] + 50, 0, 100), clamp(rule_of_40 + 40, 0, 100)])
    efficiency = average([clamp(100 - (inputs["cac_payback_months"] * 1.5), 0, 100), clamp(100 - (inputs["sales_cycle_days"] / 3), 0, 100)])
    rq = average([clamp(inputs["recurring_revenue_pct"], 0, 100), clamp(100 - inputs["services_revenue_pct"], 0, 100), clamp(70 + _adj_map()["billing"][inputs["billing_profile"]] * 40, 0, 100)])
    risk = average([
        clamp(100 - inputs["largest_customer_arr_pct"] * 2, 0, 100), clamp(100 - inputs["top5_customer_arr_pct"], 0, 100),
        clamp(70 + _adj_map()["founder"][inputs["founder_dependence"]] * 40, 0, 100), clamp(70 + _adj_map()["product"][inputs["product_differentiation"]] * 40, 0, 100),
        clamp(70 + _adj_map()["reporting"][inputs["reporting_quality"]] * 40, 0, 100),
    ])
    return {"growth": normalize_score(growth), "retention": normalize_score(retention), "profitability": normalize_score(profitability), "efficiency": normalize_score(efficiency), "revenue_quality": normalize_score(rq), "risk_transferability": normalize_score(risk)}


def generate_recommendations(subscores: dict[str, int], inputs: dict[str, Any]) -> list[str]:
    recs = []
    for area, _ in sorted(subscores.items(), key=lambda x: x[1])[:3]:
        if area == "efficiency":
            recs.append("Shorten CAC payback through pricing, conversion, or lower acquisition spend.")
        elif area == "risk_transferability":
            recs.append("Reduce concentration and founder dependency by broadening ownership of customer relationships.")
        elif area == "retention":
            recs.append("Improve net revenue retention via expansion playbooks and customer success programs.")
        elif area == "revenue_quality":
            recs.append("Increase annual billing and recurring mix to improve revenue quality and cash flow.")
        elif area == "profitability":
            recs.append("Improve gross margin and operating leverage to strengthen durability.")
        elif area == "growth":
            recs.append("Improve sustainable growth by tightening ICP targeting and upsell motions.")
    if inputs["reporting_quality"] in {"basic_or_messy", "decent_but_incomplete"}:
        recs.append("Strengthen KPI reporting and cohort tracking before a fundraising or sale process.")
    return recs[:5]


def calc_confidence_score(inputs: dict[str, Any], warnings: list[str]) -> int:
    score = 70
    if inputs["recurring_revenue_pct"] >= 85:
        score += 5
    if inputs["reporting_quality"] in {"strong_and_board_ready", "very_strong_and_diligence_ready"}:
        score += 5
    if inputs.get("nrr_pct") is not None and inputs.get("grr_pct") is not None and inputs["nrr_pct"] >= inputs["grr_pct"]:
        score += 5
    if inputs["prior_arr"] == 0:
        score -= 10
    if inputs["recurring_revenue_pct"] < 70:
        score -= 10
    if inputs["services_revenue_pct"] > 30:
        score -= 10
    if inputs["reporting_quality"] == "basic_or_messy":
        score -= 10
    if inputs["largest_customer_arr_pct"] > 30:
        score -= 5
    if warnings:
        score -= 10
    return int(clamp(score, 0, 100))


def confidence_bucket(score: int) -> str:
    if score >= 80:
        return "High"
    if score >= 60:
        return "Medium"
    return "Low"


def rank_drivers(scale_adjustment: float, adjustments: dict[str, float]) -> tuple[list[str], list[str]]:
    items = {"scale_adjustment": scale_adjustment, **adjustments}
    ordered = sorted(items.items(), key=lambda x: x[1], reverse=True)
    positive = [f"{LABELS[k]} ({v:+.2f}x)" for k, v in ordered if v > 0][:3]
    negative = [f"{LABELS[k]} ({v:+.2f}x)" for k, v in sorted(items.items(), key=lambda x: x[1]) if v < 0][:3]
    return positive, negative


def run_valuation(inputs: dict[str, Any]) -> dict[str, Any]:
    validate_inputs(inputs)
    trailing_growth = calc_trailing_growth(inputs["current_arr"], inputs["prior_arr"])
    forward_growth = calc_forward_growth(inputs["forward_arr"], inputs["current_arr"])
    warnings = generate_soft_warnings(inputs, trailing_growth, forward_growth)

    rule_of_40 = safe_add(trailing_growth, inputs["ebitda_margin_pct"])
    clean_arr = inputs["current_arr"] * (inputs["recurring_revenue_pct"] / 100)
    adjusted_clean_arr = clean_arr * (1 - get_services_penalty(inputs["services_revenue_pct"]))
    base_growth_multiple = get_base_growth_multiple(trailing_growth, forward_growth)
    scale_adjustment = get_scale_adjustment(inputs["current_arr"])

    m = _adj_map()
    adjustments = {
        "nrr_adjustment": m["nrr"](inputs["nrr_pct"]),
        "grr_adjustment": m["grr"](inputs["grr_pct"]),
        "gross_margin_adjustment": m["gross_margin"](inputs["gross_margin_pct"]),
        "rule_of_40_adjustment": m["rule_of_40"](rule_of_40),
        "cac_payback_adjustment": m["cac"](inputs["cac_payback_months"]),
        "largest_customer_adjustment": m["largest"](inputs["largest_customer_arr_pct"]),
        "top5_adjustment": m["top5"](inputs["top5_customer_arr_pct"]),
        "billing_adjustment": m["billing"][inputs["billing_profile"]],
        "founder_dependence_adjustment": m["founder"][inputs["founder_dependence"]],
        "product_adjustment": m["product"][inputs["product_differentiation"]],
        "reporting_adjustment": m["reporting"][inputs["reporting_quality"]],
        "sales_cycle_adjustment": m["sales_cycle"](inputs["sales_cycle_days"]),
        "acv_adjustment": m["acv"](inputs["acv"]),
        "forward_growth_overlay": m["forward"](forward_growth),
    }
    final_multiple = clamp(base_growth_multiple + scale_adjustment + sum(adjustments.values()), 1.0, 12.0)

    base_ev = adjusted_clean_arr * final_multiple
    low_ev = base_ev * 0.85
    high_ev = base_ev * 1.15

    base_equity = base_ev + inputs["net_cash"]
    low_equity = low_ev + inputs["net_cash"]
    high_equity = high_ev + inputs["net_cash"]

    confidence_score = calc_confidence_score(inputs, warnings)
    positive_drivers, negative_drivers = rank_drivers(scale_adjustment, adjustments)
    subscores = calculate_subscores(inputs, trailing_growth, forward_growth, rule_of_40)

    return {
        "derived_metrics": {"trailing_growth_pct": trailing_growth, "forward_growth_pct": forward_growth, "rule_of_40": rule_of_40, "clean_arr": clean_arr, "adjusted_clean_arr": adjusted_clean_arr},
        "multiple_components": {"base_growth_multiple": base_growth_multiple, "scale_adjustment": scale_adjustment, **adjustments},
        "valuation": {
            "final_arr_multiple": final_multiple,
            "low_ev": low_ev,
            "base_ev": base_ev,
            "high_ev": high_ev,
            "low_equity_value": low_equity,
            "base_equity_value": base_equity,
            "high_equity_value": high_equity,
        },
        "confidence": {"score": confidence_score, "label": confidence_bucket(confidence_score)},
        "drivers": {"positive": positive_drivers, "negative": negative_drivers},
        "subscores": subscores,
        "recommendations": generate_recommendations(subscores, inputs),
        "warnings": warnings,
    }
