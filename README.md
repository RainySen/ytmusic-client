# YTMusic Minimal Client

Cliente de escritorio para YouTube Music hecho con Python, PySide6 y VLC. Está pensado para PCs modestas: no usa Electron ni mantiene un navegador abierto, la red corre en hilos de fondo y la interfaz se mantiene fluida mientras suena la música.

<img width="1552" height="977" alt="image" src="https://github.com/user-attachments/assets/fcc6cbe7-dce3-4903-b435-e72a9dc03bf8" />
<img width="1552" height="977" alt="image" src="https://github.com/user-attachments/assets/0a8effac-850f-4d8c-9ee9-9472125c0ad6" />



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
- **Reproductor:** cola con arrastrar y soltar, radio automática, aleatorio, repetición, Me gusta, silencio y pestañas *A continuación*, *Letra* y *Similares*. La barra de progreso va delgada arriba de todo, de borde a borde, dejando el resto para los controles, como en YouTube Music. Un clic en la barra abre el reproductor y el clic derecho muestra un menú con los controles; el nombre del artista y del álbum llevan a su página. Un clic en la barra de progreso o de volumen salta directo a ese punto. El corazón de Me gusta aparece de una vez cuando la canción ya trae ese dato (radio, discografía de un artista); si no, se consulta aparte. En la discografía de un artista, las canciones que ya tienen Me gusta muestran un corazón junto a la duración.
- **Reproducción automática:** un switch arriba de la cola (además del ajuste en Configuración) la llena sola con recomendaciones cuando eliges una canción, igual que el de YouTube Music.
- **Tu canal:** haz clic en tu foto de cuenta y elige "Tu canal" para ver tu nombre, tu foto, lo que escuchaste hace poco y tus artistas favoritos de tu biblioteca, con "Aleatorio" y "Mix" para reproducirlo. La API de YouTube Music no expone un conteo real de reproducciones para esto, así que la lista de canciones es tu historial reciente, no un ranking.
- **Ir al artista:** en el menú de cualquier canción (clic derecho o botón ⋮, en listas, Inicio y búsqueda) y en el clic derecho de la barra del reproductor. Abre la página del artista principal de la canción.
- **Fijar en volver a escuchar:** desde esos mismos menús puedes fijar una canción para que aparezca primero en el estante "Volver a escucharlo" del Inicio (si YouTube Music no manda ese estante, se crea). Se quita con "Quitar de volver a escuchar". **El fijado es solo local:** se guarda en `data/listen_again_pins.json` (hasta 30 canciones), se borra al cerrar sesión (no si la sesión solo caduca) y no se sincroniza con tu cuenta de YouTube Music ni con otros dispositivos, porque la librería que usamos para hablar con YouTube Music (ytmusicapi) no expone la función de fijar de la app oficial.
- **Tus playlists:** el botón de las tres líneas, junto al logo, despliega un panel con tus playlists ordenadas por modificación reciente; las fijadas van primero. Cada una tiene sus tres puntos con las mismas opciones que el clic derecho: fijar, reproducir a continuación, agregar a la cola o eliminar (las locales).
- **Menús contextuales:** el botón de tres puntos y el clic derecho permiten reproducir a continuación, agregar a la cola y guardar en una playlist, ya sea local o de tu cuenta.
- **Letras sincronizadas** por línea o por palabra (ver [Letras](#letras)).
- **Biblioteca:** tus playlists, canciones guardadas, canciones con Me gusta y artistas más escuchados. Las canciones se cargan por tandas: al llegar al final de la lista se piden más solas, en vez de traerlas todas de golpe.
- **Búsqueda:** guarda tus últimas búsquedas y las sugiere al volver a escribir; el mejor resultado se destaca arriba.
- **Sesión:** inicio con Google o pegando cURL o cookies, con aviso cuando la sesión caduca.
- **Rendimiento:** arranque rápido desde la última sesión, miniaturas y secciones que se cargan al verlas y precarga de las próximas canciones.
- **Bandeja del sistema:** al minimizar sigue sonando. Un clic en el icono de la bandeja abre la ventana y recarga el inicio, igual que el botón Inicio.

Solo se ha probado en Windows 10 y 11.

## Configuración

El engranaje de la barra superior abre la configuración; los cambios se aplican al instante y se guardan en `data/settings.json`.

- **Seguir en segundo plano al cerrar:** al cerrar la ventana la música sigue y la app queda en la bandeja. Si se apaga, cerrar la ventana cierra la app.
- **Mini reproductor:** ventana pequeña siempre visible con los controles cuando minimizas o cierras a la bandeja. Se puede mover y recuerda su posición.
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

El orden, qué proveedores usar y la clave de Better Lyrics se cambian en la configuración y se aplican a la siguiente letra que se pida. También puedes definir la clave con la variable de entorno `BETTER_LYRICS_API_KEY`, que tiene prioridad. Si tenías un `data/lyrics_settings.json` de versiones anteriores, se importa solo la primera vez y se renombra a `lyrics_settings.json.migrated`.

**Romanización (romaji y similares):** cuando el idioma original no usa alfabeto latino, se pide una transcripción a [Unison](https://unison.boidu.dev) (el mismo servicio que usa Better Lyrics para esto) y se muestra en una segunda línea, más pequeña, debajo de cada verso. Se puede apagar en la configuración. Unison detecta solo si hace falta romanizar; no hay una manera de pedir solo un idioma en particular.

Si un proveedor falla (por ejemplo LRCLIB con un error 503), se reintenta una vez y, si sigue fallando, se omite durante 1 minuto; mientras tanto la letra que se muestre no se guarda, así que se vuelve a buscar en cuanto el proveedor responda. Con letra por palabra se ilumina cada palabra al cantarse.

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
