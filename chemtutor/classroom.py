"""Loopback UI and API for the post-class discussion review module."""
import argparse,json,threading,uuid,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from .models import Model,parse_object,create_model
from .history import saved_reviews,review_name,rename_review
from .knowledge_index import KnowledgeIndex
from .workbench import analyze,validate_input
ROOT=Path(__file__).resolve().parents[1];LOCK=threading.RLock()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8875);parser.add_argument('--provider-env');args=parser.parse_args()
 model=create_model(args.provider_env);index=KnowledgeIndex(ROOT/'var/knowledge.sqlite3')
 class Handler(BaseHTTPRequestHandler):
  def send(self,data,status=200,mime='application/json; charset=utf-8'):
   body=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode()
   self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)));self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
  def do_GET(self):
   u=urlsplit(self.path);q=parse_qs(u.query)
   pages={'/':'workbench','/workbench':'workbench','/history':'history','/settings':'settings','/examples':'examples'}
   if u.path in pages:return self.send((ROOT/'web'/(pages[u.path]+'.html')).read_bytes(),mime='text/html; charset=utf-8')
   if u.path=='/api/example':
    name=q.get('id',[''])[0]
    if name not in ['reading','allocation']:return self.send({'error':'示例不存在'},404)
    return self.send((ROOT/'examples'/(name+'.json')).read_bytes())
   if u.path=='/api/workbench-bootstrap':
    with index.connect() as db:scopes=[{'course':c,'version':v,'documents':n} for c,v,n in db.execute('SELECT course,version,count(*) FROM kb_documents GROUP BY course,version')]
    return self.send({'model':model.model or '未配置','samples':[json.loads(p.read_text()) for p in sorted((ROOT/'examples').glob('*.json'))],'knowledge_scopes':scopes,'material_evaluations':[]})
   if u.path=='/api/settings':
    endpoint=urlsplit(model.base_url)
    return self.send({'active':{'model':model.model or '未配置','connection':'compatible_api','endpoint':model.base_url or '未配置','reasoning':None,'authentication':'本机API配置','authentication_status':'已读取配置，未测试连接' if model.ready else '尚未配置完成','config_source':str(Path(args.provider_env).expanduser()) if args.provider_env else '环境变量'},'defaults':{'model':'由本机配置提供','reasoning_effort':'由API服务决定','fallback':False},'limits':{'process_requests':model.budget.max_requests,'process_token_threshold':model.budget.max_tokens},'config_file':str(ROOT/'.env.example'),'editable':False})
   if u.path=='/api/workbench-history':
    try:return self.send(saved_reviews(ROOT/'var/workbench',query=q.get('q',[''])[0][:200],offset=int(q.get('offset',['0'])[0]),limit=int(q.get('limit',['20'])[0])))
    except ValueError:return self.send({'error':'分页范围无效'},400)
   if u.path=='/api/workbench-job':
    jid=q.get('id',[''])[0]
    try:name=review_name(ROOT/'var/workbench',jid)
    except ValueError:return self.send({'error':'复盘编号无效'},400)
    target=ROOT/'var/workbench'/(jid+'.json')
    if not target.exists():return self.send({'id':jid,'status':'running'})
    try:job=json.loads(target.read_text())
    except ValueError:return self.send({'id':jid,'status':'running'})
    job['display_title']=name or job['title'];return self.send(job)
   return self.send({'error':'未找到'},404)
  def do_POST(self):
   try:
    if self.headers.get('Origin') not in [None,'http://'+self.headers.get('Host','')]:return self.send({'error':'不允许跨站请求'},403)
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=300000:raise ValueError('请求为空或过大')
    packet=json.loads(self.rfile.read(length))
    if self.path=='/api/workbench-rename':
     with LOCK:result=rename_review(ROOT/'var/workbench',packet.get('id'),packet.get('name'))
     return self.send(result)
    if self.path!='/api/workbench-run':return self.send({'error':'未找到'},404)
    if not model.ready:return self.send({'error':'请先配置API地址、模型和密钥。查看设置页及README。'},503)
    packet=validate_input(packet);jid='workbench-'+uuid.uuid4().hex[:10]
    threading.Thread(target=analyze,args=(model,packet,jid),daemon=True).start();return self.send({'id':jid},202)
   except (ValueError,TypeError,KeyError) as exc:return self.send({'error':str(exc)},400)
  def log_message(self,*args):pass
 server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
 print(f'Classroom review http://127.0.0.1:{server.server_address[1]}',flush=True)
 server.serve_forever()
if __name__=='__main__':main()
