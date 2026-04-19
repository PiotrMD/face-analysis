import json
import base64
from typing import Dict

# ═══════════════════════════════════════════════════════════════════
# OBSERVATION PROMPTS — Step 1: photo → plain-text notes (PL / EN)
# ═══════════════════════════════════════════════════════════════════
OBSERVATION_PROMPT_PL = """Przejrzyj to zdjęcie twarzy i wypełnij poniższy formularz oceny. Bądź konkretny w tym, co faktycznie widzisz. Prosty język, bez żargonu medycznego. Odpowiedz WYŁĄCZNIE po polsku.

WARUNKI ZATRZYMANIA (sprawdź najpierw):
- Okulary przeciwsłoneczne lub okulary zasłaniające oczy → napisz "EYES_BLOCKED" i zakończ
- Brak ludzkiej twarzy na zdjęciu → napisz "NO_FACE" i zakończ
- Wyraźny cyfrowy filtr upiększający (plastikowa/wyretuszowana skóra, filtr Snapchat) → napisz "FILTER_DETECTED" i zakończ
- W pozostałych przypadkach → kontynuuj formularz poniżej

━━━ OBSZAR 1: OKOLICA OCZU ━━━
Cienie/sińce pod oczami: brak / łagodne / umiarkowane / wyraźne
Worki lub opuchlizna pod oczami: brak / łagodne / umiarkowane / wyraźne
Kurze łapki (linie w kącikach oczu): brak / delikatne / umiarkowane / głębokie
Opadanie górnej powieki: brak / łagodne / wyraźne
Ogólna świeżość okolicy oczu: świeża / neutralna / zmęczona

━━━ OBSZAR 2: JAKOŚĆ SKÓRY ━━━
Tekstura skóry: gładka / lekko nierówna / nierówna / bardzo nierówna
Widoczność porów: niewidoczne / lekko widoczne / wyraźnie widoczne / duże
Równomierność kolorytu: równomierny / drobne nierówności / umiarkowane nierówności / bardzo nierówny
Wygląd nawilżenia skóry: pełna/nawilżona / normalna / lekko odwodniona / odwodniona
Ogólna jakość skóry: doskonała / dobra / przeciętna / wymaga uwagi

━━━ OBSZAR 3: ZMARSZCZKI ━━━
Linie na czole: brak / delikatne dynamiczne / umiarkowane / głębokie statyczne
Linie między brwiami (jedenastki): brak / łagodne / umiarkowane / głębokie
Bruzdy nosowo-wargowe: brak / delikatne / umiarkowane / głębokie
Linie wokół ust: brak / delikatne / umiarkowane / głębokie
Ogólny poziom zmarszczek: minimalny / łagodny / umiarkowany / wyraźny

━━━ OBSZAR 4: NAPIĘCIE I SPRĘŻYSTOŚĆ TWARZY ━━━
Sprężystość policzków: dobra / lekko opadające / wyraźnie opadające
Zarys żuchwy: wyraźny / lekko niewyraźny / niewyraźny / tworzące się jowle
Owal dolnej części twarzy: wyraźny / lekko miękki / miękki
Ogólna sprężystość: doskonała / dobra / przeciętna / wymaga uwagi

━━━ OBSZAR 5: OWAL TWARZY ━━━
Proporcje twarzy (trójpodziały): zrównoważone / dominuje górna część / dominuje dolna część
Zarys brody: wyraźny / łagodny / cofnięty
Ogólny owal: dobrze zarysowany / dobry / miękki

━━━ OBSZAR 6: PRZEBARWIENIA ━━━
Plamy słoneczne / ciemne przebarwienia: brak / 1-2 małe / kilka / rozległe
Ślady po trądziku: brak / 1-2 / kilka / wiele
Ogólny stan przebarwień: czysta / drobne / umiarkowane / wyraźne

━━━ OBSZAR 7: NACZYNKA / RUMIEŃ ━━━
Ogólne zaczerwienienie: brak / łagodne / umiarkowane / wyraźne
Widoczne naczynka: brak / kilka / umiarkowanie / wiele
Wzorzec zaczerwienienia: brak / łagodny / wyraźny
Ogólny problem naczyniowy: brak / łagodny / umiarkowany / wyraźny

━━━ MOCNE STRONY ━━━
Wymień 3-5 konkretnych rzeczy, które naprawdę dobrze wyglądają na tej twarzy:
1.
2.
3.
(4.)
(5.)

━━━ PODSUMOWANIE ━━━
Jedno zdanie: jakie jest ogólne wrażenie tej twarzy?"""

