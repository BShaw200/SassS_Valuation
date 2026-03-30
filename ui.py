from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from helpers import DISCLAIMER, money, multiple
from question_config import SECTIONS, all_questions
from valuation_engine import ValidationError, run_valuation

INTRO_PAGE = "intro"
RESULTS_PAGE = "results"
DASHBOARD_PAGE = "dashboard"


def _default_for(question: dict):
    if "default" in question:
        return question["default"]
    if question["type"] == "radio":
        return question["options"][0]
    return 0.0


def _option_label(question: dict, value: str) -> str:
    return question.get("option_labels", {}).get(value, value.replace("_", " ").title())


def _context_line(question: dict, original_value: object | None = None) -> str:
    parts: list[str] = []
    if question.get("unit"):
        parts.append(f"Unit: {question['unit']}.")
    if original_value is not None:
        parts.append(f"Original answer: {_format_answer(question, original_value)}.")
    if question.get("context_text"):
        parts.append(question["context_text"])
    return " ".join(parts)


def _format_answer(question: dict, value: object) -> str:
    q_type = question["type"]
    if q_type in {"currency", "currency_signed"}:
        return money(float(value))
    if q_type == "percentage":
        return f"{float(value):.1f}%"
    if q_type == "number":
        unit = question.get("unit", "")
        unit_suffix = f" {unit}" if unit else ""
        return f"{float(value):.0f}{unit_suffix}"
    if q_type == "radio":
        return _option_label(question, str(value))
    return str(value)


def _render_question(question: dict, value):
    q_type = question["type"]
    common_kwargs = {"help": question.get("help_text")}

    if q_type in {"currency", "percentage", "number", "currency_signed"}:
        kwargs = dict(common_kwargs)
        if "min" in question:
            kwargs["min_value"] = float(question["min"])
        if "max" in question:
            kwargs["max_value"] = float(question["max"])
        kwargs["step"] = float(question.get("step", 1.0))
        if q_type == "percentage":
            kwargs["format"] = "%.1f"
        elif q_type == "number" and float(question.get("step", 1.0)) < 1:
            kwargs["format"] = "%.1f"
        else:
            kwargs["format"] = "%.0f"
        answer = st.number_input(question["label"], value=float(value), **kwargs)
        st.caption(_context_line(question))
        return answer

    if q_type == "radio":
        options = question["options"]
        idx = options.index(value) if value in options else 0
        answer = st.radio(
            question["label"],
            options=options,
            index=idx,
            format_func=lambda option: _option_label(question, option),
            horizontal=False,
            help=question.get("help_text"),
        )
        st.caption(_context_line(question))
        return answer

    raise ValueError(f"Unsupported input type {q_type}")


def _currency_slider_step(anchor: float, configured_step: float | None) -> float:
    if configured_step is not None:
        return configured_step
    if anchor >= 10_000_000:
        return 100_000.0
    if anchor >= 1_000_000:
        return 25_000.0
    if anchor >= 100_000:
        return 5_000.0
    return 1_000.0


