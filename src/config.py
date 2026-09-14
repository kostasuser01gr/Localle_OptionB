from __future__ import annotations

DEFAULT_CONFIG = {
    "minimum_confidence": 0.85,
    "auto_send_enabled": False,
    "human_review_holding_reply_enabled": True,
    "business_timezone": "Europe/Athens",
    "company_name": "Meltemi Rentals",
    "verified_business_facts": {
        "reference_small_car_july_eur_per_day": 35,
        "full_insurance_no_excess": True,
        "second_driver_included": True,
        "airport_delivery_pickup_included": True,
        "fuel_policy": "full-to-full",
        "support_24_7": True,
        "no_card_amount_hold": True,
    },
    "vehicle_model_map": {
        "fiat panda": "MINI",
    },
}
