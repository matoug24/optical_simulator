@echo off
setlocal
cd /d "%~dp0"
set "OPTICS_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%OPTICS_PYTHON%" goto bundled
where py >nul 2>nul
if errorlevel 1 goto ordinary
py -3 app.py
goto finished
:ordinary
python app.py
goto finished
:bundled
"%OPTICS_PYTHON%" app.py
:finished
if not errorlevel 1 goto end
echo.
echo See README.md for setup instructions.
pause
:end
endlocal
