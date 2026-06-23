"""
ragshield_core.llm_backends
One interface, four backends:
  - "anthropic"    : Claude (real API)
  - "ollama"       : local LLaMA via Ollama (OpenAI-compatible)
  - "azure_openai" : Azure OpenAI (real API)
  - "mock"         : heuristic, no network. Reads the retrieved context and
                     returns whichever candidate answer the context best supports.
                     Each mock instance has a "susceptibility" so different mock
                     LLMs can DISAGREE under poison — which is what powers the
                     Ring-3 cross-LLM consensus demo without any API.

The RAG answer call is `answer_with_context(question, context_docs, candidates)`.
`candidates` is optional [true_answer, wrong_answer]; the mock uses it to decide.
"""
from __future__ import annotations
import os, re
from typing import Optional


class LLMBackend:
    def __init__(self, mode: str = "mock", model: Optional[str] = None,
                 susceptibility: float = 0.5, name: Optional[str] = None):
        self.mode = mode
        self.susceptibility = susceptibility  # 0..1, higher = more easily fooled
        self.name = name or mode
        self.model = model
        self._client = None

        if mode == "anthropic":
            from anthropic import Anthropic
            self._client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.model = model or "claude-haiku-4-5"
            self.name = name or f"Claude ({self.model})"
        elif mode == "ollama":
            from openai import OpenAI
            self._client = OpenAI(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                api_key="ollama")
            self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1:8b")
            self.name = name or f"LLaMA ({self.model})"
        elif mode == "azure_openai":
            from openai import AzureOpenAI
            self._client = AzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"))
            self.model = model or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
            self.name = name or f"Azure ({self.model})"
        elif mode == "mock":
            self.name = name or "Mock-LLM"
        else:
            raise ValueError(f"Unknown LLM mode: {mode}")

    # -- low-level completion (real backends) --
    def _complete(self, prompt: str, max_tokens: int = 200, temperature: float = 0.2) -> str:
        if self.mode == "anthropic":
            r = self._client.messages.create(
                model=self.model, max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}])
            return r.content[0].text
        # OpenAI-compatible (ollama / azure)
        r = self._client.chat.completions.create(
            model=self.model, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "user", "content": prompt}])
        return r.choices[0].message.content

    # -- RAG answer with retrieved context --
    def answer_with_context(self, question: str, context_docs: list[dict],
                            candidates: Optional[list[str]] = None) -> str:
        if self.mode == "mock":
            return self._mock_answer(question, context_docs, candidates)

        context = "\n\n".join(
            f"[Doc {i+1}] {d.get('title','')}\n{d.get('text','')}"
            for i, d in enumerate(context_docs))
        prompt = (
            "Answer the question using ONLY the context documents. "
            "Be concise (one short sentence).\n\n"
            f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:")
        return self._complete(prompt).strip()

    # -- heuristic mock: lets the demo run with zero dependencies --
    def _mock_answer(self, question: str, context_docs: list[dict],
                     candidates: Optional[list[str]]) -> str:
        blob = " ".join(d.get("text", "") for d in context_docs).lower()
        if candidates and len(candidates) == 2:
            true_ans, wrong_ans = candidates
            t = blob.count(true_ans.lower())
            w = blob.count(wrong_ans.lower())
            # weight wrong-answer mentions by this model's susceptibility
            w_eff = w * (0.4 + 1.2 * self.susceptibility)
            if w_eff > t:
                return wrong_ans
            if t > 0:
                return true_ans
            return "I don't have enough information."
        # no candidates: return the most frequent capitalized phrase as a guess
        m = re.findall(r"[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)*", " ".join(
            d.get("text", "") for d in context_docs))
        return max(set(m), key=m.count) if m else "Unknown"


def make_consensus_panel(mode_for_real: Optional[str] = None) -> list[LLMBackend]:
    """
    Build the 3-LLM panel used by Ring 3.
    In demo mode: 3 mock LLMs with DIFFERENT susceptibilities, so under poison
    they disagree (the whole point of cross-LLM consensus).
    In real mode: Claude + Ollama (+ Azure if configured).
    """
    from .config import demo_mode, available_backends
    if demo_mode():
        return [
            LLMBackend("mock", susceptibility=0.85, name="Mock-A (weak)"),
            LLMBackend("mock", susceptibility=0.45, name="Mock-B (medium)"),
            LLMBackend("mock", susceptibility=0.15, name="Mock-C (robust)"),
        ]
    panel, avail = [], available_backends()
    if "anthropic" in avail:
        panel.append(LLMBackend("anthropic", name="Claude"))
    panel.append(LLMBackend("ollama", name="LLaMA"))
    if "azure_openai" in avail:
        panel.append(LLMBackend("azure_openai", name="Azure-GPT"))
    return panel or [LLMBackend("mock", name="Mock-fallback")]
