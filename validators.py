import os
import json
import base64
from typing import Dict, Tuple, Optional
from werkzeug.datastructures import FileStorage


# Updated allowed extensions
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}


def validate_file_technical(files_dict: Dict[str, FileStorage]) -> Tuple[bool, Optional[str]]:
    """
    Validate files technically — single en_face only.
    Returns:
        (is_valid, error_message)
    """
    required_keys = {'en_face'}

    # Check if all required files are present
    provided_keys = set(k for k in files_dict.keys() if k in required_keys)
    missing = required_keys - provided_keys
    if missing:
        return False, f"Missing files: {', '.join(missing)}"

    # Validate each file
    for file_key in required_keys:
        file = files_dict[file_key]

        # Check if file is selected
        if file.filename == '':
            return False, f"File '{file_key}' is empty (no filename)"

        # Check file extension
        if '.' not in file.filename:
            return False, f"File '{file_key}' has no extension"

        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"File '{file_key}' has invalid extension '.{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

        # Check if file has content
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size == 0:
            return False, f"File '{file_key}' is empty (0 bytes)"

        if file_size > 16 * 1024 * 1024:  # 16MB
            return False, f"File '{file_key}' is too large (max 16MB)"

    return True, None


_STRICT_VALIDATION_PROMPT = """You are a medical photo intake validator. You receive 3 photos that should be:
- Photo 1 (en_face): one person, facing camera directly (frontal view)
- Photo 2 (profile_left): same person, left profile (ear visible on left, face pointing right)
- Photo 3 (profile_right): same person, right profile (ear visible on right, face pointing left)

Analyze all 3 photos and return ONLY a valid JSON object. No markdown. No explanation. No code fences.

{
  "en_face": {
    "face_detected": <true|false>,
    "face_count": <integer 0, 1, or 2+>,
    "pose": <"frontal"|"left_profile"|"right_profile"|"angled"|"unclear">,
    "quality": <"ok"|"blurred"|"too_dark"|"face_cut"|"obstructed"|"expression_issue"|"other">,
    "quality_note": "<empty string or 1-sentence note>"
  },
  "profile_left": {
    "face_detected": <true|false>,
    "face_count": <integer>,
    "pose": <"frontal"|"left_profile"|"right_profile"|"angled"|"unclear">,
    "quality": <"ok"|"blurred"|"too_dark"|"face_cut"|"obstructed"|"expression_issue"|"other">,
    "quality_note": "<empty string or 1-sentence note>"
  },
  "profile_right": {
    "face_detected": <true|false>,
    "face_count": <integer>,
    "pose": <"frontal"|"left_profile"|"right_profile"|"angled"|"unclear">,
    "quality": <"ok"|"blurred"|"too_dark"|"face_cut"|"obstructed"|"expression_issue"|"other">,
    "quality_note": "<empty string or 1-sentence note>"
  },
  "same_person": <true|false>,
  "same_person_confidence": <float 0.0 to 1.0>,
  "same_person_note": "<empty string or 1-sentence note>"
}

POSE RULES:
- frontal: face looking directly at camera, both eyes visible, symmetric
- left_profile: camera sees the person's LEFT side — left ear and cheek in foreground, nose tip pointing RIGHT in frame
- right_profile: camera sees the person's RIGHT side — right ear and cheek in foreground, nose tip pointing LEFT in frame
- angled: between frontal and profile, 30-75 degrees
- unclear: face present but orientation cannot be determined

QUALITY RULES:
- blurred: motion blur or out of focus making features indistinct
- too_dark: underexposed, face detail lost in shadow
- face_cut: chin, forehead, or sides of face cut off by frame edge
- obstructed: glasses, hair over face, mask, hand, or other object blocking significant area
- expression_issue: extreme grimace, eyes closed, mouth wide open preventing clinical assessment
- other: some other quality problem described in quality_note

SAME PERSON: compare facial bone structure, eye spacing, nose shape, ear shape across all 3 photos.
- same_person_confidence 0.9-1.0: almost certainly same person
- same_person_confidence 0.5-0.89: probably same person but uncertain
- same_person_confidence 0.0-0.49: likely different people
"""

