import unittest

from tools.demo_replay import x_ambiguous, x_competitor, x_german_complete


class DemoReplayFixtureTests(unittest.TestCase):
    def test_multilingual_demo_fixtures_have_their_intended_return_dates(self):
        self.assertEqual(x_german_complete(None)["return"]["date_text"], "10 August")
        self.assertEqual(x_competitor(None)["return"]["date_text"], "7 September")
        self.assertEqual(x_ambiguous(None)["return"]["date_text"], "08/04")
