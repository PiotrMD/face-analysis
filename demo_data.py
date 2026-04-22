DEMO_RESULT = {
    "overall_score": 7,
    "intro": "Twoja skóra jest w dobrej kondycji z kilkoma obszarami, które warto wzmocnić.",
    "strengths": ["Jakość skóry", "Owal twarzy", "Przebarwienia"],
    "concerns":  ["Naczynka / Rumień", "Zmarszczki", "Napięcie skóry"],
    "strengths_items": [
        {"label": "Jakość skóry",  "score": 8, "key": "skin_quality"},
        {"label": "Owal twarzy",   "score": 8, "key": "face_oval"},
        {"label": "Przebarwienia", "score": 8, "key": "pigmentation"},
    ],
    "concerns_items": [
        {"label": "Naczynka / Rumień", "score": 6, "key": "vessels"},
        {"label": "Zmarszczki",        "score": 6, "key": "wrinkles"},
        {"label": "Napięcie skóry",    "score": 6, "key": "skin_tension"},
    ],
    "treatments": [
        "Toksyna botulinowa",
        "Laser naczyniowy",
        "Mezoterapia",
        "Nici liftingujące",
    ],
    "areas": {
        "okolica_oczu":  7,
        "jakosc_skory":  8,
        "zmarszczki":    6,
        "napiecie":      6,
        "owal_twarzy":   8,
        "przebarwienia": 8,
        "naczynka":      6,
    },
    "area_labels": {
        "okolica_oczu":  "Okolica oczu",
        "jakosc_skory":  "Jakość skóry",
        "zmarszczki":    "Zmarszczki",
        "napiecie":      "Napięcie twarzy",
        "owal_twarzy":   "Owal twarzy",
        "przebarwienia": "Przebarwienia",
        "naczynka":      "Naczynka / Rumień",
    },
    "health_note": "Regularne stosowanie filtra SPF 50+ to podstawa ochrony przed fotostarzeniem. Warto również zadbać o odpowiednie nawodnienie skóry od wewnątrz.",
    "lang": "pl",
    # Bio age — scores: skin=8, wr=6, st=6, oval=8, eyes=7, pig=8, ve=6 (no neck)
    # weighted=7.02 → age=33.4 → no corrections → confidence=0.90 → range 31–36
    # user_age=45, bio_mid=33.5, diff=+11.5 ≥ 5 → "wskazuje na młodszy wiek niż metrykalny"
    "bio_age_min":      31,
    "bio_age_max":      36,
    "bio_prefix":       "",
    "bio_confidence":   0.90,
    "bio_factors":      ["jakość skóry", "owal twarzy", "przebarwienia"],
    "bio_factors_type": "positive",
    # User data
    "user_age":    45,
    "user_height": 172,
    "user_weight": 74.0,
    "user_bmi":    25.0,
}
