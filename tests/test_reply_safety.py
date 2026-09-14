import unittest
from src.reply_safety import deterministic_reply_guard

class ReplySafetyTests(unittest.TestCase):
    def test_normal_reply_passes(self):
        r=deterministic_reply_guard("Thanks for your request. I only need your phone number.", {"strategy":"ACKNOWLEDGE_CONFIRM_ASK_ONLY_MISSING"})
        self.assertTrue(r["safe"], r)

    def test_exact_price_rejected(self):
        r=deterministic_reply_guard("The price is 35 EUR/day.", {})
        self.assertFalse(r["safe"]); self.assertIn("unverified_numeric_price",r["reasons"])

    def test_english_booking_confirmation_rejected(self):
        r=deterministic_reply_guard("Your booking is confirmed.", {})
        self.assertFalse(r["safe"]); self.assertIn("booking_or_availability_claim",r["reasons"])

    def test_german_confirmation_rejected(self):
        r=deterministic_reply_guard("Ihre Buchung ist bestätigt.", {})
        self.assertFalse(r["safe"]); self.assertIn("booking_or_availability_claim",r["reasons"])

    def test_internal_state_rejected(self):
        r=deterministic_reply_guard("Status: HUMAN_REVIEW", {})
        self.assertFalse(r["safe"]); self.assertIn("internal_state_exposed",r["reasons"])

    def test_hold_strategy_must_not_have_reply(self):
        r=deterministic_reply_guard("We received your request.", {"strategy":"HOLD_FOR_HUMAN"})
        self.assertFalse(r["safe"]); self.assertIn("unexpected_reply_for_hold_strategy",r["reasons"])

    def test_greek_confirmation_rejected(self):
        r=deterministic_reply_guard("Η κράτησή σας επιβεβαιώθηκε.", {"strategy":"ACKNOWLEDGE"})
        self.assertFalse(r["safe"])
        self.assertIn("booking_or_availability_claim",r["reasons"])