OBSERVATION_PROMPT_EN = """Look at this face photo and fill in the assessment form below. Be specific about what you actually see. Plain language, no jargon. Answer ONLY in English.

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
Redness pattern: none / mild / notable
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

REPORT_PROMPT_PL = """Na podstawie obserwacji napisz przyjazny raport analizy twarzy dla pacjenta. Ton: ciepły, pozytywny beauty-doradca — nie lekarz.

KALIBRACJA OBSZARÓW (1-10) — punkty MUSZĄ odzwierciedlać obserwacje:
- okolica_oczu: wyraźne cienie/worki → 3-4 | łagodne → 6-7 | świeża/brak → 8-10
- zmarszczki: głębokie statyczne → 2-4 | umiarkowane → 5-6 | drobne dynamiczne → 7-8 | brak → 9-10
- napiecie: opadanie/jowle → 2-4 | łagodne obniżenie → 5-6 | dobra sprężystość → 8-10
- jakosc_skory: szorstka+rozszerzone pory → 3-5 | lekkie nierówności → 6-7 | gładka → 9-10
- przebarwienia: rozległe plamy → 2-4 | kilka drobnych → 5-7 | brak → 9-10
- naczynka: wyraźne naczynia/rumień → 3-5 | lekkie → 6-7 | brak → 9-10
- owal_twarzy: jowle/nieokreślony → 3-5 | dobry → 7-8 | wyrazisty → 9-10
ZAKAZ: dawać 6-7 wszystkim obszarom. Wyniki MUSZĄ być zróżnicowane.
ZAKAZ: powielać ten sam opis dla różnych pacjentów — każdy opis musi odnosić się do tego konkretnego zdjęcia.

INTRO zależnie od wyników:
- Większość obszarów 8-10: "Twoja twarz jest w świetnej kondycji — [konkretna cecha]."
- Mix 6-8: "Masz ładne atuty — [konkretna cecha] — kilka zabiegów pomoże wydobyć je jeszcze bardziej."
- Kilka obszarów <5: "Warto zadbać o kilka obszarów — masz duży potencjał do poprawy."

Zabiegi: TYLKO nazwy z tej listy: {treatments}

Zwróć TYLKO poprawny JSON (bez markdown):

{{
  "overall_score": <1-10>,
  "intro": "<jedno konkretne zdanie — nawiązuj do TEGO zdjęcia, nie szablonu>",
  "strengths": [
    "<konkretna mocna strona — nazwij co dokładnie wygląda dobrze>",
    "<konkretna mocna strona>",
    "<konkretna mocna strona>"
  ],
  "concerns": [
    "<konkretny obszar do poprawy — delikatnie sformułowany>",
    "<konkretny obszar do poprawy>"
  ],
  "treatments": [
    "<nazwa zabiegu z listy>",
    "<nazwa zabiegu z listy>"
  ],
  "areas": {{
    "okolica_oczu":  <1-10 zgodnie z kalibracja>,
    "jakosc_skory":  <1-10>,
    "zmarszczki":    <1-10>,
    "napiecie":      <1-10>,
    "owal_twarzy":   <1-10>,
    "przebarwienia": <1-10>,
    "naczynka":      <1-10>
  }}
}}"""

REPORT_PROMPT_EN = """Based on the observations, write a friendly face analysis report for the patient. Tone: warm, positive beauty advisor — not a doctor.

