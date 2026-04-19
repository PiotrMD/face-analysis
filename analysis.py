import json
import base64
from typing import Dict

CLINICAL_PROMPT = """You are a board-certified aesthetic medicine physician preparing a structured pre-consultation clinical documentation record. The patient has uploaded a standardized frontal photograph (en face) and consented to a clinical screening assessment to support their upcoming in-person consultation.

Your task is to document clinical findings across 7 anatomical domains, identify the primary clinical concern requiring intervention, and outline a treatment priority plan. This is a medical documentation task, not a subjective evaluation of appearance.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE REQUIREMENT — CRITICAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALL text values in the JSON output MUST be written in Polish (język polski).
This applies to every string field: summary, findings, skin_tension, fatigue_factors, overall_perception, recommendations, and all others.
Do NOT use English words in any field value. Use Polish anatomical and clinical terminology.
Examples of FORBIDDEN English in field values:
  BAD: "Slight tissue descent" → GOOD: "Niewielkie opadanie tkanek"
  BAD: "Mild laxity"          → GOOD: "Łagodna wiotkość"
  BAD: "Mildly blurred"       → GOOD: "Łagodnie zatarta"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCUMENTATION STANDARDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORBIDDEN generic phrases (these make documentation clinically invalid):
  "zbliżone do normy", "obszary wymagające uwagi", "harmonijne", "dobrze zdefiniowane",
  "wygląda naturalnie", "ogólnie dobra", "proporcje są dobre", "twarz jest symetryczna",
  "wygląda zdrowo", "prawidłowy", "bez zastrzeżeń", "zadowalający"

DOCUMENTATION STYLE — clinical case notes, not a subjective opinion:
  - Document findings as a physician would write in a medical chart
  - Name the anatomical structure, then describe the clinical finding
  - Use grades and measurements where applicable: "stopień 1 wg skali Barton", "~2mm", ">0.4mm"
  - Do not omit findings or soften them with non-clinical adjectives
  - TONE: use cause → effect → perception chain. Example:
      BAD:  "Obniżone napięcie skóry."
      GOOD: "Obniżone napięcie skóry policzków powoduje opadanie tkanek, co wpływa na odbiór zmęczenia twarzy."
  - For uncertainty: use "obraz sugeruje", "cechy zgodne z", "wymaga potwierdzenia w konsultacji"

EVERY clinical statement must contain:
  1. ANATOMICAL LOCATION — exact structure (e.g. "okolica podoczodołowa lewa", "strefa T nosa", "lewy kąt ust")
  2. CLINICAL FINDING — specific type and severity (e.g. "utrata objętości stopień 1", "asymetria ~2mm", "pory >0.4mm", "rhytidy dynamiczne stopień 2")

If no significant pathology is documented in a domain: write "brak istotnych nieprawidłowości klinicznych w [structure]" and still document 2–3 minor deviations observed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLINICAL INDEX — overall_score (integer 0–100)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is a composite clinical documentation index reflecting the cumulative extent of documented findings across all 7 domains. It is NOT a subjective attractiveness rating — it measures how many and how significant the documented clinical conditions are.

  85–100 : minimal clinical findings; very few conditions documented
  70–84  : mild findings; 1–2 domains with documented concerns
  55–69  : moderate findings; multiple documented conditions (typical pre-consultation range)
  40–54  : significant findings; most domains have documented clinical conditions
  <40    : extensive multi-domain clinical documentation

Typical pre-consultation patient: 55–68. Do not inflate the index.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIELD DOCUMENTATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

summary — exactly 3 sentences for the clinical chart:
  Sentence 1: primary structural strength — anatomical structure + specific clinical observation
  Sentence 2: primary clinical concern — exact location + specific finding type
  Sentence 3: clinical outlook — what the patient should expect or prioritize at the in-person visit
  BANNED: disclaimers, vague adjectives, flattery, marketing language

biological_age_estimate:
  Format: "XX–XX lat — [specific clinical sign that drove the estimate]"
  Example: "37–43 lat — rhytidy dynamiczne stopień 2 przy kątach oczu i pory >0.4mm w strefie T wskazują na przyspieszone fotostarzenie"

strongest_asset:
  One sentence. Document the anatomical structure that shows the fewest concerns and explain the specific clinical observation supporting this.

top_priority:
  1–2 sentences documenting the primary condition requiring earliest clinical attention:
  (a) exact anatomical location + specific finding type
  (b) functional or clinical impact on adjacent structures or perceived condition
  (c) expected progression without treatment
  Use clinical consequence language:
    "może nasilać efekt zmęczenia twarzy"
    "pogłębia cień podoczodołowy i efekt chronicznego zmęczenia"
    "bez interwencji defekt będzie postępował z wiekiem"
  BAD: "Poprawa jakości skóry"
  GOOD: "Utrata objętości w okolicy podoczodołowej lewej (tear trough stopień 1–2 wg skali Barton) pogłębia cień podoczodołowy i wymaga interwencji — bez leczenia defekt będzie narastał i nasilał efekt chronicznego zmęczenia twarzy."

recommendations — 5 to 7 items, ordered by clinical priority:
  Format: [CLINICAL INDICATION] + [PROCEDURE/PRODUCT] + [DOSE or FREQUENCY]
  Rules:
  - Concise enough to scan in 5 seconds
  - Medically realistic — standard-of-care interventions
  - Written as physician's pre-procedure briefing notes
  BAD: "Stosuj krem z SPF"
  GOOD: "Fotoprotekcja: mineralny SPF 50+ PA++++ codziennie rano — warunek skuteczności każdej interwencji aktywnej"

sections — documentation rules for ALL 7 domains:
  status: "moderate" = would prescribe or refer at an in-person clinic visit
  finding: [anatomical structure] + [specific clinical observation with grade or measurement]
  detail: 3–4 items, each = [location] + [finding type + grade/measurement]
    - At least 1 item must document a condition or concern
    - Grades and measurements preferred: "~2mm", "stopień 2 wg skali Lemperle", ">0.4mm"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCUMENTATION EXAMPLE — match this specificity and clinical tone
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Do NOT copy this example. Use it as a calibration reference only.

{
  "overall_score": 64,
  "summary": "Łuki jarzmowe wykazują symetryczną projekcję boczną bez utraty objętości, stanowiąc klinicznie korzystną cechę strukturalną środkowej trzeciej twarzy. W okolicy podoczodołowej obustronnie udokumentowano utratę objętości stopień 1 wg skali Barton, z silniejszym cieniem tear trough po lewej stronie, klinicznie istotną dla efektu zmęczenia twarzy. Priorytetem konsultacji jest ocena wskazań do regeneracji okolicy podoczodołowej.",
  "biological_age_estimate": "37–42 lat — rhytidy dynamiczne stopień 2 przy zewnętrznych kątach oczu oraz pory >0.4mm w strefie T nosa wskazują na przyspieszone fotostarzenie",
  "strongest_asset": "Łuki jarzmowe — symetryczna projekcja boczna w okolicy jarzmowo-skroniowej bez dokumentowanych ubytków objętości, rzadka cecha strukturalna w tej grupie wiekowej.",
  "top_priority": "Utrata objętości w okolicy podoczodołowej lewej (tear trough stopień 1–2 wg skali Barton) pogłębia cień podoczodołowy i efekt chronicznego zmęczenia — bez interwencji defekt będzie narastał i utrwalał cień.",
  "recommendations": [
    "Tear trough: fibryna bogatokomórkowa (PRF) lub łagodne stymulatory — regeneracja okolicy podoczodołowej bez ryzyka obrzęku",
    "Rhytidy dynamiczne okolicy oka: toksyna botulinowa 8–10j w mięsień okrężny oka obustronnie, co 4–5 miesięcy",
    "Tekstura skóry: tretynoin 0.05% co drugi wieczór przez 6 tygodni, następnie 0.1% codziennie",
    "Fotoprotekcja: mineralny SPF 50+ PA++++ codziennie rano",
    "Pory i sebostaza strefy T: niacynamid 10% serum rano i wieczór przez min. 12 tygodni"
  ],
  "sections": {
    "skin_quality": {
      "status": "moderate",
      "finding": "Strefa T nosa i czoła z rozszerzonymi porami >0.4mm i niejednorodnym mikrorelief skóry; policzek lewy z ogniskami hiperpigmentacji pozapalnej.",
      "detail": [
        "Strefa T (nos, czoło): pory >0.4mm, cechy sebostazy",
        "Policzek lewy: 3–4 ogniska hiperpigmentacji pozapalnej ~3–5mm",
        "Powierzchnia policzków: niejednorodny mikrorelief z lokalnymi nierównościami tekstury"
      ]
    }
  }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT — return ONLY the JSON object below, no markdown, no explanations
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{
  "overall_score": <integer 0-100>,
  "summary": "<sentence 1: structural asset> <sentence 2: primary concern> <sentence 3: clinical outlook>",
  "biological_age_estimate": "<XX-XX lat — specific clinical sign>",
  "strongest_asset": "<anatomical structure + clinical observation>",
  "top_priority": "<location + finding + progression + intervention>",
  "recommendations": [
    "<INDICATION: PROCEDURE DOSE/FREQUENCY>",
    "<INDICATION: PROCEDURE DOSE/FREQUENCY>",
    "<INDICATION: PROCEDURE DOSE/FREQUENCY>",
    "<INDICATION: PROCEDURE DOSE/FREQUENCY>",
    "<INDICATION: PROCEDURE DOSE/FREQUENCY>"
  ],
  "category_scores": {
    "symmetry": <integer 0-10>,
    "proportions": <integer 0-10>,
    "aging_signs": <integer 0-10>,
    "skin_quality": <integer 0-10>,
    "eye_area": <integer 0-10>,
    "lips_lower_face": <integer 0-10>,
    "hairline_hair": <integer 0-10>
  },
  "key_findings": [
    {"section": "symmetry",       "finding": "<anatomical location + clinical finding>", "status": "<good|mild|moderate>", "score": <0-10>},
    {"section": "proportions",    "finding": "<anatomical location + clinical finding>", "status": "<good|mild|moderate>", "score": <0-10>},
    {"section": "aging_signs",    "finding": "<anatomical location + clinical finding>", "status": "<good|mild|moderate>", "score": <0-10>},
    {"section": "skin_quality",   "finding": "<anatomical location + clinical finding>", "status": "<good|mild|moderate>", "score": <0-10>},
    {"section": "eye_area",       "finding": "<anatomical location + clinical finding>", "status": "<good|mild|moderate>", "score": <0-10>},
    {"section": "lips_lower_face","finding": "<anatomical location + clinical finding>", "status": "<good|mild|moderate>", "score": <0-10>},
    {"section": "hairline_hair",  "finding": "<anatomical location + clinical finding>", "status": "<good|mild|moderate>", "score": <0-10>}
  ],
  "sections": {
    "symmetry":       {"status": "<good|mild|moderate>", "finding": "<structure + finding>", "detail": ["<loc + finding>", "<loc + finding>", "<loc + finding>"]},
    "proportions":    {"status": "<good|mild|moderate>", "finding": "<structure + finding>", "detail": ["<loc + finding>", "<loc + finding>", "<loc + finding>"]},
    "aging_signs":    {"status": "<good|mild|moderate>", "finding": "<structure + finding>", "detail": ["<loc + finding>", "<loc + finding>", "<loc + finding>"]},
    "skin_quality":   {"status": "<good|mild|moderate>", "finding": "<structure + finding>", "detail": ["<loc + finding>", "<loc + finding>", "<loc + finding>"]},
    "eye_area":       {"status": "<good|mild|moderate>", "finding": "<structure + finding>", "detail": ["<loc + finding>", "<loc + finding>", "<loc + finding>"]},
    "lips_lower_face":{"status": "<good|mild|moderate>", "finding": "<structure + finding>", "detail": ["<loc + finding>", "<loc + finding>", "<loc + finding>"]},
    "hairline_hair":  {"status": "<good|mild|moderate>", "finding": "<structure + finding>", "detail": ["<loc + finding>", "<loc + finding>", "<loc + finding>"]}
  },
  "overall_perception": {
    "freshness": "<świeży|neutralny|zmęczony>",
    "apparent_age": "<młodszy niż wiek biologiczny|odpowiedni do wieku|starszy niż wiek biologiczny>",
    "impression": "<one sentence in Polish: what the overall face communicates aesthetically — cause + effect + perception>"
  },
  "fatigue_factors": {
    "primary": "<main anatomical factor creating tired appearance, in Polish — or 'brak cech zmęczenia' if face looks fresh>",
    "contributing": ["<factor in Polish>", "<factor in Polish>"],
    "explanation": "<one sentence: cause → effect → perceived fatigue, in Polish>"
  },
  "skin_tension": {
    "under_eye": "<po polsku: napięcie/wiotkość, efekt percepcyjny>",
    "cheeks": "<po polsku: napięcie/opadanie tkanek, efekt percepcyjny>",
    "jawline": "<po polsku: definicja linii żuchwy lub zatarcie przez opadanie tkanek>",
    "neck": "<po polsku: znalezisko lub 'Ocena szyi ograniczona przez kadr zdjęcia.'>"
  },
  "disclaimer": "Dokumentacja kliniczna sporządzona na podstawie fotografii. Nie zastępuje badania lekarskiego.",
  "skin_health_note": "<one sentence in Polish: why improving skin quality in this patient increases longevity and predictability of aesthetic procedures>",
  "findings": [
    {
      "id": "<unique_snake_case>",
      "name": "<finding name in Polish>",
      "area": "<anatomical location in Polish>",
      "kategoria": "<skin_quality|pigment_vascular|eye_area|volume_contour|forehead_hairline|lesions|neck|skin_tension>",
      "nasilenie": "<brak|lagodny|umiarkowany|zaawansowany>",
      "priorytet": "<wysoki|sredni|niski>",
      "wplyw_estetyczny": "<one sentence in Polish: cause → effect → perception>",
      "kierunek_postepowania": ["<Polish medical procedure name>"],
      "wymaga_potwierdzenia": false,
      "dlaczego_wazne": "<one sentence in Polish>",
      "co_moze_sie_poglebiac": "<one sentence in Polish>",
      "co_wdrozyc_najpierw": "<one sentence in Polish>"
    }
  ]
}

findings: include 6–10 entries. MANDATORY: at least one eye_area entry, at least one skin_tension entry, AND at least one neck entry (if neck visible in photo) — these are REQUIRED, analysis is incomplete without them. If neck not visible, include one neck entry with nasilenie: "brak" and note the frame limitation.
nasilenie values: brak (no significant finding) | lagodny | umiarkowany | zaawansowany
priorytet values: wysoki | sredni | niski
kategoria: skin_quality=pory/tekstura/nawilżenie | pigment_vascular=przebarwienia/naczynka/rumień | eye_area=dolina łez/cienie/obrzęki/zmarszczki okolicy oczu | volume_contour=policzki/owal/żuchwa | forehead_hairline=czoło/linia włosów | lesions=blizny/brodawki (zawsze wymaga_potwierdzenia:true) | neck=skóra szyi/napięcie szyi | skin_tension=napięcie skóry twarzy/policzków/żuchwy
kierunek_postepowania: napięcie→RF mikroigłowa/mezoterapia/stymulatory/osocze/fibryna | pory/tekstura→peelingi/laser frakcyjny/RF mikroigłowa | przebarwienia→peelingi/laser frakcyjny | naczynka→laser naczyniowy | objętość policzków/owalu→filler HA | okolica podoczodołowa/tear trough→fibryna bogatokomórkowa/łagodne stymulatory (NIE filler HA — ryzyko obrzęku) | zmarszczki dynamiczne→toksyna botulinowa | lesions→elektrokoagulacja | szyja→RF mikroigłowa/mezoterapia/laser frakcyjny
eye_area finding: ALWAYS document tear trough (depth/grade), dark circles (character), puffiness (if present), and whether the area creates a tired appearance.
skin_tension finding: wplyw_estetyczny MUST explain the perceptual consequence — e.g. "obniżone napięcie policzków powoduje opadanie tkanek i wpływa na odbiór zmęczenia twarzy"
lesions: always use "obraz sugeruje" / "cechy zgodne z" / "wymaga potwierdzenia w konsultacji"

SCORING GUIDE for category_scores and key_findings score (0–10 per domain):
  9–10: no documented clinical concerns in this domain
  7–8:  minor documented findings, no intervention indicated
  5–6:  documented findings, monitoring or topical treatment indicated
  3–4:  documented conditions requiring clinical intervention
  1–2:  significant multi-focal findings requiring priority intervention
category_scores must align with domain status: "good" → 7–10, "mild" → 4–6, "moderate" → 1–4.
key_findings must include all 7 domains, one entry each, score matching category_scores."""

