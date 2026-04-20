import os
import requests


def _cfg():
    return {
        'resend_key':  os.getenv('RESEND_API_KEY', ''),
        'mail_from':   os.getenv('MAIL_FROM', 'analiza@estetykamedyczna.pl'),
        'to_primary':  os.getenv('MAIL_TO_PRIMARY', ''),
        'to_cc':       os.getenv('MAIL_TO_CC', ''),
    }


def _send(to: str, subject: str, body: str, cc: str = None):
    cfg = _cfg()
    api_key = cfg['resend_key']
    if not api_key:
        raise ValueError("RESEND_API_KEY not configured")

    payload = {
        "from":    cfg['mail_from'],
        "to":      [to],
        "subject": subject,
        "text":    body,
    }
    if cc:
        payload["cc"] = [cc]

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    if resp.status_code not in (200, 201):
        raise ValueError(f"Resend error {resp.status_code}: {resp.text[:200]}")


def send_clinic_notification(full_name: str, phone: str, email: str,
                              message: str, token: str, timestamp: str):
    cfg = _cfg()
    body = (
        "Nowe zgłoszenie konsultacji\n"
        "════════════════════════════\n\n"
        f"Imię i nazwisko: {full_name}\n"
        f"Telefon:         {phone}\n"
        f"E-mail:          {email}\n"
        f"Wiadomość:       {message or '-'}\n\n"
        f"Data zgłoszenia: {timestamp}\n"
        f"ID analizy:      {token or '-'}\n"
    )
    _send(
        to=cfg['to_primary'],
        subject="Nowe zgłoszenie konsultacji z aplikacji Analiza Estetyczna",
        body=body,
        cc=cfg['to_cc'] or None,
    )


def send_patient_confirmation_with_link(to_email: str, full_name: str, token: str, base_url: str):
    results_url = f"{base_url.rstrip('/')}/results/{token}"
    body = (
        f"Szanowna/y Pani/Pan {full_name},\n\n"
        "Dziękujemy za przesłanie zgłoszenia.\n\n"
        "Skontaktujemy się z Tobą możliwie szybko w godzinach pracy kliniki,\n"
        "wtorek–piątek 12:00–20:00.\n\n"
        "Serdecznie pozdrawiamy,\n"
        "Centrum Estetyki Medycznej\n"
        "dr n. med. Piotr Niedziałkowski\n\n"
        "Telefon: +48 690 584 584\n"
        "www.estetykamedyczna.pl\n"
    )
    _send(to=to_email, subject="Potwierdzenie zgłoszenia — Twoja analiza estetyczna", body=body)


def send_followup_day3(to_email: str, full_name: str, token: str, base_url: str):
    results_url = f"{base_url.rstrip('/')}/results/{token}" if token else ""
    link_line = f"\nLink do Twojej analizy: {results_url}\n" if results_url else ""
    body = (
        f"Szanowna/y Pani/Pan {full_name},\n\n"
        "Kilka dni temu przeprowadziła/ł Pani/Pan analizę estetyczną twarzy\n"
        "w Centrum Estetyki Medycznej.\n\n"
        "Chciałem przypomnieć, że zmiany udokumentowane w analizie —\n"
        "takie jak utrata napięcia skóry, objętości czy pogłębiające się\n"
        "zmarszczki — mają naturalną tendencję do postępowania z wiekiem.\n\n"
        "Wczesna interwencja daje znacznie lepsze efekty i jest mniej\n"
        "inwazyjna niż leczenie bardziej zaawansowanych zmian.\n"
        + link_line +
        "\nJeśli ma Pani/Pan pytania lub chciałaby/chciałby umówić się\n"
        "na konsultację — zapraszamy do kontaktu:\n\n"
        "Telefon: +48 690 584 584\n"
        "Godziny: wtorek–piątek 12:00–20:00\n\n"
        "Serdecznie pozdrawiamy,\n"
        "Centrum Estetyki Medycznej\n"
        "dr n. med. Piotr Niedziałkowski\n"
        "www.estetykamedyczna.pl\n"
    )
    _send(to=to_email, subject="Twoja analiza estetyczna — kilka słów od lekarza", body=body)