_DISPLAY_NAMES = {
    'en_face':       'En Face',
    'profile_left':  'Profil Lewy',
    'profile_right': 'Profil Prawy',
}

_EXPECTED_POSES = {
    'en_face':       'frontal',
    'profile_left':  'left_profile',
    'profile_right': 'right_profile',
}

_QUALITY_MESSAGES_PL = {
    'blurred':          'Zdjęcie {} jest niewyraźne lub rozmyte. Wgraj ostrzejsze zdjęcie.',
    'too_dark':         'Zdjęcie {} jest zbyt ciemne do analizy. Zrób zdjęcie w lepszym oświetleniu.',
    'face_cut':         'Na zdjęciu {} twarz jest przycięta. Upewnij się, że cała twarz mieści się w kadrze.',
    'obstructed':       'Na zdjęciu {} twarz jest zasłonięta (włosy, okulary, maska). Usuń przeszkody i spróbuj ponownie.',
    'expression_issue': 'Na zdjęciu {} wyraz twarzy utrudnia analizę. Przyjmij naturalny, spokojny wyraz.',
}


def validate_same_person_embeddings(file_paths_dict: Dict[str, str]) -> Dict:
    """
    Real same-person check using deepface (Facenet, 128-d embeddings).
    Computes pairwise Euclidean distances between all 3 photos.
    Threshold: distance < 0.6 → same person, >= 0.6 → different person.
    Threshold is intentionally above deepface's frontal default (0.40) to
    accommodate frontal-vs-profile pose variance for the same identity.

    Returns:
        {
            is_valid: bool,
            error: str | None,      # Polish user-facing message on failure
            distances: dict,        # {pair_key: float} — always logged
        }
    """
    try:
        from deepface import DeepFace
        import numpy as np
    except ImportError:
        print("[EMBEDDING] deepface not installed — skipping same-person check")
        return {'is_valid': True, 'error': None, 'distances': {}}

    THRESHOLD = 0.6          # Euclidean on Facenet 128-d unit-sphere vectors
    MODEL     = 'Facenet'    # 128-d, good cross-pose recognition
    DETECTOR  = 'opencv'     # fastest; works for frontal and mild profile angles

    SLOT_DISPLAY = {
        'en_face':       'En Face',
        'profile_left':  'Profil Lewy',
        'profile_right': 'Profil Prawy',
    }

    encodings: Dict[str, object] = {}

    for key in ['en_face', 'profile_left', 'profile_right']:
        path = file_paths_dict.get(key)
        if not path:
            return {'is_valid': False,
                    'error': f'Brak ścieżki pliku: {key}.',
                    'distances': {}}

        try:
            reps = DeepFace.represent(
                img_path=path,
                model_name=MODEL,
                detector_backend=DETECTOR,
                enforce_detection=True,
            )
            if not reps:
                raise ValueError("no embedding returned")
            encodings[key] = np.array(reps[0]['embedding'])
            conf = reps[0].get('face_confidence', 'n/a')
            print(f"[EMBEDDING] {key}: encoded OK face_confidence={conf}")
        except Exception as e:
            print(f"[EMBEDDING] encoding failed for {key}: {str(e).encode('ascii', errors='replace').decode()}")
            return {
                'is_valid': False,
                'error': (f'Nie wykryto twarzy na zdjęciu {SLOT_DISPLAY[key]}. '
                          'Wgraj wyraźniejsze zdjęcie z widoczną twarzą.'),
                'distances': {}
            }

    pairs = [
        ('en_face', 'profile_left'),
        ('en_face', 'profile_right'),
        ('profile_left', 'profile_right'),
    ]

    distances: Dict[str, float] = {}
    failed: list = []

    for k1, k2 in pairs:
        # L2-normalize both vectors before distance so scale is 0–√2 (cosine distance)
        e1 = encodings[k1] / (np.linalg.norm(encodings[k1]) + 1e-10)
        e2 = encodings[k2] / (np.linalg.norm(encodings[k2]) + 1e-10)
        dist = float(np.linalg.norm(e1 - e2))
        pair_key = f'{k1}_vs_{k2}'
        distances[pair_key] = round(dist, 4)
        same = dist < THRESHOLD
        print(f"[EMBEDDING] {pair_key}: dist={dist:.4f} threshold={THRESHOLD} "
              f"same_person={'YES' if same else 'NO'}")
        if not same:
            failed.append(pair_key)

    if failed:
        print(f"[EMBEDDING] same_person_result=False failed_pairs={failed} distances={distances}")
        return {
            'is_valid': False,
            'error': ('Zdjęcia wyglądają na należące do różnych osób. '
                      'Wgraj 3 zdjęcia tej samej twarzy.'),
            'distances': distances,
        }

    print(f"[EMBEDDING] same_person_result=True distances={distances}")
    return {'is_valid': True, 'error': None, 'distances': distances}


