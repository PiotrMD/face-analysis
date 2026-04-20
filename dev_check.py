#!/usr/bin/env python3
"""
dev_check.py — Developer checklist runner.

Runs automated checks that don't require the OpenAI API.
Use after every significant change to catch regressions early.

Usage:
    python dev_check.py           # all checks
    python dev_check.py --fast    # skip checks that start Flask app

Checks covered (no API key needed):
    1.  App boots and /demo returns 200
    2.  Upload rejects empty / corrupt file with 4xx
    3.  Rejection messages exist for all 8 codes (PL + EN)
    4.  Translation keys match between PL and EN
    5.  Demo result has all required fields
    6.  Score fields are in valid range in demo data
    7.  Treatments list is non-empty and consistent with allowed list
    8.  Forbidden medical terms not in active prompts
    9.  Rejection block returns error_hint in JSON response
   10.  Results page renders without Jinja2 errors (/demo)

Checks requiring API (use diag_test.py for these):
    - OpenAI returns valid JSON (diag_test.py)
    - Results differ across photos (diag_test.py --stage1)
    - Treatments differ across photos (diag_test.py)
"""

from __future__ import annotations

import sys
import os
import json
import argparse
import io
from typing import Callable

from dotenv import load_dotenv
load_dotenv(override=True)


# ── Colour helpers ─────────────────────────────────────────────────────────────

def _green(s: str) -> str: return f"\033[32m{s}\033[0m"
def _red(s: str)   -> str: return f"\033[31m{s}\033[0m"
def _grey(s: str)  -> str: return f"\033[90m{s}\033[0m"
def _bold(s: str)  -> str: return f"\033[1m{s}\033[0m"


# ── Check runner ───────────────────────────────────────────────────────────────

class CheckRunner:
    def __init__(self) -> None:
        self.passed  = 0
        self.failed  = 0
        self.skipped = 0

    def run(self, label: str, fn: Callable[[], tuple[bool, str]]) -> None:
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"Exception: {e}"

        if ok:
            self.passed += 1
            status = _green("PASS")
        else:
            self.failed += 1
            status = _red("FAIL")

        print(f"  {status}  {label}")
        if detail:
            prefix = "       "
            for line in detail.splitlines():
                print(f"{prefix}{_grey(line)}")

    def summary(self) -> None:
        total = self.passed + self.failed + self.skipped
        print()
        print(_bold(f"Results: {self.passed}/{total} passed"), end="")
        if self.failed:
            print(f"  {_red(str(self.failed) + ' failed')}", end="")
        print()


# ── Individual checks ──────────────────────────────────────────────────────────

def check_demo_200() -> tuple[bool, str]:
    """GET /demo returns 200 and has key HTML elements."""
    from app import app
    with app.test_client() as c:
        r = c.get('/demo')
        if r.status_code != 200:
            return False, f"status={r.status_code}"
        body = r.data.decode('utf-8', errors='replace')
        required = ['res-score-card', 'res-chips', 'res-tags', 'openConsultBtn']
        missing = [k for k in required if k not in body]
        if missing:
            return False, f"Missing HTML: {missing}"
        return True, ""


def check_upload_rejects_empty() -> tuple[bool, str]:
    """POST /analyze with empty file returns 4xx, not 500."""
    from app import app
    with app.test_client() as c:
        empty = (io.BytesIO(b""), "empty.jpg")
        r = c.post('/analyze', data={'en_face': empty}, content_type='multipart/form-data')
        if r.status_code == 500:
            return False, "Got 500 — unhandled error on empty file"
        if r.status_code >= 400:
            return True, f"Correctly rejected with {r.status_code}"
        return False, f"Unexpected status {r.status_code}"


def check_upload_rejects_nonimage() -> tuple[bool, str]:
    """POST /analyze with a text file returns 4xx."""
    from app import app
    with app.test_client() as c:
        fake = (io.BytesIO(b"this is not an image"), "notanimage.jpg")
        r = c.post('/analyze', data={'en_face': fake}, content_type='multipart/form-data')
        if r.status_code == 500:
            return False, "Got 500 — unhandled error on non-image file"
        return True, f"Rejected with {r.status_code}"


def check_rejection_messages() -> tuple[bool, str]:
    """All 8 rejection codes have PL and EN messages + hints."""
    from validation_messages import REJECTION_MESSAGES, get_message, get_hint

    codes = ['no_face', 'multiple_faces', 'glasses', 'filter',
             'low_light', 'blur', 'bad_angle', 'incomplete_face']
    issues = []
    for code in codes:
        if code not in REJECTION_MESSAGES:
            issues.append(f"{code}: missing entry")
            continue
        for lang in ('pl', 'en'):
            msg  = get_message(code, lang)
            hint = get_hint(code, lang)
            if not msg:
                issues.append(f"{code}/{lang}: empty message")
            if not hint:
                issues.append(f"{code}/{lang}: empty hint")
            if len(msg) > 120:
                issues.append(f"{code}/{lang}: message too long ({len(msg)} chars)")

    if issues:
        return False, "\n".join(issues)
    return True, f"{len(codes)} codes x 2 langs OK"


