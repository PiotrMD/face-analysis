import json
import base64
from typing import Dict

# ═══════════════════════════════════════════════════════════════════
# OBSERVATION PROMPT — Step 1: image → structured plain-text notes
# ═══════════════════════════════════════════════════════════════════
OBSERVATION_PROMPT = """You are an aesthetic medicine specialist completing a structured pre-consultation assessment. Your role is to observe accurately and describe findings in a balanced, constructive way — noting both what looks good and what can be improved. Fill in each field with what you actually observe.

RULE 1 — ACCURACY: Describe findings precisely with grade, location, and character.
RULE 2 — NO FABRICATION: If you cannot clearly see something, write: "CANNOT ASSESS — [reason]". Never invent.
RULE 3 — BALANCED TONE: Describe findings accurately but constructively. Use grades (1–5) for precision, but present them as information, not judgment. Every observation is an opportunity to understand the face better.
RULE 4 — STRENGTHS FIRST: Always note positive features first — good skin, full volume, sharp jawline, even tone, youthful proportions. These are as important as concerns.
RULE 5 — CONFIDENCE PER STEP: After each step, rate confidence: HIGH / MODERATE / LOW and give reason.
RULE 6 — WRINKLE GRADES: 1=barely visible | 2=clearly visible at rest | 3=moderate depth | 4=deep shadow | 5=very deep.
RULE 7 — BLACK BORDERS: Black/dark borders around the image are a display artifact. They do NOT affect photo quality. Assess the face in the center of the image normally.
RULE 8 — CANNOT ASSESS is a last resort: Use it ONLY when a specific anatomical area is physically not visible (e.g. neck out of frame). If the face is visible, assess it. Do NOT apply CANNOT ASSESS to the whole photo or to strengths.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 0 — PHOTO SUITABILITY CHECK (answer first, before any section)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Eyes visible (not covered by sunglasses/hair/occlusion): YES / NO
Face direction: EN FACE / TILTED / LOOKING DOWN / PROFILE
Photo quality: ADEQUATE / BLURRY / DARK / CROPPED
Mimics: NEUTRAL / SMILING / GRIMACING

If eyes are completely hidden by sunglasses or opaque object → write "EYES_BLOCKED: [cause]" and STOP.
If face is clearly in profile (one eye fully hidden, >35° yaw) → write "PHOTO_UNSUITABLE: face not en face — [direction]" and STOP.
If NO human face at all (photo of object, animal, landscape) → write "PHOTO_UNSUITABLE: no face detected" and STOP.
If face is totally unrecognizable (completely dark, completely out of focus) → write "PHOTO_UNSUITABLE: [reason]" and STOP.
Otherwise → write "PHOTO_OK" and continue. Black borders, letterboxing, mild blur, partial hairline, crossed arms — these are NOT reasons to stop or to write CANNOT ASSESS broadly.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — POSITIVE FEATURES (MANDATORY — do not skip, do not use CANNOT ASSESS here)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED: List at least 3 specific positive features visible in the face. If you can see the face, you MUST find positive features to document — every face has anatomical strengths.
Examples of acceptable observations:
- "Full malar volume bilaterally, no hollowing"
- "Sharp, clearly defined jawline without jowl formation"
- "Even skin tone, no visible pigmentation or redness"
- "No forehead lines visible at rest"
- "Good skin firmness in the cheek region"
- "Symmetric facial thirds, proportions well-balanced"
DO NOT write "CANNOT ASSESS" in this section. DO NOT write "good-looking face" or vague compliments. Only anatomically specific positives.
Confidence: HIGH / MODERATE / LOW — [reason]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — FOREHEAD AND GLABELLAR REGION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Horizontal forehead lines:
  - Number visible: [number or "none visible at rest"]
  - Grade (1–5): [grade]
  - Type: static (at rest) / dynamic only / both
  - Distribution: full-width / partial [location]
  - Skin texture between lines: smooth / rough / crepe-like

Glabellar lines ("11" between brows):
  - Present: YES / NO
  - Grade (1–5): [grade], Type: vertical / transverse / both, Static or dynamic

Confidence for this step: HIGH / MODERATE / LOW — [reason]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — EYE AREA (examine carefully — critical for fatigue assessment)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Crow's feet (lateral canthal lines):
  - Grade (1–5): [grade or "absent"]
  - Type: static / dynamic / both
  - Extent: outer corner only / extending onto cheek
  - Symmetry: symmetric / left worse / right worse

Upper eyelid / brow:
  - Hooding: none / mild / moderate / significant
  - Brow position: normal / descending / elevated
  - Upper eyelid skin laxity: none / mild / significant

Lower eyelid / tear trough:
  - Tear trough depth (Barton 1–4): [grade or "not visible"]
  - Shadow character: absent / vascular (bluish) / pigmentary (brownish) / volumetric (grey) / mixed
  - Infraorbital puffiness: absent / mild / moderate / marked
  - Lower eyelid skin: normal / fine lines / crepe texture / thinning
  - Left/right asymmetry: [describe or "symmetric"]

Overall periorbital impression: TIRED / RESTED / NEUTRAL — because: [specific anatomical reason]
Confidence for this step: HIGH / MODERATE / LOW — [reason]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — SKIN QUALITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
T-zone pores (forehead, nose):
  - Size: normal (<0.3mm) / enlarged (0.3–0.4mm) / significantly enlarged (>0.4mm)
  - Seborrhea: absent / mild / significant

Cheek skin texture:
  - Surface: smooth / mildly uneven / rough / irregular microrelief
  - Fine surface lines: absent / present [location + density]
  - Dehydration signs: absent / present

Skin tone:
  - Even / mildly uneven / significantly uneven

Pigmentation (list each separately):
  - Discoloration 1: location, size [mm], color [brown/grey/red], type [melasma/PIH/lentigo/vascular]
  - Additional: [or "none visible"]
  - Vascular changes: [location and extent or "absent"]

Confidence for this step: HIGH / MODERATE / LOW — [reason]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — VOLUME (separately from tension/sagging)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Malar/cheek volume: maintained / mild loss / moderate loss / significant loss
Submalar/buccal area: maintained / mild hollowing / moderate hollowing
Temple area: full / mild hollowing / significant hollowing
Midface overall assessment: [one sentence]

Confidence for this step: HIGH / MODERATE / LOW — [reason if LOW: e.g. "difficult lighting"]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — SKIN TENSION AND SAGGING (separately from volume)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cheek/malar descent: none / mild / moderate / significant
Nasolabial folds: Grade [1–4 Lemperle], symmetric / asymmetric [which worse]
Marionette lines: absent / Grade [1–4]
Jawline definition: sharp / mildly blurred / significantly blurred / jowl forming
Lower face overall tension: maintained / mildly reduced / significantly reduced

Confidence for this step: HIGH / MODERATE / LOW — [reason]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 7 — LOWER FACE AND LIPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Perioral vertical lines: absent / fine (gr 1–2) / moderate (gr 3) / deep (gr 4–5)
Oral commissures: level / descending [side]
Mental crease: absent / present [grade]
Upper lip volume: full / moderate / thin / very thin
Upper lip philtrum: clearly defined / blurred / flat
Lower lip ratio to upper: [describe]

Confidence for this step: HIGH / MODERATE / LOW — [reason]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 8 — NECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Neck visible in frame: YES / NO
If YES:
  - Skin quality vs face: same / worse / better
  - Firmness: tight / mild laxity / moderate laxity / significant laxity
  - Horizontal lines: absent / 1–2 fine / multiple moderate / deep
  - Platysma bands: visible / not visible
  - Submental area: well-defined / mild fullness / significant submental fat
If NO: "CANNOT ASSESS — neck not in frame"
Confidence: HIGH / MODERATE / LOW — [reason]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 9 — HAIR AND HAIRLINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Hairline visible: YES / NO
If YES:
  - Forehead height: low / medium / high
  - Hairline regularity: regular / irregular / receding
  - Temple density: full / mild thinning / notable thinning / significant thinning
  - Frontal zone density: full / mild thinning / notable thinning
If NO: "CANNOT ASSESS — not in frame"
Confidence: HIGH / MODERATE / LOW — [reason]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 10 — SYMMETRY AND PROPORTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Facial thirds ratio (forehead:midface:lower face): [describe]
Midline: straight / deviated [direction ~Xmm]
Notable asymmetries: [list each with location and magnitude, or "none significant"]
Aesthetic proportions overall: [one sentence]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 11 — SKIN LESIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Visible scars, raised lesions, atypical spots: [list each — location, size, morphology]
Use "image suggests" / "features consistent with" / "requires confirmation"
If none: "None identified in this photograph."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 12 — OVERALL IMPRESSION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dominant facial impression (choose 1–2 from this list only):
  "świeży / wypoczęty" | "zmęczony" | "neutralny" | "napięty / zestresowany" | "smutny / przygaszony" | "surowy / poważny" | "łagodny / pogodny"
State anatomical reason for chosen impression.
Estimated age range (with minimum ±4-year band): [XX–XX]
Confidence of age estimate: HIGH / MODERATE / LOW — [reason]
Aesthetic harmony: strong / moderate / limited — [specific reason]

REMINDER: Use "CANNOT ASSESS — [reason]" for anything not clearly visible. Document strengths as carefully as concerns."""


