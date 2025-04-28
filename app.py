import os, subprocess, tempfile, difflib
import streamlit as st
import openai
import streamlit_mermaid as stmd
import streamlit.components.v1 as components

# ── Config & state ──────────────────────────────────────────────────────────
st.set_page_config(page_title="Mermaid-Workflow Pro", layout="wide")
if "last_ai" not in st.session_state:
    st.session_state.last_ai = ""
if "last_edit" not in st.session_state:
    st.session_state.last_edit = ""

# ── Sidebar: settings & templates ────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings & Templates")

    # Live preview toggle
    live = st.checkbox("🔄 Live preview", value=False)

    orientation = st.selectbox("Direction", ["TB","LR","TD","RL"], index=0)
    theme       = st.selectbox("Theme", ["default","forest","dark"], index=0)
    temp        = st.slider("Temperature", 0.0, 1.0, 0.3, 0.05)

    # Templates & Quick-start
    st.markdown("#### 🚀 Quick-start prompts")
    templates = {
        "DevOps Pipeline": "A CI system detects a Git push → builds artifacts → runs tests → deploys to prod → alerts team.",
        "SaaS Onboarding": "User signs up → onboarding email → tutorial walkthrough → completes first action → feedback survey.",
        "Investment Close": "Client meets team → initial pitch → term negotiation → LOI → due diligence → signing → post-deal integration."
    }
    choice = st.selectbox("Pick a template", [""] + list(templates.keys()), index=0)
    if choice:
        st.session_state.workflow_desc = templates[choice]

    st.markdown("***")

    # System prompt
    system_prompt = st.text_area(
        "System prompt",
        value=(
            "You are a Mermaid diagram expert. "
            "Turn the user's description into a reflective, detailed end-to-end workflow. "
            "Include nodes, branches, notes, subgraphs, classDefs—whatever clarifies the process. "
            "Use underscores (no spaces) in IDs. "
            "Return only valid Mermaid code body—no fences or commentary."
        ),
        height=140,
    )

# ── Main layout ──────────────────────────────────────────────────────────────
col1, col2 = st.columns([1,1])

with col1:
    st.subheader("📝 Describe your workflow")
    workflow_desc = st.text_area(
        "“Enter any process…”",
        key="workflow_desc",
        height=200,
        value=st.session_state.get("workflow_desc","")
    )

    # Generate logic
    def do_generate():
        openai.api_key = os.getenv("OPENAI_API_KEY")
        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":system_prompt},
                {"role":"user","content":workflow_desc}
            ],
            temperature=temp,
        )
        st.session_state.last_ai = resp.choices[0].message.content
        st.session_state.last_edit = st.session_state.last_ai  # seed editor

    if live:
        st.experimental_memo.clear()  # clear cache so new run
        do_generate()
    else:
        if st.button("Generate diagram"):
            do_generate()

    # Editable source + diff
    if st.session_state.last_ai:
        st.markdown("#### ✍️ Edit Mermaid source")
        edited = st.text_area(
            "You can tweak the diagram code below:",
            key="edited",
            height=200,
            value=st.session_state.last_edit
        )
        st.session_state.last_edit = edited

        # Show diff
        if edited != st.session_state.last_ai:
            diff_html = difflib.HtmlDiff().make_table(
                st.session_state.last_ai.splitlines(),
                edited.splitlines(),
                context=True, numlines=1
            )
            st.markdown("#### 🔍 Changes vs AI output")
            components.html(diff_html, height=200, scrolling=True)

with col2:
    st.subheader("📊 Diagram preview")
    if st.session_state.last_edit:
        mermaid_code = (
            f"%%{{init:{{'theme':'{theme}'}}}}%%\n"
            f"graph {orientation}\n"
            f"{st.session_state.last_edit}"
        )
        stmd.st_mermaid(mermaid_code)

        # ── Export buttons ────────────────────────────────────────────────
        st.markdown("#### 📥 Export & Embed")
        # 1) Copy raw code
        st.code(mermaid_code, language="mermaid")
        st.button("Copy code to clipboard", on_click=components.html,
                  args=(f"<script>navigator.clipboard.writeText(`{mermaid_code}`);</script>",),)

        # 2) Download SVG via mermaid-cli (must have mmdc installed)
        def export_svg(code: str):
            with tempfile.NamedTemporaryFile("w", suffix=".mmd", delete=False) as f:
                f.write(code); f.flush()
                svg_path = f.name.replace(".mmd", ".svg")
                subprocess.run(["mmdc","-i",f.name,"-o",svg_path], check=True)
            return open(svg_path, "rb").read()

        try:
            svg = export_svg(mermaid_code)
            st.download_button("⬇️ SVG", svg, "diagram.svg", mime="image/svg+xml")
            # similarly PNG
            # png = export_png(mermaid_code)
            # st.download_button("⬇️ PNG", png, "diagram.png", mime="image/png")
        except Exception:
            st.info("Install `mmdc` CLI in your env to enable SVG exports.")

        # 3) Embed snippet
        embed_snippet = (
            f'<div class="mermaid">\n{mermaid_code}\n</div>\n'
            '<script src="https://unpkg.com/mermaid/dist/mermaid.min.js"></script>\n'
            '<script>mermaid.initialize({startOnLoad:true});</script>'
        )
        st.text_area("Copy HTML embed", value=embed_snippet, height=150)

