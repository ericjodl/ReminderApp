@echo off
REM Baut RapStudio.exe als Single-File Windows-Anwendung
setlocal

if not exist .venv (
    echo Lege virtuelle Umgebung an...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

pyinstaller ^
  --noconfirm ^
  --windowed ^
  --onefile ^
  --name RapStudio ^
  --collect-submodules sounddevice ^
  --collect-data soundfile ^
  run.py

echo.
echo Fertig. Die EXE liegt unter dist\RapStudio.exe
echo Hinweis: Fuer MP3-Import/Export muss ffmpeg im PATH liegen
echo (https://www.gyan.dev/ffmpeg/builds/  -> "release essentials").
endlocal