def _round_up(value: float, step: float) -> float:
    if step <= 0:
        return value
    return ((value + step - 1) // step) * step


def _slider_bounds(question: dict, current_value: float, baseline_value: float) -> tuple[float, float, float]:
    q_type = question["type"]
    configured_step = float(question.get("step", 1.0))

    if q_type == "percentage":
        return float(question.get("min", 0.0)), float(question.get("max", 100.0)), configured_step

    if q_type == "number":
        return float(question.get("min", 0.0)), float(question.get("max", max(current_value, baseline_value))), configured_step

    anchor = max(abs(current_value), abs(baseline_value), abs(float(question.get("default", 0.0))), 1.0)
    step = _currency_slider_step(anchor, configured_step)
    if q_type == "currency_signed":
        span = max(anchor * 2, step * 20)
        return -_round_up(span, step), _round_up(span, step), step

    max_value = max(anchor * 2, step * 20)
    return float(question.get("min", 0.0)), _round_up(max_value, step), step


def _render_dashboard_control(question: dict, baseline_value):
    widget_key = f"dashboard_{question['field_id']}"
    q_type = question["type"]

    if widget_key not in st.session_state:
        st.session_state[widget_key] = baseline_value

    if q_type == "radio":
        if st.session_state[widget_key] not in question["options"]:
            st.session_state[widget_key] = baseline_value
        st.select_slider(
            question["label"],
            options=question["options"],
            key=widget_key,
            format_func=lambda option: _option_label(question, option),
        )
        st.caption(_context_line(question, baseline_value))
        return

    slider_state_key = f"{widget_key}_slider"
    current_value = float(st.session_state.get(slider_state_key, st.session_state[widget_key]))
    min_value, max_value, step = _slider_bounds(question, current_value, float(baseline_value))
    clamped_value = min(max(current_value, min_value), max_value)
    st.session_state[widget_key] = clamped_value

    integral_slider = all(float(value).is_integer() for value in (min_value, max_value, step, clamped_value))
    st.session_state[slider_state_key] = int(clamped_value) if integral_slider else float(clamped_value)
    slider_kwargs = {
        "label": question["label"],
        "min_value": int(min_value) if integral_slider else float(min_value),
        "max_value": int(max_value) if integral_slider else float(max_value),
        "value": int(clamped_value) if integral_slider else float(clamped_value),
        "step": int(step) if integral_slider else float(step),
        "key": slider_state_key,
    }
    st.session_state[widget_key] = st.slider(**slider_kwargs)
    st.caption(_context_line(question, baseline_value))


def _read_dashboard_answers(base_answers: dict[str, object]) -> dict[str, object]:
    answers: dict[str, object] = {}
    for question in all_questions():
        widget_key = f"dashboard_{question['field_id']}"
        answers[question["field_id"]] = st.session_state.get(widget_key, base_answers[question["field_id"]])
    return answers


def _load_dashboard_state(source_answers: dict[str, object]) -> None:
    baseline_answers = {question["field_id"]: source_answers[question["field_id"]] for question in all_questions()}
    st.session_state.dashboard_base_answers = dict(baseline_answers)
    st.session_state.dashboard_answers = dict(baseline_answers)
    for question in all_questions():
        widget_key = f"dashboard_{question['field_id']}"
        st.session_state[widget_key] = baseline_answers[question["field_id"]]
        st.session_state[f"{widget_key}_slider"] = baseline_answers[question["field_id"]]


def _waterfall_chart(steps: list[dict]) -> alt.Chart:
    step_order = [step["label"] for step in steps]
    dataframe = pd.DataFrame(
        [
            {
                "label": step["label"],
                "kind": step["kind"],
                "start": min(step["start"], step["end"]),
                "end": max(step["start"], step["end"]),
                "delta": step["delta"],
                "tooltip_delta": f"{step['delta']:+.2f}x" if step["kind"] != "total" else f"{step['end']:.2f}x",
                "value_label": f"{step['delta']:+.2f}x" if step["kind"] != "total" else f"{step['end']:.2f}x",
            }
            for step in steps
        ]
    )

    base = alt.Chart(dataframe).encode(
        x=alt.X("label:N", sort=step_order, axis=alt.Axis(labelAngle=-25, title=None)),
        y=alt.Y("start:Q", title="ARR multiple (x)"),
        y2="end:Q",
        color=alt.Color(
            "kind:N",
            legend=None,
            scale=alt.Scale(
                domain=["positive", "negative", "total"],
                range=["#0f766e", "#b91c1c", "#1d4ed8"],
            ),
        ),
        tooltip=[
            alt.Tooltip("label:N", title="Component"),
            alt.Tooltip("tooltip_delta:N", title="Impact"),
        ],
    )

    bars = base.mark_bar(size=42)
    labels = base.mark_text(dy=-8, color="#111827").encode(text="value_label:N", y="end:Q")
    return (bars + labels).properties(height=420)


def _render_results() -> None:
    st.title("Valuation Results")
    try:
        result = run_valuation(st.session_state.answers)
    except ValidationError as exc:
        st.error(str(exc))
        if st.button("Back to inputs"):
            st.session_state.page = 0
            st.rerun()
        return

    valuation = result["valuation"]
    confidence = result["confidence"]
    metric_cards = [
        ("Base ARR Multiple", multiple(valuation["base_arr_multiple"]), None),
        (
            "Implied ARR Multiple",
            multiple(valuation["final_arr_multiple"]),
            f"{valuation['final_arr_multiple'] - valuation['base_arr_multiple']:+.2f}x vs base",
        ),
        ("Base Enterprise Value", money(valuation["base_ev"]), None),
        ("Enterprise Value Range", f"{money(valuation['low_ev'])} to {money(valuation['high_ev'])}", None),
    ]

    cols = st.columns(len(metric_cards))
    for idx, (label, value, delta) in enumerate(metric_cards):
        cols[idx].metric(label, value, delta=delta)

    st.caption(
        f"Confidence: {confidence['label']} ({confidence['score']}/100). "
        f"The base ARR multiple is {valuation['base_arr_multiple']:.2f}x before company-specific adjustments."
    )

    if result["warnings"]:
        for warning in result["warnings"]:
            st.warning(warning)

    left, right = st.columns([3, 2])
    with left:
        st.subheader("ARR Multiple Waterfall")
        st.caption("Positive drivers are applied first, followed by the negative drivers, to bridge from the base multiple to the implied multiple.")
        st.altair_chart(_waterfall_chart(result["waterfall_steps"]), use_container_width=True)
    with right:
        st.subheader("Key drivers")
        st.write("**Top positive drivers**")
        if result["drivers"]["positive"]:
            for item in result["drivers"]["positive"]:
                st.write(f"- {item}")
        else:
            st.write("No material positive adjustments.")

        st.write("**Top negative drivers**")
        if result["drivers"]["negative"]:
            for item in result["drivers"]["negative"]:
                st.write(f"- {item}")
        else:
            st.write("No material negative adjustments.")

    st.subheader("Subscores")
    for key, score in result["subscores"].items():
        detail = result["subscore_details"][key]
        score_col, writeup_col = st.columns([1, 2])
        with score_col:
            st.write(f"**{detail['title']}**")
            st.progress(score / 100)
            st.caption(f"{score}/100")
        with writeup_col:
            st.write(detail["writeup"])

    st.subheader("Recommended actions")
    for recommendation in result["recommendations"]:
        st.write(f"- {recommendation}")

    st.caption(DISCLAIMER)
    action_col, edit_col = st.columns(2)
    if action_col.button("Open Dashboard"):
        _load_dashboard_state(st.session_state.answers)
        st.session_state.page = DASHBOARD_PAGE
        st.rerun()
    if edit_col.button("Back to edit inputs"):
        st.session_state.page = 0
        st.rerun()


def _render_dashboard() -> None:
    if "dashboard_base_answers" not in st.session_state:
        _load_dashboard_state(st.session_state.answers)

    base_answers = st.session_state.dashboard_base_answers
    scenario_answers = _read_dashboard_answers(base_answers)
    st.session_state.dashboard_answers = dict(scenario_answers)

    st.title("Dashboard")
    st.write(
        "Adjust the sliders below to see how changes to the original questionnaire answers can add to or detract from the SaaS valuation."
    )

    control_col, reset_col, edit_col = st.columns(3)
    if control_col.button("Back to results"):
        st.session_state.page = RESULTS_PAGE
        st.rerun()
    if reset_col.button("Reset scenario"):
        _load_dashboard_state(base_answers)
        st.rerun()
    if edit_col.button("Back to edit inputs"):
        st.session_state.page = 0
        st.rerun()

    base_result = run_valuation(base_answers)
    scenario_error: str | None = None
    try:
        scenario_result = run_valuation(scenario_answers)
    except ValidationError as exc:
        scenario_result = None
        scenario_error = str(exc)

    if scenario_result is not None:
        scenario_value = scenario_result["valuation"]
        base_value = base_result["valuation"]
        metric_cols = st.columns(3)
        metric_cols[0].metric(
            "Implied ARR Multiple",
            multiple(scenario_value["final_arr_multiple"]),
            delta=f"{scenario_value['final_arr_multiple'] - base_value['final_arr_multiple']:+.2f}x vs original",
        )
        metric_cols[1].metric(
            "Enterprise Value",
            money(scenario_value["base_ev"]),
            delta=f"{money(scenario_value['base_ev'] - base_value['base_ev'])} vs original",
        )
        metric_cols[2].metric(
            "Enterprise Value Range",
            f"{money(scenario_value['low_ev'])} to {money(scenario_value['high_ev'])}",
            delta=None,
        )
        st.caption(
            f"Original baseline: {multiple(base_value['final_arr_multiple'])} and {money(base_value['base_ev'])} enterprise value."
        )
    else:
        st.error(scenario_error)
        st.caption("Bring the sliders back into a valid range to resume scenario modeling.")

    for section_idx, section in enumerate(SECTIONS):
        with st.expander(section["title"], expanded=section_idx == 0):
            for question in section["questions"]:
                _render_dashboard_control(question, base_answers[question["field_id"]])

    st.session_state.dashboard_answers = _read_dashboard_answers(base_answers)


def render_app() -> None:
    st.set_page_config(page_title="SaaS Valuation Quiz", layout="wide")

    if "page" not in st.session_state:
        st.session_state.page = INTRO_PAGE
    if "answers" not in st.session_state:
        st.session_state.answers = {
            question["field_id"]: _default_for(question)
            for section in SECTIONS
            for question in section["questions"]
        }

    if st.session_state.page == INTRO_PAGE:
        st.title("SaaS Valuation Quiz App")
        st.write(
            "This tool estimates an approximate private-market SaaS valuation range based on common SaaS transaction drivers such as growth, retention, margins, efficiency, concentration, and transferability."
        )
        st.info("Estimated completion time: 5-8 minutes")
        st.caption(DISCLAIMER)
        if st.button("Start"):
            st.session_state.page = 0
            st.rerun()
        return

    if isinstance(st.session_state.page, int) and st.session_state.page < len(SECTIONS):
        section = SECTIONS[st.session_state.page]
        st.progress((st.session_state.page + 1) / (len(SECTIONS) + 1))
        st.header(section["title"])

        with st.form(f"section_{st.session_state.page}"):
            new_answers = {}
            for question in section["questions"]:
                field = question["field_id"]
                new_answers[field] = _render_question(question, st.session_state.answers[field])

            back_col, next_col = st.columns(2)
            back = back_col.form_submit_button("Back", disabled=st.session_state.page == 0)
            next_label = "See results" if st.session_state.page == len(SECTIONS) - 1 else "Next"
            nxt = next_col.form_submit_button(next_label)

        if back:
            st.session_state.answers.update(new_answers)
            st.session_state.page = max(0, st.session_state.page - 1)
            st.rerun()
        if nxt:
            st.session_state.answers.update(new_answers)
            if st.session_state.page == len(SECTIONS) - 1:
                st.session_state.page = RESULTS_PAGE
            else:
                st.session_state.page += 1
            st.rerun()
        return

    if st.session_state.page == RESULTS_PAGE:
        _render_results()
        return

    if st.session_state.page == DASHBOARD_PAGE:
        _render_dashboard()
        return

    st.session_state.page = RESULTS_PAGE
    st.rerun()
