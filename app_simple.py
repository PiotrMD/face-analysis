import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
results_storage = {}


def generate_mock_result():
    """Generate mock analysis result"""
    return {
        "overall_score": 7.8,
        "summary": "Excellent facial proportions with strong symmetry and harmonious features. Well-defined structure.",
        "estimated_skin_age": 28,
        "strongest_asset": "Eye symmetry and definition",
        "top_priority": "Enhanced skin texture refinement",
        "recommendations": [
            "Regular hydration routine",
            "Sun protection (SPF 30+)",
            "Targeted eye care products",
            "Professional facial treatments quarterly"
        ],
        "disclaimer": "This is a mock analysis for demonstration."
    }


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    # Check files
    if 'en_face' not in request.files or 'profile_left' not in request.files or 'profile_right' not in request.files:
        return jsonify({'error': 'Missing files'}), 400

    files = {
        'en_face': request.files['en_face'],
        'profile_left': request.files['profile_left'],
        'profile_right': request.files['profile_right']
    }

    # Validate each file
    for key, file in files.items():
        if not file or file.filename == '':
            return jsonify({'error': f'File {key} is empty'}), 400

        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({'error': f'Invalid extension for {key}. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

        file.seek(0, os.SEEK_END)
        if file.tell() == 0:
            return jsonify({'error': f'File {key} is 0 bytes'}), 400
        file.seek(0)

    # Save files
    token = str(uuid.uuid4())
    saved_paths = {}
    for key, file in files.items():
        filename = secure_filename(f"{token}_{key}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        saved_paths[key] = filepath

    # Generate mock analysis
    analysis = generate_mock_result()

    # Store
    results_storage[token] = {
        'analysis': analysis,
        'files': saved_paths,
        'email': request.form.get('email', '')
    }

    return redirect(url_for('results', token=token))


@app.route('/results/<token>')
def results(token):
    if token not in results_storage:
        return render_template('results.html', error='Token not found'), 404

    result = results_storage[token]['analysis']
    return render_template('results.html', result=result, token=token)


@app.route('/api/results/<token>')
def api_results(token):
    if token not in results_storage:
        return jsonify({'error': 'Not found'}), 404

    return jsonify(results_storage[token]['analysis'])


if __name__ == '__main__':
    print("[APP_SIMPLE] Starting on port 8888")
    app.run(debug=False, port=8888)
