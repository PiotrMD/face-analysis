"""
face_validator_ai.py
AI-based face photo validation module.

Runs BEFORE the main clinical analysis pipeline.
Uses GPT-4o vision to assess:
  1. Photo technical quality (sharpness, lighting, resolution)
  2. Face positioning and head pose (yaw / pitch / roll)
  3. Occlusions, filters, and mimics
  4. Overall facial impression (from approved label set)
  5. Facial harmony (structural, non-evaluative)

Returns structured JSON or raises ValueError with user-facing message.
"""
import json
import base64

VALIDATION_PROMPT = """Analyze this face photograph for clinical suitability. Return ONLY a valid JSON object — no markdown, no explanation, no text outside the JSON.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOCKING CONDITIONS — set image_valid: false if ANY applies
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
B1. More than one face visible in the photo
B2. Face not fully visible: hairline, eyes, nose, mouth, jawline must all be present
B3. Eyes covered by sunglasses, opaque glasses, hair, hand, or any occlusion
B4. Strong beauty filter, skin smoothing filter, or AI-generated appearance detected
B5. Head yaw (left-right rotation) estimated above 18 degrees
B6. Head pitched strongly down (looking at floor) — eyes barely or not visible
B7. Photo severely blurry (cannot assess skin or eye area), very dark, or badly overexposed
B8. Face occupies less than 20% of the image area
B9. Strong non-neutral expression: wide open smile showing teeth, strong squint, raised eyebrows, open mouth
B10. Partial face: chin or forehead cut off by frame

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WARNINGS (do not block, but set warning flags)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
W1. Mild head rotation (8–18 degrees yaw) — allow but note reduced confidence for symmetry/jawline
W2. Single-sided strong shadow — note reduced confidence for volume assessment
W3. Mild non-neutral expression (subtle smile, slight tension)
W4. Neck not visible in frame — cannot assess neck region
W5. Hairline not visible — cannot assess hairline/forehead region
W6. Corrective glasses present (non-sunglasses) — may partially obscure upper orbital rim

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HEAD POSE ASSESSMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Estimate rotation in three axes based on facial landmarks:
  yaw (left/right rotation):  "minimal" <5° | "small" 5–10° | "moderate" 10–18° | "large" >18°
  pitch (up/down tilt):       "minimal" <5° | "small" 5–10° | "moderate" 10–18° | "large" >18°
  roll (side tilt):           "minimal" <3° | "small" 3–8°  | "moderate" 8–15°  | "large" >15°
  acceptable_for_analysis: false if yaw="large" OR pitch="large" OR (yaw="moderate" AND roll="moderate")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OVERALL IMPRESSION — choose 1–2 labels from this list ONLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"świeży / wypoczęty" | "neutralny" | "zmęczony" | "napięty / zestresowany" | "smutny / przygaszony" | "surowy / poważny" | "łagodny / pogodny"

STRICT RULES:
- Do NOT default to "zmęczony" for every face. If the face looks rested or fresh → use "świeży / wypoczęty" or "neutralny"
- Each reason must name a SPECIFIC anatomical feature
- BAD reason: "twarz wygląda na zmęczoną"
- GOOD reason: "obciążona okolica podoczodołowa z cieniem tear trough"
- GOOD reason: "zachowana pełna objętość policzków i spokojna okolica oka — twarz wygląda świeżo"
- confidence must reflect actual photo quality — use "niska" if lighting is uneven or face is small

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HARMONY ASSESSMENT — structural, not aesthetic evaluation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
harmony.level: "wysoka" | "umiarkowana" | "obnizona"
harmony.notes: specific structural observations — NOT generic compliments

BAD notes: "good harmony", "nice proportions", "harmonious face"
GOOD notes:
  "Zachowana proporcja trzech pięter twarzy — czoło, środkowa i dolna część zbliżone do 1:1:1"
  "Wyraźna linia żuchwy bez cech opadania ani formowania się jowli"
  "Asymetria policzków — lewa strona nieznacznie bardziej spłaszczona"
  "Obciążona okolica oka zaburza spójność górnej i środkowej części twarzy"

Restrictions:
- Do NOT assess symmetry if yaw is "moderate" or "large"
- Do NOT comment on neck if neck is not visible
- Do NOT comment on hairline if it is not clearly visible
- If confidence is "niska" — do not make strong harmony conclusions

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RETURN THIS EXACT JSON STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "image_valid": <true|false>,
  "rejection_reason": <null or "Polish user-facing reason why photo is rejected">,
  "face_count": <integer>,
  "face_fully_visible": <true|false>,
  "frontal_face": <true|false>,
  "neutral_expression": <true|false>,
  "eyes_visible": <true|false>,
  "occlusion_detected": <true|false>,
  "occlusion_type": <null | "sunglasses" | "hair" | "hand" | "mask" | "filter" | "glasses" | "other">,
  "filter_detected": <true|false>,
  "lighting_ok": <true|false>,
  "sharpness_ok": <true|false>,
  "neck_visible": <true|false>,
  "hairline_visible": <true|false>,
  "warnings": ["<Polish warning string>"],
  "head_pose": {
    "yaw": "<minimal|small|moderate|large>",
    "pitch": "<minimal|small|moderate|large>",
    "roll": "<minimal|small|moderate|large>",
    "acceptable_for_analysis": <true|false>,
    "note": "<null or Polish note about pose limitation>"
  },
  "overall_impression": {
    "labels": ["<label from approved list>"],
    "confidence": "<wysoka|umiarkowana|niska>",
    "reasons": ["<anatomically specific Polish reason 1>", "<reason 2>"]
  },
  "harmony": {
    "level": "<wysoka|umiarkowana|obnizona>",
    "confidence": "<wysoka|umiarkowana|niska>",
    "notes": ["<specific structural Polish note 1>", "<note 2>"]
  }
}"""

