import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / 'n8n' / 'code' / 'attach_reply_gate.js'

VALID = {
    'safe': True,
    'language_match': True,
    'claims_availability': False,
    'claims_booking_confirmed': False,
    'quotes_unverified_price': False,
    'assigns_vehicle': False,
    'attacks_competitor': False,
    'exposes_internal': False,
    'asks_only_allowed_fields': True,
    'facts_match_plan': True,
    'reason': 'Reply accurately records the approved request without commitments.',
}


def run_gate(*, reply, verifier, auto_send=False):
    harness = r'''
const fs=require('fs'), vm=require('vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const core={status:'READY',subject:'Reservation enquiry',from:'guest@example.com',reply_strategy:'READY_REPLY',next_action:'review_request',runtime:{auto_send_enabled:input.auto_send}};
const context={Buffer,$json:input.verifier,$:(name)=>({item:{json:name==='Merge + Validate + Decide'?core:{body:input.reply}}})};
const source=`(function(){${fs.readFileSync(input.gate,'utf8')}\n})()`;
process.stdout.write(JSON.stringify(vm.runInNewContext(source,context)));
'''
    p = subprocess.run(
        ['node', '-e', harness], input=json.dumps({
            'gate': str(GATE), 'reply': reply, 'verifier': verifier,
            'auto_send': auto_send,
        }), text=True, capture_output=True, check=True,
    )
    return json.loads(p.stdout)[0]['json']


class ReplyGateContractTests(unittest.TestCase):
    def test_renderer_body_is_verified_and_valid_json_can_draft(self):
        result = run_gate(
            reply='Dear Test Customer A6,\n\nWe have received the following details.\n\nBest regards,\nLocalle',
            verifier={'body': json.dumps(VALID)},
        )
        self.assertTrue(result['verifier_valid'])
        self.assertTrue(result['reply_safe'])
        self.assertEqual(result['reply_safety_reasons'], [])
        self.assertFalse(result['review_required'])
        self.assertFalse(result['send_now'])
        self.assertEqual(result['delivery_state'], 'DRAFT_ONLY')

    def test_malformed_verifier_output_fails_closed(self):
        result = run_gate(reply='Received.', verifier={'body': '{not json'})
        self.assertFalse(result['verifier_valid'])
        self.assertFalse(result['reply_safe'])
        self.assertTrue(result['review_required'])
        self.assertEqual(result['delivery_state'], 'HELD_REPLY_SAFETY')

    def test_unsafe_verifier_json_fails_closed(self):
        unsafe = dict(VALID, safe=False, claims_booking_confirmed=True)
        result = run_gate(reply='Received.', verifier={'body': json.dumps(unsafe)})
        self.assertTrue(result['verifier_valid'])
        self.assertFalse(result['reply_safe'])
        self.assertIn('semantic_verifier_rejected', result['reply_safety_reasons'])

    def test_deterministic_guard_rejects_confirmation_even_if_model_is_wrong(self):
        result = run_gate(
            reply='Your reservation is confirmed and availability is guaranteed.',
            verifier={'body': json.dumps(VALID)},
        )
        self.assertFalse(result['reply_safe'])
        self.assertIn('booking_or_availability_claim', result['reply_safety_reasons'])

    def test_auto_send_never_bypasses_safety(self):
        result = run_gate(reply='Received.', verifier={'body': '{not json'}, auto_send=True)
        self.assertFalse(result['send_now'])