FINDINGS_EXTENSION = """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXTENDED FIELDS — dodaj do tego samego JSON
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Uwzględnij w obiekcie JSON dwa dodatkowe pola na końcu:

"skin_health_note": "<jedno zdanie po polsku: dlaczego poprawa jakości skóry tej osoby zwiększa trwałość i przewidywalność efektów procedur estetycznych>"

"findings": [
  {
    "id": "<unikalne_snake_case>",
    "name": "<nazwa zmiany po polsku>",
    "area": "<lokalizacja anatomiczna po polsku>",
    "kategoria": "<skin_quality|pigment_vascular|eye_area|volume_contour|forehead_hairline|lesions|neck>",
    "nasilenie": "<brak|lagodny|umiarkowany|zaawansowany>",
    "priorytet": "<wysoki|sredni|niski>",
    "wplyw_estetyczny": "<jedno zdanie po polsku — wpływ na wygląd>",
    "kierunek_postepowania": ["<procedura>"],
    "wymaga_potwierdzenia": false,
    "dlaczego_wazne": "<jedno zdanie>",
    "co_moze_sie_poglebiac": "<jedno zdanie — progresja bez interwencji>",
    "co_wdrozyc_najpierw": "<jedno zdanie — pierwszy krok>"
  }
]

Uwzględnij 4–10 findings — tylko rzeczywiście widoczne lub sugerowane zmiany.

Definicje kategorii:
skin_quality → pory, tekstura, nawilżenie — skóra twarzy
pigment_vascular → przebarwienia, naczynka, rumień
eye_area → dolina łez (tear trough), cienie, obrzęki, zmarszczki okolicy oczu, napięcie powieki dolnej
  WAŻNE dla eye_area: zawsze udokumentuj tear trough (głębokość), charakter cieni (naczyniowy/objętościowy/pigmentacyjny), czy obszar tworzy efekt zmęczenia
volume_contour → objętość policzków, owal twarzy, linia żuchwy
forehead_hairline → linia włosów, gęstość, czoło
lesions → blizny, brodawki, włókniaki — ZAWSZE wymaga_potwierdzenia: true; użyj: "obraz sugeruje", "cechy zgodne z"
neck → skóra szyi, napięcie, zmarszczki poziome, przebarwienia — jeśli niewidoczna: dodaj finding z nasilenie: "brak" i note "Ocena ograniczona przez kadr"
skin_tension → napięcie skóry policzków, napięcie żuchwy, opadanie tkanek — wplyw_estetyczny MUSI zawierać: "wpływa na odbiór zmęczenia twarzy" lub "nie wpływa istotnie na odbiór zmęczenia"

Kierunki postępowania (polskie terminy):
napięcie/firmness/skin_tension → RF mikroigłowa, mezoterapia, stymulatory, osocze bogatopłytkowe, fibryna
pory/tekstura → peelingi, laser frakcyjny, RF mikroigłowa
przebarwienia → peelingi, laser frakcyjny
naczynka/rumień → laser naczyniowy
okolica podoczodołowa/tear trough → fibryna bogatokomórkowa (PRF), łagodne stymulatory tkankowe — NIGDY filler HA (ryzyko powikłań obrzękowych)
zmarszczki dynamiczne → toksyna botulinowa
objętość policzków/owalu → filler HA, stymulatory
lesions → elektrokoagulacja
szyja → RF mikroigłowa, mezoterapia, laser frakcyjny, stymulatory

Ten obszar ma kluczowy wpływ na odbiór zmęczenia twarzy — musi być udokumentowany w każdej analizie: eye_area finding."""

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


