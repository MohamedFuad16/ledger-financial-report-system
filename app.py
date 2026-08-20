"""
Legacy single-page Streamlit UI.

The Flask app in ``server.py`` plus ``static/`` is the primary interface; this
file is kept because the original experiment was run from it. It now delegates
to the same ``pipeline.run_pipeline`` as the API, so runs produced here use the
identical strategies, prompt and Pydantic validation.

Run with:  streamlit run app.py
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from api_client import GLMError, test_api_key
from extraction import STRATEGIES
from models import SchemaValidationError
from pipeline import (
    ensure_dirs,
    evidence_table,
    result_table,
    run_pipeline,
    safe_filename,
    store_pdf,
)
from prompts import SYSTEM_PROMPT
from settings import (
    CODING_BASE_URL,
    GENERAL_BASE_URL,
    current_settings,
    load_local_env,
    save_verified_settings,
)

ensure_dirs()
load_local_env()


def mask_key(key: str) -> str:
    if not key:
        return "Not configured"
    if len(key) <= 8:
        return "•" * 8
    return f"{key[:4]}…{key[-4:]}"


def persist_upload(uploaded_file) -> Path:
    """Write a Streamlit UploadedFile into uploads/ under a unique name."""
    temp = Path("uploads") / f".streamlit_{safe_filename(uploaded_file.name)}"
    temp.write_bytes(uploaded_file.getvalue())
    try:
        return store_pdf(temp, original_name=uploaded_file.name)
    finally:
        temp.unlink(missing_ok=True)


st.set_page_config(page_title="Annual Report → Asset Balance Sheet", page_icon="📄", layout="wide")

st.title("Annual Report → Asset-side Balance Sheet")
st.caption("PDF upload → text extraction → one LLM request → fixed 27-row schema, validated with Pydantic.")

# ---------- API SETTINGS ----------
st.subheader("1. API connection")

settings = current_settings()
endpoint_options = {
    "General Z.AI API": GENERAL_BASE_URL,
    "GLM Coding Plan endpoint": CODING_BASE_URL,
    "Custom base URL": "custom",
}

current_base = settings["base_url"]
if current_base == GENERAL_BASE_URL:
    default_endpoint_index = 0
elif current_base == CODING_BASE_URL:
    default_endpoint_index = 1
else:
    default_endpoint_index = 2

with st.container(border=True):
    col1, col2 = st.columns([1, 1])

    with col1:
        api_key_input = st.text_input(
            "Z.AI API key",
            type="password",
            placeholder=mask_key(settings["api_key"]),
            help="The key is tested first. It is written to the local .env file only after the test succeeds.",
        )
        model_input = st.text_input(
            "Model ID",
            value=settings["model"] or "glm-5.3",
            help="Use the exact model identifier exposed by your Z.AI account.",
        )

    with col2:
        endpoint_choice = st.selectbox("Endpoint", list(endpoint_options.keys()), index=default_endpoint_index)

        selected_base = endpoint_options[endpoint_choice]
        if selected_base == "custom":
            selected_base = st.text_input(
                "Custom base URL",
                value=current_base if current_base not in {GENERAL_BASE_URL, CODING_BASE_URL} else GENERAL_BASE_URL,
            ).strip()

        if endpoint_choice == "GLM Coding Plan endpoint":
            st.warning(
                "Z.AI documents the Coding Plan endpoint for supported coding tools/scenarios. "
                "A custom financial-extraction app may not be covered by Coding Plan quota. "
                "Use only if your account/plan explicitly permits this use."
            )

    enable_reasoning = st.toggle("Enable model reasoning", value=settings.get("enable_reasoning", True))
    temperature = st.slider("Temperature", 0.0, 1.0, float(settings.get("temperature", 0.1)), 0.05)

    if st.button("Test connection & save", use_container_width=True):
        candidate_key = api_key_input.strip() or settings["api_key"]

        if not candidate_key:
            st.error("Enter an API key before testing.")
        elif not model_input.strip():
            st.error("Enter a model ID.")
        elif not selected_base:
            st.error("Enter a base URL.")
        else:
            with st.spinner("Testing API key, endpoint, and model…"):
                ok, message, elapsed = test_api_key(
                    api_key=candidate_key,
                    model=model_input.strip(),
                    base_url=selected_base,
                    # Without this the probe defaults to the OpenAI-style
                    # "reasoning" parameter, which Z.AI does not accept.
                    provider=settings.get("provider", ""),
                )

            if ok:
                save_verified_settings(
                    api_key=candidate_key,
                    model=model_input.strip(),
                    base_url=selected_base,
                    enable_reasoning=enable_reasoning,
                    temperature=temperature,
                )
                st.session_state["api_verified"] = True
                st.success(f"Connection verified in {elapsed:.2f}s. Settings saved locally to .env.")
            else:
                st.session_state["api_verified"] = False
                st.error(f"Connection test failed: {message}")

settings = current_settings()
has_saved_key = bool(settings["api_key"])

if has_saved_key:
    st.caption(f"Saved configuration: {mask_key(settings['api_key'])} · {settings['model']} · {settings['base_url']}")
else:
    st.info("Configure and verify the API before running the experiment.")

# ---------- PDF EXPERIMENT ----------
st.subheader("2. Annual Report")

strategy_labels = {s.key: s.label for s in STRATEGIES.values()}
strategy_key = st.selectbox(
    "Strategy",
    list(strategy_labels.keys()),
    format_func=lambda k: strategy_labels[k],
)

fiscal_year = st.text_input(
    "Target fiscal year (hint only — the model still detects it itself)",
    value="",
    help="Leave blank to rely purely on detection.",
)

uploaded_file = st.file_uploader("Drag and drop the Annual Report PDF", type=["pdf"], accept_multiple_files=False)

if uploaded_file is not None:
    st.success(f"{uploaded_file.name} · {uploaded_file.size / 1024 / 1024:.2f} MB")

    if st.button("Run extraction", type="primary", use_container_width=True, disabled=not has_saved_key):
        try:
            settings = current_settings()
            pdf_path = persist_upload(uploaded_file)

            with st.status("Running extraction…", expanded=True) as status:
                prediction = run_pipeline(
                    pdf_path=pdf_path,
                    settings=settings,
                    strategy_key=strategy_key,
                    system_prompt=SYSTEM_PROMPT,
                    fiscal_year_hint=fiscal_year,
                    enable_reasoning=settings.get("enable_reasoning", True),
                    temperature=settings.get("temperature", 0.1),
                    display_name=uploaded_file.name,
                    on_progress=lambda update: st.write(update.get("message", "")),
                )
                status.update(
                    label=f"Completed in {prediction['api_elapsed_seconds']:.1f}s",
                    state="complete",
                    expanded=False,
                )

            for warning in prediction["warnings"]:
                st.warning(warning)

            st.subheader("3. Model output")
            st.caption(
                f"Run {prediction['run_id']} · {prediction['strategy_label']} · "
                f"detected FY {prediction['detected_fiscal_year'] or '—'} · "
                f"{prediction['page_count']} pages · ~{prediction['approx_input_tokens']:,} input tokens"
            )

            rows = prediction["rows"]
            df = pd.DataFrame(result_table(rows))
            st.dataframe(df, use_container_width=True, hide_index=True)

            metrics = prediction["metrics"]
            if metrics["has_golden"]:
                col_a, col_b = st.columns(2)
                col_a.metric(
                    "Exact accuracy",
                    f"{metrics['accuracy']:.1f}%",
                    f"{metrics['exact_matches']} / {metrics['total_compared']} items",
                )
                col_b.metric(
                    "Coverage",
                    f"{metrics['coverage']:.1f}%",
                    f"{metrics['filled_fields']} / {prediction['schema_rows']} fields",
                )
            else:
                st.info(
                    f"No golden answers stored for FY {prediction['fiscal_year'] or '—'}; "
                    "coverage is reported but accuracy cannot be scored."
                )

            with st.expander("Evidence returned by the model"):
                st.dataframe(pd.DataFrame(evidence_table(rows)), use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "Download output CSV",
                    data=df.to_csv(index=False).encode("utf-8"),
                    file_name=f"{prediction['run_id']}_prediction.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with col2:
                st.download_button(
                    "Download output JSON",
                    data=json.dumps(prediction, ensure_ascii=False, indent=2),
                    file_name=f"{prediction['run_id']}_prediction.json",
                    mime="application/json",
                    use_container_width=True,
                )

            st.caption(
                f"Local run artifacts: runs/{prediction['run_id']}/request.json, "
                f"raw_response.json, prediction.json"
            )

        except (GLMError, SchemaValidationError, ValueError, RuntimeError) as exc:
            st.error(str(exc))
            st.caption("Any artifacts created before the failure are preserved under runs/.")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Unexpected error: {exc}")
