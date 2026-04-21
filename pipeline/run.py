"""
Pipeline orchestrator — runs Stage 1 + Stage 2, assembles the final result dict.

Public API:
    analyze(file_paths_dict, openai_client, model, lang) -> dict
"""

from __future__ import annotations
from typing import Dict

from pipeline import stage1_validate, stage2_score
from prompts import SCORE_FIELD_LABELS_PL, SCORE_FIELD_LABELS_EN
from treatments import AREA_LABELS_PL, AREA_LABELS_EN, recommend_treatments


# Maps 16-field keys → 7 template area keys (score bars)
_FIELD_TO_AREA = {
    "eye_area":     "okolica_oczu",
    "skin_quality": "jakosc_skory",
    "wrinkles":     "zmarszczki",
    "skin_tension": "napiecie",
    "face_oval":    "owal_twarzy",
    "pigmentation": "przebarwienia",
    "vessels":      "naczynka",
}

# ── Bio age model ─────────────────────────────────────────────────────────────

# Weights when neck IS visible (sum = 1.0)
_BIO_WEIGHTS_NECK = {
    "skin_quality": 0.20,
    "wrinkles":     0.18,
    "skin_tension": 0.16,
    "face_oval":    0.14,
    "eye_area":     0.10,
    "pigmentation": 0.07,
    "vessels":      0.05,
    "neck":         0.10,
}
# Weights when neck NOT visible — rescaled so remaining 7 fields sum to 1.0
_NO_NECK_BASE_SUM = 0.90
_BIO_WEIGHTS_NO_NECK = {
    k: v / _NO_NECK_BASE_SUM
    for k, v in _BIO_WEIGHTS_NECK.items()
    if k != "neck"
}

_BIO_FACTOR_LABELS_PL = {
    "skin_quality": "jakość skóry",
    "wrinkles":     "zmarszczki",
    "skin_tension": "napięcie skóry",
    "face_oval":    "owal twarzy",
    "eye_area":     "okolica oczu",
    "pigmentation": "przebarwienia",
    "vessels":      "naczynka",
    "neck":         "szyja",
}
_BIO_FACTOR_LABELS_EN = {
    "skin_quality": "skin quality",
    "wrinkles":     "wrinkles",
    "skin_tension": "skin firmness",
    "face_oval":    "face oval",
    "eye_area":     "eye area",
    "pigmentation": "pigmentation",
    "vessels":      "vascular",
    "neck":         "neck",
}


def _calc_confidence(image_quality: dict) -> float:
    """
    Confidence based on photo quality only — NOT score spread.
    Returns float in [0.30, 0.90].
    """
    score = 1.0

    sharpness = image_quality.get("sharpness", "medium")
    lighting  = image_quality.get("lighting",  "adequate")
    face_full = image_quality.get("face_fully_visible", True)

    if sharpness == "low":      score -= 0.30
    elif sharpness == "medium": score -= 0.12

    if lighting == "poor":      score -= 0.25
    elif lighting == "adequate": score -= 0.10

    if not face_full:           score -= 0.20

    return max(0.30, min(0.90, score))


