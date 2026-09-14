import unittest
from src.engine import build_reply_plan, decide_status
from src.normalization import enrich_extraction
from src.reply_templates import compose_reply
from tests.fixtures import base_extraction

class ReplyTests(unittest.TestCase):
    def _reply(self,lang="en",**kw):
        x=enrich_extraction(base_extraction(language=lang,**kw)); d=decide_status(x); return compose_reply(build_reply_plan(x,d), {"full_insurance_no_excess":True})
    def test_languages_nonempty(self):
        for lang in ["en","el","de","fr","it","es"]: self.assertTrue(self._reply(lang))
    def test_missing_only_asks_missing(self):
        r=self._reply("en",customer_name=None,phone=None); self.assertIn("full name",r); self.assertIn("contact phone number",r); self.assertNotIn("car category",r)
    def test_ready_does_not_confirm(self):
        r=self._reply(); self.assertIn("check availability",r.lower()); self.assertNotIn("your booking is confirmed",r.lower())
    def test_competitor_total_cost(self):
        r=self._reply("en",competitor={"price_mentioned":True,"price_text":"8 EUR/day"}); self.assertIn("final payable total",r)
