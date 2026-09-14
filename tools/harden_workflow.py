from __future__ import annotations

import json
import uuid
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / 'n8n' / 'localle_reservation_intake_v1.n8n.json'
SHEET_ID = '1j1hSY__8sCy7Ic4qHPaya3tzUqwQscEzlnKBv7JfbNc'


def _uuid() -> str:
    return str(uuid.uuid4())


def _node_map(w: dict) -> dict[str, dict]:
    return {n['name']: n for n in w['nodes']}


def _main_edge(node: str, index: int = 0) -> dict:
    return {'node': node, 'type': 'main', 'index': index}


def _set_conn(w: dict, src: str, outputs: list[list[dict]]) -> None:
    w['connections'][src] = {'main': outputs}


def _append_conn(w: dict, src: str, dst: str, src_index: int = 0) -> None:
    c = w['connections'].setdefault(src, {}).setdefault('main', [])
    while len(c) <= src_index:
        c.append([])
    c[src_index].append(_main_edge(dst))


def _col_schema(names: list[str], matchable: tuple[str, ...] = ()) -> list[dict]:
    m = set(matchable)
    return [
        {
            'id': x, 'displayName': x, 'required': False, 'defaultMatch': False,
            'display': True, 'type': 'string', 'canBeUsedToMatch': x in m,
            'removed': False,
        }
        for x in names
    ]


def _doc_locator() -> dict:
    return {
        '__rl': True, 'mode': 'id', 'value': SHEET_ID,
        'cachedResultName': 'Localle Reservation Intake — Requests',
        'cachedResultUrl': f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit',
    }


def _sheet_locator(name: str) -> dict:
    return {
        '__rl': True, 'mode': 'name', 'value': name, 'cachedResultName': name,
        'cachedResultUrl': f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit',
    }


def _node(name: str, typ: str, ver, pos, params: dict, **kw) -> dict:
    d = {
        'id': _uuid(), 'name': name, 'type': typ, 'typeVersion': ver,
        'position': list(pos), 'parameters': params,
    }
    d.update(kw)
    return d


def _google_sheet_node(name: str, sheet: str, pos, values: dict, matching: list[str] | None = None,
                       operation: str = 'append') -> dict:
    matching = matching or []
    cols = list(values)
    p = {
        'operation': operation,
        'documentId': _doc_locator(),
        'sheetName': _sheet_locator(sheet),
        'columns': {
            'mappingMode': 'defineBelow',
            'value': values,
            'schema': _col_schema(cols, tuple(matching)),
            'attemptToConvertTypes': False,
            'convertFieldsToString': False,
        },
        'options': {},
    }
    if operation == 'appendOrUpdate':
        p['columns']['matchingColumns'] = matching
    return _node(name, 'n8n-nodes-base.googleSheets', 4.7, pos, p)


