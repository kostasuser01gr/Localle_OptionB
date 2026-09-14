from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from src.pipeline import process_message
from src.store import SQLiteStore
from tests.fixtures import base_extraction, message


def x_missing_identity(_):
    return base_extraction(customer_name=None,phone=None,email='guest@example.com')

def x_identity_followup(_):
    x=base_extraction(
        customer_name='John Smith',phone='+44 7700 123456',email=None,
        pickup={'date_text':None,'date_iso':None,'time_text':None,'location':None},
        vehicle={'category':None,'transmission':'unspecified','model_text':None},
        message_intent='follow_up'
    )
    x['return']={'date_text':None,'date_iso':None,'time_text':None,'location':None}
    return x

def x_german_complete(_):
    return base_extraction(
        language='de',customer_name='Anna Keller',phone='+49 170 5551234',email='anna@example.de',
        pickup={'date_text':'5 August','date_iso':None,'time_text':None,'location':'Kos Airport'},
        vehicle={'category':'small','transmission':'automatic','model_text':None},confidence=.98
    )
    x['return']={'date_text':'10 August','date_iso':None,'time_text':None,'location':None}
    return x

def x_competitor(_):
    return base_extraction(
        language='fr',customer_name='Jean Dupont',phone='+33 612345678',email='jean@example.fr',
        pickup={'date_text':'3 September','date_iso':None,'time_text':None,'location':'Kos Airport'},
        competitor={'price_mentioned':True,'price_text':'8 € par jour'},confidence=.98
    )
    x['return']={'date_text':'7 September','date_iso':None,'time_text':None,'location':None}
    return x

def x_ambiguous(_):
    return base_extraction(
        customer_name='Chris',phone='+44 7700 900111',
        pickup={'date_text':'03/04','date_iso':None,'time_text':None,'location':'Kos Airport'},
        vehicle={'category':'small','transmission':'automatic','model_text':None},confidence=.98
    )
    x['return']={'date_text':'08/04','date_iso':None,'time_text':None,'location':None}
    return x

def x_multiple(_):
    return base_extraction(multiple_requests=True,confidence=.99)


def slim(result):
    return {
        'duplicate':result.get('duplicate'),
        'request_id':(result.get('row') or {}).get('request_id'),
        'revision':(result.get('row') or {}).get('revision'),
        'status':result['decision']['status'],
        'missing_fields':result['decision'].get('missing_fields'),
        'human_review_reason':result['decision'].get('human_review_reason'),
        'reply_plan':result.get('reply_plan'),
        'reply':result.get('reply'),
        'send_enabled':result.get('send_enabled',False),
    }


def main():
    db=tempfile.NamedTemporaryFile(suffix='.db',delete=False);db.close()
    store=SQLiteStore(db.name)
    results=[]
    # Same-thread continuation proves one business request, two messages, revision update.
    r1=process_message(message(message_id='m-en-1',thread_id='t-en',body='Hi, small automatic 18-23 July, Kos Airport 10am.'),x_missing_identity,store)
    r2=process_message(message(message_id='m-en-2',thread_id='t-en',body='John Smith, +44 7700 123456'),x_identity_followup,store)
    results += [{'case':'english_missing_identity',**slim(r1)},{'case':'english_followup_same_request',**slim(r2)}]
    results.append({'case':'german_complete',**slim(process_message(message(message_id='m-de',thread_id='t-de',body='German complete request'),x_german_complete,store))})
    results.append({'case':'french_competitor_objection',**slim(process_message(message(message_id='m-fr',thread_id='t-fr',body='French request with competitor offer'),x_competitor,store))})
    results.append({'case':'ambiguous_numeric_date',**slim(process_message(message(message_id='m-amb',thread_id='t-amb',body='03/04 to 08/04'),x_ambiguous,store))})
    results.append({'case':'multiple_requests',**slim(process_message(message(message_id='m-multi',thread_id='t-multi',body='two independent cars'),x_multiple,store))})
    # Duplicate immutable message ID is a no-op.
    results.append({'case':'duplicate_delivery',**slim(process_message(message(message_id='m-de',thread_id='t-de',body='German complete request'),x_german_complete,store))})
    # Auto-reply is ignored before extractor runs.
    called=[]
    def should_not_run(_): called.append(True); return base_extraction()
    auto=process_message(message(message_id='m-auto',thread_id='t-auto',body='Out of office',headers={'Auto-Submitted':'auto-replied'}),should_not_run,store)
    results.append({'case':'auto_reply_loop_guard','status':auto['decision']['status'],'extractor_called':bool(called),'reply':auto.get('reply','')})
    out={'safe_default':'auto_send_enabled=false','cases':results}
    (ROOT/'evidence'/'demo_replay.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
