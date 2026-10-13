import copy,unittest
from chemtutor.ratios import parse_rate,validate_inventory
SOURCE='There are 50000 candles. 5% of the more dangerous candles also have a defect. Half the purple eggs have five pieces; 1/4 of the blue eggs do.'
def record(token='5%',base='more dangerous candles',part='have a defect'):
 return {'ratios':[{'id':'P1','rate_text':token,'base_quote':base,'part_quote':part,'relation':'share','evidence':{'source_id':'R1','quote':SOURCE}}]}
class RatioInventoryTests(unittest.TestCase):
 def test_explicit_denominator_cannot_be_renamed_all(self):
  with self.assertRaisesRegex(ValueError,'显式分母'):validate_inventory(record(base='candles'),{'R1':SOURCE})
 def test_actual_scoped_denominator_is_preserved(self):
  r=validate_inventory(record(),{'R1':SOURCE})['ratios'][0]
  self.assertEqual(r['value'],0.05);self.assertTrue(r['explicit_denominator'])
 def test_fraction_and_half_scope_cannot_be_swapped(self):
  self.assertEqual(validate_inventory(record('Half','purple eggs','five pieces'),{'R1':SOURCE})['ratios'][0]['value'],0.5)
  with self.assertRaises(ValueError):validate_inventory(record('Half','blue eggs','five pieces'),{'R1':SOURCE})
  self.assertEqual(validate_inventory(record('1/4','blue eggs','do'),{'R1':SOURCE})['ratios'][0]['value'],0.25)
 def test_fake_source_rate_and_duplicate_identifiers_are_rejected(self):
  with self.assertRaises(ValueError):validate_inventory(record('4%'),{'R1':SOURCE})
  x=record();x['ratios']*=2
  with self.assertRaises(ValueError):validate_inventory(x,{'R1':SOURCE})
 def test_percentages_and_fractions_do_not_execute_code(self):
  self.assertEqual(parse_rate('150%'),1.5)
  self.assertEqual(parse_rate('2/5'),0.4)
  for bad in ['1/0','__import__("os")','1+2']:
   with self.assertRaises((ValueError,ZeroDivisionError)):parse_rate(bad)
if __name__=='__main__':unittest.main()

class RatioPipelineTests(unittest.TestCase):
 def test_supported_label_cannot_hide_unsupported_denominator_transfer(self):
  import json
  from chemtutor.workbench import analyze
  from tests.test_quantity_reasoning import Fake,PACKET
  p=copy.deepcopy(PACKET);p['materials'][0]['text']+=' 5% of the special guests attend.'
  class ScopedFake(Fake):
   def completion(self,messages,tools):
    payload=json.loads(messages[1]['content'])
    if messages[0]['content'].startswith('只从原始题干'):
     return {'content':json.dumps({'ratios':[{'id':'P1','rate_text':'5%','base_quote':'special guests','part_quote':'attend','relation':'share','evidence':{'source_id':'R1','quote':'5% of the special guests attend.'}}]})}
    r=super().completion(messages,tools)
    if 'expected_claim_ids' in payload and 'conversation' in payload:
     obj=json.loads(r['content'])
     for item in obj['items']:
      item.update(verdict='supported',relation_verdict='same',reasoning_verdict='valid',ratio_usage='applied',ratio_checks=[{'source_ratio_id':'P1','applied_base':'all guests','base_relation':'different','transfer_basis':'not_given','reason':'no source support'}])
     r['content']=json.dumps(obj)
    return r
  job=analyze(ScopedFake(),p)
  self.assertEqual(job['status'],'completed');self.assertEqual(job['triage']['decision'],'insufficient_evidence')
  self.assertEqual(job['semantic_review']['status'],'incomplete');self.assertIsNone(job['material'])
 def test_pure_acknowledgments_do_not_replace_last_mathematical_claim(self):
  from chemtutor.workbench import analyze
  from tests.test_quantity_reasoning import Fake,PACKET
  p=copy.deepcopy(PACKET);p['messages'].append({'id':'T2','role':'student','text':'Yes, I understand. I appreciate your help!'})
  job=analyze(Fake(),p)
  self.assertEqual(job['triage']['decision'],'needs_correction')
  self.assertEqual(job['active_claims'][0]['quotes'][0]['turn_id'],'T1')

