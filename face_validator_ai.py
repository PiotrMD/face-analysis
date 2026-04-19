"""
face_validator_ai.py
AI-based face photo validation module.

Runs BEFORE the main aesthetic analysis pipeline.
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

VALIDATION_PROMPT = """Assess this face photograph for aesthetic analysis suitability. Return ONLY a valid JSON object — no markdown, no explanation, no text outside the JSON.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOCKING CONDITIONS — set image_valid: false if ANY applies
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
B1. No human face present (photo of object, animal, document, landscape, etc.)
B2. More than one person visible in the photo
B3. ANY glasses present — sunglasses OR regular corrective glasses (glasses of any kind block orbital area assessment)
B4. Face is unrecognizable: completely dark, severely out of focus throughout, face features indistinguishable
B5. Head yaw above 45 degrees — clearly near-profile, one eye mostly hidden
B6. Strong beauty filter or clearly AI-generated face (plastic skin texture, airbrushed appearance)

NOT blocking — pass through with warnings:
- Black borders or letterboxing around the photo
- Partial hairline or chin slightly cut off
- Hairline not visible (cut by frame or black border)
- Chin slightly cut off
- Mild blur or lower resolution (webcam, screenshot)
- Slight smile, mild expression
- Arms crossed or slight pose variation
- Professional/clinic photos with standard crop
- Face smaller than ideal but still clearly visible
- Any standard portrait crop (chest-up, shoulders-up, face-only)

face_fully_visible: set to false ONLY when the face itself is severely cropped —
meaning more than 40% of the face area is outside the frame.
Do NOT set face_fully_visible: false for:
  - hairline cut off at top
  - chin cut off at bottom
  - black letterboxing borders
  - standard portrait framing
  - the person wearing a shirt or uniform that covers the neck

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WARNINGS (do not block, but set warning flags)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
W1. Head rotation 20–35 degrees — reduced confidence for symmetry/jawline
W2. Single-sided strong shadow — reduced confidence for volume
W3. Non-neutral expression (mild smile, slight tension)
W4. Neck not visible — cannot assess neck region
W5. Hairline not visible or cut off — cannot assess hairline
W6. Photo quality moderate (webcam, mild blur) — reduced skin texture confidence
W7. Black borders or letterboxing detected

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HEAD POSE ASSESSMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Estimate rotation in three axes based on facial landmarks:
  yaw (left/right rotation):  "minimal" <10° | "small" 10–20° | "moderate" 20–35° | "large" >35°
  pitch (up/down tilt):       "minimal" <10° | "small" 10–20° | "moderate" 20–35° | "large" >35°
  roll (side tilt):           "minimal" <5°  | "small" 5–12°  | "moderate" 12–20° | "large" >20°
  acceptable_for_analysis: false if yaw="large" OR pitch="large"

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
    'glasses':    'Wykryto okulary — zasłaniają obszar oczu niezbędny do analizy. Wgraj zdjęcie bez okularów.',
    'sunglasses': 'Wykryto okulary — zasłaniają obszar oczu niezbędny do analizy. Wgraj zdjęcie bez okularów.',
    'filter':     'Wykryto filtr upiększający lub retusz AI — analiza skóry i tkanek niemożliwa. Wgraj nieretuszowane zdjęcie.',
    'pose_large': 'Głowa jest zbyt mocno obrócona. Ustaw twarz prosto do aparatu i spróbuj ponownie.',
    'multi_face': 'Na zdjęciu widać więcej niż jedną osobę. Wgraj zdjęcie, na którym jesteś tylko Ty.',
    'no_face':    'Nie wykryto twarzy człowieka. Wgraj zdjęcie twarzy en face.',
    'cropped':    'Twarz jest ucięta — musi być widoczna cała twarz od linii włosów do podbródka.',
    'eyes':       'Oczy nie są widoczne lub są zasłonięte. Wgraj zdjęcie z widocznymi, otwartymi oczami.',
    'blurry':     'Zdjęcie jest zbyt niewyraźne do analizy. Zrób ostrzejsze zdjęcie w dobrym świetle.',
    'expression': 'Mimika nie jest neutralna. Wgraj zdjęcie z neutralnym wyrazem twarzy.',
    'default':    'Wgraj pojedyncze zdjęcie twarzy en face: twarz prosto do aparatu, oba oczy widoczne, bez okularów, bez filtrów.',
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
    if occlusion in ('sunglasses', 'glasses') or not r.get('eyes_visible', True):
        return REJECTION_MESSAGES['glasses']
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
                "You are a photo quality assessment system for aesthetic face analysis. "
                "Assess whether the photo is suitable for aesthetic evaluation. "
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

    # Log what GPT decided for each blocking field
    occlusion  = result.get('occlusion_type') or ''
    eyes_ok    = result.get('eyes_visible', True)
    filter_det = result.get('filter_detected', False)
    face_cnt   = result.get('face_count', 1)
    pose       = result.get('head_pose', {})
    print(f"[VALIDATE_AI] occlusion={occlusion!r} eyes={eyes_ok} filter={filter_det} "
          f"face_count={face_cnt} pose_yaw={pose.get('yaw')} "
          f"frontal={result.get('frontal_face')} sharpness={result.get('sharpness_ok')}")

    # Hard-block: glasses
    if occlusion in ('sunglasses', 'glasses') or not eyes_ok:
        print(f"[VALIDATE_AI] REJECT reason=glasses occlusion={occlusion!r} eyes_visible={eyes_ok}")
        raise ValueError(f"EYES_BLOCKED: {REJECTION_MESSAGES['glasses']}")
    # Hard-block: AI filter
    if filter_det:
        print("[VALIDATE_AI] REJECT reason=filter")
        raise ValueError(f"PHOTO_UNSUITABLE: {REJECTION_MESSAGES['filter']}")
    # Hard-block: no face
    if face_cnt == 0:
        print("[VALIDATE_AI] REJECT reason=no_face")
        raise ValueError(f"PHOTO_UNSUITABLE: {REJECTION_MESSAGES['no_face']}")
    # Hard-block: multiple faces (was missing before — B2 in prompt had no corresponding code block)
    if face_cnt > 1:
        print(f"[VALIDATE_AI] REJECT reason=multiple_faces face_count={face_cnt}")
        raise ValueError(f"PHOTO_UNSUITABLE: {REJECTION_MESSAGES['multi_face']}")

    # face_fully_visible=false is NEVER a hard block — log and continue
    if not result.get('face_fully_visible', True):
        print("[VALIDATE_AI] face_fully_visible=false — soft warning only, NOT blocking", flush=True)

    # Pose, lighting — pass with warnings logged
    warnings = result.get('warnings', [])
    if not result.get('lighting_ok', True):
        print("[VALIDATE_AI] WARNING low_light")
        warnings.append("Nierównomierne oświetlenie może obniżyć precyzję analizy skóry.")
    if not result.get('head_pose', {}).get('acceptable_for_analysis', True):
        yaw = result.get('head_pose', {}).get('yaw', '?')
        print(f"[VALIDATE_AI] WARNING bad_angle yaw={yaw}")
    print(f"[VALIDATE_AI] PASS face_fully_visible={result.get('face_fully_visible')} warnings={warnings}")
    return result
