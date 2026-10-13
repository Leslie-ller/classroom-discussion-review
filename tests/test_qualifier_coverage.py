import unittest
from chemtutor.discussion import validate_qualifier_coverage
class QualifierCoverageTests(unittest.TestCase):
 def setUp(self):
  self.turns=[{'id':'T1','role':'student','text':'The only possible combination is 2 and 3. Total is 5.'},{'id':'T2','role':'teacher','text':'Yes, total is 5.'}]
 def test_answer_alone_cannot_cover_uniqueness(self):
  with self.assertRaises(ValueError):validate_qualifier_coverage({'claims':[{'status':'active','statement':'总数5','quotes':[{'turn_id':'T1','quote':'Total is 5.'}]}]},self.turns)
 def test_quote_alone_cannot_hide_qualifier_in_statement(self):
  with self.assertRaises(ValueError):validate_qualifier_coverage({'claims':[{'status':'active','statement':'组合2和3','quotes':[{'turn_id':'T1','quote':'The only possible combination is 2 and 3.'}]}]},self.turns)
 def test_qualifier_retained_but_not_judged_by_guard(self):
  validate_qualifier_coverage({'claims':[{'status':'active','statement':'唯一组合2和3','quotes':[{'turn_id':'T1','quote':'The only possible combination is 2 and 3.'}]}]},self.turns)
 def test_teacher_total_does_not_retract_unique_reason(self):
  with self.assertRaises(ValueError):validate_qualifier_coverage({'claims':[{'status':'superseded','statement':'唯一组合2和3','quotes':[{'turn_id':'T1','quote':'The only possible combination is 2 and 3.'}],'replaced_by':[{'turn_id':'T2','quote':'Yes, total is 5.'}]}]},self.turns)
 def test_question_does_not_become_a_claim(self):
  validate_qualifier_coverage({'claims':[]},[{'id':'T1','role':'student','text':'Does this always work?'}])
 def test_explicit_past_belief_not_revived(self):
  validate_qualifier_coverage({'claims':[]},[{'id':'T1','role':'student','text':'I previously thought this always works, but now understand the exception.'}])
if __name__=='__main__':unittest.main()
