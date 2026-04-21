"""
Stage 2: Face analysis — structured scoring.

Input:  image file path + validation metadata from Stage 1
Output: {
    "photo_check":           {"accepted": bool, "reject_reason": str|None},
    "scores":                {field: int, ...},   # 16 fields, each 1–10
    "strengths":             [field_key, ...],     # 3 best field keys
    "improvements":          [field_key, ...],     # 3 worst field keys
    "suggested_treatments":  [str, ...],           # from allowed list only
    "health_note":           str,
    "doctor_consultation":   bool,
}

Uses a single GPT-4o vision call with ANALYSIS_PROMPT_PL/EN.
GPT returns JSON directly — no intermediate text step.

Error handling:
  - JSON parse failure → logs raw response, raises AnalysisError
  - Validation failure → logs errors, normalizes what it can, logs [SCORE2_WARN]
  - Truncated response → retries once with higher max_tokens
  - Stop condition in response → raises ValueError with EYES_BLOCKED/PHOTO_UNSUITABLE prefix
"""

from __future__ import annotations
import json
import base64
from typing import Any

from prompts import ANALYSIS_PROMPT_PL, ANALYSIS_PROMPT_EN, SCORE_FIELDS, SCORE_FIELDS_OPTIONAL
from treatments import TREATMENTS_PL, TREATMENTS_EN


# ── Public exception ──────────────────────────────────────────────────────────

class AnalysisError(Exception):
    """Raised when Stage 2 cannot produce a usable result."""


# ── Entry point ───────────────────────────────────────────────────────────────

def run(
    image_path: str,
    openai_client,
    model: str = "gpt-4o",
    lang: str = "pl",
    validation_metadata: dict | None = None,
    user_age: int | None = None,
) -> dict:
    """
    Returns analysis dict on success.

    Raises:
        ValueError("EYES_BLOCKED: ...")     — glasses detected
        ValueError("PHOTO_UNSUITABLE: ...")  — no face / filter
        AnalysisError(...)                   — unrecoverable JSON error
    """
    allowed_treatments = TREATMENTS_PL if lang == "pl" else TREATMENTS_EN
    treatments_str = ", ".join(allowed_treatments)

    prompt_template = ANALYSIS_PROMPT_PL if lang == "pl" else ANALYSIS_PROMPT_EN
    prompt = prompt_template.format(treatments=treatments_str)

    context = _build_context(validation_metadata, lang, user_age)
    if context:
        prompt = context + "\n\n" + prompt

    system_msg = (
        "Jesteś asystentem klinicznym w gabinecie dermatologii i medycyny estetycznej. "
        "Twoim zadaniem jest obiektywna ocena widocznych cech skóry i tkanek twarzy "
        "na podstawie zdjęcia dostarczonego przez pacjenta w celach diagnostycznych. "
        "Oceniasz wyłącznie kliniczne parametry skóry — nie oceniasz urody ani atrakcyjności. "
        "Zwróć WYŁĄCZNIE poprawny JSON — bez markdown, bez tekstu poza JSON."
        if lang == "pl" else
        "You are a clinical assistant in a dermatology and aesthetic medicine practice. "
        "Your task is to objectively assess visible skin and facial tissue characteristics "
        "from a photo submitted by the patient for diagnostic purposes. "
        "You assess clinical skin parameters only — not attractiveness or beauty. "
        "Return ONLY valid JSON — no markdown, no text outside JSON."
    )

    image_b64, media_type = _encode_image(image_path)
    messages = [
        {"role": "system", "content": system_msg},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_b64}"}},
                {"type": "text",      "text": prompt},
            ],
        },
    ]

    # Call with retry on truncation
    raw = _call_with_retry(openai_client, messages, model)

    # Parse JSON
    try:
        data = _parse_json(raw)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"[STAGE2 ERROR] JSON parse failed: {e}", flush=True)
        print(f"[STAGE2 ERROR] raw response first_500={repr(raw[:500])}", flush=True)
        raise AnalysisError(f"Nie udało się przetworzyć odpowiedzi modelu: {e}") from e

    # Handle stop conditions from GPT (safety net — Stage 1 should have caught these)
    pc = data.get("photo_check", {})
    if isinstance(pc, dict) and not pc.get("accepted", True):
        reason = pc.get("reject_reason", "no_face")
        print(f"[STAGE2] stop condition from GPT: reject_reason={reason}", flush=True)
        raise ValueError(f"REJECT:{reason}")

    # Validate response
    valid, errors = _validate_response(data, allowed_treatments)
    if not valid:
        print(f"[STAGE2 WARN] validation issues ({len(errors)}): {errors}", flush=True)
        print(f"[STAGE2 WARN] normalizing what we can...", flush=True)

    result = _normalize(data, allowed_treatments)
    _log_scores(result)
    return result