def _build_messages(images_data: dict) -> list:
    user_content = []
    if 'en_face' in images_data:
        img = images_data['en_face']
        user_content.append({"type": "image_url", "image_url": {"url": f"data:{img['media_type']};base64,{img['data']}"}})
    user_content.append({"type": "text", "text": CLINICAL_PROMPT})
    return [
        {"role": "system", "content": "You are a physician preparing structured pre-consultation clinical documentation based on patient photographs. Document findings objectively and return structured JSON as instructed."},
        {"role": "user",   "content": user_content},
    ]


def _validate_result(result: dict) -> None:
    for field in REQUIRED_TOP_FIELDS:
        if field not in result:
            raise ValueError(f"Brak wymaganego pola: {field}")

    result['overall_score'] = int(round(float(result['overall_score'])))
    if not (0 <= result['overall_score'] <= 100):
        raise ValueError(f"overall_score poza zakresem 0-100: {result['overall_score']}")

    if not isinstance(result['recommendations'], list) or len(result['recommendations']) < 3:
        raise ValueError("recommendations musi być listą z co najmniej 3 elementami")

    cat = result.get('category_scores', {})
    for sec_name in REQUIRED_SECTIONS:
        if sec_name not in cat:
            raise ValueError(f"Brak category_scores['{sec_name}']")
        result['category_scores'][sec_name] = int(round(float(cat[sec_name])))

    kf = result.get('key_findings', [])
    if not isinstance(kf, list):
        result['key_findings'] = []
        kf = []
    kf_sections = {item.get('section') for item in kf if isinstance(item, dict)}
    missing_kf = set(REQUIRED_SECTIONS) - kf_sections
    if missing_kf:
        # Synthesize missing key_findings entries from sections
        for sec_name in missing_kf:
            sec = result.get('sections', {}).get(sec_name, {})
            result['key_findings'].append({
                'section': sec_name,
                'finding': sec.get('finding', '—'),
                'status': sec.get('status', 'mild'),
                'score': result.get('category_scores', {}).get(sec_name, 5),
            })

    sections = result.get('sections', {})
    for section_name in REQUIRED_SECTIONS:
        if section_name not in sections:
            raise ValueError(f"Brak sekcji: {section_name}")
        sec = sections[section_name]
        missing = REQUIRED_SECTION_KEYS - set(sec.keys())
        if missing:
            raise ValueError(f"Sekcja '{section_name}' brakuje pól: {missing}")
        if sec['status'] not in VALID_STATUSES:
            raise ValueError(f"Sekcja '{section_name}' ma nieprawidłowy status: {sec['status']}")
        if not isinstance(sec.get('detail'), list):
            sec['detail'] = [sec.get('finding', '—')]

    # Lenient normalization of extended fields — don't fail if missing
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
            cleaned.append(f)
        result['findings'] = cleaned

    # Normalize overall_perception
    op = result.get('overall_perception')
    if not isinstance(op, dict):
        result['overall_perception'] = None
    else:
        valid_freshness = {'świeży', 'neutralny', 'zmęczony'}
        if op.get('freshness') not in valid_freshness:
            op['freshness'] = op.get('freshness', 'neutralny')

    # Normalize fatigue_factors
    ff = result.get('fatigue_factors')
    if not isinstance(ff, dict):
        result['fatigue_factors'] = None
    else:
        if not isinstance(ff.get('contributing'), list):
            ff['contributing'] = []

    # Normalize skin_tension
    st = result.get('skin_tension')
    if not isinstance(st, dict):
        result['skin_tension'] = None


