# YTMusic Minimal Client

Cliente de escritorio para YouTube Music hecho con Python, PySide6 y VLC. Está pensado para PCs modestas: no usa Electron ni mantiene un navegador abierto, la red corre en hilos de fondo y la interfaz se mantiene fluida mientras suena la música.

<img width="1552" height="977" alt="image" src="https://github.com/user-attachments/assets/fcc6cbe7-dce3-4903-b435-e72a9dc03bf8" />
<img width="1552" height="977" alt="image" src="https://github.com/user-attachments/assets/0a8effac-850f-4d8c-9ee9-9472125c0ad6" />



Inspirado en [ytmdesktop](https://github.com/ytmdesktop/ytmdesktop). No está afiliado a YouTube ni a Google.

## Contenido

- [Características](#características)
- [Instalación](#instalación)
- [Inicio de sesión](#inicio-de-sesión)
- [Letras](#letras)
- [Ejecutar desde el código](#ejecutar-desde-el-código)
- [Compilar el instalador](#compilar-el-instalador)
- [Arquitectura](#arquitectura)
- [Pruebas](#pruebas)
- [Solución de problemas](#solución-de-problemas)
- [Contribuir](#contribuir)
- [Licencia](#licencia)

## Características

- **Explorar y buscar:** inicio con estantes y estados de ánimo, Explorar (lanzamientos, tendencias, géneros) y búsqueda de canciones, artistas, álbumes y playlists.
- **Páginas propias:** perfil de artista (Aleatorio, Mix, canciones populares, discografía), álbumes, sencillos y EP, y playlists, con botón de volver.
- **Reproductor:** cola con arrastrar y soltar, radio automática, aleatorio, repetición y pestañas *A continuación*, *Letra* y *Similares*.
- **Menús contextuales:** el botón de tres puntos y el clic derecho permiten reproducir a continuación, agregar a la cola y guardar en una playlist, ya sea local o de tu cuenta.
- **Letras sincronizadas** por línea o por palabra (ver [Letras](#letras)).
- **Sesión:** inicio con Google o pegando cURL o cookies, con aviso cuando la sesión caduca.
- **Rendimiento:** arranque rápido desde la última sesión, miniaturas y secciones que se cargan al verlas y precarga de las próximas canciones.
- **Bandeja del sistema:** al minimizar sigue sonando.

Solo se ha probado en Windows 10 y 11.

## Instalación

1. Descarga `YTMusicClient-Setup-<versión>.exe` desde la sección [Releases](../../releases).
2. Ejecútalo. Se instala solo para tu usuario y no pide permisos de administrador.
3. Si el PC no tiene VLC de 64 bits, el instalador lo descarga (versión 3.0.21, con verificación SHA-256) y lo instala. En ese paso Windows pide permisos de administrador.

Para actualizar, ejecuta el instalador de la versión nueva sobre la anterior: la app se reemplaza en su sitio y se conservan tus datos.

Como el instalador todavía no está firmado, Windows SmartScreen puede mostrar "Windows protegió su PC". Pulsa **Más información** y luego **Ejecutar de todas formas**.

### Tus datos

La sesión, las playlists locales, la cola, la caché y el registro se guardan en la carpeta `data`, dentro de la carpeta de instalación (o junto a `app.py` si ejecutas desde el código). Al desinstalar, esa carpeta se elimina. Nada se envía a servidores propios: la app solo habla con YouTube, con los proveedores de letras y con las páginas de miniaturas.

## Inicio de sesión

Puedes usar la app sin sesión, pero no tendrás tu biblioteca ni podrás guardar en tus playlists.

- **Iniciar sesión con Google:** abre una ventana con Chromium embebido (QtWebEngine, incluido en PySide6) solo mientras inicias sesión. Al llegar a YouTube Music se guardan las cookies y la ventana se cierra. No necesitas tener un navegador abierto después.
- **Pegar cURL o cookies:** alternativa por si lo anterior falla. Acepta un cURL de cualquier navegador (F12, pestaña Red, una petición `browse`, clic derecho, Copiar como cURL; bash, cmd o PowerShell), cabeceras copiadas como texto, una cadena de cookies, un `cookies.txt` o un JSON de Cookie-Editor. La cookie imprescindible es `__Secure-3PAPISID`.

La sesión se guarda en `data/oauth.json`, en texto plano, así que trátalo como una contraseña y no lo compartas. La app la verifica al arrancar y cada 30 minutos; si caduca, te pide iniciar sesión otra vez.

## Letras

Se consultan varios proveedores en orden y gana la primera respuesta sincronizada. Si ninguno la tiene, se muestra texto plano.

1. **Better Lyrics** ([API](https://github.com/better-lyrics/api)): sincronización por sílaba o palabra. Sin clave solo responde lo que ya tiene en caché; el resto requiere una clave que sus autores entregan por proyecto.
2. **LRCLIB** ([lrclib.net](https://lrclib.net)): gratuito, sincronizado por línea.
3. **YouTube Music:** la letra de YouTube, normalmente sin tiempos.

Para cambiar el orden o poner tu clave, crea `data/lyrics_settings.json` o define la variable de entorno `BETTER_LYRICS_API_KEY`:

```json
{ "providers": ["betterlyrics", "lrclib", "youtube"], "better_lyrics_api_key": "" }
```

Un proveedor que falla se omite durante 5 minutos. Con letra por palabra se ilumina cada palabra al cantarse.

## Ejecutar desde el código

Requisitos: Python 3.10 o superior (probado en 3.14) y [VLC de 64 bits](https://www.videolan.org/vlc/) instalado. Si aparece un error de `libvlc.dll` o `ctypes`, casi seguro se mezclan 32 y 64 bits; usa 64 bits para Python y para VLC.

```bash
git clone https://github.com/RainySen/ytmusic-client.git
cd ytmusic-client
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Compilar el instalador

```bash
pip install -r requirements-dev.txt
.\build-release.ps1
```

El script hace tres cosas:

1. Compila con PyInstaller en modo `--onedir` (`release\YTMusicClient\`).
2. Recorta de esa carpeta los componentes de Qt que no se usan (`installer/prune_bundle.py`).
3. Si tienes [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install JRSoftware.InnoSetup`), genera `release\YTMusicClient-Setup-<versión>.exe`, de unos 105 MB. Casi todo el peso es QtWebEngine.

La versión sale de `FileVersion` en `version_info.txt`. Para publicar una versión nueva, cambia ahí `filevers`, `prodvers`, `FileVersion` y `ProductVersion`. El workflow `.github/workflows/release.yml` hace el mismo proceso en GitHub Actions al empujar una etiqueta `v*` y adjunta el instalador al Release.

## Arquitectura

Las dependencias apuntan hacia adentro y solo `core/bootstrap.py` conoce las clases concretas.

```
app.py            Punto de entrada: QApplication, login y ventana principal
core/             config.py (rutas y parámetros), logging_setup.py, bootstrap.py (raíz de composición)
domain/           Lógica sin red ni disco: PlayQueue, StreamCache, modelos, parseo de letras y búsquedas
infra/            TaskRunner (hilos), ytmusicapi, yt-dlp, VLC, letras, sesión, miniaturas, JSON
services/         Casos de uso: reproducción, catálogo, biblioteca, letras, autenticación, streams
presenters/       Conectan cada vista con sus servicios
ui/               Widgets y señales; no conocen los servicios
tests/            Pruebas unitarias, de UI y de presenters
installer/        Script de Inno Setup y recorte del bundle
data/             Datos del usuario (se crea sola, ignorada por git)
```

- **Concurrencia:** `TaskRunner` usa un `QThreadPool` y entrega los resultados en el hilo principal por señal en cola. Con `key`, solo llega el último resultado de cada clave. No combines `threading.Thread` con `QTimer.singleShot(0, fn)`: el callback nunca se ejecuta.
- **Reproducción:** `StreamService` tiene dos pools para que reproducir nunca espere tras una precarga, deduplica peticiones y cachea las URL según su `expire=`.
- **Presenters:** PySide solo guarda referencias débiles a los métodos de objetos que no son `QObject`; por eso `bootstrap.UserInterface` retiene los presenters.

## Pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Las pruebas corren sin red y sin pantalla (Qt en modo `offscreen`). `tests/test_live_flows.py` usa la red real y VLC, y solo se ejecuta si activas la variable:

```bash
set YTMUSIC_LIVE_TESTS=1 && python -m pytest tests/test_live_flows.py -q -s
```

## Solución de problemas

- **No suena nada o falla una canción:** la reproducción depende de yt-dlp y YouTube cambia su API con frecuencia. Actualiza con `pip install --upgrade yt-dlp`; con el instalador hay que esperar a una versión nueva.
- **Error de `libvlc.dll`:** instala VLC de 64 bits. No sirve la versión de 32 bits.
- **"Tu sesión caducó":** vuelve a iniciar sesión. Si ocurre muy seguido, prueba el método de pegar cURL desde tu navegador habitual.
- **Google dice que el navegador no es seguro:** usa la opción de pegar cURL o cookies.
- **El login con Google se queda en una pantalla de Google** (revisión de seguridad, consentimiento de cookies, etc.): la ventana continúa sola a YouTube Music cuando detecta tu sesión. Si no avanza, pulsa **Ya inicié sesión, continuar** en la parte de abajo. Si aun así falla, el recorrido de páginas queda en `data/ytmusic-client.log` (líneas `login page:`), útil para reportar el problema.
- **Errores en general:** se registran en `data/ytmusic-client.log`.

## Contribuir

Las contribuciones son bienvenidas. Abre un issue antes de un cambio grande.

- Ejecuta `python -m pytest` antes de enviar cambios.
- El código va sin docstrings; solo se usan comentarios cortos de palabras clave, en minúsculas y sin tildes, sobre las clases y métodos importantes.
- Respeta las capas de la [arquitectura](#arquitectura): `ui` no importa servicios y `domain` no importa `infra`, servicios ni `ui`.

## Licencia

[MIT](LICENSE). Usa PySide6 (LGPL), ytmusicapi (MIT), yt-dlp (Unlicense) y VLC (LGPL/GPL, instalado aparte).
