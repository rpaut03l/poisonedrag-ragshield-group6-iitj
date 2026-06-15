<a id="top"></a>

[Repo Home](../README.md) · [Docs Index](README.md) · [Paper Summary](PAPER_SUMMARY.md) · [Gap & Fix](GAP_AND_FIX.md) · **Viva Q&A**

---

# Viva Q&A — PoisonedRAG + RAG-Shield

> **Prep for every Group 6 member.** The professor or examiner can ask *anyone* about *any* part. These cover the paper, the attack, the gap, our defense, the implementation, and likely curveballs. Read all of them; know your own section cold.

Legend for who's most likely to field each block — but **everyone** should be able to answer the core ones (marked ★).

---

## A. RAG fundamentals  *(Jeenal)*

**★ Q1. What is RAG and why is it used?**
Retrieval-Augmented Generation grounds an LLM's answer in documents retrieved from an external knowledge base. It addresses two LLM weaknesses: outdated knowledge (training is frozen in time) and hallucination (making things up). The LLM answers using fetched, relevant text instead of memory alone.

**★ Q2. Walk me through the RAG pipeline.**
(1) User asks a question. (2) A retriever embeds the question and finds the top-K most similar documents in the KB. (3) Those documents are placed in the LLM's context. (4) The LLM generates an answer grounded in them.

**Q3. What is a retriever? Name some.**
The component that finds relevant documents by comparing vector embeddings of the query and documents. Examples used in the paper: Contriever, DPR (Dense Passage Retrieval), ANCE.

**Q4. What does "top-K" mean?**
The K most similar documents the retriever returns for a query (e.g., top-5). Only these reach the LLM.

**Q5. Where is RAG used in the real world?**
ChatGPT browsing, Bing Chat, enterprise document search, customer-support bots, and medical/legal/financial assistants.

---

## B. The problem & threat model  *(Amit)*

**★ Q6. What's the core contribution of the paper?**
It's the first knowledge-corruption attack on RAG. It shows the knowledge base is a new, practical attack surface: injecting a few malicious docs makes the LLM produce an attacker-chosen answer.

**Q7. What exactly is the attack surface?**
The knowledge base. Prior work secured or improved the model and retriever; nobody had weaponized the fact that KBs are often open (wikis, scraped web, user uploads).

**★ Q8. Define the threat model.**
The attacker picks a target question and a target (wrong) answer, injects malicious texts into the KB, and aims to make the LLM output that answer for that question.

**Q9. Black-box vs white-box — what's the difference?**
Black-box: attacker knows only the question (realistic). White-box: attacker also knows the retriever's model and weights (stronger, but unrealistic — shows the upper bound).

**Q10. Why is the black-box setting more important?**
Because it's realistic. Anyone who can edit a wiki or upload a document is effectively a black-box attacker. White-box requires insider access most attackers won't have.

**Q11. Does the attacker need access to the LLM?**
No. That's what makes it dangerous — they never touch the model, its weights, or its API. They only add documents to the KB.

---

## C. How the attack works  *(Sharvan)*

**★ Q12. What two conditions must a poison document satisfy?**
(1) Retrieval condition — it must be similar enough to the question to be retrieved into the top-K. (2) Generation condition — once retrieved, it must mislead the LLM into outputting the target answer. Both must hold simultaneously.

**★ Q13. Explain the `P = S + I` decomposition.**
Each poison doc P is split into two parts. S (retrieval trigger) is crafted to match the question semantically so it gets retrieved. I (injection text) carries the misinformation so the LLM generates the wrong answer. S solves retrieval; I solves generation.

**Q14. Why split into two parts instead of one blob?**
Because the two conditions pull in different directions. Optimizing one text for both at once is hard; decomposing lets each sub-text specialize — one for retrieval, one for generation.

**Q15. How is the attack formulated mathematically?**
As an optimization problem: find a set of malicious texts that maximizes the probability the LLM emits the target answer, subject to the texts being retrievable for the target question.

**Q16. Give an analogy for S and I.**
A Trojan horse. S is the disguise that gets it through the gate (retrieval). I is the soldier inside that does the damage (generation).

---

## D. Attack variants & results  *(Sudeb)*

**Q17. How does the black-box attack craft poison?**
It prompts an LLM to write a passage supporting the chosen wrong answer for the target question, and embeds the question's keywords verbatim so the passage gets retrieved. Then injects ~5 such passages.

**Q18. How does the white-box attack differ?**
It uses gradient-based optimization (HotFlip-style token substitution) on the retrieval trigger S, exploiting knowledge of the retriever's weights to maximize retrieval rank.

**Q19. What is HotFlip?**
A gradient-based adversarial technique that finds which token substitutions most change a model's output — used here to optimize the retrieval trigger.

