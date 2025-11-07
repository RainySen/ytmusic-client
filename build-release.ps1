# ==========================================
# Build Script: YTMusicClient Release
# ==========================================

Write-Host "Limpiando builds anteriores..." -ForegroundColor Yellow
Remove-Item -Recurse -Force build, dist, release, "*.spec" -ErrorAction SilentlyContinue

Write-Host "Compilando ejecutable Release..." -ForegroundColor Cyan

# === INICIO DE CAMBIOS ===
# Añadimos --collect-datas ytmusicapi para que también incluya sus archivos de traducción.
& ".\.venv\Scripts\python.exe" -m nuitka --standalone --output-dir=release --plugin-enable=pyside6 --windows-icon-from-ico="icon.ico" --windows-product-name="YTMusicClient" --windows-file-description="YTMusic Minimal Client" --windows-file-version="1.0.0.0" --output-filename="YTMusicClient.exe" --nofollow-import-to=yt_dlp --include-package-data=yt_dlp --include-package-data=ytmusicapi --include-package-data=qtawesome app.py

Write-Host "Compilación completada." -ForegroundColor Green
Write-Host "Ejecutable disponible en: release\YTMusicClient.exe"