"""Shared helpers for the Streamlit pages."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from ragshield_core.rag_shield import RAGShield
from ragshield_core.retriever import load_targets


@st.cache_resource
def get_shield(poisoned: bool = True):
    return RAGShield().setup(poisoned=poisoned)


def get_targets():
    return load_targets()


def doc_row(d, show_trust=False):
    src = d.get("source", "clean")
    badge = "🔴 POISON" if src == "POISONED" else "🟢 clean"
    score = d.get("score", 0.0)
    line = f"{badge} · score={score:.3f}"
    if show_trust and "trust" in d:
        line += f" · trust={d['trust']:.3f}"
    title = d.get("title", "")[:60]
    return line, title, d.get("text", "")[:240]
