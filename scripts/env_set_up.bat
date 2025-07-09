@echo off

REM ===== HOW TO RUN =====
REM Open PowerShell in the Chatbot_Sakina folder, then run:
REM .\scripts\env_set_up.bat

REM Step 1: Create virtual environment (.venv)
echo Creating virtual environment in .venv...
python -m venv .venv

REM Step 2: Activate and install dependencies
echo Activating environment and installing requirements...
call .\.venv\Scripts\activate
pip install -r requirements.txt

echo ✅ SakinaAI virtual environment setup complete.
echo Run app with: .venv\Scripts\activate && streamlit run app.py

pause