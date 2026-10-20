import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.build_qa_index import build


class AskCorpusIndexTests(unittest.TestCase):
    def test_all_source_text_indexed_and_shard_tampering_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'shards').mkdir()
            rows=[
                {'submission_id':'26110080001','text':'Consultants discussed E-Rate disclosure.',
                 'filer_raw':'One','text_sha256':''},
                {'submission_id':'26110080002','text':'Consultants asked for fee disclosure.',
                 'filer_raw':'Two','text_sha256':''},
                {'submission_id':'26110080003','text':'Rural library connectivity concerns.',
                 'filer_raw':'Three','text_sha256':''},
            ]
            for row in rows:row['text_sha256']=hashlib.sha256(row['text'].encode()).hexdigest()
            name='filings-0001.jsonl.gz'
            data=gzip.compress(('\n'.join(json.dumps(row) for row in rows)+'\n').encode())
            path=root/'shards'/name
            path.write_bytes(data)
            manifest={'snapshot_id':'test','source_archive_sha256':'test-source',
                      'records':3,'records_with_text':3,
                      'shards':[{'name':name,'sha256':hashlib.sha256(data).hexdigest(),
                                 'records':3}]}
            (root/'manifest.json').write_text(json.dumps(manifest))
            out=root/'qa'
            summary=build(root,out)
            self.assertEqual(summary['records'],3)
            self.assertEqual(summary['with_text'],3)
            published=json.loads((out/'manifest.json').read_text())
            self.assertEqual(len(published['docs']),3)
            # A meaningful word appearing twice is retrievable in both documents.
            posting=json.loads((out/'d.json').read_text())['disclosure']
            self.assertEqual(posting[::2],[0,1])
            path.write_bytes(data+b'corrupted')
            with self.assertRaisesRegex(ValueError,'checksum'):
                build(root,out)

if __name__=='__main__':
    unittest.main()
