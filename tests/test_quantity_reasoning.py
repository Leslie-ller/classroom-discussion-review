import json,unittest
from chemtutor.workbench import analyze
from tests.semantic_fixture import reply
PACKET={'task_type':'math_word_problem','messages':[{'id':'T1','role':'student','text':'90/30=3，所以可以邀请3位朋友。'}],'materials':[{'id':'R1','title':'原题','text':'预算90元，每人30元，自己和朋友一起参加。'}]}
class Fake:
 model='fake'
 def __init__(self,confirmation='contradicted',inconsistent=False):self.calls=0;self.confirmation=confirmation;self.inconsistent=inconsistent
 def completion(self,messages,tools):
  p=json.loads(messages[1]['content'])
  if 'expected_claim_ids' in p and 'conversation' in p:
   self.semantic_calls=getattr(self,'semantic_calls',0)+1
   verdict='contradicted' if self.semantic_calls==1 else self.confirmation
   r=reply(messages,verdict,'3是总人数，朋友是3-1=2位。');x=json.loads(r['content'])
   for i in x['items']:
    i['asserted_quantity']['scope']='朋友';i['source_quantity']['scope']='总参与者'
    if self.inconsistent:i.update(verdict='supported',relation_verdict='different',reasoning_verdict='invalid')
   return {'content':json.dumps(x)}
  if 'sentences' in p:
   return {'content':json.dumps({'items':[{'sentence_id':u['id'],'kind':'guidance','verdict':'supported','reason':'模拟核验','evidence':[],'calculations':[]} for u in p['sentences']]})}
  if 'verified_corrections' in p:return {'content':json.dumps({'title':'人数','explanation':'总人数3，朋友2。','worked_contrast':'3-1=2。','limits':'模拟'})}
  outputs=[{'checks':[{'id':'C1','claim':'2位朋友','evidence':[{'source_id':'R1','quote':'自己和朋友一起参加'}]}]},
  {'claims':[{'id':'F1','statement':'3位朋友','status':'active','quotes':[{'turn_id':'T1','quote':'可以邀请3位朋友'}]}]},
  {'items':[{'claim_id':'FINAL-F1','verdict':'contradicted','reason':'把总人数当朋友','corrected_claim':'3为总人数','evidence':[{'source_id':'R1','quote':'自己和朋友一起参加'}],'numeric_error_witness':{'original_expression':'3','correct_expression':'90/30'},'calculations':[]}]}]
  r={'content':json.dumps(outputs[self.calls])};self.calls+=1;return r
class QuantityReasoningTests(unittest.TestCase):
 def test_equal_value_different_quantity_can_be_corrected(self):
  j=analyze(Fake(),PACKET)
  self.assertEqual(j['status'],'completed');self.assertEqual(j['triage']['decision'],'needs_correction')
  self.assertFalse(j['claim_verification']['items'][0]['numeric_error_witness']['has_numeric_discrepancy'])
  self.assertTrue(j['claim_verification']['items'][0]['semantic_error_confirmed'])
 def test_two_reviewers_disagree_hold_semantic_correction(self):
  j=analyze(Fake('supported'),PACKET)
  self.assertEqual(j['triage']['decision'],'insufficient_evidence');self.assertIsNone(j['material'])
 def test_supported_label_with_wrong_scope_is_rejected(self):
  j=analyze(Fake(inconsistent=True),PACKET)
  self.assertEqual(j['triage']['decision'],'insufficient_evidence');self.assertIsNone(j['material'])
  self.assertEqual(j['semantic_review']['status'],'incomplete')
 def test_numeric_string_is_parsed_without_relaxing_arithmetic(self):
  class StringFake(Fake):
   def completion(self,messages,tools):
    r=super().completion(messages,tools);p=json.loads(messages[1]['content'])
    if 'expected_claim_ids' in p and 'conversation' in p:
     x=json.loads(r['content'])
     for i in x['items']:i['calculations']=[{'expression':'90/30','expected':'3'}]
     r['content']=json.dumps(x)
    return r
  j=analyze(StringFake(),PACKET)
  self.assertEqual(j['triage']['decision'],'needs_correction')
  self.assertEqual(j['semantic_review']['first']['items'][0]['calculations'][0]['expected'],3)
if __name__=='__main__':unittest.main()
