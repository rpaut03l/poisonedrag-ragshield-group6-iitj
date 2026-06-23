<a id="top"></a>

[Repo Home](README.md) · [Quickstart](QUICKSTART.md) · **Project Guide**

---

# RAG-Shield — Complete Project Guide

Everything in one place: what each file does, what every GUI page shows, and every command to run. Hand this to the team.

## Contents
- [1. One-minute mental model](#1-one-minute-mental-model)
- [2. File-by-file map](#2-file-by-file-map)
- [3. The Streamlit GUI explained](#3-the-streamlit-gui-explained)
- [4. All run commands](#4-all-run-commands)
- [5. Demo / live mode](#5-demo--live-mode)
- [6. Presentation flow](#6-presentation-flow)
- [7. Troubleshooting](#7-troubleshooting)

---

## 1. One-minute mental model

```
   QUESTION
      |
      v
  [ Retriever ]  -- finds top-K docs from the KB (clean + hidden poison)
      |
      v
  +--------------------- RAG-SHIELD ---------------------+
  | Ring 1  Ingest Guard   : block crafted poison docs   |
  | Ring 2  Retrieval Score: drop low-trust / inconsistent|
  | Ring 3  Cross-LLM Vote : 3 LLMs; disagree => re-ask  |
  +------------------------------------------------------+
      |
      v
   TRUSTED ANSWER
```

- **No defense** = the LLM reads the poisoned top-K and returns the attacker's answer.
- **RAG-Shield on** = the three rings strip the poison, the true answer survives.

---

## 2. File-by-file map

### Core engine — `ragshield_core/`
| File | Responsibility |
|------|----------------|
| `config.py` | Paths, env loading, `demo_mode()` flag, `TOP_K`, backend detection |
| `llm_backends.py` | One interface for Claude / Ollama / Azure / **mock**; builds the 3-LLM consensus panel |
| `retriever.py` | Document store + retriever (TF-IDF in demo, FAISS in live), KB loading, poison injection, built-in demo KB + targets |
| `ring1_ingest.py` | Ingest Guard — `PerplexityDetector`, `PatternDetector`, `OutlierDetector`, `IngestGuard` |
| `ring2_retrieval.py` | Retrieval Scorer — `ProvenanceWeight`, `ConsistencyCheck`, `RetrievalScorer` |
| `ring3_consensus.py` | `CrossLLMConsensus` — parallel vote + re-retrieval on disagreement |
| `rag_shield.py` | **Orchestrator** — wires retriever + 3 rings; `setup()`, `answer()`, `trace()` |

### Frontend — `frontend/`
| File | Page |
|------|------|
| `app.py` | Landing page + sidebar nav |
| `pages/1_Attack_Demo.py` | Attack Demo |
| `pages/2_Defense_Demo.py` | Defense Demo (ring-by-ring) |
| `pages/3_Side_by_Side.py` | Side-by-Side A/B |
| `pages/4_Forensic_Explorer.py` | Forensic Explorer |
| `pages/5_Results_Dashboard.py` | Results Dashboard (ASR chart) |
| `components/_shared.py` | Shared helpers, cached shield builder |

### Evaluation — `evaluation/`
| File | Purpose |
|------|---------|
| `run_experiments.py` | Headless ASR harness; writes `results/asr_results.json` |
| `target_questions.json` | 10 target questions (true + wrong answers) |

### Runners & config (root)
| File | Purpose |
|------|---------|
| `demo_cli.py` | One-question terminal demo |
| `run_demo.sh` | Launch the Streamlit UI |
| `setup_project.sh` | One-shot install (Python 3.11 + light deps + smoke test) |
| `requirements-demo.txt` | Light deps for demo mode (no torch/faiss) |
| `requirements.txt` | Full deps for live mode |
| `.streamlit/config.toml` | Headless + no email prompt (so the UI always starts) |

---

## 3. The Streamlit GUI explained

The **left sidebar** lists the landing page (`app`) plus 5 pages. Pick a target question on each page, then click the action button.

### Top tags (always visible)
- **Mode: DEMO** — TF-IDF retriever + mock LLMs, no keys. (Becomes **LIVE** when `DEMO_MODE=0`.)
- **top-K = 5** — how many docs the retriever pulls per query.
- **Group 6 · IIT Jodhpur** — branding.

### 🔴 Attack Demo
*Proves the problem.* Pick a question → **Run attack (no defense)**.
- **Left:** raw retrieved context. Poison docs (🔴) out-rank clean docs (🟢) — note their higher `score`.
- **Right:** the LLM returns the attacker's **wrong** answer → red "ATTACK SUCCEEDED".
- **Say:** "Five poison docs out-rank everything and hijack the answer."

### 🛡️ Defense Demo
*Proves the fix.* Same KB, RAG-Shield on → **Run with RAG-Shield**.
- **Ring 1 column:** count of poison docs blocked at ingest + their perplexity/pattern scores.
- **Ring 2 column:** low-trust docs dropped + trust scores on what's kept.
- **Ring 3 column:** each LLM's answer + panel **agreement %**; if they disagreed, a note that it re-retrieved without the suspect doc.
- **Bottom:** corrected answer restored → green "DEFENDED".

### ⚖️ Side-by-Side
*The money shot.* One question → **Compare**.
- Two columns: **Plain RAG (🔴 wrong)** vs **RAG-Shield (🟢 right)**, together. Best single screen for the audience.

### 🔬 Forensic Explorer
*Show your work (viva).* Every retrieved doc is expandable and reveals its Ring 1 verdict JSON (perplexity, pattern, outlier, blocked?). Below: Ring 2 trust re-ranking and the Ring 3 panel JSON. Open this when asked "how do you know it caught the poison?"

### 📊 Results Dashboard
*The numbers.* **Run evaluation** computes ASR live across all target questions:
- Bar chart: **No Defense** vs **Paper's Defenses\*** vs **RAG-Shield**.
- Two metrics: ASR no-defense and ASR with shield (with the drop).
- Per-question table. *\*Paper's-defenses bar is an illustrative placeholder.*

---

## 4. All run commands

```bash
# activate the env first (every new terminal)
source .venv/bin/activate

# launch the GUI
DEMO_MODE=1 streamlit run frontend/app.py        # http://localhost:8501

# one-question terminal demo
DEMO_MODE=1 python demo_cli.py "Who founded Tesla Motors?"

# full evaluation + write results JSON
DEMO_MODE=1 python evaluation/run_experiments.py

# different port if 8501 is busy
DEMO_MODE=1 streamlit run frontend/app.py --server.port 8502
```

---

## 5. Demo / live mode

| | DEMO_MODE=1 (default) | DEMO_MODE=0 (live) |
|---|---|---|
| Retriever | TF-IDF (sklearn) | FAISS + sentence-transformers |
| LLMs | 3 mock LLMs (different susceptibility) | Claude + Ollama LLaMA (+ Azure if set) |
| Keys needed | none | `ANTHROPIC_API_KEY` (+ Ollama running) |
| Install | `requirements-demo.txt` | `requirements.txt` |
| Speed | instant | slower (model load + API) |

Switch to live later:
```bash
pip install -r requirements.txt
cp .env.example .env && nano .env          # add ANTHROPIC_API_KEY
ollama pull llama3.1:8b && ollama serve &  # optional 2nd vendor
DEMO_MODE=0 streamlit run frontend/app.py
```

---

## 6. Presentation flow

Walk the pages in this order — problem → fix → how → proof → numbers:

1. **Attack Demo** — show the hijack.
2. **Side-by-Side** — instant before/after contrast.
3. **Defense Demo** — open the rings; explain each.
4. **Forensic Explorer** — show the actual detection scores.
5. **Results Dashboard** — run it live, show the chart.

Rohit drives this on slide 19 (5 min). Backup if the UI hiccups: `python evaluation/run_experiments.py` in a terminal.

---

## 7. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Streamlit stuck at `Email:` prompt | `.streamlit/config.toml` ships with `headless = true` to skip it; or set `~/.streamlit/credentials.toml` with `email = ""` |
| `localhost:8501` blank | Server didn't start — check the terminal for a traceback; confirm with `lsof -i :8501` |
| `networkx>=3.3` / torch install error | Your venv is Python < 3.10. Rebuild with 3.11: `brew install python@3.11` then `./setup_project.sh` |
| venv `source` exit 126 | Broken venv — `rm -rf .venv && python3.11 -m venv .venv` |
| Port busy | `--server.port 8502` |

---

[Repo Home](README.md) · [Quickstart](QUICKSTART.md) · **Project Guide**

[↑ Back to top](#top)
