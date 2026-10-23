#!/usr/bin/env python3
"""Source-linked four-axis *candidate* census for reviewer adjudication.

This first pass scans all 3,230 original FCC comment texts and all completed
Kaggle GPT-OSS claim JSON files. It does not infer that a matching filing
endorses a policy, nor that a misuse allegation is true. Its counts MUST be
labeled candidate counts (not votes, verified positions, or misconduct).
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_FILES=ROOT/'data/llm_census_kaggle/filings'
DEFAULT_CORPUS=ROOT/'data/fcc_corpus'
DEFAULT_META=ROOT/'docs/data/corpus_index.json'
DEFAULT_OUTPUT=ROOT/'docs/data/kaggle/priority_position_candidates.json'
CONTACT=re.compile(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?<!\d)(?:\+1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}(?!\d)')
E=re.compile(r'e[\u2011\u2013\u2014\s-]?rate|universal service|federal (?:broadband|connectivity) support',re.I)
POSITIVE=frozenset(['preserve_expand','abolish_program','targeted_restriction','favor_new_federal_condition',
                    'oppose_new_federal_condition','conditional_or_locally_controlled','affirmative_harm_concern',
                    'questions_harm_claim','general_misuse_allegation','specific_allegation'])
AXES={
 'funding':('preserve_expand','abolish_program','targeted_restriction','conditional_or_redesign'),
 'conditions':('favor_new_federal_condition','oppose_new_federal_condition','conditional_or_locally_controlled','existing_rules_only'),
 'screen_harms':('affirmative_harm_concern','questions_harm_claim','acknowledges_concern_no_policy'),
 'misuse':('specific_allegation','general_misuse_allegation','risk_or_hypothetical','oversight_only'),
}
# These are HIGH-RECALL REVIEW TRIGGERS, not intent or stance classifiers.
# Inspect full source around each hit; redacted/quoted FCC text may trigger.
RAW_RULES={
 'preserve_expand':[
    r'\b(?:preserv\w*|continu\w*|maintain\w*|strengthen\w*|keep|fully fund|sustain\w*|protect)\b.{0,100}\be[\s-]?rate\b',
    r'\be[\s-]?rate\b.{0,85}\b(?:continu\w*|remain\w*|preserv\w*|maintain\w*|strengthen\w*|fully fund|essential|critical)\b',
    r'\b(?:oppose|reject|do not|should not|must not)\b.{0,85}\b(?:terminat\w*|eliminat\w*|sunset|cut|abolish)\b.{0,100}\b(?:e[\s-]?rate|program|funding)\b',
 ],
 'abolish_program':[
    r'\b(?:abolish|sunset|terminat\w*|end|eliminat\w*|defund)\b.{0,80}\be[\s-]?rate\b',
    r'\be[\s-]?rate\b.{0,85}\b(?:abolish|sunset|terminat\w*|eliminat\w*|defund|end the program)\b',
 ],
 'targeted_restriction':[
    r'\b(?:stop funding|reduce funding|withhold funding|restrict subsidies|cut funding|limit eligibility|narrow eligibility|not subsidiz\w*)\b.{0,120}\b(?:school|e[\s-]?rate|wifi|wi-fi|device|service|technology|internet|funding)\b',
    r'\be[\s-]?rate\b.{0,110}\b(?:restrict|limit|narrow|cut|reduce|withhold)\b.{0,80}\b(?:eligib\w*|fund\w*|service|wi[\s-]?fi|device)\b',
 ],
 'conditional_or_redesign':[
    r'\be[\s-]?rate\b.{0,110}\b(?:condition\w*|reform|moderniz\w*|require\w*|eligib\w*|redesign)\b',
 ],
 'favor_new_federal_condition':[
    r'\b(?:require|impose|mandate|condition|tie|make)\b.{0,90}\b(?:e[\s-]?rate|funding|recipients)\b.{0,95}\b(?:screen|safety|filter|monitor|limit|protect|parent|instruction|education\w*)\b',
    r'\be[\s-]?rate\b.{0,110}\b(?:conditioned|conditional|require\w*|mandat\w*)\b.{0,80}\b(?:screen|safety|filter|parent|educational)\b',
 ],
 'oppose_new_federal_condition':[
    r'\b(?:oppose|reject|avoid|do not|should not|must not|against)\b.{0,95}\b(?:federal|blanket|uniform|additional|new)\b.{0,70}\b(?:screen|mandate|condition|monitor|filter|requirement)\b',
    r'\b(?:e[\s-]?rate|funding)\b.{0,130}\b(?:should not|must not|avoid)\b.{0,85}\b(?:condition|require|screen|mandat)\b',
 ],
 'conditional_or_locally_controlled':[
    r'\b(?:local control|local discretion|local flexibility|locally determined|school-level decisions|unfunded mandate|one-size-fits-all|technically feasible)\b',
    r'\b(?:privacy|implement\w*|fund\w*)\b.{0,85}\b(?:safeguard|constraint|flexibility)\b',
 ],
 'existing_rules_only':[
    r'\b(?:existing|current)\b.{0,55}\b(?:cipa|internet safety|filtering)\b.{0,85}\b(?:sufficient|adequate|already|enough|protect)\b',
 ],
 'affirmative_harm_concern':[
    r'\b(?:excessive|too much|unlimited|overuse|unrestricted)\b.{0,52}\b(?:screen\W*time|screens?|device use|digital exposure)\b',
    r'\b(?:screen\W*time|screen use|digital exposure)\b.{0,95}\b(?:harm\w*|risk\w*|addict\w*|development|health|impair\w*|disrupt\w*|sleep|attention|displac\w*|negative|declin\w*)\b',
    r'\b(?:harm\w*|health|mental health|academic|developmental|addict\w*)\b.{0,95}\b(?:screen\W*time|screen use|device use|digital exposure)\b',
 ],
 'questions_harm_claim':[
    r'\b(?:unsupported|unsubstantiat\w*|not established|insufficient evidence|not demonstrated)\b.{0,105}\b(?:screen\W*time|screen use|device use|digital exposure)\b',
 ],
 'acknowledges_concern_no_policy':[
    r'\b(?:screen\W*time|screen use|device use|digital exposure|screens in (?:schools|classrooms))\b',
 ],
 'general_misuse_allegation':[
    r'\b(?:e[\s-]?rate|e[\s-]?rate funds|taxpayer funds)\b.{0,150}\b(?:misus\w*|abuse\w*|wast\w*|fraud\w*|improperly used|ineligible spend\w*)\b',
    r'\b(?:misus\w*|wast\w*|fraud\w*|improperly used)\b.{0,125}\b(?:e[\s-]?rate|fund\w*|subsid\w*)\b',
 ],
 'specific_allegation':[
    r'\b(?:fraudulent(?:ly)?|improper(?:ly)?|ineligible|misus(?:e|ed)|divert(?:ed|ing)?|overbill(?:ed|ing)?|bid.rigg\w*|kickback\w*)\b.{0,125}\b(?:e[\s-]?rate|fund\w*|bill\w*|procure\w*|payment\w*|contract\w*|school wi[\s-]?fi)\b',
    r'\b(?:e[\s-]?rate|taxpayer|federal)\b.{0,110}\b(?:funds|dollars|subsidies|money)\b.{0,85}\b(?:are being|is being|have been|were|was)\b.{0,65}\b(?:misus\w*|divert\w*|wast\w*|spent|fraud\w*)\b',
 ],
 'risk_or_hypothetical':[
    r'\b(?:risk|potential|prevent|preventing|could|might|possible|concern\w*)\b.{0,75}\b(?:fraud|misuse|abuse|waste|improper payment)\b',
 ],
 'oversight_only':[
    r'\b(?:fraud prevention|program integrity|competitive bidding oversight|improper payments|fraud detection|consultant conflicts of interest|abuse prevention|anticorruption|anti-fraud)\b',
 ],
}
PATTERNS={key:[re.compile(x,re.I|re.S) for x in rules] for key,rules in RAW_RULES.items()}
MODEL_ISSUES={
 'funding':{'erate_sunset','erate_eligibility_scope','special_construction','mibs','discount_matrix','targeted_competition'},
 'conditions':{'screen_time_condition','cipa_byod','cipa_network_filter','cipa_monitoring_privacy','cipa_social_media','parent_opt_out','education_outcomes','cipa_public_hearings','safety_policy_transparency'},
 'screen_harms':{'screen_time_condition','parent_opt_out','daily_hour_limits'},
 'misuse':{'vendor_influence','consultant_percent_fees','consultant_registration','consultant_definition'},
}
HINTS={
 'preserve_expand':re.compile(r'\b(?:continu\w*|preserv\w*|maintain\w*|keep|expand|strengthen|fully fund|do not (?:cut|sunset|eliminat\w*))\b',re.I),
 'abolish_program':re.compile(r'\b(?:end|abolish|sunset|eliminate|terminate|defund)\b.{0,65}\b(?:e[\s-]?rate|program)\b',re.I),
 'targeted_restriction':re.compile(r'\b(?:eliminat\w*|stop|limit|narrow|restrict|cut|reduc\w*|withhold)\b.{0,120}\b(?:fund\w*|subsid\w*|eligib\w*|wi[\s-]?fi|service|e[\s-]?rate)\b',re.I),
 'favor_new_federal_condition':re.compile(r'\b(?:impose|require|mandate|condition|enforce|tie funding to|set (?:screen|daily) limits)\b',re.I),
 'oppose_new_federal_condition':re.compile(r'\b(?:oppose|avoid|reject|do not|not require|not mandate|should not|must not)\b.{0,125}\b(?:condition|mandate|screen|monitor|requirement|limit)\b',re.I),
 'conditional_or_locally_controlled':re.compile(r'\b(?:local discretion|local flexibility|locally|technically feasible|implementation time|privacy safeguards|unfunded mandate)\b',re.I),
 'affirmative_harm_concern':re.compile(r'\b(?:excessive screen|screen\W*time|digital exposure)\b.{0,140}\b(?:harm|health|risk|attention|addict|learning|negative|declin|develop)\w*',re.I),
 'general_misuse_allegation':re.compile(r'\b(?:misuse|misused|fraud|waste|abuse|improper|ineligible)\b',re.I),
}
NEGATION_WARNING=re.compile(r'\b(?:should (?:not|never)|must not|do not|oppose|reject|avoid|whether|asks? (?:if|whether)|we seek comment|the commission proposes|proposed rule|nprm)\b',re.I)
CONTACT_REPLACEMENT='[CONTACT REDACTED]'

def redact(s):
    return CONTACT.sub(CONTACT_REPLACEMENT,s)

def window(text,start,end,padding=150):
    lo=max(0,start-padding);hi=min(len(text),end+padding)
    return {'quote':redact(text[lo:hi]),'start':lo,'end':hi}

def build_one(sid,text,model,meta):
    all_hits={label:[] for choices in AXES.values() for label in choices}
    for label,patterns in PATTERNS.items():
        for p in patterns:
            for m in p.finditer(text):
                if len(all_hits[label])>=3:break
                ev=window(text,m.start(),m.end(),115)
                quote=ev['quote']
                if any(x['start']==ev['start'] for x in all_hits[label]):continue
                flags=[]
                if NEGATION_WARNING.search(quote):flags.append('quoted_opposition_or_fcc_prompt_possible')
                if label in {'specific_allegation','general_misuse_allegation'}:
                    if re.search(r'\b(?:risk|prevent|potential|hypothetical|could|possible|proposal|proposed|whether)\b',quote,re.I):
                        flags.append('may_be_hypothetical_or_regulatory_discussion')
                    if re.search(r'\b(?:funding for wifi|wi[\s-]?fi|screen\W*time|device use)\b',quote,re.I):
                        flags.append('may_be_normative_objection_not_illegal_spending')
                all_hits[label].append({'origin':'source_text_regex','label':label,'quote':quote,
                     'start':ev['start'],'end':ev['end'],'caution_flags':flags})
            if len(all_hits[label])>=3:break
    # Machine action text is a candidate retrieval cue only; source quote remains
    # the literal evidence. NEVER infer stance from model 'support'/'oppose'.
    if model:
        for c in model.get('claims',[]):
            topic=str(c.get('provision_id') or '')
            act=str(c.get('requested_action') or '')
            arg=str(c.get('argument') or '')
            input_text=act+' '+arg
            for axis,issues in MODEL_ISSUES.items():
                if topic not in issues and not (axis=='misuse' and str(c.get('reason_family'))=='fraud_integrity'):
                    continue
                for label in AXES[axis]:
                    pattern=HINTS.get(label)
                    if pattern is None or not pattern.search(input_text) or len(all_hits[label])>=4:continue
                    offset=c.get('evidence_start')
                    quote=str(c.get('evidence_quote') or '')
                    if not isinstance(offset,int) or not quote or text[offset:offset+len(quote)]!=quote:continue
                    all_hits[label].append({'origin':'kaggle_claim_model_action','label':label,
                        'quote':redact(quote[:350]),'start':offset,'end':offset+len(quote),
                        'machine_requested_action':redact(act[:210]),
                        'caution_flags':['MODEL_INTERPRETATION_UNVALIDATED','must_verify_filer_endorsement']})
    output={}
    for axis,labels in AXES.items():
        detected=[l for l in labels if all_hits[l]]
        selected=[]
        for l in detected:selected.extend(all_hits[l][:3])
        output[axis]={'candidate_labels':detected,'evidence':selected[:11],
                      'review_status':'not_adjudicated',
                      'interpretation':'Retrieval flags only; NO verified stance or proven allegation'}
    # Misuse risk is not itself evidence of an actual violation.
    if output['misuse']['candidate_labels']:
        output['misuse']['flagged_as_allegation_candidate']=any(x in output['misuse']['candidate_labels']
            for x in ('specific_allegation','general_misuse_allegation'))
        output['misuse']['caution']='Allegation asserted or potentially discussed in a public comment; no finding of misconduct.'
    out={'id':sid,'filer':str(model.get('filer_raw') or meta.get('organization') or '') if model else str(meta.get('organization') or ''),
         'role':meta.get('role') or 'unresolved','date':meta.get('date') or '',
         'ocr_candidate':bool(meta.get('ocr') or (model and str(model.get('has_unreviewed_ocr','0'))=='1')),
         'model_semantic_scope':model.get('semantic_scope','unavailable') if model else 'unavailable',
         'duplicate_count':int(meta.get('duplicate_count') or 1),
         'has_source_text':bool(text),
         'axes':output}
    return out

def build(files=DEFAULT_FILES, corpus=DEFAULT_CORPUS, index=DEFAULT_META,output=DEFAULT_OUTPUT,strict=True):
    meta=json.loads(Path(index).read_text(encoding='utf-8'))['filings']
    manifest=json.loads((Path(corpus)/'manifest.json').read_text(encoding='utf-8'))
    if strict and (len(meta)!=3231 or manifest['records']!=3231 or manifest['records_with_text']!=3230):
        raise ValueError('Unexpected source corpus baseline')
    meta_by={str(m['id']):m for m in meta}
    models={}
    for p in sorted(Path(files).glob('*.json')):
        d=json.loads(p.read_text(encoding='utf-8'))
        sid=str(d.get('submission_id') or '')
        if sid not in meta_by:raise ValueError('LLM output outside indexed corpus '+sid)
        if d.get('status')=='complete':models[sid]=d
    if strict and len(models)!=3230:
        raise ValueError(f'Expected 3230 complete Kaggle model filings: {len(models)}')
    found=set();out=[]
    for shard in manifest['shards']:
        gz=Path(corpus)/'shards'/shard['name']
        if hashlib.sha256(gz.read_bytes()).hexdigest()!=shard['sha256']:
            raise ValueError('Source archive shard hash mismatch '+str(gz))
        with gzip.open(gz,'rt',encoding='utf-8') as fh:
            for line in fh:
                if not line.strip():continue
                row=json.loads(line)
                sid=str(row['submission_id'])
                if sid in found or sid not in meta_by:raise ValueError('Duplicate or unexpected ID '+sid)
                found.add(sid)
                body=str(row.get('text') or '')
                if hashlib.sha256(body.encode('utf-8')).hexdigest()!=row['text_sha256']:
                    raise ValueError('Text source checksum mismatch '+sid)
                if sid in models and models[sid].get('source_sha256')!=row['text_sha256']:
                    raise ValueError('Kaggle source text differs from original '+sid)
                out.append(build_one(sid,body,models.get(sid),meta_by[sid]))
    if len(found)!=manifest['records'] or found!=set(meta_by):
        raise ValueError('Some original source records were never checked')
    out.sort(key=lambda x:x['id'])
    counts={axis:{label:sum(label in r['axes'][axis]['candidate_labels'] for r in out)
                  for label in labels} for axis,labels in AXES.items()}
    counts['misuse']['potential_allegation_any']=sum(r['axes']['misuse'].get('flagged_as_allegation_candidate',False) for r in out)
    intersections={
      'screen_concern_and_restriction_candidate':sum(
          'affirmative_harm_concern' in r['axes']['screen_harms']['candidate_labels'] and
          'targeted_restriction' in r['axes']['funding']['candidate_labels'] for r in out),
      'screen_concern_and_new_condition_candidate':sum(
          'affirmative_harm_concern' in r['axes']['screen_harms']['candidate_labels'] and
          'favor_new_federal_condition' in r['axes']['conditions']['candidate_labels'] for r in out),
    }
    dataset={'version':'priority-positions-candidates-v1','generated_utc':datetime.now(timezone.utc).isoformat(),
        'status':'UNADJUDICATED_RETRIEVAL_CANDIDATES_NOT_VOTES_NOT_CONFIRMED_MISCONDUCT',
        'source_records':len(out),'readable_filings':sum(r['has_source_text'] for r in out),
        'model_completed_filings':len(models),'codebook':'../../analysis_methods/priority_position_codebook.md',
        'axis_labels':{k:list(v) for k,v in AXES.items()},
        'candidate_filing_counts':counts,'candidate_intersections':intersections,
        'notes':[
          'Every source text searched end to end; machine and regex-derived labels are RESEARCH REVIEW CANDIDATES only.',
          'A positive cue may be quoted FCC proposal text, a contested allegation, or the opposite position; a negative cue is not a verified absence.',
          'No model support/oppose labels were used. Source offsets show literal evidence but not endorsement.',
          'Misuse allegations are statements in filings, not proven illegal use, fraud, or official findings.',
          'Long filings, OCR, incomplete extraction, source copies, repeated text, and unverified affiliations require targeted review.',
        ],'filings':out}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(dataset,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    return dataset

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--files',type=Path,default=DEFAULT_FILES)
    p.add_argument('--corpus',type=Path,default=DEFAULT_CORPUS)
    p.add_argument('--index',type=Path,default=DEFAULT_META)
    p.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    a=p.parse_args()
    result=build(a.files,a.corpus,a.index,a.output)
    print(json.dumps({'source_records':result['source_records'],
        'readable_filings':result['readable_filings'],
        'candidate_filing_counts':result['candidate_filing_counts'],
        'candidate_intersections':result['candidate_intersections'],
        'status':result['status']},indent=2))
if __name__=='__main__':main()
