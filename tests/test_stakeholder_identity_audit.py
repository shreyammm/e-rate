"""Regression tests for identity reconciliation and independent model validation."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reconcile_stakeholder_labels import build, comparison, old_category, priority
from scripts.identity_llm_pass import parse_answer

class StakeholderIdentityAuditTest(unittest.TestCase):
    def test_mapping_does_not_pretend_vendors_are_advocacy_groups(self):
        self.assertIsNone(old_category("edtech_learning_vendor"))
        self.assertIsNone(old_category("trade_association"))
        self.assertEqual(old_category("school_technology_staff"),"school_staff")
        self.assertEqual(comparison("school_staff","school_district"),"school_institution_vs_staff")
        self.assertEqual(comparison("consultant","advocacy_group"),"cross_sector_conflict")
        self.assertEqual(comparison("consultant","unknown"),"deterministic_specific_model_unknown")

    def test_source_evidence_validation_prevents_model_hallucination(self):
        text="I am a district technology director and work for a public school."
        digest=hashlib.sha256(text.encode()).hexdigest()
        args=(text,"", "test-model", "55", digest)
        good=parse_answer({
            "role":"school_technology_staff",
            "basis":"author_self_description",
            "evidence_quote":"I am a district technology director",
        },*args)
        self.assertEqual(good["role"],"school_technology_staff")
        self.assertTrue(good["source_evidence_verified"])
        bad=parse_answer({
            "role":"erate_consultant","basis":"author_self_description",
            "evidence_quote":"I am an E-Rate consultant",
        },*args)
        self.assertEqual(bad["role"],"unresolved")
        self.assertFalse(bad["source_evidence_verified"])
        meta=parse_answer({
            "role":"edtech_learning_vendor","basis":"metadata_organization",
            "evidence_quote":"",
        },text,"Edtech Example LLC","test-model","55",digest)
        self.assertEqual(meta["role"],"edtech_learning_vendor")
        self.assertTrue(meta["source_evidence_verified"])
        no_meta=parse_answer({
            "role":"edtech_learning_vendor","basis":"metadata_organization",
            "evidence_quote":"",
        },*args)
        self.assertEqual(no_meta["role"],"unresolved")

    def test_end_to_end_report_counts_and_privacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            registry={"coverage":{"manually_reviewed_filings":0},"filings":[
                dict(id="1",role="school_district",organization="Example School District",basis="filer_field_organization",
                     identity_status="strong_source_cue",needs_review=False,source_url="https://www.fcc.gov/ecfs/filing/1",
                     text_sha256="a",multi_submitter_metadata=False),
                dict(id="2",role="erate_consultant",organization="Example E-Rate Services LLC",basis="filer_field_organization",
                     identity_status="candidate",needs_review=True,source_url="https://www.fcc.gov/ecfs/filing/2",
                     text_sha256="b",multi_submitter_metadata=False),
                dict(id="3",role="edtech_learning_vendor",organization="Example Edtech LLC",basis="curated_company_type_candidate",
                     identity_status="candidate",needs_review=True,source_url="https://www.fcc.gov/ecfs/filing/3",
                     text_sha256="c",multi_submitter_metadata=False),
                dict(id="4",role="named_person_capacity_unstated",organization="",basis="provisional_full_text_role",
                     identity_status="candidate",needs_review=True,source_url="https://www.fcc.gov/ecfs/filing/4",
                     text_sha256="d",multi_submitter_metadata=False)
            ]}
            qa={"filings":{
                "1":{"machine_inferred_role":"school_staff"},
                "2":{"machine_inferred_role":"advocacy_group"},
                "3":{"machine_inferred_role":"unknown"},
                "4":{"machine_inferred_role":"library"},
            }}
            r=root/"registry.json";q=root/"quality.json";out=root/"audit.json";second=root/"second"
            second.mkdir()
            r.write_text(json.dumps(registry));q.write_text(json.dumps(qa))
            (second/"2.json").write_text(json.dumps({
                "submission_id":"2","source_sha256":"b","role":"erate_consultant",
                "basis":"metadata_organization","source_evidence_verified":True,
                "model":"test-model","status":"unvalidated_machine_candidate"
            }))
            report=build(r,q,second,out)
            c=report["summary"]["comparison_counts"]
            self.assertEqual(c["school_institution_vs_staff"],1)
            self.assertEqual(c["cross_sector_conflict"],1)
            self.assertEqual(c["unmapped_taxonomy"],1)
            self.assertEqual(c["model_specific_deterministic_unknown"],1)
            self.assertEqual(report["coverage"]["both_specific_comparable"],2)
            self.assertEqual(report["summary"]["raw_disagreements_among_comparable"],3)
            self.assertEqual(report["coverage"]["second_pass_completed"],1)
            self.assertEqual(report["summary"]["human_adjudicated"],0)
            text=out.read_text()
            self.assertNotIn("filer_raw",text)
            self.assertNotIn("evidence_quote",text)
            self.assertTrue(report["high_priority_review"])
            # Model outputs must refer to the same source content.
            model=json.loads((second/"2.json").read_text())
            model["source_sha256"]="incorrect"
            (second/"2.json").write_text(json.dumps(model))
            with self.assertRaises(ValueError):
                build(r,q,second,out)

if __name__=="__main__":
    unittest.main()
