$ErrorActionPreference = 'Stop'
$phpExecutable = if ($env:IMANTAG_PHP) { $env:IMANTAG_PHP } else { 'C:\xampp\php\php.exe' }
$env:PHP_INI_SCAN_DIR = Join-Path (Split-Path $PSScriptRoot -Parent) 'config\php'
& $phpExecutable @args
exit $LASTEXITCODE
