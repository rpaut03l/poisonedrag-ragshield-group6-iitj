"""
ragshield_core.rag_shield
The orchestrator. Wires Retriever + Ring1 + Ring2 + Ring3 into one pipeline
and exposes a single `answer()` call plus a `trace()` call that returns every
ring's decision for the forensic UI.

Usage:
    shield = RAGShield().setup(poisoned=True)
    out = shield.answer("Who founded Tesla Motors?", defense=True,
                        candidates=["Martin Eberhard", "Nikola Jones"])
"""
from __future__ import annotations
from typing import Optional

from .retriever import Retriever, load_targets
from .ring1_ingest import IngestGuard
from .ring2_retrieval import RetrievalScorer
from .ring3_consensus import CrossLLMConsensus
from .llm_backends import make_consensus_panel
from . import config


class RAGShield:
    def __init__(self, top_k: int = None):
        self.top_k = top_k or config.TOP_K
        self.retriever = Retriever()
        self.ingest = IngestGuard()
        self.scorer = RetrievalScorer()
        self.panel = make_consensus_panel()
        self.consensus = CrossLLMConsensus(self.panel)
        self._questions = [t["question"] for t in load_targets()]

    # ---------- setup ----------
    def setup(self, poisoned: bool = True):
        """
        Load KB and (optionally) inject poison into the corpus.
        NOTE: Ring 1 is NOT applied here. It is applied per-query only when
        defense=True, so the no-defense baseline genuinely sees the poison
        (otherwise the attack could never 'succeed' and the demo would lie).
        """
        self.retriever.load_kb()
        self.poisoned = poisoned
        if poisoned:
            self.retriever.load_poison()
            self.retriever.inject_poison()   # builds index with poison included
        else:
            self.retriever.build()
        self._ring1_blocked = []
        return self

    # ---------- main entry ----------
    def answer(self, question: str, defense: bool = True,
               candidates: Optional[list[str]] = None) -> dict:
        trace = self.trace(question, defense=defense, candidates=candidates)
        return {"answer": trace["answer"], "defense": defense, "trace": trace}

    def trace(self, question: str, defense: bool = True,
              candidates: Optional[list[str]] = None) -> dict:
        retrieved = self.retriever.retrieve(question, self.top_k)
        t = {"question": question, "defense": defense, "retrieved": retrieved,
             "ring1_blocked": []}

        if not defense:
            # plain RAG: first LLM answers directly on the RAW (poisoned) retrieval
            llm = self.panel[0]
            t["answer"] = llm.answer_with_context(question, retrieved, candidates)
            t["mode"] = "no-defense"
            return t

        # ----- DEFENSE ON -----
        # Ring 1: screen the retrieved docs at query time (ingest-style checks)
        kept1, blocked1 = self.ingest.filter_corpus(retrieved, self._questions)
        t["ring1_blocked"] = blocked1
        retrieved = kept1 if kept1 else retrieved   # never strip everything

        # Ring 2: rescore + drop low-trust
        kept, dropped = self.scorer.filter(retrieved)
        t["ring2_kept"], t["ring2_dropped"] = kept, dropped

        # Ring 3: cross-LLM consensus with re-retrieval on disagreement
        def reretrieve(suspects):
            ids = {s.get("id") for s in suspects}
            return [d for d in kept if d.get("id") not in ids]

        verdict = self.consensus.run(question, kept, candidates, reretrieve)
        t["ring3"] = verdict
        t["answer"] = verdict["answer"]
        t["mode"] = "rag-shield"
        return t
