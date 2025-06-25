@echo off

REM ===== HOW TO RUN =====
REM Open PowerShell in the Chatbot_Sakina folder, then run:
REM .\scripts\env_set_up.bat

REM Step 1: Create conda environment
echo Creating conda environment 'SakinaAI' with Python 3.10...
conda create -y -n SakinaAI python=3.10

REM Step 2: Activate the environment and install requirements
echo Activating environment and installing requirements...
call conda activate SakinaAI
pip install -r requirements.txt

echo ✅ SakinaAI environment setup complete.
echo Run app with: streamlit run app.py

pause
