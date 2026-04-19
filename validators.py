import os
from typing import Dict, Tuple, Optional
from werkzeug.datastructures import FileStorage


ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}


def validate_file_technical(files_dict: Dict[str, FileStorage]) -> Tuple[bool, Optional[str]]:
    """
    Validate files technically — single en_face only.
    Returns:
        (is_valid, error_message)
    """
    required_keys = {'en_face'}

    provided_keys = set(k for k in files_dict.keys() if k in required_keys)
    missing = required_keys - provided_keys
    if missing:
        return False, f"Missing files: {', '.join(missing)}"

    for file_key in required_keys:
        file = files_dict[file_key]

        if file.filename == '':
            return False, f"File '{file_key}' is empty (no filename)"

        if '.' not in file.filename:
            return False, f"File '{file_key}' has no extension"

        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"File '{file_key}' has invalid extension '.{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size == 0:
            return False, f"File '{file_key}' is empty (0 bytes)"

        if file_size > 16 * 1024 * 1024:
            return False, f"File '{file_key}' is too large (max 16MB)"

    return True, None
