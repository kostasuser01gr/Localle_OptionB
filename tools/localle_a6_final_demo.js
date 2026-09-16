#!/usr/bin/env node
'use strict';

// Read-only strict execution inspector for the final A7 demo. It reads only
// Localle's SQLite execution history and never calls Gmail or Google APIs.
const cp = require('child_process');
const path = require('path');
const { parse } = require(path.join(process.cwd(), '.n8n-runtime/node_modules/flatted'));

const db = path.join(process.cwd(), '.n8n-runtime/user/.n8n/database.sqlite');
const subject = 'Localle demo reservation — Test Customer A7';
const sender = 'userco000@gmail.com';
const baseline = Number(process.argv[2] || 0);
const sql = (query) => {
  const raw = cp.execFileSync(
    'sqlite3',
    ['-json', db, query],
    { encoding: 'utf8' }
  ).trim();

  // sqlite3 -json prints an empty string when a SELECT returns zero rows.
  // JSON.parse('') crashes the watcher before the A6 execution exists.
  return raw || '[]';
};
const one = (query) => JSON.parse(sql(query))[0];
const equal = (actual, expected) => actual === expected;
const pass = (ok, label) => console.log(`${ok ? 'PASS' : 'FAIL'} ${label}`);

function latestOutput(runData, name) {
  const attempts = runData[name] || [];
  for (let i = attempts.length - 1; i >= 0; i -= 1) {
    const output = attempts[i]?.data?.main?.[0]?.[0]?.json;
    if (output) return output;
  }
  return {};
}

function inspect(executionId) {
  const raw = cp.execFileSync('sqlite3', [db, `SELECT data FROM execution_data WHERE executionId=${Number(executionId)}`], { encoding: 'utf8' });
  const data = parse(raw.trim());
  const run = data.resultData?.runData || {};
  const inbound = latestOutput(run, 'Normalize Inbound');
  const duplicate = latestOutput(run, 'Duplicate / Recovery Gate');
  const decision = latestOutput(run, 'Merge + Validate + Decide');
  const request = latestOutput(run, 'UPSERT Request');
  const renderer = latestOutput(run, 'Render Customer Reply');
  const verifier = latestOutput(run, 'Verify Reply Safety');
  const gate = latestOutput(run, 'Attach Reply + Send Gate');
  const ledger = latestOutput(run, 'Persist Event Ledger');
  const verifierVerdict = gate.verifier_verdict || {};
  const noHumanReview = !(run['UPSERT Human Review'] || []).length;
  const checks = [
    [inbound.subject === subject && String(inbound.from).includes(sender), 'exact Gmail message'],
    [Boolean(inbound.normalized_customer_message), 'normalization'],
    [duplicate.is_duplicate === false, 'is_duplicate=false'],
    [decision.status === 'READY', 'status=READY'],
    [Array.isArray(decision.missing_fields) && decision.missing_fields.length === 0, 'missing_fields=[]'],
    [decision.vehicle_category_normalized === 'ECONOMY', 'ECONOMY'],
    [decision.transmission === 'automatic', 'automatic'],
    [Boolean(run['UPSERT Request']?.length), 'Request UPSERT'],
    [request.customer_name === 'Test Customer A7' && request.phone_raw === '+30 690 000 0005', 'real Request values'],
    [request.phone_raw === '+30 690 000 0005' && request.phone_raw !== '#ERROR!', 'phone_raw payload not #ERROR'],
    [Boolean(String(renderer.body ?? renderer.text ?? renderer.output ?? renderer.response ?? '').trim()), 'reply renderer non-empty'],
    [gate.reply_body.includes('Localle') && !/\[Your Name\]|\[Your Company Name\]/i.test(gate.reply_body), 'Localle signature with no placeholders'],
    [!/\b(?:deposit|credit[- ]?card|card amount|card hold|payment|insurance|fuel(?:\s+policy)?|cancell?ation|availability)\b/i.test(gate.reply_body), 'no unsupported policy claims'],
    [!verifier.error && !gate.verifier_error, 'verifier no error'],
    [gate.verifier_valid === true && verifierVerdict.safe === true && verifierVerdict.language_match === true && verifierVerdict.claims_availability === false && verifierVerdict.claims_booking_confirmed === false && verifierVerdict.quotes_unverified_price === false && verifierVerdict.assigns_vehicle === false && verifierVerdict.attacks_competitor === false && verifierVerdict.exposes_internal === false && verifierVerdict.asks_only_allowed_fields === true && verifierVerdict.facts_match_plan === true, 'structured verifier safe=true'],
    [gate.reply_safe === true, 'reply_safe=true'],
    [Array.isArray(gate.reply_safety_reasons) && gate.reply_safety_reasons.length === 0, 'no safety reasons'],
    [gate.review_required === false, 'review_required=false'],
    [noHumanReview, 'no Human Review branch'],
    [gate.send_now === false, 'send_now=false'],
    [gate.delivery_state === 'DRAFT_ONLY', 'DRAFT_ONLY'],
    [Boolean(run['Persist Event Ledger']?.length) && (ledger.result_status === 'READY' || gate.status === 'READY'), 'event ledger READY'],
    [gate.send_now === false, 'reply_sent=false'],
    [Boolean(run['Audit Draft']?.length), 'Audit Draft path'],
  ];
  for (const [ok, label] of checks) pass(ok, label);
  return checks.every(([ok]) => ok);
}

const workflow = one("SELECT active,triggerCount,nodes FROM workflow_entity WHERE id='LOCALLEOPTB2026A'");
const nodes = JSON.parse(workflow.nodes);
const triggerCount = nodes.filter((node) => node.type === 'n8n-nodes-base.gmailTrigger').length;
pass(workflow.active === 1, 'workflow active');
pass(workflow.triggerCount === 1 && triggerCount === 1, 'exactly one active trigger');
pass(nodes.length === 48, 'expected node count');

let found;
for (let attempt = 0; attempt < 720; attempt += 1) {
  const rows = JSON.parse(sql(`SELECT e.id,d.data FROM execution_entity e JOIN execution_data d ON d.executionId=e.id WHERE e.workflowId='LOCALLEOPTB2026A' AND e.id>${baseline} AND e.status='success' ORDER BY e.id DESC LIMIT 20`));
  found = rows.find((row) => {
    try {
      const run = parse(row.data).resultData?.runData || {};
      const inbound = latestOutput(run, 'Normalize Inbound');
      return inbound.subject === subject && String(inbound.from).includes(sender);
    } catch (_) { return false; }
  });
  if (found) break;
  process.stdout.write(attempt % 12 === 0 ? 'Waiting for A7 Gmail execution…\n' : '.');
  cp.execFileSync('sleep', ['5']);
}

if (!found) {
  console.log('\nLOCALLE A7 — FIX / REVIEW STILL REQUIRED');
  process.exitCode = 1;
} else {
  console.log(`\nInspecting execution ${found.id}`);
  const strict = inspect(found.id);
  if (!strict) {
    console.log('LOCALLE A7 — FIX / REVIEW STILL REQUIRED');
    process.exitCode = 1;
  } else {
    console.log('VISUAL SHEET CHECK: Requests is open. Confirm phone_raw visibly reads +30 690 000 0005 (no apostrophe and no #ERROR!), then type VERIFIED.');
    process.stdin.setEncoding('utf8');
    process.stdin.once('data', (answer) => {
      if (answer.trim() === 'VERIFIED') console.log('LOCALLE A7 LIVE E2E — STRICT PASS');
      else { console.log('LOCALLE A7 — FIX / REVIEW STILL REQUIRED'); process.exitCode = 1; }
    });
  }
}
