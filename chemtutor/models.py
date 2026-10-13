"""Portable Chat Completions transport. Credentials remain on the server."""
import json,os,shlex,ssl,time,urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from .usage import RequestBudget
ROOT=Path(__file__).resolve().parents[1]

def parse_object(content):
 if not isinstance(content,str):raise ValueError('模型没有返回报告')
 value=content.strip()
 if value.startswith('```'):value=value.split('\n',1)[1].rsplit('```',1)[0]
 report=json.loads(value)
 if not isinstance(report,dict):raise ValueError('报告应为对象')
 return report

def load_config(path=None):
 names=['CHEMTUTOR_BASE_URL','CHEMTUTOR_MODEL','CHEMTUTOR_API_KEY','CHEMTUTOR_MAX_REQUESTS','CHEMTUTOR_MAX_TOTAL_TOKENS']
 config={k:os.environ.get(k,'') for k in names}
 if path:
  for line in Path(path).expanduser().read_text().splitlines():
   line=line.strip()
   if not line or line.startswith('#') or '=' not in line:continue
   key,value=line.removeprefix('export ').split('=',1);key=key.strip()
   if key in names:
    parts=shlex.split(value,comments=True);config[key]=parts[0] if len(parts)==1 else ''
 return config

class Model:
 def __init__(self,*args,base_url='',model='',api_key='',max_requests=None,max_total_tokens=None):
  self.base_url=base_url.rstrip('/');self.model=model;self.api_key=api_key
  if self.base_url:
   u=urlsplit(self.base_url)
   if u.scheme not in ['https','http'] or not u.hostname or u.username or u.password or u.query or u.fragment:raise ValueError('API地址需为不含认证信息的HTTP(S)根地址')
  self.http_context=ssl.create_default_context()
  self.budget=RequestBudget(40 if max_requests is None else max_requests,90000 if max_total_tokens is None else max_total_tokens,ROOT/'var/provider-pauses.json',urlsplit(self.base_url).hostname+'|'+model if self.base_url else 'unconfigured')
 @property
 def ready(self):return bool(self.base_url and self.model and self.api_key)
 def completion(self,messages,schemas=None):
  if not self.ready:raise RuntimeError('请先配置API地址、模型与密钥')
  body={'model':self.model,'messages':messages,'temperature':0.1,'max_tokens':3000}
  if schemas:body.update(tools=schemas,tool_choice='auto')
  if urlsplit(self.base_url).hostname=='api.deepseek.com':body['thinking']={'type':'disabled'}
  req=urllib.request.Request(self.base_url+'/chat/completions',data=json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.api_key})
  number=self.budget.reserve(body['max_tokens']);started=time.monotonic()
  try:
   with urllib.request.urlopen(req,context=self.http_context,timeout=90) as response:result=json.loads(response.read(2_000_000))
  except Exception as exc:
   status=getattr(exc,'code',None);self.budget.finish(http_status=status)
   error=RuntimeError('模型接口余额不足（HTTP 402），后续请求已停止。' if status==402 else '模型请求失败'+('（HTTP '+str(status)+'）' if status else '')+'；原始任务已保留。')
   error.request_info={'request_number':number,'http_status':status,'elapsed_seconds':round(time.monotonic()-started,3)}
   raise error from exc
  usage={k:v for k,v in (result.get('usage') or {}).items() if type(v) is int and v>=0 and 'token' in k};self.budget.finish(usage)
  message=result['choices'][0]['message'];message['_usage']=usage;message['_request']={'request_number':number,'elapsed_seconds':round(time.monotonic()-started,3)}
  return message

def create_model(path=None):
 cfg=load_config(path)
 return Model(base_url=cfg['CHEMTUTOR_BASE_URL'],model=cfg['CHEMTUTOR_MODEL'],api_key=cfg['CHEMTUTOR_API_KEY'],max_requests=int(cfg['CHEMTUTOR_MAX_REQUESTS'] or 40),max_total_tokens=int(cfg['CHEMTUTOR_MAX_TOTAL_TOKENS'] or 90000))
