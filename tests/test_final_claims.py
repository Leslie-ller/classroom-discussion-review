import json,unittest
from chemtutor.workbench import analyze
from tests.semantic_fixture import reply

class FinalClaimsTests(unittest.TestCase):
    def test_teacher_praise_cannot_programmatically_cancel_verified_contradiction(self):
        packet={'task_type':'math_word_problem','title':'test','messages':[
            {'id':'T1','role':'student','text':'购买数量是197张。'},
            {'id':'T2','role':'teacher','text':'Well done'}],
            'materials':[{'id':'R1','title':'原始题目','text':'原有80张，使用220张，剩余23张。'}]}
        class Model:
            model='fake'
            def __init__(self):self.messages=[]
            def completion(self,messages,tools):
                self.messages.append(messages)
                semantic=reply(messages,'contradicted')
                if semantic:return semantic
                if 'sentences' in json.loads(messages[1]['content']):
                    units=json.loads(messages[1]['content'])['sentences']
                    return {'content':json.dumps({'items':[{'sentence_id':u['id'],'kind':'guidance' if u['field'] in ['title','limits'] else 'derivation','verdict':'supported','reason':'原题数量守恒','evidence':[{'source_id':'R1','quote':'原有80张'}],'calculations':[]} for u in units]},ensure_ascii=False)}
                outputs=[{'checks':[{'id':'C1','claim':'购买163','evidence':[{'source_id':'R1','quote':'原有80张'}]}],'limits':''},
                    {'claims':[{'id':'F1','statement':'购买197','status':'active','quotes':[{'turn_id':'T1','quote':'购买数量是197张'}]}],'limits':''},
                    {'items':[{'claim_id':'FINAL-F1','verdict':'contradicted','reason':'数量守恒','corrected_claim':'购买163张','evidence':[{'source_id':'R1','quote':'使用220张'}],'numeric_error_witness':{'original_expression':'197','correct_expression':'220+23-80'},'calculations':[{'expression':'220+23-80','expected':163}]}]},
                    {'title':'数量守恒','explanation':'应购买163张','worked_contrast':'原有加购买减使用等于剩余','limits':'模拟'}]
                return {'content':json.dumps(outputs[3] if 'verified_corrections' in json.loads(messages[1]['content']) else outputs[len(self.messages)-1],ensure_ascii=False)}
        model=Model();job=analyze(model,packet)
        self.assertEqual(job['status'],'completed');self.assertEqual(job['triage']['decision'],'needs_correction')
        self.assertEqual(job['verified_calculations'][0]['value'],163)
        self.assertNotIn('triage',[t['stage'] for t in job['trace']])
        self.assertNotIn('support_audit',[t['stage'] for t in job['trace']])
        self.assertNotIn('candidate_independent_checks',model.messages[1][1]['content'])

    def test_superseded_statement_removed_before_verification(self):
        packet={'task_type':'math_word_problem','messages':[
            {'id':'T1','role':'student','text':'购买数量是197张。'},
            {'id':'T2','role':'student','text':'现在修正为购买163张。'}],
            'materials':[{'id':'R1','title':'原始题目','text':'原有80张，使用220张，剩余23张。'}]}
        class Model:
            model='fake'
            def __init__(self):self.calls=[]
            def completion(self,messages,tools):
                self.calls.append(messages)
                semantic=reply(messages)
                if semantic:return semantic
                outputs=[{'checks':[{'id':'C1','claim':'163','evidence':[{'source_id':'R1','quote':'原有80张'}]}]},
                    {'claims':[{'id':'F1','statement':'197','status':'superseded','quotes':[{'turn_id':'T1','quote':'购买数量是197张'}],'replaced_by':[{'turn_id':'T2','quote':'修正为购买163张'}]},
                               {'id':'F2','statement':'163','status':'active','quotes':[{'turn_id':'T2','quote':'修正为购买163张'}]}]},
                    {'items':[{'claim_id':'FINAL-F2','verdict':'supported','reason':'实际已改正','evidence':[],'calculations':[]}]}]
                return {'content':json.dumps(outputs[len(self.calls)-1],ensure_ascii=False)}
        m=Model();job=analyze(m,packet)
        self.assertEqual(job['triage']['decision'],'no_correction');self.assertIsNone(job['material'])
        payload=json.loads(m.calls[2][1]['content'])
        self.assertEqual([c['id'] for c in payload['claims']],[ 'FINAL-F2'])

    def test_equivalent_numeric_rewrite_cannot_generate_correction(self):
        packet={'task_type':'math_word_problem','messages':[{'id':'T1','role':'student','text':'第二年200-135=65本。'}],
                'materials':[{'id':'R1','title':'原题','text':'共售200本，第一年90本，第三年45本。'}]}
        class Model:
            model='fake'
            def __init__(self):self.calls=0
            def completion(self,messages,tools):
                self.calls+=1
                semantic=reply(messages)
                if semantic:return semantic
                outputs=[{'checks':[{'id':'C1','claim':'65','evidence':[{'source_id':'R1','quote':'共售200本'}]}]},
                    {'claims':[{'id':'F1','status':'active','statement':'200-135=65','quotes':[{'turn_id':'T1','quote':'200-135=65本'}]}]},
                    {'items':[{'claim_id':'FINAL-F1','verdict':'contradicted','reason':'拟改成分开减','corrected_claim':'200-90-45=65','evidence':[{'source_id':'R1','quote':'第一年90本'}],
                              'numeric_error_witness':{'original_expression':'200-135=65','correct_expression':'200-90-45','original_asserted_value':65},'calculations':[]}]}]
                return {'content':json.dumps(outputs[self.calls-1],ensure_ascii=False)}
        m=Model();job=analyze(m,packet)
        self.assertEqual(job['status'],'completed');self.assertEqual(job['triage']['decision'],'no_correction')
        self.assertIsNone(job['material']);self.assertEqual(m.calls,4)
        self.assertEqual(job['claim_verification']['items'][0]['proposed_verdict'],'contradicted')
