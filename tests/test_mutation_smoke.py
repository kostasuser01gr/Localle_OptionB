import unittest

from tools.mutation_smoke import IGNORED_WORKSPACE_ARTIFACTS


class MutationSmokeWorkspaceTests(unittest.TestCase):
    def test_local_runtime_artifacts_are_not_copied_into_mutation_cases(self):
        self.assertTrue({".git", ".venv", ".n8n-runtime", "*.zip"}.issubset(IGNORED_WORKSPACE_ARTIFACTS))
