import os
import streamlit as st
import openai
import streamlit_mermaid as stmd            # community component
import streamlit.components.v1 as components

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Mermaid-from-Prompt", layout="wide")
st.title("🖍️ Prompt → Mermaid Diagram")

# ── Sidebar UI for prompt customization ─────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    orientation = st.selectbox(
        "Diagram direction",
        ["TB","LR","TD","RL"],
        index=0,
        help="TB = top→bottom (Notion style)."
    )

    theme = st.selectbox(
        "Mermaid theme",
        ["default","forest","dark"],
        index=0,
        help="Controls colors/style of the chart."
    )

    temperature = st.slider(
        "OpenAI temperature",
        0.0, 1.0, 0.3, step=0.05,
        help="Higher = more creative edges/labels."
    )

    system_prompt = st.text_area(
        "System prompt",
        value=(
            "You are a mermaid diagram expert. "
            "Turn the user's description into a set of Mermaid nodes and edges. "
            "Return **only** the body (e.g. `A-->B` lines), **no** `graph` directive, no fences."
        ),
        height=100
    )

# ── Main input ───────────────────────────────────────────────────────────────
workflow_desc = st.text_area(
    "📝 Describe your workflow",
    placeholder="e.g. Data engineer ingests CSV → triggers ETL → loads to warehouse → BI dashboard refreshes…",
    height=180,
)
generate = st.button("Generate diagram", disabled=not workflow_desc)

# ── OpenAI call ─────────────────────────────────────────────────────────────
def prompt_to_mermaid(desc: str, sys_msg: str, temp: float) -> str:
    resp = openai.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[
            {"role":"system", "content": sys_msg},
            {"role":"user",   "content": desc}
        ],
        temperature=temp,
    )
    return resp.choices[0].message.content.strip()

# ── Generate & render ───────────────────────────────────────────────────────
if generate:
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Please set your OPENAI_API_KEY in Streamlit secrets.")
    else:
        openai.api_key = os.getenv("OPENAI_API_KEY")

        with st.spinner("🧠 Thinking…"):
            body = prompt_to_mermaid(workflow_desc, system_prompt, temperature)

        # prefix with theme+graph directive
        mermaid_code = (
            f"%%{{init: {{'theme':'{theme}'}}}}%%\n"
            f"graph {orientation}\n"
            f"{body}"
        )

        st.subheader("Mermaid source")
        st.code(mermaid_code, language="mermaid")

        st.subheader("📊 Diagram (streamlit-mermaid)")
        stmd.st_mermaid(mermaid_code)

        st.subheader("📊 Diagram (Notion-style embed)")
        components.html(f"""
            <div class="mermaid">
            {mermaid_code}
            </div>
            <script src="https://unpkg.com/mermaid/dist/mermaid.min.js"></script>
            <script>mermaid.initialize({{startOnLoad:true}});</script>
        """, height=450)
