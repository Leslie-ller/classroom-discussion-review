"""Read saved review metadata without sending conversations to the browser list."""
import json
from pathlib import Path

def saved_reviews(directory,*,query='',offset=0,limit=20):
 if not 0<=offset or not 1<=limit<=50:raise ValueError('分页范围无效')
 rows=[];needle=query.strip().casefold()
 for path in Path(directory).glob('workbench-*.json'):
  try:
   job=json.loads(path.read_text());jid=job['id']
   if job.get('model')=='fake':continue
   if not isinstance(jid,str) or jid!=path.stem:continue
   title=review_name(directory,jid) or str(job.get('title','未命名复盘'))
   if needle and needle not in (title+' '+jid).casefold():continue
   packet=job.get('input') or {};triage=job.get('triage') or {}
   rows.append({'id':jid,'title':title,'started_at':job.get('started_at',''),
    'status':job.get('status','unknown'),'decision':triage.get('decision'),
    'has_material':bool(job.get('material')),'turns':len(packet.get('messages',[])),
    'materials':len(packet.get('materials',[]))})
  except (OSError,ValueError,KeyError,TypeError):continue
 rows.sort(key=lambda row:(row['started_at'],row['id']),reverse=True)
 return {'total':len(rows),'offset':offset,'limit':limit,'items':rows[offset:offset+limit]}

def review_name(directory,jid):
 import re
 if not isinstance(jid,str) or not re.fullmatch(r'workbench-[A-Za-z0-9]{1,35}',jid):raise ValueError('复盘编号无效')
 path=Path(directory)/'review-names'/(jid+'.json')
 try:
  value=json.loads(path.read_text()).get('name')
  return value if isinstance(value,str) and value.strip() else None
 except (OSError,ValueError):return None

def rename_review(directory,jid,name):
 import re
 if not isinstance(jid,str) or not re.fullmatch(r'workbench-[A-Za-z0-9]{1,35}',jid):raise ValueError('复盘编号无效')
 if not isinstance(name,str) or not 1<=len(name.strip())<=120 or any(ord(c)<32 for c in name):raise ValueError('名称需为1至120个字符，不能含换行')
 if not (Path(directory)/(jid+'.json')).is_file():raise ValueError('找不到复盘记录')
 folder=Path(directory)/'review-names';folder.mkdir(exist_ok=True)
 title=name.strip();(folder/(jid+'.json')).write_text(json.dumps({'name':title},ensure_ascii=False)+'\n')
 return {'id':jid,'name':title}
