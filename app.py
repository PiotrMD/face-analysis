import os
import uuid
import time
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv

import threading
import time as _time
from database import init_db, Analysis, ContactRequest, FollowUpEmail
from validators import validate_file_technical
from analysis import analyze_face_with_ai
from demo_data import DEMO_RESULT

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'face-analysis-dev-key-2026')

# Configuration
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Initialize database
init_db()

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
USE_MOCK_MODE = not OPENAI_API_KEY or 'sk-' not in OPENAI_API_KEY

if not USE_MOCK_MODE:
    openai_client = OpenAI(api_key=OPENAI_API_KEY, timeout=120.0)
    print(f"[OPENAI READY] key=...{OPENAI_API_KEY[-6:]}")
else:
    openai_client = None
    print(f"[NO API KEY] OPENAI_API_KEY={repr(OPENAI_API_KEY)} — mock mode active")

# In-memory storage for quick access (cache)
results_storage = {}

# Static file version for cache-busting
STATIC_VERSION = str(int(time.time()))


@app.context_processor
def inject_globals():
    from translations import TRANSLATIONS
    lang = session.get('lang', 'pl')
    if lang not in TRANSLATIONS:
        lang = 'pl'
    return {
        'static_version': STATIC_VERSION,
        'ga_id':       os.getenv('GA_MEASUREMENT_ID', ''),
        'og_base_url': os.getenv('APP_URL', 'https://www.estetykamedyczna.pl'),
        'lang': lang,
        't':    TRANSLATIONS[lang],
    }


@app.route('/set-lang/<lang>')
def set_lang(lang):
    if lang in ('pl', 'en'):
        session['lang'] = lang
    return redirect(request.referrer or '/')


def _followup_worker():
    """Daemon thread: sends scheduled follow-up emails every 5 minutes."""
    _time.sleep(30)  # let the app fully start first
    while True:
        try:
            from mailer import send_followup_day3, send_followup_day7
            base_url = os.getenv('APP_URL', 'http://127.0.0.1:5000')
            for fu in FollowUpEmail.get_pending():
                try:
                    if fu.email_type == 'day3':
                        send_followup_day3(fu.email, fu.full_name, fu.token or '', base_url)
                    elif fu.email_type == 'day7':
                        send_followup_day7(fu.email, fu.full_name)
                    fu.mark_sent()
                    print(f"[FOLLOWUP] sent {fu.email_type} → {fu.email}", flush=True)
                except Exception as e:
                    fu.mark_error(e)
                    print(f"[FOLLOWUP] FAILED {fu.email_type} → {fu.email}: {e}", flush=True)
        except Exception as e:
            print(f"[FOLLOWUP WORKER] error: {e}", flush=True)
        _time.sleep(300)  # check every 5 minutes


_worker = threading.Thread(target=_followup_worker, daemon=True, name="followup-worker")
_worker.start()


def _run_analysis(token: str, saved_paths: dict, lang: str = 'pl'):
    """
    Run OpenAI analysis. Returns result dict on success, None on failure.
    If no API key is configured, returns None immediately.
    """
    if USE_MOCK_MODE:
        print(f"[NO API KEY] Analysis unavailable — configure OPENAI_API_KEY. token={token}")
        return None

    client = openai_client or OpenAI(api_key=os.getenv('OPENAI_API_KEY', ''))
    try:
        print(f"[OPENAI CALL START] token={token} lang={lang}", flush=True)
        result = analyze_face_with_ai(saved_paths, client, lang=lang)
        print(f"[OPENAI CALL SUCCESS] token={token}", flush=True)
        return result
    except ValueError as e:
        msg = str(e)
        if any(msg.startswith(p) for p in ("EYES_BLOCKED:", "PHOTO_UNSUITABLE:", "POOR_PHOTO_QUALITY:")):
            raise
        import traceback
        tb = traceback.format_exc()
        print(f"[OPENAI CALL FAILED ValueError] {msg}\n{tb}", flush=True)
        return None
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[OPENAI CALL FAILED Exception] {type(e).__name__}: {e}\n{tb}", flush=True)
        return None


