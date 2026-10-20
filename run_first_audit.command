#!/bin/zsh
set -e
cd "${0:A:h}"
CORPUS="$HOME/Downloads/fcc_complete_corpus"
if [ ! -f "$CORPUS/filings_manifest.csv" ]; then
  echo "Cannot find $CORPUS/filings_manifest.csv"
  echo 'Place your existing corpus in ~/Downloads/fcc_complete_corpus.'
  exit 1
fi
python3 -m erate.engine --corpus "$CORPUS"
python3 scripts/ocr_triage.py --corpus "$CORPUS"
python3 -m erate.annotation sample --corpus "$CORPUS"
echo '\nAUDIT COMPLETE. No original corpus files changed.'
echo 'To view the dashboard: python3 -m pip install -r requirements-dashboard.txt'
echo 'Then: python3 -m streamlit run app.py -- --corpus ~/Downloads/fcc_complete_corpus'
