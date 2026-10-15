@echo off
setlocal
cd /d "%~dp0..\procesamiento"
"%~dp0..\.venv\Scripts\python.exe" -m uvicorn app.main:app_factory --factory --host 127.0.0.1 --port 8002 --workers 1 --no-access-log
exit /b %errorlevel%
