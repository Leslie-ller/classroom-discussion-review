"""Fake independent reviewer outputs for pipeline behavior tests (not quality scores)."""
import json

def reply(messages,verdict='supported',corrected='163张'):
 p=json.loads(messages[1]['content'])
 if not ('expected_claim_ids' in p and 'conversation' in p):return None
 items=[]
 for c in p['claims']:
  items.append({'claim_id':c['id'],'verdict':verdict,'reason':'按原题数量关系逐项核对',
   'asserted_quantity':{'entity':'原文对象','unit':'个','scope':'原文范围','relation':c['statement']},
   'source_quantity':{'entity':'题干对象','unit':'个','scope':'题干范围','relation':'原题关系'},
   'relation_verdict':'different' if verdict=='contradicted' else 'same' if verdict=='supported' else 'unclear',
   'reasoning_verdict':'invalid' if verdict=='contradicted' else 'not_stated',
   'corrected_claim':corrected if verdict=='contradicted' else '',
   'evidence':[{'source_id':p['original_materials'][0]['id'],'quote':p['original_materials'][0]['text']}],
   'quotes':c['quotes'],'calculations':[]})
 return {'content':json.dumps({'items':items},ensure_ascii=False)}
