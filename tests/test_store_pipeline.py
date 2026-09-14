import tempfile
import threading
import unittest
from src.pipeline import process_message
from src.store import SQLiteStore
from tests.fixtures import base_extraction, message

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.NamedTemporaryFile(suffix=".db",delete=False); self.tmp.close(); self.store=SQLiteStore(self.tmp.name)
    def extractor(self, normalized): return base_extraction(customer_name=None,phone=None,email=normalized["from"])
    def test_first_message_needs_info(self):
        r=process_message(message(),self.extractor,self.store); self.assertEqual(r["decision"]["status"],"NEEDS_INFO"); self.assertFalse(r["send_enabled"])
    def test_duplicate_is_exactly_once(self):
        process_message(message(),self.extractor,self.store); r=process_message(message(),self.extractor,self.store); self.assertTrue(r["duplicate"]); self.assertEqual(r["decision"]["status"],"NO_CHANGE")
    def test_auto_reply_not_extracted(self):
        called=[]
        def bad(_): called.append(1); return base_extraction()
        r=process_message(message(headers={"Auto-Submitted":"auto-replied"}),bad,self.store); self.assertEqual(r["decision"]["status"],"NO_CHANGE"); self.assertEqual(called,[])
    def test_followup_updates_same_request(self):
        process_message(message(),self.extractor,self.store)
        def follow(_):
            x=base_extraction(customer_name="John Smith",phone="+447700123456",email=None,pickup={"date_text":None,"date_iso":None,"time_text":None,"location":None},vehicle={"category":None,"transmission":"unspecified","model_text":None}); x["return"]={"date_text":None,"date_iso":None,"time_text":None,"location":None}; return x
        r=process_message(message(message_id="m2",body="John Smith +447700123456"),follow,self.store); self.assertEqual(r["decision"]["status"],"READY"); self.assertEqual(r["row"]["revision"],2)
    def test_concurrent_duplicate_one_commits(self):
        outcomes=[]; lock=threading.Lock()
        def worker():
            local=SQLiteStore(self.tmp.name)
            try: result=process_message(message(),self.extractor,local)
            except Exception as e: result={"error":str(e)}
            with lock: outcomes.append(result)
        threads=[threading.Thread(target=worker) for _ in range(8)]
        for t in threads:t.start()
        for t in threads:t.join()
        committed=sum(1 for x in outcomes if not x.get("duplicate") and "error" not in x)
        duplicates=sum(1 for x in outcomes if x.get("duplicate"))
        self.assertEqual(committed,1); self.assertEqual(duplicates,7)
