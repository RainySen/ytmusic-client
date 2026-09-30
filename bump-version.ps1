param(
    [Parameter(Mandatory = $true)][string]$Version,
    [switch]$Publish
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Version = $Version -replace '^v\.?', ''
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Usa el formato mayor.menor.parche, por ejemplo 1.3.0" }

$parts = $Version.Split(".")
$tuple = "($($parts[0]), $($parts[1]), $($parts[2]), 0)"
$text = Get-Content version_info.txt -Raw

$text = $text -replace 'filevers=\([^)]*\)', "filevers=$tuple"
$text = $text -replace 'prodvers=\([^)]*\)', "prodvers=$tuple"
$text = $text -replace "'FileVersion', '[^']*'", "'FileVersion', '$Version'"
$text = $text -replace "'ProductVersion', '[^']*'", "'ProductVersion', '$Version'"

Set-Content version_info.txt $text -NoNewline -Encoding utf8
Write-Host "Version $Version escrita en version_info.txt" -ForegroundColor Green

if (-not $Publish) {
    Write-Host "Compila con .\build-release.ps1, o publica con .\bump-version.ps1 $Version -Publish"
    return
}

$tag = "v$Version"
git rev-parse -q --verify "refs/tags/$tag" | Out-Null
if ($LASTEXITCODE -eq 0) { throw "La etiqueta $tag ya existe; usa una version nueva" }

git add version_info.txt
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "chore: version $Version"
    if ($LASTEXITCODE -ne 0) { throw "No se pudo hacer el commit de la version" }
}

git tag $tag
if ($LASTEXITCODE -ne 0) { throw "No se pudo crear la etiqueta $tag" }
git push
if ($LASTEXITCODE -ne 0) { throw "No se pudo subir la rama" }
git push origin $tag
if ($LASTEXITCODE -ne 0) { throw "No se pudo subir la etiqueta $tag" }

Write-Host "Etiqueta $tag subida: GitHub compila el instalador y publica el release solo" -ForegroundColor Green
