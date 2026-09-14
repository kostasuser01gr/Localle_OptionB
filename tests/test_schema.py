import json
import unittest
from pathlib import Path
import jsonschema
from tests.fixtures import base_extraction

ROOT=Path(__file__).resolve().parents[1]

class SchemaTests(unittest.TestCase):
    def test_fixture_validates_against_extraction_schema(self):
        schema=json.loads((ROOT/'schemas'/'extraction.schema.json').read_text())
        jsonschema.validate(base_extraction(),schema)

    def test_schema_has_no_refs_for_n8n_parser_compatibility(self):
        raw=(ROOT/'schemas'/'extraction.schema.json').read_text()
        self.assertNotIn('"$ref"',raw)
