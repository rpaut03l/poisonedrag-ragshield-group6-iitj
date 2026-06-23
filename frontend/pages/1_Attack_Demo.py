import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "components"))
from _shared import get_shield, get_targets, doc_row
import streamlit as st

st.set_page_config(page_title="Attack Demo", page_icon="🔴", layout="wide")
st.title("🔴 Attack Demo — PoisonedRAG in action")
st.markdown("A handful of poison documents injected into the knowledge base hijack the answer.")

shield = get_shield(poisoned=True)
targets = get_targets()
labels = [t["question"] for t in targets]
choice = st.selectbox("Pick a target question", labels)
t = next(x for x in targets if x["question"] == choice)
cands = [t["true_answer"], t["wrong_answer"]]

if st.button("Run attack (no defense)", type="primary"):
    out = shield.answer(choice, defense=False, candidates=cands)
    tr = out["trace"]
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Retrieved context (raw)")
        for d in tr["retrieved"]:
            line, title, text = doc_row(d)
            st.markdown(f"**{title}** — {line}")
            st.caption(text)
    with c2:
        st.markdown("#### Result")
        st.markdown(f"True answer: **{t['true_answer']}**")
        st.markdown(f"Attacker's target: **{t['wrong_answer']}**")
        fooled = t["wrong_answer"].lower() in out["answer"].lower()
        st.markdown(f"### LLM said: {'🔴 ' if fooled else '🟢 '}`{out['answer']}`")
        if fooled:
            st.error("ATTACK SUCCEEDED — the LLM returned the attacker's answer.")
        else:
            st.success("Attack did not land this time.")
        st.caption("The poison docs out-rank the clean ones in retrieval, so they "
                   "dominate the context the LLM reads.")
