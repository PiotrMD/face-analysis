"""
Pipeline orchestrator — runs Stage 1 + Stage 2, assembles the final result dict.

Stage 3 (report generation) is no longer called — Stage 2 returns all needed
structured data and this module builds patient-facing text from it in Python.

Public API:
    analyze(file_paths_dict, openai_client, model, lang) -> dict

Return dict is compatible with results.html template:
    overall_score, intro, strengths, concerns, treatments,
    health_note, areas (flat int dict), area_labels, lang
"""

from __future__ import annotations
from typing import Dict

from pipeline import stage1_validate, stage2_score
from prompts import SCORE_FIELD_LABELS_PL, SCORE_FIELD_LABELS_EN
from treatments import AREA_LABELS_PL, AREA_LABELS_EN, recommend_treatments


# Maps new 16-field keys → old 7 template area keys (for the score bars)
_FIELD_TO_AREA = {
    "eye_area":     "okolica_oczu",
    "skin_quality": "jakosc_skory",
    "wrinkles":     "zmarszczki",
    "skin_tension": "napiecie",
    "face_oval":    "owal_twarzy",
    "pigmentation": "przebarwienia",
    "vessels":      "naczynka",
}


def analyze(
    file_paths_dict: Dict[str, str],
    openai_client,
    model: str = "gpt-4o",
    lang: str = "pl",
    user_age: int | None = None,
) -> dict:
    """
    Runs Stage 1 → Stage 2, then assembles the result.

    Raises ValueError with "EYES_BLOCKED:" or "PHOTO_UNSUITABLE:" prefix
    if a hard block is detected (Stage 1 or Stage 2).

    Returns result dict on success.
    """
    image_path = file_paths_dict.get("en_face", "")
    if not image_path:
        raise ValueError("PHOTO_UNSUITABLE: Brak pliku zdjęcia.")

    # ── Stage 1: Validate ─────────────────────────────────────────────────────
    print(f"[PIPELINE] stage1 start image={image_path} lang={lang}", flush=True)
    val = stage1_validate.run(image_path, openai_client, model)

    if not val["accepted"]:
        reason_code = val.get("reject_reason") or "no_face"
        print(f"[PIPELINE] stage1 blocked reason={reason_code} lang={lang}", flush=True)
        raise ValueError(f"REJECT:{reason_code}")

    print(f"[PIPELINE] stage1 done warnings={len(val['warnings'])}", flush=True)

    # ── Stage 2: Score ────────────────────────────────────────────────────────
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

    # ── Assemble ──────────────────────────────────────────────────────────────
    result = _assemble(score_result, lang, user_age)

    print(
        f"[PIPELINE] complete overall={result['overall_score']} "
        f"strengths={len(result['strengths'])} concerns={len(result['concerns'])}",
        flush=True,
    )
    return result


# ── Internal ──────────────────────────────────────────────────────────────────

def _assemble(score_result: dict, lang: str, user_age: int | None = None) -> dict:
    """Build the template-compatible result dict from Stage 2 output."""
    scores  = score_result.get("scores", {})
    labels  = SCORE_FIELD_LABELS_PL if lang == "pl" else SCORE_FIELD_LABELS_EN

    # Flat int scores for the 7 template area bars
    area_labels = AREA_LABELS_PL if lang == "pl" else AREA_LABELS_EN
    areas_flat: dict[str, int] = {}
    for field_key, area_key in _FIELD_TO_AREA.items():
        areas_flat[area_key] = max(1, min(10, int(scores.get(field_key, 6))))

    # overall_score — use GPT's own overall_face score, fallback to bar average
    overall_raw = scores.get("overall_face")
    if overall_raw and isinstance(overall_raw, int) and 1 <= overall_raw <= 10:
        overall_score = overall_raw
    else:
        overall_score = max(1, min(10, round(sum(areas_flat.values()) / len(areas_flat))))

    # intro — generated in Python from overall_score (no API call)
    intro = _build_intro(overall_score, lang)

    strength_keys  = score_result.get("strengths", [])
    concern_keys   = score_result.get("improvements", [])

    strengths_items = [
        {"label": labels.get(k, k), "score": scores.get(k, 5), "key": k}
        for k in strength_keys
    ]
    concerns_items = [
        {"label": labels.get(k, k), "score": scores.get(k, 5), "key": k}
        for k in concern_keys
    ]

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
        "biological_age":  score_result.get("biological_age"),
        "user_age":        user_age,
    }


def _build_intro(overall: int, lang: str) -> str:
    """Generate a short intro sentence from the overall score. No API call."""
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
