"""
Stage 3: Patient report generation.

Input:  score_result from Stage 2  (areas with scores + notes, positives, summary)
Output: {
    "intro":       str,
    "strengths":   list[str],
    "concerns":    list[str],
    "treatments":  list[str],
    "health_note": str,
}

Uses a single GPT-4o call with REPORT_PROMPT_PL/EN.
Scores are passed as plain text context — GPT only generates text, never re-scores.
"""

from __future__ import annotations
import json

from prompts import REPORT_PROMPT_PL, REPORT_PROMPT_EN
from treatments import TREATMENTS_PL, TREATMENTS_EN, AREA_LABELS_PL, AREA_LABELS_EN, REQUIRED_AREAS


_HEALTH_NOTES_PL = [
    "Pamiętaj, że regularne stosowanie filtra SPF 50+ to podstawa ochrony przed fotostarzeniem.",
    "Codzienna pielęgnacja — nawilżanie i ochrona przeciwsłoneczna — spowalnia procesy starzenia.",
    "Regularne wizyty kontrolne u lekarza estetycznego pozwalają utrzymać efekty zabiegów.",
]

_HEALTH_NOTES_EN = [
    "Remember that daily SPF 50+ application is the foundation of anti-ageing protection.",
    "Daily skincare — moisturising and sun protection — slows the ageing process.",
    "Regular check-up visits allow you to maintain treatment results over time.",
]


def run(
    score_result: dict,
    lang: str = "pl",
    openai_client = None,
    model: str = "gpt-4o",
) -> dict:
    """
    Returns patient-friendly report dict on success.
    Falls back to a minimal generated report if GPT fails.
    """
    treatments_list = TREATMENTS_PL if lang == "pl" else TREATMENTS_EN
    labels          = AREA_LABELS_PL if lang == "pl" else AREA_LABELS_EN

    prompt_template = REPORT_PROMPT_PL if lang == "pl" else REPORT_PROMPT_EN
    prompt = prompt_template.format(treatments=", ".join(treatments_list))

    score_context = _format_scores(score_result, labels, lang)

    system_msg = (
        "Jesteś przyjaznym beauty-doradcą piszącym spersonalizowany raport analizy twarzy dla pacjenta. "
        "Bądź ciepły, pozytywny i konkretny. "
        "Pisz WYŁĄCZNIE po polsku. Zwróć tylko poprawny JSON — bez markdown."
        if lang == "pl" else
        "You are a friendly beauty advisor writing a personalised face analysis report for a patient. "
        "Be warm, positive, and specific. "
        "Write ONLY in English. Return only valid JSON — no markdown."
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"{score_context}\n\n{prompt}"},
    ]

    for attempt in range(2):
        try:
            raw = _call(openai_client, messages, model, max_tokens=1500)
            print(f"[STAGE3] attempt={attempt+1} raw first_400={repr(raw[:400])}", flush=True)
            data = _parse_json(raw)
            result = _normalize(data, score_result, lang, treatments_list)
            print(f"[STAGE3] intro={repr(result['intro'][:80])}", flush=True)
            return result
        except (ValueError, json.JSONDecodeError) as e:
            print(f"[STAGE3] attempt={attempt+1} failed: {e}", flush=True)
            if attempt == 1:
                return _fallback(score_result, lang)

    return _fallback(score_result, lang)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _format_scores(score_result: dict, labels: dict, lang: str) -> str:
    """Format Stage 2 output as readable context for GPT."""
    areas = score_result.get("areas", {})
    lines = ["WYNIKI OCENY:" if lang == "pl" else "SCORING RESULTS:"]
    for key in REQUIRED_AREAS:
        area_data = areas.get(key, {})
        score = area_data.get("score", "?")
        note  = area_data.get("note", "")
        label = labels.get(key, key)
        lines.append(f"  {label}: {score}/10 — {note}")

    positives = score_result.get("positives", [])
    summary   = score_result.get("summary", "")

    if positives:
        header = "MOCNE STRONY:" if lang == "pl" else "POSITIVES:"
        lines.append(f"\n{header}")
        for p in positives:
            lines.append(f"  - {p}")

    if summary:
        header = "OGÓLNE WRAŻENIE:" if lang == "pl" else "OVERALL IMPRESSION:"
        lines.append(f"\n{header} {summary}")

    return "\n".join(lines)


