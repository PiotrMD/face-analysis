"""
face_identity_validator.py
OpenCV-based face photo validation — fast, no external API.

Checks: image readable, not too blurry, exactly one face of sufficient size.
Used as the first gate before AI validation (face_validator_ai.py).
"""

import cv2
import numpy as np


def _get_cascade():
    """Return OpenCV frontal-face cascade, loading once per process."""
    if not hasattr(_get_cascade, "_cc"):
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
    import numpy as _np

    try:
        f = files.get("en_face") if hasattr(files, "get") else None
        if not f:
            return {"is_valid": False, "errors": ["Wgraj jedno wyraźne zdjęcie twarzy en face."]}

        data = f.read()
        try:
            f.seek(0)
        except Exception:
            pass

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
            print(f"[VALIDATOR] REJECT reason=blur value={blur:.1f} threshold=8.0")
            return {"is_valid": False, "errors": ["Zdjęcie jest zbyt niewyraźne do analizy."]}

        cc = _get_cascade()
        if cc is None:
            print("[VALIDATOR] cascade unavailable — fail-open")
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
            print("[VALIDATOR] PASS reason=no_face_opencv — deferring to AI validator")
            return {"is_valid": True, "errors": []}

        if face_count > 1:
            areas = [fw * fh for (fx, fy, fw, fh) in faces]
            largest_idx = int(np.argmax(areas))
            largest_area = areas[largest_idx]
            second_area = sorted(areas, reverse=True)[1]
            ratio = second_area / largest_area
            print(f"[VALIDATOR] multi-face: second/largest={ratio:.2f} threshold=0.40")
            if ratio > 0.40:
                print(f"[VALIDATOR] REJECT reason=multi_face second_ratio={ratio:.2f}")
                return {"is_valid": False, "errors": ["Na zdjęciu wykryto więcej niż jedną twarz. Załącz zdjęcie przedstawiające wyłącznie Twoją twarz."]}
            faces = [faces[largest_idx]]
            print("[VALIDATOR] multi-face: kept largest, filtered false positive")

        fx, fy, fw, fh = faces[0]
        face_ratio = (fw * fh) / (w * h) if w * h > 0 else 0.0
        print(f"[VALIDATOR] en_face: face_ratio={face_ratio:.3f} threshold=0.008")

        if face_ratio < 0.008:
            print(f"[VALIDATOR] REJECT reason=face_too_small ratio={face_ratio:.3f}")
            return {"is_valid": False, "errors": ["Twarz powinna być wyraźnie widoczna. Zrób zdjęcie bliżej."]}

        print(f"[VALIDATOR] PASS blur={blur:.1f} face_ratio={face_ratio:.3f}")
        return {"is_valid": True, "errors": []}

    except Exception as e:
        print("VALIDATION ERROR:", str(e).encode("ascii", errors="replace").decode())
        return {"is_valid": False, "errors": ["Błąd walidacji zdjęcia."]}