APP_VERSION = "75bcc0c-v6"  # hardcoded — update on each deploy to confirm Railway runs latest


@app.route('/version')
def version():
    import subprocess
    try:
        git_commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], text=True).strip()
    except Exception:
        git_commit = 'unavailable'
    return jsonify({'version': APP_VERSION, 'git': git_commit, 'started': STATIC_VERSION})


@app.route('/demo')
def demo():
    return render_template('results.html', result=DEMO_RESULT, token='demo', is_demo=True)


@app.route('/')
def index():
    analyses_count = Analysis.count_completed()
    return render_template('home.html', analyses_count=analyses_count)


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        return _analyze_inner()
    except Exception as e:
        print(f"[ANALYZE UNHANDLED] {type(e).__name__}: {e}")
        return jsonify({
            "success":    False,
            "error":      str(e),
            "error_type": type(e).__name__,
        }), 500


def _analyze_inner():
    from face_identity_validator import validate_faces

    # ── STEP 1: Validate single en face image ────────────────────────────────
    print("VALIDATION START")
    validation = validate_faces(request.files)
    print("VALIDATION RESULT:", validation)

    if not validation or not validation.get("is_valid"):
        print("BLOCKING ANALYSIS")
        return jsonify({
            "success":           False,
            "validation_failed": True,
            "validation_errors": validation.get("errors", ["Błąd walidacji zdjęcia"]),
            "errors":            validation.get("errors", ["Błąd walidacji zdjęcia"]),
        }), 422

    print("ANALYSIS CONTINUES")

    force = request.args.get('force') == '1'

    # ── STEP 2: Check en_face present ───────────────────────────────────────
    if 'en_face' not in request.files or not request.files['en_face'].filename:
        return jsonify({'success': False, 'error': 'Brak zdjęcia en face.'}), 400

    en_face_file = request.files['en_face']

    # ── STEP 3: Technical file validation ───────────────────────────────────
    is_valid, error_msg = validate_file_technical({'en_face': en_face_file})
    if not is_valid:
        print(f"[FILES FAIL] {error_msg}")
        return jsonify({'success': False, 'error': f'Nieprawidłowy plik: {error_msg}'}), 400

    print("[FILES OK]")

    # ── STEP 4: Save file ────────────────────────────────────────────────────
    token = str(uuid.uuid4())
    print(f"[TOKEN GENERATED] {token}")

    filename  = secure_filename(f"{token}_en_face_{en_face_file.filename}")
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    en_face_file.save(file_path)
    saved_paths = {'en_face': file_path}

    # ── STEP 5: Analysis ─────────────────────────────────────────────────────
    lang = session.get('lang', 'pl')
    cached = results_storage.get(token)
    if cached and not force:
        print(f"[CACHE HIT] token={token}")
        analysis_result = cached['analysis']
    else:
        if force: print("[FORCE CACHE BYPASS]")
        else: print(f"[CACHE MISS] token={token}")
        try:
            analysis_result = _run_analysis(token, saved_paths, lang=lang)
        except ValueError as e:
            msg = str(e)
            print(f"[ANALYZE ERROR] ValueError routing: {repr(msg[:200])}", flush=True)
            if 'EYES_BLOCKED' in msg:
                user_msg = ('Photo with sunglasses detected — eye area analysis not possible. Please upload a photo without sunglasses.'
                            if lang == 'en' else
                            'Wykryto zdjęcie z okularami przeciwsłonecznymi — analiza okolicy oczu niemożliwa. Wgraj zdjęcie bez okularów.')
            elif 'PHOTO_UNSUITABLE' in msg:
                user_msg = ('Photo is unsuitable for analysis. Please upload a clear en face photo.'
                            if lang == 'en' else
                            'Zdjęcie nieodpowiednie do analizy. Wgraj wyraźne zdjęcie en face.')
            elif 'POOR_PHOTO_QUALITY' in msg:
                user_msg = ('Photo quality is insufficient for reliable analysis. Please upload a clear, close-up en face photo — face straight, both eyes visible, no sunglasses.'
                            if lang == 'en' else
                            'Jakość zdjęcia nie pozwala na rzetelną analizę. Wgraj wyraźne zbliżenie twarzy en face — twarz prosto, obie oczy widoczne, brak okularów.')
            else:
                user_msg = str(e)
            return jsonify({
                "success": False,
                "validation_failed": True,
                "errors": [user_msg],
                "validation_errors": [user_msg],
            }), 422

    if analysis_result is None:
        Analysis.save_result(token, None, error="OpenAI call failed")
        return jsonify({"success": False, "error": "Analiza nie powiodła się. Spróbuj ponownie."}), 500

    # ── STEP 6: Store ────────────────────────────────────────────────────────
    Analysis.save_result(token, analysis_result)
    results_storage[token] = {'analysis': analysis_result, 'files': saved_paths}

    redirect_url = url_for('results', token=token) + ('?force=1' if force else '')
    print(f"[JSON RETURNED] redirect_url={redirect_url}")
    return jsonify({'success': True, 'redirect_url': redirect_url})


