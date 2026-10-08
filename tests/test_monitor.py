import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from app.monitor import poll


class MonitorTests(unittest.TestCase):
    def test_local_delivery_deduplication_resolution_and_redaction(self):
        healthy = {'database':'ready','worker_healthy':True,'queue':{'oldest_seconds':0,'review':0},
                   'stale_sync_count':0,'operations':[],'assistant':[]}
        with tempfile.TemporaryDirectory() as directory:
            with patch('app.monitor.snapshot', side_effect=RuntimeError('sensitive-password-example')):
                self.assertEqual(poll(directory)[0]['code'],'database_unavailable')
                self.assertEqual(poll(directory),[])
            with patch('app.monitor.snapshot',return_value=healthy):
                self.assertEqual(poll(directory)[0]['state'],'resolved')
            events=[json.loads(x) for x in (Path(directory)/'alerts.jsonl').read_text().splitlines()]
            self.assertEqual(len(events),2)
            self.assertNotIn('sensitive-password-example', ''.join(p.read_text() for p in Path(directory).iterdir()))

    def test_queue_and_unknown_write_alerts_have_no_payload(self):
        value={'database':'ready','worker_healthy':False,'queue':{'oldest_seconds':90,'review':1},
               'stale_sync_count':1,'operations':[{'status':'unknown','n':1}],'assistant':[]}
        with tempfile.TemporaryDirectory() as directory, patch('app.monitor.snapshot',return_value=value):
            self.assertEqual({e['code'] for e in poll(directory)},
                             {'worker_stale','queue_backlog','sync_review','sync_stale','write_review'})
