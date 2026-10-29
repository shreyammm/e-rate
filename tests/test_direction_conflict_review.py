"""Review queue must preserve source identity and NOT claim a mixed model label is a real disagreement."""
import unittest
from scripts.build_direction_conflict_review import make_queue, COLUMNS


class DirectionConflictQueueTest(unittest.TestCase):
    @staticmethod
    def fixture():
        rows=[
            {'id':'1','issue':'erate_sunset','position':'support','start':12,
             'quote':'Reject any proposal to cut the E-Rate program.',
             'action':'Preserve E-Rate'},
            {'id':'1','issue':'erate_sunset','position':'oppose','start':12,
             'quote':'Reject any proposal to cut the E-Rate program.',
             'action':'Reject cuts'},
            {'id':'2','issue':'consultant_registration','position':'support','start':8,
             'quote':'Some consultants should register.','action':'Register firms'},
            {'id':'2','issue':'consultant_registration','position':'oppose','start':40,
             'quote':'Individuals need not separately register.','action':'Exempt employees'},
            {'id':'3','issue':'other_policy_issue','position':'support','start':0,
             'quote':'General passage','action':'Support some option'},
            {'id':'3','issue':'other_policy_issue','position':'oppose','start':3,
             'quote':'Another passage','action':'Oppose other option'},
        ]
        ledger={'rows':rows,'_file_sha256':'mockhash'}
        audit={'machine_claim_ledger_sha256':'mockhash',
               'coverage':{'machine_claim_rows_checked':len(rows)},
               'machine_direction_consistency':{
                   'identical_source_spans_with_opposing_machine_labels':1}}
        census={'coverage':{'filings':3},
                'inputs':{'machine_claim_ledger_sha256':'mockhash','player_registry_sha256':'registry'},
                'filings':[
                    {'id':'1','group':'school_institutions','role':'school_district','organization':'Example Schools'},
                    {'id':'2','group':'erate_consultants','role':'erate_consultant','organization':'Consultants LLC'},
                    {'id':'3','group':'parents','role':'parent_guardian','organization':''},
                ]}
        return ledger,audit,census

    def test_exact_source_span_review_is_prioritized_and_not_direction(self):
        ledger,audit,census=self.fixture()
        rows,summary=make_queue(ledger,audit,census)
        self.assertEqual(len(rows),2)
        self.assertEqual(summary['same_span_case_count'],1)
        self.assertEqual(summary['filing_issue_pairs_with_both_machine_labels'],2)
        by={r['filing_id']:r for r in rows}
        self.assertTrue(by['1']['identical_quote_and_offset'])
        self.assertEqual(by['1']['review_stratum'],'identical_span_conflicting_machine_labels')
        self.assertFalse(by['2']['identical_quote_and_offset'])
        self.assertEqual(by['2']['review_stratum'],'industry_issue_mixed_machine_labels')
        self.assertFalse(any(x.get('review_status') for x in rows))
        self.assertEqual(set(COLUMNS)-set(rows[0]),{'review_stratum'}-{'review_stratum'})

    def test_model_claims_same_policy_issue_only_and_digest_must_match(self):
        ledger,audit,census=self.fixture()
        rows,_=make_queue(ledger,audit,census,max_other_per_group=1)
        self.assertNotIn('3',{r['filing_id'] for r in rows})
        audit['machine_claim_ledger_sha256']='wrong'
        with self.assertRaisesRegex(ValueError,"hash"):
            make_queue(ledger,audit,census)

    def test_reproducible_and_unmodeled_preserved(self):
        ledger,audit,census=self.fixture()
        x,a=make_queue(ledger,audit,census)
        y,b=make_queue(ledger,audit,census)
        self.assertEqual(x,y)
        self.assertEqual(a['review_strata'],b['review_strata'])


if __name__ == "__main__":
    unittest.main()
