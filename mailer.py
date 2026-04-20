import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import make_msgid, formatdate


def _cfg():
    return {
        'host':       os.getenv('SMTP_HOST', ''),
        'port':       int(os.getenv('SMTP_PORT', 587)),
        'user':       os.getenv('SMTP_USER', ''),
        'password':   os.getenv('SMTP_PASS', ''),
        'mail_from':  os.getenv('MAIL_FROM', ''),
        'to_primary': os.getenv('MAIL_TO_PRIMARY', ''),
        'to_cc':      os.getenv('MAIL_TO_CC', ''),
    }


def _send(to: str, subject: str, body: str, cc: str = None):
    cfg = _cfg()
    if not cfg['host'] or not cfg['user'] or not cfg['mail_from']:
        raise ValueError("SMTP not configured — set SMTP_HOST, SMTP_USER, MAIL_FROM in .env")

    msg = MIMEMultipart('alternative')
    msg['From']       = cfg['mail_from']
    msg['To']         = to
    msg['Subject']    = subject
    msg['Message-ID'] = make_msgid(domain='estetykamedyczna.pl')
    msg['Date']       = formatdate(localtime=True)
    if cc:
        msg['Cc'] = cc
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    recipients = [to] + ([cc] if cc else [])
    port = cfg['port']
    if port == 465:
        with smtplib.SMTP_SSL(cfg['host'], port, timeout=20) as srv:
            srv.ehlo()
            srv.login(cfg['user'], cfg['password'])
            srv.sendmail(cfg['mail_from'], recipients, msg.as_bytes())
    else:
        with smtplib.SMTP(cfg['host'], port, timeout=20) as srv:
            srv.ehlo()
            srv.starttls()
            srv.ehlo()
            srv.login(cfg['user'], cfg['password'])
            srv.sendmail(cfg['mail_from'], recipients, msg.as_bytes())


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
        "Poniżej znajdzie Pani/Pan link do swojej analizy estetycznej twarzy:\n"
        f"{results_url}\n\n"
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
    if not cfg['host'] or not cfg['user'] or not cfg['mail_from']:
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
