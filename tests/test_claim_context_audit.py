import unittest
from scripts.audit_claim_context import context_flags, opposing_machine_position_flags

def row(quote,**kwargs):
    return {'id':'26110080000','start':0,'quote':quote,'argument':'',
            'action':'', 'position':'discussion_no_position',**kwargs}

class ContextAuditTest(unittest.TestCase):
    def test_plain_quote_is_not_auto_attributed_elsewhere(self):
        q='School internet networks have recurring annual maintenance expenses.'
        self.assertNotIn('possible_attributed_or_opposing_voice',context_flags(row(q),q))
    def test_references_other_speakers_without_concluding_truth(self):
        intro='The opponents argue that screen time harms all students. '
        quote='Screen time harms all students when internet is provided.'
        r={'id':'1','start':len(intro),'quote':quote,'position':'discussion_no_position',
           'argument':'screen time concerns','action':'review screen time'}
        self.assertIn('possible_attributed_or_opposing_voice',context_flags(r,intro+quote))
    def test_preserves_negation_as_review_lead_only(self):
        quote='The FCC should not eliminate the E-rate program.'
        x={'id':'1','start':0,'quote':quote,'position':'support','argument':'','action':''}
        self.assertIn('negation_in_source_requires_stance_inspection',context_flags(x,quote))
    def test_quote_offsets_must_match(self):
        with self.assertRaises(ValueError):
            context_flags(row('The text is not source correct'), 'Something entirely different')
    def test_redaction_honors_checkpoint_excerpt_end_boundary(self):
        # Raw quote ends in a partial phone number. The longer source text
        # contains the remaining digits, but those must NOT be redacted here.
        body='Office of Superintendent (978) 640-7800 and public comment.'
        excerpt='Office of Superintendent (978)'
        item={'id':'1','start':0,'quote':excerpt,'position':'discussion_no_position',
              'argument':'','action':''}
        self.assertIsInstance(context_flags(item,body,original_quote=excerpt),list)

    def test_same_issue_opposing_machine_labels_are_review_leads_not_stances(self):
        claims=[
            {'id':'1','issue':'erate_sunset','position':'support','start':10,'quote':'quoted text'},
            {'id':'1','issue':'erate_sunset','position':'oppose','start':55,'quote':'different text'},
            {'id':'1','issue':'screen_time_condition','position':'oppose','start':55,'quote':'different text'},
            {'id':'2','issue':'erate_sunset','position':'support','start':10,'quote':'quoted text'},
            {'id':'3','issue':'other_policy_issue','position':'support','start':3,'quote':'random'},
            {'id':'3','issue':'other_policy_issue','position':'oppose','start':4,'quote':'other'}
        ]
        flags, stats=opposing_machine_position_flags(claims)
        self.assertEqual(stats['filing_issue_pairs_with_mixed_machine_directions'],1)
        self.assertEqual(stats['filings_with_mixed_machine_directions'],1)
        self.assertEqual(stats['identical_source_spans_with_opposing_machine_labels'],0)
        self.assertEqual(set(flags),{'0','1'})
        self.assertIn('mixed_machine_directions_same_filing_and_issue',flags['0'])

    def test_identical_source_evidence_with_opposite_labels_is_prioritized(self):
        rows=[{'id':'1','issue':'consultant_registration','position':p,
               'start':33,'quote':'one source passage'} for p in ('support','oppose')]
        flags, summary=opposing_machine_position_flags(rows)
        self.assertEqual(summary['identical_source_spans_with_opposing_machine_labels'],1)
        self.assertTrue(all('opposing_machine_labels_on_identical_source_span' in x
                            for x in flags.values()))

    def test_multiple_claim_uses_are_review_flagged(self):
        quote='High-speed school access improves connectivity reliability.'
        self.assertIn('one_quote_used_for_multiple_machine_claims',context_flags(row(quote),quote,3))
if __name__=='__main__':unittest.main()