def _call(client, messages: list, model: str, max_tokens: int) -> str:
    response = client.chat.completions.create(
        model=model, messages=messages, max_tokens=max_tokens, temperature=0.6,
    )
    choice = response.choices[0]
    raw    = choice.message.content or ""
    print(f"[STAGE3] finish={choice.finish_reason} len={len(raw)}", flush=True)
    if not raw or len(raw) < 20:
        raise ValueError(f"Stage3: empty response (finish={choice.finish_reason})")
    low = raw.lower()
    if any(low.startswith(p) for p in ("i'm sorry", "i cannot", "przepraszam, nie mogę")):
        raise ValueError(f"Stage3: soft refusal: {repr(raw[:80])}")
    return raw


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"Stage3: no JSON in response: {repr(text[:300])}")
    return json.loads(text[start : end + 1])


def _normalize(data: dict, score_result: dict, lang: str, treatments_list: list) -> dict:
    """Validate and clean GPT output. Fill missing fields — never crash."""
    allowed_set = {t.lower() for t in treatments_list}

    intro = data.get("intro", "")
    if not isinstance(intro, str) or len(intro.strip()) < 10:
        intro = _fallback_intro(score_result, lang)
    print(f"[STAGE3 INTRO] kept={len(intro.strip())>=10} intro={repr(intro[:80])}", flush=True)

    strengths = data.get("strengths", [])
    if not isinstance(strengths, list) or not strengths:
        positives = score_result.get("positives", [])
        strengths = positives[:3] if positives else (
            ["Dobra ogólna kondycja twarzy"] if lang == "pl" else ["Good overall facial condition"]
        )
    strengths = [s for s in strengths if isinstance(s, str) and len(s) > 3][:6]

    concerns = data.get("concerns", [])
    if not isinstance(concerns, list):
        concerns = []
    concerns = [c for c in concerns if isinstance(c, str) and len(c) > 3][:5]

    raw_treatments = data.get("treatments", [])
    if not isinstance(raw_treatments, list):
        raw_treatments = []
    treatments = [
        t for t in raw_treatments
        if isinstance(t, str) and any(
            allowed.lower() in t.lower() or t.lower() in allowed.lower()
            for allowed in allowed_set
        )
    ][:5]

    health_note = data.get("health_note", "")
    if not isinstance(health_note, str) or len(health_note.strip()) < 10:
        health_note = (_HEALTH_NOTES_PL if lang == "pl" else _HEALTH_NOTES_EN)[0]

    return {
        "intro":       intro,
        "strengths":   strengths,
        "concerns":    concerns,
        "treatments":  treatments,
        "health_note": health_note,
    }


def _fallback_intro(score_result: dict, lang: str) -> str:
    areas  = score_result.get("areas", {})
    scores = [areas[k]["score"] for k in REQUIRED_AREAS if k in areas and isinstance(areas[k], dict)]
    avg    = sum(scores) / len(scores) if scores else 6.5
    if lang == "pl":
        if avg >= 8:
            return "Twoja twarz jest w naprawdę dobrej kondycji — masz piękne atuty, które warto pielęgnować."
        if avg >= 6:
            return "Masz ładne cechy twarzy — kilka ukierunkowanych zabiegów pomoże wydobyć je jeszcze bardziej."
        return "Warto zadbać o kilka obszarów — masz duży potencjał, który odpowiednie zabiegi mogą pięknie uwydatnić."
    if avg >= 8:
        return "Your face is in really good shape — you have beautiful features worth maintaining."
    if avg >= 6:
        return "You have lovely facial features — a few targeted treatments will enhance them even further."
    return "There are a few areas worth addressing — you have great potential that the right treatments can beautifully enhance."


def _fallback(score_result: dict, lang: str) -> dict:
    """Minimal report built from scores when GPT fails entirely."""
    print("[STAGE3] using fallback report", flush=True)
    treatments_list = TREATMENTS_PL if lang == "pl" else TREATMENTS_EN
    areas  = score_result.get("areas", {})
    low    = [k for k in REQUIRED_AREAS if isinstance(areas.get(k), dict) and areas[k].get("score", 10) <= 5]
    labels = AREA_LABELS_PL if lang == "pl" else AREA_LABELS_EN

    concerns = []
    if lang == "pl":
        for k in low[:3]:
            concerns.append(f"Obszar '{labels.get(k, k)}' — warto omówić z lekarzem.")
    else:
        for k in low[:3]:
            concerns.append(f"Area '{labels.get(k, k)}' — worth discussing with the doctor.")

    treatments = treatments_list[:2] if low else []

    return {
        "intro":       _fallback_intro(score_result, lang),
        "strengths":   score_result.get("positives", [])[:3],
        "concerns":    concerns,
        "treatments":  treatments,
        "health_note": (_HEALTH_NOTES_PL if lang == "pl" else _HEALTH_NOTES_EN)[0],
    }
