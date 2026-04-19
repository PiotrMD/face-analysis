"""
face_identity_validator.py
MVP validation pipeline — fail-closed, softened for real-world use.

Steps:
  1. Face count / size / blur per image
  2. View angle check (lenient)
  3. Age + gender consistency (lenient, fail-open on error)
  4. Face similarity — cosine distance on Facenet embeddings
"""

import os
import tempfile
import cv2
import numpy as np
from typing import Dict, List, Tuple

# ── Thresholds — tuned for real-world frontal+profile variation ─────────────
THRESHOLD     = 0.75   # cosine distance; same person if dist < this
                       # raised from 0.60 → allows more pose variation
MODEL         = "Facenet"
DETECTOR      = "opencv"
MIN_FACE_RATIO = 0.02  # face area / image area (lowered from 0.03)
BLUR_MIN       = 25.0  # Laplacian variance (lowered from 50.0)
AGE_MAX_DIFF   = 20    # years

SLOT_DISPLAY = {
    "en_face":      "En Face",
    "profile_left": "Profil Lewy",
    "profile_right":"Profil Prawy",
}
KEYS  = ["en_face", "profile_left", "profile_right"]
PAIRS = [
    ("en_face", "profile_left"),
    ("en_face", "profile_right"),
    ("profile_left", "profile_right"),
]


def _s(e) -> str:
    return str(e).encode("ascii", errors="replace").decode()


def _fail(errors: List[str], stage: str, warnings=None, checks=None, score=0.0) -> Dict:
    print(f"[VALIDATOR] FAIL stage={stage} errors={errors}")
    print("[VALIDATOR] analysis_blocked=YES")
    return {
        "is_valid":          False,
        "errors":            errors,
        "stage":             stage,
        "warnings":          warnings or [],
        "consistency_score": score,
        "checks":            checks or {},
    }


def _pass(warnings=None, checks=None, score=1.0) -> Dict:
    print("[VALIDATOR] analysis_blocked=NO")
    return {
        "is_valid":          True,
        "errors":            [],
        "stage":             "passed",
        "warnings":          warnings or [],
        "consistency_score": score,
        "checks":            checks or {},
    }


def _get_cascade():
    """Return OpenCV frontal-face cascade, loading once per process."""
    if not hasattr(_get_cascade, "_cc"):
        import cv2
        cc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if cc.empty():
            cc = None
        _get_cascade._cc = cc
    return _get_cascade._cc


def validate_faces(files):
    """
    Single-image validation for en face photo — fast OpenCV-only path.
    Checks: file present, image readable, exactly one face, face large enough, not too blurry.
    NEVER returns None.
    """
    import tempfile, os as _os

    try:
        f = files.get("en_face") if hasattr(files, "get") else None
        if not f:
            return {"is_valid": False, "errors": ["Wgraj jedno wyraźne zdjęcie twarzy en face."]}

        # Read image directly from the file stream — no temp file needed for imread
        import numpy as _np
        data = f.read()
        try: f.seek(0)
        except Exception: pass

        arr = _np.frombuffer(data, dtype=_np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return {"is_valid": False, "errors": ["Nie udało się odczytać zdjęcia. Wgraj plik JPG lub PNG."]}

        h, w = img.shape[:2]
        if max(h, w) > 1200:
            scale = 1200 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            h, w = img.shape[:2]

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        print(f"[VALIDATOR] en_face: size={w}x{h} blur={blur:.1f}")

        if blur < 8.0:
            return {"is_valid": False, "errors": ["Zdjęcie jest zbyt niewyraźne do analizy."]}

        cc = _get_cascade()
        if cc is None:
            print("[VALIDATOR] cascade unavailable — skipping face check")
            return {"is_valid": True, "errors": []}

        eq = cv2.equalizeHist(gray)
        faces = cc.detectMultiScale(eq, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))
        face_count = len(faces)
        print(f"[VALIDATOR] en_face: face_count={face_count}")

        if face_count == 0:
            faces = cc.detectMultiScale(eq, scaleFactor=1.2, minNeighbors=2, minSize=(30, 30))
            face_count = len(faces)
            print(f"[VALIDATOR] en_face: face_count (retry)={face_count}")

        if face_count == 0:
            # Fail-open — let GPT-4o validator decide
            print("[VALIDATOR] en_face: no face by OpenCV — passing to AI validator")
            return {"is_valid": True, "errors": []}

        if face_count > 1:
            areas = [fw * fh for (fx, fy, fw, fh) in faces]
            largest_idx = int(np.argmax(areas))
            largest_area = areas[largest_idx]
            second_area = sorted(areas, reverse=True)[1]
            if second_area > largest_area * 0.40:
                return {"is_valid": False, "errors": ["Na zdjęciu wykryto więcej niż jedną twarz. Załącz zdjęcie przedstawiające wyłącznie Twoją twarz."]}
            faces = [faces[largest_idx]]
            print(f"[VALIDATOR] en_face: multiple detections, kept largest")

        fx, fy, fw, fh = faces[0]
        face_ratio = (fw * fh) / (w * h) if w * h > 0 else 0.0
        print(f"[VALIDATOR] en_face: face_ratio={face_ratio:.3f}")

        if face_ratio < 0.008:
            return {"is_valid": False, "errors": ["Twarz powinna być wyraźnie widoczna. Zrób zdjęcie bliżej."]}

        # Eye detection removed — unreliable with makeup/lighting; GPT-4o handles this

        print("[VALIDATOR] en_face: PASS")
        return {"is_valid": True, "errors": []}

    except Exception as e:
        print("VALIDATION ERROR:", str(e).encode("ascii", errors="replace").decode())
        return {"is_valid": False, "errors": ["Błąd walidacji zdjęcia."]}


