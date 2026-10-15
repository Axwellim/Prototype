@echo off
setlocal
cd /d "%~dp0..\laravel"
call "%~dp0php.cmd" artisan documentos:trabajar %*
exit /b %errorlevel%