# ── OpenAI call ───────────────────────────────────────────────────────────────

def _call_with_retry(client, messages: list, model: str) -> str:
    """Call GPT with retry on truncation. Raises AnalysisError if both attempts fail."""
    for attempt, max_tokens in enumerate([1400, 1800]):
        raw = _call(client, messages, model, max_tokens)
        if raw:
            return raw
        print(f"[STAGE2] attempt {attempt+1} failed, retrying with max_tokens={max_tokens}", flush=True)
    raise AnalysisError("Stage2: no response after 2 attempts")


def _call(client, messages: list, model: str, max_tokens: int) -> str | None:
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.5,   # 0.5: enough variance to reflect actual photo differences
    )
    choice = response.choices[0]
    raw    = (choice.message.content or "").strip()
    finish = choice.finish_reason

    print(f"[STAGE2] finish={finish} len={len(raw)} max_tokens={max_tokens}", flush=True)
    print(f"[STAGE2] raw first_400={repr(raw[:400])}", flush=True)

    if not raw or len(raw) < 20:
        print(f"[STAGE2] empty/too-short response (finish={finish})", flush=True)
        return None
    if finish == "length":
        print(f"[STAGE2] response truncated at max_tokens={max_tokens}", flush=True)
        return None  # trigger retry with higher max_tokens
    return raw


# ── JSON parsing ──────────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict:
    text = text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        parts = text.split("```", 2)
        inner = parts[1] if len(parts) > 1 else ""
        if inner.startswith("json"):
            inner = inner[4:]
        text = inner.rsplit("```", 1)[0].strip()
    # Extract JSON object
    start = text.find("{")
    end   = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found. text={repr(text[:200])}")
    return json.loads(text[start : end + 1])


# ── Validation ────────────────────────────────────────────────────────────────

