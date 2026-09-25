param(
    [Parameter(Mandatory = $true)][string]$Version
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Usa el formato mayor.menor.parche, por ejemplo 1.1.0" }

$parts = $Version.Split(".")
$tuple = "($($parts[0]), $($parts[1]), $($parts[2]), 0)"
$text = Get-Content version_info.txt -Raw

$text = $text -replace 'filevers=\([^)]*\)', "filevers=$tuple"
$text = $text -replace 'prodvers=\([^)]*\)', "prodvers=$tuple"
$text = $text -replace "'FileVersion', '[^']*'", "'FileVersion', '$Version'"
$text = $text -replace "'ProductVersion', '[^']*'", "'ProductVersion', '$Version'"

Set-Content version_info.txt $text -NoNewline -Encoding utf8
Write-Host "Version $Version escrita en version_info.txt" -ForegroundColor Green
Write-Host "Compila con .\build-release.ps1 y, para publicar, crea la etiqueta v$Version"