def validate_photos_strict(
    file_paths_dict: Dict[str, str],
    openai_client,
    model: str = "gpt-4o"
) -> Dict:
    """
    Comprehensive single-call validation: face presence, correct pose, image quality,
    and same-person check across all 3 photos.

    Returns:
        {
            is_valid: bool,
            errors: list[str],        # blocking issues in Polish
            field_errors: dict,       # per-slot Polish error (for UI highlighting)
            warnings: list[str],      # non-blocking quality notes
            detected_views: dict,     # slot -> detected pose string
            same_person_confidence: float
        }
    """
    if openai_client is None:
        return {
            'is_valid': True, 'errors': [], 'field_errors': {},
            'warnings': [], 'detected_views': {}, 'same_person_confidence': 1.0
        }

    ext_to_mime = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp'}
    slot_labels = {
        'en_face':       'Zdjęcie 1 (en_face) — widok z przodu',
        'profile_left':  'Zdjęcie 2 (profile_left) — profil lewy',
        'profile_right': 'Zdjęcie 3 (profile_right) — profil prawy',
    }

    content = [{"type": "text", "text": _STRICT_VALIDATION_PROMPT}]
    for key in ['en_face', 'profile_left', 'profile_right']:
        path = file_paths_dict.get(key)
        if not path:
            continue
        with open(path, 'rb') as f:
            b64 = base64.standard_b64encode(f.read()).decode('utf-8')
        mime = ext_to_mime.get(path.rsplit('.', 1)[-1].lower(), 'image/jpeg')
        content.append({"type": "text", "text": slot_labels[key]})
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})

    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            max_tokens=700,
            temperature=0,
            response_format={"type": "json_object"}
        )
        raw = response.choices[0].message.content
        print(f"[STRICT VALIDATION RAW] {raw[:400]}")
        data = json.loads(raw)
    except Exception as e:
        print(f"[STRICT VALIDATION EXCEPTION] {e} — allowing analysis to continue")
        return {
            'is_valid': True, 'errors': [], 'field_errors': {},
            'warnings': [f'Walidacja wstępna niedostępna: {e}'],
            'detected_views': {}, 'same_person_confidence': 1.0
        }

    errors = []
    field_errors = {}
    warnings = []
    detected_views = {}

    for key in ['en_face', 'profile_left', 'profile_right']:
        img = data.get(key, {})
        name = _DISPLAY_NAMES[key]
        expected_pose = _EXPECTED_POSES[key]

        face_detected = img.get('face_detected', False)
        face_count    = int(img.get('face_count', 0))
        pose          = img.get('pose', 'unclear')
        quality       = img.get('quality', 'ok')
        quality_note  = img.get('quality_note', '')
        detected_views[key] = pose

        print(f"[STRICT VALIDATION] {key}: face={face_detected} count={face_count} "
              f"pose={pose} quality={quality} note={quality_note!r}")

        # Face presence
        if not face_detected or face_count == 0:
            msg = f"Na zdjęciu {name} nie wykryto wyraźnej twarzy. Wgraj zdjęcie z widoczną twarzą skierowaną do aparatu."
            field_errors[key] = msg
            errors.append(msg)
            continue

        if face_count > 1:
            msg = f"Na zdjęciu {name} wykryto więcej niż jedną twarz. Wgraj zdjęcie z jedną osobą w kadrze."
            field_errors[key] = msg
            errors.append(msg)
            continue

        # Pose check
        if pose != expected_pose:
            pose_msgs = {
                'en_face':       f"Zdjęcie En Face nie wygląda jak widok z przodu. Ustaw twarz prosto do aparatu — oba oczy powinny być widoczne symetrycznie.",
                'profile_left':  f"Zdjęcie Profil Lewy nie wygląda jak lewy profil. Ustaw twarz bokiem — lewa strona twarzy powinna być skierowana do aparatu.",
                'profile_right': f"Zdjęcie Profil Prawy nie wygląda jak prawy profil. Ustaw twarz bokiem — prawa strona twarzy powinna być skierowana do aparatu.",
            }
            msg = pose_msgs[key]
            field_errors.setdefault(key, msg)
            errors.append(msg)

        # Quality check (blocking for severe issues)
        blocking_quality = {'blurred', 'too_dark', 'face_cut', 'obstructed', 'expression_issue'}
        if quality in blocking_quality:
            tmpl = _QUALITY_MESSAGES_PL.get(quality, f"Zdjęcie {name} ma problemy z jakością — {quality_note or quality}.")
            msg = tmpl.format(name)
            if key not in field_errors:
                field_errors[key] = msg
            errors.append(msg)
        elif quality == 'other' and quality_note:
            warnings.append(f"Zdjęcie {name}: {quality_note}")

    # Same-person check
    same_person            = data.get('same_person', True)
    same_person_confidence = float(data.get('same_person_confidence', 1.0))
    same_person_note       = data.get('same_person_note', '')

    print(f"[STRICT VALIDATION] same_person={same_person} confidence={same_person_confidence:.2f} note={same_person_note!r}")

    if not same_person or same_person_confidence < 0.5:
        msg = "Wgrane zdjęcia wyglądają na należące do różnych osób. Upewnij się, że wszystkie 3 zdjęcia przedstawiają tę samą osobę."
        errors.append(msg)

    return {
        'is_valid':                len(errors) == 0,
        'errors':                  errors,
        'field_errors':            field_errors,
        'warnings':                warnings,
        'detected_views':          detected_views,
        'same_person_confidence':  same_person_confidence,
    }