REJECTION_MESSAGES = {
    'sunglasses': 'Wykryto okulary przeciwsłoneczne — zakrywają kluczowy obszar oczu. Wgraj zdjęcie bez okularów.',
    'filter':     'Wykryto filtr upiększający lub retusz AI — analiza skóry i tkanek niemożliwa. Wgraj nieretuszowane zdjęcie.',
    'pose_large': 'Głowa jest zbyt mocno obrócona lub pochylona. Ustaw twarz prosto do aparatu i spróbuj ponownie.',
    'multi_face': 'Na zdjęciu widać więcej niż jedną twarz. Wgraj zdjęcie, na którym jesteś tylko Ty.',
    'no_face':    'Nie wykryto twarzy. Upewnij się, że twarz jest wyraźnie widoczna i zajmuje znaczną część zdjęcia.',
    'cropped':    'Twarz jest ucięta — musi być widoczna cała twarz od linii włosów do podbródka.',
    'eyes':       'Oczy nie są widoczne lub są zasłonięte. Wgraj zdjęcie z widocznymi, otwartymi oczami.',
    'blurry':     'Zdjęcie jest zbyt niewyraźne do analizy. Zrób ostrzejsze zdjęcie w dobrym świetle.',
    'expression': 'Mimika nie jest neutralna. Wgraj zdjęcie z neutralnym wyrazem twarzy.',
    'default':    'Nie mogę wykonać wiarygodnej analizy. Proszę wgrać pojedyncze zdjęcie twarzy na wprost, patrząc prosto w aparat, z neutralną mimiką, bez filtrów, bez zasłonięcia twarzy, przy równym świetle i z dobrą ostrością.',
}

PHOTO_INSTRUCTIONS = 'Zrób pojedyncze zdjęcie twarzy na wprost, patrząc prosto w aparat, z neutralną mimiką, bez filtrów, bez okularów, z odsłoniętą twarzą i widoczną szyją, przy równym świetle, z dobrą ostrością.'


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
        raise ValueError(f"No JSON found in validation response: {repr(text[:300])}")
    return json.loads(text[start:end+1])


def _user_rejection_message(result: dict) -> str:
    """Pick the most appropriate user-facing rejection message."""
    r = result
    occlusion = r.get('occlusion_type') or ''
    if occlusion == 'sunglasses' or not r.get('eyes_visible', True):
        return REJECTION_MESSAGES['sunglasses']
    if r.get('filter_detected'):
        return REJECTION_MESSAGES['filter']
    if r.get('head_pose', {}).get('acceptable_for_analysis') is False:
        return REJECTION_MESSAGES['pose_large']
    if r.get('face_count', 1) > 1:
        return REJECTION_MESSAGES['multi_face']
    if r.get('face_count', 1) == 0:
        return REJECTION_MESSAGES['no_face']
    if not r.get('face_fully_visible', True):
        return REJECTION_MESSAGES['cropped']
    if not r.get('sharpness_ok', True):
        return REJECTION_MESSAGES['blurry']
    if not r.get('neutral_expression', True):
        return REJECTION_MESSAGES['expression']
    # Use AI-generated reason if available
    ai_reason = r.get('rejection_reason')
    if ai_reason and isinstance(ai_reason, str) and len(ai_reason) > 10:
        return ai_reason
    return REJECTION_MESSAGES['default']