OBSERVATION_PROMPT = """You are a dermatologist writing clinical observation notes from a patient photograph for pre-consultation records. Document visible anatomical findings only. Be specific and systematic — address every numbered point.

SECTION A — PERIORBITAL REGION:
A1. Tear trough (sulcus orbitalis inferior): depth (shallow/moderate/deep), left vs right asymmetry, shadow quality (sharp/diffuse)
A2. Infraorbital discoloration: absent or present; if present — character: vascular (bluish-purple), pigmentary (brownish), volumetric shadow (grey), or mixed
A3. Infraorbital puffiness / festoons: absent or present; if present — grade (mild/moderate/marked) and exact location
A4. Periorbital skin quality: visible fine lines, crepiness, thinness of lower eyelid skin
A5. Lateral canthal lines ("crow's feet"): absent / fine / moderate / deep; static or dynamic only
A6. Overall periorbital fatigue appearance: does this area create a tired or rested impression — state specifically why

SECTION B — SKIN TENSION AND TISSUE DESCENT:
B1. Cheeks / malar area: tissue firmness vs. descent; malar fat pad position; any hollowing
B2. Nasolabial folds: depth (grade 1–4), symmetry left/right
B3. Marionette lines: present or absent; if present — depth and symmetry
B4. Jawline definition: clearly defined / mildly blurred / significantly blurred; any jowl formation
B5. Lower face contour: chin projection, mental crease if visible
B6. Mid-face volume: maintained / mild loss / significant loss — location

SECTION C — SKIN QUALITY:
C1. T-zone (forehead, nose): pore size (normal/<0.3mm/>0.4mm), surface texture, seborrhea signs
C2. Cheeks: texture uniformity, microrelief, any roughness or irregular surface
C3. Overall skin tone: even / uneven; focal discolorations (location, size, color); diffuse redness or vascular pattern
C4. Skin hydration appearance: normal / dehydrated surface / oily shine

SECTION D — AGING SIGNS:
D1. Forehead lines: horizontal rhytids — depth and extent; vertical glabellar lines — present/absent
D2. Periorbital lines: see Section A5
D3. Lower face lines: nasolabial (see B2), marionette (see B3), chin/mental crease
D4. Overall elasticity impression from skin surface: normal / mildly reduced / significantly reduced

SECTION E — SYMMETRY AND PROPORTIONS:
E1. Facial thirds (forehead : midface : lower face ratio — equal / upper dominant / lower dominant)
E2. Facial width-to-height proportions
E3. Midline alignment: straight / deviated (direction and approximate mm)
E4. Structural left/right asymmetries — list each with anatomical location and estimated magnitude

SECTION F — LIPS AND LOWER FACE:
F1. Upper lip: volume (full/moderate/thin), philtrum definition, vermillion border clarity
F2. Lower lip: volume relative to upper lip
F3. Lip symmetry: left/right, commissure height
F4. Perioral area: vertical lip lines if present, oral commissure descent

SECTION G — HAIRLINE AND HAIR:
G1. Forehead height (low/medium/high)
G2. Hairline shape and regularity
G3. Hair density at temples and frontal zone: full / mild thinning / notable thinning

SECTION H — NECK (CRITICAL — examine carefully):
If the neck IS visible in the photograph:
  H1. Skin quality: texture, pore appearance, surface uniformity vs face
  H2. Skin firmness and laxity: tight / mild laxity / moderate laxity / significant laxity
  H3. Horizontal neck lines (necklace lines): absent / 1–2 fine / multiple moderate / deep
  H4. Platysma bands: visible or not visible
  H5. Submental area (under chin): well-defined / mild fullness / submental fat
  H6. Pigmentation: even / uneven; any discoloration compared to face
  H7. Overall neck skin age appearance vs facial skin: same / looks older / looks younger
If the neck is NOT visible in the photograph: write "Neck not visible in frame — assessment not possible."

SECTION I — SKIN LESIONS:
Document any visible scars, raised spots, pigmented lesions, or atypical changes. For each: location, approximate size, morphology. Use: "image suggests", "features consistent with", "requires confirmation at in-person examination".

Write concisely. Be anatomically specific. Address EVERY lettered point. Do NOT score, rate, or make treatment recommendations."""


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
        model=model, messages=messages, max_tokens=max_tokens, temperature=0, seed=42,
    )
    choice  = response.choices[0]
    raw     = choice.message.content
    refusal = getattr(choice.message, 'refusal', None)
    print(f"[API] finish={choice.finish_reason} refusal={bool(refusal)} len={len(raw) if raw else 0}")
    if refusal or not raw or len(raw) < 20:
        raise ValueError(f"API refused or returned empty (finish={choice.finish_reason})")
    return raw


