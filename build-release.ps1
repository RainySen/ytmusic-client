# ==========================================
# Build Script: YTMusicClient Release
# ==========================================

Write-Host "Limpiando builds anteriores..." -ForegroundColor Yellow
Remove-Item -Recurse -Force build, dist, release -ErrorAction SilentlyContinue

Write-Host "Compilando ejecutable Release..." -ForegroundColor Cyan

& ".\.venv\Scripts\pyinstaller.exe" `
    --onefile `
    --noconsole `
    --clean `
    --distpath release `
    --name "YTMusicClient" `
    --icon "icon.ico" `
    --version-file "version_info.txt" `
    "app.py"

Write-Host "Compilación completada." -ForegroundColor Green
Write-Host "Ejecutable disponible en: release\YTMusicClient.exe"
