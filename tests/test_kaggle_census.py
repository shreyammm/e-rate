import gzip, io, json, tempfile, unittest
from unittest.mock import patch
from pathlib import Path
from scripts.kaggle_census import c,MODEL,SIZE,OVERLAP,pack,restore,source_spans,model_call

class Checkpoints(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.book=c.load_book();self.row={'submission_id':'1234567890','text':'Please retain funding for our libraries and students.',
            'source_url':'https://www.fcc.gov/ecfs/filing/1234567890','filer_raw':'',
            'date_submission':'','has_unreviewed_ocr':'0','agency_record_candidate':'0'}
    def tearDown(self):self.temp.cleanup()
    def payload(self):
        r=self.row
        return {'submission_id':r['submission_id'],'status':'complete','model':MODEL,
            'params_key':c.params_key(r,self.book,MODEL,SIZE,OVERLAP),'source_sha256':c.digest(r['text']),
            'claims':[{'evidence_start':0,'evidence_end':len(r['text']),'evidence_quote':r['text']}]}
    def bundle(self,obj):
        p=self.root/'bundle.gz'
        with gzip.open(p,'wt') as f:f.write(json.dumps(obj)+'\n')
        return p
    def test_restore_pack_and_resume(self):
        obj=self.payload();out=self.root/'out'
        self.assertEqual(restore(self.bundle(obj),out,[self.row],self.book),1)
        bundle=self.root/'packed.gz';pack(out,bundle)
        self.assertEqual(restore(bundle,out,[self.row],self.book),0)
    def test_changed_source_rejected_before_writing(self):
        obj=self.payload();row=dict(self.row,text='changed source')
        with self.assertRaises(ValueError):restore(self.bundle(obj),self.root/'out',[row],self.book)
        self.assertFalse((self.root/'out').exists())
    def test_invented_quote_rejected(self):
        obj=self.payload();obj['claims'][0]['evidence_quote']='fabricated quotation'
        with self.assertRaises(ValueError):restore(self.bundle(obj),self.root/'out',[self.row],self.book)
    def test_wrong_model_rejected(self):
        obj=self.payload();obj['model']='another-model'
        with self.assertRaises(ValueError):restore(self.bundle(obj),self.root/'out',[self.row],self.book)
    def test_partial_progress_survives(self):
        obj=self.payload();obj.update(status='partial',next_chunk=1,parts=[{'claims':obj['claims']}])
        self.assertEqual(restore(self.bundle(obj),self.root/'out',[self.row],self.book),1)
    def test_invalid_partial_progress_rejected(self):
        obj=self.payload();obj.update(status='partial',next_chunk=2,parts=[])
        with self.assertRaises(ValueError):restore(self.bundle(obj),self.root/'out',[self.row],self.book)
    def test_truncated_model_response_retries_with_larger_token_budget(self):
        seen=[]
        def mock_urlopen(req,timeout=None):
            payload=json.loads(req.data.decode('utf-8'))
            options=payload['options']
            seen.append((options['num_ctx'],options['num_predict']))
            if len(seen)==1:
                output={'done_reason':'length','message':{'content':''}}
            else:
                output={'done_reason':'stop','message':{'content':json.dumps({
                    'summary':'Brief source-grounded summary',
                    'stakeholder_role':'unknown','stakeholder_quote':'','claims':[]})}}
            return io.BytesIO(json.dumps(output).encode('utf-8'))
        messages=[
            {'role':'system','content':'Cite the original source.'},
            {'role':'user','content':json.dumps({
                'source_text':'Schools and libraries need affordable E-Rate broadband access.'})}
        ]
        with patch('scripts.kaggle_census.urllib.request.urlopen',side_effect=mock_urlopen), \
             patch('scripts.kaggle_census.time.sleep',return_value=None):
            result=model_call(messages,MODEL,'http://127.0.0.1:11434/api/chat')
        self.assertEqual(result['claims'],[])
        self.assertEqual(seen,[(8192,3072),(10240,4096)])

    def test_source_spans_are_exact_and_cover_full_window(self):
        body=('A long paragraph about the E-Rate program and school funding.\n'*180)[:6500]
        spans=source_spans(body)
        self.assertTrue(all(15<=len(s)<=200 and s in body for s in spans.values()))
        # Check coverage against a non-repeating source too, including final tail.
        body=''.join(chr(0x400+i) for i in range(1300))
        covered=set()
        for span in source_spans(body).values():
            start=body.index(span);covered.update(range(start,start+len(span)))
        self.assertEqual(covered,set(range(len(body))))

if __name__=='__main__':unittest.main()