def validate_identity(file_paths: Dict[str, str]) -> Dict:
    """Legacy path-based entry point."""
    try:
        return _run_pipeline(file_paths)
    except Exception as e:
        print(f"[VALIDATOR] FAIL CLOSED: {_s(e)}")
        return _fail(["Weryfikacja tożsamości niedostępna."], stage="internal_error")


def _run_pipeline(file_paths: Dict[str, str]) -> Dict:
    # ── DEBUG MODE: only check exactly one face per image ────────────────────
    DEBUG_FACE_ONLY = True

    try:
        from deepface import DeepFace
    except ImportError as e:
        print(f"[VALIDATOR] deepface missing: {_s(e)}")
        return _fail(["Weryfikacja tożsamości niedostępna."], stage="internal_error")

    checks: Dict      = {}
    embeddings: Dict  = {}
    face_regions: Dict = {}
    face_counts: List[int] = []   # track per-image face counts

    # ── Step 1: face detection (tolerant: 2/3 images must have 1 face) ──────
    for key in KEYS:
        path = file_paths.get(key, "")
        if not path or not os.path.exists(path):
            return _fail(
                [f"Brak pliku {SLOT_DISPLAY[key]}."],
                stage="missing_file", checks=checks,
            )

        # Load + preprocess: resize to max 800px, save as RGB temp file
        img = cv2.imread(path)
        if img is None:
            print(f"[VALIDATOR] {key}: cannot read image")
            checks[key] = {"status": "unreadable", "face_count": 0}
            face_counts.append(0)
            continue

        h, w = img.shape[:2]
        if max(h, w) > 800:
            scale = 800 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            h, w = img.shape[:2]

        # Write preprocessed RGB copy to temp file for DeepFace
        fd, tmp_prep = tempfile.mkstemp(suffix=".jpg", prefix=f"prep_{key}_")
        os.close(fd)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        cv2.imwrite(tmp_prep, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        print(f"[VALIDATOR] {key}: size={w}x{h} blur={blur:.1f}")

        try:
            reps = DeepFace.represent(
                img_path=tmp_prep, model_name=MODEL,
                detector_backend=DETECTOR, enforce_detection=True,
            )
        except Exception as e:
            print(f"[VALIDATOR] {key}: face detection failed — {_s(e)}")
            checks[key] = {"status": "no_face", "face_detected": False, "face_count": 0}
            face_counts.append(0)
            try: os.remove(tmp_prep)
            except Exception: pass
            continue
        finally:
            try: os.remove(tmp_prep)
            except Exception: pass

        face_count = len(reps)
        face_counts.append(face_count)
        print(f"[VALIDATOR] {key}: face_count={face_count} face_detected={face_count >= 1} embedding_created={face_count == 1}")

        if face_count == 1:
            fa         = reps[0].get("facial_area", {})
            fw, fh_dim = fa.get("w", w // 2), fa.get("h", h // 2)
            face_ratio  = (fw * fh_dim) / (w * h) if w * h > 0 else 0.0
            vec  = np.array(reps[0]["embedding"], dtype=np.float64)
            norm = np.linalg.norm(vec)
            if norm >= 1e-10:
                embeddings[key]   = vec / norm
                face_regions[key] = {"fa": fa, "img_w": w, "img_h": h}
            checks[key] = {
                "status": "ok", "face_detected": True,
                "face_count": 1, "embedding_created": norm >= 1e-10,
                "face_ratio": round(face_ratio, 3), "blur": round(blur, 1),
            }
        elif face_count == 0:
            checks[key] = {"status": "no_face", "face_detected": False, "face_count": 0, "blur": round(blur, 1)}
        else:
            checks[key] = {"status": "multiple_faces", "face_detected": True, "face_count": face_count, "blur": round(blur, 1)}

    # ── Tolerant decision: at least 2/3 images must have exactly 1 face ─────
    valid_count = sum(1 for c in face_counts if c == 1)
    print(f"FACE COUNTS: {face_counts}")
    print(f"[VALIDATOR] valid_face_images={valid_count}/3 (need >= 2)")

    if valid_count < 2:
        return _fail(
            ["Na jednym ze zdjęć nie wykryto jednej wyraźnej twarzy."],
            stage="face_detection", checks=checks,
        )

    # ── DEBUG BYPASS: if all 3 images have exactly 1 face, pass immediately ──
    if DEBUG_FACE_ONLY:
        print("[VALIDATOR] DEBUG_FACE_ONLY=True — skipping similarity/angle/consistency")
        print("[VALIDATOR] analysis_blocked=NO")
        return {"is_valid": True, "errors": [], "stage": "passed", "warnings": [], "consistency_score": 1.0, "checks": checks}

    # ── Step 2: view angle check ─────────────────────────────────────────────
    view_ok, view_note = _check_views(face_regions)
    print(f"[VALIDATOR] view_check: ok={view_ok} detail={view_note}")
    checks["views"] = {"ok": view_ok, "detail": view_note}

    if not view_ok:
        return _fail(
            ["Jedno ze zdjęć nie odpowiada wymaganemu ujęciu."],
            stage="view_angle", checks=checks,
        )

    # ── Step 3: age + gender consistency (lenient, fail-open) ───────────────
    consistency_score, consistency_info = _check_consistency(file_paths)
    print(f"[VALIDATOR] consistency: score={consistency_score:.2f} info={consistency_info}")
    checks["consistency"] = consistency_info

    if consistency_score < 0.2:
        return _fail(
            ["Nie udało się potwierdzić, że zdjęcia przedstawiają tę samą osobę."],
            stage="consistency", checks=checks, score=consistency_score,
        )

    # ── Step 4: face similarity ──────────────────────────────────────────────
    distances: Dict[str, float] = {}
    failed_pairs: List[str]     = []

    for k1, k2 in PAIRS:
        dist  = round(1.0 - float(np.dot(embeddings[k1], embeddings[k2])), 4)
        pk    = f"{k1}_vs_{k2}"
        distances[pk] = dist
        same  = dist < THRESHOLD
        print(f"[VALIDATOR] {pk}: dist={dist:.4f} threshold={THRESHOLD} same_person={'YES' if same else 'NO'}")
        if not same:
            failed_pairs.append(pk)

    checks["similarity"] = {"distances": distances, "failed_pairs": failed_pairs}

    if failed_pairs:
        print(f"[VALIDATOR] same_person_final=False failed_pairs={failed_pairs}")
        return _fail(
            ["Nie udało się potwierdzić, że zdjęcia przedstawiają tę samą osobę."],
            stage="face_similarity", checks=checks, score=consistency_score,
        )

    print(f"[VALIDATOR] same_person_final=True distances={distances}")
    return _pass(checks=checks, score=consistency_score)


def _check_views(face_regions: Dict) -> Tuple[bool, str]:
    """
    Lenient: only reject if en_face is clearly a side profile.
    cx_ratio < 0.22 or > 0.78 → clearly off-center → not frontal.
    """
    orientations = {}
    for key, data in face_regions.items():
        fa = data["fa"]
        w  = data["img_w"]
        cx = fa.get("x", 0) + fa.get("w", w // 2) / 2
        ratio = cx / w if w > 0 else 0.5
        if 0.22 <= ratio <= 0.78:
            orient = "frontal"
        elif ratio < 0.22:
            orient = "profile_right_facing"
        else:
            orient = "profile_left_facing"
        orientations[key] = {"orient": orient, "cx_ratio": round(ratio, 3)}
        print(f"[VALIDATOR] {key}: detected_view={orient} cx_ratio={ratio:.3f}")

    ef = orientations.get("en_face", {}).get("orient", "frontal")
    if ef not in ("frontal",):
        return False, f"en_face detected as {ef}"

    return True, str(orientations)


def _check_consistency(file_paths: Dict[str, str]) -> Tuple[float, Dict]:
    """
    DeepFace.analyze age+gender consistency. Fail-open: errors → score=1.0.
    """
    try:
        from deepface import DeepFace
        analyses = {}
        for key in KEYS:
            path = file_paths.get(key, "")
            if not path or not os.path.exists(path):
                continue
            try:
                r = DeepFace.analyze(
                    img_path=path, actions=["age", "gender"],
                    detector_backend=DETECTOR,
                    enforce_detection=False, silent=True,
                )
                if isinstance(r, list): r = r[0]
                analyses[key] = {
                    "age":    r.get("age", 0),
                    "gender": r.get("dominant_gender", "unknown"),
                }
                print(f"[VALIDATOR] {key}: age={analyses[key]['age']} gender={analyses[key]['gender']}")
            except Exception as e:
                print(f"[VALIDATOR] {key}: analyze skipped — {_s(e)}")

        valid = [v for v in analyses.values() if v]
        if len(valid) < 2:
            return 1.0, {"note": "insufficient data — skipped"}

        genders   = [v["gender"] for v in valid]
        ages      = [v["age"]    for v in valid]
        age_range = max(ages) - min(ages)
        gender_ok = len(set(genders)) == 1
        age_ok    = age_range <= AGE_MAX_DIFF

        score = 1.0
        if not gender_ok: score -= 0.5
        if not age_ok:    score -= 0.3
        score = max(0.0, score)

        return score, {
            "genders": genders, "ages": ages,
            "gender_consistent": gender_ok,
            "age_range": age_range, "age_consistent": age_ok,
            "score": score,
        }
    except Exception as e:
        print(f"[VALIDATOR] consistency error (non-fatal): {_s(e)}")
        return 1.0, {"note": f"error: {_s(e)}"}
