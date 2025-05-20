import os
import re
import json
import uuid
import base64
from datetime import datetime
import streamlit as st
import openai
import streamlit_mermaid as stmd
from io import BytesIO

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Flowwmaid: Streamline Workflows", layout="wide")

# Initialize session state for workflow history
if 'workflow_history' not in st.session_state:
    st.session_state.workflow_history = []
if 'current_workflow_id' not in st.session_state:
    st.session_state.current_workflow_id = None

# ── Sidebar UI for prompt customization ─────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Basic settings
    orientation = st.selectbox(
        "Diagram Direction", ["TB", "LR", "TD", "RL"], index=0,
        help="TB = top→bottom, LR = left→right, etc."
    )
    theme = st.selectbox(
        "Workflow Diagram Color Scheme", ["default", "forest", "dark", "neutral"], index=0
    )
    temperature = st.slider(
        "Chart Complexity", 0.0, 1.0, 0.3, step=0.05,
        help="Higher values create more creative but potentially less structured diagrams"
    )
    
    # Advanced settings
    with st.expander("Advanced Settings"):
        model = st.selectbox(
            "Model", 
            ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
            index=0,
            help="More powerful models may create better diagrams but cost more"
        )
        
        system_prompt = st.text_area(
            "Context Prompt",
            value=(
                "You are a Mermaid diagram expert. "
                "Turn the user's description into a reflective, detailed end-to-end workflow. "
                "Include all nodes, conditional branches, notes, subgraphs, classDefs—whatever makes it clear. "
                "Use underscores in multi-word IDs (no spaces). "
                "Return ONLY valid Mermaid code body—no markdown fences or extra commentary."
            ),
            height=140
        )
    
    # Workflow history section
    st.header("💾 Saved Workflows")
    if st.session_state.workflow_history:
        selected_workflow_index = st.selectbox(
            "Load saved workflow",
            options=range(len(st.session_state.workflow_history)),
            format_func=lambda i: f"{st.session_state.workflow_history[i]['name']} ({st.session_state.workflow_history[i]['date']})"
        )
        
        if st.button("Load Selected"):
            selected = st.session_state.workflow_history[selected_workflow_index]
            st.session_state.current_workflow_id = selected['id']
            st.session_state.loaded_workflow = selected
            st.rerun()
            
        if st.button("Delete Selected"):
            del st.session_state.workflow_history[selected_workflow_index]
            st.rerun()
    else:
        st.info("No saved workflows yet")

# ── Template Selection ───────────────────────────────────────────────────────
templates = {
    "Product Development": "A product team identifies market needs → Research and ideation → Feature prioritization → Design wireframes and prototypes → Development sprints → QA and testing → User feedback sessions → Release → Post-release monitoring",
    "Sales Process": "Lead generation → Lead qualification → Initial contact → Needs assessment → Demo or proposal → Negotiation → Close deal → Onboarding → Follow-up and retention",
    "Content Marketing": "Content strategy planning → Topic research → Content creation → Internal review → Revisions → Publishing → Distribution across channels → Performance monitoring → Content repurposing",
    "Customer Support": "Customer submits ticket → Automated categorization → Priority assignment → Agent review → Research solution → Resolution implementation → Customer verification → Feedback collection → Knowledge base update",
    "Recruitment": "Job requisition → Job posting → Resume screening → Initial interview → Skills assessment → Team interviews → Reference checks → Offer negotiation → Onboarding process",
    "Custom": ""
}

# ── Main UI ───────────────────────────────────────────────────────────────
st.title("🖍️ Flowwmaid: Streamline Workflows")

cols = st.columns([2, 1])
with cols[0]:
    selected_template = st.selectbox("Choose a workflow template or create custom:", 
                                    options=list(templates.keys()),
                                    index=len(templates)-1)  # Default to Custom

workflow_desc = ""
# Handle template selection or load saved workflow
if selected_template != "Custom":
    workflow_desc = templates[selected_template]
elif hasattr(st.session_state, 'loaded_workflow'):
    workflow_desc = st.session_state.loaded_workflow['description']
    del st.session_state.loaded_workflow  # Clear after loading

workflow_desc = st.text_area(
    "📝 Describe your workflow:",
    value=workflow_desc,
    placeholder="e.g. 'A deals team sources mandate → performs due diligence → negotiates terms → closes transaction → handles post-deal integration and reporting.'",
    height=150,
)

# ── Buttons row ───────────────────────────────────────────────────────────────
cols = st.columns([1, 1, 1])
with cols[0]:
    generate = st.button("🔄 Generate Diagram", disabled=not workflow_desc.strip(), use_container_width=True)
with cols[1]:
    save_button = st.button("💾 Save Workflow", disabled=not hasattr(st.session_state, 'last_mermaid_code'), use_container_width=True)
with cols[2]:
    export_options = st.button("📤 Export Options", disabled=not hasattr(st.session_state, 'last_mermaid_code'), use_container_width=True)

# ── OpenAI call -------------------------------------------------------------
def prompt_to_mermaid(desc: str, sys_msg: str, temp: float, model_name: str) -> str:
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    # Enhanced prompt with more specific instructions
    enhanced_desc = f"""
Create a detailed Mermaid workflow diagram for:
{desc}

Requirements:
- Use meaningful node IDs and descriptive labels 
- Include decision points with yes/no branches where appropriate
- Group related steps into subgraphs
- Add helpful notes for key steps
- Use consistent styling with classDef
- Make the diagram read clearly from start to finish
"""
    
    resp = openai.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": enhanced_desc}
        ],
        temperature=temp,
    )
    return resp.choices[0].message.content

