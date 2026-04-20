# Checklista developerska — face-analysis-2026

Uruchom po każdej istotnej zmianie w projekcie.

---

## Szybka weryfikacja automatyczna

```bash
python dev_check.py
```

Pokrywa: upload, walidację, komunikaty błędów, tłumaczenia, strukturę danych, różnorodność zabiegów, bezpieczeństwo treści, renderowanie.

Dla testów z prawdziwym API OpenAI:

```bash
python diag_test.py --stage1
```

Pokrywa: poprawność JSON, różnicowanie wyników, pokrywanie się zabiegów między zdjęciami.

---

## Pełna checklista

### 1. Upload zdjęcia

- [ ] Wgraj zdjęcie przez formularz — strona przechodzi do wyników
- [ ] Wgraj przez kamerę (mobilna) — zdjęcie trafia do analizy
- [ ] Wgraj plik > 16 MB — pojawia się komunikat o za dużym pliku
- [ ] Brak pliku + kliknięcie "Analizuj" — komunikat o braku zdjęcia

```bash
# Automatycznie:
python dev_check.py
# Szukaj: "Empty file upload rejected", "Non-image file upload rejected"
```

---

### 2. Walidacja zdjęcia

- [ ] Zdjęcie z okularami — komunikat "Na zdjęciu wykryto okulary. Zdejmij okulary..."
- [ ] Zdjęcie niewyraźne — komunikat "Zdjęcie jest zbyt niewyraźne..."
- [ ] Zdjęcie z filtrem — komunikat "Wykryto filtr upiększający..."
- [ ] Zdjęcie z boku — komunikat "Twarz jest zbyt mocno obrócona..."
- [ ] Komunikat zawiera wskazówkę co poprawić (hint pod błędem)

```bash
# Sprawdź 8 kodów i ich treść:
python -c "
from validation_messages import get_message, get_hint
for code in ['no_face','multiple_faces','glasses','filter','low_light','blur','bad_angle','incomplete_face']:
    print(f'{code}:')
    print(f'  PL: {get_message(code, \"pl\")}')
    print(f'  hint: {get_hint(code, \"pl\")}')
"
```

---

### 3. Poprawne zdjęcia nie są zbyt często odrzucane

- [ ] Wyraźne zdjęcie en face bez okularów — przechodzi walidację
- [ ] Wskaźnik odrzuceń poprawnych zdjęć poniżej ~10%
- [ ] Blurness threshold nie jest za restrykcyjny (OpenCV Laplacian < 5.0)

```bash
# Sprawdź Stage 1 na zestawie zdjęć testowych:
python diag_test.py --stage1
# Szukaj: "[Stage 1] accepted" vs "[Stage 1] REJECT"
```

Próg blur w `pipeline/stage1_validate.py`:
```python
if blur_val < 5.0:   # twardy blok
if blur_val < 15.0:  # ostrzeżenie tylko
```

---

### 4. OpenAI zwraca poprawny JSON

- [ ] Brak błędu `[STAGE2 ERROR] JSON parse failed`
- [ ] Brak błędu `AnalysisError`
- [ ] Wynik zawiera wszystkie 16 pól scores
- [ ] Pola scores są liczbami 1–10, nie napisami

```bash
python diag_test.py --model gpt-4o
# Szukaj: "[OK]" przy każdym zdjęciu, brak "[FAIL]"
# Wyniki JSON w test_results/*.json
```

Logi aplikacji — szukaj:
```
[PIPELINE SUCCESS]
[STAGE2 WARN] — akceptowalne, ale sprawdź co znormalizowano
[STAGE2 ERROR] — problem do naprawy
```

---

### 5. Wynik jest różny dla różnych zdjęć

- [ ] Dwa różne zdjęcia dają różne score'y
- [ ] Mean field difference > 1.5 między parami zdjęć
- [ ] Żadne pole nie ma stdev < 0.8 na zestawie ≥ 3 zdjęć

```bash
python diag_test.py --stage1
# Szukaj sekcji "PAIRWISE SIMILARITY" i "DIFFERENTIATION REPORT"
# PASS: "No differentiation issues detected"
# FAIL: "SUSPICIOUS: ... are very similar"
```

---

### 6. Rekomendacje zabiegów nie są stale takie same

- [ ] Różne profile słabych obszarów → różne zabiegi
- [ ] Brak "TREATMENT OVERLAP" flagowania w diag_test.py