# ═══════════════════════════════════════════════════════════════════
# CLINICAL PROMPT — Step 2: observations → structured JSON
# ═══════════════════════════════════════════════════════════════════
CLINICAL_PROMPT = """You are a warm, knowledgeable aesthetic medicine physician preparing a personalised pre-consultation report for your patient. Your goal is to help them understand their unique facial features — what looks great, what can be gently improved, and what to focus on at their upcoming consultation. Tone: professional but encouraging, like a trusted expert speaking directly to the patient.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE — CRITICAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALL free-text values in the JSON MUST be in Polish (język polski).
Enum/code keys (nasilenie, priorytet, kategoria, status, freshness) stay as specified.
BAD: "Slight tissue descent" → GOOD: "Niewielkie opadanie tkanek"
BAD: "Mild laxity" → GOOD: "Łagodna wiotkość"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANTI-FABRICATION — ABSOLUTE RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You may ONLY document findings explicitly stated in the OBSERVATIONS below.
If observations say "CANNOT ASSESS" or do not mention a feature → write "ocena ograniczona — niewidoczne na zdjęciu".
NEVER invent wrinkles, pigmentation, volume loss, or any finding not in the observations.
NEVER assume a finding is present because it is "typical" for an age group.
A physician who invents findings is clinically dangerous.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANTI-MONOTONY — CRITICAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORBIDDEN: assigning "zmęczony" to every face regardless of observations.
FORBIDDEN: always skewing biological age estimate upward.
FORBIDDEN: writing about neck or hairline when observations say "CANNOT ASSESS".
FORBIDDEN: copying the same phrases across reports.
FORBIDDEN: using vague adjectives like "delikatne", "subtelne" for clearly significant findings.
FORBIDDEN: giving every patient the same overall_score (typical range 45–80, must reflect findings).
FORBIDDEN: giving every category a score of 7 — scores must span the actual 1–10 range.
REQUIRED: if the face looks rested, fresh, or young — document that clearly and positively.
REQUIRED: vary the vocabulary, emphasis, and tone based on the actual observations.
REQUIRED: if confidence is LOW for a feature, write so explicitly and avoid strong conclusions.
REQUIRED: every patient report must be distinguishable from other patients by specific details.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRENGTHS-FIRST APPROACH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"strengths" field: list 3–6 concrete positive observations from the photo.
Each item must name a specific anatomical structure and what is good about it.
BAD (too vague): "Dobra cera", "Ładna twarz", "Twarz wygląda zdrowo"
GOOD (anatomically specific):
  "Zachowana pełna objętość policzków — brak utraty tkanki malarnej"
  "Wyraźnie zarysowana linia żuchwy bez cech opadania ani formowania się jowli"
  "Równomierny koloryt skóry bez widocznych ognisk przebarwień"
  "Brak zmarszczek statycznych czoła w spoczynku — tylko wczesne dynamiczne"
  "Dobra gęstość włosów w strefie czołowej i skroniowej"
  "Zachowana definicja łuków jarzmowych"
  "Symetria strukturalna twarzy — brak istotnych asymetrii"
  "Dobrze zachowana objętość wargi górnej"
If observations clearly show NO concerns in a region → always add that region to strengths.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURES — 0–4 granular scoring
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For each of the 8 features, provide: score (0–4), confidence (wysoka|umiarkowana|niska), notes (Polish)
Score meaning: 0=brak (no concern), 1=łagodny, 2=umiarkowany, 3=zaawansowany, 4=nasilony (severe)
CONFIDENCE RULES:
  - Use "niska" when: part of face not visible, blurry, difficult lighting, CANNOT ASSESS in observations
  - Use "umiarkowana" when: partially visible or lighting complicates assessment
  - Use "wysoka" only when clearly visible with good lighting

Features:
  under_eye: combined score of tear trough depth + shadow intensity + puffiness
  midface_volume: malar/cheek volume preservation (0=full, 4=significant hollowing)
  tissue_descent: gravitational sagging of cheeks/lower face (0=none, 4=severe jowls)
  jawline_jowls: jawline sharpness (0=sharp/clean, 4=blurred with jowl formation)
  skin_texture: pores + surface quality + microrelief (0=excellent, 4=severe)
  skin_tone: evenness of color + pigmentation (0=even, 4=severely uneven)
  neck: neck skin + tension + lines (0=excellent, 4=significant — use niska confidence if not visible)
  hairline: hairline integrity + density (0=normal, 4=significant loss — use niska confidence if not visible)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BIOLOGICAL AGE ESTIMATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Format: "XX–XX lat — [specific visible sign driving estimate] — pewność: wysoka|umiarkowana|niska"
NEVER give a single year — always a range (minimum ±4 years).
NEVER cluster estimates in the 40–50 range by default.
If skin is very good and lines minimal → estimate may be 25–30 range.
If confidence is LOW → write that clearly: "pewność: niska — zdjęcie nie pozwala na wiarygodną ocenę"
Example: "32–38 lat — brak zmarszczek statycznych, pełna objętość policzków, drobne dynamiczne kurze łapki — pewność: umiarkowana"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOMINANT IMPRESSION — choose 1–2 from this list ONLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"świeży / wypoczęty" | "zmęczony" | "neutralny" | "napięty / zestresowany" | "smutny / przygaszony" | "surowy / poważny" | "łagodny / pogodny"
Choose strictly based on anatomical observations — not assumptions about age or gender.
If the face looks rested → use "świeży / wypoczęty" or "neutralny".
DO NOT default to "zmęczony" unless tear trough, volume loss, or skin laxity clearly create fatigue signs.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OVERALL_SCORE — composite clinical index 0–100
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reflects cumulative extent of documented findings. NOT attractiveness.
85–100: minimal findings — young/well-preserved, 0–1 domains with minor concerns
70–84: mild findings — 1–2 domains with concerns, no priority intervention
55–69: moderate findings — multiple documented conditions, 3–4 domains
40–54: significant findings — most domains have conditions requiring intervention
<40: extensive multi-domain findings

Calibration reference points:
  Score 91: 20–28 y/o, no lines at rest, excellent skin, full volume, sharp jawline
  Score 78: 30–37 y/o, grade 1–2 crow's feet, mild nasolabial folds, minor pore enlargement
  Score 64: 40–50 y/o, grade 2–3 forehead lines, moderate volume loss, skin laxity in 2–3 zones
  Score 49: 52–60 y/o, deep wrinkles multiple zones, notable volume loss, blurred jawline
  Score 34: 62+ y/o, grade 4–5 wrinkles, significant sagging, major volume loss

Calibrate HONESTLY. Do NOT cluster scores near 62. A young person with good skin should score 80+.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TONE AND LANGUAGE STANDARDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORBIDDEN vague phrases: "zbliżone do normy", "harmonijne", "wygląda naturalnie", "ogólnie dobra", "prawidłowy", "bez zastrzeżeń"
FORBIDDEN alarming language: "schorzenie", "wymaga natychmiastowej interwencji", "defekt będzie postępował"

Every finding MUST contain:
  1. ANATOMICAL LOCATION (exact structure)
  2. SPECIFIC OBSERVATION (what is seen, with grade/detail)

Use encouraging, informative language:
  Instead of "Obniżone napięcie skóry powoduje defekt" → "Skóra policzków wykazuje naturalne oznaki upływu czasu — warto omówić metody wzmacniające."
  Instead of "Utrata objętości stopień 2" → "Okolica policzków mogłaby zyskać na odświeżeniu objętości."
  For uncertainty: "obraz sugeruje", "cechy zgodne z", "warto ocenić podczas wizyty"

summary — exactly 3 sentences:
  Sentence 1: what looks GREAT — name the strongest visible asset
  Sentence 2: the one area that MOST deserves attention — described constructively
  Sentence 3: positive OUTLOOK — what the consultation will focus on and what improvement is possible

strongest_asset — enthusiastic sentence about the best-preserved feature.

top_priority — 1–2 sentences: name the area that would benefit most from treatment and what improvement is possible. Use language like "może zyskać", "warto rozważyć", "poprawa jest osiągalna" — NOT "bez interwencji defekt będzie postępował".

recommendations — 5–7 items, ordered by priority:
  Format: [CEL]: [METODA] [SZCZEGÓŁY]
  Focus on what is achievable and why it would help.
  GOOD: "Nawilżenie i ochrona skóry: mineralny SPF 50+ PA++++ codziennie — podstawa każdej dobrej pielęgnacji"
  GOOD: "Odświeżenie objętości policzków: kwas hialuronowy — naturalny efekt, subtelna poprawa"

sections — 7 domains, each:
  status: "good" = excellent, nothing to address | "mild" = worth monitoring / light treatment | "moderate" = would benefit from treatment
  finding: [anatomical structure] + [specific observation] — written constructively
  detail: 3–4 items with specific observations — include both positives and areas to address

category_scores (0–10 per domain):
  9–10: excellent — no concerns
  7–8: very good — minor observations only
  5–6: good — some areas worth addressing
  3–4: this domain would benefit from treatment
  1–2: this domain is the priority for consultation
  "good" status → score 7–10 | "mild" → 4–6 | "moderate" → 1–4

skin_tension — document SEPARATELY from volume:
  under_eye, cheeks, jawline, neck (or limitation note if neck not visible)
  wplyw_estetyczny for skin_tension findings MUST state impact on fatigue perception.

fatigue_factors — if face looks rested:
  primary: "brak dominujących cech zmęczenia"
  contributing: []
  explanation: [explain what gives a fresh/rested appearance]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT — return ONLY valid JSON, no markdown, no explanations
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{
  "overall_score": <integer 0–100>,
  "confidence_global": "<wysoka|umiarkowana|niska>",
  "dominant_impression": ["<impression1 from approved list>"],
  "strengths": [
    "<specific anatomical positive observation — Polish>",
    "<specific anatomical positive observation — Polish>",
    "<specific anatomical positive observation — Polish>"
  ],
  "features": {
    "under_eye":      {"score": <0–4>, "confidence": "<wysoka|umiarkowana|niska>", "notes": "<Polish>"},
    "midface_volume": {"score": <0–4>, "confidence": "<wysoka|umiarkowana|niska>", "notes": "<Polish>"},
    "tissue_descent": {"score": <0–4>, "confidence": "<wysoka|umiarkowana|niska>", "notes": "<Polish>"},
    "jawline_jowls":  {"score": <0–4>, "confidence": "<wysoka|umiarkowana|niska>", "notes": "<Polish>"},
    "skin_texture":   {"score": <0–4>, "confidence": "<wysoka|umiarkowana|niska>", "notes": "<Polish>"},
    "skin_tone":      {"score": <0–4>, "confidence": "<wysoka|umiarkowana|niska>", "notes": "<Polish>"},
    "neck":           {"score": <0–4>, "confidence": "<wysoka|umiarkowana|niska>", "notes": "<Polish>"},
    "hairline":       {"score": <0–4>, "confidence": "<wysoka|umiarkowana|niska>", "notes": "<Polish>"}
  },
  "summary": "<sentence 1: structural strength> <sentence 2: primary concern> <sentence 3: clinical outlook>",
  "biological_age_estimate": "<XX–XX lat — specific visible sign — pewność: wysoka|umiarkowana|niska>",
  "strongest_asset": "<anatomical structure + specific observation>",
  "top_priority": "<location + finding + consequence + progression>",
  "skin_health_note": "<one sentence in Polish: why skin quality improvement matters for this patient>",
  "recommendations": [
    "<WSKAZANIE: PROCEDURA DAWKA/CZĘSTOTLIWOŚĆ>",
    "<WSKAZANIE: PROCEDURA DAWKA/CZĘSTOTLIWOŚĆ>",
    "<WSKAZANIE: PROCEDURA DAWKA/CZĘSTOTLIWOŚĆ>",
    "<WSKAZANIE: PROCEDURA DAWKA/CZĘSTOTLIWOŚĆ>",
    "<WSKAZANIE: PROCEDURA DAWKA/CZĘSTOTLIWOŚĆ>"
  ],
  "category_scores": {
    "symmetry":        <integer 0–10>,
    "proportions":     <integer 0–10>,
    "aging_signs":     <integer 0–10>,
    "skin_quality":    <integer 0–10>,
    "eye_area":        <integer 0–10>,
    "lips_lower_face": <integer 0–10>,
    "hairline_hair":   <integer 0–10>
  },
  "key_findings": [
    {"section": "symmetry",        "finding": "<location + finding>", "status": "<good|mild|moderate>", "score": <0–10>},
    {"section": "proportions",     "finding": "<location + finding>", "status": "<good|mild|moderate>", "score": <0–10>},
    {"section": "aging_signs",     "finding": "<location + finding>", "status": "<good|mild|moderate>", "score": <0–10>},
    {"section": "skin_quality",    "finding": "<location + finding>", "status": "<good|mild|moderate>", "score": <0–10>},
    {"section": "eye_area",        "finding": "<location + finding>", "status": "<good|mild|moderate>", "score": <0–10>},
    {"section": "lips_lower_face", "finding": "<location + finding>", "status": "<good|mild|moderate>", "score": <0–10>},
    {"section": "hairline_hair",   "finding": "<location + finding>", "status": "<good|mild|moderate>", "score": <0–10>}
  ],
  "sections": {
    "symmetry":        {"status": "<good|mild|moderate>", "finding": "<structure + finding>", "detail": ["<loc + finding>", "<loc + finding>", "<loc + finding>"]},
    "proportions":     {"status": "<good|mild|moderate>", "finding": "<structure + finding>", "detail": ["<loc + finding>", "<loc + finding>", "<loc + finding>"]},
    "aging_signs":     {"status": "<good|mild|moderate>", "finding": "<structure + finding>", "detail": ["<loc + finding>", "<loc + finding>", "<loc + finding>"]},
    "skin_quality":    {"status": "<good|mild|moderate>", "finding": "<structure + finding>", "detail": ["<loc + finding>", "<loc + finding>", "<loc + finding>"]},
    "eye_area":        {"status": "<good|mild|moderate>", "finding": "<structure + finding>", "detail": ["<loc + finding>", "<loc + finding>", "<loc + finding>"]},
    "lips_lower_face": {"status": "<good|mild|moderate>", "finding": "<structure + finding>", "detail": ["<loc + finding>", "<loc + finding>", "<loc + finding>"]},
    "hairline_hair":   {"status": "<good|mild|moderate>", "finding": "<structure + finding>", "detail": ["<loc + finding>", "<loc + finding>", "<loc + finding>"]}
  },
  "overall_perception": {
    "freshness": "<wypoczęty|świeży|neutralny|poważny|napięty|zmęczony|przygnębiony>",
    "aesthetic_character": "<one Polish word: e.g. elegancki|wyrazisty|klasyczny|delikatny|surowy|ciepły|intensywny|spokojny|dynamiczny|naturalny>",
    "impression": "<one Polish sentence: what this face communicates aesthetically — cause + effect + perception>"
  },
  "fatigue_factors": {
    "primary": "<main anatomical factor creating tired appearance — or 'brak dominujących cech zmęczenia' if face looks rested>",
    "contributing": ["<Polish factor>", "<Polish factor>"],
    "explanation": "<one Polish sentence: cause → effect → perceived fatigue or freshness>"
  },
  "skin_tension": {
    "under_eye": "<Polish: tension/laxity + perceptual effect>",
    "cheeks": "<Polish: tension/tissue descent + perceptual effect>",
    "jawline": "<Polish: jawline definition or blurring>",
    "neck": "<Polish: finding — or 'Ocena szyi ograniczona przez kadr zdjęcia.' if not visible>"
  },
  "disclaimer": "Dokumentacja kliniczna sporządzona na podstawie fotografii. Nie zastępuje badania lekarskiego.",
  "findings": []
}"""


