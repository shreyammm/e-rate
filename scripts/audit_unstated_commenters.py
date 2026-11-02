#!/usr/bin/env python3
"""Inspect every source filing whose public registry lacks a speaker capacity.

The output is privacy-minimal: no personal names, raw excerpts, or contact
details. It gives every entry a specific evidence disposition and ECFS link,
rather than conflating an unstated occupation with an unknown stakeholder.
"""
from __future__ import annotations
import gzip, hashlib, json, re
from collections import Counter
from pathlib import Path
from scripts.build_player_registry import ROOT, context_capacity, signoff_evidence, opening_institution, organization_label, candidate_affiliation

REGISTRY = ROOT / 'docs/data/player_registry.json'
CORPUS = ROOT / 'data/fcc_corpus'
OUTPUT = ROOT / 'docs/data/unstated_identity_audit.json'

def scan(registry=REGISTRY, source=CORPUS, output=OUTPUT):
    registry = json.loads(Path(registry).read_text())
    targets = {r['id']: r for r in registry['filings']
               if r.get('identity_status') == 'capacity_not_stated' or r.get('needs_review')}
    manifest = json.loads((Path(source)/'manifest.json').read_text())
    results = {}
    for shard in manifest['shards']:
        file = Path(source)/'shards'/shard['name']
        assert hashlib.sha256(file.read_bytes()).hexdigest() == shard['sha256']
        with gzip.open(file, 'rt', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                raw = json.loads(line)
                sid = str(raw['submission_id'])
                if sid not in targets: continue
                body = str(raw.get('text') or '')
                filer = str(raw.get('filer_raw') or '')
                source_capacity = context_capacity(body)
                signed_role, signed_org, sign_basis = signoff_evidence(body)
                header_org = opening_institution(body)
                meta_org = organization_label(filer) or candidate_affiliation(filer)
                # Domain/affiliation cues are recorded for source review only.
                # A mention alone cannot establish an occupation or representation.
                intro = body[:3500]
                tail = body[-2500:]
                clues = []
                indicators = {
                    'self_description': bool(source_capacity.role),
                    'signature_role': bool(signed_role),
                    'signature_organization': bool(signed_org),
                    'letterhead_organization': bool(header_org),
                    'metadata_organization': bool(meta_org),
                    'potential_employment': bool(re.search(
                        r'(?i)\\b(?:i work (?:for|at|with)|i am employed by|'
                        r'i serve (?:as|on|at)|my employer|our organization|'
                        r'we at (?:the|our)|my school|our district)\\b',intro)),
                    'potential_representation': bool(re.search(
                        r'(?i)\\b(?:on behalf of|we represent|i represent|'
                        r'counsel for|representing the)\\b',intro)),
                    'closing_present': bool(re.search(
                        r'(?im)^\\s*(?:respectfully submitted|sincerely|'
                        r'best regards|submitted by|signed by)\\b',tail)),
                    'text_available': bool(body.strip()),
                    'ocr_candidate': str(raw.get('has_unreviewed_ocr','0'))=='1'
                }
                clues = [k for k,v in indicators.items() if v]
                # These are dispositions, not classifications. Keep remaining
                # named individuals as "capacity unstated" when source lacks proof.
                if source_capacity.role or signed_role or signed_org or header_org or meta_org:
                    disposition = 'source_identity_evidence_needs_reconciliation'
                elif indicators['potential_employment'] or indicators['potential_representation']:
                    disposition = 'possible_affiliation_needs_full_source_review'
                elif not indicators['text_available'] or indicators['ocr_candidate']:
                    disposition = 'incomplete_or_ocr_source'
                else:
                    disposition = 'no_explicit_professional_capacity_found'
                results[sid] = {
                    'id':sid, 'source_url':'https://www.fcc.gov/ecfs/filing/'+sid,
                    'current_role':targets[sid]['role'],
                    'current_identity_status':targets[sid]['identity_status'],
                    'source_sha256':raw.get('text_sha256') or '',
                    'disposition':disposition, 'evidence_indicators':clues,
                    'candidate_capacity':source_capacity.role or signed_role or '',
                    'candidate_organization':meta_org or signed_org or header_org or '',
                    'requires_human_confirmation':True
                }
    if set(results) != set(targets):
        raise ValueError('Missing target source records: '+str(sorted(set(targets)-set(results))[:10]))
    records=sorted(results.values(),key=lambda x:(x['disposition'],x['id']))
    out={'schema_version':'unstated-identity-source-audit-v1',
         'scope':'Every filing whose current identity is flagged or whose capacity is unstated',
         'population':len(records),
         'disposition_counts':dict(Counter(x['disposition'] for x in records)),
         'note':'Source-level machine triage, not individual human adjudication. Do not infer employer or authority solely from discussion of a sector.',
         'records':records}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(out,indent=2)+'\\n')
    return out

if __name__ == '__main__':
    report=scan()
    print('Source filings inspected:',report['population'])
    print(report['disposition_counts'])
