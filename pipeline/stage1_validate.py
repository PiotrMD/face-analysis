"""
Stage 1: Photo validation.

Returns a structured result dict:
{
    "accepted":       bool,
    "reject_reason":  str | None,   # one of the REJECT_CODES below, or None
    "details": {
        "face_detected":    bool,
        "single_face":      bool,
        "glasses_detected": bool,
        "filter_suspected": bool,
        "too_dark":         bool,
        "too_blurry":       bool,
        "bad_angle":        bool,
        "face_incomplete":  bool,
    },
    "warnings":  list[str],   # non-blocking notes for logging
    "metadata":  dict,        # head_pose, neck_visible etc. passed to Stage 2
}

Rejection codes (reject_reason values):
    no_face | multiple_faces | glasses | filter | low_light | blur | bad_angle

    incomplete_face is NOT a rejection code — it is a warning-only flag.
    A photo passes even when face_fully_visible=false, as long as:
      - exactly one face detected
      - eyes visible
      - no glasses, no filter
      - acceptable quality

Thresholds:
    OpenCV blur:           Laplacian variance < 5.0
    OpenCV face too small: face_area / image_area < 0.002 → no_face (not incomplete_face)
    OpenCV multi-face:     second/largest > 0.40
    AI bad_angle:          only when head_pose.yaw="large" (>35°)
    AI low_light:          only when lighting_ok=false AND sharpness_ok=false together
    incomplete_face:       NEVER causes rejection — soft warning only

Never raises. Returns accepted=True on unexpected errors (fail-open).
"""

from __future__ import annotations

# Hard-reject codes only. incomplete_face is intentionally absent — it is warning-only.
_REJECT_PRIORITY = [
    'no_face',
    'multiple_faces',
    'glasses',
    'filter',
    'blur',
    'low_light',
    'bad_angle',
]

_EMPTY_DETAILS = {
    "face_detected":    True,
    "single_face":      True,
    "glasses_detected": False,
    "filter_suspected": False,
    "too_dark":         False,
    "too_blurry":       False,
    "bad_angle":        False,
    "face_incomplete":  False,
}


def run(image_path: str, openai_client, model: str = "gpt-4o") -> dict:
    details  = dict(_EMPTY_DETAILS)
    warnings: list[str] = []
    metadata: dict = {}

    # ── Gate 1: OpenCV ───────────────────────────────────────────────────────
    ocv = _opencv_gate(image_path)
    details.update(ocv["details"])
    warnings.extend(ocv["warnings"])

    if ocv["reject_reason"]:
        return _build(False, ocv["reject_reason"], details, warnings, metadata)

    # ── Gate 2: GPT-4o vision ────────────────────────────────────────────────
    if openai_client is None:
        print("[STAGE1] PASS (mock mode — no openai_client)", flush=True)
        return _build(True, None, details, warnings, metadata)

    ai = _ai_gate(image_path, openai_client, model)
    details.update(ai["details"])
    warnings.extend(ai["warnings"])
    metadata = ai["metadata"]

    if ai["reject_reason"]:
        return _build(False, ai["reject_reason"], details, warnings, metadata)

    print(f"[STAGE1] PASS details={_details_summary(details)}", flush=True)
    return _build(True, None, details, warnings, metadata)


# ── OpenCV gate ───────────────────────────────────────────────────────────────

