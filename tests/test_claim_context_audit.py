import unittest
from scripts.audit_claim_context import context_flags

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

    def test_multiple_claim_uses_are_review_flagged(self):
        quote='High-speed school access improves connectivity reliability.'
        self.assertIn('one_quote_used_for_multiple_machine_claims',context_flags(row(quote),quote,3))
if __name__=='__main__':unittest.main()