FINDINGS_EXTENSION = """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINDINGS — complete the "findings" array in the same JSON
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Include 5–10 findings. Mandatory: at least one eye_area entry, at least one skin_tension entry.
If neck is visible → include neck entry. If not visible → include one neck entry with nasilenie "brak" and note the frame limitation.

Each finding object:
{
  "id": "<unique_snake_case_id>",
  "name": "<finding name — Polish>",
  "area": "<anatomical location — Polish>",
  "kategoria": "<skin_quality|pigment_vascular|eye_area|volume_contour|forehead_hairline|lesions|neck|skin_tension>",
  "nasilenie": "<brak|lagodny|umiarkowany|zaawansowany>",
  "priorytet": "<wysoki|sredni|niski>",
  "wplyw_estetyczny": "<one Polish sentence: cause → effect → perception>",
  "kierunek_postepowania": ["<Polish procedure name>"],
  "wymaga_potwierdzenia": false,
  "dlaczego_wazne": "<one Polish sentence>",
  "co_moze_sie_poglebiac": "<one Polish sentence — progression without intervention>",
  "co_wdrozyc_najpierw": "<one Polish sentence — first step>"
}

Category definitions:
  skin_quality → pory, tekstura, nawilżenie skóry twarzy
  pigment_vascular → przebarwienia, naczynka, rumień
  eye_area → dolina łez, cienie, obrzęki, zmarszczki okolicy oczu — ALWAYS document tear trough depth, shadow character, fatigue impact
  volume_contour → objętość policzków, owal twarzy, linia żuchwy
  forehead_hairline → linia włosów, gęstość, czoło
  lesions → blizny, brodawki, włókniaki — ALWAYS wymaga_potwierdzenia: true; use "obraz sugeruje" / "cechy zgodne z"
  neck → skóra szyi, napięcie, zmarszczki — if not visible: nasilenie "brak", note frame limitation
  skin_tension → napięcie policzków, żuchwy, opadanie tkanek — wplyw_estetyczny MUST state fatigue impact

Treatment directions (kierunek_postepowania):
  skin_tension → RF mikroigłowa, mezoterapia, stymulatory tkankowe, osocze bogatopłytkowe (PRP), fibryna (PRF)
  pory/tekstura → peelingi chemiczne, laser frakcyjny, RF mikroigłowa
  przebarwienia → peelingi chemiczne, laser frakcyjny
  naczynka/rumień → laser naczyniowy
  eye_area/tear trough → fibryna bogatokomórkowa (PRF), łagodne stymulatory — NIGDY filler HA (ryzyko obrzęku)
  zmarszczki dynamiczne → toksyna botulinowa
  objętość policzków/owalu → filler HA, stymulatory tkankowe
  lesions → elektrokoagulacja
  szyja → RF mikroigłowa, mezoterapia, laser frakcyjny, stymulatory tkankowe"""