@app.route('/results/<token>')
def results(token):
    """Retrieve results from memory or database"""

    force_results = request.args.get('force') == '1'

    # Skip memory cache entirely when force=1
    if token in results_storage and not force_results:
        print(f"[CACHE HIT] token={token}")
        result_data = results_storage[token]['analysis']
        return render_template('results.html', result=result_data, token=token)

    if force_results:
        print(f"[FORCE CACHE BYPASS] /results — reading from DB, not memory cache")
    print(f"[CACHE MISS] token={token} — querying DB")
    # Try database (for persistence)
    analysis = Analysis.get_by_token(token)
    if analysis and analysis.analysis_result:
        import json
        result_data = json.loads(analysis.analysis_result)
        # Also cache in memory
        results_storage[token] = {'analysis': result_data}
        return render_template('results.html', result=result_data, token=token)

    # Error page
    if analysis and analysis.error:
        return render_template('results.html', error=f'Analysis failed: {analysis.error}'), 404

    # Token not found
    return render_template('results.html', error='Analysis not found'), 404


@app.route('/api/results/<token>')
def api_results(token):
    """JSON API endpoint"""

    # Try memory first
    if token in results_storage:
        return jsonify(results_storage[token]['analysis'])

    # Try database
    analysis = Analysis.get_by_token(token)
    if analysis and analysis.analysis_result:
        import json
        result_data = json.loads(analysis.analysis_result)
        # Cache in memory
        results_storage[token] = {'analysis': result_data}
        return jsonify(result_data)

    # Error
    if analysis and analysis.error:
        return jsonify({'error': analysis.error}), 422

    return jsonify({'error': 'Analysis not found'}), 404


