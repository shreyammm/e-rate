#!/usr/bin/env python3
"""Chromium smoke test for the complete published Kaggle Research Studio.
Runs without GPT inference; checks live DOM with actual JSON outputs.
Use: python tests/smoke_kaggle_page.py
Requires: playwright and installed chromium.
"""
from __future__ import annotations
import http.server
import pathlib
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

ROOT=pathlib.Path(__file__).resolve().parents[1]
PORT=18742
EXPECTED=14835

def run():
    cmd=[sys.executable,"-m","http.server",str(PORT),"--bind","127.0.0.1","--directory",str(ROOT/"docs")]
    server=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    try:
        time.sleep(1.5)
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
            page=browser.new_page(viewport={"width":1440,"height":950})
            exceptions=[]
            page.on("pageerror",lambda e:exceptions.append(str(e)))
            page.goto(f"http://127.0.0.1:{PORT}/kaggle.html",wait_until="domcontentloaded",timeout=120000)
            page.wait_for_function(
                "()=>document.querySelector('#kr-status')?.textContent.includes('Loaded and checked')",
                timeout=120000)
            assert "14,835" in page.locator("#kr-status").inner_text()
            out=ROOT/"artifacts"
            out.mkdir(exist_ok=True)
            page.screenshot(path=str(out/"kaggle-research-smoke.png"),full_page=True)
            assert page.locator("#kr-kpis .kr-kpi").count()==6
            assert page.locator("#kr-cluster-list .kr-cluster-item").count()==42
            assert "Source-linked evidence ledger" in page.locator("#ledger").inner_text()
            assert "14,835" in page.locator("#kr-ledger-count").inner_text()
            # Question scans the complete 14,835-row index.
            page.fill("#kr-question","What concerns do commenters raise about screen time and E-Rate funding?")
            page.click("#kr-ask")
            assert str(EXPECTED) in page.locator("#kr-answer-status").inner_text().replace(",","")
            assert "Question-specific evidence map" in page.locator("#kr-answer").inner_text()
            assert not page.locator("#kr-llm-run").is_disabled()
            # Inspect a real multi-issue filing.
            page.fill("#kr-filing-id","26110080734")
            page.click("#kr-filing-open")
            assert "Alaska" in page.locator("#kr-filing-profile").inner_text()
            assert "20" in page.locator("#kr-filing-status").inner_text()
            # Compare a known screen-time policy issue and show explanation.
            page.select_option("#kr-issue-select","screen_time_condition")
            assert "filings" in page.locator("#kr-issue-summary").inner_text().lower()
            # Sunset polarity risk must remain quarantined.
            page.select_option("#kr-issue-select","erate_sunset")
            assert "withheld" in page.locator("#kr-issue-summary").inner_text().lower()
            # Risk index identifies 417 long-window filings.
            page.select_option("#kr-qa-kind","prioritized")
            assert "417" in page.locator("#kr-qa-count").inner_text()
            # Filtered source ledger is functional.
            page.fill("#kr-ledger-q","26110080734")
            assert "26110080734" in page.locator("#kr-ledger-results").inner_text()
            page.fill("#kr-ledger-q","")
            # Audit queue rendered and browseable.
            assert page.locator("#kr-audit-list article").count()>0
            assert not exceptions,"Unhandled browser errors: "+repr(exceptions)
            out=ROOT/"artifacts"
            out.mkdir(exist_ok=True)
            page.screenshot(path=str(out/"kaggle-research-smoke.png"),full_page=True)
            print("SUCCESS: all 14,835 Kaggle claims loaded; query, arguments, profile, audit, stance and QA views rendered.")
            browser.close()
    finally:
        server.terminate()
        try:server.wait(timeout=4)
        except subprocess.TimeoutExpired:server.kill()

if __name__=="__main__":run()