# ── Sanitization -----------------------------------------------------------
def clean_mermaid_body(raw: str) -> str:
    # 1) Remove any triple-backtick fences
    cleaned = re.sub(r"```(?:mermaid)?", "", raw, flags=re.IGNORECASE)

    # 2) Drop any pre-existing 'graph' or 'flowchart' lines
    cleaned = re.sub(r"(?mi)^ *(graph|flowchart)\s+\w+.*$", "", cleaned)

    # 3) Split, strip trailing whitespace, drop blank lines
    lines = [ln.rstrip() for ln in cleaned.splitlines() if ln.strip()]

    # 4) Whitelist only valid Mermaid constructs
    kept = []
    for ln in lines:
        if re.match(r"^%%\{.*\}%%$", ln):                # directive
            kept.append(ln)
        elif re.match(r"^subgraph\s+\w+", ln):            # subgraph start
            kept.append(ln)
        elif re.match(r"^end$", ln, flags=re.IGNORECASE): # subgraph end
            kept.append(ln)
        elif re.match(r"^classDef\s+\w+", ln):            # class definitions
            kept.append(ln)
        elif re.match(r"^class\s+\w+", ln):               # class assignments
            kept.append(ln)
        elif re.match(r"^note\s+(left|right|top|bottom)\s+of\s+\w+", ln):  # notes
            kept.append(ln)
        elif re.search(r"--?>", ln):                      # any arrow (--> or ->)
            kept.append(ln)
        elif re.search(r"\[.*\]", ln):                    # standalone node defs
            kept.append(ln)
        # else: drop everything else (prose, bullets, etc.)
    return "\n".join(kept)

# ── Save workflow function -------------------------------------------------
def save_current_workflow(name, description, mermaid_code):
    workflow = {
        'id': str(uuid.uuid4()),
        'name': name,
        'description': description,
        'mermaid_code': mermaid_code,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    st.session_state.workflow_history.append(workflow)
    st.session_state.current_workflow_id = workflow['id']
    return workflow['id']

# ── Export functions -------------------------------------------------------
def get_download_link(content, filename, text):
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">{text}</a>'
    return href

def export_as_png(mermaid_code, filename="flowwmaid_diagram.png"):
    # This would be a placeholder - actual implementation would require
    # integrating with a rendering service like mermaid.ink or using
    # a local renderer like puppeteer
    st.warning("PNG export requires server-side rendering and is simulated in this demo")
    # Placeholder for actual PNG export functionality
    return None

# ── Generate & render ───────────────────────────────────────────────────────
if generate:
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Set OPENAI_API_KEY in Streamlit secrets or .env file.")
    else:
        with st.spinner("🧠 Generating detailed diagram..."):
            raw_output = prompt_to_mermaid(workflow_desc, system_prompt, temperature, model)
            body = clean_mermaid_body(raw_output)

        mermaid_code = (
            f"%%{{init:{{'theme':'{theme}'}}}}%%\n"
            f"graph {orientation}\n"
            f"{body}"
        )
        
        # Store the generated code in session state
        st.session_state.last_mermaid_code = mermaid_code
        
        # Display the diagram
        st.subheader("Workflow Diagram")
        stmd.st_mermaid(mermaid_code)
        
        # Display the editable code with auto-updating preview
        st.subheader("Edit Diagram Code")
        edited_code = st.text_area("Mermaid Code (editable)", value=mermaid_code, height=300)
        
        if edited_code != mermaid_code:
            st.subheader("Updated Preview")
            try:
                stmd.st_mermaid(edited_code)
                st.session_state.last_mermaid_code = edited_code  # Update with valid edits
            except Exception as e:
                st.error(f"Error in Mermaid syntax: {e}")

# ── Save workflow dialog ---------------------------------------------------
if save_button:
    with st.form("save_workflow_form"):
        st.subheader("Save Current Workflow")
        workflow_name = st.text_input("Workflow Name", value=f"Workflow {len(st.session_state.workflow_history) + 1}")
        save_submitted = st.form_submit_button("Save")
        
        if save_submitted:
            save_current_workflow(workflow_name, workflow_desc, st.session_state.last_mermaid_code)
            st.success(f"Workflow '{workflow_name}' saved successfully!")
            st.rerun()

# ── Export dialog ----------------------------------------------------------
if export_options:
    with st.form("export_options_form"):
        st.subheader("Export Options")
        export_format = st.selectbox("Export Format", ["Mermaid Code (.md)", "JSON", "Markdown"])
        export_filename = st.text_input("Filename", value="flowwmaid_diagram")
        export_submitted = st.form_submit_button("Export")
        
        if export_submitted:
            if export_format == "Mermaid Code (.md)":
                content = f"```mermaid\n{st.session_state.last_mermaid_code}\n```"
                st.markdown(get_download_link(content, f"{export_filename}.md", "Download Mermaid Code"), unsafe_allow_html=True)
            elif export_format == "JSON":
                export_data = {
                    "description": workflow_desc,
                    "mermaid_code": st.session_state.last_mermaid_code,
                    "exported_at": datetime.now().isoformat()
                }
                content = json.dumps(export_data, indent=2)
                st.markdown(get_download_link(content, f"{export_filename}.json", "Download JSON"), unsafe_allow_html=True)
            elif export_format == "Markdown":
                content = f"# {export_filename}\n\n## Workflow Description\n\n{workflow_desc}\n\n## Diagram\n\n```mermaid\n{st.session_state.last_mermaid_code}\n```"
                st.markdown(get_download_link(content, f"{export_filename}.md", "Download Markdown"), unsafe_allow_html=True)

# ── Footer ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align: center">
    <p>Flowwmaid - Convert text to detailed workflow diagrams with AI</p>
</div>
""", unsafe_allow_html=True)
