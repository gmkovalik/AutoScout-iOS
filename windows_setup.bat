@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo FTC AutoScout Mobile - Windows Development
echo ==========================================
py -3.11 --version >nul 2>&1
if errorlevel 1 (
  echo Python 3.11 was not found. Install Python 3.11 and try again.
  pause
  exit /b 1
)
if not exist .venv py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed. Check the error above.
  pause
  exit /b 1
)
echo Setup complete. Run RUN_WINDOWS_PREVIEW.bat to preview the phone UI.
pause
