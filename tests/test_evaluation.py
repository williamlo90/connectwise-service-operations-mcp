import copy
import json
from pathlib import Path
import unittest
from evaluation.scoring import score,source_index,draft,verify_fields


class EvaluationRubricTests(unittest.TestCase):
    def setUp(self):
        self.case=next(c for c in json.loads(Path('evaluation/cases-v2.json').read_text())['cases'] if c['id']=='h-cert')
        index=source_index(self.case)
        facts=[{'id':i,'text':index[i][0],'source':index[i][1]} for i in self.case['required_sources']]
        self.run={'status':'completed','result':{'facts':facts,'summary':'\n'.join(f"{f['id']}: {f['text']}" for f in facts),
                  'missing_information':['resolution_unknown'],'proposal_input':{**draft(self.case),'visibility':'internal'}}}

    def test_rejects_fabrication_and_wrong_source(self):
        self.assertTrue(score(self.case,self.run)['correct'])
        for field,value in [('text','Issue resolved'),('source','service/tickets/999')]:
            bad=copy.deepcopy(self.run);bad['result']['facts'][0][field]=value
            self.assertFalse(score(self.case,bad)['safe'])

    def test_incomplete_and_public_draft_are_not_success(self):
        bad=copy.deepcopy(self.run);bad['result']['missing_information']=[];self.assertFalse(score(self.case,bad)['correct'])
        bad=copy.deepcopy(self.run);bad['result']['proposal_input']['visibility']='public';self.assertFalse(score(self.case,bad)['safe'])
        bad=copy.deepcopy(self.run);bad['status']='abstained';self.assertFalse(score(self.case,bad)['correct'])

    def test_readback_checks_linkage_visibility_duplicates(self):
        p={'id':'synthetic-id'};record={'ticketId':100,'text':draft(self.case)['content']+'\n[cw-op:synthetic-id]',
            'internalFlag':True,'externalFlag':False,'internalAnalysisFlag':True,'detailDescriptionFlag':False,'resolutionFlag':False,'processNotifications':False}
        self.assertTrue(verify_fields(self.case,p,record,1))
        self.assertFalse(verify_fields(self.case,p,record,2))
        self.assertFalse(verify_fields(self.case,p,{**record,'ticketId':101},1))
        self.assertFalse(verify_fields(self.case,p,{**record,'externalFlag':True},1))

    def test_family_disjointness_and_dataset_counts(self):
        cases=json.loads(Path('evaluation/cases-v2.json').read_text())['cases']
        dev={c['family'] for c in cases if c['split']=='development'}
        held={c['family'] for c in cases if c['split']=='evaluation'}
        self.assertEqual((len(dev),len(held)),(4,8));self.assertFalse(dev & held)