@app.route('/contact', methods=['POST'])
def contact():
    from mailer import send_clinic_notification, send_patient_confirmation, send_patient_confirmation_with_link
    from datetime import datetime as dt

    try:
        data = request.get_json(silent=True) or {}
        full_name    = (data.get('full_name')    or '').strip()
        phone_number = (data.get('phone_number') or '').strip()
        email        = (data.get('email')        or '').strip()
        message      = (data.get('message')      or '').strip()
        token        = (data.get('token')        or '').strip()
        consent      = bool(data.get('consent'))

        if not full_name or not phone_number or not email:
            return jsonify({'success': False, 'error': 'Imię, telefon i adres e-mail są wymagane.'}), 400

        if not consent:
            return jsonify({'success': False, 'error': 'Wymagana jest zgoda na przetwarzanie danych.'}), 400

        if len(full_name) > 200 or len(phone_number) > 50 or len(email) > 200:
            return jsonify({'success': False, 'error': 'Wprowadzone dane są zbyt długie.'}), 400

        if '@' not in email or '.' not in email.split('@')[-1]:
            return jsonify({'success': False, 'error': 'Podaj prawidłowy adres e-mail.'}), 400

        # ── STEP 1: Save lead — must succeed before any email ───────────────
        ContactRequest.save(token or None, full_name, phone_number,
                            email=email, message=message or None)
        print(f"[CONTACT] lead saved name={full_name!r} phone={phone_number!r} email={email!r} token={token!r}", flush=True)

        timestamp = dt.now().strftime('%Y-%m-%d %H:%M')

        # ── STEP 2: Clinic notification ─────────────────────────────────────
        try:
            send_clinic_notification(full_name, phone_number, email, message, token, timestamp)
            print(f"[MAIL] clinic notification sent", flush=True)
        except Exception as e:
            print(f"[MAIL] clinic notification FAILED: {e}", flush=True)

        # ── STEP 3: Patient confirmation with results link ───────────────────
        try:
            base_url = os.getenv('APP_URL', 'http://127.0.0.1:5000')
            if token:
                send_patient_confirmation_with_link(email, full_name, token, base_url)
            else:
                send_patient_confirmation(email, full_name)
            print(f"[MAIL] patient confirmation sent to {email!r}", flush=True)
        except Exception as e:
            print(f"[MAIL] patient confirmation FAILED: {e}", flush=True)

        # ── STEP 4: Schedule follow-up emails (day 3 + day 7) ────────────────
        try:
            FollowUpEmail.schedule(email, full_name, token or None)
            print(f"[FOLLOWUP] scheduled day3+day7 for {email!r}", flush=True)
        except Exception as e:
            print(f"[FOLLOWUP] schedule FAILED: {e}", flush=True)

        return jsonify({'success': True})

    except Exception as e:
        print(f"[CONTACT ERROR] {e}", flush=True)
        return jsonify({'success': False, 'error': 'Nie udało się zapisać zgłoszenia. Spróbuj ponownie.'}), 500


@app.route('/feedback', methods=['POST'])
def feedback():
    data  = request.get_json(silent=True) or {}
    text  = (data.get('text') or '').strip()[:2000]
    token = (data.get('token') or '').strip()
    if text:
        print(f"[FEEDBACK] token={token!r} text={text!r}", flush=True)
        try:
            with open('feedback.log', 'a', encoding='utf-8') as f:
                import json as _json
                f.write(_json.dumps({'token': token, 'text': text}, ensure_ascii=False) + '\n')
        except Exception:
            pass
    return jsonify({'success': True})


@app.errorhandler(413)
def request_too_large(error):
    return jsonify({
        'success': False,
        'validation_failed': True,
        'errors': ['Plik jest za duży. Maksymalny rozmiar to 16 MB — skompresuj zdjęcie i spróbuj ponownie.'],
    }), 413


@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400


@app.errorhandler(422)
def unprocessable_entity(error):
    return jsonify({'error': 'Unprocessable entity'}), 422


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


def _free_port(port: int):
    """Kill any process currently listening on the given port."""
    import psutil, signal
    freed = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.net_connections(kind='inet'):
                if conn.laddr.port == port and conn.status == 'LISTEN':
                    if proc.pid == os.getpid():
                        continue
                    print(f"[STARTUP] killing stale process pid={proc.pid} name={proc.info['name']!r} on port {port}", flush=True)
                    proc.kill()
                    freed.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    if freed:
        import time as _time
        _time.sleep(1)


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    if port == 5000:
        _free_port(5000)
    app.run(debug=os.getenv('FLASK_DEBUG', 'False') == 'True',
            port=port, use_reloader=False, threaded=True)