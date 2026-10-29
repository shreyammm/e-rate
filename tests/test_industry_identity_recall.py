"""Regression tests for non-attribution and provenance in industry recall leads."""
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_industry_identity_recall import (
    rank_lead, source_leads, build
)


class IndustryRecallTest(unittest.TestCase):
    def test_school_technology_department_not_vendor(self):
        school={"role":"school_technology_staff",
                "organization":"Springfield School District Technology Services",
                "needs_review":False}
        signals=source_leads(school,"We support school broadband.")
        self.assertNotIn("metadata_named_technology_or_network_business",signals)
        self.assertFalse(any(x.startswith("author_intro") for x in signals))

    def test_edtech_vendor_and_erate_consultancy_are_review_leads(self):
        x={"role":"other_vendor","organization":"Example Digital Learning Platform LLC",
           "needs_review":True}
        signals=source_leads(x,"We submit comments on screen time conditions.")
        self.assertIn("metadata_named_education_software_or_content",signals)
        self.assertGreaterEqual(rank_lead(x,signals)[0],20)
        y={"role":"unresolved","organization":"","needs_review":True}
        cue=source_leads(y,"I am an E-Rate consultant working for several schools.")
        self.assertIn("author_intro_first_person_erate_consultant",cue)
        self.assertGreaterEqual(rank_lead(y,cue)[0],20)

    def test_mere_policy_mention_does_not_establish_consultancy(self):
        y={"role":"unresolved","organization":"","needs_review":True}
        self.assertEqual(source_leads(y,"The FCC should strengthen E-Rate consultant oversight."),[])
        self.assertEqual(source_leads(y,"A study noted that edtech companies help schools."),[])
        self.assertEqual(source_leads(y,"Our school technology tools require broadband."),[])

    def test_joint_party_is_not_auto_attributed_as_vendor(self):
        x={"role":"school_district","organization":"Springfield School District",
           "multi_submitter_metadata":True,"needs_review":True}
        signals=source_leads(x,"A joint statement submitted to the FCC.")
        self.assertIn("joint_institutional_metadata",signals)
        self.assertLess(rank_lead(x,signals)[0],20)

    def test_source_integrity_failure_blocks_publication(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            s=root/"corpus";(s/"shards").mkdir(parents=True)
            raw=json.dumps({"submission_id":"1","text":"hello",
                            "text_sha256":hashlib.sha256(b"hello").hexdigest()})+"\n"
            gz=gzip.compress(raw.encode())
            (s/"shards/part.jsonl.gz").write_bytes(gz)
            (s/"manifest.json").write_text(json.dumps({
                "records":3231,"shards":[{"name":"part.jsonl.gz","sha256":"bad"}]}))
            r=root/"registry.json"
            r.write_text(json.dumps({"filings":[{"id":str(i)} for i in range(3231)]}))
            with self.assertRaisesRegex(ValueError,"checksum"):
                build(s,r,root/"output.json")
            self.assertFalse((root/"output.json").exists())


if __name__ == "__main__":
    unittest.main()
