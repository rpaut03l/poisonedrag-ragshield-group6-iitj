#!/usr/bin/env bash
# run_live.sh — launch LITE-LIVE (real local LLMs, light retriever, watcher off).
set -e
pkill -9 -f streamlit 2>/dev/null || true
lsof -ti :8501,:8502 2>/dev/null | xargs kill -9 2>/dev/null || true
export SETUPTOOLS_USE_DISTUTILS=stdlib OMP_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false KMP_DUPLICATE_LIB_OK=TRUE
export PYTORCH_ENABLE_MPS_FALLBACK=1
export DEMO_MODE=0 RETRIEVER=tfidf
echo "==> LITE-LIVE  ->  http://localhost:8502"
.venv/bin/python -m streamlit run frontend/app.py \
  --server.port 8502 --server.headless true \
  --server.fileWatcherType none --server.runOnSave false
