"""
Centralized validation rejection messages — PL and EN.

Each rejection reason has:
  - 'pl': Polish user-facing message
  - 'en': English user-facing message
  - 'hint_pl': optional short hint what to fix
  - 'hint_en': optional short hint what to fix
"""

REJECTION_MESSAGES = {
    'no_face': {
        'pl':      'Nie wykryto twarzy na zdjęciu.',
        'en':      'No face detected in the photo.',
        'hint_pl': 'Zrób zdjęcie patrząc prosto w aparat — twarz musi być wyraźnie widoczna w kadrze.',
        'hint_en': 'Take a photo looking straight at the camera — your face must be clearly visible in the frame.',
    },
    'multiple_faces': {
        'pl':      'Na zdjęciu wykryto więcej niż jedną twarz.',
        'en':      'Multiple faces detected in the photo.',
        'hint_pl': 'Wgraj zdjęcie, na którym jesteś tylko Ty — bez innych osób w tle.',
        'hint_en': 'Upload a photo showing only your face — no other people in the background.',
    },
    'glasses': {
        'pl':      'Na zdjęciu wykryto okulary.',
        'en':      'Glasses were detected in the photo.',
        'hint_pl': 'Zdejmij okulary i wgraj zdjęcie ponownie.',
        'hint_en': 'Remove your glasses and upload the photo again.',
    },
    'filter': {
        'pl':      'Wykryto filtr upiększający lub retusz.',
        'en':      'A beauty filter or retouching was detected.',
        'hint_pl': 'Nie używaj filtrów ani retuszu — wgraj oryginalne, niemodyfikowane zdjęcie.',
        'hint_en': 'Do not use filters or retouching — upload an original, unmodified photo.',
    },
    'low_light': {
        'pl':      'Zdjęcie jest zbyt ciemne do analizy.',
        'en':      'The photo is too dark for analysis.',
        'hint_pl': 'Zrób jaśniejsze zdjęcie — stań przy oknie lub w dobrze oświetlonym miejscu.',
        'hint_en': 'Take a brighter photo — stand near a window or in a well-lit area.',
    },
    'blur': {
        'pl':      'Zdjęcie jest zbyt niewyraźne do analizy.',
        'en':      'The photo is too blurry for analysis.',
        'hint_pl': 'Zrób wyraźniejsze zdjęcie — trzymaj aparat nieruchomo i sprawdź ostrość przed wgraniem.',
        'hint_en': 'Take a sharper photo — keep your device still and check focus before uploading.',
    },
    'bad_angle': {
        'pl':      'Twarz jest zbyt mocno obrócona.',
        'en':      'The face is turned too far to the side.',
        'hint_pl': 'Ustaw twarz na wprost do aparatu — oba oczy muszą być wyraźnie widoczne.',
        'hint_en': 'Face the camera straight on — both eyes must be clearly visible.',
    },
    'incomplete_face': {
        'pl':      'Twarz nie jest w pełni widoczna na zdjęciu.',
        'en':      'The face is not fully visible in the photo.',
        'hint_pl': 'Pokaż całą twarz — od linii włosów po brodę — bez przycinania krawędzi.',
        'hint_en': 'Show your full face — from hairline to chin — without cropping the edges.',
    },
}

# Fallback for unknown reason codes
_FALLBACK = {
    'pl':      'Zdjęcie nie spełnia wymagań do analizy.',
    'en':      'The photo does not meet the requirements for analysis.',
    'hint_pl': 'Wgraj wyraźne zdjęcie twarzy en face bez okularów i filtrów.',
    'hint_en': 'Upload a clear en face photo without glasses or filters.',
}


def get_message(reason_code: str, lang: str = 'pl') -> str:
    """Main message for the given rejection reason."""
    entry = REJECTION_MESSAGES.get(reason_code, _FALLBACK)
    return entry.get(lang, entry.get('pl', _FALLBACK['pl']))


def get_hint(reason_code: str, lang: str = 'pl') -> str:
    """Short hint explaining what to fix."""
    entry = REJECTION_MESSAGES.get(reason_code, _FALLBACK)
    key = f'hint_{lang}'
    return entry.get(key, entry.get('hint_pl', _FALLBACK['hint_pl']))


def get_full(reason_code: str, lang: str = 'pl') -> str:
    """Message + hint combined into one user-facing string."""
    msg  = get_message(reason_code, lang)
    hint = get_hint(reason_code, lang)
    return f"{msg} {hint}"
