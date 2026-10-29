#!/usr/bin/env python3
"""Additive evidence-context triage for source-linked Kaggle machine claims.

This is a high-recall review flagger, NOT a sentiment model or proof that a
quoted statement is unendorsed. Every underlying quote/stance stays unchanged.
Uses only the source bytes and the published machine-ledger rows.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/fcc_corpus'
ROWS=ROOT/'docs/data/kaggle/machine_claim_rows.json'
OUTPUT=ROOT/'docs/data/kaggle/claim_context_audit.json'
CONTACT=re.compile(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?<!\d)(?:\+1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}(?!\d)')
WORD=re.compile(r'[a-z]{4,}',re.I)
STOP={'that','this','these','those','from','with','there','where','should','would','could','rate','funding','school','schools','federal','program','commission','students','provide','commenters','author','about','their','because','against','support','supported','claims','claim','statement','evidence','policy','fcc','education','educational','other','more','some','have'}
# Indicators of another voice nearby; contextual risk, never a definitive label.
ATTRIBUTED=re.compile(
    r'\b(?:critics?|opponents?|commenters?|the (?:commission|fcc|nprm|notice|petitioners?|report|study|authors?|advocates?))'
    r'\s+(?:say|says|state|states|argue|argues|claim|claims|ask|asks|propose|proposes|'
    r'suggest|suggests|find|finds|conclude|concludes|notes?|contends?|asserts?)\b|'
    r'\b(?:according to|the following (?:argument|question|proposal)|'
    r'as (?:others?|critics?|opponents?) (?:have )?(?:claimed|argued|stated))\b',re.I)
FCC_QUESTION=re.compile(r'\b(?:we seek comment on|the commission seeks comment|the fcc asks|the nprm proposes|'
                        r'the notice asks whether|the commission proposes)\b',re.I)
REFERENCE=re.compile(r'(?im)^(?:references|bibliography|works cited|endnotes)\s*:?\s*$')
NEGATION=re.compile(r'\b(?:not|no|never|without|reject|oppose|against|cannot|shouldn.t|wouldn.t)\b',re.I)

def words(s: str) -> set[str]:
    return {m.group(0).lower() for m in WORD.finditer(str(s or ''))}-STOP

def context_flags(row: dict, text: str, same_quote_count: int = 1,
                  original_quote: str | None = None) -> list[str]:
    """Return review leads, not a definitive author attribution."""
    start=row.get('start')
    quote=str(row.get('quote') or '')
    if not isinstance(start,int) or start<0 or start>=len(text) or not quote:
        raise ValueError('Missing/malformed source-linked quote')
    if original_quote is not None:
        # Redaction must operate on the EXACT model evidence quote; applying it
        # to a larger window can consume digits beyond a truncated phone number.
        if text[start:start+len(original_quote)]!=original_quote:
            raise ValueError('Model checkpoint quote differs from source bytes: '+str(row.get('id')))
        if CONTACT.sub('[CONTACT REDACTED]',original_quote[:320])!=quote:
            raise ValueError('Public excerpt differs from verified model quote: '+str(row.get('id')))
    elif text[start:start+len(quote)]!=quote:
        raise ValueError('Direct quote does not match source: '+str(row.get('id')))
    preceding=text[max(0,start-240):start]
    fragment=text[start:start+len(quote)+240]
    flags=[]
    if ATTRIBUTED.search(preceding[-180:]) or ATTRIBUTED.search(fragment[:min(110,len(fragment))]):
        flags.append('possible_attributed_or_opposing_voice')
    if FCC_QUESTION.search(preceding[-220:]) or FCC_QUESTION.search(fragment[:min(110,len(fragment))]):
        flags.append('fcc_prompt_or_policy_question_near_quote')
    # Local heading cue, not "any reference string in a 200-page appendix."
    if REFERENCE.search(text[max(0,start-1100):start][-500:]):
        flags.append('possible_bibliography_or_cited_material')
    source_terms=words(quote)
    interpreted=words(str(row.get('argument') or '')+' '+str(row.get('action') or ''))
    if len(source_terms)>=5 and len(interpreted)>=5 and len(source_terms & interpreted)<2:
        flags.append('low_lexical_overlap_between_quote_and_machine_paraphrase')
    if same_quote_count>=3:flags.append('one_quote_used_for_multiple_machine_claims')
    if NEGATION.search(quote) and row.get('position') in ('support','oppose'):
        # Scope-sensitive warning only: not all negations reverse directions.
        flags.append('negation_in_source_requires_stance_inspection')
    return flags

def opposing_machine_position_flags(rows: list[dict]) -> tuple[dict[str,list[str]], dict]:
    """Identify machine label collisions; never decide which claim is right.

    Labels are provisional and may reflect different regulatory subparts, a
    substantive alternative, or an actual LLM error. 'other_policy_issue' is
    too broad to interpret as a single policy question.
    """
    by_issue=defaultdict(list)
    for index,row in enumerate(rows):
        issue=str(row.get('issue') or '')
        position=str(row.get('position') or '')
        if issue not in ('', 'other_policy_issue') and position in ('support','oppose'):
            by_issue[(str(row.get('id')),issue)].append((index,row))
    result=defaultdict(set)
    mixed_issues=set()
    exact_span_collisions=set()
    for key,entries in by_issue.items():
        if not {'support','oppose'}.issubset({str(r.get('position')) for _,r in entries}):
            continue
        mixed_issues.add(key)
        for i,_ in entries:
            result[str(i)].add('mixed_machine_directions_same_filing_and_issue')
        by_span=defaultdict(list)
        for i,row in entries:
            by_span[(row.get('start'),str(row.get('quote') or ''))].append((i,row))
        for span,claims in by_span.items():
            if {'support','oppose'}.issubset({str(r.get('position')) for _,r in claims}):
                exact_span_collisions.add((key[0],key[1],span[0]))
                for i,_ in claims:
                    result[str(i)].add('opposing_machine_labels_on_identical_source_span')
    return {k:sorted(v) for k,v in result.items()},{
        'filing_issue_pairs_with_mixed_machine_directions':len(mixed_issues),
        'filings_with_mixed_machine_directions':len({k[0] for k in mixed_issues}),
        'identical_source_spans_with_opposing_machine_labels':len(exact_span_collisions),
        'affected_machine_rows':len(result),
    }


def build(source=SOURCE, ledger=ROWS, out=OUTPUT,
          checkpoints=ROOT/'data/llm_census_kaggle/filings'):
    source=Path(source);ledger=Path(ledger);out=Path(out)
    manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    rows=json.loads(ledger.read_text(encoding='utf-8'))
    if rows.get('source_filings')!=manifest.get('records') or not isinstance(rows.get('rows'),list):
        raise ValueError('Model ledger does not align to original FCC corpus')
    by_id=defaultdict(list)
    for i,r in enumerate(rows['rows']):
        by_id[str(r.get('id'))].append((i,r))
    seen=set();audited=0;by_claim={};stats=Counter()
    for shard in manifest['shards']:
        f=source/'shards'/shard['name']
        if hashlib.sha256(f.read_bytes()).hexdigest()!=shard['sha256']:
            raise ValueError('Original source shard hash mismatch '+shard['name'])
        with gzip.open(f,'rt',encoding='utf-8') as stream:
            for line in stream:
                if not line.strip():continue
                record=json.loads(line)
                sid=str(record['submission_id'])
                if sid in seen:raise ValueError('Duplicate original source filing '+sid)
                seen.add(sid)
                text=str(record.get('text') or '')
                if hashlib.sha256(text.encode()).hexdigest()!=record.get('text_sha256'):
                    if text or record.get('text_sha256'):
                        raise ValueError('Source body checksum mismatch '+sid)
                records=by_id.get(sid,[])
                counts=Counter(r.get('start') for _,r in records)
                if records:
                    checkpoint_path=Path(checkpoints)/(sid+'.json')
                    if not checkpoint_path.is_file():
                        raise ValueError('Missing raw model checkpoint for '+sid)
                    checkpoint=json.loads(checkpoint_path.read_text(encoding='utf-8'))
                    if checkpoint.get('status')!='complete' or checkpoint.get('source_sha256')!=hashlib.sha256(text.encode()).hexdigest():
                        raise ValueError('Raw checkpoint source mismatch for '+sid)
                    raw_by_key=defaultdict(list)
                    for original in checkpoint.get('claims',[]):
                        key=(original.get('provision_id'),original.get('position'),original.get('evidence_start'))
                        raw_by_key[key].append(str(original.get('evidence_quote') or ''))
                for index,claim in records:
                    key=(claim.get('issue'),claim.get('position'),claim.get('start'))
                    candidates=raw_by_key.get(key,[])
                    original_quote=next((v for v in candidates
                        if CONTACT.sub('[CONTACT REDACTED]',v[:320])==claim.get('quote')),None)
                    if original_quote is None:
                        raise ValueError('Ledger quote has no matching raw source checkpoint '+sid)
                    flags=context_flags(claim,text,counts[claim.get('start')],original_quote=original_quote)
                    # Index aligns to exact, immutable order of the published
                    # ledger. Avoid falsely merging claims using the same span.
                    if flags:
                        by_claim[str(index)]=flags
                        for flag in flags:stats[flag]+=1
                    audited+=1
    if len(seen)!=manifest['records'] or set(by_id)-seen or audited!=len(rows['rows']):
        raise ValueError('Source or claim count incomplete')
    direction_flags,direction_summary=opposing_machine_position_flags(rows['rows'])
    for index,flags in direction_flags.items():
        existing=set(by_claim.get(index,[]))
        for flag in flags:
            if flag not in existing:
                stats[flag]+=1
                existing.add(flag)
        by_claim[index]=sorted(existing)
    payload={'schema_version':'claim-context-audit-v1','generated_utc':datetime.now(timezone.utc).isoformat(),
        'source_manifest_sha256':hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest(),
        'machine_claim_ledger_sha256':hashlib.sha256(ledger.read_bytes()).hexdigest(),
        'coverage':{'source_filings_checked':len(seen),'machine_claim_rows_checked':audited,
                    'claim_rows_with_any_review_flag':len(by_claim)},
        'flag_counts':dict(stats),
        'machine_direction_consistency':direction_summary,
        'limitations':[
            'Review flags do not establish whether a quote is endorsed, whether the model stance is correct, or whether a factual claim is true.',
            'Non-flagged claims remain machine-unvalidated; this is not a validated false-negative audit.',
            'Reference and negation context can legitimately appear in authors own arguments. Review original context before changing a stance.',
            'Machine labels supporting and opposing the same named provision can reflect different conditions or subparts, not necessarily a factual contradiction.',
            'A label collision does not establish what the source author supports or opposes; independently review the original FCC request and passage.',
            'Values are keyed to zero-based row index of the machine_claim_rows.json ledger; ledger SHA-256 must match.'
        ],
        'flags_by_ledger_row_index':by_claim}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    return payload['coverage']|{'flag_counts':dict(stats)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=SOURCE)
    p.add_argument('--ledger',type=Path,default=ROWS)
    p.add_argument('--output',type=Path,default=OUTPUT)
    p.add_argument('--checkpoints',type=Path,default=ROOT/'data/llm_census_kaggle/filings')
    a=p.parse_args()
    print(json.dumps(build(a.source,a.ledger,a.output,a.checkpoints),indent=2))
if __name__=='__main__':main()
