import tempfile
import unittest
from src.pipeline import process_message
from src.store import SQLiteStore
from tests.fixtures import base_extraction, message

LANGS=["en","el","de","fr","it","es"]

class SequenceMatrixTests(unittest.TestCase):
    def test_six_language_missing_then_followup_sequences(self):
        for idx,lang in enumerate(LANGS):
            with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
                s=SQLiteStore(tmp.name); tid=f"t-{lang}"
                def first(_): return base_extraction(language=lang,customer_name=None,phone=None)
                r1=process_message(message(message_id=f"m-{idx}-1",thread_id=tid),first,s)
                self.assertEqual(r1["decision"]["status"],"NEEDS_INFO")
                self.assertTrue(r1["reply"])
                def second(_):
                    x=base_extraction(language=lang,customer_name="Test User",phone="+306900000000",email=None,pickup={"date_text":None,"date_iso":None,"time_text":None,"location":None},vehicle={"category":None,"transmission":"unspecified","model_text":None}); x["return"]={"date_text":None,"date_iso":None,"time_text":None,"location":None}; return x
                r2=process_message(message(message_id=f"m-{idx}-2",thread_id=tid,body="follow up"),second,s)
                self.assertEqual(r2["decision"]["status"],"READY")
                self.assertEqual(r2["row"]["revision"],2)