def _calc_bio_age(scores: dict, image_quality: dict, lang: str) -> dict:
    """
    Deterministic bio age model.
    Returns dict with bio_age_min, bio_age_max, bio_prefix,
    bio_confidence, bio_factors, bio_factors_type.
    """
    neck_visible = image_quality.get("neck_visible", False)
    weights = _BIO_WEIGHTS_NECK if neck_visible else _BIO_WEIGHTS_NO_NECK

    # Weighted composite score
    weighted = sum(scores.get(f, 5) * w for f, w in weights.items())

    # Base age from formula
    age_base = 65.0 - 4.5 * weighted

    # Corrections
    sq = scores.get("skin_quality", 5)
    wr = scores.get("wrinkles",     5)
    st = scores.get("skin_tension", 5)
    ea = scores.get("eye_area",     5)
    fo = scores.get("face_oval",    5)
    nk = scores.get("neck",         5)

    corr = 0
    if wr <= 4 and st <= 4:          corr += 3   # deep wrinkles + low tension
    if sq >= 8 and wr >= 8 and ea >= 7: corr -= 2  # excellent trio
    if ea <= 4:                      corr += 2   # severe eye area issues
    if fo <= 4 and st <= 4:          corr += 2   # oval + tension both poor
    if neck_visible and nk <= 4:     corr += 2   # visible bad neck
    if neck_visible and nk >= 8:     corr -= 1   # excellent neck

    age_calc = max(20.0, min(65.0, age_base + corr))

    # Confidence from image quality → determines range width
    confidence = _calc_confidence(image_quality)

    if confidence >= 0.75:
        lo, hi  = 2, 3   # 5-year range, e.g. "35–40 lat"
        prefix  = ""
    else:
        lo, hi  = 4, 4   # 8-year range, e.g. "około 33–41 lat"
        prefix  = "około " if lang == "pl" else "approximately "

    age_min = max(20, round(age_calc) - lo)
    age_max = min(65, round(age_calc) + hi)

    # Factors: deviation × weight per field
    factor_labels = _BIO_FACTOR_LABELS_PL if lang == "pl" else _BIO_FACTOR_LABELS_EN
    deviations = {f: (scores.get(f, 5) - 5) * w for f, w in weights.items()}

    if weighted >= 7.0:
        # Good result → show strengths supporting younger look
        top = sorted(deviations, key=lambda f: deviations[f], reverse=True)[:3]
        factors_type = "positive"
    else:
        # Weaker result → show factors most increasing age
        top = sorted(deviations, key=lambda f: deviations[f])[:3]
        factors_type = "negative"

    factors = [factor_labels[f] for f in top]

    return {
        "bio_age_min":    age_min,
        "bio_age_max":    age_max,
        "bio_prefix":     prefix,
        "bio_confidence": round(confidence, 2),
        "bio_factors":    factors,
        "bio_factors_type": factors_type,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def analyze(
    file_paths_dict: Dict[str, str],
    openai_client,
    model: str = "gpt-4o",
    lang: str = "pl",
    user_age: int | None = None,
) -> dict:
    """
    Runs Stage 1 → Stage 2, then assembles the result.

    Raises ValueError with "REJECT:{code}" prefix if a hard block is detected.
    Returns result dict on success.
    """
    image_path = file_paths_dict.get("en_face", "")
    if not image_path:
        raise ValueError("PHOTO_UNSUITABLE: Brak pliku zdjęcia.")

    # Stage 1: Validate
    print(f"[PIPELINE] stage1 start image={image_path} lang={lang}", flush=True)
    val = stage1_validate.run(image_path, openai_client, model)

    if not val["accepted"]:
        reason_code = val.get("reject_reason") or "no_face"
        print(f"[PIPELINE] stage1 blocked reason={reason_code}", flush=True)
        raise ValueError(f"REJECT:{reason_code}")

    print(f"[PIPELINE] stage1 done warnings={len(val['warnings'])}", flush=True)

    # Stage 2: Score
    print("[PIPELINE] stage2 start", flush=True)
    score_result = stage2_score.run(
        image_path=image_path,
        openai_client=openai_client,
        model=model,
        lang=lang,
        validation_metadata=val.get("metadata", {}),
        user_age=user_age,
    )
    print("[PIPELINE] stage2 done", flush=True)

    result = _assemble(score_result, lang, user_age)

    print(
        f"[PIPELINE] complete overall={result['overall_score']} "
        f"bio_age={result.get('bio_age_min')}–{result.get('bio_age_max')} "
        f"confidence={result.get('bio_confidence')}",
        flush=True,
    )
    return result


# ── Internal ──────────────────────────────────────────────────────────────────

def _assemble(score_result: dict, lang: str, user_age: int | None = None) -> dict:
    scores  = score_result.get("scores", {})
    labels  = SCORE_FIELD_LABELS_PL if lang == "pl" else SCORE_FIELD_LABELS_EN

    # Flat int scores for the 7 template area bars
    area_labels = AREA_LABELS_PL if lang == "pl" else AREA_LABELS_EN
    areas_flat: dict[str, int] = {}
    for field_key, area_key in _FIELD_TO_AREA.items():
        areas_flat[area_key] = max(1, min(10, int(scores.get(field_key, 6))))

    # overall_score
    overall_raw = scores.get("overall_face")
    if overall_raw and isinstance(overall_raw, int) and 1 <= overall_raw <= 10:
        overall_score = overall_raw
    else:
        overall_score = max(1, min(10, round(sum(areas_flat.values()) / len(areas_flat))))

    intro = _build_intro(overall_score, lang)

    strength_keys = score_result.get("strengths", [])
    concern_keys  = score_result.get("improvements", [])

    strengths_items = [
        {"label": labels.get(k, k), "score": scores.get(k, 5), "key": k}
        for k in strength_keys
    ]
    concerns_items = [
        {"label": labels.get(k, k), "score": scores.get(k, 5), "key": k}
        for k in concern_keys
    ]

    # Bio age — calculated from scores + image quality (no GPT estimate)
    image_quality = score_result.get("image_quality", {
        "sharpness": "medium", "lighting": "adequate",
        "face_fully_visible": True, "neck_visible": False,
    })
    bio = _calc_bio_age(scores, image_quality, lang)

    return {
        "overall_score":   overall_score,
        "intro":           intro,
        "strengths":       [i["label"] for i in strengths_items],
        "concerns":        [i["label"] for i in concerns_items],
        "strengths_items": strengths_items,
        "concerns_items":  concerns_items,
        "treatments":      recommend_treatments(scores, lang),
        "health_note":     score_result.get("health_note", ""),
        "areas":           areas_flat,
        "area_labels":     area_labels,
        "scores":          scores,
        "lang":            lang,
        "user_age":        user_age,
        # Bio age (new model)
        "bio_age_min":     bio["bio_age_min"],
        "bio_age_max":     bio["bio_age_max"],
        "bio_prefix":      bio["bio_prefix"],
        "bio_confidence":  bio["bio_confidence"],
        "bio_factors":     bio["bio_factors"],
        "bio_factors_type": bio["bio_factors_type"],
    }


def _build_intro(overall: int, lang: str) -> str:
    if lang == "pl":
        if overall >= 9:
            return "Twoja skóra prezentuje się znakomicie — widać dbałość i doskonałą kondycję."
        if overall >= 7:
            return "Twoja skóra jest w dobrej kondycji z kilkoma obszarami, które warto wzmocnić."
        if overall >= 5:
            return "Skóra wymaga regularnej pielęgnacji — kilka obszarów zasługuje na szczególną uwagę."
        return "Skóra wymaga intensywniejszej opieki w kilku kluczowych obszarach."
    else:
        if overall >= 9:
            return "Your skin looks excellent — great condition and visible care."
        if overall >= 7:
            return "Your skin is in good condition with a few areas worth strengthening."
        if overall >= 5:
            return "Your skin needs regular care — several areas deserve closer attention."
        return "Your skin would benefit from more intensive care in several key areas."
