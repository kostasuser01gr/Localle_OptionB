from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from src.engine import decide_status, merge_extractions
from src.normalization import enrich_extraction
from src.reply_safety import deterministic_reply_guard
from tests.fixtures import base_extraction

SEED=20260913


def blank_followup(**overrides):
    defaults={
        'customer_name':None,'phone':None,'email':None,
        'pickup':{'date_text':None,'date_iso':None,'time_text':None,'location':None},
        'vehicle':{'category':None,'category_normalized':None,'transmission':'unspecified','model_text':None},
        'return':{'date_text':None,'date_iso':None,'time_text':None,'location':None},
        'message_intent':'follow_up',
    }
    defaults.update(overrides)
    x=base_extraction(**defaults)
    return enrich_extraction(x)


def multiturm_invariants(n=40000):
    rng=random.Random(SEED)
    checks=0
    for i in range(n):
        kind=i%5
        if kind==0:
            first=enrich_extraction(base_extraction(customer_name=None,phone=None,pickup={'date_text':'03/04','date_iso':None,'time_text':'10:00','location':'Kos Airport'}))
            follow=blank_followup(customer_name='John Smith',phone='+447700123456',confidence=rng.uniform(.86,1))
            merged,conf=merge_extractions(first,follow)
            assert 'ambiguous_pickup_numeric_date' in {a['code'] for a in merged.get('ambiguities',[])}
            assert decide_status(merged)['status']=='NEEDS_INFO'
            checks+=2
        elif kind==1:
            first=enrich_extraction(base_extraction(pickup={'date_text':'18 July','date_iso':None,'time_text':'10:00','location':'Kos Airport'}))
            follow=blank_followup(message_intent='correction')
            follow['pickup']['time_text']=f"{11+rng.randrange(0,6):02d}:00"
            merged,conf=merge_extractions(first,follow)
            assert not conf
            assert merged['pickup']['time_text']==follow['pickup']['time_text']
            assert decide_status(merged)['status']=='READY'
            checks+=3
        elif kind==2:
            first=enrich_extraction(base_extraction(customer_name='John Smith'))
            follow=blank_followup(customer_name='Jane Smith',message_intent='follow_up')
            merged,conf=merge_extractions(first,follow)
            assert 'customer_name' in conf
            assert decide_status(merged)['status']=='HUMAN_REVIEW'
            checks+=2
        elif kind==3:
            first=enrich_extraction(base_extraction(confidence=.60,customer_name=None,phone=None))
            follow=blank_followup(customer_name='John Smith',phone='+447700123456',confidence=.99)
            merged,_=merge_extractions(first,follow)
            assert merged['confidence']==.60
            assert decide_status(merged)['status']=='HUMAN_REVIEW'
            checks+=2
        else:
            lang1=rng.choice(['en','de','fr','it','es','el'])
            lang2=rng.choice(['en','de','fr','it','es','el'])
            first=enrich_extraction(base_extraction(language=lang1))
            follow=blank_followup(language=lang2)
            merged,conf=merge_extractions(first,follow)
            assert not conf
            assert merged['language']==lang2
            checks+=2
    return {'iterations':n,'assertions':checks,'result':'PASS'}


def reply_safety_fuzz(n=30000):
    rng=random.Random(SEED+1)
    clean=[
        'Thanks for your request. Could you please send your phone number?',
        'Danke für Ihre Anfrage. Bitte senden Sie uns noch Ihre Telefonnummer.',
        'Merci pour votre demande. Pouvez-vous nous envoyer votre numéro de téléphone ?',
        'Grazie per la richiesta. Può inviarci il numero di telefono?',
        'Gracias por su solicitud. ¿Puede enviarnos su número de teléfono?',
        'Ευχαριστούμε για το αίτημά σας. Μπορείτε να μας στείλετε το τηλέφωνό σας;'
    ]
    unsafe=[
        'Your booking is confirmed.',
        'Ihre Buchung ist bestätigt.',
        'Votre réservation est confirmée.',
        'La prenotazione è confermata.',
        'Su reserva está confirmada.',
        'Η κράτησή σας επιβεβαιώθηκε.',
        'The price is €35 per day.',
        'That competitor is a scam.',
        'HUMAN_REVIEW: please wait.',
        'Your car is assigned and waiting at the airport.'
    ]
    good=bad=0
    for i in range(n):
        if rng.random()<.5:
            body=rng.choice(clean)
            r=deterministic_reply_guard(body, {'strategy':'ASK_MISSING_FIELDS'})
            assert r['safe'],(body,r)
            good+=1
        else:
            body=rng.choice(unsafe)
            r=deterministic_reply_guard(body, {'strategy':'READY_NEXT_STEP'})
            assert not r['safe'],(body,r)
            bad+=1
    return {'iterations':n,'clean_accepts':good,'unsafe_rejects':bad,'result':'PASS'}


def random_decision_invariants(n=100000):
    rng=random.Random(SEED+2)
    counts={'READY':0,'NEEDS_INFO':0,'HUMAN_REVIEW':0}
    for _ in range(n):
        x=base_extraction()
        if rng.random()<.25:x['customer_name']=None
        if rng.random()<.35:x['phone']=None
        if rng.random()<.12:x['vehicle']['category']=None
        if rng.random()<.05:x['confidence']=rng.uniform(.1,.84)
        if rng.random()<.04:x['ambiguities'].append({'code':'conflicting_dates','severity':'high','detail':'stress'})
        if rng.random()<.03:x['multiple_requests']=True
        if rng.random()<.04:x['pickup']={'date_text':'03/04','date_iso':None,'time_text':'10:00','location':'Kos Airport'}
        if rng.random()<.05 and x['phone'] is not None:x['phone']='123'
        x=enrich_extraction(x)
        d=decide_status(x)
        assert d['status'] in counts
        counts[d['status']]+=1
        if d['status']=='HUMAN_REVIEW':
            assert not d['auto_send_allowed']
        if d['status']=='READY':
            assert not d['missing_fields']
            assert not d['human_review_reason']
        if any(a.get('severity')=='high' for a in x.get('ambiguities',[])):
            assert d['status']=='HUMAN_REVIEW'
        if any(a.get('code')=='ambiguous_pickup_numeric_date' for a in x.get('ambiguities',[])) and d['status']!='HUMAN_REVIEW':
            assert d['status']=='NEEDS_INFO'
            assert 'pickup.date_text' in d['missing_fields']
    return {'iterations':n,'counts':counts,'result':'PASS'}


def main():
    data={
        'seed':SEED,
        'multi_turn':multiturm_invariants(),
        'reply_safety':reply_safety_fuzz(),
        'decision_fuzz':random_decision_invariants(),
        'note':'Synthetic stress tests validate invariants; they are not observed Localle production probabilities.'
    }
    out=ROOT/'evidence'/'stress_results.json'
    out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(data,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
