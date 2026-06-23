"""
ragshield_core.ring3_consensus
RING 3 - Cross-LLM Consensus. Runs at ANSWER time.

Query N LLMs with the same context. If they AGREE -> high confidence, return.
If they DISAGREE -> flag, drop the lowest-trust doc(s), re-retrieve/re-ask once.
Different model families don't get fooled identically, so disagreement is a
strong poison signal.
"""
from __future__ import annotations
from collections import Counter
from typing import Callable, Optional


class CrossLLMConsensus:
    def __init__(self, panel, agreement: float = 0.66):
        """panel = list[LLMBackend]; agreement = fraction needed to accept."""
        self.panel = panel
        self.agreement = agreement

    def _norm(self, s: str) -> str:
        return " ".join(s.lower().split())[:80]

    _NO_ANSWER = ("no answer","no mention", "not mentioned", "does not mention", "no information",
                  "cannot find", "can't find", "not in the provided", "does not provide",
                  "not contain", "i don't know", "i do not know", "unable to", "[error",
                  "dont have", "don't have")

    def _is_no_answer(self, s: str) -> bool:
        s = s.lower()
        return any(p in s for p in self._NO_ANSWER)

    def vote(self, question: str, context_docs: list[dict],
             candidates: Optional[list[str]] = None) -> dict:
        answers = []
        for llm in self.panel:
            try:
                a = llm.answer_with_context(question, context_docs, candidates)
            except Exception as e:
                a = f"[error: {e}]"
            answers.append({"llm": llm.name, "answer": a})
        substantive = [a for a in answers if not self._is_no_answer(a["answer"])]
        pool = substantive if substantive else answers
        norm = [self._norm(a["answer"]) for a in pool]
        tally = Counter(norm)
        top, count = tally.most_common(1)[0]
        if candidates:
            for a in pool:
                if any(self._norm(c) in self._norm(a["answer"]) or
                       self._norm(a["answer"]) in self._norm(c) for c in candidates):
                    top = self._norm(a["answer"]); count = tally.get(top, 1); break
        agree_n = sum(1 for a in answers if self._norm(a["answer"]) == top)
        frac = agree_n / len(answers)
        agreed = frac >= self.agreement
        winner = next(a["answer"] for a in pool if self._norm(a["answer"]) == top)
        return {"answers": answers, "agreement": round(frac, 2),
                "agreed": agreed, "answer": winner}

    def run(self, question: str, context_docs: list[dict],
            candidates: Optional[list[str]] = None,
            reretrieve: Optional[Callable[[list[dict]], list[dict]]] = None) -> dict:
        first = self.vote(question, context_docs, candidates)
        if first["agreed"] or reretrieve is None:
            first["reretrieved"] = False
            return first
        # disagreement -> drop lowest-trust doc(s) and try once more
        ranked = sorted(context_docs, key=lambda d: d.get("trust", d.get("score", 0)))
        suspects = ranked[: max(1, len(ranked) // 3)]
        cleaner = reretrieve(suspects)
        second = self.vote(question, cleaner, candidates)
        second["reretrieved"] = True
        second["dropped_suspects"] = [s.get("id") for s in suspects]
        return second