def _opencv_gate(image_path: str) -> dict:
    details  = dict(_EMPTY_DETAILS)
    warnings: list[str] = []

    try:
        import cv2
        import numpy as np

        with open(image_path, "rb") as f:
            data = f.read()

        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            details["face_detected"] = False
            print("[STAGE1/opencv] REJECT unreadable_image", flush=True)
            return {"reject_reason": "no_face", "details": details, "warnings": warnings}

        h, w = img.shape[:2]
        if max(h, w) > 1200:
            scale = 1200 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            h, w = img.shape[:2]

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur_val = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        print(f"[STAGE1/opencv] size={w}x{h} blur={blur_val:.1f} threshold=5.0", flush=True)

        # Threshold lowered: 8.0 → 5.0 for more tolerance
        if blur_val < 5.0:
            details["too_blurry"] = True
            print(f"[STAGE1/opencv] REJECT blur={blur_val:.1f}", flush=True)
            return {"reject_reason": "blur", "details": details, "warnings": warnings}

        if blur_val < 15.0:
            warnings.append(f"Zdjęcie jest lekko niewyraźne (blur={blur_val:.0f}) — wyniki mogą być mniej precyzyjne.")

        from face_identity_validator import _get_cascade
        cc = _get_cascade()
        if cc is None:
            print("[STAGE1/opencv] cascade unavailable — skip face detection", flush=True)
            return {"reject_reason": None, "details": details, "warnings": warnings}

        eq = cv2.equalizeHist(gray)
        faces = cc.detectMultiScale(eq, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))
        if len(faces) == 0:
            faces = cc.detectMultiScale(eq, scaleFactor=1.2, minNeighbors=2, minSize=(30, 30))

        face_count = len(faces)
        print(f"[STAGE1/opencv] face_count={face_count}", flush=True)

        if face_count == 0:
            # Fail-open: OpenCV misses faces with makeup/lighting; defer to AI
            print("[STAGE1/opencv] no face detected by OpenCV — deferring to AI gate", flush=True)
            return {"reject_reason": None, "details": details, "warnings": warnings}

        if face_count > 1:
            areas   = [fw * fh for (_, _, fw, fh) in faces]
            largest = max(areas)
            second  = sorted(areas, reverse=True)[1]
            ratio   = second / largest
            # Also require second face to be meaningfully large in absolute terms
            # (door handles, knobs, background objects are small false positives)
            second_face_ratio = second / (w * h) if w * h > 0 else 0.0
            print(f"[STAGE1/opencv] multi_face second/largest={ratio:.2f} second_abs={second_face_ratio:.4f} threshold=0.55/0.01", flush=True)
            if ratio > 0.55 and second_face_ratio > 0.01:
                details["single_face"] = False
                print(f"[STAGE1/opencv] REJECT multiple_faces ratio={ratio:.2f}", flush=True)
                return {"reject_reason": "multiple_faces", "details": details, "warnings": warnings}
            faces = [faces[0]]  # keep largest

        fx, fy, fw, fh = faces[0]
        face_ratio = (fw * fh) / (w * h) if w * h > 0 else 0.0
        print(f"[STAGE1/opencv] face_ratio={face_ratio:.4f}", flush=True)
        if face_ratio < 0.002:
            # Face is extremely tiny — very likely not a portrait at all
            print(f"[STAGE1/opencv] REJECT face_too_small ratio={face_ratio:.4f}", flush=True)
            details["face_detected"] = False
            return {"reject_reason": "no_face", "details": details, "warnings": warnings}

        if face_ratio < 0.02:
            warnings.append("Twarz jest mała w kadrze — zrób zdjęcie bliżej dla lepszej analizy.")

        print(f"[STAGE1/opencv] PASS blur={blur_val:.1f} face_ratio={face_ratio:.4f}", flush=True)
        return {"reject_reason": None, "details": details, "warnings": warnings}

    except Exception as e:
        print(f"[STAGE1/opencv] error (fail-open): {e}", flush=True)
        return {"reject_reason": None, "details": details, "warnings": warnings}


# ── AI gate ───────────────────────────────────────────────────────────────────