# Required fields for the complete output
REQUIRED_SECTIONS = [
    'symmetry', 'proportions', 'aging_signs',
    'skin_quality', 'eye_area', 'lips_lower_face', 'hairline_hair'
]
REQUIRED_SECTION_KEYS = {'status', 'finding', 'detail'}
VALID_STATUSES = {'good', 'mild', 'moderate'}
REQUIRED_TOP_FIELDS = [
    'overall_score', 'summary', 'biological_age_estimate',
    'strongest_asset', 'top_priority', 'recommendations',
    'category_scores', 'key_findings', 'sections', 'disclaimer'
]
VALID_CONFIDENCE = {'wysoka', 'umiarkowana', 'niska'}
VALID_FEATURES = {'under_eye', 'midface_volume', 'tissue_descent', 'jawline_jowls',
                  'skin_texture', 'skin_tone', 'neck', 'hairline'}
VALID_FRESHNESS = {'wypoczęty', 'świeży', 'neutralny', 'poważny', 'napięty', 'zmęczony', 'przygnębiony'}
VALID_IMPRESSION = {
    'świeży / wypoczęty', 'zmęczony', 'neutralny',
    'napięty / zestresowany', 'smutny / przygaszony', 'surowy / poważny', 'łagodny / pogodny'
}


def _validate_result(result: dict) -> None:
    # Core fields
    for field in REQUIRED_TOP_FIELDS:
        if field not in result:
            raise ValueError(f"Brak wymaganego pola: {field}")

    result['overall_score'] = int(round(float(result['overall_score'])))
    if not (0 <= result['overall_score'] <= 100):
        raise ValueError(f"overall_score poza zakresem: {result['overall_score']}")

    if not isinstance(result['recommendations'], list) or len(result['recommendations']) < 3:
        raise ValueError("recommendations musi być listą z co najmniej 3 elementami")

    # category_scores
    cat = result.get('category_scores', {})
    for sec_name in REQUIRED_SECTIONS:
        if sec_name not in cat:
            raise ValueError(f"Brak category_scores['{sec_name}']")
        result['category_scores'][sec_name] = int(round(float(cat[sec_name])))

    # key_findings — synthesize missing
    kf = result.get('key_findings', [])
    if not isinstance(kf, list):
        result['key_findings'] = []
        kf = []
    kf_sections = {item.get('section') for item in kf if isinstance(item, dict)}
    for sec_name in set(REQUIRED_SECTIONS) - kf_sections:
        sec = result.get('sections', {}).get(sec_name, {})
        result['key_findings'].append({
            'section': sec_name,
            'finding': sec.get('finding', '—'),
            'status': sec.get('status', 'mild'),
            'score': result.get('category_scores', {}).get(sec_name, 5),
        })

    # sections
    sections = result.get('sections', {})
    for section_name in REQUIRED_SECTIONS:
        if section_name not in sections:
            raise ValueError(f"Brak sekcji: {section_name}")
        sec = sections[section_name]
        missing = REQUIRED_SECTION_KEYS - set(sec.keys())
        if missing:
            raise ValueError(f"Sekcja '{section_name}' brakuje pól: {missing}")
        if sec['status'] not in VALID_STATUSES:
            raise ValueError(f"Sekcja '{section_name}' nieprawidłowy status: {sec['status']}")
        if not isinstance(sec.get('detail'), list):
            sec['detail'] = [sec.get('finding', '—')]

    # findings — normalize
    findings = result.get('findings')
    if isinstance(findings, list):
        valid_nasilenie = {'brak', 'lagodny', 'umiarkowany', 'zaawansowany'}
        valid_priorytet = {'wysoki', 'sredni', 'niski'}
        valid_kategoria = {'skin_quality', 'pigment_vascular', 'eye_area', 'volume_contour',
                           'forehead_hairline', 'lesions', 'neck', 'skin_tension'}
        cleaned = []
        for f in findings:
            if not isinstance(f, dict):
                continue
            if f.get('nasilenie') not in valid_nasilenie:
                f['nasilenie'] = 'lagodny'
            if f.get('priorytet') not in valid_priorytet:
                f['priorytet'] = 'sredni'
            if f.get('kategoria') not in valid_kategoria:
                f['kategoria'] = 'skin_quality'
            if not isinstance(f.get('kierunek_postepowania'), list):
                f['kierunek_postepowania'] = []
            if not isinstance(f.get('wymaga_potwierdzenia'), bool):
                f['wymaga_potwierdzenia'] = f.get('kategoria') == 'lesions'
            # Filter placeholder "ocena ograniczona" findings that have it in BOTH name and area
            name_lower = f.get('name', '').lower()
            area_lower = f.get('area', '').lower()
            if ('ocena ograniczona' in name_lower or 'cannot assess' in name_lower or 'assessment limited' in name_lower) and \
               ('ocena ograniczona' in area_lower or 'cannot assess' in area_lower or 'assessment limited' in area_lower):
                continue
            # Also filter kierunek_postepowania placeholder values
            kp = f.get('kierunek_postepowania', [])
            if isinstance(kp, list):
                f['kierunek_postepowania'] = [
                    tag for tag in kp
                    if isinstance(tag, str) and 'ocena ograniczona' not in tag.lower()
                       and 'cannot assess' not in tag.lower()
                ]
            cleaned.append(f)
        result['findings'] = cleaned

    # overall_perception — normalize
    op = result.get('overall_perception')
    if not isinstance(op, dict):
        result['overall_perception'] = None
    else:
        if op.get('freshness') not in VALID_FRESHNESS:
            op['freshness'] = 'neutralny'

    # fatigue_factors — normalize
    ff = result.get('fatigue_factors')
    if not isinstance(ff, dict):
        result['fatigue_factors'] = None
    else:
        if not isinstance(ff.get('contributing'), list):
            ff['contributing'] = []

    # skin_tension — normalize
    st = result.get('skin_tension')
    if not isinstance(st, dict):
        result['skin_tension'] = None

    # strengths — normalize (lenient)
    strengths = result.get('strengths')
    if not isinstance(strengths, list):
        result['strengths'] = []
    else:
        result['strengths'] = [s for s in strengths if isinstance(s, str) and s.strip()]

    # dominant_impression — normalize
    di = result.get('dominant_impression')
    if not isinstance(di, list):
        result['dominant_impression'] = []

    # confidence_global — normalize
    if result.get('confidence_global') not in VALID_CONFIDENCE:
        result['confidence_global'] = 'umiarkowana'

    # features — normalize
    features = result.get('features')
    if not isinstance(features, dict):
        result['features'] = {}
        features = result['features']
    for feat_key in VALID_FEATURES:
        feat = features.get(feat_key)
        if not isinstance(feat, dict):
            features[feat_key] = {'score': 0, 'confidence': 'niska', 'notes': 'ocena ograniczona'}
        else:
            try:
                feat['score'] = max(0, min(4, int(round(float(feat.get('score', 0))))))
            except (ValueError, TypeError):
                feat['score'] = 0
            if feat.get('confidence') not in VALID_CONFIDENCE:
                feat['confidence'] = 'niska'
            if not isinstance(feat.get('notes'), str):
                feat['notes'] = ''


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


