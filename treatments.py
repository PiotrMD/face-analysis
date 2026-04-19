TREATMENTS_PL = [
    "Toksyna botulinowa",
    "Filler HA",
    "Stymulatory tkankowe",
    "Fibryna bogatokomórkowa",
    "Laser frakcyjny",
    "Laser naczyniowy",
    "Radiofrekwencja mikroigłowa",
    "Mezoterapia",
    "Peelingi",
]

TREATMENTS_EN = [
    "Botulinum toxin",
    "HA filler",
    "Tissue stimulators",
    "Platelet-rich fibrin",
    "Fractional laser",
    "Vascular laser",
    "Microneedling radiofrequency",
    "Mesotherapy",
    "Peels",
]

AREA_LABELS_PL = {
    "okolica_oczu":  "Okolica oczu",
    "jakosc_skory":  "Jakość skóry",
    "zmarszczki":    "Zmarszczki",
    "napiecie":      "Napięcie twarzy",
    "owal_twarzy":   "Owal twarzy",
    "przebarwienia": "Przebarwienia",
    "naczynka":      "Naczynka / Rumień",
}

AREA_LABELS_EN = {
    "okolica_oczu":  "Eye area",
    "jakosc_skory":  "Skin quality",
    "zmarszczki":    "Wrinkles",
    "napiecie":      "Face firmness",
    "owal_twarzy":   "Face oval",
    "przebarwienia": "Pigmentation",
    "naczynka":      "Vascular / Redness",
}

REQUIRED_AREAS = list(AREA_LABELS_PL.keys())


# ── Treatment rules ────────────────────────────────────────────────────────────
# Each field maps to an ordered list of treatments (first = highest priority).
# These are applied by recommend_treatments() based on the weakest scored areas.

FIELD_TREATMENTS_PL: dict[str, list[str]] = {
    "wrinkles":     ["Toksyna botulinowa", "Stymulatory tkankowe", "Laser frakcyjny"],
    "skin_tension": ["Radiofrekwencja mikroigłowa", "Stymulatory tkankowe", "Filler HA"],
    "skin_quality": ["Mezoterapia", "Peelingi", "Radiofrekwencja mikroigłowa"],
    "pigmentation": ["Peelingi", "Laser frakcyjny"],
    "vessels":      ["Laser naczyniowy"],
    "face_oval":    ["Filler HA", "Toksyna botulinowa"],
    "freshness":    ["Mezoterapia", "Fibryna bogatokomórkowa"],
    "neck":         ["Radiofrekwencja mikroigłowa", "Stymulatory tkankowe"],
    "eye_area":     ["Toksyna botulinowa", "Fibryna bogatokomórkowa"],
    "upper_face":   ["Toksyna botulinowa"],
    "mid_face":     ["Filler HA", "Stymulatory tkankowe"],
    "lower_face":   ["Toksyna botulinowa", "Filler HA"],
    "hair_thinning":["Mezoterapia", "Fibryna bogatokomórkowa"],
    # no treatments for these — not actionable or not visible
    "hairline":     [],
    "symmetry":     [],
    "overall_face": [],
}

FIELD_TREATMENTS_EN: dict[str, list[str]] = {
    "wrinkles":     ["Botulinum toxin", "Tissue stimulators", "Fractional laser"],
    "skin_tension": ["Microneedling radiofrequency", "Tissue stimulators", "HA filler"],
    "skin_quality": ["Mesotherapy", "Peels", "Microneedling radiofrequency"],
    "pigmentation": ["Peels", "Fractional laser"],
    "vessels":      ["Vascular laser"],
    "face_oval":    ["HA filler", "Botulinum toxin"],
    "freshness":    ["Mesotherapy", "Platelet-rich fibrin"],
    "neck":         ["Microneedling radiofrequency", "Tissue stimulators"],
    "eye_area":     ["Botulinum toxin", "Platelet-rich fibrin"],
    "upper_face":   ["Botulinum toxin"],
    "mid_face":     ["HA filler", "Tissue stimulators"],
    "lower_face":   ["Botulinum toxin", "HA filler"],
    "hair_thinning":["Mesotherapy", "Platelet-rich fibrin"],
    "hairline":     [],
    "symmetry":     [],
    "overall_face": [],
}


def recommend_treatments(
    scores: dict,
    lang: str = "pl",
    min_count: int = 3,
    max_count: int = 5,
) -> list:
    """
    Select treatments based on the weakest scored areas.

    Scoring threshold: fields with score <= 7 are candidates.
    Weight: score <= 4 → 3 pts, 5–6 → 2 pts, 7 → 1 pt.
    Treatments accumulate points from all matching weak fields.
    Returns min_count–max_count treatments ranked by total points.

    Fallback: if fewer than min_count treatments are found from the
    threshold, pull from the worst fields regardless of score so the
    result is never empty.
    """
    from prompts import SCORE_FIELDS_OPTIONAL

    field_map = FIELD_TREATMENTS_PL if lang == "pl" else FIELD_TREATMENTS_EN

    # Visible fields: exclude overall_face and optional fields stuck at default 5
    visible = {
        k: v for k, v in scores.items()
        if k != "overall_face"
        and not (k in SCORE_FIELDS_OPTIONAL and v == 5)
    }

    sorted_fields = sorted(visible.items(), key=lambda x: x[1])

    # Accumulate weights from all fields at or below threshold
    weights: dict[str, int] = {}
    for field, score in sorted_fields:
        if score > 7:
            continue
        w = 3 if score <= 4 else 2 if score <= 6 else 1
        for treatment in field_map.get(field, []):
            weights[treatment] = weights.get(treatment, 0) + w

    # Fallback: pull from worst fields until we reach min_count
    if len(weights) < min_count:
        for field, _ in sorted_fields[:5]:
            for treatment in field_map.get(field, []):
                if treatment not in weights:
                    weights[treatment] = 1
            if len(weights) >= min_count:
                break

    ranked = sorted(weights.items(), key=lambda x: -x[1])
    result  = [t for t, _ in ranked[:max_count]]

    print(
        f"[TREATMENTS] lang={lang} weak_fields={[f for f,s in sorted_fields if s<=7]} "
        f"weights={dict(list(weights.items())[:6])} result={result}",
        flush=True,
    )
    return result
