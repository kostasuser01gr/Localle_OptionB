import json, re, subprocess, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WF=ROOT/'n8n'/'localle_reservation_intake_v1.n8n.json'

class N8nContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w=json.loads(WF.read_text())
        cls.nodes={n['name']:n for n in cls.w['nodes']}

    def test_safe_default_and_inactive(self):
        self.assertFalse(self.w.get('active'))
        code=self.nodes['Normalize Inbound']['parameters']['jsCode']
        self.assertIn('auto_send_enabled:false',code.replace(' ',''))

    def test_current_node_versions(self):
        self.assertEqual(self.nodes['Gmail Trigger']['typeVersion'],1.4)
        self.assertEqual(self.nodes['Reply in Same Gmail Thread']['typeVersion'],2.2)
        self.assertEqual(self.nodes['UPSERT Request']['typeVersion'],4.7)
        self.assertEqual(self.nodes['Extract Reservation']['typeVersion'],1.9)
        self.assertEqual(self.nodes['Extraction Model']['typeVersion'],1.3)
        self.assertEqual(self.nodes['Strict Extraction Schema']['typeVersion'],1.3)

    def test_trigger_reads_full_body_and_unread_only(self):
        p=self.nodes['Gmail Trigger']['parameters']
        self.assertFalse(p['simple'])
        self.assertEqual(p['filters']['readStatus'],'unread')
        self.assertIn('in:inbox',p['filters']['q'])

    def test_ai_extractor_has_no_tools(self):
        c=self.w['connections']
        self.assertIn('ai_languageModel',c['Extraction Model'])
        self.assertIn('ai_outputParser',c['Strict Extraction Schema'])
        all_types=[]
        for src, groups in c.items():
            all_types.extend(groups.keys())
        self.assertNotIn('ai_tool',all_types)

    def test_business_entity_and_event_matching_keys_are_locked(self):
        self.assertEqual(self.nodes['UPSERT Request']['parameters']['columns']['matchingColumns'], ['thread_id'])
        self.assertEqual(self.nodes['Persist Event Ledger']['parameters']['columns']['matchingColumns'], ['message_id'])
        self.assertEqual(self.nodes['Confirm Reply Sent in Ledger']['parameters']['columns']['matchingColumns'], ['message_id'])
        self.assertEqual(self.nodes['UPSERT Human Review']['parameters']['columns']['matchingColumns'], ['request_id'])
        req_lookup=self.nodes['Lookup Request by Thread']['parameters']['filtersUI']['values'][0]
        msg_lookup=self.nodes['Lookup Processed Message']['parameters']['filtersUI']['values'][0]
        self.assertEqual(req_lookup['lookupColumn'], 'thread_id')
        self.assertEqual(msg_lookup['lookupColumn'], 'message_id')

    def test_request_and_event_are_persisted_before_reply_send(self):
        # Static path invariants: no direct edge can bypass the persist gates.
        c=self.w['connections']
        self.assertEqual(c['Merge + Validate + Decide']['main'][0][0]['node'],'UPSERT Request')
        self.assertEqual(c['Attach Reply + Send Gate']['main'][0][0]['node'],'Persist Event Ledger')
        send_parents=[]
        for src,groups in c.items():
            for branch in groups.get('main',[]):
                for edge in branch:
                    if edge['node']=='Reply in Same Gmail Thread': send_parents.append(src)
        self.assertEqual(send_parents,['AUTO SEND enabled + safe?'])

    def test_send_failure_routes_to_human_review_not_blind_retry(self):
        n=self.nodes['Reply in Same Gmail Thread']
        self.assertEqual(n.get('onError'),'continueErrorOutput')
        self.assertFalse(n.get('retryOnFail',False))
        error_branch=self.w['connections']['Reply in Same Gmail Thread']['main'][1]
        self.assertEqual(error_branch[0]['node'],'Build Send-Uncertain Review')

    def test_credentials_are_not_embedded(self):
        for n in self.w['nodes']:
            self.assertNotIn('credentials',n,f"credential material should not ship in {n['name']}")

    def test_all_n8n_expression_node_references_exist(self):
        names=set(self.nodes)
        raw=WF.read_text()
        refs=set(re.findall(r"\$\('([^']+)'\)",raw))
        self.assertFalse(refs-names,refs-names)

    def test_all_code_nodes_are_javascript_syntax_valid(self):
        for n in self.w['nodes']:
            if n['type']!='n8n-nodes-base.code': continue
            with tempfile.NamedTemporaryFile('w',suffix='.js',delete=False) as f:
                f.write(n['parameters']['jsCode']); path=f.name
            p=subprocess.run(['node','--check',path],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,f"{n['name']}: {p.stderr}")

    def test_reply_node_is_same_thread_reply_not_new_send(self):
        p=self.nodes['Reply in Same Gmail Thread']['parameters']
        self.assertEqual(p['operation'],'reply')
        self.assertEqual(p['messageId'],"={{ $('Attach Reply + Send Gate').item.json.message_id }}")
        self.assertFalse(p['options']['appendAttribution'])
        self.assertTrue(p['options']['replyToSenderOnly'])

