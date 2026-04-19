import json
import base64
from typing import Dict

# ═══════════════════════════════════════════════════════════════════
# OBSERVATION PROMPT — Step 1: photo → plain-text notes
# ═══════════════════════════════════════════════════════════════════
OBSERVATION_PROMPT = """Look at this face photo and fill in the assessment form below. Be specific about what you actually see. Plain language, no jargon.

STOP CONDITIONS (answer first):
- Sunglasses or glasses blocking eyes → write "EYES_BLOCKED" and stop
- No human face in photo → write "NO_FACE" and stop
- Obvious digital beauty filter (plastic/airbrushed skin, Snapchat filter) → write "FILTER_DETECTED" and stop
- Otherwise → continue with the form below

━━━ AREA 1: EYE AREA ━━━
Dark circles / shadows under eyes: none / mild / moderate / strong
Under-eye bags or puffiness: absent / mild / moderate / marked
Crow's feet (corner lines): absent / fine / moderate / deep
Upper eyelid heaviness: none / mild / notable
Overall eye area freshness: fresh / neutral / tired

━━━ AREA 2: SKIN QUALITY ━━━
Skin texture: smooth / slightly rough / rough / very rough
Pore visibility: not visible / mildly visible / clearly visible / prominent
Skin tone evenness: even / minor unevenness / moderate unevenness / very uneven
Skin hydration appearance: plump / normal / slightly dehydrated / dehydrated
Overall skin quality: excellent / good / fair / needs attention

━━━ AREA 3: WRINKLES ━━━
Forehead lines: none / fine dynamic / moderate / deep static
Between-brow lines (11s): none / mild / moderate / deep
Nose-to-mouth lines (nasolabial): none / fine / moderate / deep
Around-mouth lines: none / fine / moderate / deep
Overall wrinkle level: minimal / mild / moderate / significant

━━━ AREA 4: FACE FIRMNESS / TENSION ━━━
Cheek firmness: firm / mildly descended / notably descended
Jawline definition: sharp / mildly blurred / blurred / jowl formation
Lower face oval: defined / mildly soft / soft
Overall firmness: excellent / good / fair / needs attention

━━━ AREA 5: FACE OVAL ━━━
Face proportions (thirds): balanced / upper-dominant / lower-dominant
Chin definition: well-defined / mild / recessed
Overall oval: well-defined / good / soft

━━━ AREA 6: PIGMENTATION ━━━
Sun spots / dark patches: none / 1-2 small / several / extensive
Post-acne marks: none / 1-2 / several / many
Overall pigmentation: clear / minor / moderate / significant

━━━ AREA 7: VASCULAR / REDNESS ━━━
General redness: none / mild / moderate / strong
Visible broken capillaries: none / a few / moderate / many
Rosacea signs: none / possible / likely
Overall vascular concern: none / mild / moderate / significant

━━━ POSITIVES ━━━
List 3-5 specific things that genuinely look good about this face:
1.
2.
3.
(4.)
(5.)

━━━ SUMMARY ━━━
One sentence: what is the overall impression of this face?"""


# ═══════════════════════════════════════════════════════════════════
# REPORT PROMPT — Step 2: observations → patient-friendly JSON
# ═══════════════════════════════════════════════════════════════════

TREATMENTS_PL = [
    "Toksyna botulinowa",
    "RF mikroigłowa",
    "Mezoterapia",
    "Peelingi chemiczne",
    "Laser frakcyjny",
    "Stymulatory tkankowe",
    "Osocze bogatopłytkowe (PRP)",
    "Fibryna bogatokomórkowa (PRF)",
    "Filler HA",
    "Laser naczyniowy",
    "Elektrokoagulacja",
]

TREATMENTS_EN = [
    "Botulinum toxin",
    "Microneedling RF",
    "Mesotherapy",
    "Chemical peels",
    "Fractional laser",
    "Tissue stimulators",
    "Platelet-rich plasma (PRP)",
    "Platelet-rich fibrin (PRF)",
    "HA filler",
    "Vascular laser",
    "Electrocoagulation",
]

