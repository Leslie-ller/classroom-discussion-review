import json,unittest
from chemtutor.workbench import analyze
from tests.semantic_fixture import reply
class TriageOnlyTests(unittest.TestCase):
 def test_verified_correction_can_stop_before_material_when_requested(self):
  packet={'task_type':'math_word_problem','messages':[{'id':'T1','role':'student','text':'总数为5个。'}],'materials':[{'id':'R1','title':'原题','text':'实际总数为10个。'}]}
  class Fake:
   model='fake'
   def __init__(self):self.calls=0
   def completion(self,messages,tools):
    self.calls+=1
    semantic=reply(messages,'contradicted','10个')
    if semantic:return semantic
    outputs=[{'checks':[{'id':'C1','claim':'10个','evidence':[{'source_id':'R1','quote':'实际总数为10个'}]}]},
             {'claims':[{'id':'F1','statement':'总数5个','status':'active','quotes':[{'turn_id':'T1','quote':'总数为5个'}]}]},
             {'items':[{'claim_id':'FINAL-F1','verdict':'contradicted','reason':'总数差异','corrected_claim':'10个','evidence':[{'source_id':'R1','quote':'实际总数为10个'}],'numeric_error_witness':{'original_expression':'5','correct_expression':'10'},'calculations':[]}]}]
    return {'content':json.dumps(outputs[self.calls-1],ensure_ascii=False)}
  m=Fake();j=analyze(m,packet,generate_material=False)
  self.assertEqual(j['status'],'completed');self.assertEqual(j['triage']['decision'],'needs_correction')
  self.assertIsNone(j['material']);self.assertEqual(j['material_generation']['status'],'not_requested')
  self.assertNotIn('material',[t['stage'] for t in j['trace']]);self.assertEqual(m.calls,5)
if __name__=='__main__':unittest.main()
