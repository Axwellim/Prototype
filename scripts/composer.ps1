$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$env:COMPOSER_HOME = Join-Path $projectRoot '.tools\composer-home'
$env:COMPOSER_CACHE_DIR = Join-Path $projectRoot '.tools\composer-cache'
& "$PSScriptRoot\php.ps1" "$projectRoot\composer.phar" @args
exit $LASTEXITCODE