REPORT_PROMPT_PL = """Na podstawie obserwacji napisz przyjazny raport analizy twarzy dla pacjenta. Ton: ciepły, pozytywny beauty-doradca — nie lekarz.

ZASADY:
- Mocne strony: konkretne, pozytywne — co naprawdę wygląda dobrze
- Do poprawy: delikatne, konstruktywne — szansa na poprawę, nie problem
- Zabiegi: TYLKO nazwy z tej listy, bez opisów: {treatments}
- Skale 1–10: 10=idealnie, 7-9=dobrze, 5-6=przeciętnie, 3-4=wymaga uwagi, 1-2=pilnie
- Nie wymyślaj rzeczy niewidocznych na zdjęciu
- Każdy pacjent ma inny wynik — nie kopiuj szablonów

Zwróć TYLKO poprawny JSON (bez markdown):

{{
  "overall_score": <1-10>,
  "intro": "<jedno zdanie po polsku — ciepłe powitanie i ogólna ocena>",
  "strengths": [
    "<konkretna mocna strona po polsku>",
    "<konkretna mocna strona po polsku>",
    "<konkretna mocna strona po polsku>"
  ],
  "concerns": [
    "<obszar do poprawy po polsku — delikatnie>",
    "<obszar do poprawy po polsku — delikatnie>"
  ],
  "treatments": [
    "<nazwa zabiegu z listy>",
    "<nazwa zabiegu z listy>"
  ],
  "areas": {{
    "okolica_oczu":  <1-10>,
    "jakosc_skory":  <1-10>,
    "zmarszczki":    <1-10>,
    "napiecie":      <1-10>,
    "owal_twarzy":   <1-10>,
    "przebarwienia": <1-10>,
    "naczynka":      <1-10>
  }}
}}"""

REPORT_PROMPT_EN = """Based on the observations, write a friendly face analysis report for the patient. Tone: warm, positive beauty advisor — not a doctor.

RULES:
- Strengths: specific, positive — what genuinely looks good
- Concerns: gentle, constructive — an opportunity to improve, not a problem
- Treatments: ONLY names from this list, no descriptions: {treatments}
- Scores 1–10: 10=perfect, 7-9=good, 5-6=average, 3-4=needs attention, 1-2=urgent
- Do not invent things not visible in the photo
- Each patient has a different result — do not copy templates

Return ONLY valid JSON (no markdown):

{{
  "overall_score": <1-10>,
  "intro": "<one warm sentence in English — welcoming intro and overall impression>",
  "strengths": [
    "<specific strength in English>",
    "<specific strength in English>",
    "<specific strength in English>"
  ],
  "concerns": [
    "<area for improvement in English — gently worded>",
    "<area for improvement in English — gently worded>"
  ],
  "treatments": [
    "<treatment name from list>",
    "<treatment name from list>"
  ],
  "areas": {{
    "okolica_oczu":  <1-10>,
    "jakosc_skory":  <1-10>,
    "zmarszczki":    <1-10>,
    "napiecie":      <1-10>,
    "owal_twarzy":   <1-10>,
    "przebarwienia": <1-10>,
    "naczynka":      <1-10>
  }}
}}"""


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

_SOFT_REFUSALS = (
    "i'm sorry, i can't",
    "i'm sorry, i cannot",
    "i can't assist",
    "i cannot assist",
    "i'm not able to",
    "i cannot help",
    "i can't help",
    "sorry, i can't",
    "sorry, but i can't",
)


# ═══════════════════════════════════════════════════════════════════
# API helpers
# ═══════════════════════════════════════════════════════════════════

