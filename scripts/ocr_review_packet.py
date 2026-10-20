#!/usr/bin/env python3
"""Create an OFFLINE, private OCR page-versus-transcript review packet.

The packet contains document images and OCR text. It MUST remain on the user's Mac.
It does not modify original documents, OCR transcripts or filing manifests.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from erate.engine import local_path, read_csv, sha256
from scripts.recover_pdf_ocr import evidence_ready


def safe_fcc_link(url: str) -> str:
    try:
        u = urlsplit(url)
        if (u.scheme == 'https' and u.netloc == 'www.fcc.gov'
                and u.path.startswith('/ecfs/document/') and not u.username):
            return url
    except ValueError:
        pass
    return ''


def keys_for_review(sample: list[dict], qc: list[dict], limit: int, high_only: bool) -> list[tuple[str, str]]:
    if limit < 1:
        raise ValueError('limit must be positive')
    priority = [(r['submission_id'], r['document_number']) for r in qc
                if r.get('review_priority') == 'high']
    regular = [(r['submission_id'], r['document_number']) for r in sample]
    keys = priority if high_only else priority + regular
    unique = list(dict.fromkeys(keys))
    return unique[:limit]


def render_packet(base: Path, limit: int = 20, dpi: int = 95, high_only: bool = False) -> tuple[Path, int, int]:
    import pymupdf

    base = base.expanduser().resolve()
    audit = base / 'analysis_observatory'
    out = audit / 'ocr_recovery'
    sample, _ = read_csv(out / 'ocr_review_sample_generated.csv')
    qc, _ = read_csv(out / 'ocr_qc_documents.csv')
    manifest, _ = read_csv(out / 'run_manifest.csv')
    rows = {(r['submission_id'], r['document_number']): r for r in manifest}
    qc_rows = {(r['submission_id'], r['document_number']): r for r in qc}
    keys = keys_for_review(sample, qc, limit, high_only)
    if not keys:
        raise ValueError('No OCR documents found in the review selection')

    sheets = []
    total_pages = 0
    for sid, number in keys:
        row = rows.get((sid, number))
        quality = qc_rows.get((sid, number))
        if not row or not quality:
            raise ValueError(f'No OCR manifest or quality record: {sid}/{number}')
        source = local_path(base, row.get('original_path', ''))
        if source is None or not source.is_file():
            raise FileNotFoundError(f'Original PDF missing: {sid}/{number}')
        original_hash = sha256(source.read_bytes())
        if not evidence_ready(out, row, original_hash, row.get('ocr_engine', '')):
            raise ValueError(f'OCR evidence or original SHA-256 mismatch: {sid}/{number}')
        ev_rel = Path(row['evidence_path'])
        ev_path = (out / ev_rel).resolve()
        if not ev_path.is_relative_to(out.resolve()):
            raise ValueError('Unsafe OCR evidence path')
        evidence = json.loads(ev_path.read_text(encoding='utf-8'))
        pages_evidence = evidence.get('page_results', [])

        panels = []
        with pymupdf.open(source) as pdf:
            if len(pdf) != len(pages_evidence):
                raise ValueError(f'Page count differs between PDF and OCR evidence: {sid}/{number}')
            for idx, page in enumerate(pdf):
                scale = dpi / 72
                area = page.rect.width * page.rect.height * scale * scale
                if area > 3_000_000:
                    scale *= (3_000_000 / area) ** .5
                pix = page.get_pixmap(
                    matrix=pymupdf.Matrix(scale, scale),
                    colorspace=pymupdf.csRGB, alpha=False)
                image = base64.b64encode(pix.tobytes('png')).decode('ascii')
                text = '\n'.join(
                    str(line.get('text', '')) for line in pages_evidence[idx].get('lines', []))
                empty = not text.strip()
                panel = (
                    '<div class="page"><div class="pagehead">Page '
                    + str(idx + 1) + (' — EMPTY OCR' if empty else '')
                    + '</div><div class="columns"><img alt="Original page '
                    + str(idx + 1) + '" src="data:image/png;base64,' + image
                    + '"><pre>' + html.escape(text)
                    + '</pre></div></div>'
                )
                panels.append(panel)
                total_pages += 1

        url = safe_fcc_link(row.get('source_url', ''))
        link = ('<a target="_blank" rel="noopener noreferrer" href="'
                + html.escape(url, quote=True) + '">Original FCC filing</a>') if url else ''
        flags = html.escape(quality.get('quality_flags', 'none') or 'none')
        sid_text = html.escape(sid, quote=True)
        n_text = html.escape(number, quote=True)
        sheets.append(
            '<section class="review" data-sid="' + sid_text
            + '" data-number="' + n_text + '"><h2>Filing ' + sid_text
            + ' · Attachment ' + n_text + '</h2><p>' + link
            + ' · OCR characters: ' + html.escape(row.get('ocr_chars', '0'))
            + ' · Flags: ' + flags + '</p>'
            + '<div class="controls"><label>Review result '
            + '<select class="decision">'
            + '<option value="pending">Pending</option>'
            + '<option value="accurate">Accurate on pages reviewed</option>'
            + '<option value="minor_problems">Minor corrections needed</option>'
            + '<option value="major_problems">Major transcription problems</option>'
            + '<option value="missing_content">Visible content missing from OCR</option>'
            + '<option value="needs_investigation">Needs investigation</option>'
            + '</select></label><label>Empty OCR pages '
            + '<select class="blank"><option value="not_reviewed">Not reviewed</option>'
            + '<option value="legitimately_blank">Confirmed blank in source</option>'
            + '<option value="missed_visible_content">Missed visible content</option>'
            + '<option value="not_applicable">No empty OCR pages</option>'
            + '</select></label><label>Notes <textarea class="notes" rows="2"'
            + ' placeholder="What did you check? Any names, negations, numbers,'
            + ' missing pages, or reading-order problems?"></textarea></label></div>'
            + ''.join(panels) + '</section>'
        )

    js = r'''
function quoted(x) { return '"' + String(x).replace(/"/g,'""') + '"'; }
document.getElementById('export').addEventListener('click', () => {
  const reviewer = document.getElementById('reviewer').value.trim();
  const table = [['submission_id','document_number','review_status',
      'blank_pages_review','reviewer','review_notes','reviewed_utc']];
  for (const sec of document.querySelectorAll('section.review')) {
    table.push([sec.dataset.sid, sec.dataset.number,
      sec.querySelector('.decision').value,
      sec.querySelector('.blank').value,
      reviewer, sec.querySelector('.notes').value,
      new Date().toISOString()]);
  }
  const csv = table.map(row => row.map(quoted).join(',')).join('\r\n');
  const blob = new Blob([csv],{type:'text/csv;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'ocr_human_reviews.csv';
  a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),1000);
});
'''
    css = '''
body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif;
max-width:1500px;margin:auto;padding:24px;background:#f6f7f9;color:#222}
header{padding:16px 20px;background:white;position:sticky;top:0;border:1px solid #bbb;z-index:3}
section{background:white;margin:26px 0;padding:18px;border:1px solid #ccc;border-radius:7px}
h1,h2{margin:6px 0 12px}p{line-height:1.5}
button,select,textarea,input{font:inherit;padding:7px}
button{background:#164b7e;color:white;border:0;border-radius:4px;cursor:pointer}
.controls{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:15px 0}
.controls label{display:flex;flex-direction:column;gap:5px}
.controls label:last-child{grid-column:1/-1}
.page{margin:20px 0}.pagehead{font-weight:600;background:#e5ebf2;padding:8px}
.columns{display:grid;grid-template-columns:1fr 1fr;gap:15px;align-items:start}
.columns img{display:block;max-width:100%;border:1px solid #ddd}
.columns pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.55 ui-monospace,monospace;
max-height:900px;overflow:auto;border:1px solid #ddd;padding:12px;background:#fff}
@media(max-width:850px){.columns{grid-template-columns:1fr}}
'''
    packet = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
              '<meta name="viewport" content="width=device-width,initial-scale=1">'
              '<title>Private OCR review packet</title><style>' + css
              + '</style></head><body><header><h1>Local OCR review packet</h1>'
              '<p>Private: contains original document images and recognized text. '
              'Stay offline. This is a visual review tool, not an accuracy certificate. '
              'A document marked accurate means only the pages you actually inspected.</p>'
              '<label>Reviewer <input id="reviewer" placeholder="Reviewer ID"></label> '
              '<button id="export">Download review decisions (CSV)</button>'
              '</header>' + ''.join(sheets) + '<script>' + js
              + '</script></body></html>')
    output = out / ('ocr_review_packet_high_priority.html' if high_only
                     else 'ocr_review_packet_sample.html')
    output.write_text(packet, encoding='utf-8')
    return output, len(keys), total_pages


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus', type=Path,
                   default=Path.home() / 'Downloads/fcc_complete_corpus')
    p.add_argument('--limit', type=int, default=20)
    p.add_argument('--dpi', type=int, default=95)
    p.add_argument('--high-priority-only', action='store_true')
    args = p.parse_args()
    if args.limit < 1 or args.limit > 40:
        p.error('--limit must be from 1 to 40')
    if args.dpi < 72 or args.dpi > 150:
        p.error('--dpi must be from 72 to 150')
    filename, documents, pages = render_packet(
        args.corpus, args.limit, args.dpi, args.high_priority_only)
    print(f'Private review packet: {filename} ({documents} PDFs, {pages} pages)')
    print('Open with: open ' + str(filename))
    print('Never commit this HTML or exported review CSV to a public repository.')


if __name__ == '__main__':
    main()
