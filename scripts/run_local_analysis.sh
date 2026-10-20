#!/bin/bash
# Mac Apple Silicon FCC local LLM census; checkpoint and push to existing GitHub.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MODEL="ibm/granite4.2:8b"
OUT="data/llm_census_mac"
PREVIEW="docs/data/llm_mac_exploratory.json"
AUDIT="docs/data/llm_mac_audit_queue.json"
ONCE=0
case "${1:-}" in
  "") ;;
  --once) ONCE=1 ;;
  -h|--help) echo "Run: bash scripts/run_local_analysis.sh [--once]"; exit 0 ;;
  *) echo "Unknown option"; exit 2 ;;
esac
if [[ "$(uname -s)" != "Darwin" ]]; then echo "This setup is intended for macOS."; exit 1; fi
if [[ "$(git branch --show-current)" != "main" ]]; then echo "Checkout the main branch first."; exit 1; fi
if ! command -v python3 >/dev/null 2>&1; then echo "Python 3 is required."; exit 1; fi
echo "Updating source and analysis pipeline..."
git pull --ff-only origin main
if [[ -x /opt/homebrew/bin/brew ]]; then export PATH="/opt/homebrew/bin:$PATH"; fi
if ! command -v ollama >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "Installing Ollama with Homebrew..."
    brew install ollama
  else
    echo "Install the Ollama macOS app once from https://ollama.com/download/mac"
    echo "Open it, then rerun this exact command."
    open "https://ollama.com/download/mac" || true
    exit 1
  fi
fi
mkdir -p "$OUT" docs/data logs
if ! curl -fsS --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "Starting local Ollama server..."
  nohup ollama serve >logs/ollama_mac.log 2>&1 </dev/null &
  for i in $(seq 1 50); do
    if curl -fsS --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then break; fi
    sleep 2
  done
fi
if ! curl -fsS --max-time 5 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "Ollama did not start. See logs/ollama_mac.log or launch the Ollama app."
  exit 1
fi
echo "Verifying US open-source IBM Granite 4.2 8B (~5.3 GB first download)..."
ollama pull "$MODEL"
python3 -m unittest discover -s tests -p test_llm_census.py -q

pending() {
  python3 -m scripts.llm_census --input-dir data/fcc_corpus --out-dir "$OUT"     --model "$MODEL" --chunk-size 6500 --chunk-overlap 350 --pending-only |
    python3 -c 'import json,sys; print(json.loads(sys.stdin.read().strip().splitlines()[-1])["pending"])'
}
upload() {
  # Regenerate summary after exact-text checkpoint reuse, even on the last batch.
  python3 - <<'PY'
from pathlib import Path
from scripts.llm_census import load_corpus,load_book,summarize,atomic_json
records=load_corpus(Path('data/fcc_corpus'),None,'ocr_candidate_v1','augmented')
d=Path('data/llm_census_mac')
summary=summarize(records,d,load_book(),'ibm/granite4.2:8b',6500,350)
atomic_json(Path('docs/data/llm_mac_exploratory.json'),summary)
print('Complete model classifications:',summary['completed_filings'])
PY
  if [[ -f "$OUT/suggested_human_audit.json" ]]; then
    cp "$OUT/suggested_human_audit.json" "$AUDIT"
  fi
  git add -A -- "$OUT" "$PREVIEW"
  if [[ -f "$AUDIT" ]]; then git add -A -- "$AUDIT"; fi
  if git diff --cached --quiet; then echo "No new results to upload."; return; fi
  if [[ -z "$(git config user.name || true)" ]]; then git config user.name "FCC Corpus Research"; fi
  if [[ -z "$(git config user.email || true)" ]]; then git config user.email "fcc-research@users.noreply.github.com"; fi
  git commit -m "Checkpoint local Granite 8B FCC argument and stance extraction"
  git pull --rebase origin main
  git push origin HEAD:main
  echo "Upload complete: https://shreyammm.github.io/e-rate/llm.html"
}
n=0
while true; do
  left="$(pending)"
  echo "=========================================="
  echo "$left of 3,231 FCC filing records remain to be processed."
  if [[ "$left" == "0" ]]; then upload; echo "Full corpus classified."; break; fi
  n=$((n+1)); echo "Starting local batch $n; keep this Mac awake."
  code=0
  python3 -m scripts.llm_census --input-dir data/fcc_corpus     --out-dir "$OUT" --publish-preview "$PREVIEW"     --model "$MODEL" --chunk-size 6500 --chunk-overlap 350     --limit 35 --max-chunks-per-filing 8 --max-minutes 40 || code=$?
  upload
  echo "Batch $n uploaded; $(pending) filings remain."
  if [[ "$code" != "0" ]]; then
    echo "Retryable inference errors occurred. Previous work is safe on disk and GitHub."
    echo "Rerun the same command; analysis resumes from the saved checkpoints."
    exit "$code"
  fi
  if [[ "$ONCE" == "1" ]]; then echo "One batch uploaded. Rerun without --once to continue."; break; fi
  if [[ "$n" -ge 500 ]]; then echo "Safety stop; rerun to resume."; break; fi
done