def _call_raw(openai_client, messages: list, model: str, max_tokens: int) -> str:
    response = openai_client.chat.completions.create(
        model=model, messages=messages, max_tokens=max_tokens, temperature=0.5,
    )
    choice  = response.choices[0]
    raw     = choice.message.content or ''
    refusal = getattr(choice.message, 'refusal', None)
    print(f"[API] finish={choice.finish_reason} refusal={bool(refusal)} len={len(raw)}")
    if refusal or not raw or len(raw) < 20:
        raise ValueError(f"API refused or returned empty (finish={choice.finish_reason})")
    if any(raw.lower().startswith(p) for p in _SOFT_REFUSALS):
        print(f"[API] soft refusal detected: {repr(raw[:80])}")
        raise ValueError(f"API soft refusal: {raw[:80]}")
    if choice.finish_reason == 'length':
        raise ValueError(f"API response truncated — max_tokens={max_tokens} insufficient")
    return raw


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    start = text.find("{")
    end   = text.rfind("}")
    if start == -1 or end == -1:
        print(f"[EXTRACT_JSON FAIL] first 500 chars: {repr(text[:500])}")
        raise ValueError("No JSON object found in response")
    return json.loads(text[start:end+1])


# ═══════════════════════════════════════════════════════════════════
# Pipeline steps
# ═══════════════════════════════════════════════════════════════════

def _observe(openai_client, images_data: dict, model: str, validation_context: dict = None) -> str:
    user_content = []
    if 'en_face' in images_data:
        img = images_data['en_face']
        user_content.append({"type": "image_url", "image_url": {"url": f"data:{img['media_type']};base64,{img['data']}"}})

    observation_text = OBSERVATION_PROMPT
    if validation_context:
        ctx_lines = ["[PRE-VALIDATION CONTEXT]:"]
        hp = validation_context.get('head_pose', {})
        if hp:
            ctx_lines.append(f"  Head pose: yaw={hp.get('yaw','?')} pitch={hp.get('pitch','?')}")
        if not validation_context.get('neck_visible', True):
            ctx_lines.append("  Neck not visible in frame")
        if not validation_context.get('hairline_visible', True):
            ctx_lines.append("  Hairline not visible in frame")
        observation_text = "\n".join(ctx_lines) + "\n\n" + observation_text

    user_content.append({"type": "text", "text": observation_text})
    messages = [
        {"role": "system", "content": "You are an aesthetic face analysis specialist. Fill in the assessment form based on what you see in the photo. Be specific and honest about both positive features and areas for improvement."},
        {"role": "user",   "content": user_content},
    ]
    return _call_raw(openai_client, messages, model, max_tokens=1500)


def _report(openai_client, observations: str, model: str, lang: str = 'pl') -> dict:
    treatments = ", ".join(TREATMENTS_PL if lang == 'pl' else TREATMENTS_EN)
    prompt_template = REPORT_PROMPT_PL if lang == 'pl' else REPORT_PROMPT_EN
    prompt = prompt_template.format(treatments=treatments)

    system_msg = (
        "You are a friendly beauty advisor writing a personalised face analysis for a patient. "
        "Be warm, positive, and specific. Return only valid JSON — no markdown, no extra text."
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user",   "content": f"OBSERVATIONS:\n{observations}\n\n{prompt}"},
    ]
    for attempt in range(2):
        raw = _call_raw(openai_client, messages, model, max_tokens=2000)
        try:
            return _extract_json(raw)
        except (ValueError, json.JSONDecodeError) as e:
            print(f"[REPORT] JSON parse failed attempt {attempt+1}: {e} — raw[:200]: {repr(raw[:200])}")
            if attempt == 1:
                raise
    raise ValueError("_report: exhausted retries")