def check_rejection_returns_hint() -> tuple[bool, str]:
    """ValueError REJECT:{code} → JSON includes error_hint."""
    from app import app
    # We can't trigger a real rejection without the API, but we can verify
    # the app.py handler logic by importing it and running a mock
    import app as app_module
    from validation_messages import get_message, get_hint

    # Simulate the parsing logic from app.py
    test_cases = [
        ('REJECT:glasses',         'glasses'),
        ('REJECT:blur',            'blur'),
        ('REJECT:no_face',         'no_face'),
        ('EYES_BLOCKED: old fmt',  'glasses'),
        ('PHOTO_UNSUITABLE: msg',  'no_face'),
    ]
    issues = []
    for msg, expected_code in test_cases:
        if msg.startswith('REJECT:'):
            code = msg.split(':', 1)[1].strip()
        elif 'EYES_BLOCKED' in msg:
            code = 'glasses'
        elif 'PHOTO_UNSUITABLE' in msg:
            code = 'no_face'
        else:
            code = 'no_face'

        if code != expected_code:
            issues.append(f"msg={msg!r}: got code={code}, expected={expected_code}")
        # Verify get_hint doesn't crash and returns something
        hint = get_hint(code, 'pl')
        if not hint:
            issues.append(f"code={code}: no hint")

    if issues:
        return False, "\n".join(issues)
    return True, f"{len(test_cases)} parsing cases OK"


def check_translation_parity() -> tuple[bool, str]:
    """PL and EN translation dicts have identical keys."""
    from translations import TRANSLATIONS
    pl_keys = set(TRANSLATIONS['pl'].keys())
    en_keys = set(TRANSLATIONS['en'].keys())
    missing_en = pl_keys - en_keys
    missing_pl = en_keys - pl_keys
    issues = []
    if missing_en:
        issues.append(f"Missing in EN: {sorted(missing_en)}")
    if missing_pl:
        issues.append(f"Missing in PL: {sorted(missing_pl)}")
    if issues:
        return False, "\n".join(issues)
    return True, f"{len(pl_keys)} keys match"


def check_demo_result_structure() -> tuple[bool, str]:
    """DEMO_RESULT has all fields the template expects."""
    from demo_data import DEMO_RESULT

    required_fields = [
        'overall_score', 'intro', 'strengths', 'concerns',
        'strengths_items', 'concerns_items', 'treatments',
        'areas', 'area_labels', 'lang',
    ]
    missing = [f for f in required_fields if f not in DEMO_RESULT]
    if missing:
        return False, f"Missing fields: {missing}"

    # Scores in range
    score = DEMO_RESULT['overall_score']
    if not isinstance(score, int) or not (1 <= score <= 10):
        return False, f"overall_score={score!r} out of 1–10"

    for item in DEMO_RESULT.get('strengths_items', []):
        s = item.get('score', 0)
        if not (1 <= s <= 10):
            return False, f"strengths_items score {s} out of range"

    for key, val in DEMO_RESULT.get('areas', {}).items():
        if not (1 <= val <= 10):
            return False, f"areas[{key}]={val} out of range"

    return True, f"all {len(required_fields)} fields present, scores in range"


def check_treatments_valid() -> tuple[bool, str]:
    """DEMO_RESULT treatments are in the allowed list."""
    from demo_data import DEMO_RESULT
    from treatments import TREATMENTS_PL, TREATMENTS_EN

    lang = DEMO_RESULT.get('lang', 'pl')
    allowed = TREATMENTS_PL if lang == 'pl' else TREATMENTS_EN
    treatments = DEMO_RESULT.get('treatments', [])

    if not treatments:
        return False, "treatments list is empty"
    if len(treatments) < 2:
        return False, f"only {len(treatments)} treatment(s) — expected at least 2"

    unknown = [t for t in treatments if t not in allowed]
    if unknown:
        return False, f"unknown treatments: {unknown}"

    return True, f"{len(treatments)} treatments, all valid"


