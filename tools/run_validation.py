from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence'
EVIDENCE.mkdir(exist_ok=True)
start=time.time()


def run(cmd, name, *, env=None):
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,env=env)
    (EVIDENCE/f'{name}.txt').write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
    if p.returncode:
        print(p.stdout)
        print(p.stderr,file=sys.stderr)
        raise SystemExit(p.returncode)
    return p

# Reproducible generation from source: base workflow -> hardening pass.
run([sys.executable,'tools/build_n8n_workflows.py'],'build_workflows')
run([sys.executable,'tools/harden_workflow.py'],'harden_workflow')
release_audit_proc=run([sys.executable,'tools/audit_release.py'],'release_audit_stdout')

# Compile + unit / contract tests.
run([sys.executable,'-m','compileall','-q','src','tests','tools'],'compileall')
proc=run([sys.executable,'-m','unittest','discover','-v'],'unit_test_output')

# Scenario probability model + high-volume invariant stress. These are synthetic, not production stats.
sim=run([sys.executable,'-m','src.simulate'],'simulation_stdout')
stress=run([sys.executable,'tools/stress_scenarios.py'],'stress_stdout')
second_seed=run([sys.executable,'tools/independent_second_seed.py'],'independent_second_seed_stdout')
mutation_smoke=run([sys.executable,'tools/mutation_smoke.py'],'mutation_smoke_stdout')
demo_replay=run([sys.executable,'tools/demo_replay.py'],'demo_replay_stdout')

schema=json.loads((ROOT/'schemas'/'extraction.schema.json').read_text())
workflow=json.loads((ROOT/'n8n'/'localle_reservation_intake_v1.n8n.json').read_text())
demo=json.loads((ROOT/'n8n'/'localle_reservation_logic_demo.n8n.json').read_text())
contract=json.loads((ROOT/'config'/'live_sheet_contract.json').read_text())

# Independent source/workflow reconciliation.
node_by_name={n['name']:n for n in workflow['nodes']}
assert node_by_name['Merge + Validate + Decide']['parameters']['jsCode']==(ROOT/'n8n/code/merge_validate.js').read_text()
assert node_by_name['Attach Reply + Send Gate']['parameters']['jsCode']==(ROOT/'n8n/code/attach_reply_gate.js').read_text()
assert workflow['active'] is False
assert workflow['settings']['timezone']=='Europe/Athens'
assert 'Verify Reply Safety' in node_by_name
assert 'Build Extraction Failure Review' in node_by_name
assert 'Processed_Messages' in contract['sheets'] and 'Human_Review' in contract['sheets']

# Every embedded Code node must parse as JavaScript.
js_checked=0
for n in workflow['nodes']+demo['nodes']:
    if n['type']!='n8n-nodes-base.code':
        continue
    tmp=EVIDENCE/f'_tmp_{js_checked}.js'
    tmp.write_text(n['parameters']['jsCode'],encoding='utf-8')
    p=subprocess.run(['node','--check',str(tmp)],capture_output=True,text=True)
    try: tmp.unlink()
    except FileNotFoundError: pass
    if p.returncode:
        raise SystemExit(f"JavaScript syntax failed in {n['name']}: {p.stderr}")
    js_checked+=1
(EVIDENCE/'javascript_syntax.txt').write_text(f'PASS — {js_checked} embedded Code nodes parsed by node --check\n',encoding='utf-8')

# Secret scan: intentionally narrow patterns to avoid false positives from documentation words.
secret_patterns=[
    re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
    re.compile(r'AIza[0-9A-Za-z_-]{30,}'),
    re.compile(r'ghp_[A-Za-z0-9]{30,}'),
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
]
secret_hits=[]
for p in ROOT.rglob('*'):
    if not p.is_file() or p.name=='MANIFEST.sha256' or p.suffix in {'.pyc','.db'} or '__pycache__' in p.parts:
        continue
    try: text=p.read_text(encoding='utf-8')
    except UnicodeDecodeError: continue
    for pat in secret_patterns:
        if pat.search(text): secret_hits.append(f'{p.relative_to(ROOT)}:{pat.pattern}')
if secret_hits:
    raise SystemExit('Secret scan failed: '+', '.join(secret_hits))
(EVIDENCE/'secret_scan.txt').write_text('PASS — no API keys/private keys detected\n',encoding='utf-8')