def validate_faces_with_ai(
    file_paths_dict: Dict[str, str],
    openai_client,
    model: str = "gpt-4o"
) -> Tuple[bool, Dict]:
    """
    Validate that each image contains exactly 1 human face using OpenAI Vision API.
    If openai_client is None, skip validation and return OK.

    Args:
        file_paths_dict: {'en_face': '/path/to/file', ...}
        openai_client: OpenAI client instance or None (for mock mode)
        model: Model to use (default gpt-4o)

    Returns:
        (is_valid, error_dict)
    """

    # If no OpenAI client, skip validation (mock mode)
    if openai_client is None:
        return True, {
            'valid': True,
            'issues': {
                'en_face': None,
                'profile_left': None,
                'profile_right': None
            }
        }

    issues = {
        'en_face': None,
        'profile_left': None,
        'profile_right': None
    }

    for key, file_path in file_paths_dict.items():
        try:
            # Read and encode image
            with open(file_path, 'rb') as f:
                image_data = base64.standard_b64encode(f.read()).decode('utf-8')

            # Determine media type
            ext = file_path.rsplit('.', 1)[1].lower()
            media_type_map = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'webp': 'image/webp'
            }
            media_type = media_type_map.get(ext, 'image/jpeg')

            # Call OpenAI Vision API
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Check if this image contains exactly 1 human face. Reply with ONLY one word: 'OK' if exactly 1 face, 'NO_FACE' if no face, or 'MULTIPLE_FACES' if more than 1 face."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=10
            )

            result = response.choices[0].message.content.strip().upper()

            if result == 'NO_FACE':
                issues[key] = "No human face detected in this image"
            elif result == 'MULTIPLE_FACES':
                issues[key] = "Multiple faces detected. Please provide an image with exactly 1 face"
            elif result != 'OK':
                issues[key] = f"Unexpected validation response: {result}"

        except Exception as e:
            issues[key] = f"Validation error: {str(e)}"

    # Check if there are any issues
    has_issues = any(v is not None for v in issues.values())

    return not has_issues, {
        'valid': not has_issues,
        'issues': issues
    }
