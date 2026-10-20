import csv, json, tempfile, unittest
from pathlib import Path
from erate.engine import analyze, normalized_text, filer_key, read_csv, sha256, write_csv, local_path
from erate.annotation import SCHEMA, validate, make_sample
from erate.near_duplicates import jaccard, shingles

FIL=['submission_id','date_submission','submission_type','filers','text_data_chars','document_count',
     'documents_downloaded','documents_extracted','status','issues','source_url']
DOC=['submission_id','document_number','filename','url','local_file','sha256','http_status',
     'file_status','text_file','text_chars','extraction_status','error']

class TestCorpus(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)/'corpus';self.base.mkdir()
        self.out=self.base/'analysis_observatory'
        for name in ['combined_text','original_documents','attachment_text']:(self.base/name).mkdir()
        txt='We support maintaining internet access for rural schools and libraries, including reliable connectivity.'
        (self.base/'combined_text/111.txt').write_text(txt)
        (self.base/'combined_text/112.txt').write_text(txt.replace('  ',' '))
        (self.base/'combined_text/113.txt').write_text('blob:https://example.invalid/unique')
        (self.base/'original_documents/111_1.pdf').write_bytes(b'%PDF example original fixture')
        (self.base/'attachment_text/111_1.txt').write_text('No text found')
        filings=[]
        for sid,name,status,nd in [('111','Jane Doe','complete',1),('112','JANE DOE','complete',0),('113','A School','unresolved',0)]:
            filings.append(dict(submission_id=sid,date_submission='2026-10-13T10:00:00Z',submission_type='COMMENT',
                filers=name,text_data_chars='0',document_count=str(nd),documents_downloaded=str(nd),documents_extracted=str(nd),
                status=status,issues='',source_url='https://www.fcc.gov/ecfs/filing/'+sid))
        write_csv(self.base/'filings_manifest.csv',filings,FIL)
        d=dict(submission_id='111',document_number='1',filename='scanned.pdf',url='https://example.invalid/scanned.pdf',
               local_file='original_documents/111_1.pdf',sha256=sha256(b'%PDF example original fixture'),http_status='',
               file_status='downloaded',text_file='attachment_text/111_1.txt',text_chars='13',
               extraction_status='embedded_text',error='')
        write_csv(self.base/'documents_manifest.csv',[d],DOC)

    def test_audit_and_duplicates(self):
        before=(self.base/'filings_manifest.csv').read_bytes()
        summary=analyze(self.base,self.out)
        self.assertEqual(summary['index_filings'],3)
        self.assertEqual(summary['filings_by_status']['unresolved'],1)
        self.assertEqual(summary['filer_keys_exact_normalized_unverified'],2)
        self.assertEqual(summary['largest_single_filer_count'],2)
        self.assertEqual(summary['filings_in_exact_duplicate_clusters'],2)
        self.assertEqual(summary['document_quality_flag_counts']['pdf_text_100_chars_or_fewer_review_ocr'],1)
        self.assertIn('possibly_extraction_placeholder',summary['document_quality_flag_counts'])
        self.assertEqual(before,(self.base/'filings_manifest.csv').read_bytes())

    def test_unsafe_path_rejected(self):
        with self.assertRaises(ValueError):local_path(self.base,'../../etc/passwd')

    def test_annotation_must_quote_source(self):
        analyze(self.base,self.out)
        rows=[dict(submission_id='111',issue_id='broadband_access',position='support',evidence_quote='We support maintaining internet access',
            stakeholder_type='individual_other',stakeholder_evidence='',coder_id='coder1',coding_method='manual',confidence='high',notes='')]
        write_csv(self.out/'manual_annotations.csv',rows,SCHEMA)
        self.assertEqual(validate(self.base,self.out),(1,0))
        rows[0]['evidence_quote']='Fabricated phrase not in document'
        write_csv(self.out/'manual_annotations.csv',rows,SCHEMA)
        self.assertEqual(validate(self.base,self.out),(0,1))

    def test_normalization(self):
        self.assertEqual(normalized_text('  A\t  B\n'),'a b')
        self.assertEqual(filer_key('Jane  Doe'),filer_key('JANE DOE'))
        a,_=shingles('one two three four five six')
        self.assertEqual(jaccard(a,a),1)

if __name__ == '__main__':unittest.main()
