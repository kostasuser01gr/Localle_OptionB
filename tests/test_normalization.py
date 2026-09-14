import unittest
from src.normalization import enrich_extraction, normalize_phone, normalize_vehicle
from tests.fixtures import base_extraction

class NormalizationTests(unittest.TestCase):
    def test_phone_plus(self):
        self.assertEqual(normalize_phone("+44 7700 123 456")["normalized"], "+447700123456")
    def test_phone_00(self):
        self.assertEqual(normalize_phone("0044 7700 123456")["normalized"], "+447700123456")
    def test_bad_phone(self):
        self.assertEqual(normalize_phone("123")["status"], "invalid_length")
    def test_category_alias(self):
        x = normalize_vehicle(base_extraction())
        self.assertEqual(x["category_normalized"], "ECONOMY")
    def test_model_map_only_when_verified(self):
        x = base_extraction(vehicle={"category":None,"transmission":"manual","model_text":"Fiat Panda"})
        v = normalize_vehicle(x, {"fiat panda":"MINI"})
        self.assertEqual(v["category_normalized"], "MINI")
        self.assertEqual(v["normalization_evidence"], "verified_model_map")
    def test_invalid_phone_adds_ambiguity(self):
        x = enrich_extraction(base_extraction(phone="123"))
        self.assertTrue(any(a["code"] == "invalid_phone_format" for a in x["ambiguities"]))

class DateAmbiguityTests(unittest.TestCase):
    def test_ambiguous_pickup_numeric_date_is_flagged(self):
        x = base_extraction(pickup={"date_text":"03/04","date_iso":None,"time_text":None,"location":"Kos Airport"})
        e = enrich_extraction(x)
        self.assertTrue(any(a["code"] == "ambiguous_pickup_numeric_date" for a in e["ambiguities"]))
