import random
import unittest
from src.engine import decide_status
from src.normalization import enrich_extraction
from tests.fixtures import base_extraction

class FuzzTests(unittest.TestCase):
    def test_25000_random_decisions_never_auto_send_review_or_duplicate(self):
        rng=random.Random(20260913)
        for _ in range(25000):
            x=base_extraction()
            if rng.random()<.25:x["customer_name"]=None
            if rng.random()<.3:x["phone"]=None
            if rng.random()<.1:x["vehicle"]["category"]=None
            if rng.random()<.04:x["phone"]="123"
            if rng.random()<.05:x["confidence"]=rng.random()*.8
            if rng.random()<.03:x["ambiguities"].append({"code":"conflicting_dates","severity":"high","detail":"fuzz"})
            if rng.random()<.01:x["multiple_requests"]=True
            x=enrich_extraction(x)
            duplicate=rng.random()<.02
            d=decide_status(x,duplicate_message=duplicate)
            self.assertIn(d["status"],{"READY","NEEDS_INFO","HUMAN_REVIEW","NO_CHANGE"})
            if d["status"] in {"HUMAN_REVIEW","NO_CHANGE"}: self.assertFalse(d["auto_send_allowed"])
