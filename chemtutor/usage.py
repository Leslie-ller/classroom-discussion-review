"""Bound requests, retain provider token counts, and stop after exhausted balance."""
import hashlib,json,threading
from pathlib import Path

class BudgetStop(RuntimeError):
    pass

class RequestBudget:
    def __init__(self,max_requests=40,max_tokens=90000,pause_path=None,provider=''):
        if max_requests<1 or max_tokens<1:raise ValueError('预算必须大于0')
        self.max_requests=max_requests;self.max_tokens=max_tokens
        self.requests=0;self.tokens=0;self.inflight=0;self.unknown_usage=0
        self.lock=threading.RLock();self.pause_path=Path(pause_path) if pause_path else None
        self.provider=hashlib.sha256(provider.encode()).hexdigest()[:20];self.paused=False
    def reserve(self,output_limit):
        with self.lock:
            if self.paused:raise BudgetStop('模型接口余额不足，已停止后续请求；恢复余额后显式解除暂停。')
            if self.pause_path and self.pause_path.exists():
                data=json.loads(self.pause_path.read_text())
                if self.provider in data:raise BudgetStop('模型接口此前返回余额不足，已暂停；本次没有发送请求。')
            if self.requests>=self.max_requests:raise BudgetStop('本轮模型请求达到上限 '+str(self.max_requests)+'，本次没有发送请求。')
            # Provider-reported token budget is a soft threshold: prompt size is not known before billing.
            if self.tokens+self.inflight*output_limit>=self.max_tokens:raise BudgetStop('已报告token用量达到预算阈值，本次没有发送请求。')
            self.requests+=1;self.inflight+=1
            return self.requests
    def finish(self,usage=None,http_status=None):
        with self.lock:
            self.inflight-=1
            total=(usage or {}).get('total_tokens')
            if type(total) is int and total>=0:self.tokens+=total
            else:self.unknown_usage+=1
            if http_status==402:
                self.paused=True
                if self.pause_path:
                    self.pause_path.parent.mkdir(parents=True,exist_ok=True)
                    data=json.loads(self.pause_path.read_text()) if self.pause_path.exists() else {}
                    data[self.provider]={'http_status':402,'reason':'Insufficient Balance'}
                    self.pause_path.write_text(json.dumps(data,indent=2))
    def snapshot(self):
        with self.lock:
            return {'requests':self.requests,'max_requests':self.max_requests,'reported_total_tokens':self.tokens,
                    'token_threshold':self.max_tokens,'requests_without_usage':self.unknown_usage,
                    'inflight':self.inflight,'paused':self.paused,'token_threshold_is_soft':True}

def token_summary(trace):
    rows=[t for t in trace if t.get('model_request')]
    summary={'requests':len(rows),'requests_with_usage':0,'prompt_tokens':0,'completion_tokens':0,'total_tokens':0,'requests_without_usage':0}
    for t in rows:
        usage=t.get('usage') or {}
        if type(usage.get('total_tokens')) is not int:
            summary['requests_without_usage']+=1;continue
        summary['requests_with_usage']+=1
        for k in ['prompt_tokens','completion_tokens','total_tokens']:
            if type(usage.get(k)) is int:summary[k]+=usage[k]
    summary['complete']=summary['requests_without_usage']==0
    return summary
