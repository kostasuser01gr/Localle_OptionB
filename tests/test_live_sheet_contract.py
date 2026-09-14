import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class LiveSheetContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=json.loads((ROOT/'config'/'live_sheet_contract.json').read_text())
        cls.workflow=json.loads((ROOT/'n8n'/'localle_reservation_intake_v1.n8n.json').read_text())

    def test_all_google_sheet_targets_exist_in_live_contract(self):
        allowed=set(self.contract['sheets'])
        targets=set()
        for n in self.workflow['nodes']:
            if n['type']!='n8n-nodes-base.googleSheets':
                continue
            sheet=n['parameters'].get('sheetName',{}).get('value')
            if sheet:
                targets.add(sheet)
        self.assertFalse(targets-allowed, targets-allowed)

    def test_google_sheet_mapping_columns_exist(self):
        for n in self.workflow['nodes']:
            if n['type']!='n8n-nodes-base.googleSheets':
                continue
            sheet=n['parameters'].get('sheetName',{}).get('value')
            if not sheet or sheet not in self.contract['sheets']:
                continue
            allowed=set(self.contract['sheets'][sheet])
            mapping=set(n['parameters'].get('columns',{}).get('value',{}))
            self.assertFalse(mapping-allowed, f"{n['name']} -> {sheet}: {mapping-allowed}")

    def test_required_runtime_tables_are_present(self):
        for name in ('Requests','Processed_Messages','Human_Review','Audit'):
            self.assertIn(name,self.contract['sheets'])

    def test_live_contract_sheet_id_matches_workflow(self):
        expected=self.contract['spreadsheet_id']
        for n in self.workflow['nodes']:
            if n['type']=='n8n-nodes-base.googleSheets':
                self.assertEqual(n['parameters']['documentId']['value'],expected,n['name'])
