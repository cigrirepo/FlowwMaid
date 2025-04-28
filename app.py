import os
import re
import streamlit as st
import openai
import streamlit_mermaid as stmd

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Mermaid-from-Prompt", layout="wide")
st.title("🖍️ Prompt → Detailed Mermaid Diagram")

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
            "Turn the user's description into a reflective, detailed end-to-end workflow. "
            "Include all relevant nodes, conditional branches, notes or subgraphs you deem necessary. "
            "Use underscores in multi-word IDs (no spaces). "
            "Return ONLY valid Mermaid code body—no markdown fences, no extra commentary outside the diagram."
        ),
        height=140
    )

# ── Main input ───────────────────────────────────────────────────────────────
workflow_desc = st.text_area(
    "📝 Describe your workflow in detail",
    placeholder="e.g. ‘A deals team sources mandate → … → post-deal integration and reporting.’",
    height=200,
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
    # 1) Strip triple-backtick fences (```mermaid or ```), case-insensitive
    cleaned = re.sub(r"```(?:mermaid)?", "", raw, flags=re.IGNORECASE)
    # 2) Remove any existing 'graph <dir>' lines so we can re-inject ours
    cleaned = re.sub(r"(?mi)^graph\s+\w+.*$", "", cleaned)
    # 3) Trim and drop blank lines but keep everything else
    lines = [ln.rstrip() for ln in cleaned.splitlines() if ln.strip()]
    return "\n".join(lines)

# ── Generate & render ───────────────────────────────────────────────────────
if generate:
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Set OPENAI_API_KEY in Streamlit secrets.")
    else:
        with st.spinner("Generating detailed diagram…"):
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
