document.addEventListener('DOMContentLoaded', function() {
    setupFileInputs();
    setupFormSubmission();
});

function showFormError(msg) {
    const el = document.getElementById('formError');
    if (el) { el.textContent = msg; el.style.display = 'block'; }
    console.error('[ANALYZE] Error:', msg);
}

function hideFormError() {
    const el = document.getElementById('formError');
    if (el) { el.style.display = 'none'; el.textContent = ''; }
}

function setupFileInputs() {
    const fileInputs = document.querySelectorAll('input[type="file"]');

    fileInputs.forEach(input => {
        const uploadArea = input.previousElementSibling;
        if (!uploadArea) return;
        const fileNameSpan = uploadArea.querySelector('.file-name');

        uploadArea.addEventListener('click', () => input.click());

        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file && fileNameSpan) {
                fileNameSpan.textContent = file.name;
                uploadArea.classList.add('filled');
            }
        });

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = 'var(--primary-color)';
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.style.borderColor = '';
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '';
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                input.files = files;
                input.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    });
}

function setupFormSubmission() {
    const form = document.getElementById('analysisForm');
    if (!form) {
        console.error('[ANALYZE] Form #analysisForm not found');
        return;
    }

    console.log('[ANALYZE] Form submission handler attached');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideFormError();

        console.log('[ANALYZE] Submit triggered');

        const en_face = document.getElementById('en_face').files[0];
        const profile_left = document.getElementById('profile_left').files[0];
        const profile_right = document.getElementById('profile_right').files[0];

        console.log('[ANALYZE] Files:', {
            en_face: en_face ? en_face.name : null,
            profile_left: profile_left ? profile_left.name : null,
            profile_right: profile_right ? profile_right.name : null
        });

        if (!en_face || !profile_left || !profile_right) {
            showFormError('Proszę wgrać wszystkie 3 zdjęcia przed analizą.');
            return;
        }

        const formData = new FormData();
        formData.append('en_face', en_face);
        formData.append('profile_left', profile_left);
        formData.append('profile_right', profile_right);

        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = 'Analizuję...';

        try {
            console.log('[ANALYZE] Sending POST /analyze...');

            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });

            console.log('[ANALYZE] Response:', response.status, 'redirected:', response.redirected, 'url:', response.url);

            const data = await response.json().catch(err => {
                console.error('[ANALYZE] JSON parse failed:', err);
                return {};
            });

            console.log('ANALYZE RESPONSE:', data);

            if (data.redirect_url) {
                console.log('[ANALYZE] Redirecting to:', data.redirect_url);
                window.location.href = data.redirect_url;
                return;
            }

            if (response.redirected) {
                console.log('[ANALYZE] Following redirect to:', response.url);
                window.location.href = response.url;
                return;
            }

            if (data.error) {
                showFormError('Błąd: ' + data.error);
            } else {
                showFormError('Nieoczekiwana odpowiedź serwera (status ' + response.status + ')');
            }

            submitBtn.disabled = false;
            submitBtn.textContent = originalText;

        } catch (error) {
            console.error('[ANALYZE] Network error:', error);
            showFormError('Błąd sieci: ' + error.message + '. Sprawdź czy serwer działa.');
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });
}
