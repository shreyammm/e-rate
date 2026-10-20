import json
import gzip
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.llm_census import (split_text,load_corpus,process_record, reuse_exact_text_classifications,
                                summarize,validate_chunk,digest,params_key,ALLOWED_MODELS,ollama_call)


class LLMCensusTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        self.src=self.home/'input'
        self.src.mkdir()
        self.out=self.home/'out'
        self.book={"version":"test-codebook", "stakeholder_roles":["school_district","parent_guardian","unknown"], "reason_families":["access_affordability_equity","child_safety","other"], "provisions":[{"id":"erate_sunset", "label":"Limit or sunset E-Rate", "category":"scope", "notice_status":"question_for_comment", "policy_option":"Reduce or eliminate E-Rate support."}]}
        self.body=('Our school district opposes ending the E-Rate program. '
             'Without these funds, children will lose affordable internet access. '
             'We are asking the FCC to preserve E-Rate support.')
        self.sid='26110077816'
        self.row={'submission_id':self.sid,'text':self.body,'source_url':'https://www.fcc.gov/ecfs/filing/'+self.sid,
                  'filer_raw':'District A','date_submission':'2026-10-12',
                  'has_unreviewed_ocr':'0','agency_record_candidate':'0'}

    def model(self,messages,model,url):
        return {'summary':'District asks to keep E-Rate','stakeholder_role':'school_district',
                'stakeholder_quote':'Our school district',
                'claims':[{'provision_id':'erate_sunset','position':'oppose',
                           'requested_action':'Preserve E-Rate','reason_family':'access_affordability_equity',
                           'claim_kind':'predicted_consequence',
                           'argument':'Lost access for children',
                           'evidence_quote':'Without these funds, children will lose affordable internet access.',
                           'uncertain':False}]}

    def test_us_developed_apache_licensed_model_allowlist(self):
        self.assertEqual(ALLOWED_MODELS, frozenset({'ibm/granite4:1b-q4_K_M', 'granite4.2:3b', 'granite4.2:8b', 'ibm/granite4.2:8b'}))

    def test_granite_request_disables_thinking_and_requires_json(self):
        captured={}
        class FakeResponse:
            def __enter__(self):return self
            def __exit__(self,*exc):return False
            def read(self,*args):
                return json.dumps({"message":{"content":json.dumps({"claims":[]})}}).encode()
        def mock_urlopen(req,timeout):
            captured.update(json.loads(req.data))
            return FakeResponse()
        with patch('urllib.request.urlopen',mock_urlopen):
            result=ollama_call([{'role':'user','content':'test'}],
                               'granite4.2:3b','http://localhost:11434/api/chat')
        self.assertEqual(captured['model'],'granite4.2:3b')
        self.assertIs(captured['think'],False)
        self.assertEqual(captured['format'],'json')
        self.assertEqual(result['claims'],[])

    def test_missing_role_quote_is_not_a_verified_stakeholder(self):
        chunk={'text':self.body,'start':0,'end':len(self.body)}
        prediction=self.model(None,None,None)
        prediction['stakeholder_quote']=''
        coded=validate_chunk(prediction,chunk,self.body,self.book)
        self.assertEqual(coded['stakeholder_role'],'unknown')

    def test_malformed_missing_claims_list_is_retried_and_rejected(self):
        class BadResponse:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,*args):
                return json.dumps({'message':{'content':'{"summary":"wrong but no claims"}'}}).encode()
        with patch('urllib.request.urlopen',return_value=BadResponse()):
            with patch('time.sleep',return_value=None):
                with self.assertRaisesRegex(RuntimeError,'missing claims array'):
                    ollama_call([{'role':'user','content':'test'}],
                                'granite4.2:3b','http://localhost:11434/api/chat')

    def test_verbatim_and_invalid_claim_rejection(self):
        chunk={'text':self.body,'start':0,'end':len(self.body)}
        r=self.model(None,None,None)
        r['claims'].append({**r['claims'][0], 'evidence_quote':'COMPLETELY FABRICATED QUOTE'})
        out=validate_chunk(r,chunk,self.body,self.book)
        self.assertEqual(len(out['claims']),1)
        self.assertEqual(out['invalid_claims_rejected'],1)
        self.assertEqual(out['claims'][0]['evidence_start'],self.body.find('Without these funds'))

    def test_checkpoint_and_aggregation_and_incremental_skip(self):
        self.assertEqual(process_record(self.row,self.book,self.out,'fake','local',
                     5800,400,call=self.model),'complete')
        self.assertEqual(process_record(self.row,self.book,self.out,'fake','local',
                     5800,400,call=lambda *a:self.fail('unexpected model call')),'already_complete')
        agg=summarize([self.row],self.out,self.book,'fake',5800,400)
        self.assertEqual(agg['completed_filings'],1)
        self.assertEqual(next(x for x in agg['provisions'] if x['provision_id']=='erate_sunset')
                         ['positions']['oppose'],1)
        self.assertEqual(agg['argument_type_counts']['predicted_consequence'],1)
        erate=next(p for p in agg['provisions'] if p['provision_id']=='erate_sunset')
        self.assertEqual(erate['inferred_role_by_position']['school_district']['oppose'],1)
        self.assertEqual(erate['claim_reason_by_position']['oppose']['access_affordability_equity'],1)
        self.assertTrue((self.out/'suggested_human_audit.json').exists())
        self.assertEqual(agg['completed_filings_in_exact_text_duplicate_groups'],0)

    def test_fair_partial_processing_does_not_hog_entire_queue(self):
        row={**self.row,'text':self.body*45}
        calls=[]
        def model(*args):
            calls.append(1)
            return self.model(*args)
        state=process_record(row,self.book,self.out,'fake','local',700,80,
                             call=model,max_chunks=3)
        self.assertEqual(state,'partial')
        self.assertEqual(len(calls),3)
        path=self.out/'filings'/f'{self.sid}.json'
        self.assertEqual(json.loads(path.read_text())['next_chunk'],3)
        state=process_record(row,self.book,self.out,'fake','local',700,80,
                             call=model,max_chunks=3)
        self.assertEqual(state,'partial')
        self.assertEqual(json.loads(path.read_text())['next_chunk'],6)

    def test_partial_resumption(self):
        # A preexisting checkpoint resumes the second chunk without redoing the first.
        row={**self.row,'text':self.body*80}
        chunks=split_text(row['text'],700,80)
        key=params_key(row,self.book,'fake',700,80)
        p=self.out/'filings'/f'{self.sid}.json'
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps({'params_key':key,'status':'partial',
                                 'submission_id':self.sid,'parts':[], 'next_chunk':1}))
        calls=[]
        def called(*args):
            calls.append(args)
            return self.model(*args)
        process_record(row,self.book,self.out,'fake','local',700,80,call=called)
        self.assertEqual(len(calls),len(chunks)-1)
        self.assertEqual(json.loads(p.read_text())['chunk_count'],len(chunks))

    def test_portable_input_and_checksum(self):
        (self.src/'filings.jsonl').write_text(json.dumps(self.row)+'\n')
        rows=load_corpus(self.src,None,'ocr_candidate_v1','augmented')
        self.assertEqual(rows[0]['submission_id'],self.sid)
        self.assertEqual(rows[0]['text'],self.body)

    def test_checksum_verified_compressed_corpus_shards(self):
        shards=self.src/'shards'
        shards.mkdir()
        row={**self.row,'text_sha256':digest(self.body)}
        payload=(json.dumps(row)+chr(10)).encode('utf-8')
        shard=shards/'filings-0001.jsonl.gz'
        shard.write_bytes(gzip.compress(payload,mtime=0))
        metadata={'records':1,'shards':[{'name':shard.name,
                  'sha256':hashlib.sha256(shard.read_bytes()).hexdigest()}]}
        (self.src/'manifest.json').write_text(json.dumps(metadata))
        records=load_corpus(self.src,None,'ocr_candidate_v1','augmented')
        self.assertEqual(records[0]['text'],self.body)
        shard.write_bytes(shard.read_bytes()+b'corruption')
        with self.assertRaisesRegex(ValueError,'shard SHA-256 mismatch'):
            load_corpus(self.src,None,'ocr_candidate_v1','augmented')

    def test_no_text_not_faked(self):
        row={**self.row,'text':'','submission_id':'26110077817'}
        process_record(row,self.book,self.out,'fake','local',5800,400,call=lambda *a:self.fail('called'))
        result=summarize([row],self.out,self.book,'fake',5800,400)
        self.assertEqual(result['completed_filings'],0)
        self.assertEqual(result['processing_status']['no_source_text'],1)

    def test_overlapping_chunks_cover_all_original_text(self):
        text='hello ' * 1400
        c=split_text(text,1000,200)
        self.assertEqual(c[0]['start'],0)
        self.assertEqual(c[-1]['end'],len(text))
        for prev,cur in zip(c,c[1:]):
            self.assertLess(cur['start'],prev['end'])
            self.assertLessEqual(cur['start'],prev['end'])

if __name__=='__main__':unittest.main()
