import unittest
from pathlib import Path

from tools.mutation_smoke import IGNORED_WORKSPACE_ARTIFACTS

ROOT = Path(__file__).resolve().parents[1]


class MutationSmokeWorkspaceTests(unittest.TestCase):
    def test_local_runtime_artifacts_are_not_copied_into_mutation_cases(self):
        self.assertTrue({".git", ".venv", ".n8n*", ".playwright-cli", "*.zip"}.issubset(IGNORED_WORKSPACE_ARTIFACTS))

    def test_validation_secret_scan_excludes_ignored_local_runtime_state(self):
        validation_source = (ROOT / 'tools' / 'run_validation.py').read_text(encoding='utf-8')
        self.assertIn("any(part.startswith('.n8n') for part in p.parts)", validation_source)
        self.assertIn("'.playwright-cli' in p.parts", validation_source)