def _observe(openai_client, images_data: dict, model: str) -> str:
    """Step 1: image → plain-text clinical observations."""
    user_content = []
    if 'en_face' in images_data:
        img = images_data['en_face']
        user_content.append({"type": "image_url", "image_url": {"url": f"data:{img['media_type']};base64,{img['data']}"}})
    user_content.append({"type": "text", "text": OBSERVATION_PROMPT})
    messages = [
        {"role": "system", "content": "You are a dermatologist writing clinical observation notes from patient photographs."},
        {"role": "user",   "content": user_content},
    ]
    return _call_raw(openai_client, messages, model, max_tokens=900)


LANG_REQUIREMENT_EN = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE REQUIREMENT — CRITICAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALL text values in the JSON output MUST be written in English.
This applies to every string field: summary, findings, skin_tension, fatigue_factors, overall_perception, recommendations, disclaimer, and all others.
Do NOT use Polish words in any free-text field value. Use English anatomical and clinical terminology.
Examples of REQUIRED English:
  GOOD: "Mild tissue descent in the malar region"
  GOOD: "Mild laxity of the lower cheek"
  GOOD: "Slightly blurred jawline definition"
ENUM KEYS that must remain as specified fixed values regardless of language:
  nasilenie: brak | lagodny | umiarkowany | zaawansowany  (these are code values, keep them)
  priorytet: wysoki | sredni | niski  (code values, keep them)
  kategoria: skin_quality | pigment_vascular | eye_area | volume_contour | forehead_hairline | lesions | neck | skin_tension
  status: good | mild | moderate
  overall_perception.freshness: swiezy | neutralny | zmeczony  (code values, keep them)"""

LANG_REQUIREMENT_PL = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE REQUIREMENT — CRITICAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALL text values in the JSON output MUST be written in Polish (język polski).
This applies to every string field: summary, findings, skin_tension, fatigue_factors, overall_perception, recommendations, and all others.
Do NOT use English words in any field value. Use Polish anatomical and clinical terminology.
Examples of FORBIDDEN English in field values:
  BAD: "Slight tissue descent" → GOOD: "Niewielkie opadanie tkanek"
  BAD: "Mild laxity"          → GOOD: "Łagodna wiotkość"
  BAD: "Mildly blurred"       → GOOD: "Łagodnie zatarta\""""