class N8nDefenseInDepthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w=json.loads(WF.read_text())
        cls.nodes={n['name']:n for n in cls.w['nodes']}

    def test_reply_has_independent_semantic_verifier(self):
        self.assertIn('Verify Reply Safety',self.nodes)
        self.assertIn('Reply Safety Model',self.nodes)
        self.assertIn('Reply Safety Schema',self.nodes)
        self.assertIn('ai_languageModel',self.w['connections']['Reply Safety Model'])
        self.assertIn('ai_outputParser',self.w['connections']['Reply Safety Schema'])
        render=self.w['connections']['Render Customer Reply']['main']
        self.assertEqual(render[0][0]['node'],'Verify Reply Safety')
        self.assertEqual(render[1][0]['node'],'Verify Reply Safety')
        verifier=self.w['connections']['Verify Reply Safety']['main']
        self.assertEqual(verifier[0][0]['node'],'Attach Reply + Send Gate')
        self.assertEqual(verifier[1][0]['node'],'Attach Reply + Send Gate')

    def test_reply_gate_is_multilingual_and_fail_closed(self):
        code=self.nodes['Attach Reply + Send Gate']['parameters']['jsCode']
        for token in ('buchung','réservation','prenotazione','reserva','κράτησ'):
            self.assertIn(token,code)
        self.assertIn('semantic_verifier_rejected',code)
        self.assertIn('review_required',code)

    def test_human_review_includes_safety_failures_not_only_business_state(self):
        cond=self.nodes['Needs Human Review?']['parameters']['conditions']['conditions'][0]
        self.assertIn('review_required',cond['leftValue'])
        self.assertEqual(cond['operator']['type'],'boolean')

    def test_extraction_failure_is_bounded_and_fail_closed(self):
        extract=self.nodes['Extract Reservation']
        self.assertTrue(extract.get('retryOnFail'))
        self.assertEqual(extract.get('maxTries'),3)
        self.assertEqual(extract.get('onError'),'continueErrorOutput')
        branches=self.w['connections']['Extract Reservation']['main']
        self.assertEqual(branches[1][0]['node'],'Build Extraction Failure Review')
        self.assertIn('Persist Extraction Failure Ledger',self.nodes)
        self.assertIn('UPSERT Extraction Failure Review',self.nodes)

    def test_only_gmail_send_node_can_emit_customer_reply_and_has_no_retry(self):
        send_nodes=[]
        for n in self.w['nodes']:
            if n['type']=='n8n-nodes-base.gmail' and n['parameters'].get('operation') in {'send','reply'}:
                send_nodes.append(n)
        self.assertEqual([n['name'] for n in send_nodes],['Reply in Same Gmail Thread'])
        self.assertFalse(send_nodes[0].get('retryOnFail',False))

    def test_auto_send_gate_depends_on_post_verification_send_now(self):
        cond=self.nodes['AUTO SEND enabled + safe?']['parameters']['conditions']['conditions'][0]
        self.assertIn('Attach Reply + Send Gate',cond['leftValue'])
        self.assertIn('send_now',cond['leftValue'])

class RuntimeConfigGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w=json.loads(WF.read_text())
        cls.nodes={n['name']:n for n in cls.w['nodes']}

    def test_auto_send_is_loaded_from_config_sheet_fail_closed(self):
        self.assertIn('Lookup AUTO SEND Config',self.nodes)
        self.assertIn('Apply Runtime Config',self.nodes)
        lookup=self.nodes['Lookup AUTO SEND Config']
        self.assertEqual(lookup['parameters']['sheetName']['value'],'Config')
        vals=lookup['parameters']['filtersUI']['values']
        self.assertEqual(vals[0]['lookupColumn'],'key')
        self.assertEqual(vals[0]['lookupValue'],'auto_send_enabled')
        self.assertTrue(lookup.get('alwaysOutputData'))
        code=self.nodes['Apply Runtime Config']['parameters']['jsCode']
        self.assertIn('auto_send_enabled:enabled',code)
        self.assertIn("String(raw??'')",code)

    def test_config_gate_is_on_the_only_normal_inbound_path(self):
        c=self.w['connections']
        self.assertEqual(c['Normalize Inbound']['main'][0][0]['node'],'Lookup AUTO SEND Config')
        self.assertEqual(c['Lookup AUTO SEND Config']['main'][0][0]['node'],'Apply Runtime Config')
        self.assertEqual(c['Apply Runtime Config']['main'][0][0]['node'],'Should Process?')
        merge=self.nodes['Merge + Validate + Decide']['parameters']['jsCode']
        self.assertIn("$('Apply Runtime Config').item.json",merge)