def _normalize(result: dict) -> dict:
    """Normalize and fill in missing fields with safe defaults."""
    result.setdefault('image_valid', False)
    result.setdefault('face_count', 1)
    result.setdefault('face_fully_visible', True)
    result.setdefault('frontal_face', True)
    result.setdefault('neutral_expression', True)
    result.setdefault('eyes_visible', True)
    result.setdefault('occlusion_detected', False)
    result.setdefault('occlusion_type', None)
    result.setdefault('filter_detected', False)
    result.setdefault('lighting_ok', True)
    result.setdefault('sharpness_ok', True)
    result.setdefault('neck_visible', False)
    result.setdefault('hairline_visible', True)
    result.setdefault('warnings', [])

    # head_pose
    hp = result.get('head_pose')
    if not isinstance(hp, dict):
        result['head_pose'] = {
            'yaw': 'minimal', 'pitch': 'minimal', 'roll': 'minimal',
            'acceptable_for_analysis': True, 'note': None
        }
    else:
        valid_grades = {'minimal', 'small', 'moderate', 'large'}
        hp.setdefault('yaw',   'minimal')
        hp.setdefault('pitch', 'minimal')
        hp.setdefault('roll',  'minimal')
        if hp.get('yaw')   not in valid_grades: hp['yaw']   = 'minimal'
        if hp.get('pitch') not in valid_grades: hp['pitch'] = 'minimal'
        if hp.get('roll')  not in valid_grades: hp['roll']  = 'minimal'
        if not isinstance(hp.get('acceptable_for_analysis'), bool):
            hp['acceptable_for_analysis'] = hp.get('yaw') != 'large' and hp.get('pitch') != 'large'
        hp.setdefault('note', None)

    # overall_impression
    oi = result.get('overall_impression')
    valid_impressions = {'świeży / wypoczęty', 'neutralny', 'zmęczony', 'napięty / zestresowany',
                         'smutny / przygaszony', 'surowy / poważny', 'łagodny / pogodny'}
    valid_confidence  = {'wysoka', 'umiarkowana', 'niska'}
    if not isinstance(oi, dict):
        result['overall_impression'] = {'labels': ['neutralny'], 'confidence': 'niska', 'reasons': []}
    else:
        if not isinstance(oi.get('labels'), list):
            oi['labels'] = ['neutralny']
        else:
            oi['labels'] = [l for l in oi['labels'] if l in valid_impressions] or ['neutralny']
        if oi.get('confidence') not in valid_confidence:
            oi['confidence'] = 'umiarkowana'
        if not isinstance(oi.get('reasons'), list):
            oi['reasons'] = []

    # harmony
    harm = result.get('harmony')
    valid_harmony = {'wysoka', 'umiarkowana', 'obnizona'}
    if not isinstance(harm, dict):
        result['harmony'] = {'level': 'umiarkowana', 'confidence': 'niska', 'notes': []}
    else:
        if harm.get('level') not in valid_harmony:
            harm['level'] = 'umiarkowana'
        if harm.get('confidence') not in valid_confidence:
            harm['confidence'] = 'niska'
        if not isinstance(harm.get('notes'), list):
            harm['notes'] = []

    return result


def validate_face_ai(image_path: str, openai_client, model: str = "gpt-4o") -> dict:
    """
    AI-based face photo validation.

    Returns normalized validation dict on success.
    Raises ValueError with 'EYES_BLOCKED:' or 'PHOTO_UNSUITABLE:' prefix for app.py to handle.
    """
    with open(image_path, 'rb') as f:
        image_data = base64.standard_b64encode(f.read()).decode('utf-8')

    ext = image_path.rsplit('.', 1)[-1].lower()
    media_type = {
        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
        'png': 'image/png', 'webp': 'image/webp'
    }.get(ext, 'image/jpeg')

    messages = [
        {
            "role": "system",
            "content": (
                "You are a clinical photography quality assessment system. "
                "Analyze face photographs for analysis suitability. "
                "Return ONLY valid JSON — no markdown, no text outside the JSON. "
                "Be strict with blocking conditions but do not over-reject borderline cases."
            )
        },
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_data}"}},
                {"type": "text", "text": VALIDATION_PROMPT}
            ]
        }
    ]

    response = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=700,
        temperature=0.1,
    )

    raw = response.choices[0].message.content or ''
    print(f"[VALIDATE_AI] finish={response.choices[0].finish_reason} len={len(raw)}")

    try:
        result = _extract_json(raw)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[VALIDATE_AI] JSON parse error: {e} — raw: {repr(raw[:300])}")
        # Fail open: if we can't parse, let the main analysis try
        return _normalize({'image_valid': True, 'warnings': ['Walidacja AI niedostępna — analiza może mieć obniżoną pewność.']})

    result = _normalize(result)
    print(f"[VALIDATE_AI] valid={result['image_valid']} pose={result['head_pose']['yaw']} impression={result['overall_impression']['labels']}")

    if not result['image_valid']:
        msg = _user_rejection_message(result)
        occlusion = result.get('occlusion_type') or ''
        if occlusion == 'sunglasses' or not result.get('eyes_visible', True):
            raise ValueError(f"EYES_BLOCKED: {msg}")
        if result.get('filter_detected'):
            raise ValueError(f"PHOTO_UNSUITABLE: {msg}")
        raise ValueError(f"PHOTO_UNSUITABLE: {msg}")

    if not result['head_pose'].get('acceptable_for_analysis', True):
        msg = REJECTION_MESSAGES['pose_large']
        raise ValueError(f"PHOTO_UNSUITABLE: {msg}")

    return result
