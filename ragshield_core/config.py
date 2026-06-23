"""
ragshield_core.config
Central configuration: paths, environment, and run-mode flags.

Two run modes:
  - DEMO_MODE=1  (default): lightweight TF-IDF retriever + heuristic "mock" LLM.
                 Runs instantly, no API keys, no Ollama, no FAISS needed.
  - DEMO_MODE=0 : real FAISS index + sentence-transformers + live LLM backends
                 (Anthropic / Ollama / Azure). Use once your KB + keys are ready.
"""
from __future__ import annotations
import os
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---- project paths -------------------------------------------------
# This file lives in <root>/llm_backends/ ... no — it's imported as a sibling.
# We resolve ROOT as the project root (the dir that contains this package's parent).
ROOT = Path(__file__).resolve().parent.parent
KB_DIR = ROOT / "knowledge_base"
VECTOR_DIR = KB_DIR / "vector_store"
KB_DOCS = KB_DIR / "kb_data" / "kb_docs.jsonl"
FAISS_INDEX = VECTOR_DIR / "kb.faiss"
FAISS_META = VECTOR_DIR / "kb_meta.json"
POISON_CORPUS = ROOT / "baseline" / "poison_corpus.jsonl"
TARGETS = ROOT / "evaluation" / "target_questions.json"
RESULTS_DIR = ROOT / "evaluation" / "results"

# ---- run mode ------------------------------------------------------
def demo_mode() -> bool:
    """True unless DEMO_MODE=0 is explicitly set."""
    return os.getenv("DEMO_MODE", "1") not in ("0", "false", "False")

# ---- retrieval defaults --------------------------------------------
TOP_K = int(os.getenv("TOP_K", "5"))

def retriever_backend() -> str:
    if demo_mode():
        return "demo"
    return os.getenv("RETRIEVER", "tfidf")
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-mpnet-base-v2")

# ---- LLM backend defaults ------------------------------------------
def available_backends() -> list[str]:
    """Which real LLM backends are configured (besides the always-on mock)."""
    out = []
    if os.getenv("ANTHROPIC_API_KEY"):
        out.append("anthropic")
    # ollama assumed reachable on localhost; user can pick it
    out.append("ollama")
    if os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"):
        out.append("azure_openai")
    return out
