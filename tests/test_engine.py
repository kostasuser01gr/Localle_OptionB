import unittest
from src.engine import build_reply_plan, decide_status, merge_extractions
from src.normalization import enrich_extraction
from tests.fixtures import base_extraction

class EngineTests(unittest.TestCase):
    def ready(self, **kw): return enrich_extraction(base_extraction(**kw))
    def test_complete_ready(self): self.assertEqual(decide_status(self.ready())["status"], "READY")
    def test_missing_name_phone(self):
        d=decide_status(self.ready(customer_name=None,phone=None)); self.assertEqual(d["status"],"NEEDS_INFO"); self.assertEqual(d["missing_fields"],["customer_name","phone"])
    def test_bad_phone_needs_info(self):
        d=decide_status(self.ready(phone="123")); self.assertEqual(d["status"],"NEEDS_INFO"); self.assertIn("phone",d["missing_fields"])
    def test_low_conf_review(self): self.assertEqual(decide_status(self.ready(confidence=.2))["status"],"HUMAN_REVIEW")
    def test_multiple_review(self): self.assertEqual(decide_status(self.ready(multiple_requests=True))["status"],"HUMAN_REVIEW")
    def test_return_before_pickup(self):
        x=self.ready(pickup={"date_text":"12 Aug 2026","date_iso":"2026-08-12","time_text":None,"location":None})
        x["return"]={"date_text":"9 Aug 2026","date_iso":"2026-08-09","time_text":None,"location":None}
        self.assertEqual(decide_status(x)["status"],"HUMAN_REVIEW")
    def test_non_customer_event_no_change(self): self.assertEqual(decide_status({},inbound_disposition="IGNORE_AUTO")["status"],"NO_CHANGE")
    def test_duplicate_no_change(self): self.assertEqual(decide_status({},duplicate_message=True)["status"],"NO_CHANGE")
    def test_unspecified_followup_neutral(self):
        first=self.ready(); follow=self.ready(customer_name=None,phone=None,email=None,pickup={"date_text":None,"date_iso":None,"time_text":None,"location":None},vehicle={"category":None,"category_normalized":None,"transmission":"unspecified","model_text":None})
        follow["return"]={"date_text":None,"date_iso":None,"time_text":None,"location":None}
        merged,conf=merge_extractions(first,follow); self.assertEqual(conf,[]); self.assertEqual(merged["vehicle"]["transmission"],"automatic")
    def test_low_confidence_is_sticky_across_unrelated_followup(self):
        first=self.ready(customer_name=None,phone=None,confidence=.70)
        follow=self.ready(customer_name="John Smith",phone="+447700123456",confidence=.99,pickup={"date_text":None,"date_iso":None,"time_text":None,"location":None},vehicle={"category":None,"category_normalized":None,"transmission":"unspecified","model_text":None})
        follow["return"]={"date_text":None,"date_iso":None,"time_text":None,"location":None}
        merged,_=merge_extractions(first,follow)
        self.assertEqual(merged["confidence"],.70)
        self.assertEqual(decide_status(merged)["status"],"HUMAN_REVIEW")

    def test_explicit_correction_updates_operational_field(self):
        first=self.ready(pickup={"date_text":"18 July","date_iso":None,"time_text":"10:00","location":"Kos Airport"})
        follow=self.ready(message_intent="correction",customer_name=None,phone=None,email=None,pickup={"date_text":None,"date_iso":None,"time_text":"11:00","location":None},vehicle={"category":None,"category_normalized":None,"transmission":"unspecified","model_text":None})
        follow["return"]={"date_text":None,"date_iso":None,"time_text":None,"location":None}
        merged,conf=merge_extractions(first,follow)
        self.assertEqual(conf,[])
        self.assertEqual(merged["pickup"]["time_text"],"11:00")
        self.assertIn("pickup.time_text", merged["_applied_corrections"])

    def test_language_switch_is_not_conflict(self):
        first=self.ready(language="de")
        follow=self.ready(language="en",customer_name=None,phone=None,email=None,pickup={"date_text":None,"date_iso":None,"time_text":None,"location":None},vehicle={"category":None,"category_normalized":None,"transmission":"unspecified","model_text":None})
        follow["return"]={"date_text":None,"date_iso":None,"time_text":None,"location":None}
        merged,conf=merge_extractions(first,follow)
        self.assertEqual(conf,[])
        self.assertEqual(merged["language"],"en")

    def test_unresolved_ambiguous_date_survives_unrelated_followup(self):
        first=enrich_extraction(base_extraction(customer_name=None,phone=None,pickup={"date_text":"03/04","date_iso":None,"time_text":None,"location":"Kos Airport"}))
        follow=self.ready(customer_name="John Smith",phone="+447700123456",email=None,pickup={"date_text":None,"date_iso":None,"time_text":None,"location":None},vehicle={"category":None,"category_normalized":None,"transmission":"unspecified","model_text":None})
        follow["return"]={"date_text":None,"date_iso":None,"time_text":None,"location":None}
        merged,_=merge_extractions(first,follow)
        self.assertIn("ambiguous_pickup_numeric_date", {a["code"] for a in merged["ambiguities"]})
        self.assertEqual(decide_status(merged)["status"],"NEEDS_INFO")

    def test_ambiguous_date_clears_when_customer_clarifies(self):
        first=enrich_extraction(base_extraction(customer_name=None,phone=None,pickup={"date_text":"03/04","date_iso":None,"time_text":None,"location":"Kos Airport"}))
        follow=self.ready(message_intent="correction",customer_name="John Smith",phone="+447700123456",email=None,pickup={"date_text":"3 April 2027","date_iso":"2027-04-03","time_text":None,"location":None},vehicle={"category":None,"category_normalized":None,"transmission":"unspecified","model_text":None})
        follow["return"]={"date_text":None,"date_iso":None,"time_text":None,"location":None}
        merged,_=merge_extractions(first,follow)
        self.assertNotIn("ambiguous_pickup_numeric_date", {a["code"] for a in merged["ambiguities"]})
    def test_conflict_review(self):
        merged,conf=merge_extractions(self.ready(customer_name="John"),self.ready(customer_name="Jane")); self.assertIn("customer_name",conf); self.assertEqual(decide_status(merged)["status"],"HUMAN_REVIEW")
    def test_competitor_plan(self):
        x=self.ready(competitor={"price_mentioned":True,"price_text":"8 EUR/day"}); d=decide_status(x); p=build_reply_plan(x,d); self.assertTrue(p["include_total_cost_comparison"]); self.assertIn("availability_confirmed",p["forbidden_claims"])
    def test_review_holding_plan(self):
        x=self.ready(confidence=.3); p=build_reply_plan(x,decide_status(x),holding_reply_enabled=True); self.assertEqual(p["strategy"],"SAFE_HOLDING_REPLY")

class AmbiguousDateDecisionTests(unittest.TestCase):
    def test_ambiguous_numeric_pickup_requests_clarification(self):
        x=enrich_extraction(base_extraction(pickup={"date_text":"03/04","date_iso":None,"time_text":None,"location":"Kos Airport"}))
        d=decide_status(x)
        self.assertEqual(d["status"],"NEEDS_INFO")
        self.assertIn("pickup.date_text",d["missing_fields"])
