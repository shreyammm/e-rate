'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const p=require('../docs/assets/priority_positions.js');
test('four independent axes preserve misuse vs safeguards distinction',()=>{
 assert.equal(Object.keys(p.CONFIG).length,4);
 assert.ok(p.CONFIG.funding.labels.abolish_program);
 assert.ok(p.CONFIG.funding.labels.targeted_restriction);
 assert.ok(p.CONFIG.conditions.labels.oppose_new_federal_condition);
 assert.ok(p.CONFIG.screen_harms.labels.affirmative_harm_concern);
 assert.ok(p.CONFIG.misuse.labels.specific_allegation);
 assert.ok(p.CONFIG.misuse.labels.oversight_only);
});
test('review candidate counts do not imply votes or established wrongdoing',()=>{
 const rows=[
  {id:'1',axes:{funding:{candidate_labels:['preserve_expand']},misuse:{candidate_labels:['risk_or_hypothetical']}}},
  {id:'2',axes:{funding:{candidate_labels:['preserve_expand','abolish_program']},misuse:{candidate_labels:['general_misuse_allegation']}}},
  {id:'3',axes:{funding:{candidate_labels:[]},misuse:{candidate_labels:[]}}}
 ];
 assert.equal(p.counts(rows,'funding','preserve_expand'),2);
 assert.equal(p.counts(rows,'misuse','general_misuse_allegation'),1);
 assert.equal(p.counts(rows,'misuse','specific_allegation'),0);
});
test('adjudication requires full filing and evidence',()=>{
 const base={reviewer:'r1',axis:'funding',id:'123',labels:['preserve_expand'],
 note:'This author explicitly wants the program to continue.',source:{start:55,quote:'Continue E-Rate',origin:'source_text_regex'},read:true};
 assert.equal(p.reviewDecision({...base,read:false}).ok,false);
 assert.equal(p.reviewDecision({...base,source:null}).ok,false);
 assert.equal(p.reviewDecision({...base,note:'tiny'}).ok,false);
 const ok=p.reviewDecision(base);assert.equal(ok.ok,true);
 assert.equal(ok.value.review_stage,'one_reviewer_only_not_validated');
 assert.deepEqual(ok.value.labels,['preserve_expand']);
});
test('misuse review distinguishes illegal allegation from legally allowed spending objections',()=>{
 const base={reviewer:'r2',axis:'misuse',id:'777',labels:['general_misuse_allegation'],
 note:'The filer claims federal subsidies are being misused.',source:{start:13,quote:'misused',origin:'source_text_regex'},read:true};
 assert.equal(p.reviewDecision({...base,legal:'not_assessed'}).ok,false);
 assert.equal(p.reviewDecision({...base,legal:'normative_objection_not_illegal'}).ok,true);
 const output=p.reviewDecision({...base,legal:'alleges_illegal_or_ineligible'});
 assert.equal(output.value.misuse_legal_characterization,'alleges_illegal_or_ineligible');
});
test('CSV exports defend against formula injection',()=>{
 const s=p.csv([{filing_id:'17',explanation:'=HYPERLINK("bad")'}],['filing_id','explanation']);
 assert.ok(s.includes("'=HYPERLINK"));
});
test('full reviewer page has all four axes and source-review controls',()=>{
 const fs=require('node:fs'),path=require('node:path');
 const html=fs.readFileSync(path.join(__dirname,'../docs/positions.html'),'utf8');
 for(const id of ['pp-axes','pp-results','pp-overlap-cards','pp-reviewer','pp-export','pp-role','pp-label'])
   assert.ok(html.includes('id="'+id+'"'),id+' missing');
 assert.ok(html.includes('./assets/priority_positions.js'));
});
