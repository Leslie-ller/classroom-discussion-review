import unittest
from chemtutor.workbench import calculate,validate_input,analyze
class WorkbenchTests(unittest.TestCase):
 def packet(self):return {'title':'模拟','messages':[{'id':'T1','role':'student','text':'我已经理解规则，可以结束。'}],'materials':[{'id':'R1','title':'模拟规则','text':'本次只核查给定规则，不推断额外事实。'}]}
 def test_calculator_rejects_code_and_supports_arithmetic(self):
  self.assertEqual(calculate('80*(1-2*0.1)'),64)
  for x in ['__import__("os")','1**100000','a+1']:
   with self.assertRaises(ValueError):calculate(x)
 def test_duplicate_ids_rejected(self):
  p=self.packet();p['messages']*=2
  with self.assertRaises(ValueError):validate_input(p)
 def test_no_correction_never_calls_material_stage(self):
  class Model:
   model='fake'
   def __init__(self):self.calls=[]
   def completion(self,messages,tools):
    import json
    self.calls.append(messages)
    if len(self.calls)==1:return {'content':json.dumps({'checks':[{'id':'C1','claim':'不推断额外事实','evidence':[{'source_id':'R1','quote':'不推断额外事实'}]}],'limits':'模拟'})}
    return {'content':json.dumps({'decision':'no_correction','summary':'无需纠错','corrections':[],'resolutions':[],'limits':'模拟'})}
  m=Model();j=analyze(m,self.packet());self.assertEqual(j['status'],'completed');self.assertIsNone(j['material']);self.assertEqual(len(m.calls),2)
  self.assertNotIn('conversation',m.calls[0][1]['content']);self.assertIn('conversation',m.calls[1][1]['content'])
 def test_unsupported_correction_blocks_material(self):
  import json
  class Model:
   model='fake'
   def __init__(self):self.calls=0
   def completion(self,messages,tools):
    self.calls+=1
    outputs=[{'checks':[{'id':'C1','claim':'不推断额外事实','evidence':[{'source_id':'R1','quote':'不推断额外事实'}]}],'limits':''},
     {'decision':'needs_correction','summary':'拟纠正','corrections':[{'issue':'不应结束','corrected_claim':'必须继续讨论十次','check_ids':['C1'],'quotes':[{'turn_id':'T1','quote':'可以结束'}]}],'resolutions':[],'limits':''},
     {'items':[{'index':0,'verdict':'insufficient','reason':'规则没有支持十次','evidence':[],'discussion_state':'unclear','turn_evidence':[{'turn_id':'T1','quote':'可以结束'}]}]}]
    return {'content':json.dumps(outputs[self.calls-1],ensure_ascii=False)}
  m=Model();j=analyze(m,self.packet())
  self.assertEqual(j['status'],'completed');self.assertEqual(j['triage']['decision'],'insufficient_evidence')
  self.assertIsNone(j['material']);self.assertEqual(m.calls,3)
  self.assertEqual(j['proposed_triage']['corrections'][0]['corrected_claim'],'必须继续讨论十次')
 def test_knowledge_scope_required_and_empty_materials_allowed(self):
  p=self.packet();p['materials']=[];p['knowledge']={'course':'jwst','version':'1.18.1'}
  self.assertEqual(validate_input(p)['knowledge'],p['knowledge'])
  p['knowledge']={'course':'jwst'}
  with self.assertRaises(ValueError):validate_input(p)
 def test_supported_but_resolved_issue_never_generates_material(self):
  import json
  class Model:
   model='fake'
   def __init__(self):self.calls=0
   def completion(self,messages,tools):
    self.calls+=1
    outputs=[{'checks':[{'id':'C1','claim':'不推断额外事实','evidence':[{'source_id':'R1','quote':'不推断额外事实'}]}],'limits':''},
     {'decision':'needs_correction','summary':'历史错误','corrections':[{'issue':'补了额外事实','corrected_claim':'不推断额外事实','check_ids':['C1'],'quotes':[{'turn_id':'T1','quote':'可以结束'}]}],'resolutions':[],'limits':''},
     {'items':[{'index':0,'verdict':'supported','reason':'规则支持但讨论已修正','evidence':[{'source_id':'R1','quote':'不推断额外事实'}],'discussion_state':'resolved','turn_evidence':[{'turn_id':'T1','quote':'可以结束'}]}]}]
    return {'content':json.dumps(outputs[self.calls-1],ensure_ascii=False)}
  m=Model();j=analyze(m,self.packet())
  self.assertEqual(j['triage']['decision'],'no_correction');self.assertIsNone(j['material']);self.assertEqual(m.calls,3)
if __name__=='__main__':unittest.main()