SCORE CALIBRATION (1-10) — scores MUST match observations:
- eye_area (okolica_oczu): strong dark circles/bags → 3-4 | mild → 6-7 | fresh/none → 8-10
- wrinkles (zmarszczki): deep static → 2-4 | moderate → 5-6 | fine dynamic → 7-8 | none → 9-10
- firmness (napiecie): jowls/descent → 2-4 | mild softening → 5-6 | good firmness → 8-10
- skin quality (jakosc_skory): rough+pores → 3-5 | minor issues → 6-7 | smooth → 9-10
- pigmentation (przebarwienia): extensive spots → 2-4 | a few → 5-7 | none → 9-10
- vascular (naczynka): visible capillaries/redness → 3-5 | mild → 6-7 | none → 9-10
- face oval (owal_twarzy): jowls/undefined → 3-5 | good → 7-8 | defined → 9-10
FORBIDDEN: giving 6-7 to all areas. Scores MUST vary.
FORBIDDEN: copying the same text for different patients.

INTRO based on results:
- Most areas 8-10: "Your face is in great condition — [specific feature]."
- Mix 6-8: "You have lovely features — [specific feature] — a few targeted treatments will enhance them further."
- Several areas <5: "There are a few areas worth addressing — you have great potential for improvement."

Treatments: ONLY names from this list: {treatments}

Return ONLY valid JSON (no markdown):

