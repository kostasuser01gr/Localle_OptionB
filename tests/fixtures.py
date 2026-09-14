def base_extraction(**overrides):
    data = {
        "language": "en", "customer_name": "John Smith", "phone": "+44 7700 123456", "email": "john@example.com",
        "pickup": {"date_text": "18 July", "date_iso": None, "time_text": "10:00", "location": "Kos Airport"},
        "return": {"date_text": "23 July", "date_iso": None, "time_text": None, "location": None},
        "vehicle": {"category": "small", "transmission": "automatic", "model_text": None},
        "competitor": {"price_mentioned": False, "price_text": None}, "multiple_requests": False, "message_intent": "new_request", "ambiguities": [], "confidence": 0.97,
    }
    data.update(overrides)
    return data

def message(message_id="m1", thread_id="t1", body="Hi, I need a small automatic car from 18 July until 23 July. We arrive at Kos airport around 10am.", **kw):
    data = {"message_id":message_id, "thread_id":thread_id, "from":"guest@example.com", "to":"rentals@example.com", "subject":"Car rental", "body_text":body, "body_html":"", "received_at":"2026-09-13T16:00:00Z", "headers":{}}
    data.update(kw)
    return data