def _patch_prompt_for_lang(prompt: str, lang: str) -> str:
    """Swap language requirement block and all Polish-language examples for English output."""
    if lang != 'en':
        return prompt

    # 1. Language requirement block
    prompt = prompt.replace(LANG_REQUIREMENT_PL, LANG_REQUIREMENT_EN)

    # 2. Generic "in Polish" / "po polsku" labels
    prompt = prompt.replace("in Polish", "in English")
    prompt = prompt.replace("po polsku", "in English")
    prompt = prompt.replace("(język polski)", "(English)")
    prompt = prompt.replace("Polish medical procedure name", "English medical procedure name")
    prompt = prompt.replace("po angielsku", "in English")

    # 2b. Output format field templates — replace Polish directives with English
    prompt = prompt.replace(
        '"biological_age_estimate": "<XX-XX lat — specific clinical sign>",',
        '"biological_age_estimate": "<XX-XX years — specific clinical sign>",')
    prompt = prompt.replace(
        '"freshness": "<świeży|neutralny|zmęczony>",',
        '"freshness": "<swiezy|neutralny|zmeczony>",')
    prompt = prompt.replace(
        '"apparent_age": "<młodszy niż wiek biologiczny|odpowiedni do wieku|starszy niż wiek biologiczny>",',
        '"apparent_age": "<younger than biological age|age-appropriate|older than biological age>",')
    prompt = prompt.replace(
        '"impression": "<one sentence in Polish: what the overall face communicates aesthetically — cause + effect + perception>"',
        '"impression": "<one sentence in English: what the overall face communicates aesthetically — cause + effect + perception>"')
    prompt = prompt.replace(
        '"primary": "<main anatomical factor creating tired appearance, in Polish — or \'brak cech zmęczenia\' if face looks fresh>",',
        '"primary": "<main anatomical factor creating tired appearance, in English — or \'no signs of fatigue\' if face looks fresh>",')
    prompt = prompt.replace(
        '"contributing": ["<factor in Polish>", "<factor in Polish>"],',
        '"contributing": ["<factor in English>", "<factor in English>"],')
    prompt = prompt.replace(
        '"explanation": "<one sentence: cause → effect → perceived fatigue, in Polish>"',
        '"explanation": "<one sentence: cause → effect → perceived fatigue, in English>"')
    prompt = prompt.replace(
        '"under_eye": "<po polsku: napięcie/wiotkość, efekt percepcyjny>",',
        '"under_eye": "<in English: tension/laxity, perceptual effect>",')
    prompt = prompt.replace(
        '"cheeks": "<po polsku: napięcie/opadanie tkanek, efekt percepcyjny>",',
        '"cheeks": "<in English: tension/tissue descent, perceptual effect>",')
    prompt = prompt.replace(
        '"jawline": "<po polsku: definicja linii żuchwy lub zatarcie przez opadanie tkanek>",',
        '"jawline": "<in English: jawline definition or blurring by tissue descent>",')
    prompt = prompt.replace(
        '"neck": "<po polsku: znalezisko lub \'Ocena szyi ograniczona przez kadr zdjęcia.\'>"',
        '"neck": "<in English: finding or \'Neck assessment limited by photo frame.\'>"')
    prompt = prompt.replace(
        '"disclaimer": "Dokumentacja kliniczna sporządzona na podstawie fotografii. Nie zastępuje badania lekarskiego.",',
        '"disclaimer": "Clinical documentation based on a photograph. Does not replace a medical examination.",')
    prompt = prompt.replace(
        '"name": "<finding name in Polish>",',
        '"name": "<finding name in English>",')
    prompt = prompt.replace(
        '"area": "<anatomical location in Polish>",',
        '"area": "<anatomical location in English>",')
    prompt = prompt.replace(
        '"wplyw_estetyczny": "<one sentence in Polish: cause → effect → perception>",',
        '"wplyw_estetyczny": "<one sentence in English: cause → effect → perception>",')
    prompt = prompt.replace(
        '"dlaczego_wazne": "<one sentence in Polish>",',
        '"dlaczego_wazne": "<one sentence in English>",')
    prompt = prompt.replace(
        '"co_moze_sie_poglebiac": "<one sentence in Polish — progresja bez interwencji>",',
        '"co_moze_sie_poglebiac": "<one sentence in English — progression without intervention>",')
    prompt = prompt.replace(
        '"co_wdrozyc_najpierw": "<one sentence in Polish — pierwszy krok>"',
        '"co_wdrozyc_najpierw": "<one sentence in English — first step>"')

    # 2c. FINDINGS_EXTENSION Polish section headers
    prompt = prompt.replace(
        "EXTENDED FIELDS — dodaj do tego samego JSON",
        "EXTENDED FIELDS — add to the same JSON")
    prompt = prompt.replace(
        "Uwzględnij w obiekcie JSON dwa dodatkowe pola na końcu:",
        "Include in the JSON object two additional fields at the end:")
    prompt = prompt.replace(
        '"nazwa zmiany po polsku"', '"finding name in English"')
    prompt = prompt.replace(
        '"lokalizacja anatomiczna po polsku"', '"anatomical location in English"')
    prompt = prompt.replace(
        '"jedno zdanie po polsku — wpływ na wygląd"', '"one sentence in English — aesthetic impact"')
    prompt = prompt.replace(
        '"jedno zdanie"', '"one sentence in English"')
    prompt = prompt.replace(
        '"jedno zdanie — progresja bez interwencji"', '"one sentence — progression without intervention"')
    prompt = prompt.replace(
        '"jedno zdanie — pierwszy krok"', '"one sentence — first step"')
    prompt = prompt.replace(
        "Uwzględnij 4–10 findings — tylko rzeczywiście widoczne lub sugerowane zmiany.",
        "Include 4–10 findings — only actually visible or suggested changes.")

    # 3. Procedure / treatment direction examples  (CLINICAL_PROMPT line)
    prompt = prompt.replace(
        "kierunek_postepowania: napięcie→RF mikroigłowa/mezoterapia/stymulatory/osocze/fibryna | pory/tekstura→peelingi/laser frakcyjny/RF mikroigłowa | przebarwienia→peelingi/laser frakcyjny | naczynka→laser naczyniowy | objętość policzków/owalu→filler HA | okolica podoczodołowa/tear trough→fibryna bogatokomórkowa/łagodne stymulatory (NIE filler HA — ryzyko obrzęku) | zmarszczki dynamiczne→toksyna botulinowa | lesions→elektrokoagulacja | szyja→RF mikroigłowa/mezoterapia/laser frakcyjny",
        "kierunek_postepowania: skin tension→microneedling RF/mesotherapy/biostimulators/PRP/PRF | pores/texture→chemical peels/fractional laser/microneedling RF | pigmentation→chemical peels/fractional laser | vascular/redness→vascular laser | cheek/oval volume→HA filler/biostimulators | periorbital/tear trough→platelet-rich fibrin (PRF)/gentle biostimulators (NOT HA filler — oedema risk) | dynamic wrinkles→botulinum toxin | lesions→electrocoagulation | neck→microneedling RF/mesotherapy/fractional laser"
    )

    # 4. Kierunki postępowania block (FINDINGS_EXTENSION)
    prompt = prompt.replace(
        "Kierunki postępowania (polskie terminy):\n"
        "napięcie/firmness/skin_tension → RF mikroigłowa, mezoterapia, stymulatory, osocze bogatopłytkowe, fibryna\n"
        "pory/tekstura → peelingi, laser frakcyjny, RF mikroigłowa\n"
        "przebarwienia → peelingi, laser frakcyjny\n"
        "naczynka/rumień → laser naczyniowy\n"
        "okolica podoczodołowa/tear trough → fibryna bogatokomórkowa (PRF), łagodne stymulatory tkankowe — NIGDY filler HA (ryzyko powikłań obrzękowych)\n"
        "zmarszczki dynamiczne → toksyna botulinowa\n"
        "objętość policzków/owalu → filler HA, stymulatory\n"
        "lesions → elektrokoagulacja\n"
        "szyja → RF mikroigłowa, mezoterapia, laser frakcyjny, stymulatory",
        "Treatment directions:\n"
        "skin tension/skin_tension → microneedling RF, mesotherapy, biostimulators, PRP, platelet-rich fibrin (PRF)\n"
        "pores/texture → chemical peels, fractional laser, microneedling RF\n"
        "pigmentation → chemical peels, fractional laser\n"
        "vascular/redness → vascular laser\n"
        "periorbital/tear trough → platelet-rich fibrin (PRF), gentle biostimulators — NEVER HA filler (oedema risk)\n"
        "dynamic wrinkles → botulinum toxin\n"
        "cheek/oval volume → HA filler, biostimulators\n"
        "lesions → electrocoagulation\n"
        "neck → microneedling RF, mesotherapy, fractional laser, biostimulators"
    )

    # 5. Recommendations example (CLINICAL_PROMPT)
    prompt = prompt.replace(
        '  BAD: "Stosuj krem z SPF"\n  GOOD: "Fotoprotekcja: mineralny SPF 50+ PA++++ codziennie rano — warunek skuteczności każdej interwencji aktywnej"',
        '  BAD: "Use sunscreen"\n  GOOD: "Photoprotection: mineral SPF 50+ PA++++ every morning — prerequisite for effectiveness of any active intervention"'
    )

    # 6. Example JSON block with Polish content — replace with English
    prompt = prompt.replace(
        '"summary": "Łuki jarzmowe wykazują symetryczną projekcję boczną bez utraty objętości, stanowiąc klinicznie korzystną cechę strukturalną środkowej trzeciej twarzy. W okolicy podoczodołowej obustronnie udokumentowano utratę objętości stopień 1 wg skali Barton, z silniejszym cieniem tear trough po lewej stronie, klinicznie istotną dla efektu zmęczenia twarzy. Priorytetem konsultacji jest ocena wskazań do regeneracji okolicy podoczodołowej."',
        '"summary": "The zygomatic arches demonstrate symmetric lateral projection without volume loss, representing a clinically favourable structural feature of the middle facial third. Bilateral periorbital volume loss grade 1 by the Barton scale is documented, with a more pronounced tear trough shadow on the left, clinically significant for the tired-face appearance. The consultation priority is assessment of indications for periorbital regeneration."'
    )
    prompt = prompt.replace(
        '"biological_age_estimate": "37–42 lat — rhytidy dynamiczne stopień 2 przy zewnętrznych kątach oczu oraz pory >0.4mm w strefie T nosa wskazują na przyspieszone fotostarzenie"',
        '"biological_age_estimate": "37–42 years — dynamic rhytids grade 2 at the lateral canthi and pores >0.4 mm in the T-zone indicate accelerated photoageing"'
    )
    prompt = prompt.replace(
        '"strongest_asset": "Łuki jarzmowe — symetryczna projekcja boczna w okolicy jarzmowo-skroniowej bez dokumentowanych ubytków objętości, rzadka cecha strukturalna w tej grupie wiekowej."',
        '"strongest_asset": "Zygomatic arches — symmetric lateral projection in the zygomatic-temporal region without documented volume deficits, a rare structural feature in this age group."'
    )
    prompt = prompt.replace(
        '"top_priority": "Utrata objętości w okolicy podoczodołowej lewej (tear trough stopień 1–2 wg skali Barton) pogłębia cień podoczodołowy i efekt chronicznego zmęczenia — bez interwencji defekt będzie narastał i utrwalał cień."',
        '"top_priority": "Volume loss in the left periorbital region (tear trough grade 1–2 by Barton scale) deepens the infraorbital shadow and chronic tired-face appearance — without intervention the defect will progress and the shadow will become permanent."'
    )
    prompt = prompt.replace(
        '"recommendations": [\n    "Tear trough: fibryna bogatokomórkowa (PRF) lub łagodne stymulatory — regeneracja okolicy podoczodołowej bez ryzyka obrzęku",\n    "Rhytidy dynamiczne okolicy oka: toksyna botulinowa 8–10j w mięsień okrężny oka obustronnie, co 4–5 miesięcy",\n    "Tekstura skóry: tretynoin 0.05% co drugi wieczór przez 6 tygodni, następnie 0.1% codziennie",\n    "Fotoprotekcja: mineralny SPF 50+ PA++++ codziennie rano",\n    "Pory i sebostaza strefy T: niacynamid 10% serum rano i wieczór przez min. 12 tygodni"\n  ]',
        '"recommendations": [\n    "Tear trough: platelet-rich fibrin (PRF) or gentle biostimulators — periorbital regeneration without oedema risk",\n    "Periorbital dynamic rhytids: botulinum toxin 8–10 U into orbicularis oculi bilaterally, every 4–5 months",\n    "Skin texture: tretinoin 0.05% every other evening for 6 weeks, then 0.1% daily",\n    "Photoprotection: mineral SPF 50+ PA++++ every morning",\n    "Pores and T-zone sebostasis: niacinamide 10% serum morning and evening for min. 12 weeks"\n  ]'
    )
    prompt = prompt.replace(
        '"finding": "Strefa T nosa i czoła z rozszerzonymi porami >0.4mm i niejednorodnym mikrorelief skóry; policzek lewy z ogniskami hiperpigmentacji pozapalnej."',
        '"finding": "T-zone of nose and forehead with enlarged pores >0.4 mm and uneven skin microrelief; left cheek with foci of post-inflammatory hyperpigmentation."'
    )
    prompt = prompt.replace(
        '"detail": [\n        "Strefa T (nos, czoło): pory >0.4mm, cechy sebostazy",\n        "Policzek lewy: 3–4 ogniska hiperpigmentacji pozapalnej ~3–5mm",\n        "Powierzchnia policzków: niejednorodny mikrorelief z lokalnymi nierównościami tekstury"\n      ]',
        '"detail": [\n        "T-zone (nose, forehead): pores >0.4 mm, signs of sebostasis",\n        "Left cheek: 3–4 foci of post-inflammatory hyperpigmentation ~3–5 mm",\n        "Cheek surface: uneven microrelief with local texture irregularities"\n      ]'
    )

    # 7. disclaimer
    prompt = prompt.replace(
        '"disclaimer": "Dokumentacja kliniczna sporządzona na podstawie fotografii. Nie zastępuje badania lekarskiego."',
        '"disclaimer": "Clinical documentation based on a photograph. Does not replace a medical examination."'
    )

    # 8. top_priority consequence language examples
    prompt = prompt.replace(
        '    "może nasilać efekt zmęczenia twarzy"\n    "pogłębia cień podoczodołowy i efekt chronicznego zmęczenia"\n    "bez interwencji defekt będzie postępował z wiekiem"',
        '    "may intensify the tired-face appearance"\n    "deepens the infraorbital shadow and chronic tired-face effect"\n    "without intervention the defect will progress with age"'
    )
    prompt = prompt.replace(
        '  BAD: "Poprawa jakości skóry"\n  GOOD: "Utrata objętości w okolicy podoczodołowej lewej (tear trough stopień 1–2 wg skali Barton) pogłębia cień podoczodołowy i wymaga interwencji — bez leczenia defekt będzie narastał i nasilał efekt chronicznego zmęczenia twarzy."',
        '  BAD: "Improvement of skin quality"\n  GOOD: "Volume loss in the left periorbital region (tear trough grade 1–2 Barton) deepens the infraorbital shadow and requires intervention — without treatment the defect will progress and the chronic tired-face appearance will worsen."'
    )

    # 9. summary sentence examples
    prompt = prompt.replace(
        '  BAD:  "Obniżone napięcie skóry."\n      GOOD: "Obniżone napięcie skóry policzków powoduje opadanie tkanek, co wpływa na odbiór zmęczenia twarzy."',
        '  BAD:  "Reduced skin tension."\n      GOOD: "Reduced cheek skin tension causes tissue descent, affecting the perceived tired-face appearance."'
    )

    # 10. "brak istotnych nieprawidłowości" fallback instruction
    prompt = prompt.replace(
        'write "brak istotnych nieprawidłowości klinicznych w [structure]"',
        'write "no significant clinical abnormalities in [structure]"'
    )

    # 11. FINDINGS_EXTENSION — definicje kategorii (Polish category definitions)
    prompt = prompt.replace(
        "Definicje kategorii:\n"
        "skin_quality → pory, tekstura, nawilżenie — skóra twarzy\n"
        "pigment_vascular → przebarwienia, naczynka, rumień\n"
        "eye_area → dolina łez (tear trough), cienie, obrzęki, zmarszczki okolicy oczu, napięcie powieki dolnej\n"
        "  WAŻNE dla eye_area: zawsze udokumentuj tear trough (głębokość), charakter cieni (naczyniowy/objętościowy/pigmentacyjny), czy obszar tworzy efekt zmęczenia\n"
        "volume_contour → objętość policzków, owal twarzy, linia żuchwy\n"
        "forehead_hairline → linia włosów, gęstość, czoło\n"
        "lesions → blizny, brodawki, włókniaki — ZAWSZE wymaga_potwierdzenia: true; użyj: \"obraz sugeruje\", \"cechy zgodne z\"\n"
        "neck → skóra szyi, napięcie, zmarszczki poziome, przebarwienia — jeśli niewidoczna: dodaj finding z nasilenie: \"brak\" i note \"Ocena ograniczona przez kadr\"\n"
        "skin_tension → napięcie skóry policzków, napięcie żuchwy, opadanie tkanek — wplyw_estetyczny MUSI zawierać: \"wpływa na odbiór zmęczenia twarzy\" lub \"nie wpływa istotnie na odbiór zmęczenia\"",
        "Category definitions:\n"
        "skin_quality → pores, texture, hydration — facial skin\n"
        "pigment_vascular → pigmentation, vascular changes, redness\n"
        "eye_area → tear trough, shadows, puffiness, periorbital lines, lower eyelid laxity\n"
        "  IMPORTANT for eye_area: always document tear trough (depth), shadow character (vascular/volumetric/pigmentary), whether area creates tired appearance\n"
        "volume_contour → cheek volume, facial oval, jawline\n"
        "forehead_hairline → hairline, density, forehead\n"
        "lesions → scars, warts, fibromas — ALWAYS wymaga_potwierdzenia: true; use: \"image suggests\", \"features consistent with\"\n"
        "neck → neck skin, tension, horizontal lines, pigmentation — if not visible: add finding with nasilenie: \"brak\" and note \"Assessment limited by frame\"\n"
        "skin_tension → cheek skin tension, jawline tension, tissue descent — wplyw_estetyczny MUST include: \"affects the tired-face appearance\" or \"does not significantly affect tired-face appearance\""
    )

    # 12. skin_health_note description
    prompt = prompt.replace(
        '"skin_health_note": "<jedno zdanie po polsku: dlaczego poprawa jakości skóry tej osoby zwiększa trwałość i przewidywalność efektów procedur estetycznych>"',
        '"skin_health_note": "<one sentence in English: why improving skin quality in this patient increases longevity and predictability of aesthetic procedures>"'
    )

    # 13. Final Polish note about eye_area
    prompt = prompt.replace(
        "Ten obszar ma kluczowy wpływ na odbiór zmęczenia twarzy — musi być udokumentowany w każdej analizie: eye_area finding.",
        "This area has a key impact on the tired-face appearance — must be documented in every analysis: eye_area finding."
    )

    # 14. CLINICAL_PROMPT forbidden phrases (Polish) — add English context
    prompt = prompt.replace(
        'FORBIDDEN generic phrases (these make documentation clinically invalid):\n'
        '  "zbliżone do normy", "obszary wymagające uwagi", "harmonijne", "dobrze zdefiniowane",\n'
        '  "wygląda naturalnie", "ogólnie dobra", "proporcje są dobre", "twarz jest symetryczna",\n'
        '  "wygląda zdrowo", "prawidłowy", "bez zastrzeżeń", "zadowalający"',
        'FORBIDDEN generic phrases (these make documentation clinically invalid):\n'
        '  "within normal limits", "areas requiring attention", "harmonious", "well-defined",\n'
        '  "looks natural", "generally good", "proportions are good", "face is symmetric",\n'
        '  "looks healthy", "normal", "no concerns", "satisfactory"'
    )

    # 15. Overall_perception and skin_health_note format placeholders
    prompt = prompt.replace(
        '"impression": "<one sentence in English: what the overall face communicates aesthetically — cause + effect + perception>"',
        '"impression": "<one sentence: what the overall face communicates aesthetically — cause + effect + perception>"'
    )

    return prompt