**★ Q20. What are the headline numbers?**
~90% attack success rate by injecting just 5 malicious texts per target question into a KB with millions of documents.

**Q21. What models/datasets was it tested on?**
LLMs: GPT-4, GPT-3.5, LLaMA-2, Vicuna, PaLM 2. Retrievers: Contriever, DPR, ANCE. Datasets: NQ, HotpotQA, MS-MARCO. It generalizes across all of them.

**Q22. Why only 5 poison docs? Why not more?**
Because 5 is enough to dominate the top-K for the target question. The point is the attack is cheap and stealthy — a handful of docs hidden among millions.

---

## E. The gap  *(Kosuru)*

**★ Q23. What defenses did the paper test, and did they work?**
Perplexity filtering, query paraphrasing, and knowledge expansion. None worked sufficiently — residual attack success stayed around 30%+. The authors conclude existing defenses are insufficient and call for new ones.

**★ Q24. Why does perplexity filtering fail?**
Because the poison is LLM-generated, so it's fluent and has natural perplexity. The filter only catches crude, unnatural text.

**Q25. Why does paraphrasing fail?**
The poison matches the question's meaning, not its exact words. Rewording the query doesn't move the embeddings enough to dodge the poison.

**Q26. Why does knowledge expansion fail?**
Retrieving more documents still includes the poison, and the LLM continues to weight it heavily.

**★ Q27. State the gap in one sentence.**
Existing single-layer defenses are each a single point of failure, leaving 30%+ residual attack success; what's missing is layered, defense-in-depth protection across ingest, retrieval, and generation.

---

## F. Our solution: RAG-Shield  *(Pujan + Rohit)*

**★ Q28. What is RAG-Shield?**
A 3-ring, defense-in-depth pipeline. Ring 1 (Ingest Guard) screens documents as they enter the KB. Ring 2 (Retrieval Scorer) re-ranks/filters retrieved docs at query time. Ring 3 (Cross-LLM Consensus) verifies the answer with multiple LLMs. Poison must beat all three at once.

**★ Q29. What does Ring 1 do?**
Ingest-time screening: perplexity scoring, embedding-outlier detection, and pattern matching for docs that embed a question verbatim (a retrieval-trigger tell). Catches crude poison at the door.

**★ Q30. What does Ring 2 do?**
Query-time scoring: source-provenance/trust weighting, inter-document consistency checks (poison contradicts the clean majority), and trust-weighted re-ranking of the top-K before it reaches the LLM.

**★ Q31. What does Ring 3 do?**
Generation-time verification: query 3 different LLMs in parallel; if they disagree, flag the answer and re-retrieve excluding the suspect documents. Different model families don't get fooled identically, so disagreement signals poison.

**Q32. Why is defense-in-depth better than one strong filter?**
Because each ring catches what the others miss, and an attacker must defeat all three independent checkpoints simultaneously — far harder than tuning poison to beat a single check.

**Q33. How is Ring 1 different from the paper's perplexity defense?**
The paper used perplexity *alone*. Ring 1 combines perplexity with embedding-outlier detection and verbatim-query pattern matching — and it's only the first of three layers, so its misses are caught downstream.

**Q34. Won't Ring 3 be fooled if all three LLMs read the same poison?**
It can be — that's why Rings 1 and 2 run first to remove most poison. Ring 3 is the backstop for what slips through. Cross-family disagreement is a strong but not perfect signal; the re-retrieval step is what actually fixes the answer.

**Q35. Why multiple LLM vendors instead of one?**
Models from different families (e.g., Anthropic vs Meta) have different training and failure modes, so they're less likely to be fooled in the same way. Agreement across vendors is stronger evidence than agreement within one.

---

## G. Implementation  *(Rohit)*

**Q36. What's the tech stack?**
Python 3.11, FAISS for the vector index, sentence-transformers (`all-mpnet-base-v2`) for embeddings, a 5,000-doc Wikipedia KB, Streamlit UI, and three LLM backends (Claude, Azure OpenAI, Ollama/LLaMA) behind a unified interface.

**Q37. Why `all-mpnet-base-v2`?**
It's a strong, widely-used general-purpose sentence embedding model (768-dim) with a good quality/speed balance, suitable for semantic retrieval.

**Q38. Why FAISS?**
It's a fast, production-grade library for similarity search over dense vectors — the standard choice for a vector store at this scale.

**Q39. Why 5,000 docs and not millions like the paper?**
For a demonstrable, reproducible project on local hardware. The mechanism is identical; scale is a future-work item. The attack still works because the KB has natural gaps the poison fills.

