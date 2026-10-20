import csv
import json
import tempfile
import unittest
from pathlib import Path
from scripts.recover_pdf_ocr import parse_tesseract_tsv, evidence_ready, METHOD_VERSION
from scripts.coverage_diagnostics import analyze
from erate.engine import write_csv,sha256

class TestOcrStaging(unittest.TestCase):
    def test_tesseract_groups_words(self):
        fields=['level','page_num','block_num','par_num','line_num','word_num','left','top','width','height','conf','text']
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'words.tsv'
            write_csv(p,[{'level':'5','page_num':'1','block_num':'1','par_num':'1','line_num':'1','word_num':str(i),
               'left':'0','top':'0','width':'10','height':'10','conf':'94','text':word}
               for i,word in enumerate(['rural','internet','access'],1)],fields)
            # Tesseract uses TSV; convert the fixture output's delimiters.
            with p.open() as f:
                rows=list(csv.DictReader(f))
            tsv='\t'.join(fields)+'\n'+'\n'.join('\t'.join(r[k] for k in fields) for r in rows)
            result=parse_tesseract_tsv(tsv)
            self.assertEqual(result[0]['text'],'rural internet access')
            self.assertAlmostEqual(result[0]['confidence'],.94)

    def test_skip_only_when_hashes_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'text').mkdir()
            (p/'evidence').mkdir()
            body=b'Recovered sample\n'
            (p/'text/111_1.txt').write_bytes(body)
            ev={'original_sha256':'abc','ocr_text_sha256':sha256(body),'ocr_method_version':METHOD_VERSION}
            (p/'evidence/111_1.json').write_text(json.dumps(ev))
            row={'original_sha256':'abc','ocr_engine':'apple_vision','ocr_method_version':METHOD_VERSION,
                 'status':'completed','text_path':'text/111_1.txt','evidence_path':'evidence/111_1.json'}
            self.assertTrue(evidence_ready(p,row,'abc','apple_vision'))
            self.assertFalse(evidence_ready(p,row,'xyz','apple_vision'))
            (p/'text/111_1.txt').write_text('changed')
            self.assertFalse(evidence_ready(p,row,'abc','apple_vision'))

class TestCoverageDiagnostics(unittest.TestCase):
    def test_reconciles_ocr_vs_other_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            inv=[]
            for sid,chars in [('111','0'),('112','0'),('113','400')]:
                inv.append(dict(submission_id=sid,submission_type='COMMENT',status='complete',
                    combined_text_file_count='1',text_chars='50',substantive_text_chars=chars,
                    document_count='1',quality_flags='',source_url='',filer_key=sid))
            write_csv(p/'filing_inventory.csv',inv,list(inv[0]))
            pdf=[dict(submission_id='111',triage_class='ocr_candidate_image_based')]
            write_csv(p/'pdf_deep_review.csv',pdf,list(pdf[0]))
            write_csv(p/'exact_duplicate_clusters.csv',[],['cluster_id','submission_ids'])
            out=analyze(p)
            self.assertEqual(out['filings_without_substantive_text'],2)
            self.assertEqual(out['filings_without_substantive_text_and_with_flagged_pdf'],1)
            self.assertEqual(out['filings_without_substantive_text_no_flagged_pdf'],1)

if __name__=='__main__':unittest.main()
