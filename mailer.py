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
    with smtplib.SMTP(cfg['host'], cfg['port'], timeout=15) as srv:
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