{{
  "overall_score": <1-10>,
  "intro": "<one specific sentence — reference THIS photo, not a template>",
  "strengths": [
    "<specific strength — name exactly what looks good>",
    "<specific strength>",
    "<specific strength>"
  ],
  "concerns": [
    "<specific concern — gently worded>",
    "<specific concern>"
  ],
  "treatments": [
    "<treatment name from list>",
    "<treatment name from list>"
  ],
  "areas": {{
    "okolica_oczu":  <1-10 per calibration>,
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
    print(f"[API] finish={choice.finish_reason} refusal={bool(refusal)} len={len(raw)}", flush=True)
    print(f"[API] raw_content={repr(raw[:200])}", flush=True)
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

def _observe(openai_client, images_data: dict, model: str, validation_context: dict = None, lang: str = 'pl') -> str:
    user_content = []
    if 'en_face' in images_data:
        img = images_data['en_face']
        user_content.append({"type": "image_url", "image_url": {"url": f"data:{img['media_type']};base64,{img['data']}"}})

    observation_text = OBSERVATION_PROMPT_PL if lang == 'pl' else OBSERVATION_PROMPT_EN
    if validation_context:
        ctx_lines = ["[KONTEKST PRE-WALIDACJI]:" if lang == 'pl' else "[PRE-VALIDATION CONTEXT]:"]
        hp = validation_context.get('head_pose', {})
        if hp:
            ctx_lines.append(f"  Kąt głowy: yaw={hp.get('yaw','?')} pitch={hp.get('pitch','?')}")
        if not validation_context.get('neck_visible', True):
            ctx_lines.append("  Szyja niewidoczna w kadrze" if lang == 'pl' else "  Neck not visible in frame")
        if not validation_context.get('hairline_visible', True):
            ctx_lines.append("  Linia włosów niewidoczna" if lang == 'pl' else "  Hairline not visible in frame")
        observation_text = "\n".join(ctx_lines) + "\n\n" + observation_text

    user_content.append({"type": "text", "text": observation_text})
    system_msg = (
        "Jesteś specjalistą od estetycznej analizy twarzy. Wypełnij formularz oceny na podstawie tego, co widzisz na zdjęciu. Bądź konkretny i szczery zarówno co do mocnych stron, jak i obszarów do poprawy. Odpowiadaj WYŁĄCZNIE po polsku."
        if lang == 'pl' else
        "You are an aesthetic face analysis specialist. Fill in the assessment form based on what you see in the photo. Be specific and honest about both positive features and areas for improvement. Answer ONLY in English."
    )
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user",   "content": user_content},
    ]
    result = _call_raw(openai_client, messages, model, max_tokens=1500)
    print(f"[OBSERVE RAW] lang={lang} first_300={repr(result[:300])}", flush=True)
    return result


def _report(openai_client, observations: str, model: str, lang: str = 'pl') -> dict:
    treatments = ", ".join(TREATMENTS_PL if lang == 'pl' else TREATMENTS_EN)
    prompt_template = REPORT_PROMPT_PL if lang == 'pl' else REPORT_PROMPT_EN
    prompt = prompt_template.format(treatments=treatments)

    system_msg = (
        "Jesteś przyjaznym beauty-doradcą piszącym spersonalizowaną analizę twarzy dla pacjenta. "
        "Bądź ciepły, pozytywny i konkretny. Wszystkie teksty pisz WYŁĄCZNIE po polsku. Zwróć tylko poprawny JSON — bez markdown, bez dodatkowego tekstu."
        if lang == 'pl' else
        "You are a friendly beauty advisor writing a personalised face analysis for a patient. "
        "Be warm, positive, and specific. Write ALL text ONLY in English. Return only valid JSON — no markdown, no extra text."
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user",   "content": f"OBSERVATIONS:\n{observations}\n\n{prompt}"},
    ]
    for attempt in range(2):
        raw = _call_raw(openai_client, messages, model, max_tokens=2000)
        print(f"[REPORT RAW] attempt={attempt+1} lang={lang} first_500={repr(raw[:500])}", flush=True)
        try:
            parsed = _extract_json(raw)
            print(f"[REPORT PARSED] intro={repr(parsed.get('intro',''))} overall_score={parsed.get('overall_score')} areas={parsed.get('areas')}", flush=True)
            return parsed
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

    # overall_score: recompute as area average
    area_scores = [areas[k] for k in REQUIRED_AREAS]
    result['overall_score'] = max(1, min(10, int(round(sum(area_scores) / len(area_scores)))))

    # Log per-area scores for comparison across photos
    area_str = ' '.join(f"{k[:5]}={areas[k]}" for k in REQUIRED_AREAS)
    print(f"[SCORES] overall={result['overall_score']} | {area_str}")

    # intro: log what GPT returned; fallback ONLY if missing or too short
    intro = result.get('intro', '')
    print(f"[INTRO GPT] lang={lang} intro={repr(intro)}", flush=True)
    if not isinstance(intro, str) or len(intro.strip()) < 15:
        score = result['overall_score']
        if lang == 'pl':
            if score >= 8:
                result['intro'] = "Twoja twarz jest w naprawdę dobrej kondycji — masz piękne atuty, które warto pielęgnować."
            elif score >= 6:
                result['intro'] = "Masz ładne cechy twarzy — kilka ukierunkowanych zabiegów pomoże wydobyć je jeszcze bardziej."
            else:
                result['intro'] = "Warto zadbać o kilka obszarów — masz duży potencjał, który odpowiednie zabiegi mogą pięknie uwydatnić."
        else:
            if score >= 8:
                result['intro'] = "Your face is in really good shape — you have beautiful features worth maintaining."
            elif score >= 6:
                result['intro'] = "You have lovely facial features — a few targeted treatments will enhance them even further."
            else:
                result['intro'] = "There are a few areas worth addressing — you have great potential that the right treatments can beautifully enhance."
        print(f"[INTRO FALLBACK USED] score={score} intro={repr(result['intro'])}", flush=True)
    else:
        print(f"[INTRO GPT KEPT] intro={repr(intro)}", flush=True)

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
    observations = _observe(openai_client, images_data, model, validation_context=validation, lang=lang)
    print(f"[OBSERVE OK] lang={lang} {len(observations)} chars", flush=True)

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
