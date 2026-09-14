import unittest
from src.email_normalizer import normalize_message
from tests.fixtures import message

class EmailNormalizerTests(unittest.TestCase):
    def test_plain_message(self):
        x = normalize_message(message())
        self.assertEqual(x["disposition"], "PROCESS")
        self.assertIn("small automatic", x["normalized_customer_message"])
    def test_html_message(self):
        x = normalize_message(message(body="", body_html="<p>Hello<br>I need a car</p>"))
        self.assertEqual(x["disposition"], "PROCESS")
        self.assertIn("I need a car", x["normalized_customer_message"])
    def test_quoted_history_removed(self):
        x = normalize_message(message(body="My phone is +44 7700 123456\n\nOn Tue, John wrote:\n> old request"))
        self.assertEqual(x["normalized_customer_message"], "My phone is +44 7700 123456")
    def test_signature_removed(self):
        x = normalize_message(message(body="My phone is +44 7700 123456\nSent from my iPhone\nold noise"))
        self.assertNotIn("old noise", x["normalized_customer_message"])
    def test_auto_submitted_ignored(self):
        x = normalize_message(message(headers={"Auto-Submitted":"auto-replied"}))
        self.assertEqual(x["disposition"], "IGNORE_AUTO")
    def test_bulk_ignored(self):
        x = normalize_message(message(headers={"Precedence":"bulk"}))
        self.assertEqual(x["disposition"], "IGNORE_AUTO")
    def test_bounce_ignored(self):
        x = normalize_message(message(**{"from":"MAILER-DAEMON@example.com"}))
        self.assertEqual(x["disposition"], "IGNORE_BOUNCE")
    def test_empty_ignored(self):
        x = normalize_message(message(body="   "))
        self.assertEqual(x["disposition"], "IGNORE_EMPTY")