def _validate_response(data: Any, allowed_treatments: list) -> tuple[bool, list[str]]:
    """
    Check that the response matches the expected schema.
    Returns (is_valid, list_of_error_strings).
    Does NOT raise — just reports.
    """
    errors: list[str] = []
    allowed_set = {t.lower() for t in allowed_treatments}

    # photo_check
    pc = data.get("photo_check")
    if not isinstance(pc, dict):
        errors.append(f"photo_check: expected dict, got {type(pc).__name__}")
    else:
        if not isinstance(pc.get("accepted"), bool):
            errors.append(f"photo_check.accepted: expected bool, got {pc.get('accepted')!r}")

    # scores — all 16 fields, each 1–10
    scores = data.get("scores")
    if not isinstance(scores, dict):
        errors.append(f"scores: expected dict, got {type(scores).__name__}")
    else:
        for field in SCORE_FIELDS:
            if field not in scores:
                errors.append(f"scores.{field}: missing")
            else:
                v = scores[field]
                try:
                    f = float(v)
                    if not (1 <= f <= 10):
                        errors.append(f"scores.{field}={v} out of range 1–10")
                except (ValueError, TypeError):
                    errors.append(f"scores.{field}={v!r} is not a number")

    # strengths — 3 valid field keys
    strengths = data.get("strengths")
    if not isinstance(strengths, list):
        errors.append(f"strengths: expected list, got {type(strengths).__name__}")
    else:
        if len(strengths) != 3:
            errors.append(f"strengths: expected 3 items, got {len(strengths)}")
        for s in strengths:
            if s not in SCORE_FIELDS:
                errors.append(f"strengths: unknown field key {s!r}")

    # improvements — 3 valid field keys
    improvements = data.get("improvements")
    if not isinstance(improvements, list):
        errors.append(f"improvements: expected list, got {type(improvements).__name__}")
    else:
        if len(improvements) != 3:
            errors.append(f"improvements: expected 3 items, got {len(improvements)}")
        for imp in improvements:
            if imp not in SCORE_FIELDS:
                errors.append(f"improvements: unknown field key {imp!r}")

    # suggested_treatments — from allowed list
    treatments = data.get("suggested_treatments")
    if not isinstance(treatments, list):
        errors.append(f"suggested_treatments: expected list, got {type(treatments).__name__}")
    else:
        for t in treatments:
            if not isinstance(t, str):
                errors.append(f"suggested_treatments: item is not a string: {t!r}")
            elif not any(t.lower() in a or a in t.lower() for a in allowed_set):
                errors.append(f"suggested_treatments: {t!r} not in allowed list")

    # health_note — non-empty string
    hn = data.get("health_note")
    if not isinstance(hn, str) or len(hn.strip()) < 10:
        errors.append(f"health_note: missing or too short ({hn!r})")

    # doctor_consultation — bool
    dc = data.get("doctor_consultation")
    if not isinstance(dc, bool):
        errors.append(f"doctor_consultation: expected bool, got {dc!r}")

    if errors:
        print(f"[STAGE2 VALIDATE] {len(errors)} error(s):", flush=True)
        for e in errors:
            print(f"[STAGE2 VALIDATE]   • {e}", flush=True)

    return len(errors) == 0, errors


# ── Normalization ─────────────────────────────────────────────────────────────

def _normalize(data: dict, allowed_treatments: list) -> dict:
    """
    Coerce / fill in missing fields so the result is always usable.
    Never crashes — always returns a complete dict.
    """
    allowed_set = {t.lower() for t in allowed_treatments}

    # scores — clamp each to 1–10, fill missing with 5
    raw_scores = data.get("scores", {})
    if not isinstance(raw_scores, dict):
        raw_scores = {}
    scores: dict[str, int] = {}
    for field in SCORE_FIELDS:
        try:
            v = max(1, min(10, int(round(float(raw_scores.get(field, 5))))))
        except (ValueError, TypeError):
            v = 5
        scores[field] = v

    # strengths — if invalid keys, pick top 3 from scores (excluding overall_face + optional defaults)
    raw_strengths = data.get("strengths", [])
    strengths = _fix_top_fields(raw_strengths, scores, top=True)

    # improvements — if invalid keys, pick bottom 3
    raw_improvements = data.get("improvements", [])
    improvements = _fix_top_fields(raw_improvements, scores, top=False)

    # suggested_treatments — keep only items from allowed list
    raw_treatments = data.get("suggested_treatments", [])
    if not isinstance(raw_treatments, list):
        raw_treatments = []
    treatments = [
        t for t in raw_treatments
        if isinstance(t, str) and any(t.lower() in a or a in t.lower() for a in allowed_set)
    ][:4]

    # health_note — fallback if missing
    health_note = data.get("health_note", "")
    if not isinstance(health_note, str) or len(health_note.strip()) < 10:
        health_note = (
            "Pamiętaj, że regularne stosowanie filtra SPF 50+ to podstawa ochrony przed fotostarzeniem."
            if "PL" in str(data.get("_lang_hint", "PL")).upper()
            else "Remember that daily SPF 50+ application is the foundation of anti-ageing protection."
        )

    # photo_check — if not present, assume accepted (Stage 1 already validated)
    pc_raw = data.get("photo_check", {})
    photo_check = {
        "accepted":      bool(pc_raw.get("accepted", True)) if isinstance(pc_raw, dict) else True,
        "reject_reason": pc_raw.get("reject_reason") if isinstance(pc_raw, dict) else None,
    }

    # biological_age — clamp to 18–80
    bio_age_raw = data.get("biological_age")
    try:
        bio_age = max(18, min(80, int(bio_age_raw)))
    except (TypeError, ValueError):
        bio_age = None

    return {
        "photo_check":          photo_check,
        "scores":               scores,
        "strengths":            strengths,
        "improvements":         improvements,
        "suggested_treatments": treatments,
        "health_note":          health_note.strip(),
        "biological_age":       bio_age,
        "doctor_consultation":  True,
    }


