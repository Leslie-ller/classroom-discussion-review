import copy,unittest
from chemtutor.discussion import validate_updates,current_claim_context
from chemtutor.workbench import quote_valid

class ClaimUpdateTests(unittest.TestCase):
    def setUp(self):
        self.messages=[{'id':'T1','role':'student','text':'300 is three days. It takes 3 weeks.'},
                       {'id':'T2','role':'teacher','text':'300 pages per week, therefore 7 weeks.'},
                       {'id':'T3','role':'student','text':'Yes, 2100/300 = 7 weeks.'}]
        self.old={'turn_id':'T1','quote':'300 is three days.'}
        self.new={'turn_id':'T3','quote':'2100/300 = 7 weeks.'}
        self.context={'turn_id':'T2','quote':'300 pages per week, therefore 7 weeks.'}
        self.ledger={'claims':[{'id':'c1','facet':'relation','quotes':[self.new],'context_quotes':[self.context]}],
                     'updates':[{'claim_id':'c1','facet':'relation','action':'replaced','previous_quotes':[self.old],'current_quotes':[self.new],'reason':'New unit weeks replaces days.'}]}
    def test_new_relation_uses_new_teacher_context_not_old_error(self):
        validate_updates(self.ledger,self.messages,quote_valid)
        ctx=current_claim_context(self.ledger['claims'],self.messages)
        self.assertEqual([t['id'] for t in ctx],['T2','T3'])
        self.assertNotIn('three days',str(ctx))
    def test_replaced_reason_cannot_be_inherited(self):
        x=copy.deepcopy(self.ledger);x['claims'][0]['context_quotes'].append(self.old)
        with self.assertRaises(ValueError):validate_updates(x,self.messages,quote_valid)
    def test_transition_must_be_chronological(self):
        x=copy.deepcopy(self.ledger);x['updates'][0]['previous_quotes']=[self.new]
        with self.assertRaises(ValueError):validate_updates(x,self.messages,quote_valid)
    def test_update_can_anchor_a_contained_actual_quote(self):
        x=copy.deepcopy(self.ledger);x['updates'][0]['current_quotes']=[{'turn_id':'T3','quote':'7 weeks.'}]
        validate_updates(x,self.messages,quote_valid)

    def test_fake_current_quote_rejected(self):
        x=copy.deepcopy(self.ledger);x['updates'][0]['current_quotes']=[{'turn_id':'T3','quote':'It is 10 weeks'}]
        with self.assertRaises(ValueError):validate_updates(x,self.messages,quote_valid)
    def test_current_wrong_reason_is_not_removed(self):
        messages=[{'id':'T1','role':'student','text':'It is 180 treats. There are 60 houses.'}]
        claims=[{'quotes':[{'turn_id':'T1','quote':'There are 60 houses.'}],'context_quotes':[]}]
        self.assertEqual(current_claim_context(claims,messages)[0]['text'],'There are 60 houses.')
    def test_answer_only_does_not_automatically_import_old_reason(self):
        claims=[{'quotes':[self.new],'context_quotes':[]}]
        self.assertEqual([t['id'] for t in current_claim_context(claims,self.messages)],['T3'])

if __name__=='__main__':unittest.main()
