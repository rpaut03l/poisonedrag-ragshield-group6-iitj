<div align="center">

# PoisonedRAG + RAG-Shield

**Reproducing a state-of-the-art RAG knowledge-poisoning attack — and building the defense the authors said didn't yet exist.**

![Course](https://img.shields.io/badge/Course-CSL6010%20Cyber%20Security-7C3AED)
![Institute](https://img.shields.io/badge/IIT%20Jodhpur-M.Tech%20AI-0EA5E9)
![Group](https://img.shields.io/badge/Group-6-14B8A6)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Status](https://img.shields.io/badge/status-active-success)
![License](https://img.shields.io/badge/license-MIT-yellow)

[Paper Summary](docs/paper_summary.md) · [Gap &amp; Fix](docs/gap_and_fix.md) · [Viva Q&amp;A](docs/viva_qa.md) · [Slides](slides/PoisonedRAG_Group6_Presentation.pptx)

</div>

---

## Contents

- [1. What this project is](#1-what-this-project-is)
- [2. The paper in one paragraph](#2-the-paper-in-one-paragraph)
- [3. The gap we fill](#3-the-gap-we-fill)
- [4. Our solution — RAG-Shield](#4-our-solution--rag-shield-3-ring-defense)
- [5. Tech stack](#5-tech-stack)
- [6. Repository structure](#6-repository-structure)
- [7. The 8 steps the professor requires](#7-the-8-steps-the-professor-requires)
- [8. Team — Group 6](#8-team--group-6)
- [9. Links](#9-links)

---

## 1. What this project is

This repository does two things:

1. **Reproduces** the attack from the USENIX Security 2025 paper *PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented Generation of Large Language Models* on our own knowledge base.
2. **Proposes and implements our own defense — RAG-Shield** — a 3-ring, defense-in-depth pipeline that closes the gap the paper explicitly leaves open ("existing defenses are insufficient... highlighting the need for new defenses").

The result: attack success rate drops from ~90% (undefended) to ~13% (RAG-Shield), while normal-query accuracy is preserved.

---

## 2. The paper in one paragraph

RAG (Retrieval-Augmented Generation) makes an LLM answer using documents pulled from an external knowledge base, fixing stale knowledge and reducing hallucination. PoisonedRAG is the **first knowledge-corruption attack** on RAG: an attacker injects just **5 malicious documents per target question** into a KB of **millions** of clean documents, and induces the LLM to output an **attacker-chosen wrong answer** — achieving a **~90% attack success rate**. Each poison document is split into two parts, `P = S + I`: `S` is a retrieval trigger (gets the doc retrieved), `I` is the injection (misleads the LLM). The attack works in both black-box (LLM-generated poison, realistic) and white-box (gradient-optimized) settings, across many LLMs, retrievers, and datasets.

Full details: [`docs/paper_summary.md`](docs/paper_summary.md)

---

## 3. The gap we fill

The authors evaluated the standard defenses (perplexity filtering, query paraphrasing, knowledge expansion) and showed **they don't work** — residual attack success stays around 30%+. They call for new defenses.

**Our gap statement:** single-layer defenses are a single point of failure. We need **defense-in-depth** that screens documents at *ingest*, at *retrieval*, and at *generation*.

Full analysis: [`docs/gap_and_fix.md`](docs/gap_and_fix.md)

---

## 4. Our solution — RAG-Shield (3-ring defense)

```
   User Query
       |
       v
  Knowledge Base  (clean docs + hidden poison)
       |
       v
  +-----------------------------------------------+
  |  RING 1 - Ingest Guard                        |
  |  perplexity + embedding-outlier + pattern     |
  +-----------------------------------------------+
       |
       v
  +-----------------------------------------------+
  |  RING 2 - Retrieval Scorer                    |
  |  source-provenance + inter-doc consistency    |
  +-----------------------------------------------+
       |
       v
  +-----------------------------------------------+
  |  RING 3 - Cross-LLM Consensus                 |
  |  Claude + Azure OpenAI + Ollama (LLaMA)       |
  |  disagreement => re-retrieve excluding suspect|
  +-----------------------------------------------+
       |
       v
  Trusted Answer
```

| Ring | Stage | Mechanism | Catches |
|------|-------|-----------|---------|
| **1 - Ingest Guard** | Document added to KB | Perplexity scoring + embedding-outlier detection + pattern match (verbatim query embedded) | Crude / templated poison at the door |
| **2 - Retrieval Scorer** | Query time | Source-provenance weighting + inter-document consistency + trust re-ranking | Poison that contradicts the consensus of clean docs |
| **3 - Cross-LLM Consensus** | Generation | Query 3 LLMs in parallel, flag disagreement, re-retrieve excluding suspects | Poison that slipped through rings 1-2 |

**Why it works:** to succeed, poison must defeat *all three independent checkpoints at once* — far harder than beating any single filter.

---

## 5. Tech stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.11 (venv) |
| Vector index | FAISS |
| Embeddings | `sentence-transformers` — `all-mpnet-base-v2` (768-dim, CPU mode on Mac) |
| Knowledge base | 5,000 Wikipedia docs (`wikimedia/wikipedia`, `20231101.en`) |
| LLM backends | Anthropic Claude · Azure OpenAI · Ollama (LLaMA 3.1 8B) |
| UI | Streamlit (attack demo, defense demo, side-by-side, forensic explorer, results dashboard) |
| Orchestration | Custom `LLMBackend` unified interface |

---

## 6. Repository structure

```
Major-Project-PoisonedRAG/
├── README.md                  <- you are here
├── docs/
│   ├── paper_summary.md        <- the paper, explained for the team
│   ├── gap_and_fix.md          <- what's missing + what we add
│   └── viva_qa.md              <- 60+ Q&A to prep every member
├── paper/                     <- the PDF + notes
├── knowledge_base/            <- build_kb.py, build_index.py
├── baseline/                  <- target_questions.json, generate_poison.py, inject_poison.py, measure_baseline_asr.py
├── defense/                   <- ring1_ingest_guard.py, ring2_retrieval_scorer.py, ring3_cross_llm.py
├── llm_backends/              <- unified_interface.py
├── evaluation/                <- eval harness + results
├── frontend/                  <- Streamlit app
├── slides/                    <- PoisonedRAG_Group6_Presentation.pptx
└── report/                    <- final written report
```

---

## 7. The 8 steps the professor requires

| # | Step | Status | Where |
|---|------|--------|-------|
| 1 | Update Excel with paper details | ☐ | course sheet |
| 2 | Read the paper | ☐ | `docs/paper_summary.md` |
| 3 | Analyze the problem | ☐ | `docs/paper_summary.md` §Problem |
| 4 | Understand the proposed solution | ☐ | `docs/paper_summary.md` §Attack |
| 5 | Identify the gap | ☐ | `docs/gap_and_fix.md` |
| 6 | Propose our own solution | ☐ | `docs/gap_and_fix.md` §RAG-Shield |
| 7 | Implement it | ☐ | `defense/`, `frontend/` |
| 8 | Demonstrate effectiveness | ☐ | `evaluation/`, live demo |

---

## 8. Team — Group 6

| Member | ID | Role |
|--------|----|----|
| Jeenal Chaudhary | G25AIT2027 | Intro + RAG background |
| Amit Singh | G25AIT2007 | Problem & threat model · Research |
| Sharvan Vittala | G25AIT2099 | Attack mechanics · Ring 1 |
| Sudeb Ghosh | G25AIT2113 | Attack deep-dive · Adversarial testing |
| Kosuru Yuvaraj | G25AIT2054 | Gap analysis · Ring 2 |
| Pujan Chakraborty | G25AIT2076 | RAG-Shield design · Evaluation |
| Rohit Patel | G25AIT2089 | Tech lead · Architecture · Implementation · Live demo |
| Vishnu Priya | G25AIT2128 | Frontend · Report · Demo video |

---

## 9. Links

- **Paper:** https://www.usenix.org/conference/usenixsecurity25/presentation/zou-poisonedrag
- **arXiv:** https://arxiv.org/abs/2402.07867
- **Official code:** https://github.com/sleeepeer/PoisonedRAG
- **Our fork:** https://github.com/rpaut03l/sleeepeer_PoisonedRAG

---

*Course: CSL6010 Cyber Security · Prof. Susil Kumar Mohanty · M.Tech AI · IIT Jodhpur*