class NumericBindingTests(unittest.TestCase):
 def test_scoped_ratio_application_cannot_silently_rename_total_count(self):
  from chemtutor.ratios import numeric_base_bindings
  inventory=validate_inventory(record(),{'R1':SOURCE})
  claim={'quotes':[{'turn_id':'T1','quote':'5% of 50000 is 2500 candles that have the defect.'}]}
  rows=numeric_base_bindings(claim,inventory,{'R1':SOURCE})
  self.assertEqual(len(rows),1);self.assertEqual(rows[0]['actual_application'],'5% of 50000')
  self.assertEqual(rows[0]['source_denominator_quote'],'more dangerous candles')
 def test_unconditional_or_explicitly_bound_count_is_not_flagged(self):
  from chemtutor.ratios import numeric_base_bindings
  inventory=validate_inventory(record(base='more dangerous candles'),{'R1':SOURCE})
  claim={'quotes':[{'turn_id':'T1','quote':'5% of 50000 is 2500.'}]}
  self.assertFalse(numeric_base_bindings(claim,inventory,{'R1':'There are 50000 more dangerous candles.'}))
  inventory['ratios'][0]['base_quote']='candles'
  self.assertFalse(numeric_base_bindings(claim,inventory,{'R1':SOURCE}))

class NumericalStageFailureTests(unittest.TestCase):
 def test_numeric_witness_format_failure_does_not_block_independent_semantics(self):
  import json
  from tests.test_quantity_reasoning import Fake,PACKET
  from chemtutor.workbench import analyze
  class BrokenNumeric(Fake):
   def completion(self,messages,tools):
    if 'candidate_independent_checks' in json.loads(messages[1]['content']):
     return {'content':json.dumps({'items':[{'claim_id':'FINAL-F1','verdict':'contradicted','reason':'scope mismatch','corrected_claim':'3 total','evidence':[{'source_id':'R1','quote':'自己和朋友一起参加'}]}]})}
    return super().completion(messages,tools)
  job=analyze(BrokenNumeric(),PACKET)
  self.assertEqual(job['status'],'completed');self.assertEqual(job['triage']['decision'],'needs_correction')
  self.assertIn('numeric_review_failure',job)
  self.assertTrue(job['claim_verification']['items'][0]['semantic_error_confirmed'])

class InventoryNormalizationTests(unittest.TestCase):
 def test_ratio_phrases_normalize_without_promoting_plain_quantity(self):
  from chemtutor.ratios import normalize_inventory
  source='10 minutes; six times that long; half as much time; 2 kittens each.'
  rows=[]
  for n,(token,kind) in enumerate([('10 minutes','per_period'),('six times that long','share'),('half as much time','share'),('2 kittens each','per_period')]):
   rows.append({'id':str(n),'rate_text':token,'base_quote':'time','part_quote':'time','relation':kind,'evidence':{'source_id':'R1','quote':source}})
  x=normalize_inventory({'ratios':rows},{'R1':source})
  self.assertEqual([r['rate_text'] for r in x['ratios']],['six times','half','2'])
  self.assertEqual([r['relation'] for r in x['ratios']],['multiplier','share','per_unit'])
  self.assertEqual(len(x['omitted_quantities']),1);self.assertEqual(parse_rate('six times'),6)
 def test_pronoun_and_suggested_antecedent_remain_separate(self):
  from chemtutor.ratios import normalize_inventory
  source='30 bunnies; he gave 2/5 of them to his friend.'
  x={'ratios':[{'id':'P1','rate_text':'2/5','base_quote':'30 bunnies','part_quote':'to his friend','relation':'share','evidence':{'source_id':'R1','quote':source}}]}
  x=validate_inventory(normalize_inventory(x,{'R1':source}),{'R1':source})
  self.assertEqual(x['ratios'][0]['base_quote'],'them');self.assertEqual(x['ratios'][0]['antecedent_quote'],'30 bunnies')
 def test_normalization_does_not_make_fake_rate_or_wrong_group_valid(self):
  from chemtutor.ratios import normalize_inventory
  with self.assertRaises(ValueError):normalize_inventory(record('4%'),{'R1':SOURCE})
  with self.assertRaises(ValueError):validate_inventory(normalize_inventory(record(base='candles'),{'R1':SOURCE}),{'R1':SOURCE})
