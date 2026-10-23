#!/usr/bin/env python3
"""Browser integration test using the REAL full-source E-Rate candidate index."""
from __future__ import annotations
import pathlib
import shutil
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

ROOT=pathlib.Path(__file__).resolve().parents[1]
PORT=18746

def main():
 server=subprocess.Popen([sys.executable,'-m','http.server',str(PORT),'--bind','127.0.0.1','--directory',str(ROOT/'docs')],
   stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
 try:
  time.sleep(1.5)
  with sync_playwright() as p:
   installed=next((shutil.which(x) for x in ('google-chrome','chromium','chromium-browser') if shutil.which(x)),None)
   browser=p.chromium.launch(headless=True,executable_path=installed,args=['--no-sandbox']) if installed else p.chromium.launch(headless=True,args=['--no-sandbox'])
   page=browser.new_page(viewport={'width':1400,'height':850},accept_downloads=True)
   errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto('http://127.0.0.1:'+str(PORT)+'/positions.html',wait_until='domcontentloaded',timeout=120000)
   page.wait_for_function("() => document.querySelector('#pp-status')?.textContent.includes('Scanned all')",timeout=120000)
   assert '3,231' in page.locator('#pp-status').inner_text()
   assert page.locator('#pp-axes .pp-axis-card').count()==4
   assert page.locator('#pp-results .pp-filing').count()>0
   # All figures are candidate matches, not fake audited vote totals.
   assert 'candidate' in page.locator('#pp-count').inner_text().lower()
   # Find the suspected-misuse cases and verify the explicit accusation warning.
   page.select_option('#pp-axis','misuse')
   page.select_option('#pp-label','general_misuse_allegation')
   assert page.locator('#pp-results .pp-filing').count()>0
   assert 'not an established finding' in page.locator('#pp-results .pp-flag-note').first.inner_text().lower()
   # Select an actual screen concern, review original evidence and save ONE reviewer decision.
   page.select_option('#pp-axis','screen_harms')
   page.select_option('#pp-label','affirmative_harm_concern')
   card=page.locator('#pp-results .pp-filing').first
   assert card.count()==1
   card.locator('.pp-sources input[type=radio]').first.check()
   card.locator('.pp-review-grid input[type=checkbox]').first.check()
   card.locator('.pp-review textarea').fill('After reading this source, the commenter affirmatively raises screen-use harms.')
   card.locator('.pp-review .pp-check input[type=checkbox]').last.check()
   card.locator('.pp-review button').click()
   assert 'Saved locally' in card.locator('.pp-saved').inner_text()
   with page.expect_download() as transfer:
    page.click('#pp-export')
   assert transfer.value.suggested_filename.endswith('.csv')
   out=ROOT/'artifacts'
   out.mkdir(exist_ok=True)
   page.screenshot(path=str(out/'positions-qa-smoke.png'),full_page=False)
   assert not errors,'Browser JavaScript errors: '+str(errors)
   print('SUCCESS: all original records loaded; four panels, misuse cautions, source evidence, one-reader save and CSV export functional.')
   browser.close()
 finally:
  server.terminate()
  try:server.wait(timeout=4)
  except subprocess.TimeoutExpired:server.kill()

if __name__=='__main__':main()
