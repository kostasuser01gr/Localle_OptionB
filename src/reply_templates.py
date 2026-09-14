from __future__ import annotations

from typing import Any

FIELD_LABELS = {
    "en": {"customer_name":"full name", "phone":"contact phone number", "pickup.date_text":"pickup date", "return.date_text":"return date", "vehicle.category":"car category"},
    "el": {"customer_name":"ονοματεπώνυμο", "phone":"τηλέφωνο επικοινωνίας", "pickup.date_text":"ημερομηνία παραλαβής", "return.date_text":"ημερομηνία επιστροφής", "vehicle.category":"κατηγορία αυτοκινήτου"},
    "de": {"customer_name":"vollständigen Namen", "phone":"Telefonnummer", "pickup.date_text":"Abholdatum", "return.date_text":"Rückgabedatum", "vehicle.category":"Fahrzeugkategorie"},
    "fr": {"customer_name":"nom complet", "phone":"numéro de téléphone", "pickup.date_text":"date de prise en charge", "return.date_text":"date de retour", "vehicle.category":"catégorie de voiture"},
    "it": {"customer_name":"nome completo", "phone":"numero di telefono", "pickup.date_text":"data di ritiro", "return.date_text":"data di riconsegna", "vehicle.category":"categoria dell'auto"},
    "es": {"customer_name":"nombre completo", "phone":"número de teléfono", "pickup.date_text":"fecha de recogida", "return.date_text":"fecha de devolución", "vehicle.category":"categoría del coche"},
}

OPENERS = {
    "en":"Thanks for your request.", "el":"Ευχαριστούμε για το αίτημά σας.", "de":"Vielen Dank für Ihre Anfrage.",
    "fr":"Merci pour votre demande.", "it":"Grazie per la richiesta.", "es":"Gracias por su solicitud.",
}
HOLDING = {
    "en":"We received your request and a member of our team will review the details shortly.",
    "el":"Λάβαμε το αίτημά σας και ένα μέλος της ομάδας μας θα ελέγξει σύντομα τις λεπτομέρειες.",
    "de":"Wir haben Ihre Anfrage erhalten. Unser Team prüft die Angaben in Kürze.",
    "fr":"Nous avons bien reçu votre demande. Notre équipe vérifiera les détails rapidement.",
    "it":"Abbiamo ricevuto la richiesta. Il nostro team verificherà a breve i dettagli.",
    "es":"Hemos recibido su solicitud. Nuestro equipo revisará los detalles en breve.",
}
NEXT_STEP = {
    "en":"We’ll now check availability and prepare the exact offer before confirming anything.",
    "el":"Θα ελέγξουμε τώρα τη διαθεσιμότητα και θα ετοιμάσουμε την ακριβή προσφορά πριν επιβεβαιωθεί οτιδήποτε.",
    "de":"Wir prüfen nun die Verfügbarkeit und erstellen das genaue Angebot, bevor etwas bestätigt wird.",
    "fr":"Nous allons maintenant vérifier la disponibilité et préparer l’offre exacte avant toute confirmation.",
    "it":"Ora verificheremo la disponibilità e prepareremo l’offerta esatta prima di qualsiasi conferma.",
    "es":"Ahora comprobaremos la disponibilidad y prepararemos la oferta exacta antes de confirmar nada.",
}
TOTAL_COST = {
    "en":"When comparing prices, it’s useful to compare the final payable total, including insurance, excess/deposit, airport fees and additional-driver charges.",
    "el":"Στη σύγκριση τιμών είναι χρήσιμο να συγκρίνεται το τελικό πληρωτέο ποσό, μαζί με ασφάλιση, απαλλαγή/εγγύηση, χρεώσεις αεροδρομίου και επιπλέον οδηγό.",
    "de":"Beim Preisvergleich lohnt sich der Blick auf den tatsächlich zahlbaren Gesamtpreis inklusive Versicherung, Selbstbeteiligung/Kaution, Flughafengebühren und Zusatzfahrer.",
    "fr":"Pour comparer les prix, il est utile de regarder le montant total réellement payable, y compris assurance, franchise/dépôt, frais d’aéroport et conducteur supplémentaire.",
    "it":"Nel confronto dei prezzi è utile considerare il totale effettivo da pagare, inclusi assicurazione, franchigia/deposito, costi aeroportuali e conducente aggiuntivo.",
    "es":"Al comparar precios, conviene comparar el total final a pagar, incluidos seguro, franquicia/depósito, tasas de aeropuerto y conductor adicional.",
}
ASK_PREFIX = {
    "en":"I only need", "el":"Χρειάζομαι μόνο", "de":"Ich benötige nur noch", "fr":"Il me manque seulement", "it":"Mi servono solo", "es":"Solo necesito",
}

def _lang(code: str) -> str:
    primary = (code or "en").split("-")[0].lower()
    return primary if primary in FIELD_LABELS else "en"

def compose_reply(plan: dict[str, Any], verified_facts: dict[str, Any] | None = None) -> str:
    strategy = plan.get("strategy")
    if strategy in {"NO_REPLY", "HOLD_FOR_HUMAN"}:
        return ""
    lang = _lang(str(plan.get("language") or "en"))
    if strategy == "SAFE_HOLDING_REPLY":
        return HOLDING[lang]
    lines = [OPENERS[lang]]
    missing = plan.get("missing_fields") or []
    if strategy == "ACKNOWLEDGE_CONFIRM_ASK_ONLY_MISSING" and missing:
        labels = [FIELD_LABELS[lang].get(x, x) for x in missing]
        if len(labels) == 1:
            joined = labels[0]
        else:
            joined = ", ".join(labels[:-1]) + (" and " if lang == "en" else ", ") + labels[-1]
        suffix = "." if lang != "el" else "."
        lines.append(f"{ASK_PREFIX[lang]} {joined}{suffix}")
    else:
        lines.append(NEXT_STEP[lang])
    if plan.get("include_total_cost_comparison"):
        lines.append(TOTAL_COST[lang])
        facts = verified_facts or {}
        inclusions: list[str] = []
        if facts.get("full_insurance_no_excess"):
            inclusions.append("full insurance with no excess")
        if facts.get("second_driver_included"):
            inclusions.append("second driver")
        if facts.get("airport_delivery_pickup_included"):
            inclusions.append("airport delivery/pickup")
        if facts.get("no_card_amount_hold"):
            inclusions.append("no card amount hold")
        if inclusions and lang == "en":
            lines.append("Our stated offer includes: " + ", ".join(inclusions) + ".")
    return "\n\n".join(lines)
