import json,unittest
from chemtutor.workbench import analyze,literal_equations
from tests.semantic_fixture import reply

PACKET={'task_type':'math_word_problem','messages':[{'id':'T1','role':'student','text':'应购买197张。'}],'materials':[{'id':'R1','title':'原题','text':'原有80张，使用220张，剩余23张。'}]}
class Fake:
 model='fake'
 def __init__(self,mode):self.calls=0;self.drafts=0;self.mode=mode
 def completion(self,messages,tools):
  semantic=reply(messages,'contradicted')
  if semantic:return semantic
  self.calls+=1;payload=json.loads(messages[1]['content'])
  if 'sentences' in json.loads(messages[1]['content']):
   items=[]
   for u in payload['sentences']:
    bad='277' in u['text'] or (self.mode=='second_reject' and '独立复核' in messages[0]['content'] and u['field']=='explanation')
    items.append({'sentence_id':u['id'],'kind':'derivation' if u['field']=='explanation' else 'guidance','verdict':'contradicted' if bad else 'supported','reason':'总量应为243，277无依据' if bad else '符合原题','evidence':[{'source_id':'R1','quote':'原有80张'}],'calculations':[]})
   return {'content':json.dumps({'items':items})}
  if 'verified_corrections' in payload:
   self.drafts+=1
   explanation='需要的总量为277张。' if self.mode=='semantic' and self.drafts==1 else '220+23-80=164。' if self.mode=='numeric' else '新增数量为163张，合计80+163-220=23。' if self.mode!='chinese' else '每月总花费为100+20+100=220。'
   return {'content':json.dumps({'title':'数量守恒','explanation':explanation,'worked_contrast':'核对剩余数量。','limits':'按题干给定数量。'})}
  outputs=[{'checks':[{'id':'C1','claim':'163','evidence':[{'source_id':'R1','quote':'原有80张'}]}]},
    {'claims':[{'id':'F1','statement':'197','status':'active','quotes':[{'turn_id':'T1','quote':'应购买197张'}]}]},
    {'items':[{'claim_id':'FINAL-F1','verdict':'contradicted','reason':'数量守恒','corrected_claim':'163张','evidence':[{'source_id':'R1','quote':'使用220张'}],'numeric_error_witness':{'original_expression':'197','correct_expression':'220+23-80'},'calculations':[]}]}]
  return {'content':json.dumps(outputs[self.calls-1])}
class MaterialAuditTests(unittest.TestCase):
 def test_semantically_wrong_quantity_is_rewritten_and_history_kept(self):
  j=analyze(Fake('semantic'),PACKET)
  self.assertEqual(j['status'],'completed');self.assertEqual(len(j['material_attempts']),2)
  self.assertFalse(j['material_attempts'][0]['passed']);self.assertTrue(j['material_attempts'][1]['passed'])
  self.assertNotIn('277',j['material']['explanation']);self.assertEqual(j['material_audit']['status'],'passed')
 def test_literal_false_equation_withheld_even_if_model_approves_it(self):
  j=analyze(Fake('numeric'),PACKET)
  self.assertEqual(j['status'],'completed');self.assertIsNone(j['material'])
  self.assertEqual(j['material_audit']['status'],'withheld');self.assertEqual(len(j['material_attempts']),2)
  self.assertFalse(j['material_audit']['literal_equations'][0]['passed'])
 def test_chinese_prefix_does_not_truncate_expression(self):
  j=analyze(Fake('chinese'),PACKET)
  self.assertEqual(j['material_audit']['status'],'passed')
  self.assertEqual(j['material_audit']['literal_equations'][0]['expression'],'100+20+100')
 def test_second_independent_rejection_blocks_first_approval(self):
  j=analyze(Fake('second_reject'),PACKET)
  self.assertIsNone(j['material']);self.assertEqual(j['material_audit']['status'],'withheld')
  self.assertTrue(all(i['verdict']=='supported' for i in j['material_attempts'][0]['audit']['items']))
  self.assertTrue(any(i['verdict']=='contradicted' for i in j['material_attempts'][0]['independent_review']['items']))
 def test_complete_chained_equalities_are_checked(self):
  rows=literal_equations('总费用10000+80×500=10000+40000=50000美元。','S1')
  self.assertEqual(len(rows),2);self.assertTrue(all(r['passed'] for r in rows))
  self.assertFalse(all(r['passed'] for r in literal_equations('总费用10000+80×500=10000+30000=40000美元。','S1')))
 def test_percentages_are_numeric_fractions_in_prose(self):
  rows=literal_equations('人数50×(1+60%)=50×1.6=80位。','S1')
  self.assertEqual(len(rows),2);self.assertTrue(all(r['passed'] for r in rows))
if __name__=='__main__':unittest.main()