def _report(openai_client, observations: str, model: str, lang: str = 'pl') -> dict:
    """Step 2: observations text → structured JSON."""
    lang_name = 'English' if lang == 'en' else 'Polish'
    base_prompt = CLINICAL_PROMPT + FINDINGS_EXTENSION
    patched_prompt = _patch_prompt_for_lang(base_prompt, lang)
    prompt = (
        f"Format these clinical observation notes into structured {lang_name}-language JSON.\n\n"
        f"OBSERVATIONS:\n" + observations + "\n\n"
        f"Return ONLY valid JSON. All free-text values must be in {lang_name}.\n\n"
        + patched_prompt
    )
    messages = [
        {"role": "system", "content": f"You are a physician formatting clinical notes into structured JSON with all text in {lang_name}. Return only valid JSON, no markdown."},
        {"role": "user",   "content": prompt},
    ]
    raw = _call_raw(openai_client, messages, model, max_tokens=4500)
    return _extract_json(raw)


def analyze_face_with_ai(
    file_paths_dict: Dict[str, str],
    openai_client,
    model: str = "gpt-4o",
    lang: str = 'pl'
) -> Dict:
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

    # Step 1: observe — gpt-4o (vision)
    observations = _observe(openai_client, images_data, model)
    print(f"[OBSERVE OK] {len(observations)} chars")

    # Step 2: report — gpt-4o (reliable JSON, no image)
    result = _report(openai_client, observations, model, lang=lang)
    _validate_result(result)
    return result