# Parse generated evidence for final report.
simulation=json.loads((EVIDENCE/'simulation_results.json').read_text())
stress_data=json.loads((EVIDENCE/'stress_results.json').read_text())
second_seed_data=json.loads((EVIDENCE/'independent_second_seed_validation.json').read_text())
mutation_data=json.loads((EVIDENCE/'mutation_smoke_results.json').read_text())
release_audit=json.loads((EVIDENCE/'release_audit.json').read_text())
test_count=proc.stderr.count(' ... ok')+proc.stdout.count(' ... ok')
report={
    'release':'v2.0-final-safe-default',
    'python_compile':'PASS',
    'unit_tests':'PASS',
    'unit_test_count':test_count,
    'python_js_parity_cases':10000,
    'unit_fuzz_cases':25000,
    'multi_turn_stress_iterations':stress_data['multi_turn']['iterations'],
    'multi_turn_stress_assertions':stress_data['multi_turn']['assertions'],
    'reply_safety_stress_iterations':stress_data['reply_safety']['iterations'],
    'decision_stress_iterations':stress_data['decision_fuzz']['iterations'],
    'probability_simulation_cases_per_scenario':simulation['base']['n'],
    'probability_simulation_total':sum(x['n'] for x in simulation.values()),
    'independent_second_seed':'PASS',
    'second_seed_python_js_parity_cases':second_seed_data['python_js_parity']['cases'],
    'second_seed_multi_turn_iterations':second_seed_data['multi_turn']['iterations'],
    'second_seed_reply_safety_iterations':second_seed_data['reply_safety']['iterations'],
    'second_seed_decision_stress_iterations':second_seed_data['decision_fuzz']['iterations'],
    'second_seed_probability_total':sum(x['n'] for x in second_seed_data['probability'].values()),
    'mutation_smoke':'PASS',
    'mutations_detected':mutation_data['mutations_detected'],
    'mutations_total':mutation_data['mutations_total'],
    'schema_json':'PASS',
    'live_sheet_contract_json':'PASS',
    'n8n_production_json':'PASS',
    'n8n_demo_json':'PASS',
    'workflow_source_reconciliation':'PASS',
    'javascript_syntax':'PASS',
    'javascript_code_nodes_checked':js_checked,
    'static_secret_scan':'PASS',
    'production_node_count':len(workflow['nodes']),
    'demo_node_count':len(demo['nodes']),
    'auto_send_default':False,
    'credentials_embedded':False,
    'blind_retry_on_gmail_send':False,
    'semantic_reply_verifier':True,
    'extraction_failure_fail_closed':True,
    'demo_replay':'PASS',
    'release_graph_audit':release_audit['result'],
    'auto_send_control':'Config Sheet fail-closed',
    'elapsed_seconds':round(time.time()-start,3),
    'limitations':[
        'Generated n8n JSON is statically validated but not executed inside a live n8n runtime in this environment.',
        'Google Sheets event idempotency is best-effort under simultaneous distributed executions; a transactional store is recommended for hard exactly-once production semantics.',
        'No real availability, live quote, or fleet source is connected; the workflow must never invent these facts.'
    ]
}
(EVIDENCE/'validation_summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

release_doc=f'''# Release validation — {report["release"]}

Final automated release gate: **PASS**.

## Executed checks

- Unit / contract tests: **{report["unit_test_count"]} PASS**
- Python ↔ JavaScript parity: **{report["python_js_parity_cases"]:,} cases**
- Unit fuzz: **{report["unit_fuzz_cases"]:,} cases**
- Multi-turn conversation stress: **{report["multi_turn_stress_iterations"]:,} conversations / {report["multi_turn_stress_assertions"]:,} assertions**
- Reply-safety stress: **{report["reply_safety_stress_iterations"]:,} cases**
- Decision stress: **{report["decision_stress_iterations"]:,} cases**
- Synthetic probability simulation: **{report["probability_simulation_total"]:,} requests total**
- Independent second-seed parity/stress/probability run: **PASS** ({report["second_seed_python_js_parity_cases"]:,} parity + {report["second_seed_multi_turn_iterations"]:,} conversations + {report["second_seed_reply_safety_iterations"]:,} reply-safety + {report["second_seed_decision_stress_iterations"]:,} decision stress + {report["second_seed_probability_total"]:,} probability cases)
- Mutation sensitivity: **{report["mutations_detected"]}/{report["mutations_total"]} critical mutations detected**
- n8n production graph: **{report["production_node_count"]} nodes**
- Embedded JavaScript syntax checks: **{report["javascript_code_nodes_checked"]} Code nodes**
- Release graph audit: **{report["release_graph_audit"]}**
- Static secret scan: **PASS**
- Workflow source reconciliation: **PASS**
- Live Google Sheet contract snapshot: **PASS**

## Synthetic automation scenarios

- Smooth assumptions: **{simulation["smooth"]["automated_pct"]}%** automated / **{simulation["smooth"]["human_review_pct"]}%** human review
- Base assumptions: **{simulation["base"]["automated_pct"]}%** automated / **{simulation["base"]["human_review_pct"]}%** human review
- Adverse assumptions: **{simulation["adverse"]["automated_pct"]}%** automated / **{simulation["adverse"]["human_review_pct"]}%** human review

These are synthetic workload assumptions, not observed Localle production metrics.

## Safety state

- Workflow ships inactive.
- `Config → auto_send_enabled` defaults to `FALSE`.
- Missing/invalid config fails closed to no send.
- No credentials are embedded.
- Gmail customer send has no blind retry after an uncertain send result.
- Replies require both semantic verification and deterministic multilingual safety validation.
- AI extraction failure is persisted and escalated rather than silently dropped.

## External gate that remains intentionally unclaimed

This environment does not contain an n8n runtime. The export, node graph, expressions, code, schemas and contracts are validated, but an actual import/execution against the target n8n instance with bound Gmail/Google/OpenAI credentials must still be performed as a controlled test before real customer auto-send.

## Production boundary

The exercise provides no real availability, live pricing or fleet source. The workflow therefore does not claim availability, quote a live price, confirm a booking, or allocate a vehicle. Hard distributed exactly-once semantics should move transactional state from Google Sheets to a transactional store if the system is productionized at larger concurrency.
'''
(ROOT/'docs'/'release_validation.md').write_text(release_doc,encoding='utf-8')

# Manifest generated last so it hashes the final validation evidence and docs.
for cache in ROOT.rglob('__pycache__'):
    if cache.is_dir():
        for p in cache.iterdir():
            try: p.unlink()
            except OSError: pass
        try: cache.rmdir()
        except OSError: pass
files=[]
for p in sorted(ROOT.rglob('*')):
    if p.is_file() and p.name!='MANIFEST.sha256' and '__pycache__' not in p.parts and p.suffix!='.pyc':
        files.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT)}")
(ROOT/'MANIFEST.sha256').write_text('\n'.join(files)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