```bash
# Automatycznie — 3 różne profile:
python dev_check.py
# Szukaj: "recommend_treatments() varies across profiles — PASS"

# Z prawdziwymi zdjęciami:
python diag_test.py --stage1
# Szukaj sekcji "PAIRWISE SIMILARITY" -> "Shared treatments"
# Akceptowalne: <= 3 wspólnych zabiegów między parą zdjęć
```

---

### 7. Wersja polska i angielska są spójne

- [ ] Liczba kluczy tłumaczeń PL == EN
- [ ] Demo działa w obu językach (`/demo` + `/set-lang/en`)
- [ ] Komunikaty błędów walidacji mają wersję PL i EN
- [ ] Tytuł strony wyników: "Wirtualna analiza twarzy" / "Virtual Face Analysis"

```bash
# Automatycznie:
python dev_check.py
# Szukaj: "PL and EN translation keys match — PASS"

# Ręcznie:
# 1. Otwórz /demo — sprawdź PL
# 2. Kliknij EN — sprawdź angielski tytuł i etykiety
```

---

### 8. Ekran mobilny jest czytelny

- [ ] Chrome DevTools: ustaw 390px szerokości (iPhone 15)
- [ ] Tytuł "Wirtualna analiza twarzy" widoczny bez scrolla
- [ ] Liczba wyniku (np. "7/10") czytelna, nie ucinam
- [ ] Chipy mocnych stron / obszarów do poprawy zawijają się poprawnie
- [ ] Przyciski CTA (Umów konsultację / telefon) są pełnej szerokości
- [ ] Topbar minimalny — tylko brand + lang + telefon
- [ ] Sekcja "Szczegółowe oceny" jest zwinięta domyślnie

Sprawdź rozmiary:
```css
/* Oczekiwane breakpointy w style.css */
@media (max-width: 480px) { ... }  /* iPhone SE i mniejsze */
```

---

### 9. Błędy są jasne dla użytkownika

- [ ] Każdy komunikat błędu zawiera: co jest nie tak + co zrobić
- [ ] Nie ma komunikatu "Error 422" ani "Unexpected response"
- [ ] Hint wyświetla się pod głównym błędem (szare tło, strzałka)
- [ ] Komunikat nie używa żargonu technicznego

Sprawdź wygląd bloku błędu:
```html
<!-- Oczekiwana struktura w DOM po odrzuceniu: -->
<ul class="vblock__list">
  <li>Na zdjęciu wykryto okulary.</li>
</ul>
<p class="vblock__hint">
  Zdejmij okulary i zrób nowe zdjęcie — ...
</p>
```

---

### 10. Wynik nie brzmi jak diagnoza medyczna

- [ ] Brak słów: "rosacea", "trądzik różowaty", "rozpoznanie", "diagnoza"
- [ ] Brak sformułowań probabilistycznych: "możliwe", "prawdopodobne"
- [ ] Sekcja `health_note` nie wymienia chorób ani leków
- [ ] `result.intro` to zdanie o kondycji skóry, nie diagnoza

```bash
# Automatycznie — sprawdź prompty:
python dev_check.py
# Szukaj: "No diagnosis language in active prompts — PASS"

# Ręcznie — sprawdź wynik z prawdziwego zdjęcia:
python diag_test.py --stage1
# W pliku test_results/*.json sprawdź pole "health_note"
# Nie powinno zawierać: nazw chorób, leków, "wymaga leczenia"
```

---

## Szybkie komendy

```bash
# Szybka weryfikacja bez API (po każdej zmianie kodu):
python dev_check.py

# Pełny test z API (przed deployem):
python diag_test.py --stage1

# Test konkretnego zdjęcia:
python diag_test.py sciezka/do/zdjecia.jpg --stage1

# Test w języku angielskim:
python diag_test.py --lang en --stage1

# Demo strony wyników:
# http://localhost:5000/demo
# http://localhost:5000/demo (po /set-lang/en)
```

---

## Pliki kluczowe

| Plik | Co robi |
|---|---|
| `pipeline/stage1_validate.py` | Walidacja zdjęcia (OpenCV + AI) |
| `pipeline/stage2_score.py` | Analiza i scoring (GPT-4o) |
| `pipeline/run.py` | Orkiestrator — łączy Stage 1 + 2 |
| `validation_messages.py` | Komunikaty błędów dla użytkownika |
| `treatments.py` | Reguły rekomendacji zabiegów |
| `prompts.py` | Prompty systemowe dla GPT |
| `translations.py` | Wszystkie teksty PL + EN |
| `templates/results.html` | Ekran wyników |
| `static/style.css` | Style (sekcja `RESULTS PAGE` na końcu) |
| `dev_check.py` | Ten skrypt |
| `diag_test.py` | Testy z prawdziwym API |