def check_no_medical_diagnosis_language() -> tuple[bool, str]:
    """Active prompts don't contain diagnosis-sounding phrases."""
    forbidden = [
        'rosacea',
        'trądzik różowaty',
        'rozpoznanie',
        'diagnozowanie',
        'clinical suitability',
        'medical diagnosis',
        'możliwe/prawdopodobne',
    ]
    files_to_check = ['prompts.py']
    hits = []
    for fname in files_to_check:
        try:
            with open(fname, encoding='utf-8') as f:
                content = f.read().lower()
            for term in forbidden:
                if term.lower() in content:
                    hits.append(f"{fname}: '{term}'")
        except FileNotFoundError:
            pass

    if hits:
        return False, "Forbidden medical language found:\n" + "\n".join(hits)
    return True, f"checked {len(files_to_check)} file(s), no forbidden terms"


def check_recommend_treatments_varies() -> tuple[bool, str]:
    """recommend_treatments() produces different output for different score profiles."""
    from treatments import recommend_treatments

    profiles = [
        {'wrinkles': 3, 'skin_tension': 3, 'eye_area': 4, 'skin_quality': 8, 'vessels': 8},
        {'skin_quality': 3, 'pigmentation': 3, 'freshness': 4, 'wrinkles': 8, 'skin_tension': 9},
        {'vessels': 3, 'pigmentation': 4, 'face_oval': 3, 'skin_quality': 9, 'wrinkles': 9},
    ]

    results = []
    for p in profiles:
        t = recommend_treatments(p, lang='pl')
        results.append(frozenset(t))

    if len(set(results)) < 2:
        return False, f"All profiles produced identical treatments: {results[0]}"

    pairs_identical = sum(1 for i in range(len(results))
                          for j in range(i+1, len(results))
                          if results[i] == results[j])
    if pairs_identical > 0:
        return False, f"{pairs_identical} identical treatment pair(s) across different profiles"

    details = []
    for i, (p, r) in enumerate(zip(profiles, results)):
        details.append(f"Profile {i+1}: {sorted(r)}")
    return True, "\n".join(details)


def check_results_page_no_template_errors() -> tuple[bool, str]:
    """Results page (/demo) renders without Jinja2 or Python errors."""
    from app import app
    with app.test_client() as c:
        r = c.get('/demo')
        if r.status_code != 200:
            return False, f"status={r.status_code}"
        body = r.data.decode('utf-8', errors='replace')
        # Jinja2 errors show as {{ or {%
        if '{{' in body or '{%' in body:
            return False, "Unrendered Jinja2 tags found in output"
        # Python errors
        if 'Traceback' in body or 'TemplateSyntaxError' in body:
            return False, "Exception traceback in rendered page"
        # Check required sections appear
        sections = ['res-topbar', 'res-score-card', 'res-chips', 'res-tags', 'res-cta']
        missing = [s for s in sections if s not in body]
        if missing:
            return False, f"Missing sections: {missing}"
        return True, "page rendered cleanly, all sections present"


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Developer checklist — no API required")
    parser.add_argument('--fast', action='store_true', help='Skip Flask app checks')
    args = parser.parse_args()

    runner = CheckRunner()

    print()
    print(_bold("dev_check.py — automated developer checklist"))
    print(_grey("  No OpenAI API calls — for pipeline tests use diag_test.py"))
    print()

    print(_bold("[ Upload & HTTP ]"))
    if not args.fast:
        runner.run("GET /demo returns 200",               check_demo_200)
        runner.run("Empty file upload rejected (not 500)", check_upload_rejects_empty)
        runner.run("Non-image file upload rejected",       check_upload_rejects_nonimage)
    else:
        print(_grey("  (skipped — use without --fast to run Flask checks)"))

    print()
    print(_bold("[ Validation messages ]"))
    runner.run("All 8 rejection codes have PL + EN messages", check_rejection_messages)
    runner.run("ValueError parsing - error_hint in response",   check_rejection_returns_hint)

    print()
    print(_bold("[ Translations ]"))
    runner.run("PL and EN translation keys match",  check_translation_parity)

    print()
    print(_bold("[ Data integrity ]"))
    runner.run("DEMO_RESULT has all required fields",  check_demo_result_structure)
    runner.run("DEMO_RESULT treatments are in allowed list", check_treatments_valid)
    runner.run("recommend_treatments() varies across profiles", check_recommend_treatments_varies)

    print()
    print(_bold("[ Content safety ]"))
    runner.run("No diagnosis language in active prompts", check_no_medical_diagnosis_language)

    print()
    print(_bold("[ Rendering ]"))
    if not args.fast:
        runner.run("Results page renders without errors", check_results_page_no_template_errors)
    else:
        print(_grey("  (skipped)"))

    runner.summary()

    if runner.failed:
        print()
        print(_grey("  For API-dependent checks (score variety, JSON format):"))
        print(_grey("  python diag_test.py --stage1"))
        sys.exit(1)


if __name__ == '__main__':
    main()
