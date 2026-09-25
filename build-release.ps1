$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$version = [regex]::Match((Get-Content version_info.txt -Raw), "'FileVersion',\s*'([^']+)'").Groups[1].Value
if (-not $version) { throw "No se encontro FileVersion en version_info.txt" }

$python = ".\env\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = ".\.venv\Scripts\python.exe" }
if (-not (Test-Path $python)) { $python = "python" }

$iscc = (Get-Command iscc -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
    $iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") |
        Where-Object { Test-Path $_ } | Select-Object -First 1
}

Write-Host "Limpiando builds anteriores..." -ForegroundColor Yellow
Remove-Item -Recurse -Force build, dist, release, "*.spec" -ErrorAction SilentlyContinue

Write-Host "Compilando YTMusicClient $version..." -ForegroundColor Cyan
& $python -m PyInstaller --onedir --noconsole --clean --noconfirm --distpath release --name "YTMusicClient" --icon "icon.ico" --version-file "version_info.txt" --collect-datas yt_dlp --collect-datas qtawesome --collect-datas ytmusicapi --hidden-import "PySide6.QtSvg" "app.py"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fallo" }

& $python installer\prune_bundle.py release\YTMusicClient
if ($LASTEXITCODE -ne 0) { throw "prune_bundle fallo" }

if ($iscc) {
    Write-Host "Generando instalador..." -ForegroundColor Cyan
    & $iscc "/DAppVersion=$version" "installer\YTMusicClient.iss"
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup fallo" }
    Write-Host "Instalador: release\YTMusicClient-Setup-$version.exe" -ForegroundColor Green
} else {
    Write-Host "Inno Setup no encontrado (winget install JRSoftware.InnoSetup); solo se genero la carpeta release\YTMusicClient" -ForegroundColor Yellow
}