def _fix_top_fields(raw: Any, scores: dict, top: bool) -> list[str]:
    """
    Validate that raw is a list of 3 valid SCORE_FIELDS keys.
    If not, compute top/bottom 3 from scores directly.
    """
    # Check if raw is valid
    if (
        isinstance(raw, list)
        and len(raw) == 3
        and all(isinstance(k, str) and k in SCORE_FIELDS for k in raw)
    ):
        return raw

    # Compute from scores — exclude overall_face, exclude optional fields at default (5)
    candidates = {
        k: v for k, v in scores.items()
        if k != "overall_face" and not (k in SCORE_FIELDS_OPTIONAL and v == 5)
    }
    if len(candidates) < 3:
        candidates = {k: v for k, v in scores.items() if k != "overall_face"}

    sorted_fields = sorted(candidates, key=lambda k: candidates[k], reverse=top)
    return sorted_fields[:3]


# ── Utilities ─────────────────────────────────────────────────────────────────

def _encode_image(image_path: str) -> tuple[str, str]:
    ext = image_path.rsplit(".", 1)[-1].lower()
    media_type = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "webp": "image/webp",
    }.get(ext, "image/jpeg")
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8"), media_type


def _build_context(metadata: dict | None, lang: str, user_age: int | None = None) -> str:
    lines = []
    if user_age and isinstance(user_age, int) and 18 <= user_age <= 99:
        lines.append(f"[Wiek pacjenta: {user_age} lat]" if lang == "pl" else f"[Patient age: {user_age} years]")
    if not metadata:
        return "\n".join(lines)
    hp = metadata.get("head_pose", {})
    if hp and hp.get("yaw") not in (None, "minimal", "small"):
        lines.append(f"[Głowa obrócona: yaw={hp.get('yaw')}]" if lang == "pl" else f"[Head rotated: yaw={hp.get('yaw')}]")
    if not metadata.get("neck_visible", True):
        lines.append("[Szyja niewidoczna]" if lang == "pl" else "[Neck not visible]")
    if not metadata.get("hairline_visible", True):
        lines.append("[Linia włosów niewidoczna]" if lang == "pl" else "[Hairline not visible]")
    return "\n".join(lines)


def _log_scores(result: dict) -> None:
    scores = result["scores"]
    visible_vals = [v for k, v in scores.items()
                    if k != "overall_face" and not (k in SCORE_FIELDS_OPTIONAL and v == 5)]
    spread = max(visible_vals) - min(visible_vals) if visible_vals else 0
    avg    = sum(visible_vals) / len(visible_vals) if visible_vals else 0
    print(f"[STAGE2 SCORES] overall={scores.get('overall_face')} avg={avg:.1f} "
          f"spread={spread} min={min(visible_vals, default=0)} max={max(visible_vals, default=0)}", flush=True)
    print(f"[STAGE2 SCORES] full_json={json.dumps(scores)}", flush=True)
    print(f"[STAGE2 SCORES] strengths={result['strengths']}", flush=True)
    print(f"[STAGE2 SCORES] improvements={result['improvements']}", flush=True)
    print(f"[STAGE2 SCORES] treatments={result['suggested_treatments']}", flush=True)
