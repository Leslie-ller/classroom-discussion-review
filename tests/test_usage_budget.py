import concurrent.futures,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from chemtutor.usage import RequestBudget,BudgetStop,token_summary
from chemtutor.classroom import Model

class UsageBudgetTests(unittest.TestCase):
 def test_concurrent_hard_request_cap(self):
  budget=RequestBudget(5,90000)
  def attempt(_):
   try:budget.reserve(3000);return True
   except BudgetStop:return False
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
   self.assertEqual(sum(pool.map(attempt,range(20))),5)
  self.assertEqual(budget.snapshot()['requests'],5)
 def test_reported_token_threshold_stops_following_requests(self):
  budget=RequestBudget(10,100)
  budget.reserve(30);budget.finish({'total_tokens':101})
  with self.assertRaises(BudgetStop):budget.reserve(30)
 def test_missing_usage_not_reported_as_zero_cost(self):
  budget=RequestBudget();budget.reserve(30);budget.finish()
  self.assertEqual(budget.snapshot()['requests_without_usage'],1)
  summary=token_summary([{'model_request':True},{'model_request':True,'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}},{'stage':'calculate'},{'model_request':False,'usage':{'total_tokens':99999},'replayed_from':'old'}])
  self.assertEqual(summary['requests'],2);self.assertEqual(summary['total_tokens'],12);self.assertFalse(summary['complete'])
 def test_402_persists_and_prevents_network_retry(self):
  with tempfile.TemporaryDirectory() as task:
   p=Path(task)/'pauses.json';m=Model(None,'llm',base_url='https://example.com/v1',api_key='test',model='fake')
   m.budget=RequestBudget(pause_path=p,provider='fake')
   with patch('chemtutor.classroom.urllib.request.urlopen',side_effect=HTTPError('https://example.com',402,'balance',None,None)) as network:
    with self.assertRaises(RuntimeError):m.completion([{'role':'user','content':'Hi'}])
    with self.assertRaises(BudgetStop):m.completion([{'role':'user','content':'Hi'}])
    self.assertEqual(network.call_count,1)
   again=RequestBudget(pause_path=p,provider='fake')
   with self.assertRaises(BudgetStop):again.reserve(3000)
 def test_provider_usage_preserved_on_message(self):
  m=Model(None,'llm',base_url='https://example.com/v1',api_key='test',model='fake');m.budget=RequestBudget()
  class Response:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self,*args):return json.dumps({'choices':[{'message':{'content':'OK'}}],'usage':{'prompt_tokens':20,'completion_tokens':3,'total_tokens':23,'prompt_cache_hit_tokens':10}}).encode()
  with patch('chemtutor.classroom.urllib.request.urlopen',return_value=Response()):r=m.completion([{'role':'user','content':'Hi'}])
  self.assertEqual(r['_usage']['total_tokens'],23);self.assertEqual(m.budget.snapshot()['reported_total_tokens'],23)

if __name__=='__main__':unittest.main()