def _validate_result(result: dict, lang: str = 'pl') -> None:
    # overall_score: clamp to 1-10
    try:
        result['overall_score'] = max(1, min(10, int(round(float(result.get('overall_score', 5))))))
    except (ValueError, TypeError):
        result['overall_score'] = 5

    # strengths: ensure list of strings
    if not isinstance(result.get('strengths'), list) or not result['strengths']:
        result['strengths'] = ["Dobra struktura twarzy" if lang == 'pl' else "Good facial structure"]
    result['strengths'] = [s for s in result['strengths'] if isinstance(s, str) and len(s) > 3][:6]

    # concerns: ensure list of strings
    if not isinstance(result.get('concerns'), list):
        result['concerns'] = []
    result['concerns'] = [s for s in result['concerns'] if isinstance(s, str) and len(s) > 3][:5]

    # treatments: validate against allowed list
    allowed = set(TREATMENTS_PL + TREATMENTS_EN)
    raw_treatments = result.get('treatments', [])
    if isinstance(raw_treatments, list):
        result['treatments'] = [t for t in raw_treatments if isinstance(t, str) and any(
            allowed_t.lower() in t.lower() or t.lower() in allowed_t.lower()
            for allowed_t in allowed
        )][:6]
    else:
        result['treatments'] = []

    # areas: clamp each to 1-10, fill missing
    areas = result.get('areas', {})
    if not isinstance(areas, dict):
        areas = {}
    for key in REQUIRED_AREAS:
        try:
            areas[key] = max(1, min(10, int(round(float(areas.get(key, 6))))))
        except (ValueError, TypeError):
            areas[key] = 6
    result['areas'] = areas

    # overall_score: recompute as area average if areas are present
    area_scores = [areas[k] for k in REQUIRED_AREAS]
    result['overall_score'] = max(1, min(10, int(round(sum(area_scores) / len(area_scores)))))

    # intro: ensure string
    if not isinstance(result.get('intro'), str) or len(result.get('intro', '')) < 5:
        result['intro'] = "Oto Twoja indywidualna analiza twarzy." if lang == 'pl' else "Here is your personalised face analysis."

    # Add area labels for template
    labels = AREA_LABELS_PL if lang == 'pl' else AREA_LABELS_EN
    result['area_labels'] = labels
    result['lang'] = lang


# ═══════════════════════════════════════════════════════════════════
# Public entry point
# ═══════════════════════════════════════════════════════════════════

def analyze_face_with_ai(
    file_paths_dict: Dict[str, str],
    openai_client,
    model: str = "gpt-4o",
    lang: str = 'pl'
) -> Dict:
    from face_validator_ai import validate_face_ai

    images_data = {}
    for key, file_path in file_paths_dict.items():
        with open(file_path, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode('utf-8')
        ext = file_path.rsplit('.', 1)[-1].lower()
        media_type = {
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'png': 'image/png', 'webp': 'image/webp'
        }.get(ext, 'image/jpeg')
        images_data[key] = {'data': image_data, 'media_type': media_type}

    # Step 0: AI photo validation (fail-open — only hard blocks)
    en_face_path = file_paths_dict.get('en_face', '')
    validation = {}
    if en_face_path:
        try:
            validation = validate_face_ai(en_face_path, openai_client, model)
            print(f"[VALIDATE_AI OK] impression={validation.get('overall_impression', {}).get('labels')}")
        except ValueError:
            raise
        except Exception as e:
            print(f"[VALIDATE_AI WARN] {e} — continuing")
            validation = {}

    # Step 1: Observe
    observations = _observe(openai_client, images_data, model, validation_context=validation)
    print(f"[OBSERVE OK] {len(observations)} chars")

    obs_upper = observations[:200].upper()
    if 'EYES_BLOCKED' in obs_upper:
        raise ValueError("EYES_BLOCKED: Zdjęcie z okularami — analiza okolicy oczu niemożliwa. Wgraj zdjęcie bez okularów.")
    if 'NO_FACE' in obs_upper:
        raise ValueError("PHOTO_UNSUITABLE: Nie wykryto twarzy. Wgraj wyraźne zdjęcie twarzy en face.")
    if 'FILTER_DETECTED' in obs_upper:
        raise ValueError("PHOTO_UNSUITABLE: Wykryto filtr beauty — analiza niemożliwa. Wgraj nieretuszowane zdjęcie.")

    # Step 2: Report
    result = _report(openai_client, observations, model, lang=lang)

    # Inject validation extras
    if validation:
        result['validation'] = validation
        result['neck_visible']     = validation.get('neck_visible', True)
        result['hairline_visible'] = validation.get('hairline_visible', True)

    _validate_result(result, lang=lang)
    return result
