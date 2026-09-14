from __future__ import annotations

import json
from collections import deque
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WF=ROOT/'n8n'/'localle_reservation_intake_v1.n8n.json'
FINAL=ROOT/'n8n'/'Localle_Option_B_Reservation_Intake_FINAL.n8n.json'
CONTRACT=ROOT/'config'/'live_sheet_contract.json'
CONFIG=ROOT/'config'/'exercise_config.json'


def main():
    w=json.loads(WF.read_text())
    final=json.loads(FINAL.read_text())
    contract=json.loads(CONTRACT.read_text())
    cfg=json.loads(CONFIG.read_text())
    assert w==final, 'final workflow alias drifted from validated workflow'
    names=[n['name'] for n in w['nodes']]
    assert len(names)==len(set(names)), 'duplicate node names'
    nodes={n['name']:n for n in w['nodes']}
    assert not w.get('active'), 'workflow must ship inactive'
    assert cfg['auto_send_enabled'] is False

    # No credentials may be embedded in any exported node.
    for n in w['nodes']:
        assert 'credentials' not in n, f"embedded credential block: {n['name']}"

    # Every referenced graph target exists.
    for src,groups in w['connections'].items():
        assert src in nodes, f'connection source missing: {src}'
        for kind,branches in groups.items():
            for branch in branches:
                for edge in branch:
                    assert edge['node'] in nodes, f"missing target {edge['node']} from {src}"

    # Main-flow reachability from Gmail Trigger, excluding intentional sticky + AI auxiliary nodes.
    seen={'Gmail Trigger'}; q=deque(['Gmail Trigger'])
    while q:
        src=q.popleft()
        for branch in w['connections'].get(src,{}).get('main',[]):
            for edge in branch:
                dst=edge['node']
                if dst not in seen:
                    seen.add(dst);q.append(dst)
    aux_types={
        '@n8n/n8n-nodes-langchain.lmChatOpenAi',
        '@n8n/n8n-nodes-langchain.outputParserStructured',
        'n8n-nodes-base.stickyNote',
    }
    expected={n['name'] for n in w['nodes'] if n['type'] not in aux_types}
    missing=expected-seen
    assert not missing, f'unreachable execution nodes: {sorted(missing)}'

    # AI auxiliary nodes must be attached to real chain nodes.
    for n in w['nodes']:
        if n['type'] not in aux_types or n['type']=='n8n-nodes-base.stickyNote':
            continue
        groups=w['connections'].get(n['name'],{})
        assert groups, f"AI auxiliary node is unattached: {n['name']}"

    # Exactly one customer-email send/reply action, and it is guarded.
    sends=[n for n in w['nodes'] if n['type']=='n8n-nodes-base.gmail' and n['parameters'].get('operation') in {'reply','send'}]
    assert [n['name'] for n in sends]==['Reply in Same Gmail Thread']
    send=sends[0]
    assert send.get('retryOnFail',False) is False
    parents=[]
    for src,groups in w['connections'].items():
        for branch in groups.get('main',[]):
            for edge in branch:
                if edge['node']=='Reply in Same Gmail Thread': parents.append(src)
    assert parents==['AUTO SEND enabled + safe?'],parents

    # Required defense nodes exist.
    for required in [
        'Lookup AUTO SEND Config','Apply Runtime Config','Lookup Processed Message',
        'Merge + Validate + Decide','Verify Reply Safety','Attach Reply + Send Gate',
        'Persist Event Ledger','Build Extraction Failure Review','Build Send-Uncertain Review'
    ]:
        assert required in nodes,required

    # Business entity and event idempotency keys are contract-critical.
    assert nodes['UPSERT Request']['parameters']['columns']['matchingColumns']==['thread_id']
    assert nodes['Persist Event Ledger']['parameters']['columns']['matchingColumns']==['message_id']
    assert nodes['Confirm Reply Sent in Ledger']['parameters']['columns']['matchingColumns']==['message_id']
    assert nodes['UPSERT Human Review']['parameters']['columns']['matchingColumns']==['request_id']
    assert nodes['Lookup Request by Thread']['parameters']['filtersUI']['values'][0]['lookupColumn']=='thread_id'
    assert nodes['Lookup Processed Message']['parameters']['filtersUI']['values'][0]['lookupColumn']=='message_id'

    # Sheets mapping must target real live-contract headers.
    for n in w['nodes']:
        if n['type']!='n8n-nodes-base.googleSheets': continue
        sheet=n['parameters'].get('sheetName',{}).get('value')
        if not sheet: continue
        assert sheet in contract['sheets'],f"unknown sheet: {sheet}"
        allowed=set(contract['sheets'][sheet])
        mapped=set(n['parameters'].get('columns',{}).get('value',{}))
        assert not mapped-allowed,f"{n['name']} unknown columns: {mapped-allowed}"

    result={
        'result':'PASS','workflow_nodes':len(w['nodes']),'main_reachable_execution_nodes':len(expected),
        'unique_customer_send_nodes':1,'credentials_embedded':False,'ships_active':False,
        'auto_send_default':False,'sheet_contracts_checked':True,'final_alias_identical':True,
    }
    (ROOT/'evidence'/'release_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
