@echo off
setlocal
set "PHP_EXE=%IMANTAG_PHP%"
if not defined PHP_EXE set "PHP_EXE=C:\xampp\php\php.exe"
set "PHP_INI_SCAN_DIR=%~dp0..\config\php"
"%PHP_EXE%" %*
exit /b %errorlevel%
