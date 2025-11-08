# ==========================================
# Build Script: YTMusicClient Release
# ==========================================

Write-Host "Limpiando builds anteriores..." -ForegroundColor Yellow
Remove-Item -Recurse -Force build, dist, release, "*.spec" -ErrorAction SilentlyContinue

Write-Host "Compilando ejecutable Release..." -ForegroundColor Cyan

# === INICIO DE CAMBIOS ===
# Añadimos --collect-datas ytmusicapi para que también incluya sus archivos de traducción.
& ".\.venv\Scripts\pyinstaller.exe" --onefile --noconsole --clean --distpath release --name "YTMusicClient" --icon "icon.ico" --version-file "version_info.txt" --collect-datas yt_dlp --collect-datas qtawesome --collect-datas ytmusicapi --hidden-import "PySide6.QtSvg" "app.py"
# === FIN DE CAMBIOS ===

Write-Host "Compilación completada." -ForegroundColor Green
Write-Host "Ejecutable disponible en: release\YTMusicClient.exe"