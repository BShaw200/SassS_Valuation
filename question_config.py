from __future__ import annotations

SECTIONS = [
    {
        "title": "Revenue & Growth",
        "questions": [
            {"field_id": "current_arr", "label": "What is your current Annual Recurring Revenue (ARR)?", "type": "currency", "required": True, "min": 0.0, "help_text": "Use current annualized recurring subscription revenue. Exclude one-time services and hardware revenue."},
            {"field_id": "prior_arr", "label": "What was your ARR 12 months ago?", "type": "currency", "required": True, "min": 0.0, "help_text": "Used to calculate trailing ARR growth."},
            {"field_id": "forward_arr", "label": "What do you expect ARR to be 12 months from now?", "type": "currency", "required": True, "min": 0.0, "help_text": "Used as a forward-looking confidence overlay."},
            {"field_id": "recurring_revenue_pct", "label": "What percentage of total revenue is true recurring subscription revenue?", "type": "percentage", "required": True, "min": 0.0, "max": 100.0, "help_text": "Include contracted recurring software subscriptions. Exclude one-time fees and most services."},
            {"field_id": "services_revenue_pct", "label": "What percentage of revenue comes from implementation, consulting, or other services?", "type": "percentage", "required": True, "min": 0.0, "max": 100.0, "help_text": "Higher services mix generally reduces SaaS multiples."},
        ],
    },
    {
        "title": "Retention & Customer Quality",
        "questions": [
            {"field_id": "nrr_pct", "label": "What is your Net Revenue Retention (NRR)?", "type": "percentage", "required": True, "min": 0.0, "max": 300.0, "help_text": "Revenue retained from the starting customer cohort after expansion, downgrades, and churn."},
            {"field_id": "grr_pct", "label": "What is your Gross Revenue Retention (GRR)?", "type": "percentage", "required": True, "min": 0.0, "max": 100.0, "help_text": "Revenue retained before expansion."},
            {"field_id": "logo_churn_pct", "label": "What is your annual logo churn rate?", "type": "percentage", "required": True, "min": 0.0, "max": 100.0, "help_text": "Percent of customers lost over the last 12 months."},
            {"field_id": "acv", "label": "What is your average annual contract value (ACV) or average revenue per account?", "type": "currency", "required": True, "min": 0.0, "help_text": "Use your best estimate if you do not track ACV formally."},
            {"field_id": "largest_customer_arr_pct", "label": "What percentage of ARR comes from your single largest customer?", "type": "percentage", "required": True, "min": 0.0, "max": 100.0, "help_text": "High concentration increases buyer risk."},
        ],
    },
    {
        "title": "Profitability & Efficiency",
        "questions": [
            {"field_id": "top5_customer_arr_pct", "label": "What percentage of ARR comes from your top 5 customers combined?", "type": "percentage", "required": True, "min": 0.0, "max": 100.0, "help_text": "Used to assess broader concentration risk."},
            {"field_id": "gross_margin_pct", "label": "What is your gross margin?", "type": "percentage", "required": True, "min": -100.0, "max": 100.0, "help_text": "(Revenue - cost of revenue) / revenue."},
            {"field_id": "ebitda_margin_pct", "label": "What is your EBITDA margin or operating profit margin?", "type": "percentage", "required": True, "min": -100.0, "max": 100.0, "help_text": "Use EBITDA margin if available. Otherwise use operating margin."},
            {"field_id": "cac_payback_months", "label": "What is your CAC payback period?", "type": "number", "required": True, "min": 0.0, "max": 120.0, "help_text": "Number of months required to recover customer acquisition cost from gross profit."},
            {"field_id": "sales_cycle_days", "label": "What is your average sales cycle?", "type": "number", "required": True, "min": 0.0, "max": 730.0, "help_text": "Approximate average number of days from qualified opportunity to close."},
        ],
    },
    {
        "title": "Risk, Transferability & Balance Sheet",
        "questions": [
            {"field_id": "billing_profile", "label": "How are customers typically billed?", "type": "radio", "required": True, "options": ["mostly_monthly", "mixed_monthly_annual", "mostly_annual_upfront", "multi_year_common"], "help_text": "Better billing terms improve revenue quality and cash flow."},
            {"field_id": "founder_dependence", "label": "How dependent is the business on the founder for sales, product direction, or key customer relationships?", "type": "radio", "required": True, "options": ["very_dependent", "somewhat_dependent", "mostly_independent", "fully_management_led"]},
            {"field_id": "product_differentiation", "label": "How differentiated is the product in the market?", "type": "radio", "required": True, "options": ["weak_or_commoditized", "somewhat_differentiated", "clearly_differentiated", "strong_moat_or_category_leader"]},
            {"field_id": "reporting_quality", "label": "How strong and reliable are your financial reporting and SaaS metrics?", "type": "radio", "required": True, "options": ["basic_or_messy", "decent_but_incomplete", "strong_and_board_ready", "very_strong_and_diligence_ready"]},
            {"field_id": "net_cash", "label": "What is your net cash or net debt position?", "type": "currency_signed", "required": True, "help_text": "Enter positive for net cash and negative for net debt."},
        ],
    },
]


def all_questions() -> list[dict]:
    return [q for section in SECTIONS for q in section["questions"]]
