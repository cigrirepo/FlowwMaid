import os
import streamlit as st
import openai
import streamlit\_mermaid as stmd  # community component

# ---- Page setup -------------------------------------------------------------

st.set\_page\_config(page\_title="Mermaid-from-Prompt", layout="wide")
st.title("🖍️ Prompt → Mermaid Diagram")

# ---- API key ----------------------------------------------------------------

openai.api\_key = os.getenv("OPENAI\_API\_KEY")  # from Streamlit secrets

# ---- UI ---------------------------------------------------------------------

user\_prompt = st.text\_area(
"Describe your process / workflow",
placeholder="e.g. ‘Data engineer ingests CSV, triggers ETL, loads to warehouse, BI dashboard refreshes…’",
height=160,
)

generate = st.button("Generate diagram", disabled=not user\_prompt)

# ---- OpenAI call ------------------------------------------------------------

def prompt\_to\_mermaid(prompt: str) -> str:
system\_msg = (
"You are a senior solutions architect. "
"Convert the user's description into a concise Mermaid flowchart. "
"Return *only* the mermaid code starting with 'graph'. No markdown fences, "
"no commentary."
)
response = openai.chat.completions.create(
model="gpt-4o-mini",  # or the model you have access to
messages=[
{"role": "system", "content": system\_msg},
{"role": "user", "content": prompt},
],
temperature=0.3,
)
return response.choices[0].message.content.strip()

# ---- Render -----------------------------------------------------------------

if generate:
with st.spinner("Thinking…"):
mermaid\_code = prompt\_to\_mermaid(user\_prompt)

```
st.subheader("Mermaid source")
st.code(mermaid_code, language="mermaid")

st.subheader("Diagram preview")
stmd.st_mermaid(mermaid_code)  # instant render via component :contentReference[oaicite:2]{index=2}

st.success("Done! Copy the code block into any Mermaid-aware doc or markdown file.")
```
