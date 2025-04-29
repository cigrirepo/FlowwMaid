import os
import re
import streamlit as st
import openai
import streamlit_mermaid as stmd

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Mermaid-from-Prompt", layout="wide")
st.title("🖍️ Flowwmaid: Generate Detailed Mermaid Diagrams")

# ── Sidebar UI ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    orientation = st.selectbox(
        "Diagram Direction",
        ["Top-To-Bottom", "Left-to-Right", "Right-to-Left"],
        index=0,
        help="Choose the formatting of your chart."
    )
    theme = st.selectbox(
        "Mermaid Diagram Theme", ["Default", "Forest", "Dark"], index=0
    )
    temperature = st.slider("Chart Complexity", 0.0, 1.0, 0.3, step=0.05)
    system_prompt = st.text_area(
        "System Prompt",
        value=(
            "You are a Mermaid diagram expert. Turn the user's description "
            "into a reflective, detailed end-to-end workflow. Include all nodes, "
            "conditional branches, notes, subgraphs, classDefs—whatever makes it clear. "
            "Use underscores in multi-word IDs (no spaces). Return ONLY valid "
            "Mermaid code body—no markdown fences or extra commentary."
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

# ── OpenAI call ─────────────────────────────────────────────────────────────
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

# ── Sanitization ───────────────────────────────────────────────────────────
def clean_mermaid_body(raw: str) -> str:
    cleaned = re.sub(r"```(?:mermaid)?", "", raw, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?mi)^ *(graph|flowchart)\s+\S+.*$", "", cleaned)
    lines = [ln.rstrip() for ln in cleaned.splitlines() if ln.strip()]
    kept = []
    for ln in lines:
        if re.match(r"^%%\{.*\}%%$", ln):
            kept.append(ln)
        elif re.match(r"^subgraph\s+\w+", ln):
            kept.append(ln)
        elif re.match(r"^end$", ln, flags=re.IGNORECASE):
            kept.append(ln)
        elif re.match(r"^classDef\s+\w+", ln):
            kept.append(ln)
        elif re.match(r"^note\s+(left|right|top|bottom)\s+of\s+\w+", ln):
            kept.append(ln)
        elif "-->" in ln or "->" in ln:
            kept.append(ln)
        elif re.search(r"\[.*\]", ln):
            kept.append(ln)
    return "\n".join(kept)

# ── Generate & render ───────────────────────────────────────────────────────
if generate:
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Set OPENAI_API_KEY in Streamlit secrets.")
    else:
        with st.spinner("🧠 Generating detailed diagram…"):
            raw_output = prompt_to_mermaid(workflow_desc, system_prompt, temperature)
            body       = clean_mermaid_body(raw_output)

        # build the spelled-out, lowercase direction:
        dir_form   = orientation.lower()            # "Top-To-Bottom" → "top-to-bottom"
        theme_form = theme.lower()                  # "Default"       → "default"

        # now use 'flowchart' instead of 'graph', and proper JSON init:
        mermaid_code = (
            f"%%{{init: {{\"theme\":\"{theme_form}\"}}}}%%\n"
            f"flowchart {dir_form}\n"
            f"{body}"
        )

        st.subheader("Mermaid Diagram Code")
        st.code(mermaid_code, language="mermaid")

        st.subheader("Workflow Diagram")
        stmd.st_mermaid(mermaid_code)
