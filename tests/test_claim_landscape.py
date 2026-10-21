import base64
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_claim_landscape import (
    completed_claims, cluster_claims, corpus_index,
    role_lookup, verify_source_spans, build
)


class ClaimLandscapeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.files=self.root/'results'
        self.files.mkdir()
        self.source=self.root/'source'
        (self.source/'shards').mkdir(parents=True)
        self.records=[
          {'id':'111','role':'unresolved'},
          {'id':'222','role':'school'},
          {'id':'333','role':'unresolved'}
        ]
        self.index=self.root/'index.json'
        self.index.write_text(json.dumps({'filings':self.records}))
        codes='010'
        self.roles=self.root/'roles.json'
        self.roles.write_text(json.dumps({
            'sequence':base64.b64encode(gzip.compress(codes.encode())).decode(),
            'expected_records':3,'expected_first_id':'111',
            'expected_last_id':'333','expected_code_counts':{'0':2,'1':1},
            'legend':{'0':'individual','1':'school_institution'}
        }))
        first='The library cannot afford rising monthly broadband costs.'
        second='The school district needs discounts to keep service affordable.'
        self.texts={'111':first,'222':second,'333':''}
        rows=[]
        for sid,text in self.texts.items():
            rows.append({'submission_id':sid,'text':text,
                         'text_sha256':hashlib.sha256(text.encode()).hexdigest()})
        encoded=''.join(json.dumps(r)+'\n' for r in rows).encode()
        zipped=gzip.compress(encoded)
        (self.source/'shards/filings-0001.jsonl.gz').write_bytes(zipped)
        (self.source/'manifest.json').write_text(json.dumps({
            'records':3,'records_with_text':2,
            'shards':[{'name':'filings-0001.jsonl.gz',
                       'sha256':hashlib.sha256(zipped).hexdigest()}]
        }))
        for sid,text in list(self.texts.items())[:2]:
            quote='cannot afford rising monthly broadband costs' if sid=='111' else 'needs discounts to keep service affordable'
            result={
                'submission_id':sid,'status':'complete','review_status':'unvalidated_machine_inference',
                'source_sha256':hashlib.sha256(text.encode()).hexdigest(),
                'source_url':'https://www.fcc.gov/ecfs/filing/'+sid,
                'claims':[{'provision_id':'other_policy_issue',
                           'position':'support',
                           'requested_action':'Maintain affordable E-Rate connectivity.',
                           'argument':'Cost to schools and libraries is too high.',
                           'reason_family':'access_affordability_equity',
                           'claim_kind':'cost_or_savings','evidence_quote':quote,
                           'evidence_start':text.index(quote),
                           'evidence_end':text.index(quote)+len(quote)}]}
            (self.files/f'{sid}.json').write_text(json.dumps(result))

    def test_every_complete_model_claim_counted(self):
        records=corpus_index(self.index)
        roles=role_lookup(records,self.roles)
        self.assertEqual(roles['222'],'school_institution')
        claims,stats,files=completed_claims(self.files,records,roles)
        self.assertEqual(len(claims),2)
        self.assertEqual(stats['complete_files_with_claims'],2)
        self.assertEqual(verify_source_spans(claims,files,self.source),2)
        labels,method=cluster_claims(claims)
        self.assertEqual(len(labels),2)

    def test_incomplete_files_not_extrapolated(self):
        path=self.root/'public.json'
        result=build(self.files,path,verify=True,index_file=self.index,
                     role_file=self.roles,source=self.source)
        self.assertEqual(result['coverage']['corpus_records'],3)
        self.assertEqual(result['coverage']['completed_machine_filings'],2)
        self.assertEqual(result['coverage']['remaining_or_incomplete_filings'],1)
        self.assertEqual(result['coverage']['machine_claim_rows'],2)
        self.assertEqual(result['coverage']['full_source_quote_offset_verified'],2)
        self.assertEqual(sum(c['distinct_filings'] for c in result['clusters']),2)
        self.assertIn('UNVALIDATED',result['model_status'])
        self.assertTrue(path.exists())
        all_rows=json.loads(path.with_name('machine_claim_rows.json').read_text())
        self.assertEqual(all_rows['publication_status'],'EXPLORATORY_MODEL_ONLY')
        self.assertEqual(len(all_rows['rows']),2)
        self.assertEqual({r['id'] for r in all_rows['rows']},{'111','222'})
        self.assertEqual({r['role'] for r in all_rows['rows']},
                         {'individual','school_institution'})

    def test_fabricated_quote_rejected_by_full_source_check(self):
        row=json.loads((self.files/'111.json').read_text())
        row['claims'][0]['evidence_quote']='A completely fabricated quote never used by a filing.'
        row['claims'][0]['evidence_end']=row['claims'][0]['evidence_start']+len(row['claims'][0]['evidence_quote'])
        (self.files/'111.json').write_text(json.dumps(row))
        records=corpus_index(self.index)
        claims,_,files=completed_claims(self.files,records,role_lookup(records,self.roles))
        with self.assertRaises(ValueError):
            verify_source_spans(claims,files,self.source)


if __name__=='__main__':
    unittest.main()