def _call_raw(openai_client, messages: list, model: str, max_tokens: int) -> str:
    response = openai_client.chat.completions.create(
        model=model, messages=messages, max_tokens=max_tokens, temperature=0.5,
    )
    choice  = response.choices[0]
    raw     = choice.message.content
    refusal = getattr(choice.message, 'refusal', None)
    print(f"[API] finish={choice.finish_reason} refusal={bool(refusal)} len={len(raw) if raw else 0}")
    if refusal or not raw or len(raw) < 20:
        raise ValueError(f"API refused or returned empty (finish={choice.finish_reason})")
    if choice.finish_reason == 'length':
        raise ValueError(f"API response truncated — max_tokens={max_tokens} insufficient")
    return raw


def _observe(openai_client, images_data: dict, model: str, validation_context: dict = None) -> str:
    """Step 1: image → plain-text structured clinical observations."""
    user_content = []
    if 'en_face' in images_data:
        img = images_data['en_face']
        user_content.append({"type": "image_url", "image_url": {"url": f"data:{img['media_type']};base64,{img['data']}"}})

    observation_text = OBSERVATION_PROMPT

    # Inject pre-computed validation context so observer can use it
    if validation_context:
        ctx_lines = ["[PRE-VALIDATION CONTEXT — already assessed, use as reference]:"]
        hp = validation_context.get('head_pose', {})
        if hp:
            ctx_lines.append(f"  Head pose: yaw={hp.get('yaw','?')} pitch={hp.get('pitch','?')} roll={hp.get('roll','?')}")
        if not validation_context.get('neck_visible', True):
            ctx_lines.append("  Neck: NOT VISIBLE in frame — do not assess neck in observations")
        if not validation_context.get('hairline_visible', True):
            ctx_lines.append("  Hairline: NOT VISIBLE in frame — do not assess hairline")
        imp = validation_context.get('overall_impression', {})
        if imp.get('labels'):
            ctx_lines.append(f"  Pre-assessed impression: {imp['labels']} (reasons: {imp.get('reasons', [])})")
        warns = validation_context.get('warnings', [])
        if warns:
            ctx_lines.append(f"  Warnings from validation: {warns}")
        observation_text = "\n".join(ctx_lines) + "\n\n" + observation_text

    user_content.append({"type": "text", "text": observation_text})
    messages = [
        {"role": "system", "content": "You are a dermatologist writing structured clinical observation notes from patient photographs. Document both strengths and concerns. Note confidence per section. Be specific and honest."},
        {"role": "user",   "content": user_content},
    ]
    return _call_raw(openai_client, messages, model, max_tokens=3500)


