import json, random, subprocess, unittest
from pathlib import Path
from src.engine import build_reply_plan, decide_status
from src.normalization import enrich_extraction
from tests.fixtures import base_extraction
ROOT=Path(__file__).resolve().parents[1]

def random_case(rng):
    x=base_extraction()
    if rng.random()<.25:x['customer_name']=None
    if rng.random()<.25:x['phone']=None
    if rng.random()<.08:x['phone']='123'
    if rng.random()<.12:x['vehicle']['category']=None
    if rng.random()<.08:x['competitor']={'price_mentioned':True,'price_text':'8 EUR/day'}
    if rng.random()<.05:x['ambiguities'].append({'code':'conflicting_dates','severity':'high','detail':'parity'})
    if rng.random()<.025:x['multiple_requests']=True
    if rng.random()<.08:x['confidence']=rng.random()*.8
    x=enrich_extraction(x)
    return {'extraction':x,'duplicate_message':rng.random()<.03,'minimum_confidence':.85,'inbound_disposition':'PROCESS','holding_reply_enabled':rng.random()>.1}

class ParityTests(unittest.TestCase):
    def test_python_js_10000(self):
        rng=random.Random(20260913); rows=[random_case(rng) for _ in range(10000)]
        p=subprocess.run(['node',str(ROOT/'tests'/'js_runner.js')],input=json.dumps(rows),text=True,capture_output=True,check=True)
        js=json.loads(p.stdout)
        for i,(r,j) in enumerate(zip(rows,js)):
            d=decide_status(r['extraction'],minimum_confidence=r['minimum_confidence'],duplicate_message=r['duplicate_message'],inbound_disposition=r['inbound_disposition'])
            rp=build_reply_plan(r['extraction'],d,holding_reply_enabled=r['holding_reply_enabled'])
            self.assertEqual(d,j['decision'],f'decision {i}'); self.assertEqual(rp,j['reply'],f'reply {i}')
