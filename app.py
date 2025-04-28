import os
import re
import streamlit as st
import openai
import streamlit_mermaid as stmd

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Mermaid-from-Prompt", layout="wide")
st.title("🖍️ Prompt → Mermaid Diagram")

# ── Sidebar UI for prompt customization ─────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    orientation = st.selectbox(
        "Diagram direction", ["TB", "LR", "TD", "RL"], index=0,
        help="TB = top→bottom"
    )
    theme = st.selectbox(
        "Mermaid theme", ["default", "forest", "dark"], index=0
    )
    temperature = st.slider(
        "OpenAI temperature", 0.0, 1.0, 0.3, step=0.05
    )
    system_prompt = st.text_area(
        "System prompt",
        value=(
            "You are a Mermaid diagram expert. "
            "Turn the user's description into Mermaid nodes & edges. "
            "Use underscores (no spaces) in IDs. "
            "Return ONLY lines like `A_Node-->B_Node`, NO `graph` or fences."
        ),
        height=120
    )

# ── Main input ───────────────────────────────────────────────────────────────
workflow_desc = st.text_area(
    "📝 Describe your workflow",
    placeholder="e.g. CSV → ETL → Data warehouse → Dashboard…",
    height=180,
)
generate = st.button("Generate diagram", disabled=not workflow_desc.strip())

# ── OpenAI call ------------------------------------------------------------
def prompt_to_mermaid(desc: str, sys_msg: str, temp: float) -> str:
    openai.api_key = os.getenv("OPENAI_API_KEY")
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user",   "content": desc}
        ],
        temperature=temp,
    )
    return resp.choices[0].message.content

# ── Sanitization -----------------------------------------------------------
def clean_mermaid_body(raw: str) -> str:
    # 1) strip fences and any pre-existing graph lines
    cleaned = re.sub(r"```(?:mermaid)?", "", raw, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?mi)^graph\s+\w+.*$", "", cleaned)
    # 2) split, strip whitespace, drop blank lines
    lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
    # 3) keep only true Mermaid edge/node definitions (must contain --> or ---)
    body_lines = [
        ln for ln in lines
        if re.search(r"--?>", ln)
    ]
    return "\n".join(body_lines)

# ── Generate & render ───────────────────────────────────────────────────────
if generate:
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Set OPENAI_API_KEY in Streamlit secrets.")
    else:
        with st.spinner("Generating…"):
            raw = prompt_to_mermaid(workflow_desc, system_prompt, temperature)
            body = clean_mermaid_body(raw)

        mermaid_code = (
            f"%%{{init:{{'theme':'{theme}'}}}}%%\n"
            f"graph {orientation}\n"
            f"{body}"
        )

        st.subheader("Mermaid source")
        st.code(mermaid_code, language="mermaid")

        st.subheader("Diagram preview")
        stmd.st_mermaid(mermaid_code)