LANG_REQUIREMENT_EN = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE — CRITICAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALL free-text values in the JSON MUST be in English.
Enum/code keys (nasilenie, priorytet, kategoria, status) stay as specified.
GOOD: "Mild tissue descent in the malar region"
GOOD: "Mild laxity of the lower cheek"
ENUM KEYS that stay as fixed values: nasilenie (brak|lagodny|umiarkowany|zaawansowany), priorytet (wysoki|sredni|niski), kategoria, status (good|mild|moderate)"""

LANG_REQUIREMENT_PL = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE — CRITICAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALL free-text values in the JSON MUST be in Polish (język polski).
Enum/code keys (nasilenie, priorytet, kategoria, status) stay as specified.
BAD: "Slight tissue descent" → GOOD: "Niewielkie opadanie tkanek"
BAD: "Mild laxity" → GOOD: "Łagodna wiotkość\""""


def _patch_prompt_for_lang(prompt: str, lang: str) -> str:
    """Swap language-specific blocks for English output."""
    if lang != 'en':
        return prompt

    prompt = prompt.replace(LANG_REQUIREMENT_PL, LANG_REQUIREMENT_EN)
    prompt = prompt.replace("in Polish", "in English")
    prompt = prompt.replace("po polsku", "in English")
    prompt = prompt.replace("— Polish", "— English")
    prompt = prompt.replace("(język polski)", "(English)")
    prompt = prompt.replace("Polish procedure name", "English medical procedure name")

    # New fields — Polish placeholders → English
    prompt = prompt.replace(
        '"<specific anatomical positive observation — Polish>"',
        '"<specific anatomical positive observation — English>"')
    prompt = prompt.replace(
        '"notes": "<Polish>"',
        '"notes": "<English>"')
    prompt = prompt.replace(
        '"<one Polish sentence: what this face communicates aesthetically — cause + effect + perception>"',
        '"<one English sentence: what this face communicates aesthetically — cause + effect + perception>"')
    prompt = prompt.replace(
        '"<main anatomical factor creating tired appearance — or \'brak dominujących cech zmęczenia\' if face looks rested>"',
        '"<main anatomical factor creating tired appearance — or \'no dominant fatigue signs\' if face looks rested>"')
    prompt = prompt.replace(
        '"<one Polish sentence: cause → effect → perceived fatigue or freshness>"',
        '"<one English sentence: cause → effect → perceived fatigue or freshness>"')
    prompt = prompt.replace(
        '"<Polish: tension/laxity + perceptual effect>"',
        '"<English: tension/laxity + perceptual effect>"')
    prompt = prompt.replace(
        '"<Polish: tension/tissue descent + perceptual effect>"',
        '"<English: tension/tissue descent + perceptual effect>"')
    prompt = prompt.replace(
        '"<Polish: jawline definition or blurring>"',
        '"<English: jawline definition or blurring>"')
    prompt = prompt.replace(
        '"<Polish: finding — or \'Ocena szyi ograniczona przez kadr zdjęcia.\' if not visible>"',
        '"<English: finding — or \'Neck assessment limited by photo frame.\' if not visible>"')

    # Biological age format
    prompt = prompt.replace(
        '"biological_age_estimate": "<XX–XX lat — specific visible sign — pewność: wysoka|umiarkowana|niska>"',
        '"biological_age_estimate": "<XX–XX years — specific visible sign — confidence: high|moderate|low>"')
    prompt = prompt.replace(
        'Format: "XX–XX lat — [specific visible sign driving estimate] — pewność: wysoka|umiarkowana|niska"',
        'Format: "XX–XX years — [specific visible sign driving estimate] — confidence: high|moderate|low"')
    prompt = prompt.replace(
        '"pewność: niska — zdjęcie nie pozwala na wiarygodną ocenę"',
        '"confidence: low — photo does not allow reliable assessment"')
    prompt = prompt.replace(
        '"32–38 lat — brak zmarszczek statycznych, pełna objętość policzków, drobne dynamiczne kurze łapki — pewność: umiarkowana"',
        '"32–38 years — no static wrinkles, full cheek volume, fine dynamic crow\'s feet — confidence: moderate"')

    # Confidence values
    prompt = prompt.replace('pewność: wysoka|umiarkowana|niska', 'confidence: high|moderate|low')
    prompt = prompt.replace('"confidence": "<wysoka|umiarkowana|niska>"', '"confidence": "<high|moderate|low>"')
    prompt = prompt.replace('"confidence_global": "<wysoka|umiarkowana|niska>"', '"confidence_global": "<high|moderate|low>"')

    # Dominant impression list
    prompt = prompt.replace(
        '"świeży / wypoczęty" | "zmęczony" | "neutralny" | "napięty / zestresowany" | "smutny / przygaszony" | "surowy / poważny" | "łagodny / pogodny"',
        '"fresh / rested" | "tired" | "neutral" | "tense / stressed" | "sad / subdued" | "stern / serious" | "gentle / cheerful"')

    # Freshness values
    prompt = prompt.replace(
        '"freshness": "<wypoczęty|świeży|neutralny|poważny|napięty|zmęczony|przygnębiony>"',
        '"freshness": "<rested|fresh|neutral|serious|tense|tired|subdued>"')

    # disclaimer
    prompt = prompt.replace(
        '"disclaimer": "Dokumentacja kliniczna sporządzona na podstawie fotografii. Nie zastępuje badania lekarskiego."',
        '"disclaimer": "Clinical documentation based on a photograph. Does not replace a medical examination."')

    # findings fields
    prompt = prompt.replace('"name": "<finding name — Polish>"', '"name": "<finding name — English>"')
    prompt = prompt.replace('"area": "<anatomical location — Polish>"', '"area": "<anatomical location — English>"')
    prompt = prompt.replace(
        '"wplyw_estetyczny": "<one Polish sentence: cause → effect → perception>"',
        '"wplyw_estetyczny": "<one English sentence: cause → effect → perception>"')
    prompt = prompt.replace('"dlaczego_wazne": "<one Polish sentence>"', '"dlaczego_wazne": "<one English sentence>"')
    prompt = prompt.replace(
        '"co_moze_sie_poglebiac": "<one Polish sentence — progression without intervention>"',
        '"co_moze_sie_poglebiac": "<one English sentence — progression without intervention>"')
    prompt = prompt.replace(
        '"co_wdrozyc_najpierw": "<one Polish sentence — first step>"',
        '"co_wdrozyc_najpierw": "<one English sentence — first step>"')

    # Forbidden phrases → English
    prompt = prompt.replace(
        'FORBIDDEN vague phrases: "zbliżone do normy", "obszary wymagające uwagi", "harmonijne", "wygląda naturalnie", "ogólnie dobra", "wygląda zdrowo", "prawidłowy", "bez zastrzeżeń"',
        'FORBIDDEN vague phrases: "within normal limits", "areas requiring attention", "harmonious", "looks natural", "generally good", "looks healthy", "normal", "no concerns"')

    # Procedure examples
    prompt = prompt.replace(
        '  BAD: "Stosuj krem z SPF"\n  GOOD: "Fotoprotekcja: mineralny SPF 50+ PA++++ codziennie rano — warunek skuteczności każdej procedury aktywnej"',
        '  BAD: "Apply sunscreen"\n  GOOD: "Photoprotection: mineral SPF 50+ PA++++ every morning — prerequisite for effectiveness of any active procedure"')

    # Tone examples
    prompt = prompt.replace(
        '  BAD: "Obniżone napięcie skóry."\n  GOOD: "Obniżone napięcie skóry policzków powoduje opadanie tkanek, co tworzy wrażenie zmęczenia twarzy."',
        '  BAD: "Reduced skin tension."\n  GOOD: "Reduced cheek skin tension causes tissue descent, creating an impression of facial fatigue."')

    # No-concern fallback
    prompt = prompt.replace(
        'write "brak istotnych nieprawidłowości w [structure]"',
        'write "no significant concerns in [structure]"')

    # "brak dominujących cech zmęczenia" example
    prompt = prompt.replace(
        '"brak dominujących cech zmęczenia"',
        '"no dominant fatigue signs"')

    # Category definitions
    prompt = prompt.replace(
        '  skin_quality → pory, tekstura, nawilżenie skóry twarzy',
        '  skin_quality → pores, texture, skin hydration')
    prompt = prompt.replace(
        '  pigment_vascular → przebarwienia, naczynka, rumień',
        '  pigment_vascular → pigmentation, vascular changes, redness')
    prompt = prompt.replace(
        '  eye_area → dolina łez, cienie, obrzęki, zmarszczki okolicy oczu — ALWAYS document tear trough depth, shadow character, fatigue impact',
        '  eye_area → tear trough, shadows, puffiness, periorbital lines — ALWAYS document tear trough depth, shadow character, fatigue impact')
    prompt = prompt.replace(
        '  volume_contour → objętość policzków, owal twarzy, linia żuchwy',
        '  volume_contour → cheek volume, facial oval, jawline')
    prompt = prompt.replace(
        '  forehead_hairline → linia włosów, gęstość, czoło',
        '  forehead_hairline → hairline, density, forehead')
    prompt = prompt.replace(
        '  neck → skóra szyi, napięcie, zmarszczki — if not visible: nasilenie "brak", note frame limitation',
        '  neck → neck skin, tension, horizontal lines — if not visible: nasilenie "brak", note frame limitation')
    prompt = prompt.replace(
        '  skin_tension → napięcie policzków, żuchwy, opadanie tkanek — wplyw_estetyczny MUST state fatigue impact',
        '  skin_tension → cheek tension, jawline tension, tissue descent — wplyw_estetyczny MUST state fatigue impact')

    # skin_health_note
    prompt = prompt.replace(
        '"skin_health_note": "<one sentence in Polish: why skin quality improvement matters for this patient>"',
        '"skin_health_note": "<one sentence in English: why skin quality improvement matters for this patient>"')

    # Strengths examples
    prompt = prompt.replace(
        '  "Zachowana pełna objętość policzków — brak utraty tkanki malarnej"',
        '  "Preserved full cheek volume — no malar tissue loss"')
    prompt = prompt.replace(
        '  "Wyraźnie zarysowana linia żuchwy bez cech opadania ani formowania się jowli"',
        '  "Sharply defined jawline without tissue descent or jowl formation"')
    prompt = prompt.replace(
        '  "Równomierny koloryt skóry bez widocznych ognisk przebarwień"',
        '  "Even skin tone without visible pigmentation foci"')
    prompt = prompt.replace(
        '  "Brak zmarszczek statycznych czoła w spoczynku — tylko wczesne dynamiczne"',
        '  "No static forehead lines at rest — only early dynamic"')

    # Features notes in English
    prompt = prompt.replace(
        '"notes": "ocena ograniczona"',
        '"notes": "assessment limited"')

    return prompt


