"""Exercise the portable HTTP transport with a local stub, never a paid API."""
import hashlib,json,subprocess,sys,tempfile,threading,time,unittest,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from chemtutor.models import load_config
from chemtutor.history import rename_review,review_name,saved_reviews
ROOT=Path(__file__).resolve().parents[1]

class PublicRuntimeTests(unittest.TestCase):
 def test_name_overlay_preserves_original_and_searches(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'workbench-example.json';p.write_text(json.dumps({'id':'workbench-example','title':'旧标题','model':'example','status':'completed','input':{}}));before=p.read_bytes()
   rename_review(folder,'workbench-example','概率讨论');self.assertEqual(review_name(folder,'workbench-example'),'概率讨论');self.assertEqual(saved_reviews(folder,query='概率')['total'],1);self.assertEqual(before,p.read_bytes())
   for value in ['','a\nb','a'*121]:
    with self.assertRaises(ValueError):rename_review(folder,'workbench-example',value)
   with self.assertRaises(ValueError):rename_review(folder,'../outside','name')
 def test_env_file_is_parsed_not_executed(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'config.env';p.write_text('CHEMTUTOR_MODEL="example model"\nIGNORED=$(touch nope)\nCHEMTUTOR_API_KEY=test\n')
   self.assertEqual(load_config(p)['CHEMTUTOR_MODEL'],'example model');self.assertFalse((Path(folder)/'nope').exists())
 def test_http_review_and_settings_never_expose_key(self):
  count=[0]
  class Stub(BaseHTTPRequestHandler):
   def do_POST(self):
    self.rfile.read(int(self.headers['Content-Length']));count[0]+=1
    report={'checks':[{'id':'C1','claim':'不推断额外事实','evidence':[{'source_id':'R1','quote':'不推断额外事实'}]}],'limits':'模拟'} if count[0]==1 else {'decision':'no_correction','summary':'无需纠错','corrections':[],'resolutions':[],'limits':'模拟'}
    body=json.dumps({'choices':[{'message':{'role':'assistant','content':json.dumps(report,ensure_ascii=False)}}],'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}}).encode()
    self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
   def log_message(self,*args):pass
  stub=ThreadingHTTPServer(('127.0.0.1',0),Stub);threading.Thread(target=stub.serve_forever,daemon=True).start()
  proc=None
  try:
   with tempfile.TemporaryDirectory() as folder:
    config=Path(folder)/'config.env';secret='local-fixture-key';config.write_text(f'CHEMTUTOR_BASE_URL=http://127.0.0.1:{stub.server_address[1]}/v1\nCHEMTUTOR_MODEL=fake\nCHEMTUTOR_API_KEY={secret}\n')
    proc=subprocess.Popen([sys.executable,'-m','chemtutor.classroom','--port','0','--provider-env',str(config)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    base=proc.stdout.readline().strip().split()[-1];self.assertTrue(base.startswith('http://127.0.0.1:'))
    def get(path):
     with urllib.request.urlopen(base+path,timeout=5) as r:return json.loads(r.read())
    def post(path,obj):
     req=urllib.request.Request(base+path,data=json.dumps(obj).encode(),headers={'Content-Type':'application/json'})
     with urllib.request.urlopen(req,timeout=5) as r:return json.loads(r.read())
    self.assertNotIn(secret,json.dumps(get('/api/settings')))
    packet={'title':'HTTP流程模拟','messages':[{'id':'T1','role':'student','text':'我已理解，可以结束。'}],'materials':[{'id':'R1','title':'模拟规则','text':'本次只核查给定规则，不推断额外事实。'}]}
    jid=post('/api/workbench-run',packet)['id'];deadline=time.monotonic()+5
    while True:
     job=get('/api/workbench-job?id='+jid)
     if job['status']!='running' or time.monotonic()>deadline:break
     time.sleep(.05)
    self.assertEqual(job['status'],'completed');self.assertEqual(job['triage']['decision'],'no_correction');self.assertEqual(count[0],2)
    original=(ROOT/'var/workbench'/(jid+'.json')).read_bytes();post('/api/workbench-rename',{'id':jid,'name':'已命名的HTTP复盘'})
    self.assertEqual(get('/api/workbench-job?id='+jid)['display_title'],'已命名的HTTP复盘');self.assertEqual((ROOT/'var/workbench'/(jid+'.json')).read_bytes(),original)
  finally:
   if proc:
    proc.terminate();proc.communicate(timeout=5)
   stub.shutdown();stub.server_close()
if __name__=='__main__':unittest.main()
