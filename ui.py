from __future__ import annotations

import streamlit as st

from helpers import DISCLAIMER, money, multiple
from question_config import SECTIONS
from valuation_engine import ValidationError, run_valuation


def _default_for(question: dict):
    if question["type"] == "radio":
        return question["options"][0]
    return 0.0


def _render_question(question: dict, value):
    q_type = question["type"]
    kwargs = {"help": question.get("help_text")}
    if q_type in {"currency", "percentage", "number", "currency_signed"}:
        return st.number_input(
            question["label"],
            value=float(value),
            step=1.0,
            format="%.2f",
            **kwargs,
        )
    if q_type == "radio":
        options = question["options"]
        idx = options.index(value) if value in options else 0
        return st.radio(question["label"], options=options, index=idx, horizontal=False, **kwargs)
    raise ValueError(f"Unsupported input type {q_type}")


def render_app() -> None:
    st.set_page_config(page_title="SaaS Valuation Quiz", layout="wide")
    if "page" not in st.session_state:
        st.session_state.page = -1
    if "answers" not in st.session_state:
        st.session_state.answers = {q["field_id"]: _default_for(q) for section in SECTIONS for q in section["questions"]}

    if st.session_state.page == -1:
        st.title("SaaS Valuation Quiz App")
        st.write(
            "This tool estimates an approximate private-market SaaS valuation range based on common SaaS transaction drivers such as growth, retention, margins, efficiency, concentration, and transferability."
        )
        st.info("Estimated completion time: 5–8 minutes")
        st.caption(DISCLAIMER)
        if st.button("Start"):
            st.session_state.page = 0
            st.rerun()
        return

    if st.session_state.page < len(SECTIONS):
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
            st.session_state.page = max(0, st.session_state.page - 1)
            st.rerun()
        if nxt:
            st.session_state.answers.update(new_answers)
            st.session_state.page += 1
            st.rerun()
        return

    st.title("Valuation Results")
    try:
        result = run_valuation(st.session_state.answers)
    except ValidationError as exc:
        st.error(str(exc))
        if st.button("Back to inputs"):
            st.session_state.page = 0
            st.rerun()
        return

    val = result["valuation"]
    conf = result["confidence"]
    cards = [
        ("Low Enterprise Value", money(val["low_ev"])),
        ("Base Enterprise Value", money(val["base_ev"])),
        ("High Enterprise Value", money(val["high_ev"])),
        ("Low Equity Value", money(val["low_equity_value"])),
        ("Base Equity Value", money(val["base_equity_value"])),
        ("High Equity Value", money(val["high_equity_value"])),
        ("Implied ARR Multiple", multiple(val["final_arr_multiple"])),
        ("Confidence Rating", f"{conf['label']} ({conf['score']}/100)"),
    ]
    cols = st.columns(4)
    for idx, (label, value) in enumerate(cards):
        cols[idx % 4].metric(label, value)

    if result["warnings"]:
        for warning in result["warnings"]:
            st.warning(warning)

    left, right = st.columns(2)
    with left:
        st.subheader("Top positive drivers")
        for item in result["drivers"]["positive"]:
            st.write(f"• {item}")
    with right:
        st.subheader("Top negative drivers")
        for item in result["drivers"]["negative"]:
            st.write(f"• {item}")

    st.subheader("Subscores")
    for key, score in result["subscores"].items():
        st.write(f"**{key.replace('_', ' ').title()}**")
        st.progress(score / 100)
        st.caption(f"{score}/100")

    st.subheader("Recommended actions")
    for rec in result["recommendations"]:
        st.write(f"• {rec}")

    st.caption(DISCLAIMER)
    if st.button("Back to edit inputs"):
        st.session_state.page = 0
        st.rerun()