def _report(openai_client, observations: str, model: str, lang: str = 'pl') -> dict:
    """Step 2: observations text → structured JSON report."""
    lang_name = 'English' if lang == 'en' else 'Polish'
    base_prompt = CLINICAL_PROMPT + FINDINGS_EXTENSION
    patched_prompt = _patch_prompt_for_lang(base_prompt, lang)

    prompt = (
        f"Format these clinical observation notes into a structured {lang_name}-language JSON report.\n\n"
        f"RULE A — GROUNDING: Every JSON field value MUST quote or directly reflect a specific finding from OBSERVATIONS. "
        f"If observations say 'CANNOT ASSESS' or do not mention a feature → write 'ocena ograniczona — niewidoczne na zdjęciu'. "
        f"NEVER use generic phrases like 'delikatne zmarszczki', 'łagodna utrata objętości' unless the observations specifically say so.\n\n"
        f"RULE B — UNIQUENESS: This report must reflect THIS patient only. "
        f"Every text field must contain at least one specific detail from the observations (grade number, side, location, measurement). "
        f"A report without specific details = invalid.\n\n"
        f"RULE C — SCORE CALIBRATION: Scores MUST reflect actual findings:\n"
        f"  - Patient with documented wrinkles grade 3+ → aging_signs ≤ 5\n"
        f"  - Patient with no wrinkles noted → aging_signs 8–10\n"
        f"  - Patient with tear trough grade 2+ → eye_area ≤ 5\n"
        f"  - Patient with full malar volume → skin_quality domain scores high\n"
        f"  - overall_score: typical patient 55–68; do NOT give everyone 60\n\n"
        f"RULE D — STRENGTHS: List 3–6 specific anatomical positives from observations. "
        f"Quote exact features observed (e.g. 'pełna objętość łuków jarzmowych', 'brak zmarszczek statycznych czoła'). "
        f"Do NOT write 'ocena ograniczona' in strengths unless the face is literally invisible.\n\n"
        f"OBSERVATIONS:\n{observations}\n\n"
        f"Return ONLY valid JSON. All free-text values in {lang_name}.\n\n"
        + patched_prompt
    )
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a warm and knowledgeable aesthetic medicine doctor writing a personalised pre-consultation report. "
                f"Lead with what is genuinely good about this patient's face. Present areas for improvement as opportunities, not problems. "
                f"Every sentence must reflect a specific finding from the observations — no generic templates. "
                f"Scores must vary based on actual findings: excellent features score high (8–10), areas needing work score low (3–5). "
                f"Tone: like a trusted expert who wants the patient to feel informed, valued, and motivated for their consultation. "
                f"Return only valid JSON, no markdown. All free text in {lang_name}."
            )
        },
        {"role": "user", "content": prompt},
    ]
    for attempt in range(2):
        raw = _call_raw(openai_client, messages, model, max_tokens=8000)
        try:
            return _extract_json(raw)
        except (ValueError, json.JSONDecodeError) as e:
            print(f"[REPORT] JSON parse failed attempt {attempt+1}: {e} — raw[:200]: {repr(raw[:200])}")
            if attempt == 1:
                raise
    raise ValueError("_report: exhausted retries")


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

    # ─── Step 0: AI validation ───────────────────────────────────────────────
    # Raises ValueError('EYES_BLOCKED:…') or ValueError('PHOTO_UNSUITABLE:…') on failure.
    en_face_path = file_paths_dict.get('en_face', '')
    validation = {}
    if en_face_path:
        try:
            validation = validate_face_ai(en_face_path, openai_client, model)
            print(f"[VALIDATE_AI OK] head_pose={validation['head_pose']['yaw']} "
                  f"impression={validation['overall_impression']['labels']} "
                  f"harmony={validation['harmony']['level']}")
        except ValueError:
            raise  # re-raise EYES_BLOCKED / PHOTO_UNSUITABLE to caller
        except Exception as e:
            # Fail-open: log and continue if validation has unexpected error
            print(f"[VALIDATE_AI WARN] non-blocking error: {e}")
            validation = {}

    # ─── Step 1: Detailed clinical observation ───────────────────────────────
    # Inject validation context so the observer knows what's already assessed.
    observations = _observe(openai_client, images_data, model, validation_context=validation)
    print(f"[OBSERVE OK] {len(observations)} chars")

    # Backup suitability check (safety net in case Step 0 missed something)
    obs_upper = observations[:400].upper()
    if 'EYES_BLOCKED' in obs_upper:
        raise ValueError("EYES_BLOCKED: Zdjęcie z okularami lub zasłoniętymi oczami — analiza niemożliwa. Wgraj zdjęcie bez okularów.")
    if 'PHOTO_UNSUITABLE' in obs_upper:
        raise ValueError("PHOTO_UNSUITABLE: Zdjęcie nieodpowiednie do analizy. Wgraj wyraźne zdjęcie en face, patrzące prosto w aparat.")

    # ─── Step 2: Format → structured JSON report ────────────────────────────
    result = _report(openai_client, observations, model, lang=lang)

    # ─── Merge validation context into result ────────────────────────────────
    if validation:
        result['validation'] = validation
        # Use AI impression if main report didn't produce one
        if not result.get('dominant_impression') and validation.get('overall_impression', {}).get('labels'):
            result['dominant_impression'] = validation['overall_impression']['labels']
        # Add harmony assessment
        if validation.get('harmony'):
            result['harmony'] = validation['harmony']
        # Add structural warnings
        if validation.get('warnings'):
            result.setdefault('analysis_warnings', [])
            result['analysis_warnings'].extend(validation['warnings'])
        # Note frame limitations
        result['neck_visible']     = validation.get('neck_visible', True)
        result['hairline_visible'] = validation.get('hairline_visible', True)

    _validate_result(result)

    return result