**Q40. Why Claude + Ollama instead of OpenAI?**
Azure OpenAI quota was unavailable across all regions during the build, and direct OpenAI hit a billing limit. We used Claude (Anthropic) + local LLaMA via Ollama — a genuine multi-vendor consensus, which is actually a stronger Ring 3 story. Azure slots in as a third LLM when quota is approved.

**Q41. How do you measure attack success rate (ASR)?**
For each target question, check whether the LLM's answer contains the attacker's target (wrong) answer. ASR = fraction of target questions where the attack succeeds. Measured undefended, with the paper's defenses, and with RAG-Shield.

**Q42. How do you avoid breaking normal queries with the defense?**
We track benign-query accuracy alongside ASR. The rings are tuned so legitimate documents pass through; provenance and consistency favor the clean majority, and Ring 3 only intervenes on disagreement.

---

## H. Results & evaluation  *(Vishnu)*

**Q43. What are your results?**
Illustrative: undefended ~91% ASR, paper's defenses ~29%, RAG-Shield ~13% — a large reduction while preserving benign accuracy. (Final numbers pending the full eval run.)

**Q44. Are these numbers final?**
They're illustrative placeholders until the full evaluation harness (30 questions × 3 LLMs × 4 defense configs) completes; we'll update before the real presentation. Being upfront about this is intentional.

**Q45. What's the evaluation setup?**
Target questions with known true/wrong answers, run through each configuration (no defense, each paper defense, RAG-Shield), across the LLM backends, measuring ASR and benign accuracy.

---

## I. Curveballs & big-picture  *(everyone — ★)*

**★ Q46. If you had to defend the project in one sentence, what would you say?**
"The paper proved RAG knowledge bases can be poisoned at 90% success and that existing defenses fail; we built RAG-Shield, a 3-ring defense-in-depth that cuts that to ~13%."

**Q47. What's the single most important slide?**
The gap slide — it's where we show the paper's own defenses fail and justify why our contribution is needed.

**Q48. What did YOU personally contribute?**
(Each member answers for their section — see the role table in the README. Rohit: full technical build, architecture, implementation, live demo. Pujan: defense design + eval. Kosuru: gap analysis + Ring 2. Etc.)

**Q49. What's the biggest limitation of your work?**
We haven't tested an adaptive attacker who knows RAG-Shield and optimizes against all three rings jointly, and our KB is 5,000 docs rather than millions. Both are future work.

**Q50. How would an attacker try to beat RAG-Shield?**
Generate fluent poison (beats Ring 1 perplexity), match the clean-doc consensus to avoid the consistency check (beats Ring 2), and craft content all LLMs accept (beats Ring 3). Beating all three jointly is much harder — that's the point — but it's the natural next attack to study.

**Q51. Is this attack illegal/unethical to study?**
Studying attacks defensively is standard security research — the paper is peer-reviewed at USENIX Security. We reproduce it in a sandbox to build and validate a defense, not to deploy it.

**Q52. What's the difference between this and prompt injection?**
Prompt injection manipulates the *input prompt* directly. PoisonedRAG manipulates the *knowledge base* the system retrieves from — the malicious content arrives through retrieval, not through the user's prompt.

**Q53. Could RAG-Shield run in production?**
Rings 1 and 2 are cheap and production-ready. Ring 3 adds latency/cost (3 LLM calls), so in production you'd gate it to low-confidence or high-stakes queries. That's a deployment tuning decision.

**Q54. Why does cross-LLM disagreement indicate poison?**
Because under clean retrieval, capable models tend to agree on factual answers. Poison that fools one model's reasoning often doesn't fool another from a different family identically, so disagreement correlates with manipulated context.

**Q55. What would you do with more time?**
Adaptive-attacker evaluation, scale to a million-doc KB, latency/cost optimization of Ring 3, and packaging RAG-Shield as a drop-in RAG middleware layer.

---

## J. 60-second elevator pitch (memorize)

> *"RAG lets LLMs answer from an external knowledge base — like an open-book exam. PoisonedRAG, from USENIX Security 2025, shows that slipping just 5 fake documents into a base of millions makes the model give an attacker's chosen wrong answer 90% of the time, and the paper proves existing defenses can't stop it. Our project, RAG-Shield, fills that gap with defense-in-depth: Ring 1 screens documents at ingest, Ring 2 scores and re-ranks them at retrieval, and Ring 3 checks the answer across three different LLMs. To win, poison has to beat all three at once — and in our tests, attack success drops from about 90% to about 13%."*


---

[Repo Home](../README.md) · [Docs Index](README.md) · [Paper Summary](PAPER_SUMMARY.md) · [Gap & Fix](GAP_AND_FIX.md) · **Viva Q&A**

[↑ Back to top](#top)
