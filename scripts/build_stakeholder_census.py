#!/usr/bin/env python3
"""Source-linked exploratory census of *arguments in filings* by stakeholder.

Counts are a complete enumeration of the PUBLISHED model-claim ledger, not a
measurement of opinions in the population or verified endorsements. Direct
original-text quote-offset validation is performed upstream; a byte-matched
audit ledger is required before deriving high-confidence context flags.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/'docs/data/player_registry.json'
CLAIMS=ROOT/'docs/data/kaggle/machine_claim_rows.json'
QUALITY=ROOT/'docs/data/kaggle/filing_quality.json'
AUDIT=ROOT/'docs/data/kaggle/claim_context_audit.json'
OUT=ROOT/'docs/data/stakeholder_argument_census.json'
SOURCE=ROOT/'data/fcc_corpus/manifest.json'
NTIA_LISTENING_REPORT='26110081266'

# A deliberately analyst-defined *argument topic* taxonomy separate from the
# FCC proposal codebook and from the open-ended lexical topic explorer.
# We code a machine-extracted proposition, not a bare source-word mention.
THEMES=[
 ('program_continuity','Keep, reduce or narrow E-Rate','Funding & infrastructure',
  ('erate_sunset',),r'(?:sunset|eliminat(?:e|ion) e[- ]?rate|abolish (?:e[- ]?rate|the program)|terminat(?:e|ion) (?:e[- ]?rate|funding)|funding cut|reduce (?:e[- ]?rate|funding)|preserv(?:e|ing) (?:e[- ]?rate|funding|the program)|continu(?:e|ing) (?:e[- ]?rate|funding)|maintain (?:e[- ]?rate|funding|the program)|narrow (?:e[- ]?rate|eligibility)|phase out (?:e[- ]?rate|funding))'),
 ('eligibility_rules','Which services E-Rate should fund','Funding & infrastructure',
  ('erate_eligibility_scope','discount_matrix'),r'(?:e[- ]?rate eligib|eligib(?:le|ility) (?:service|broadband|network|cost|fund)|categor(?:y|ies) (?:one|two|1|2)|e[- ]?rate discount|discount (?:rate|matrix|structure|level)|funding scope|eligible services)'),
 ('internal_networks','Internal networks and equipment','Funding & infrastructure',
  ('mibs',),r'(?:managed internal broadband|internal (?:connections|network)|wireless (?:access|network)|wi.?fi|router|switch|category two|category 2|mibs)'),
 ('fiber_construction','Fiber, construction and network builds','Funding & infrastructure',
  ('special_construction',),r'(?:special construction|fiber|infrastructure build|network construction|overbuild|self.construction)'),
 ('broadband_affordability','Cost, access and equity','Funding & infrastructure',
  ('rural_equity','broadband_affordability'),r'(?:affordab|low.income|digital divid|underserved|rural|tribal|broadband cost|equity|equal access)'),
 ('cybersecurity','Cybersecurity and network protection','Internet safety',
  ('cybersecurity',),r'(?:cybersecurity|cyber security|firewall|ransomware|network secur|protect student data|secure network|security equipment)'),
 ('filtering','Content filtering and CIPA safeguards','Internet safety',
  ('cipa_network_filter','cipa_age_specific','cipa_social_media','cipa_byod'),r'(?:\bcipa\b|content filter|network.level filter|internet safety filter|filtering|social media restriction|age.specific)'),
 ('student_privacy','Student privacy and surveillance','Internet safety',
  ('cipa_monitoring_privacy',),r'(?:surveill|student privac|student data|data collection|student monitor|monitoring|sensitive information|tracking)'),
 ('screen_harms','Screen-use harms and disputed effects','Screens & learning',
  (),r'(?:screen[\s-]?time (?:harm|risk|concern|addict)|excessive (?:screen|device)|device (?:addiction|dependence)|mental health|developmental harm|screen exposure concern)'),
 ('screen_policy','Screen-time limits and funding conditions','Screens & learning',
  ('screen_time_condition',),r'(?:screen[\s-]?time (?:limit|restric|condition|policy|mandat)|device (?:time|use) limit|screen[\s-]?time rules?|condition (?:e[- ]?rate|funding) on screen|require (?:a )?screen[\s-]?time plan)'),
 ('screen_use_distinctions','Instructional versus recreational screen use','Screens & learning',
  (),r'(?:recreational (?:screen|use)|educational (?:screen|use)|passive (?:screen|use)|different (?:types|forms) of screen|productive screen|instructional screen|screen.time is not|screen time is not|not all screen)'),
 ('learning_outcomes','Academic outcomes and instructional value','Screens & learning',
  ('education_outcomes',),r'(?:learning (?:outcome|benefit|opportunit)|educational (?:outcome|benefit|opportunit)|academic (?:achiev|performance|outcome)|instructional technolog|improv(?:e|ing) learning|student achievement|digital instruction)'),
 ('accessibility','Disability, accessibility and assistive tools','Screens & learning',
  (),r'(?:disabilit|accessib|assistive tech|special education|learning difference|screen reader|alternative communication)'),
 ('digital_literacy','Digital literacy and preparation','Screens & learning',
  ('cipa_digital_literacy',),r'(?:digital literac|technology education|computer (?:skill|literac)|keyboard|digital skill|prepar(?:ation|e) for the workforce|ai literac)'),
 ('parent_choice','Parental choice and opt-outs','Schools & families',
  ('parent_opt_out',),r'(?:parental (?:opt.out|consent|choice|control|right)|parent (?:opt.out|choice|consent|permission)|famil(?:y|ies) (?:opt.out|choice)|analog alternative|opt.out|parents? (?:should|must|can) (?:retain|have|choose|decide)|parents? know best|virtual school (?:option|choice)|choice of (?:virtual|online) (?:school|education)|parents? (?:retain|have) the right to choose)'),
 ('school_discretion','School autonomy and local decisions','Schools & families',
  (),r'(?:local (?:control|decision|discretion|authority)|school (?:autonomy|decision)|district (?:discretion|decisions)|educators? (?:should|best positioned)|instructional autonomy)'),
 ('consultant_registration','Registering or licensing consultants','Consultants & procurement',
  ('consultant_registration',),r'(?:consultant registr|registration (?:requirement|form)|register consultants|licens(?:e|ing) consultants)'),
 ('consultant_definition','Who counts as a consultant','Consultants & procurement',
  ('consultant_definition',),r'(?:defin(?:e|ition) of consultant|consultant definition|consultant exemp|professional service provider)'),
 ('consultant_fees','Consultant compensation and percentage fees','Consultants & procurement',
  ('consultant_percent_fees',),r'(?:percentage.based fee|percent(?:age)? of.*(?:award|fund|discount)|contingen(?:t|cy) fee|consultant compensat|fee structure|consultant payment|performance.based fee)'),
 ('consultant_reporting','Consultant disclosures and Form 5654','Consultants & procurement',
  ('consultant_form_5654','consultant_records'),r'(?:form 5654|consultant disclosure|consultant record|consultant report|reporting requirement|consultant certif|retention requirement)'),
 ('competitive_bidding','Competitive bidding and procurement rules','Consultants & procurement',
  ('targeted_competition',),r'(?:competitive bidd|bid process|procurement rule|r(e)?quest for proposals|\brfp\b|procurement practice|vendor selection)'),
 ('vendor_influence','Vendor influence and conflicts of interest','Consultants & procurement',
  ('vendor_influence',),r'(?:vendor influenc|vendor incentiv|vendor driven|conflict of interest|vendor pressur|commercial incentiv|industry influenc|vendor control|procurement bias)'),
 ('administrative_burden','Paperwork, audits and compliance costs','Consultants & procurement',
  ('administrative_forms',),r'(?:administrative burden|paperwork|bureaucrac|administrative cost|compliance burden|certification burden|application process|(?:fcc|consultant|application) form\b|red tape)'),
 ('program_integrity','Waste prevention and program oversight','Oversight & legal',
  (),r'(?:program integrity|fraud prevention|audit|oversight|safeguards against (?:fraud|abuse)|improper payment|overbilling|waste,? fraud|compliance monitoring)'),
 ('alleged_misuse','Specific alleged misuse or fraud','Oversight & legal',
  (),r'(?:alleg(?:es|ed|ing) (?:misuse|fraud|abuse)|documented (?:fraud|misuse)|specific (?:fraud|misuse)|misappropriat|kickback|fraudulent (?:billing|claim|payment)|improperly spent|funds were misused)'),
 ('fcc_authority','FCC legal authority and jurisdiction','Oversight & legal',
  ('statutory_authority',),r'(?:fcc (?:authority|jurisdiction)|statutory (?:authority|mandate)|legal authority|beyond the fcc|communications act|congress(?:ional)? authorit|ultra vires)'),
 ('edtech_study_evidence','Research evidence for instructional technology','Screens & learning',
  (),r'(?:randomi[sz]ed (?:control|trial)|meta.analysis|peer.reviewed (?:study|research)|(?:research|study|studies|evidence) (?:shows?|demonstrates?|finds?|suggests?|indicates?) (?:that )?(?:digital|edtech|instructional|educational technolog|screen)|(?:digital|edtech|instructional|educational technolog) (?:research|evidence|study|studies))'),
 ('adaptive_learning','Personalized, adaptive and differentiated instruction','Screens & learning',
  (),r'(?:adaptive learning|personaliz(?:ed|ation) (?:instruction|learning)|individualiz(?:ed|ation) (?:instruction|learning)|differentiated instruction|tailor(?:ed|ing) (?:instruction|content) to (?:student|learner))'),
 ('teacher_workload','Teacher workload and classroom implementation','Screens & learning',
  (),r'(?:teacher (?:workload|time|burden|training)|teacher professional development|educator training|classroom implement|lesson planning|teacher productivity|reduce (?:the )?burden on teachers|classroom management)'),
 ('device_management','Student devices and school IT management','Screens & learning',
  (),r'(?:device management|managed (?:devices|chromebooks|laptops)|device deployment|one.to.one devices|1:1 devices|school.issued (?:device|laptop)|device fleet|endpoint management|classroom device policy)'),
 ('consultant_value','Consultants as capacity or compliance support','Consultants & procurement',
  (),r'(?:consultants? (?:help|assist|support|enable|provide|reduce)|consulting (?:services|expertise|support)|consultants? (?:are|is) (?:essential|necessary|important)|need (?:a|an|more) e[- ]?rate consultant|speciali[sz]ed (?:e[- ]?rate|program) (?:expertise|support)|consultant expertise)'),
 ('consultant_independence','Consultant independence and vendor relationships','Consultants & procurement',
  (),r'(?:consultant (?:independence|independent|conflict|impartial|neutral|relationship)|consultants? (?:paid|compensated) by (?:vendor|service provider)|consultants? (?:recommend|select) (?:a|the )?vendor|consultant.vendor (?:relationship|tie)|consultant (?:kickback|incentive)|vendor.funded consultant)'),
 ('consultant_qualifications','Consultant qualifications and professional standards','Consultants & procurement',
  (),r'(?:consultant (?:qualification|training|credential|certification|standard|experience)|professional (?:credential|standard|qualification) for consultants|certif(?:y|ied|ication) e[- ]?rate consultants?|consultants? (?:must|should) (?:demonstrate|meet) (?:competenc|qualification))'),
 ('bid_independence','Fair and independent competitive bidding','Consultants & procurement',
  (),r'(?:independent (?:bid|procurement|evaluation)|fair (?:and open )?(?:bidding|competition)|competitive neutrality|bid (?:manipulation|rigging|integrity)|vendor (?:steering|favoritism)|procurement (?:conflict|independence|fairness)|undue (?:supplier|vendor) influence)'),
 ('technology_cost_benefit','Edtech costs, ROI and vendor value','Consultants & procurement',
  (),r'(?:edtech (?:cost|expense|spend|budget|return on investment)|(?:educational|instructional) technolog(?:y|ies) (?:cost|expense|spend|budget)|technology return on investment|cost.effective (?:edtech|software|educational technolog)|vendor (?:pricing|markups|profit)|software subscription cost)'),
 ('libraries_public_service','Library access and public services','Schools & families',
  (),r'(?:public librar|library (?:patron|service|community)|homework help|job.seek|public internet access)')
]
# Prefix semantics: source model category (not the FCC's normative direction).
ISSUE_MAP={
 'erate_sunset':'program_continuity',
 'erate_eligibility_scope':'eligibility_rules',
 'discount_matrix':'eligibility_rules',
 'mibs':'internal_networks',
 'special_construction':'fiber_construction',
 'education_outcomes':'learning_outcomes',
 'cipa_digital_literacy':'digital_literacy',
 'parent_opt_out':'parent_choice',
 'screen_time_condition':'screen_harms',
 'consultant_registration':'consultant_registration',
 'consultant_definition':'consultant_definition',
 'consultant_percent_fees':'consultant_fees',
 'consultant_form_5654':'consultant_reporting',
 'consultant_records':'consultant_reporting',
 'targeted_competition':'competitive_bidding',
 'vendor_influence':'vendor_influence',
 'administrative_forms':'administrative_burden',
 'cipa_monitoring_privacy':'student_privacy',
 'cipa_network_filter':'filtering',
 'cipa_byod':'filtering',
 'cipa_social_media':'filtering',
 'cipa_age_specific':'filtering',
 'cipa_public_hearings':'filtering'
}
NON_POSITION=re.compile(r'\b(?:does not (?:address|discuss|mention|recommend|advocate)|no explicit (?:position|recommendation)|not explicitly (?:addressed|discussed)|there is no (?:proposal|position)|not discussed|no specific position|none is recommended|no stance)\b',re.I)
NO_ACTION=re.compile(r'^(?:none|n/a|not specified|no recommendation|no action|not applicable|unknown|unclear|no specific change)$',re.I)
SPEAKER_RISK={'possible_attributed_or_opposing_voice','fcc_prompt_or_policy_question_near_quote','possible_bibliography_or_cited_material','agency_listening_summary_third_party_views_not_official_stance'}
TOPICS={code:{'id':code,'label':label,'category':category,'description':'Exploratory machine-coded argument theme; counts are distinct filings, not validated endorsements.'}
        for code,label,category,issues,pattern in THEMES}
PATTERNS={code:re.compile(pattern,re.I) for code,label,category,issues,pattern in THEMES}
BY_ISSUE=defaultdict(set)
for code,label,category,issues,pattern in THEMES:
    for i in issues:BY_ISSUE[i].add(code)

def stakeholder_group(f):
    if f.get('multi_submitter_metadata'):
        return 'joint_institutional_filings'
    r=f.get('role','unresolved')
    industry=f.get('industry_focus','unspecified')
    if r.startswith('edtech_'):return 'edtech_vendors'
    if industry=='edtech_industry':return 'edtech_trade_associations'
    if r=='erate_consultant' or r=='procurement_adviser':return 'erate_consultants'
    if industry=='erate_consulting' and r=='trade_association':return 'consultant_associations'
    if r in ('telecom_isp','network_technology_vendor'):return 'connectivity_and_network_vendors'
    if industry=='telecom_industry':return 'telecom_associations'
    if r in ('school_district','individual_school'):return 'school_institutions'
    if r in ('school_technology_staff','school_educator','school_administrator'):return 'school_professionals'
    if r=='school_connected_unknown':return 'school_affiliation_uncertain'
    if r in ('library_institution','library_staff'):return 'libraries'
    if r=='parent_guardian':return 'parents'
    if r=='government':return 'government'
    if r=='trade_association':return 'other_associations'
    if r=='advocacy_organization':return 'nonprofits_and_advocacy'
    if r=='other_vendor':return 'other_businesses'
    return 'other_or_unidentified'

GROUP_NAMES={
 'joint_institutional_filings':'Joint institutional submissions',
 'school_institutions':'Schools and districts','school_professionals':'School staff and educators',
 'school_affiliation_uncertain':'School-related, capacity unclear',
 'libraries':'Libraries','parents':'Parents and caregivers','edtech_vendors':'Edtech companies',
 'edtech_trade_associations':'Edtech industry associations','erate_consultants':'E-Rate consulting firms',
 'consultant_associations':'Consultant associations',
 'connectivity_and_network_vendors':'Internet and networking vendors',
 'telecom_associations':'Telecom industry associations','government':'Government',
 'nonprofits_and_advocacy':'Nonprofits and advocacy groups',
 'other_associations':'Other associations','other_businesses':'Other businesses',
 'other_or_unidentified':'Other or unidentified'}
GROUP_ORDER=list(GROUP_NAMES)

DASH_VARIANTS=re.compile(r'[\u2010-\u2015\u2212\u00ad\u2043\ufe58\ufe63\uff0d]')
def normalized_interpretation(s: str) -> str:
    """Normalize model typographic dashes without changing source quotations.

    Published verbatim quotes stay byte-identical. Only semantic matching
    text from the model is normalized.
    """
    return DASH_VARIANTS.sub('-',unicodedata.normalize('NFKC',str(s or '')))

def topics_for_claim(row):
    """Only machine-extracted argument/action propositions, not keyword hits in source."""
    issue=str(row.get('issue') or '')
    action=str(row.get('action') or '').strip()
    arg=str(row.get('argument') or '').strip()
    if (NO_ACTION.fullmatch(action) or not action) and (NON_POSITION.search(arg) or not arg):
        return []
    # Remove reflexive 'no recommendation' rows even if policy codebook mentions an issue.
    if NON_POSITION.search(arg) and len(arg)<200 and (not action or NO_ACTION.fullmatch(action)):
        return []
    text=normalized_interpretation(action+' '+arg)
    matches={key for key in BY_ISSUE.get(issue,())}
    for key,pattern in PATTERNS.items():
        if pattern.search(text):matches.add(key)
    # "Ordinary oversight" must not be conflated with an allegation of misuse.
    if 'alleged_misuse' in matches and not PATTERNS['alleged_misuse'].search(text):
        matches.discard('alleged_misuse')
    # Distinguish discussions of school screen-time RULES from assertions that
    # screen use harms children. This guard applies to ALL machine issue IDs.
    if 'screen_harms' in matches and not re.search(
            r'\b(?:harm|harms|risk|risks|concern|concerns|addict|addiction|excess|excessive|'
            r'mental health|developmental|negative effects|adverse effects)\b',text,re.I):
        matches.discard('screen_harms')
    return sorted(matches)

def priority(row):
    score=0
    if row.get('action') and not NO_ACTION.fullmatch(str(row['action']).strip()):score+=3
    if len(str(row.get('argument') or ''))>=65:score+=2
    if len(str(row.get('quote') or ''))>=80:score+=2
    if row.get('issue')!='other_policy_issue':score+=1
    return score

def compute(registry, claims, quality, context_audit=None, manifest=None, ledger_digest=''):
    filings=registry['filings']
    if len(filings)!=3231 or len({f['id'] for f in filings})!=3231:
        raise ValueError('Player registry coverage mismatch')
    if claims.get('source_filings')!=len(filings) or not isinstance(claims.get('rows'),list):
        raise ValueError('Machine claim ledger snapshot mismatch')
    if quality.get('coverage',{}).get('processed_readable_filings')!=3230:
        raise ValueError('Machine coverage mismatch')
    if manifest and (manifest['records']!=len(filings) or manifest['records_with_text']!=3230):
        raise ValueError('Original source snapshot changed')
    audit_match=bool(context_audit and context_audit.get('machine_claim_ledger_sha256')==ledger_digest
                     and context_audit.get('coverage',{}).get('machine_claim_rows_checked')==len(claims['rows']))
    audit_by_index=context_audit['flags_by_ledger_row_index'] if audit_match else {}
    per_id={f['id']:f for f in filings}
    qfiles=quality['filings']
    if set(qfiles)-set(per_id):raise ValueError('Unexpected model-quality filing')
    grouped=defaultdict(lambda:defaultdict(list))
    source_rows=Counter(); ignored=Counter();all_ids=set()
    for i,row in enumerate(claims['rows']):
        fid=str(row.get('id') or '')
        if fid not in per_id:raise ValueError('Machine claim from unknown FCC filing '+fid)
        if not isinstance(row.get('start'),int) or not str(row.get('quote') or ''):
            raise ValueError('Claim missing source-evidence offset')
        source_rows[fid]+=1
        if fid==NTIA_LISTENING_REPORT:
            ignored['third_party_listening_summary_claim_rows']+=1
            continue
        tags=topics_for_claim(row)
        if not tags:
            ignored['no_substantive_topic_or_nonassertion']+=1
            continue
        flags=audit_by_index.get(str(i),[])
        for topic in tags:
            grouped[fid][topic].append((row,flags))
        all_ids.add(fid)
    records=[]
    summary=defaultdict(lambda:defaultdict(set));cautious=defaultdict(lambda:defaultdict(set))
    by_role=defaultdict(lambda:defaultdict(set))
    orgs=defaultdict(lambda:defaultdict(set))
    for f in filings:
        fid=f['id'];group=stakeholder_group(f);q=qfiles.get(fid,{})
        topic_evidence=[]
        for code,claims_and_flags in sorted(grouped.get(fid,{}).items()):
            # Keep one source citation per filing/theme, prefer clear and specific.
            ranked=sorted(claims_and_flags,key=lambda p:(
                len(SPEAKER_RISK.intersection(p[1]))>0,
                -priority(p[0]),-len(str(p[0].get('quote') or ''))))
            c,flags=ranked[0]
            possible_voice_issue=bool(SPEAKER_RISK.intersection(flags))
            cautious_flag=possible_voice_issue or f.get('proxy_possible') or f.get('multi_submitter_metadata') or f.get('needs_review')
            summary[group][code].add(fid)
            by_role[f['role']][code].add(fid)
            if not cautious_flag:cautious[group][code].add(fid)
            if f.get('organization'):orgs[f['organization']][code].add(fid)
            topic_evidence.append({
                'topic':code,
                'argument':str(c.get('argument') or '')[:380],
                'action':str(c.get('action') or '')[:240],
                'quote':str(c.get('quote') or '')[:320],
                'issue':str(c.get('issue') or ''),
                'source_start':c['start'],
                'claim_count':len(claims_and_flags),
                'context_flags':list(flags),
                'needs_speaker_review':bool(cautious_flag)
            })
        records.append({
            'id':fid,'role':f['role'],'group':group,
            'industry_focus':f.get('industry_focus','unspecified'),
            'organization':f.get('organization',''),
            'text_sha256':f.get('text_sha256',''),
            'identity_basis':f.get('basis',''),
            'identity_review_required':bool(f.get('needs_review')),
            'representative_possible':bool(f.get('proxy_possible')),
            'joint_filing':bool(f.get('multi_submitter_metadata')),
            'joint_parties_in_metadata':int(f.get('submitter_field_components') or 1),
            'joint_institutions':f.get('joint_institution_candidates') or [],
            'quality_scope':q.get('semantic_scope','not_modeled'),
            'number_machine_claims':source_rows[fid],
            'topics':topic_evidence
        })
    group_den=Counter(x['group'] for x in records)
    roles_den=Counter(x['role'] for x in records)
    group_claims=Counter(x['group'] for x in records if x['topics'])
    all_codes=list(TOPICS)
    stats=[]
    for code in all_codes:
        total=set()
        for g in GROUP_NAMES:total|=summary[g][code]
        cells={}
        for g in GROUP_NAMES:
            ids=summary[g][code]
            hashes={per_id[fid].get('text_sha256') for fid in ids if per_id[fid].get('text_sha256')}
            cells[g]={
                'filings':len(ids),
                'group_filings':group_den[g],
                'group_with_any_coded_argument':group_claims[g],
                'pct_of_group_filings':round(100*len(ids)/group_den[g],1) if group_den[g] else None,
                'distinct_source_texts':len(hashes),
                'lower_risk_filings':len(cautious[g][code]),
                'needs_attribution_or_identity_review':len(ids-cautious[g][code])
            }
        stats.append({'id':code,'label':TOPICS[code]['label'],'category':TOPICS[code]['category'],
                      'filings':len(total),'distinct_source_texts':len({
                          per_id[fid].get('text_sha256') for fid in total if per_id[fid].get('text_sha256')}),
                      'by_stakeholder':cells})
    stats.sort(key=lambda x:(-x['filings'],x['label']))
    profiles=[]
    for name,issues in orgs.items():
        ids=set().union(*issues.values())
        profiles.append({
            'name':name,'filings_with_topics':len(ids),
            'distinct_source_texts':len({per_id[x].get('text_sha256') for x in ids if per_id[x].get('text_sha256')}),
            'role':per_id[sorted(ids)[0]]['role'] if ids else '',
            'group':stakeholder_group(per_id[sorted(ids)[0]]) if ids else '',
            'industry_focus':per_id[sorted(ids)[0]].get('industry_focus','unspecified') if ids else '',
            'topics':{k:len(v) for k,v in issues.items()}
        })
    profiles.sort(key=lambda x:(-x['filings_with_topics'],x['name'].casefold()))
    return {
        'schema':'stakeholder-arguments-v1',
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'method':{
            'unit':'distinct FCC filing ID; unique source hashes separately; no unique-person inference',
            'argument_detection':'Analyst theme rules applied only to source-quoted, model-extracted claims/actions; original full-text keyword hits do not count.',
            'direction':'No published support/oppose count; existing machine stance polarity is not validated.',
            'attribution':'Original participant quotes can be reported by a different filer. NTIA listening-session summary excluded from agency-position topic tallies; context flags and identity uncertainty retained.',
            'review':'All category counts are exploratory. A lower-risk count does not imply substantive human verification.',
            'coverage_limitation':'No extracted claim for a topic does not mean a filing lacks that argument, particularly with long filings or OCR.',
            'source_context_audit_sha256_verified':audit_match
        },
        'coverage':{
            'filings':len(records),'original_readable_texts':3230,
            'machine_claim_rows':len(claims['rows']),
            'filings_with_any_claim':sum(bool(x['number_machine_claims']) for x in records),
            'filings_with_coded_topics':sum(bool(x['topics']) for x in records),
            'filings_without_coded_topics':sum(not x['topics'] for x in records),
            'filings_selected_windows_only':sum(x['quality_scope']=='prioritized_windows' for x in records),
            'filings_with_multiple_submitters':sum(x['joint_filing'] for x in records),
            'unresolved_or_personal_capacity_filings':sum(x['group']=='other_or_unidentified' for x in records),
            'excluded_reported_listening_claim_rows':ignored['third_party_listening_summary_claim_rows'],
            'excluded_nonassertion_or_unmapped_claim_rows':ignored['no_substantive_topic_or_nonassertion']
        },
        'stakeholder_groups':[
            {'id':g,'label':name,'filings':group_den[g],
             'filings_with_coded_topics':group_claims[g],
             'unique_texts':len({x['text_sha256'] for x in records if x['group']==g and x['text_sha256']}),
             'joint_filings':sum(x['joint_filing'] for x in records if x['group']==g)}
            for g,name in GROUP_NAMES.items()],
        'stakeholder_roles':[{'id':r,'filings':n} for r,n in sorted(roles_den.items(),key=lambda kv:(-kv[1],kv[0]))],
        'topics':stats,'organizations':profiles,'filings':records
    }

def build(registry=REGISTRY,claim_path=CLAIMS,quality_path=QUALITY,audit_path=AUDIT,
          manifest_path=SOURCE,out=OUT):
    rb=Path(registry).read_bytes();cb=Path(claim_path).read_bytes()
    ledger=json.loads(cb);a=json.loads(Path(audit_path).read_text(encoding='utf8')) if Path(audit_path).exists() else None
    payload=compute(json.loads(rb),ledger,json.loads(Path(quality_path).read_text(encoding='utf8')),
                    a,json.loads(Path(manifest_path).read_text(encoding='utf8')),hashlib.sha256(cb).hexdigest())
    payload['inputs']={
        'player_registry_sha256':hashlib.sha256(rb).hexdigest(),
        'machine_claim_ledger_sha256':hashlib.sha256(cb).hexdigest(),
        'source_manifest_sha256':hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest()
    }
    path=Path(out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    return {'groups':len(payload['stakeholder_groups']),'topics':len(payload['topics']),
            'filings':payload['coverage']['filings'],'coded':payload['coverage']['filings_with_coded_topics'],
            'audit_matched':payload['method']['source_context_audit_sha256_verified']}
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--registry',type=Path,default=REGISTRY)
    p.add_argument('--claims',type=Path,default=CLAIMS)
    p.add_argument('--quality',type=Path,default=QUALITY)
    p.add_argument('--audit',type=Path,default=AUDIT)
    p.add_argument('--manifest',type=Path,default=SOURCE)
    p.add_argument('--out',type=Path,default=OUT)
    a=p.parse_args()
    print(json.dumps(build(a.registry,a.claims,a.quality,a.audit,a.manifest,a.out),indent=2))
if __name__=='__main__':main()
