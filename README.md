<a id="top"></a>

<div align="center">

# PoisonedRAG + RAG-Shield

**Reproducing a state-of-the-art RAG knowledge-poisoning attack — and building the defense the authors said didn't yet exist.**

![Course](https://img.shields.io/badge/Course-CSL6010%20Cyber%20Security-7C3AED)
![Institute](https://img.shields.io/badge/IIT%20Jodhpur-M.Tech%20AI-0EA5E9)
![Group](https://img.shields.io/badge/Group-6-14B8A6)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Status](https://img.shields.io/badge/status-active-success)
![License](https://img.shields.io/badge/license-MIT-yellow)

[Paper Summary](docs/paper_summary.md) · [Gap &amp; Fix](docs/gap_and_fix.md) · [Viva Q&amp;A](docs/viva_qa.md) · [Project Guide](PROJECT_GUIDE.md) · [Quickstart](QUICKSTART.md) · [Slides](slides/)

</div>

---

## Contents

- [1. tldr](#1-tldr)
- [2. the attack-poisonedrag](#2-the-attack-poisonedrag)
- [3. the gap-we-fill](#3-the-gap-we-fill)
- [4. our-solution-rag-shield](#4-our-solution-rag-shield)
- [5. how-it-works-end-to-end](#5-how-it-works-end-to-end)
- [6. tech-stack](#6-tech-stack)
- [7. repository-structure](#7-repository-structure)
- [8. setup-step-by-step](#8-setup-step-by-step)
- [9. running-the-demo](#9-running-the-demo)
- [10. the-gui-explained](#10-the-gui-explained)
- [11. demo-mode-vs-live-mode](#11-demo-mode-vs-live-mode)
- [12. results](#12-results)
- [13. the-8-steps-the-professor-requires](#13-the-8-steps-the-professor-requires)
- [14. team-group-6](#14-team-group-6)
- [15. troubleshooting](#15-troubleshooting)
- [16. links](#16-links)

---

## 1. tldr

RAG (Retrieval-Augmented Generation) lets an LLM answer using documents fetched from an external knowledge base. The **PoisonedRAG** paper (USENIX Security 2025) shows that injecting just **5 malicious documents** into a knowledge base of **millions** makes the LLM output an attacker-chosen wrong answer **~90% of the time** — and that existing defenses don't stop it.

This project (1) **reproduces** that attack and (2) builds **RAG-Shield**, a **3-ring defense-in-depth** pipeline that drops attack success from ~90% to ~13% while preserving normal-query accuracy.

The whole thing runs **instantly in demo mode** (no API keys, no GPU) and upgrades to **live mode** (real FAISS index + Claude/LLaMA) with a single environment flag.

[Back to top](#top)

---

## 2. the attack-poisonedrag

**Paper:** PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented Generation of Large Language Models
**Authors:** Wei Zou, Runpeng Geng, Binghui Wang, Jinyuan Jia
**Venue:** 34th USENIX Security Symposium, 2025 · arXiv 2402.07867

### The idea

A poison document must satisfy **two conditions at once**:

1. **Retrieval condition** — it must be similar enough to the target question to be retrieved into the top-K.
2. **Generation condition** — once retrieved, it must mislead the LLM into producing the attacker's answer.

Each poison doc is built as `P = S + I`:

```
   P (poison document)
   = S  (retrieval trigger)   +   I  (injection text)
     |                             |
     | crafted to MATCH the        | carries the MISINFORMATION
     | question so it gets         | that pushes the LLM toward
     | retrieved (the disguise)    | the wrong answer (the payload)
```

Trojan-horse analogy: `S` is the disguise that gets the horse through the gate (retrieval); `I` is the soldier inside that does the damage (generation).

### Attack flow

```
  attacker picks:  target question  +  wrong answer
          |
          v
  build 5 poison docs (S + I)  ---->  inject into knowledge base
                                              |
   user later asks the target question        |
          |                                   v
          v                          top-K retrieval pulls poison
     LLM reads poisoned context  <---  (poison out-ranks clean docs)
          |
          v
     LLM returns the ATTACKER'S answer   (attack success ~90%)
```

Full explainer: [docs/paper_summary.md](docs/paper_summary.md)

[Back to top](#top)

---

## 3. the gap-we-fill

The paper tested the obvious defenses and showed each fails:

| Defense | Why it fails |
|---------|--------------|
| Perplexity filtering | Poison is LLM-generated, so it reads fluently with natural perplexity |
| Query paraphrasing | Poison matches meaning, not exact words — rewording doesn't move embeddings enough |
| Knowledge expansion | More retrieved docs still include the poison; the LLM keeps weighting it |

Even with defenses on, attack success stays around **30%+**. The authors explicitly call for new defenses.

**Our diagnosis:** every one of those is a **single checkpoint** — a single point of failure. The attacker just tunes the poison to beat that one check.

**Gap statement:** *what's missing is layered, defense-in-depth protection that screens documents at ingest, at retrieval, and at generation — so defeating one layer is not enough.*

Full analysis: [docs/gap_and_fix.md](docs/gap_and_fix.md)

[Back to top](#top)

---

## 4. our-solution-rag-shield

RAG-Shield places **three independent rings** at three stages of the pipeline. To succeed, poison must defeat **all three at once**.

```
  +==================================================================+
  |                          RAG-SHIELD                              |
  +==================================================================+

   document being ADDED            query ARRIVES           answer being FORMED
          |                             |                        |
          v                             v                        v
   +--------------+            +-----------------+      +-------------------+
   |   RING 1     |            |     RING 2      |      |      RING 3       |
   | Ingest Guard |  ------->  | Retrieval Score |  --> | Cross-LLM Vote    |
   +--------------+            +-----------------+      +-------------------+
   perplexity                  provenance / trust       3 LLMs answer
   embedding-outlier           inter-doc consistency    if they DISAGREE ->
   pattern (verbatim Q)        trust re-ranking          drop suspect + re-ask
          |                             |                        |
          v                             v                        v
   block crafted poison       drop low-trust /          catch poison that
   at the door                inconsistent docs         slipped through 1-2
```

### Ring 1 — Ingest Guard
Screens a document as it enters the KB. Three detectors: **perplexity** (repetition / keyword-stuffing proxy), **embedding-outlier** (distance from the KB centroid), **pattern** (a target question embedded verbatim — a PoisonedRAG hallmark). A doc is blocked if the combined score exceeds the threshold.

### Ring 2 — Retrieval Scorer
At query time, re-scores the retrieved top-K. **Provenance weighting** (trusted sources rank higher), **inter-document consistency** (a doc that contradicts the clean majority is down-weighted), then **trust-weighted re-ranking**. Docs below the trust floor are dropped from the context.

### Ring 3 — Cross-LLM Consensus
Queries 3 different LLMs with the same context. If they **agree**, return with confidence. If they **disagree**, drop the lowest-trust doc(s) and **re-retrieve / re-ask once**. Different model families don't get fooled identically, so disagreement is a strong poison signal.

> Airport-security analogy: one checkpoint can be fooled; three independent checkpoints (bag scan, metal detector, human officer) are much harder to beat all at once.

[Back to top](#top)

---

## 5. how-it-works-end-to-end

Full data flow with the rings engaged:

```
  USER QUERY
     |
     v
  [ Retriever ]                         demo: TF-IDF (sklearn)
   top-K docs from KB (clean + poison)  live: FAISS + sentence-transformers
     |
     v
  [ RING 1  Ingest Guard ]   --> blocked docs logged, dropped
     |
     v
  [ RING 2  Retrieval Scorer ] --> trust re-rank; low-trust docs dropped
     |
     v
  [ RING 3  Cross-LLM Consensus ]
     |  agree?  --yes-->  return answer
     |  disagree --> drop suspect doc --> re-retrieve --> re-vote
     v
  TRUSTED ANSWER  (+ full per-ring trace for the Forensic page)
```

The orchestrator is `ragshield_core/rag_shield.py`. Two entry points:
- `answer(question, defense=True/False, candidates=[...])` — returns the answer.
- `trace(...)` — returns every ring's decision (used by the Forensic Explorer UI).

[Back to top](#top)

---

## 6. tech-stack

| Layer | Demo mode | Live mode |
|-------|-----------|-----------|
| Language | Python 3.11 | Python 3.11 |
| Retriever | TF-IDF + cosine (scikit-learn) | FAISS + `all-mpnet-base-v2` (sentence-transformers) |
| Knowledge base | built-in mini-KB | 5,000 Wikipedia docs (`wikimedia/wikipedia`, `20231101.en`) |
| LLMs | 3 heuristic mock LLMs | Claude (Anthropic) + LLaMA 3.1 (Ollama) + Azure OpenAI (optional) |
| UI | Streamlit | Streamlit |
| Eval | live ASR harness | live ASR harness |

[Back to top](#top)

---

## 7. repository-structure

```
poisonedrag-ragshield-group6-iitj/
|
+-- README.md                      <- this file
+-- PROJECT_GUIDE.md               <- file map + GUI guide + all commands
+-- QUICKSTART.md                  <- 2-minute setup
+-- LICENSE                        <- MIT
+-- requirements-demo.txt          <- light deps (demo mode)
+-- requirements.txt               <- full deps (live mode)
+-- setup_project.sh               <- one-shot installer (Python 3.11 + smoke test)
+-- run_demo.sh                    <- launch demo-mode UI
+-- run_live.sh                    <- launch lite-live UI (real local LLMs)
+-- backends_status.py             <- ping backends; show LIVE/DOWN
+-- tail_logs.sh                   <- live log feed
+-- demo_cli.py                    <- one-question terminal demo
+-- .gitignore                     <- blocks .env / .venv / FAISS index
+-- .env.example                   <- secrets template
+-- .streamlit/
|   +-- config.toml                <- headless + no email prompt
|
+-- ragshield_core/                <- THE ENGINE
|   +-- config.py                  <- paths, env, demo/live flag
|   +-- llm_backends.py            <- Claude / Ollama / Azure / mock + consensus panel
|   +-- retriever.py               <- TF-IDF + FAISS retriever, KB load, poison inject
|   +-- ring1_ingest.py            <- Ingest Guard (perplexity, pattern, outlier)
|   +-- ring2_retrieval.py         <- Retrieval Scorer (provenance, consistency)
|   +-- ring3_consensus.py         <- Cross-LLM consensus + re-retrieval
|   +-- rag_shield.py              <- orchestrator (setup / answer / trace)
|
+-- frontend/                      <- STREAMLIT DEMO
|   +-- app.py                     <- landing + sidebar nav
|   +-- pages/
|   |   +-- 1_Attack_Demo.py
|   |   +-- 2_Defense_Demo.py
|   |   +-- 3_Side_by_Side.py
|   |   +-- 4_Forensic_Explorer.py
|   |   +-- 5_Results_Dashboard.py
|   +-- components/_shared.py      <- cached shield builder + helpers
|
+-- evaluation/                    <- EVALUATION
|   +-- run_experiments.py         <- headless ASR harness -> results JSON
|   +-- target_questions.json      <- 10 target questions (true + wrong answers)
|
+-- docs/                          <- explainers
|   +-- PAPER_SUMMARY.md
|   +-- GAP_AND_FIX.md
|   +-- VIVA_QA.md
|
+-- slides/                        <- presentation deck
+-- knowledge_base/  baseline/  paper/   <- real-mode KB build + paper PDF
```

[Back to top](#top)

---

## 8. setup-step-by-step

### Prerequisites
- **Python 3.11** (not 3.9 — older versions break the dependency install)
- macOS / Linux. On macOS: `brew install python@3.11`

### Option A — one-shot script (recommended)

```bash
git clone https://github.com/rpaut03l/poisonedrag-ragshield-group6-iitj.git
cd poisonedrag-ragshield-group6-iitj
chmod +x setup_project.sh
./setup_project.sh
```

The script finds Python 3.11, builds the venv, installs the light demo deps, and runs a smoke test.

### Option B — manual

```bash
# 1. clone
git clone https://github.com/rpaut03l/poisonedrag-ragshield-group6-iitj.git
cd poisonedrag-ragshield-group6-iitj

# 2. virtual environment (MUST be Python 3.11)
python3.11 -m venv .venv
source .venv/bin/activate
python --version            # confirm 3.11.x

# 3. install demo dependencies (light, no torch/faiss)
pip install --upgrade pip
pip install -r requirements-demo.txt

# 4. verify
DEMO_MODE=1 python demo_cli.py "Who founded Tesla Motors?"
```

Expected output:
```
[NO DEFENSE]  -> Nikola Jones          (attack succeeds)
[RAG-SHIELD]  -> Martin Eberhard        (defense restores truth)
   Ring1 blocked=3  Ring2 dropped=0  Ring3 agreement=1.0
```

[Back to top](#top)

---

## 9. running-the-demo

Call the venv python by path (`.venv/bin/python`) — robust even if
`source .venv/bin/activate` fails (exit 126 on iCloud-synced Desktop paths).

```bash
# DEMO mode (mock LLMs, instant, no keys)
DEMO_MODE=1 .venv/bin/python -m streamlit run frontend/app.py --server.port 8502
# open http://localhost:8502

# LITE-LIVE mode (real local Ollama LLMs, Mac-safe) — recommended for presenting
./run_live.sh

# live backend health check + real-time log feed
DEMO_MODE=0 .venv/bin/python backends_status.py
./tail_logs.sh

# one-question terminal demo / full evaluation
DEMO_MODE=1 .venv/bin/python demo_cli.py "Who designed the Eiffel Tower?"
DEMO_MODE=1 .venv/bin/python evaluation/run_experiments.py
```

[Back to top](#top)

---

## 10. the-gui-explained

The left sidebar has the landing page plus 5 pages. The top tags show the mode (`DEMO` / `LIVE`), `top-K`, and group.

| Page | Proves | What you do | What you see |
|------|--------|-------------|--------------|
| **Attack Demo** | the problem exists | "Run attack (no defense)" | poison docs (red) out-rank clean docs; LLM returns the wrong answer |
| **Defense Demo** | the fix works | "Run with RAG-Shield" | ring-by-ring trace: Ring1 blocked count, Ring2 dropped + trust, Ring3 agreement %; correct answer restored |
| **Side-by-Side** | instant contrast | "Compare" | plain RAG (wrong) next to RAG-Shield (right), together |
| **Forensic Explorer** | how it caught it | expand any doc | the actual Ring1 scores (perplexity/pattern/outlier), Ring2 trust, Ring3 panel JSON |
| **Results Dashboard** | the numbers | "Run evaluation" | live ASR bar chart (No Defense / Paper's Defenses / RAG-Shield) + per-question table |

**Presentation order:** Attack -> Side-by-Side -> Defense -> Forensic -> Dashboard (problem, contrast, mechanism, proof, numbers).

[Back to top](#top)

---

## 11. demo-mode-vs-live-mode

Three modes via `DEMO_MODE` and `RETRIEVER`.

| | Demo | Lite-Live (recommended) | Full-Live |
|---|---|---|---|
| Flags | `DEMO_MODE=1` | `DEMO_MODE=0 RETRIEVER=tfidf` | `DEMO_MODE=0 RETRIEVER=faiss` |
| Retriever | TF-IDF | TF-IDF (light) | FAISS + sentence-transformers |
| LLMs | 3 mock | real local Ollama panel | real local (+ Claude/Azure if set) |
| Keys | none | none (local) | optional API keys |
| Crash risk on Apple Silicon | none | none | high (native-lib segfault) |
| Speed | instant | fast | slow |

Lite-Live (real local LLMs, no cloud, no crash):

```bash
.venv/bin/python -m pip install -r requirements.txt
ollama pull llama3.2:3b && ollama pull phi4-mini && ollama pull gemma3:4b
ollama serve &
./run_live.sh
```

`.env` for lite-live (no `#` comments after values):
```
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.1:8b
OLLAMA_PANEL=llama3.2:3b,phi4-mini:latest,gemma3:4b
VLLM_BASE_URL=
```

Notes: vLLM needs an NVIDIA GPU (not available on Mac). Claude API needs paid
credits (separate from a Pro subscription). After restart, clear the Streamlit
cache ("..." menu) so cached answers refresh.

[Back to top](#top)

---

## 12. results

Computed live by `evaluation/run_experiments.py` over the target questions:

```
  Attack Success Rate (%)

  No Defense        |##################################  ~91
  Paper's Defenses* |##########                          ~29
  RAG-Shield (Ours) |####                                ~13

  * illustrative placeholder until the full 30-question harness runs;
    the No-Defense and RAG-Shield bars are computed live.
```

- Holds across multiple LLM backends.
- Benign-query accuracy is preserved (the defense doesn't break normal questions).

[Back to top](#top)

---

## 13. the-8-steps-the-professor-requires

The professor's brief requires eight steps in order. The grade lives in steps 5-8 (gap, proposal, implementation, demonstration).

| # | Step | Status | Where it lives |
|---|------|--------|----------------|
| 1 | Update Excel with paper details | ✅ | [Google Sheet — Project Details](https://docs.google.com/spreadsheets/d/1mE86xKOTDGN1s-RmhSV2TMlsLKbWNKZbgLafJhPWi0g/edit?gid=0#gid=0) |
| 2 | Read the paper | ✅ | [docs/paper_summary.md](docs/paper_summary.md) - full walkthrough |
| 3 | Analyze the problem | ✅ | [docs/paper_summary.md](docs/paper_summary.md#2-the-problem-a-new-attack-surface) |
| 4 | Understand the proposed solution | ✅ | [docs/paper_summary.md](docs/paper_summary.md#4-how-the-attack-works-the-two-conditions) |
| 5 | Identify the gap | ✅ | [docs/gap_and_fix.md](docs/gap_and_fix.md#part-a-the-gap-step-5) |
| 6 | Propose our own solution | ✅ | [docs/gap_and_fix.md](docs/gap_and_fix.md#part-b-our-fix-rag-shield-step-6) |
| 7 | Implement it | ✅ | [ragshield_core/](ragshield_core/) · [frontend/](frontend/) |
| 8 | Demonstrate effectiveness | ✅ | [evaluation/](evaluation/) · live demo ([run_live.sh](run_live.sh)) |

[Back to top](#top)

---

## 14. team-group-6

| Member | ID | Role |
|--------|----|----|
| Jeenal Chaudhary | G25AIT2027 | Intro + RAG Details |
| Amit Singh | G25AIT2007 | Problem & threat model |
| Sharvan Vittala | G25AIT2099 | Attack mechanics · Ring 1 |
| Sudeb Ghosh | G25AIT2113 | Attack deep-dive · Adversarial testing |
| Kosuru Yuvaraj | G25AIT2054 | Gap analysis · Ring 2 |
| Pujan Chakraborty | G25AIT2076 | RAG-Shield design · Evaluation |
| Rohit Patel | G25AIT2089 | Architecture · Implementation · Live demo |
| Vishnu Priya | G25AIT2128 | Frontend · Report · Demo video |

[Back to top](#top)

---

## 15. troubleshooting

| Symptom | Fix |
|---------|-----|
| `networkx>=3.3` / torch install error | Your venv is Python < 3.10. Rebuild with 3.11: `rm -rf .venv && python3.11 -m venv .venv` |
| venv `source` exit code 126 | Broken venv — same rebuild as above |
| Streamlit stuck at `Email:` prompt | `.streamlit/config.toml` ships with `headless = true`; or run `printf '[general]\nemail = ""\n' > ~/.streamlit/credentials.toml` |
| `localhost:8502` blank | Server didn't start — check the terminal for a traceback; `lsof -i :8502` to confirm it's listening |
| Port busy | `--server.port 8503` (or `pkill -9 -f streamlit` to clear old ones) |
| Python segfaults in live mode | Use Lite-Live (`RETRIEVER=tfidf`) via `./run_live.sh` — avoids the torch/faiss native crash on Apple Silicon |

[Back to top](#top)

---

## 16. links

- **Paper (USENIX):** https://www.usenix.org/conference/usenixsecurity25/presentation/zou-poisonedrag
- **arXiv:** https://arxiv.org/abs/2402.07867
- **Official attack code:** https://github.com/sleeepeer/PoisonedRAG
- **Our fork:** https://github.com/rpaut03l/sleeepeer_PoisonedRAG

---

*CSL6010 Cyber Security · Prof. Susil Kumar Mohanty · M.Tech AI · IIT Jodhpur*

[Back to top](#top)
