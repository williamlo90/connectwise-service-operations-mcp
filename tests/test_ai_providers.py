import json
import os
import unittest
from unittest.mock import patch
import httpx
from app.ai_providers import generate,ProviderError,LOCAL_DIGEST
import logging
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('service_ops').setLevel(logging.CRITICAL)

VALUE={'decision':'ready','selected_sources':['ticket.summary','ticket.status'],'missing_information':['resolution_unknown']}
EVIDENCE=[{'id':'ticket.summary','text':'VPN fails','source':'service/tickets/100'},{'id':'ticket.status','text':'New','source':'service/tickets/100'}]


class ProviderContracts(unittest.TestCase):
    def config(self):
        return patch.dict(os.environ,{'AI_HOSTED_ENABLED':'true','OPENAI_API_KEY':'synthetic-openai','ANTHROPIC_API_KEY':'synthetic-anthropic',
            'XAI_API_KEY':'synthetic-xai','OPENAI_MODEL':'openai-test','ANTHROPIC_MODEL':'anthropic-test','XAI_MODEL':'xai-test','OLLAMA_MODEL':'local-test'})

    def response(self,p):
        text=json.dumps(VALUE)
        return {'openai':{'status':'completed','output':[{'content':[{'type':'output_text','text':text}]}],'usage':{'input_tokens':12,'output_tokens':8}},
            'anthropic':{'stop_reason':'end_turn','content':[{'type':'text','text':text}],'usage':{'input_tokens':12,'output_tokens':8}},
            'xai':{'choices':[{'finish_reason':'stop','message':{'content':text}}],'usage':{'prompt_tokens':12,'completion_tokens':8}},
            'ollama':{'done':True,'done_reason':'stop','message':{'content':text},'prompt_eval_count':12,'eval_count':8}}[p]

    def test_official_wire_contracts(self):
        for p in ('openai','anthropic','xai','ollama'):
            seen=[]
            def handler(req):
                if req.method=='GET':return httpx.Response(200,json={'models':[{'name':'local-test','digest':LOCAL_DIGEST.removeprefix('sha256:')}]})
                seen.append(req);body=json.loads(req.content)
                self.assertNotIn('synthetic-',json.dumps(body))
                if p=='openai':self.assertEqual(body['text']['format']['type'],'json_schema');self.assertFalse(body['store'])
                elif p=='anthropic':self.assertEqual(req.headers['anthropic-version'],'2023-06-01');self.assertEqual(body['output_config']['format']['type'],'json_schema')
                elif p=='xai':self.assertEqual(body['response_format']['json_schema']['strict'],True)
                else:self.assertFalse(body['stream']);self.assertEqual(body['keep_alive'],0);self.assertNotIn('authorization',req.headers)
                return httpx.Response(200,json=self.response(p))
            with self.config():result=generate(p,EVIDENCE,'summarize_service_ticket',False,httpx.MockTransport(handler))
            self.assertEqual(result.value,VALUE);self.assertEqual(result.usage,{'input_tokens':12,'output_tokens':8});self.assertEqual(len(seen),1)

    def test_no_fallback_or_automatic_retry(self):
        with self.config():
            for p in ('openai','anthropic','xai'):
                with self.assertRaises(ProviderError) as e:generate(p,EVIDENCE,'summary',True)
                self.assertEqual(e.exception.code,'local_only_policy')
            calls=[]
            def limited(req):calls.append(req);return httpx.Response(429)
            with self.assertRaises(ProviderError):generate('openai',EVIDENCE,'summary',False,httpx.MockTransport(limited))
            self.assertEqual(len(calls),1)
            with self.assertRaises(ProviderError) as e:
                generate('ollama',EVIDENCE,'summary',True,httpx.MockTransport(lambda _:httpx.Response(200,json={'models':[]})))
            self.assertEqual(e.exception.code,'local_model_pin_mismatch')
            with self.assertRaises(ProviderError) as e:
                generate('openai',[{'id':'ticket.summary','text':'x'*17000}],'summary',False)
            self.assertEqual(e.exception.code,'context_too_large')

    def test_malformed_truncated_refusal_and_output_limits(self):
        bad=[httpx.Response(200,json={'status':'incomplete'}),httpx.Response(200,json={'status':'completed','output':[{'content':[{'type':'refusal'}]}]}),
             httpx.Response(200,content=b'not-json'),httpx.Response(200,content=b'x'*70000)]
        with self.config():
            for r in bad:
                with self.assertRaises(ProviderError):generate('openai',EVIDENCE,'summary',False,httpx.MockTransport(lambda _:r))
            with self.assertRaises(ProviderError) as e:
                generate('anthropic',EVIDENCE,'summary',False,httpx.MockTransport(lambda _:httpx.Response(200,json={'stop_reason':'refusal'})))
            self.assertEqual(e.exception.code,'provider_refusal')

    def test_missing_usage_remains_unknown(self):
        r=self.response('openai');r.pop('usage')
        with self.config():out=generate('openai',EVIDENCE,'summary',False,httpx.MockTransport(lambda _:httpx.Response(200,json=r)))
        self.assertIsNone(out.usage['input_tokens']);self.assertIsNone(out.usage['output_tokens'])