def send_followup_day7(to_email: str, full_name: str):
    body = (
        f"Szanowna/y Pani/Pan {full_name},\n\n"
        "Tydzień temu przeprowadziła/ł Pani/Pan analizę estetyczną twarzy.\n\n"
        "Gabinet pracuje wtorek–piątek w godzinach 12:00–20:00.\n"
        "W tym tygodniu mamy jeszcze wolne terminy konsultacyjne —\n"
        "konsultacja trwa ok. 30–45 minut i jest bezpłatna.\n\n"
        "Podczas konsultacji:\n"
        "• Omówimy wyniki analizy\n"
        "• Dobierzemy indywidualny plan postępowania\n"
        "• Odpowiemy na wszystkie pytania\n\n"
        "Aby umówić termin, wystarczy zadzwonić lub napisać:\n"
        "Telefon: +48 690 584 584\n"
        "Godziny: wtorek–piątek 12:00–20:00\n\n"
        "Serdecznie pozdrawiamy,\n"
        "Centrum Estetyki Medycznej\n"
        "dr n. med. Piotr Niedziałkowski\n"
        "www.estetykamedyczna.pl\n"
    )
    _send(to=to_email, subject="Wolne terminy konsultacji — Centrum Estetyki Medycznej", body=body)


def send_discount_code(to_email: str, lang: str = 'pl') -> None:
    """Send FACE10 discount code to the patient. Falls back to console log if SMTP not configured."""
    cfg = _cfg()
    if not cfg['resend_key']:
        if lang == 'pl':
            print(f"[MAIL TEST] Do: {to_email}", flush=True)
            print(f"[MAIL TEST] Temat: Twój kod po analizie twarzy", flush=True)
            print(f"[MAIL TEST] Treść: Kod FACE10 — -10% na konsultację lub zabieg, ważny 7 dni na umówienie wizyty.", flush=True)
        else:
            print(f"[MAIL TEST] To: {to_email}", flush=True)
            print(f"[MAIL TEST] Subject: Your code after face analysis", flush=True)
            print(f"[MAIL TEST] Body: Code FACE10 — -10% on consultation or treatment, valid 7 days to book.", flush=True)
        return

    if lang == 'pl':
        subject = "Twój kod po analizie twarzy"
        body = (
            "Dziękujemy za skorzystanie z analizy twarzy.\n\n"
            "Twój kod: FACE10\n\n"
            "-10% na konsultację lub zabieg medycyny estetycznej\n\n"
            "Kod jest ważny 7 dni na umówienie wizyty.\n"
            "Sama wizyta może odbyć się później.\n\n"
            "Jeśli podczas wizyty zdecydujesz się na zabieg,\n"
            "rabat zostanie zastosowany do zabiegu.\n\n"
            "Aby skorzystać, podaj kod podczas zapisu.\n\n"
            "—\n"
            "Centrum Estetyki Medycznej\n"
            "dr n. med. Piotr Niedziałkowski\n"
            "Tel. +48 690 584 584\n"
        )
    else:
        subject = "Your code after face analysis"
        body = (
            "Thank you for using our face analysis.\n\n"
            "Your code: FACE10\n\n"
            "-10% on a consultation or aesthetic medicine treatment\n\n"
            "The code is valid for 7 days to book an appointment.\n"
            "The appointment itself can take place later.\n\n"
            "If you decide on a treatment during your visit,\n"
            "the discount will be applied to the treatment.\n\n"
            "To use it, provide the code when booking your appointment.\n\n"
            "—\n"
            "Medical Aesthetics Centre\n"
            "dr Piotr Niedziałkowski MD\n"
            "Tel. +48 690 584 584\n"
        )

    _send(to=to_email, subject=subject, body=body)


def send_patient_confirmation(to_email: str, full_name: str):
    body = (
        f"Szanowna/y Pani/Pan {full_name},\n\n"
        "Dziękujemy za przesłanie zgłoszenia.\n\n"
        "Skontaktujemy się z Tobą możliwie szybko w godzinach pracy kliniki,\n"
        "wtorek–piątek 12:00–20:00.\n\n"
        "Serdecznie pozdrawiamy,\n"
        "Centrum Estetyki Medycznej\n"
        "dr n. med. Piotr Niedziałkowski\n\n"
        "Telefon: +48 690 584 584\n"
        "www.ocenazdrowia.pl\n"
        "www.estetykamedyczna.pl\n"
    )
    _send(
        to=to_email,
        subject="Potwierdzenie zgłoszenia konsultacji",
        body=body,
    )
