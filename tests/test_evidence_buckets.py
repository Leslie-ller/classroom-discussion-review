import unittest
from chemtutor.workbench import separate_discussion_evidence

class EvidenceBucketTests(unittest.TestCase):
 def test_dialogue_is_preserved_but_not_original_evidence(self):
  x={'items':[{'verdict':'contradicted','evidence':[{'source_id':'T1','quote':'I think the answer is 40.'}]}]}
  separate_discussion_evidence(x,{'R1':'The question.'},{'T1':'I think the answer is 40.'})
  self.assertEqual(x['items'][0]['evidence'],[])
  self.assertEqual(x['items'][0]['turn_evidence'][0]['turn_id'],'T1')
 def test_genuine_source_remains_and_fake_quote_rejected(self):
  x={'items':[{'evidence':[{'source_id':'R1','quote':'The original question.'}]}]}
  separate_discussion_evidence(x,{'R1':'The original question.'},{})
  self.assertEqual(x['items'][0]['evidence'][0]['source_id'],'R1')
  with self.assertRaises(ValueError):separate_discussion_evidence({'items':[{'evidence':[{'source_id':'T1','quote':'Never said this'}]}]},{},{'T1':'Hello world.'})

if __name__=='__main__':unittest.main()
