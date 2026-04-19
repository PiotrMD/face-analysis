#!/usr/bin/env python
import os
import sys
os.chdir('c:/Users/niedz/Documents/VISUAL STUDIO/face-analysis-2026')
sys.path.insert(0, os.getcwd())

# Fresh import
from dotenv import load_dotenv
load_dotenv(override=True)

print("Testing mock mode...")

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
USE_MOCK_MODE = not OPENAI_API_KEY or 'sk-' not in OPENAI_API_KEY

print(f"OPENAI_API_KEY={OPENAI_API_KEY}")
print(f"USE_MOCK_MODE={USE_MOCK_MODE}")

if USE_MOCK_MODE:
    print("MOCK MODE IS ON - Should use mock analysis")
else:
    print("REAL MODE - Will use OpenAI")

# Now start Flask
from app import app
app.run(debug=True, port=5000, use_reloader=False)
