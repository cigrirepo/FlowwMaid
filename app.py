import os
import streamlit as st
import openai
import streamlit_mermaid as stmd  # community component

# ---- Page setup -------------------------------------------------------------
st.set_page_config(page_title="Mermaid-from-Prompt", layout="wide")
st.title("🖍️ Prompt → Mermaid Diagram")

# ---- API key ----------------------------------------------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")  # from Streamlit secrets

# ---- UI ---------------------------------------------------------------------
user_prompt = st.text_area(
    "Describe your process / workflow",
    placeholder="e.g. ‘Data engineer ingests CSV, triggers ETL, loads to warehouse, BI dashboard refreshes…’",
    height=160,
)

generate = st.button("Generate diagram", disabled=not user_prompt)

# ---- OpenAI call ------------------------------------------------------------
def prompt_to_mermaid(prompt: str) -> str:
    system_msg = (
        "You are a senior solutions architect. "
        "Convert the user's description into a concise Mermaid flowchart. "
        "Return *only* the mermaid code starting with 'graph'. No markdown fences, "
        "no commentary."
    )
    response = openai.chat.completions.create(
        model="gpt-4o-mini",  # adjust to the model you have access to
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()

# ---- Render -----------------------------------------------------------------
if generate:
    with st.spinner("Thinking…"):
        mermaid_code = prompt_to_mermaid(user_prompt)

    st.subheader("Mermaid source")
    st.code(mermaid_code, language="mermaid")

    st.subheader("Diagram preview")
    stmd.st_mermaid(mermaid_code)  # render via component

    st.success("Done! Copy the code block into any Mermaid-aware doc or markdown file.")
