@echo off
setlocal
set "COMPOSER_HOME=%~dp0..\.tools\composer-home"
set "COMPOSER_CACHE_DIR=%~dp0..\.tools\composer-cache"
call "%~dp0php.cmd" "%~dp0..\composer.phar" %*
exit /b %errorlevel%
