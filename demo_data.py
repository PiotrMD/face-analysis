DEMO_RESULT = {
    "overall_score": 68,
    "confidence_global": "umiarkowana",
    "dominant_impression": ["neutralny"],
    "strengths": [
        "Zachowana pełna objętość policzków — brak utraty tkanki malarnej w rejonie jarzmowym",
        "Symetria strukturalna twarzy dobrze zachowana — brak istotnych asymetrii morfologicznych",
        "Wyraźnie zarysowana linia żuchwy bez cech opadania tkanek ani formowania się jowli",
        "Dobra gęstość włosów w strefie czołowej i skroniowej — linia włosów regularna",
        "Wargi symetryczne z zachowaną objętością — brak zmarszczek periorbitalnych",
    ],
    "features": {
        "under_eye":      {"score": 2, "confidence": "wysoka",      "notes": "Tear trough stopień 1 obustronnie — cień objętościowy, wyraźniejszy po lewej"},
        "midface_volume": {"score": 1, "confidence": "umiarkowana", "notes": "Objętość policzków zachowana, minimalne spłaszczenie podjarzmowe"},
        "tissue_descent": {"score": 1, "confidence": "umiarkowana", "notes": "Mildnie obniżone napięcie policzków, bez istotnego opadania tkanek"},
        "jawline_jowls":  {"score": 0, "confidence": "wysoka",      "notes": "Linia żuchwy wyraźna, brak jowli"},
        "skin_texture":   {"score": 2, "confidence": "wysoka",      "notes": "Pory >0.4mm w strefie T, niejednorodny mikrorelief policzków"},
        "skin_tone":      {"score": 1, "confidence": "umiarkowana", "notes": "Koloryt ogólnie równy, cechy dehydratacji powierzchniowej"},
        "neck":           {"score": 0, "confidence": "niska",       "notes": "Ocena ograniczona — szyja poza kadrem zdjęcia"},
        "hairline":       {"score": 0, "confidence": "wysoka",      "notes": "Linia włosów regularna, gęstość prawidłowa"},
    },
    "validation": {
        "image_valid": True,
        "face_count": 1,
        "face_fully_visible": True,
        "frontal_face": True,
        "neutral_expression": True,
        "eyes_visible": True,
        "occlusion_detected": False,
        "occlusion_type": None,
        "filter_detected": False,
        "lighting_ok": True,
        "sharpness_ok": True,
        "neck_visible": False,
        "hairline_visible": True,
        "warnings": [],
        "head_pose": {
            "yaw": "minimal",
            "pitch": "minimal",
            "roll": "minimal",
            "acceptable_for_analysis": True,
            "note": None,
        },
        "overall_impression": {
            "labels": ["neutralny"],
            "confidence": "umiarkowana",
            "reasons": [
                "delikatnie obciążona okolica podoczodołowa z cieniem tear trough",
                "zachowana objętość policzków i spokojna linia żuchwy",
            ],
        },
        "harmony": {
            "level": "umiarkowana",
            "confidence": "umiarkowana",
            "notes": [
                "Zachowana proporcja trzech pięter twarzy i wyraźna linia żuchwy",
                "Nieznacznie obciążona okolica podoczodołowa zaburza spójność górno-środkowej części twarzy",
            ],
        },
    },
    "harmony": {
        "level": "umiarkowana",
        "confidence": "umiarkowana",
        "notes": [
            "Zachowana proporcja trzech pięter twarzy i wyraźna linia żuchwy",
            "Nieznacznie obciążona okolica podoczodołowa zaburza spójność górno-środkowej części twarzy",
        ],
    },
    "neck_visible": False,
    "hairline_visible": True,
    "summary": (
        "Łuki jarzmowe wykazują symetryczną projekcję boczną bez udokumentowanej utraty objętości, "
        "stanowiąc klinicznie korzystną cechę strukturalną środkowej trzeciej twarzy. "
        "W okolicy podoczodołowej obustronnie stwierdzono utratę objętości stopień 1 wg skali Barton "
        "z silniejszym cieniem tear trough po lewej stronie, klinicznie istotną dla efektu zmęczenia twarzy. "
        "Priorytetem konsultacji jest ocena wskazań do regeneracji okolicy podoczodołowej i regulacji tekstury skóry strefy T."
    ),
    "biological_age_estimate": (
        "34–40 lat — rhytidy dynamiczne stopień 1–2 przy zewnętrznych kątach oczu "
        "oraz pory >0.4mm w strefie T nosa wskazują na wczesne fotostarzenie"
    ),
    "strongest_asset": (
        "Łuki jarzmowe — symetryczna projekcja boczna w okolicy jarzmowo-skroniowej "
        "bez dokumentowanych ubytków objętości; korzystna cecha strukturalna w tej grupie wiekowej."
    ),
    "top_priority": (
        "Utrata objętości w okolicy podoczodołowej lewej (tear trough stopień 1 wg skali Barton) "
        "pogłębia cień podoczodołowy i efekt chronicznego zmęczenia — bez interwencji defekt "
        "będzie narastał z wiekiem i utrwalał percepcję zmęczenia twarzy."
    ),
    "recommendations": [
        "Tear trough: fibryna bogatokomórkowa (PRF) — regeneracja okolicy podoczodołowej bez ryzyka obrzęku",
        "Rhytidy dynamiczne okolicy oka: toksyna botulinowa 8–10j w mięsień okrężny oka obustronnie, co 4–5 miesięcy",
        "Tekstura skóry: tretynoin 0.05% co drugi wieczór przez 6 tygodni, następnie 0.1% codziennie",
        "Fotoprotekcja: mineralny SPF 50+ PA++++ codziennie rano — warunek skuteczności każdej procedury aktywnej",
        "Pory i sebostaza strefy T: niacynamid 10% serum rano i wieczór przez min. 12 tygodni",
    ],
    "category_scores": {
        "symmetry":        8,
        "proportions":     8,
        "aging_signs":     6,
        "skin_quality":    5,
        "eye_area":        5,
        "lips_lower_face": 7,
        "hairline_hair":   8,
    },
    "key_findings": [
        {"section": "symmetry",        "finding": "Symetria strukturalna zachowana; minimalna asymetria kątów ust ~1mm", "status": "good",     "score": 8},
        {"section": "proportions",     "finding": "Proporcje twarzy zbliżone do optymalnych; dolna trzecia nieznacznie dominująca", "status": "good",     "score": 8},
        {"section": "aging_signs",     "finding": "Rhytidy dynamiczne stopień 1–2 przy kątach oczu; fałd nosowo-wargowy stopień 1–2", "status": "mild",     "score": 6},
        {"section": "skin_quality",    "finding": "Strefa T: pory >0.4mm, cechy sebostazy; policzki: niejednorodny mikrorelief", "status": "mild",     "score": 5},
        {"section": "eye_area",        "finding": "Tear trough stopień 1 obustronnie; cień podoczodołowy charakteru objętościowego", "status": "mild",     "score": 5},
        {"section": "lips_lower_face", "finding": "Wargi symetryczne, objętość umiarkowana; brak zmarszczek periorbitalnych", "status": "good",     "score": 7},
        {"section": "hairline_hair",   "finding": "Linia włosów regularna; gęstość prawidłowa; czoło średniej wysokości", "status": "good",     "score": 8},
    ],
    "sections": {
        "symmetry": {
            "status": "good",
            "finding": "Symetria strukturalna twarzy zachowana; minimalna asymetria kątów ust ~1mm, nieistotna klinicznie",
            "detail": [
                "Łuki jarzmowe: symetryczna projekcja obustronna bez dokumentowanej różnicy",
                "Kąty ust: asymetria ~1mm — poniżej progu klinicznej istotności",
                "Oś pionowa twarzy: prosta, bez istotnego odchylenia od linii środkowej",
            ],
        },
        "proportions": {
            "status": "good",
            "finding": "Proporcje twarzy zbliżone do optymalnych; dolna trzecia nieznacznie dominująca",
            "detail": [
                "Trzecia górna (czoło): proporcjonalna, wysokość średnia",
                "Trzecia środkowa (oczy–nos): proporcjonalna",
                "Trzecia dolna (nos–broda): nieznacznie dominująca +2–3mm",
            ],
        },
        "aging_signs": {
            "status": "mild",
            "finding": "Rhytidy dynamiczne stopień 1–2 przy kątach oczu; fałd nosowo-wargowy stopień 1–2 obustronnie",
            "detail": [
                "Kurze łapki: stopień 1–2, dynamiczne, przy skurczu mięśnia okrężnego oka",
                "Fałd nosowo-wargowy: stopień 1–2 obustronnie, symetryczne",
                "Napięcie skóry policzków: mildnie obniżone, bez istotnego opadania tkanek",
            ],
        },
        "skin_quality": {
            "status": "mild",
            "finding": "Strefa T z rozszerzonymi porami >0.4mm i cechami sebostazy; policzki z niejednorodnym mikrorelief",
            "detail": [
                "Strefa T (nos, czoło): pory >0.4mm, cechy sebostazy",
                "Policzki: niejednorodny mikrorelief, lokalne nierówności tekstury",
                "Nawodnienie skóry: obraz sugeruje odwodnienie powierzchniowe",
            ],
        },
        "eye_area": {
            "status": "mild",
            "finding": "Tear trough stopień 1 obustronnie; cień podoczodołowy o charakterze objętościowym; brak obrzęków",
            "detail": [
                "Tear trough lewy: stopień 1 wg skali Barton, cień wyraźniejszy",
                "Tear trough prawy: stopień 1, cień łagodniejszy",
                "Skóra powieki dolnej: delikatna krepowatość, napięcie zachowane",
            ],
        },
        "lips_lower_face": {
            "status": "good",
            "finding": "Wargi symetryczne z umiarkowaną objętością; brak istotnych zmarszczek periorbitalnych",
            "detail": [
                "Warga górna: objętość umiarkowana, philtrum dobrze zarysowane",
                "Warga dolna: proporcjonalna do górnej",
                "Kąty ust: symetryczne, bez opadania kątów",
            ],
        },
        "hairline_hair": {
            "status": "good",
            "finding": "Linia włosów regularna; gęstość prawidłowa w strefie czołowej i skroniowej",
            "detail": [
                "Linia włosów: regularna, bez cech recesji",
                "Strefa skroniowa: gęstość prawidłowa",
                "Czoło: wysokość średnia, proporcjonalna do twarzy",
            ],
        },
    },
    "overall_perception": {
        "freshness": "neutralny",
        "apparent_age": "odpowiedni do wieku",
        "impression": (
            "Twarz sprawia wrażenie zadbana i symetryczna, jednak cień podoczodołowy "
            "i niejednorodna tekstura skóry strefy T tworzą subtelny efekt zmęczenia, "
            "który można skutecznie zniwelować ukierunkowanymi interwencjami."
        ),
    },
    "fatigue_factors": {
        "primary": "Cień podoczodołowy — utrata objętości tear trough stopień 1 obustronnie",
        "contributing": [
            "Niejednorodna tekstura skóry policzków",
            "Rhytidy dynamiczne stopień 1–2 przy kątach oczu",
        ],
        "explanation": (
            "Utrata objętości w okolicy podoczodołowej pogłębia cień anatomiczny, co w połączeniu "
            "z wczesnymi rhytidami dynamicznymi tworzy wrażenie chronicznego zmęczenia pomimo "
            "dobrego ogólnego stanu tkanek."
        ),
    },
    "skin_tension": {
        "under_eye": "Delikatna krepowatość skóry powieki dolnej; napięcie zachowane; wpływ na odbiór zmęczenia minimalny",
        "cheeks": "Napięcie policzków mildnie obniżone; malar fat pad w prawidłowej pozycji; brak istotnego opadania tkanek",
        "jawline": "Linia żuchwy wyraźna; brak jowli; minimalne zatarcie w okolicy kąta żuchwy",
        "neck": "Ocena szyi ograniczona przez kadr zdjęcia.",
    },
    "disclaimer": "Dokumentacja kliniczna sporządzona na podstawie fotografii. Nie zastępuje badania lekarskiego.",
    "skin_health_note": (
        "Poprawa bariery skórnej i regulacja sebostazy zwiększy trwałość efektów procedur aktywnych "
        "i zmniejszy ryzyko powikłań pozapalnych."
    ),
    "findings": [
        {
            "id": "tear_trough_bilateral",
            "name": "Tear trough obustronny",
            "area": "Okolica podoczodołowa obustronna",
            "kategoria": "eye_area",
            "nasilenie": "lagodny",
            "priorytet": "wysoki",
            "wplyw_estetyczny": "Utrata objętości w okolicy podoczodołowej pogłębia cień anatomiczny i tworzy efekt chronicznego zmęczenia twarzy.",
            "kierunek_postepowania": ["fibryna bogatokomórkowa (PRF)", "łagodne stymulatory tkankowe"],
            "wymaga_potwierdzenia": False,
            "dlaczego_wazne": "Tear trough to najczęstszy czynnik tworzący efekt zmęczenia — interwencja daje wyraźną poprawę percepcji twarzy.",
            "co_moze_sie_poglebiac": "Bez interwencji defekt będzie narastał z wiekiem wraz z postępującą utratą objętości.",
            "co_wdrozyc_najpierw": "PRF lub stymulatory tkankowe w okolicy podoczodołowej — ocena wskazań podczas konsultacji.",
        },
        {
            "id": "skin_texture_tzone",
            "name": "Rozszerzone pory i sebostaza strefy T",
            "area": "Strefa T: czoło, nos",
            "kategoria": "skin_quality",
            "nasilenie": "lagodny",
            "priorytet": "sredni",
            "wplyw_estetyczny": "Rozszerzone pory i cechy sebostazy w strefie T tworzą niejednorodny mikrorelief, widoczny na fotografiach i przy bliskim oglądaniu.",
            "kierunek_postepowania": ["peelingi chemiczne", "laser frakcyjny", "RF mikroigłowa"],
            "wymaga_potwierdzenia": False,
            "dlaczego_wazne": "Poprawa tekstury skóry zwiększa trwałość efektów procedur wypełniających i botulinowych.",
            "co_moze_sie_poglebiac": "Bez leczenia pory mogą się dalej poszerzać; sebostaza sprzyja powikłaniom pozapalnym.",
            "co_wdrozyc_najpierw": "Niacynamid 10% + tretynoin 0.05% jako przygotowanie skóry — 8–12 tygodni przed procedurami laserowymi.",
        },
        {
            "id": "crow_feet_dynamic",
            "name": "Rhytidy dynamiczne okolicy oczu",
            "area": "Zewnętrzne kąty oczu obustronna",
            "kategoria": "eye_area",
            "nasilenie": "lagodny",
            "priorytet": "sredni",
            "wplyw_estetyczny": "Kurze łapki stopień 1–2 widoczne przy skurczu mięśnia okrężnego oka; w spoczynku nieznaczne.",
            "kierunek_postepowania": ["toksyna botulinowa"],
            "wymaga_potwierdzenia": False,
            "dlaczego_wazne": "Wczesna interwencja zapobiega utrwaleniu rhytidów dynamicznych w statyczne.",
            "co_moze_sie_poglebiac": "Rhytidy dynamiczne utrwalają się z czasem w statyczne — wymagające trudniejszego leczenia.",
            "co_wdrozyc_najpierw": "Toksyna botulinowa 8–10j w mięsień okrężny oka obustronnie.",
        },
        {
            "id": "skin_tension_cheeks",
            "name": "Obniżone napięcie skóry policzków",
            "area": "Policzki obustronna",
            "kategoria": "skin_tension",
            "nasilenie": "lagodny",
            "priorytet": "sredni",
            "wplyw_estetyczny": "Mildnie obniżone napięcie skóry policzków wpływa subtelnie na odbiór zmęczenia twarzy.",
            "kierunek_postepowania": ["RF mikroigłowa", "mezoterapia", "osocze bogatopłytkowe"],
            "wymaga_potwierdzenia": False,
            "dlaczego_wazne": "Wczesne leczenie napięcia skóry zapobiega progresji do istotnego opadania tkanek.",
            "co_moze_sie_poglebiac": "Bez interwencji napięcie będzie dalej się obniżać, nasilając efekt opadania policzków.",
            "co_wdrozyc_najpierw": "RF mikroigłowa — 3 sesje co 4–6 tygodni jako program liftingujący.",
        },
        {
            "id": "neck_assessment_limited",
            "name": "Ocena szyi — ograniczona przez kadr",
            "area": "Szyja",
            "kategoria": "neck",
            "nasilenie": "brak",
            "priorytet": "niski",
            "wplyw_estetyczny": "Ocena szyi niemożliwa ze względu na kadr zdjęcia — do oceny podczas konsultacji osobistej.",
            "kierunek_postepowania": [],
            "wymaga_potwierdzenia": True,
            "dlaczego_wazne": "Szyja jest istotnym elementem oceny estetycznej — wymaga oceny podczas konsultacji.",
            "co_moze_sie_poglebiac": "Nieocenione — wymaga badania osobistego.",
            "co_wdrozyc_najpierw": "Ocena podczas konsultacji osobistej.",
        },
    ],
}