def _ai_gate(image_path: str, openai_client, model: str) -> dict:
    details  = dict(_EMPTY_DETAILS)
    warnings: list[str] = []
    metadata: dict = {}

    try:
        from face_validator_ai import validate_face_ai
        val = validate_face_ai(image_path, openai_client, model)

        # Map AI result fields → details
        details["face_detected"]    = val.get("face_count", 1) > 0
        details["single_face"]      = val.get("face_count", 1) == 1
        details["glasses_detected"] = val.get("occlusion_type") in ("glasses", "sunglasses")
        details["filter_suspected"] = val.get("filter_detected", False)
        details["too_dark"]         = not val.get("lighting_ok", True)
        details["too_blurry"]       = not val.get("sharpness_ok", True)
        details["face_incomplete"]  = not val.get("face_fully_visible", True)

        hp = val.get("head_pose", {})
        details["bad_angle"] = not hp.get("acceptable_for_analysis", True)

        metadata = {
            "head_pose":          hp,
            "neck_visible":       val.get("neck_visible", True),
            "hairline_visible":   val.get("hairline_visible", True),
            "overall_impression": val.get("overall_impression", {}),
        }
        warnings.extend(val.get("warnings", []))

        # Determine reject_reason from details (priority order)
        reject_reason = _pick_reject_reason(details, val)
        if reject_reason:
            print(f"[STAGE1/ai] REJECT {reject_reason} details={_details_summary(details)}", flush=True)
        else:
            print(f"[STAGE1/ai] PASS details={_details_summary(details)}", flush=True)

        return {"reject_reason": reject_reason, "details": details, "warnings": warnings, "metadata": metadata}

    except ValueError as e:
        msg = str(e)
        # Map prefixed ValueError from face_validator_ai → reject_reason code
        if msg.startswith("EYES_BLOCKED:"):
            reason = "glasses"
            details["glasses_detected"] = True
        elif "multiple_faces" in msg.lower() or "więcej niż jedną" in msg:
            reason = "multiple_faces"
            details["single_face"] = False
        elif msg.startswith("PHOTO_UNSUITABLE:"):
            inner = msg[len("PHOTO_UNSUITABLE:"):].strip().lower()
            if "filtr" in inner or "filter" in inner:
                reason = "filter"
                details["filter_suspected"] = True
            elif "twarz" in inner or "face" in inner:
                reason = "no_face"
                details["face_detected"] = False
            else:
                reason = "no_face"
                details["face_detected"] = False
        else:
            reason = "no_face"
            details["face_detected"] = False

        print(f"[STAGE1/ai] REJECT {reason} from ValueError: {msg[:120]}", flush=True)
        return {"reject_reason": reason, "details": details, "warnings": warnings, "metadata": metadata}

    except Exception as e:
        print(f"[STAGE1/ai] error (fail-open): {e}", flush=True)
        return {"reject_reason": None, "details": details, "warnings": [f"Walidacja AI niedostępna."], "metadata": metadata}


def _pick_reject_reason(details: dict, val: dict) -> str | None:
    """
    Returns a reject_reason code or None (pass).

    HARD BLOCKS (always reject):
      no_face, multiple_faces, glasses, filter

    CONDITIONAL BLOCKS:
      low_light  — only when BOTH lighting_ok=false AND sharpness_ok=false
      bad_angle  — only when yaw="large" (>35°) AND acceptable_for_analysis=false

    NEVER BLOCKS (warning only):
      incomplete_face / face_fully_visible=false — a cropped hairline or chin
      is NOT a reason to reject. Photo passes as long as eyes are visible.

    This function CANNOT return "incomplete_face". That code is warning-only.
    """
    if not details.get("face_detected", True):
        return "no_face"
    if not details.get("single_face", True):
        return "multiple_faces"
    if details.get("glasses_detected"):
        return "glasses"
    if details.get("filter_suspected"):
        return "filter"

    # Low light: block only when BOTH signals agree
    if not val.get("lighting_ok", True) and not val.get("sharpness_ok", True):
        return "low_light"

    # Bad angle: block only for extreme yaw
    hp = val.get("head_pose", {})
    if hp.get("yaw") == "large" and not hp.get("acceptable_for_analysis", True):
        return "bad_angle"

    # face_fully_visible=false → add warning, never reject
    if not val.get("face_fully_visible", True):
        print("[STAGE1/ai] face_fully_visible=false — warning only, NOT rejecting", flush=True)

    return None


# ── Utilities ─────────────────────────────────────────────────────────────────

def _build(accepted: bool, reject_reason: str | None, details: dict, warnings: list, metadata: dict) -> dict:
    if not accepted and reject_reason:
        from validation_messages import get_message, get_hint
        # Log for debugging
        print(
            f"[STAGE1] FINAL reject_reason={reject_reason!r} "
            f"msg_pl={get_message(reject_reason, 'pl')!r}",
            flush=True,
        )
    return {
        "accepted":      accepted,
        "reject_reason": reject_reason,
        "details":       details,
        "warnings":      warnings,
        "metadata":      metadata,
    }


def _details_summary(details: dict) -> str:
    flags = [k for k, v in details.items() if v is False or (isinstance(v, bool) and not v)]
    issues = [k for k, v in details.items() if v is True and k not in ("face_detected", "single_face")]
    return f"ok={[k for k,v in details.items() if v is True and k in ('face_detected','single_face')]} issues={issues}"
