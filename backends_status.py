"""
backends_status.py — ping each LLM backend and show which are live.
Run:  python backends_status.py
Use this right before the demo so you KNOW what Ring 3 will use.
"""
import os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from dotenv import load_dotenv; load_dotenv()
except Exception:
    pass


def check(name, fn):
    t0 = time.time()
    try:
        out = fn()
        ms = int((time.time() - t0) * 1000)
        print(f"  [LIVE] {name:18} -> {str(out).strip()[:30]!r}  ({ms} ms)")
        return True
    except Exception as e:
        msg = str(e).splitlines()[0][:70]
        print(f"  [DOWN] {name:18} -> {msg}")
        return False


def claude():
    from anthropic import Anthropic
    r = Anthropic().messages.create(model="claude-haiku-4-5", max_tokens=5,
        messages=[{"role": "user", "content": "say OK"}])
    return r.content[0].text


def ollama():
    from openai import OpenAI
    c = OpenAI(base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"), api_key="ollama")
    r = c.chat.completions.create(model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        max_tokens=5, messages=[{"role": "user", "content": "say OK"}])
    return r.choices[0].message.content


def vllm():
    base = os.getenv("VLLM_BASE_URL")
    if not base:
        raise RuntimeError("VLLM_BASE_URL not set (skipped)")
    from openai import OpenAI
    c = OpenAI(base_url=base, api_key=os.getenv("VLLM_API_KEY", "vllm"))
    r = c.chat.completions.create(model=os.getenv("VLLM_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct"),
        max_tokens=5, messages=[{"role": "user", "content": "say OK"}])
    return r.choices[0].message.content


def azure():
    if not (os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT")):
        raise RuntimeError("Azure vars not set (skipped)")
    from openai import AzureOpenAI
    c = AzureOpenAI(api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"))
    r = c.chat.completions.create(model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        max_tokens=5, messages=[{"role": "user", "content": "say OK"}])
    return r.choices[0].message.content


if __name__ == "__main__":
    demo = os.getenv("DEMO_MODE", "1") not in ("0", "false", "False")
    print(f"\nDEMO_MODE={os.getenv('DEMO_MODE','1')}  ->  ", end="")
    print("DEMO mode: Ring 3 uses 3 MOCK LLMs (no network)\n" if demo
          else "LIVE mode: Ring 3 uses the live backends below\n")
    print("Pinging backends:")
    live = []
    if check("Claude (API)", claude): live.append("Claude")
    if check("Ollama (local)", ollama): live.append("LLaMA")
    if check("vLLM (self-host)", vllm): live.append("vLLM")
    if check("Azure OpenAI", azure): live.append("Azure")
    print(f"\nLive backends: {live or 'none (demo mode will use mocks)'}")
    if not demo and len(live) < 2:
        print("WARNING: live mode wants >=2 backends for a real consensus. "
              "Start Ollama or add another, or run with DEMO_MODE=1.")
