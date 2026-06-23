<a id="top"></a>

[Repo Home](README.md) · [Docs](docs/) · **Quickstart**

---

# Quickstart — RAG-Shield Demo

Get the demo running in **under 2 minutes**. No API keys needed for demo mode.

## 0. Fix the venv first (you hit exit code 126)

Your earlier `python3.11 -m venv .venv && source .venv/bin/activate` returned **126**
(venv half-created / not executable). Rebuild it cleanly:

```bash
cd ~/Desktop/MTech\ AI\ IIT-Jodhpur*/Cohort-2-Trimester-2/Cyber-Security_ES/Major-Project-PoisonedRAG

# nuke the broken venv and remake it
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate

# sanity: prompt should now show (.venv) and this should print a 3.11 path
which python && python --version
```

If `python3.11` itself is missing:
```bash
brew install python@3.11
```

## 1. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

(Demo mode only strictly needs: `streamlit pandas scikit-learn numpy python-dotenv`.)

## 2. Run the demo (instant, no keys)

```bash
chmod +x run_demo.sh
./run_demo.sh
```

Then open **http://localhost:8501**. Use the sidebar pages:
Attack Demo → Defense Demo → Side-by-Side → Forensic Explorer → Results Dashboard.

## 3. Quick terminal check (optional)

```bash
DEMO_MODE=1 python demo_cli.py "Who founded Tesla Motors?"
DEMO_MODE=1 python evaluation/run_experiments.py
```

Expected: ASR **~100% no-defense → ~0% with RAG-Shield**.

---

## 4. Switch to LIVE mode (real FAISS + Claude + LLaMA)

Demo mode uses a lightweight TF-IDF retriever + mock LLMs so it always runs.
To use your real 5000-doc FAISS index and real LLMs:

```bash
# 1) make sure your real KB + index exist
ls knowledge_base/vector_store/kb.faiss knowledge_base/vector_store/kb_meta.json

# 2) fill .env (copy from .env.example) with at least ANTHROPIC_API_KEY
cp .env.example .env && nano .env

# 3) (optional) start local LLaMA for a 2nd vendor
brew install ollama && ollama pull llama3.1:8b && ollama serve &

# 4) run in live mode
DEMO_MODE=0 ./run_demo.sh
```

In live mode:
- Retriever loads `knowledge_base/vector_store/kb.faiss` via sentence-transformers.
- Ring 3 panel = Claude + LLaMA (+ Azure GPT if you set the Azure vars).
- Everything else is identical.

---

## What runs where

| Command | What it does |
|---------|--------------|
| `./run_demo.sh` | Launch the 5-page Streamlit demo |
| `python3.11 demo_cli.py "<question>"` | One-question terminal demo |
| `python3.11 evaluation/run_experiments.py` | Full ASR table + writes `evaluation/results/asr_results.json` |

---

[Repo Home](README.md) · [Docs](docs/) · **Quickstart**

[↑ Back to top](#top)
