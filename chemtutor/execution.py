"""Shared request protocol, budgets, retries and trace persistence."""
import json
from .usage import BudgetStop


class Execution:
    def __init__(self,model,job,save,parse,normalize,max_requests=16):
        self.model,self.job,self.save=model,job,save
        self.parse,self.normalize=parse,normalize
        self.max_requests=max_requests

    def call(self,stage,messages,tools=None):
        if sum(t.get('model_request',False) for t in self.job['trace'])>=self.max_requests:
            raise BudgetStop('本案例达到16次模型请求上限，停止后续调用。')
        trace={'stage':stage,'messages':json.loads(json.dumps(messages))}
        self.job['trace'].append(trace);self.save()
        try:response=self.model.completion(messages,tools or [])
        except Exception as exc:
            if not isinstance(exc,BudgetStop):trace['model_request']=True
            trace['request_error']=str(exc)
            if hasattr(exc,'request_info'):trace['request']=exc.request_info
            self.save();raise
        trace.update(model_request=not bool(response.get('_replayed')),response=response,
                     usage=response.get('_usage'),request=response.get('_request'))
        if response.get('_replayed'):trace['replayed_from']=response['_replayed']
        self.save();return response

    def json_stage(self,stage,prompt,payload,validator):
        messages=[{'role':'system','content':prompt},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}]
        for _ in range(3):
            response=self.call(stage,messages)
            try:
                obj=self.normalize(stage,self.parse(stage,response['content']))
                validator(obj);return obj
            except (ValueError,KeyError,TypeError,SyntaxError,ZeroDivisionError) as exc:
                self.job['trace'][-1]['validation_error']=str(exc)
                messages.extend([{'role':'assistant','content':response['content']},
                                 {'role':'user','content':'仅修复格式或引文：'+str(exc)}])
                self.save()
        raise ValueError(stage+'未通过校验')