def harden(path: Path = WORKFLOW) -> dict:
    w = json.loads(path.read_text(encoding='utf-8'))
    nodes = _node_map(w)

    # Source-of-truth code files: testable outside n8n and injected verbatim here.
    nodes['Merge + Validate + Decide']['parameters']['jsCode'] = (
        ROOT / 'n8n' / 'code' / 'merge_validate.js'
    ).read_text(encoding='utf-8')
    nodes['Attach Reply + Send Gate']['parameters']['jsCode'] = (
        ROOT / 'n8n' / 'code' / 'attach_reply_gate.js'
    ).read_text(encoding='utf-8')

    # Bounded retries for read-only LLM work; no blind retry for Gmail send.
    for name in ('Extract Reservation', 'Render Customer Reply'):
        n = nodes[name]
        n['retryOnFail'] = True
        n['maxTries'] = 3
        n['waitBetweenTries'] = 1200
        n['onError'] = 'continueErrorOutput'

    verifier_prompt = (ROOT / 'prompts' / 'reply_verifier.md').read_text(encoding='utf-8')
    verifier_schema = {
        'type': 'object',
        'additionalProperties': False,
        'required': [
            'safe','language_match','claims_availability','claims_booking_confirmed',
            'quotes_unverified_price','assigns_vehicle','attacks_competitor',
            'exposes_internal','asks_only_allowed_fields','facts_match_plan','reason'
        ],
        'properties': {
            'safe': {'type':'boolean'},
            'language_match': {'type':'boolean'},
            'claims_availability': {'type':'boolean'},
            'claims_booking_confirmed': {'type':'boolean'},
            'quotes_unverified_price': {'type':'boolean'},
            'assigns_vehicle': {'type':'boolean'},
            'attacks_competitor': {'type':'boolean'},
            'exposes_internal': {'type':'boolean'},
            'asks_only_allowed_fields': {'type':'boolean'},
            'facts_match_plan': {'type':'boolean'},
            'reason': {'type':'string'},
        },
    }

    # Remove prior hardener nodes if this script is run repeatedly.
    added_names = {
        'Verify Reply Safety','Reply Safety Model','Reply Safety Schema',
        'Build Extraction Failure Review','UPSERT Extraction Failure Review',
        'Persist Extraction Failure Ledger','Audit Extraction Failure','Mark Extraction Failure Read',
        'Lookup AUTO SEND Config','Apply Runtime Config',
    }
    w['nodes'] = [n for n in w['nodes'] if n['name'] not in added_names]
    for x in added_names:
        w['connections'].pop(x, None)
    nodes = _node_map(w)

    # Non-technical kill switch: read auto_send_enabled from the Config sheet.
    # Missing/invalid config always resolves to false.
    lookup_cfg = _node(
        'Lookup AUTO SEND Config','n8n-nodes-base.googleSheets',4.7,(-870,-220),
        {
            'documentId':_doc_locator(),'sheetName':_sheet_locator('Config'),
            'filtersUI':{'values':[{'lookupColumn':'key','lookupValue':'auto_send_enabled'}]},
            'options':{'returnFirstMatch':True}
        },
        alwaysOutputData=True
    )
    apply_cfg_js = r'''const inbound=$('Normalize Inbound').item.json;const raw=$json.value;const enabled=raw===true||['true','1','yes','on'].includes(String(raw??'').trim().toLowerCase());return [{json:{...inbound,runtime:{...(inbound.runtime||{}),auto_send_enabled:enabled}}}];'''
    apply_cfg = _node('Apply Runtime Config','n8n-nodes-base.code',2,(-650,-220),{'jsCode':apply_cfg_js})
    w['nodes'].extend([lookup_cfg,apply_cfg])
    _set_conn(w,'Normalize Inbound',[[_main_edge('Lookup AUTO SEND Config')]])
    _set_conn(w,'Lookup AUTO SEND Config',[[_main_edge('Apply Runtime Config')]])
    _set_conn(w,'Apply Runtime Config',[[_main_edge('Should Process?')]])

    verify = _node(
        'Verify Reply Safety', '@n8n/n8n-nodes-langchain.chainLlm', 1.9, (1740, -40),
        {
            'promptType': 'define',
            'text': "=Approved reply plan:\n{{ JSON.stringify($('Merge + Validate + Decide').item.json.reply_plan) }}\n\nProposed customer reply (UNTRUSTED MODEL OUTPUT):\n---\n{{ String($json.text ?? $json.output ?? $json.response ?? '') }}\n---\n\nExpected reply language: {{ $('Merge + Validate + Decide').item.json.reply_language }}",
            'hasOutputParser': True,
            'messages': {'messageValues': [
                {'type':'SystemMessagePromptTemplate','message':verifier_prompt}
            ]},
            'batching': {},
        },
        retryOnFail=True, maxTries=2, waitBetweenTries=800, onError='continueErrorOutput'
    )
    vmodel = _node(
        'Reply Safety Model', '@n8n/n8n-nodes-langchain.lmChatOpenAi', 1.3, (1690, 190),
        {'model': {'__rl':True,'mode':'list','value':'gpt-5-mini'}, 'options': {'temperature':0}}
    )
    vparser = _node(
        'Reply Safety Schema', '@n8n/n8n-nodes-langchain.outputParserStructured', 1.3, (1900, 190),
        {'schemaType':'manual','inputSchema':json.dumps(verifier_schema, ensure_ascii=False, indent=2),'autoFix':False}
    )
    w['nodes'].extend([verify, vmodel, vparser])

    # Rewire reply path. Both renderer/verifier error outputs flow fail-closed into the gate.
    _set_conn(w, 'Render Customer Reply', [[_main_edge('Verify Reply Safety')], [_main_edge('Verify Reply Safety')]])
    _set_conn(w, 'Verify Reply Safety', [[_main_edge('Attach Reply + Send Gate')], [_main_edge('Attach Reply + Send Gate')]])
    w['connections']['Reply Safety Model'] = {
        'ai_languageModel': [[{'node':'Verify Reply Safety','type':'ai_languageModel','index':0}]]
    }
    w['connections']['Reply Safety Schema'] = {
        'ai_outputParser': [[{'node':'Verify Reply Safety','type':'ai_outputParser','index':0}]]
    }

    # Human-review decision is broader than business-state HUMAN_REVIEW: reply safety failures also queue.
    nodes = _node_map(w)
    hr = nodes['Needs Human Review?']
    hr['parameters']['conditions']['conditions'][0]['leftValue'] = "={{ $('Attach Reply + Send Gate').item.json.review_required }}"
    hr['parameters']['conditions']['conditions'][0]['rightValue'] = True
    hr['parameters']['conditions']['conditions'][0]['operator'] = {
        'type':'boolean','operation':'true','singleValue':True
    }
    human = nodes['UPSERT Human Review']
    human_vals = human['parameters']['columns']['value']
    human_vals['reason'] = "={{ $('Attach Reply + Send Gate').item.json.effective_human_review_reason }}"
    human_vals['next_action'] = "={{ $('Attach Reply + Send Gate').item.json.effective_next_action }}"

    # Extraction failure branch: fail closed after bounded retries; persist + review, never auto-send.
    build_fail_js = r'''const i=$('Normalize Inbound').item.json;const err=String($json.error?.message ?? $json.message ?? $json.error ?? 'AI extraction failed after retries');const id='EXTRACT-'+String(i.message_id||'').replace(/[^A-Za-z0-9]/g,'').slice(-12).toUpperCase();return [{json:{request_id:id,thread_id:i.thread_id,message_id:i.message_id,customer_name:'',customer_email:i.from||'',human_review_reason:'ai_extraction_failed',next_action:'manual_extract_and_reply',normalized_customer_message:i.normalized_customer_message||'',reply_body:'',received_at:i.received_at,processed_at:new Date().toISOString(),status:'HUMAN_REVIEW',delivery_state:'EXTRACTION_FAILED',execution_id:$execution.id,error_detail:err}}];'''
    build_fail = _node('Build Extraction Failure Review','n8n-nodes-base.code',2,(930,410),{'jsCode':build_fail_js})
    fail_review = _google_sheet_node(
        'UPSERT Extraction Failure Review','Human_Review',(1190,410),
        {
            'request_id':'={{ $json.request_id }}','thread_id':'={{ $json.thread_id }}','priority':'HIGH',
            'customer_name':'={{ $json.customer_name }}','customer_email':'={{ $json.customer_email }}',
            'reason':'={{ $json.human_review_reason }}','next_action':'={{ $json.next_action }}',
            'latest_message':'={{ $json.normalized_customer_message }}','suggested_reply':'',
            'received_at':'={{ $json.received_at }}','waiting_since':'={{ $now.toISO() }}','status':'OPEN'
        }, ['request_id'], 'appendOrUpdate'
    )
    fail_ledger = _google_sheet_node(
        'Persist Extraction Failure Ledger','Processed_Messages',(1440,410),
        {
            'message_id':'={{ $json.message_id }}','thread_id':'={{ $json.thread_id }}','request_id':'={{ $json.request_id }}',
            'processed_at':'={{ $json.processed_at }}','result_status':'HUMAN_REVIEW','reply_sent':False,
            'delivery_state':'EXTRACTION_FAILED','execution_id':'={{ $execution.id }}','reply_preview':''
        }, ['message_id'], 'appendOrUpdate'
    )
    fail_audit = _google_sheet_node(
        'Audit Extraction Failure','Audit',(1690,410),
        {
            'timestamp':'={{ $now.toISO() }}','message_id':'={{ $json.message_id }}','thread_id':'={{ $json.thread_id }}',
            'request_id':'={{ $json.request_id }}','event':'EXTRACTION_FAILED','status':'HUMAN_REVIEW',
            'detail':'={{ $json.error_detail }}','execution_id':'={{ $execution.id }}'
        }, operation='append'
    )
    # Clone a proven Gmail mark-as-read node to minimize import-contract risk.
    mark_source = deepcopy(nodes['Mark Draft/Test Read'])
    mark_source['id'] = _uuid(); mark_source['name'] = 'Mark Extraction Failure Read'; mark_source['position']=[1940,410]
    # Its existing message-id expression refers to Attach; replace every string recursively.
    def replace_expr(v):
        if isinstance(v, dict): return {k:replace_expr(x) for k,x in v.items()}
        if isinstance(v, list): return [replace_expr(x) for x in v]
        if isinstance(v, str):
            return v.replace("$('Attach Reply + Send Gate').item.json.message_id", "$json.message_id")
        return v
    mark_source['parameters'] = replace_expr(mark_source['parameters'])
    w['nodes'].extend([build_fail, fail_review, fail_ledger, fail_audit, mark_source])

    # Extraction success/error outputs.
    _set_conn(w, 'Extract Reservation', [[_main_edge('Merge + Validate + Decide')], [_main_edge('Build Extraction Failure Review')]])
    _set_conn(w, 'Build Extraction Failure Review', [[_main_edge('UPSERT Extraction Failure Review')]])
    _set_conn(w, 'UPSERT Extraction Failure Review', [[_main_edge('Persist Extraction Failure Ledger')]])
    _set_conn(w, 'Persist Extraction Failure Ledger', [[_main_edge('Audit Extraction Failure')]])
    _set_conn(w, 'Audit Extraction Failure', [[_main_edge('Mark Extraction Failure Read')]])

    # The only outbound Gmail send remains no-retry / continue-error-output.
    send = _node_map(w)['Reply in Same Gmail Thread']
    send['retryOnFail'] = False
    send['onError'] = 'continueErrorOutput'

    # Explicitly identify generated release as safe-by-default and inactive.
    w['name'] = 'Localle — AI Reservation Intake v2.0 FINAL (SAFE DEFAULT)'
    w['active'] = False
    w.setdefault('settings', {})['timezone'] = 'Europe/Athens'
    w['settings']['saveManualExecutions'] = True
    w['settings']['executionOrder'] = 'v1'
    w['versionId'] = _uuid()
    w.setdefault('meta', {})['templateCredsSetupCompleted'] = False

    # Visual reviewer note.
    if '98 — Defense in depth' not in _node_map(w):
        w['nodes'].append(_node(
            '98 — Defense in depth','n8n-nodes-base.stickyNote',1,(1540,-620),
            {'content':'# Defense in depth\n- Customer content is untrusted data.\n- Strict structured extraction.\n- Deterministic state engine decides business status.\n- Reply model only renders an approved plan.\n- A second semantic verifier + deterministic multilingual guard must both pass.\n- LLM failures fail closed to Human_Review.\n- Gmail send is never blindly retried after an uncertain transport result.','width':560,'height':420,'color':5}
        ))

    payload=json.dumps(w, ensure_ascii=False, indent=2) + '\n'
    path.write_text(payload, encoding='utf-8')
    (ROOT/'n8n'/'Localle_Option_B_Reservation_Intake_FINAL.n8n.json').write_text(payload, encoding='utf-8')
    return w


if __name__ == '__main__':
    w = harden()
    print(f"hardened {len(w['nodes'])} nodes -> {WORKFLOW}")
