# PyMusic Client

<img width="1552" height="977" alt="image" src="https://github.com/user-attachments/assets/fcc6cbe7-dce3-4903-b435-e72a9dc03bf8" />
<img width="1552" height="977" alt="image" src="https://github.com/user-attachments/assets/0a8effac-850f-4d8c-9ee9-9472125c0ad6" />

<details open>
<summary><b>🇪🇸 Español</b> — clic para mostrar u ocultar</summary>

Cliente de escritorio para YouTube Music hecho con Python, PySide6 y VLC. Está pensado para PCs modestas: no usa Electron ni mantiene un navegador abierto, la red corre en hilos de fondo y la interfaz se mantiene fluida mientras suena la música.

Inspirado en [ytmdesktop](https://github.com/ytmdesktop/ytmdesktop). No está afiliado a YouTube ni a Google.

## Contenido

- [Características](#características)
- [Configuración](#configuración)
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
- **Reproductor:** cola con arrastrar y soltar, radio automática, aleatorio, repetición, Me gusta, silencio y pestañas *A continuación*, *Letra* y *Similares*. La barra de progreso va delgada arriba de todo, de borde a borde, dejando el resto para los controles, como en YouTube Music. Un clic en la barra abre el reproductor y el clic derecho muestra un menú con los controles; el nombre del artista y del álbum llevan a su página. Un clic en la barra de progreso o de volumen salta directo a ese punto. El corazón de Me gusta aparece de una vez cuando la canción ya trae ese dato (radio, discografía de un artista); si no, se consulta aparte. En la discografía de un artista, las canciones que ya tienen Me gusta muestran un corazón junto a la duración. Los corazones se guardan en tu cuenta: la canción entra en tu playlist "Me gusta" de YouTube Music y se ve en todos tus dispositivos.
- **Reproducción automática:** un switch arriba de la cola (además del ajuste en Configuración) la llena sola con recomendaciones cuando eliges una canción, igual que el de YouTube Music.
- **Tu canal:** haz clic en tu foto de cuenta y elige "Tu canal" para ver tu nombre, tu foto, lo que escuchaste hace poco y tus artistas favoritos de tu biblioteca, con "Aleatorio" y "Mix" para reproducirlo. La API de YouTube Music no expone un conteo real de reproducciones para esto, así que la lista de canciones es tu historial reciente, no un ranking.
- **Ir al artista:** en el menú de cualquier canción (clic derecho o botón ⋮, en listas, Inicio y búsqueda) y en el clic derecho de la barra del reproductor. Abre la página del artista principal de la canción.
- **Fijar en volver a escuchar:** desde esos mismos menús puedes fijar una canción para que aparezca primero en el estante "Volver a escucharlo" del Inicio (si YouTube Music no manda ese estante, se crea). Se quita con "Quitar de volver a escuchar". **El fijado es solo local:** se guarda en `data/listen_again_pins.json` (hasta 30 canciones), se borra al cerrar sesión (no si la sesión solo caduca) y no se sincroniza con tu cuenta de YouTube Music ni con otros dispositivos, porque la librería que usamos para hablar con YouTube Music (ytmusicapi) no expone la función de fijar de la app oficial.
- **Tus playlists:** el botón de las tres líneas, junto al logo, despliega un panel con tus playlists ordenadas por modificación reciente; las fijadas van primero. Cada una tiene sus tres puntos con las mismas opciones que el clic derecho: fijar, reproducir a continuación, agregar a la cola o eliminar (las locales).
- **Menús contextuales:** el botón de tres puntos y el clic derecho permiten reproducir a continuación, agregar a la cola y guardar en una playlist, ya sea local o de tu cuenta.
- **Letras sincronizadas** por línea o por palabra (ver [Letras](#letras)).
- **Biblioteca:** tus playlists, canciones guardadas, canciones con Me gusta y artistas más escuchados. Las canciones se cargan por tandas: al llegar al final de la lista se piden más solas, en vez de traerlas todas de golpe.
- **Búsqueda:** guarda tus últimas búsquedas y las sugiere al volver a escribir; el mejor resultado se destaca arriba. Las pestañas **YT MUSIC** y **BIBLIOTECA** cambian dónde se busca: Biblioteca busca solo en lo tuyo (Me gusta, canciones y álbumes guardados, artistas que sigues y tus playlists, incluidas las locales), útil cuando YouTube Music no muestra la canción correcta.
- **Canciones solo para Premium:** si YouTube bloquea una canción por ser exclusiva de Premium, la app la reintenta sola con tu sesión y suena si tu cuenta tiene Premium. La primera vez tarda unos segundos más; después queda recordada en `data/cache/account_only_tracks.json` para ir directo.
- **Sesión:** inicio con Google o pegando cURL o cookies, con aviso cuando la sesión caduca.
- **Rendimiento:** arranque rápido desde la última sesión, miniaturas y secciones que se cargan al verlas y precarga de las próximas canciones.
- **Bandeja del sistema:** al minimizar sigue sonando. Un clic en el icono de la bandeja abre la ventana y recarga el inicio, igual que el botón Inicio.

Solo se ha probado en Windows 10 y 11.

## Configuración

El engranaje de la barra superior abre la configuración; los cambios se aplican al instante y se guardan en `data/settings.json`.

- **Seguir en segundo plano al cerrar:** al cerrar la ventana la música sigue y la app queda en la bandeja. Si se apaga, cerrar la ventana cierra la app.
- **Mini reproductor:** ventana pequeña siempre visible con los controles cuando minimizas o cierras a la bandeja. Se puede mover y recuerda su posición. Incluye un botón para retroceder la canción, configurable a 5, 10, 15 o 20 segundos.
- **Cola automática:** al elegir una canción, la cola se llena sola con recomendaciones y se sigue extendiendo al llegar al final. Apagada, solo suena lo que elijas.
- **Cola de radio:** cuántas canciones se cargan al elegir una canción (de 5 hasta 1000 o ilimitada). Las primeras 50 llegan junto con la canción (~2 s) y el resto se carga en segundo plano por etapas; con "ilimitada" la cola se sigue extendiendo sola. El tamaño casi no afecta a la memoria: cada canción ocupa unos 230 bytes.
- **Liberar memoria en segundo plano:** con la ventana cerrada, minimizada o en modo mini reproductor se descartan miniaturas y listas tras 10 s, 20 s, 1 min o 3 min, se recargan al volver y, mientras siga oculta, la RAM se vuelve a recortar cada minuto. Con la ventana abierta también se limpia cada ese tiempo lo que no estás viendo, pero solo si no estás usando la app (está detrás de otra ventana, por ejemplo un juego, o no tocaste mouse ni teclado en ese tiempo), para no trabar el scroll. El botón **Liberar RAM ahora** hace lo mismo al instante y muestra cuántos MB devolvió al sistema. Windows vuelve a cargar en RAM lo que la app usa, así que la cifra sube un poco después de limpiar; eso es normal.
- **Iniciar con Windows:** la app arranca al encender el equipo, minimizada en la bandeja y sin abrir la ventana. Se registra en la clave `Run` del usuario y se quita al apagar el ajuste.
- **Recordar el volumen** y **restaurar la cola al abrir.**
- **Teclas multimedia:** pausa, siguiente y anterior desde el teclado, incluso con la app en segundo plano. Si otra aplicación ya tiene registrada alguna de esas teclas, esa tecla queda para ella.
- **Aviso al cambiar de canción:** notificación de la bandeja cuando la ventana está oculta o minimizada.
- **Idioma del contenido:** idioma de los textos que entrega YouTube Music (secciones del inicio, Explorar, búsquedas). Al cambiarlo se recarga el inicio. Los menús de la app siguen en español.
- **Calidad de las miniaturas:** "Automática" ya pide las imágenes al tamaño real de tu pantalla (antes se pedían más chicas de lo debido y se veían borrosas en monitores grandes o 4K). "Alta" pide un poco más de nitidez todavía; "Baja" las reduce para ahorrar memoria y datos. Al primer arranque se elige sola según tu pantalla.
- **Miniaturas en memoria:** cuántas se guardan listas para no volver a descargarlas al hacer scroll (100 a 800). Menos usa menos RAM pero recarga más seguido.
- **Letras:** orden y activación de cada proveedor, la clave de Better Lyrics y la romanización (ver [Letras](#letras)).
- **Caché:** muestra cuánto ocupan las miniaturas y los datos temporales, y permite vaciarlos. No toca la sesión, las playlists ni la cola.
- **Cuenta:** iniciar o cerrar sesión desde la misma ventana.

## Instalación

1. Descarga `PyMusicClient-Setup-<versión>.exe` desde la sección [Releases](../../releases).
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

La sesión se guarda en `data/oauth.json`, **cifrada con DPAPI de Windows**: queda atada a tu cuenta de usuario, así que otro usuario del mismo PC no puede leerla ni sirve copiar el archivo a otro equipo. Si vienes de una versión anterior con el archivo en texto plano, se cifra solo la próxima vez que abras la app. Aun así, trátalo como una contraseña: cualquiera que entre con tu usuario de Windows puede usar la sesión. La app la verifica al arrancar y cada 30 minutos; si caduca, te pide iniciar sesión otra vez.

## Letras

Se consultan varios proveedores en orden y gana la primera respuesta sincronizada. Si ninguno la tiene, se muestra texto plano.

1. **Better Lyrics** ([API](https://github.com/better-lyrics/api)): sincronización por sílaba o palabra. Sin clave solo responde lo que ya tiene en caché; el resto requiere una clave que sus autores entregan por proyecto.
2. **LRCLIB** ([lrclib.net](https://lrclib.net)): gratuito, sincronizado por línea.
3. **YouTube Music:** la letra de YouTube. Cuando está disponible llega sincronizada por línea (la provee Musixmatch) y, si no, en texto plano.

El orden, qué proveedores usar y la clave de Better Lyrics se cambian en la configuración y se aplican a la siguiente letra que se pida. También puedes definir la clave con la variable de entorno `BETTER_LYRICS_API_KEY`, que tiene prioridad. Si tenías un `data/lyrics_settings.json` de versiones anteriores, se importa solo la primera vez y se renombra a `lyrics_settings.json.migrated`.

**Romanización (romaji y similares):** cuando el idioma original no usa alfabeto latino, se pide una transcripción a [Unison](https://unison.boidu.dev) (el mismo servicio que usa Better Lyrics para esto) y se muestra en una segunda línea, más pequeña, debajo de cada verso. Se puede apagar en la configuración. Unison detecta solo si hace falta romanizar; no hay una manera de pedir solo un idioma en particular.

Si un proveedor falla (por ejemplo LRCLIB con un error 503), se reintenta una vez y, si sigue fallando, se omite durante 1 minuto; mientras tanto la letra que se muestre no se guarda, así que se vuelve a buscar en cuanto el proveedor responda. Con letra por palabra se ilumina cada palabra al cantarse.

## Ejecutar desde el código

Requisitos: Python 3.10 o superior (probado en 3.14) y [VLC de 64 bits](https://www.videolan.org/vlc/) instalado. Si aparece un error de `libvlc.dll` o `ctypes`, casi seguro se mezclan 32 y 64 bits; usa 64 bits para Python y para VLC.

```bash
git clone https://github.com/RainySen/ytmusic-client.git
cd ytmusic-client
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Si usas un IDE, asegúrate de que el intérprete sea el de `.venv\`: con otro entorno faltarán dependencias como `yt-dlp-ejs`, necesaria para las canciones exclusivas de Premium.

## Compilar el instalador

```bash
pip install -r requirements-dev.txt
.\build-release.ps1
```

El script hace tres cosas:

1. Compila con PyInstaller en modo `--onedir` (`release\YTMusicClient\`).
2. Recorta de esa carpeta los componentes de Qt que no se usan (`installer/prune_bundle.py`).
3. Si tienes [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install JRSoftware.InnoSetup`), genera `release\PyMusicClient-Setup-<versión>.exe`, de unos 105 MB. Casi todo el peso es QtWebEngine.

La versión sale de `version_info.txt`. Para cambiarla, ejecuta `.\bump-version.ps1 1.3.0`, que actualiza sus cuatro campos a la vez (`filevers`, `prodvers`, `FileVersion` y `ProductVersion`); después compila.

Para publicar una versión nueva basta un comando: `.\bump-version.ps1 1.3.0 -Publish`. Cambia la versión, hace commit, crea la etiqueta `v1.3.0` y la sube. Con eso, el workflow `.github/workflows/release.yml` compila el instalador en GitHub Actions y crea el Release solo. El workflow toma la versión de la etiqueta (acepta `v1.3.0` y `v.1.3.0`), así que el `.exe` y el instalador siempre dicen la misma versión que el Release. Si el Release ya existía, reemplaza el instalador en vez de fallar.

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
- **Una canción exclusiva de Premium no suena:** la app la reintenta con tu sesión, pero eso necesita un motor de JavaScript. Si el registro dice "The page needs to be reloaded", revisa que estés usando el entorno correcto y que `pip install -r requirements.txt` haya instalado `yt-dlp-ejs`.
- **Error de `libvlc.dll`:** instala VLC de 64 bits. No sirve la versión de 32 bits.
- **"Tu sesión caducó":** vuelve a iniciar sesión. Si ocurre muy seguido, prueba el método de pegar cURL desde tu navegador habitual.
- **Google dice que el navegador no es seguro:** usa la opción de pegar cURL o cookies.
- **El login con Google se queda en una pantalla de Google** (revisión de seguridad, consentimiento de cookies, etc.): la ventana continúa sola a YouTube Music cuando detecta tu sesión. Si no avanza, pulsa **Ya inicié sesión, continuar** en la parte de abajo. Si aun así falla, el recorrido de páginas queda en `data/ytmusic-client.log` (líneas `login page:`), útil para reportar el problema.
- **Errores en general:** se registran en `data/ytmusic-client.log`.

## Contribuir

Las contribuciones son bienvenidas. Abre un issue antes de un cambio grande.

- Ejecuta `python -m pytest` antes de enviar cambios.
- Respeta las capas de la [arquitectura](#arquitectura): `ui` no importa servicios y `domain` no importa `infra`, servicios ni `ui`.

## Donar y apoyar el proyecto

Esto no es una obligación, si quieres aportar tu granito al proyecto te seremos eternamente agradecidos, "cada moneda cuenta"
decía el homeless que pide monedas al lado de una areperia:

- **BuyMeaCoffee**:

<a href="https://www.buymeacoffee.com/seiny" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>

## Licencia

[MIT](LICENSE). Usa PySide6 (LGPL), ytmusicapi (MIT), yt-dlp (Unlicense) y VLC (LGPL/GPL, instalado aparte).

</details>

<details>
<summary><b>🇬🇧 English</b> — click to show or hide</summary>

A desktop client for YouTube Music built with Python, PySide6 and VLC. It targets modest PCs: no Electron, no browser kept open, networking runs on background threads and the interface stays smooth while the music plays.

Inspired by [ytmdesktop](https://github.com/ytmdesktop/ytmdesktop). Not affiliated with YouTube or Google.

## Contents

- [Features](#features)
- [Settings](#settings)
- [Installation](#installation)
- [Signing in](#signing-in)
- [Lyrics](#lyrics)
- [Running from source](#running-from-source)
- [Building the installer](#building-the-installer)
- [Architecture](#architecture)
- [Tests](#tests)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Browse and search:** home with shelves and moods, Explore (new releases, trending, genres) and search for songs, artists, albums and playlists.
- **Dedicated pages:** artist profile (Shuffle, Mix, top songs, discography), albums, singles and EPs, and playlists, all with a back button.
- **Player:** drag-and-drop queue, automatic radio, shuffle, repeat, Like, mute and the *Up next*, *Lyrics* and *Related* tabs. The progress bar sits thin at the very top, edge to edge, leaving the rest for the controls, like YouTube Music does. Clicking the bar opens the player and right-clicking shows a menu with the controls; the artist and album names link to their pages. Clicking the progress or volume bar jumps straight to that point. The Like heart shows up immediately when the song already carries that information (radio, an artist's discography); otherwise it is fetched separately. In an artist's discography, songs you already liked show a heart next to the duration. Hearts are saved to your account: the song lands in your YouTube Music "Liked" playlist and shows up on all your devices.
- **Autoplay:** a switch above the queue (alongside the setting in Settings) fills it automatically with recommendations when you pick a song, just like the one in YouTube Music.
- **Your channel:** click your account picture and choose "Your channel" to see your name, your picture, what you listened to recently and your favourite artists from your library, with "Shuffle" and "Mix" to play it. The YouTube Music API does not expose a real play count for this, so the song list is your recent history, not a ranking.
- **Go to artist:** in any song's menu (right click or the ⋮ button, in lists, Home and search) and in the player bar's right-click menu. Opens the page of the song's main artist.
- **Pin to listen again:** from those same menus you can pin a song so it appears first in the "Listen again" shelf on Home (if YouTube Music does not send that shelf, it is created). Remove it with "Unpin from listen again". **Pinning is local only:** it is stored in `data/listen_again_pins.json` (up to 30 songs), cleared when you sign out (not when the session merely expires) and never synced with your YouTube Music account or other devices, because the library we use to talk to YouTube Music (ytmusicapi) does not expose the official app's pinning feature.
- **Your playlists:** the hamburger button next to the logo opens a panel with your playlists sorted by most recently modified; pinned ones come first. Each has its own three-dot menu with the same options as right click: pin, play next, add to queue or delete (local ones).
- **Context menus:** the three-dot button and right click let you play next, add to queue and save to a playlist, either local or from your account.
- **Synced lyrics** by line or by word (see [Lyrics](#lyrics)).
- **Library:** your playlists, saved songs, liked songs and most played artists. Songs load in batches: when you reach the end of the list more are requested automatically, instead of fetching everything at once.
- **Search:** remembers your recent searches and suggests them as you type again; the top result is highlighted above. The **YT MUSIC** and **LIBRARY** tabs switch where the search runs: Library searches only your own content (likes, saved songs and albums, artists you follow and your playlists, local ones included), handy when YouTube Music does not surface the right song.
- **Premium-only songs:** if YouTube blocks a song as Premium-exclusive, the app retries it on its own with your session and it plays if your account has Premium. The first time takes a few seconds longer; after that it is remembered in `data/cache/account_only_tracks.json` so it goes straight there.
- **Session:** sign in with Google or by pasting cURL or cookies, with a notice when the session expires.
- **Performance:** fast start from the last session, thumbnails and sections loaded as they come into view, and prefetching of upcoming songs.
- **System tray:** minimising keeps the music playing. Clicking the tray icon opens the window and reloads Home, same as the Home button.

Only tested on Windows 10 and 11.

## Settings

The gear in the top bar opens the settings; changes apply instantly and are saved to `data/settings.json`.

- **Keep running in the background on close:** closing the window keeps the music playing and leaves the app in the tray. Turn it off and closing the window quits the app.
- **Mini player:** a small always-on-top window with the controls when you minimise or close to the tray. It can be moved and remembers its position. It includes a rewind button, configurable to 5, 10, 15 or 20 seconds.
- **Autoplay queue:** when you pick a song, the queue fills itself with recommendations and keeps extending as you reach the end. Off, only what you choose plays.
- **Radio queue:** how many songs are loaded when you pick a song (from 5 up to 1000, or unlimited). The first 50 arrive with the song (~2 s) and the rest load in the background in stages; with "unlimited" the queue keeps extending on its own. The size barely affects memory: each song takes about 230 bytes.
- **Free memory in the background:** with the window closed, minimised or in mini player mode, thumbnails and lists are dropped after 10 s, 20 s, 1 min or 3 min, reloaded when you come back and, while it stays hidden, RAM is trimmed again every minute. With the window open it also clears what you are not looking at on that same interval, but only while you are not using the app (it is behind another window, a game for instance, or you have not touched mouse or keyboard in that time), so scrolling never stutters. The **Free RAM now** button does the same instantly and reports how many MB went back to the system. Windows pages back in whatever the app uses, so the figure creeps up again after cleaning; that is normal.
- **Start with Windows:** the app starts when you turn the computer on, minimised in the tray and without opening the window. It registers in the user's `Run` key and is removed when you turn the setting off.
- **Remember the volume** and **restore the queue on start.**
- **Media keys:** pause, next and previous from the keyboard, even with the app in the background. If another application already registered one of those keys, that key stays with it.
- **Notify on song change:** a tray notification when the window is hidden or minimised.
- **Content language:** the language of the text YouTube Music returns (home shelves, Explore, searches). Changing it reloads Home. The app's own menus stay in Spanish.
- **Thumbnail quality:** "Automatic" requests images at your screen's real size (they used to be requested smaller than needed and looked blurry on large or 4K monitors). "High" asks for a little more sharpness still; "Low" shrinks them to save memory and data. On first start it picks one based on your screen.
- **Thumbnails in memory:** how many are kept ready so they are not downloaded again while scrolling (100 to 800). Fewer uses less RAM but reloads more often.
- **Lyrics:** order and activation of each provider, the Better Lyrics key and romanisation (see [Lyrics](#lyrics)).
- **Cache:** shows how much space thumbnails and temporary data take, and lets you clear them. It does not touch your session, playlists or queue.
- **Account:** sign in or out from the same window.

## Installation

1. Download `PyMusicClient-Setup-<version>.exe` from the [Releases](../../releases) section.
2. Run it. It installs for your user only and does not ask for administrator rights.
3. If the PC does not have 64-bit VLC, the installer downloads it (version 3.0.21, with SHA-256 verification) and installs it. Windows asks for administrator rights at that step.

To update, run the new version's installer over the previous one: the app is replaced in place and your data is kept.

Since the installer is not signed yet, Windows SmartScreen may show "Windows protected your PC". Click **More info** and then **Run anyway**.

### Your data

The session, local playlists, queue, cache and log live in the `data` folder, inside the installation folder (or next to `app.py` if you run from source). Uninstalling removes that folder. Nothing is sent to servers of our own: the app only talks to YouTube, the lyrics providers and the thumbnail hosts.

## Signing in

You can use the app without signing in, but you will not have your library and will not be able to save to your playlists.

- **Sign in with Google:** opens a window with embedded Chromium (QtWebEngine, included in PySide6) only while you sign in. Once it reaches YouTube Music the cookies are saved and the window closes. You do not need a browser open afterwards.
- **Paste cURL or cookies:** an alternative in case the above fails. It accepts a cURL from any browser (F12, Network tab, a `browse` request, right click, Copy as cURL; bash, cmd or PowerShell), headers copied as text, a cookie string, a `cookies.txt` or a Cookie-Editor JSON. The essential cookie is `__Secure-3PAPISID`.

The session is stored in `data/oauth.json`, **encrypted with Windows DPAPI**: it is tied to your user account, so another user on the same PC cannot read it and copying the file to another machine is useless. If you come from an earlier version with the file in plain text, it is encrypted on its own the next time you open the app. Even so, treat it like a password: anyone who logs in as your Windows user can use the session. The app verifies it at startup and every 30 minutes; if it expires, you are asked to sign in again.

## Lyrics

Several providers are queried in order and the first synced answer wins. If none has it, plain text is shown.

1. **Better Lyrics** ([API](https://github.com/better-lyrics/api)): syllable- or word-level sync. Without a key it only returns what it already has cached; the rest requires a key its authors hand out per project.
2. **LRCLIB** ([lrclib.net](https://lrclib.net)): free, synced by line.
3. **YouTube Music:** YouTube's lyrics. When available they come synced by line (provided by Musixmatch) and otherwise as plain text.

The order, which providers to use and the Better Lyrics key are changed in the settings and apply to the next lyrics request. You can also set the key with the `BETTER_LYRICS_API_KEY` environment variable, which takes precedence. If you had a `data/lyrics_settings.json` from earlier versions, it is imported once and renamed to `lyrics_settings.json.migrated`.

**Romanisation (romaji and the like):** when the original language does not use the Latin alphabet, a transcription is requested from [Unison](https://unison.boidu.dev) (the same service Better Lyrics uses for this) and shown on a second, smaller line under each verse. It can be turned off in the settings. Unison detects on its own whether romanisation is needed; there is no way to request one specific language.

If a provider fails (LRCLIB with a 503, for instance), it is retried once and, if it still fails, skipped for 1 minute; meanwhile the lyrics shown are not cached, so they are fetched again as soon as the provider responds. With word-level lyrics each word lights up as it is sung.

## Running from source

Requirements: Python 3.10 or newer (tested on 3.14) and [64-bit VLC](https://www.videolan.org/vlc/) installed. If you get a `libvlc.dll` or `ctypes` error, you are almost certainly mixing 32- and 64-bit; use 64-bit for both Python and VLC.

```bash
git clone https://github.com/RainySen/ytmusic-client.git
cd ytmusic-client
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

If you use an IDE, make sure the interpreter is the one in `.venv\`: with a different environment you will be missing dependencies such as `yt-dlp-ejs`, which Premium-only songs need.

## Building the installer

```bash
pip install -r requirements-dev.txt
.\build-release.ps1
```

The script does three things:

1. Builds with PyInstaller in `--onedir` mode (`release\YTMusicClient\`).
2. Strips the unused Qt components from that folder (`installer/prune_bundle.py`).
3. If you have [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install JRSoftware.InnoSetup`), it produces `release\PyMusicClient-Setup-<version>.exe`, around 105 MB. Almost all of that weight is QtWebEngine.

The version comes from `version_info.txt`. To change it, run `.\bump-version.ps1 1.3.0`, which updates its four fields at once (`filevers`, `prodvers`, `FileVersion` and `ProductVersion`); then build.

Publishing a new version takes a single command: `.\bump-version.ps1 1.3.0 -Publish`. It changes the version, commits, creates the `v1.3.0` tag and pushes it. From there the `.github/workflows/release.yml` workflow builds the installer on GitHub Actions and creates the Release by itself. The workflow takes the version from the tag (it accepts both `v1.3.0` and `v.1.3.0`), so the `.exe` and the installer always report the same version as the Release. If the Release already existed, it replaces the installer instead of failing.

## Architecture

Dependencies point inwards and only `core/bootstrap.py` knows the concrete classes.

```
app.py            Entry point: QApplication, login and main window
core/             config.py (paths and parameters), logging_setup.py, bootstrap.py (composition root)
domain/           Logic with no network or disk: PlayQueue, StreamCache, models, lyrics and search parsing
infra/            TaskRunner (threads), ytmusicapi, yt-dlp, VLC, lyrics, session, thumbnails, JSON
services/         Use cases: playback, catalog, library, lyrics, authentication, streams
presenters/       Wire each view to its services
ui/               Widgets and signals; they know nothing about services
tests/            Unit, UI and presenter tests
installer/        Inno Setup script and bundle trimming
data/             User data (created on its own, ignored by git)
```

- **Concurrency:** `TaskRunner` uses a `QThreadPool` and delivers results on the main thread through a queued signal. With `key`, only the latest result for each key arrives. Do not mix `threading.Thread` with `QTimer.singleShot(0, fn)`: the callback never runs.
- **Playback:** `StreamService` has two pools so playing never waits behind a prefetch, deduplicates requests and caches URLs according to their `expire=`.
- **Presenters:** PySide only keeps weak references to methods of objects that are not `QObject`; that is why `bootstrap.UserInterface` holds on to the presenters.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The tests run without network and without a display (Qt in `offscreen` mode). `tests/test_live_flows.py` uses the real network and VLC, and only runs if you set the variable:

```bash
set YTMUSIC_LIVE_TESTS=1 && python -m pytest tests/test_live_flows.py -q -s
```

## Troubleshooting

- **No sound at all, or one song fails:** playback depends on yt-dlp and YouTube changes its API often. Update with `pip install --upgrade yt-dlp`; with the installer you have to wait for a new version.
- **A Premium-only song does not play:** the app retries it with your session, but that needs a JavaScript engine. If the log says "The page needs to be reloaded", check that you are using the right environment and that `pip install -r requirements.txt` installed `yt-dlp-ejs`.
- **`libvlc.dll` error:** install 64-bit VLC. The 32-bit version will not do.
- **"Your session expired":** sign in again. If it happens very often, try the paste-cURL method from your usual browser.
- **Google says the browser is not secure:** use the paste cURL or cookies option.
- **The Google login gets stuck on a Google screen** (security review, cookie consent, etc.): the window continues to YouTube Music on its own once it detects your session. If it does not move on, press **I already signed in, continue** at the bottom. If it still fails, the page trail is recorded in `data/ytmusic-client.log` (`login page:` lines), which helps when reporting the problem.
- **Errors in general:** they are logged to `data/ytmusic-client.log`.

## Contributing

Contributions are welcome. Open an issue before a large change.

- Run `python -m pytest` before submitting changes.
- Respect the layers in the [architecture](#architecture): `ui` does not import services and `domain` does not import `infra`, services or `ui`.

## Donate and support the project

This is not an obligation. If you want to chip in to the project we will be eternally grateful, "every coin counts"
as the homeless guy asking for change next to an arepa stand used to say:

- **BuyMeaCoffee**:

<a href="https://www.buymeacoffee.com/seiny" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>

## License

[MIT](LICENSE). Uses PySide6 (LGPL), ytmusicapi (MIT), yt-dlp (Unlicense) and VLC (LGPL/GPL, installed separately).

</details>
