@echo off
setlocal
pushd "%~dp0"
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
"%PYTHON%" run.py --layout neighborhood-v1
if errorlevel 1 pause
popd
