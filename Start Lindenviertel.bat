@echo off
setlocal
pushd "%~dp0"
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
if not exist "data\mosswood-lindenviertel-20260929.sqlite3" (
    "%PYTHON%" scripts\create_lindenviertel.py
    if errorlevel 1 goto done
)
"%PYTHON%" run.py --database data/mosswood-lindenviertel-20260929.sqlite3 --layout neighborhood-v1 --seed 73 --port 8769
:done
popd
pause
