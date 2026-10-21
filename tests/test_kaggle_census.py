import gzip, json, tempfile, unittest
from pathlib import Path
from scripts import llm_census as c
from scripts.kaggle_census import MODEL,SIZE,OVERLAP,pack,restore

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

if __name__=='__main__':unittest.main()
