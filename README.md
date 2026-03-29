# SaaS Valuation Quiz App

A Streamlit MVP that collects 20 SaaS business inputs and returns an indicative private-market valuation range with explainable drivers.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Run tests

```bash
pytest -q
```

## Project structure

- `app.py`: app entrypoint
- `ui.py`: Streamlit UI flow and result dashboard
- `valuation_engine.py`: valuation logic, validation, warnings, scoring
- `question_config.py`: centralized question metadata
- `helpers.py`: shared formatting and utility functions
- `tests/`: engine, validation, and output tests (10+ cases)
