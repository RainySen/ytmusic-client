# 🎵 YTMusic Minimal Client

Un cliente de escritorio minimalista para YouTube Music, construido con Python, PySide6 y VLC.

Te permite buscar en YouTube Music, gestionar una cola de reproducción y escuchar música sin necesidad de un navegador, con una interfaz limpia y de bajo consumo.

<img width="800" height="500" alt="image" src="https://github.com/user-attachments/assets/d02358a8-d57d-479e-8c6a-f98d6e4d5904" />
<img width="800" height="500" alt="image" src="https://github.com/user-attachments/assets/b6234f13-81ca-40b2-a340-5c4968b31b6c" />

> **Nota:** Este proyecto está fuertemente inspirado en el concepto y la funcionalidad de [ytmdesktop/ytmdesktop](https://github.com/ytmdesktop/ytmdesktop).

---

## ✨ Características

* **Búsqueda Rápida:** Busca canciones y artistas directamente en YouTube Music.
* **Gestión de Cola:** Añade canciones, elimina, limpia la cola y salta entre canciones.
* **Inicio de Sesión:** Inicia sesión para acceder a tus playlists guardadas en la biblioteca.
* **Importación de Playlists:** Pega una URL de cualquier playlist de YouTube o YTMusic para cargarla en la cola.
* **Guardar Playlists:** Guarda una playlist importada directamente en tu biblioteca de YTMusic.
* **Controles Nativos:** Controles de reproducción, volumen y barra de progreso.
* **Integración con SO:** Se minimiza a la bandeja del sistema y sigue reproduciendo en segundo plano.
* **Arranque y reproducción rápidos:** todo el acceso a red va en hilos de fondo (la interfaz nunca se congela), el inicio se pinta al instante desde la última sesión, las miniaturas y secciones se cargan solo cuando se ven, y las próximas canciones de la cola se resuelven por adelantado.

---

## ⚠️ Requisitos

Esta aplicación tiene diferentes requisitos dependiendo de si la usas como desarrollador (desde el código fuente) o como usuario (usando el `.exe` compilado).

### Para Usuarios (Ejecutable `.exe`)

Solo necesitas **una cosa** instalada en tu sistema:

1.  **VLC Media Player (64 bits):** La aplicación depende del motor de VLC para la reproducción de audio.
    * **¡MUY IMPORTANTE!** Debes instalar la **versión de 64 bits** de VLC, ya que el ejecutable está compilado para 64 bits.
    * Puedes descargarlo desde el [sitio web oficial de VideoLAN](https://www.videolan.org/vlc/).
    * Si tienes instalada la versión de 32 bits (`C:\Program Files (x86)\...`), la aplicación **no funcionará** y mostrará un error de `libvlc.dll`.

### Para Desarrolladores (Correr desde código)

1.  **Python** (Recomendado 3.8 - 3.11).
2.  **VLC Media Player (64 bits):** (Mismo requisito que el de usuario).
3.  Todas las dependencias de Python listadas en `requirements.txt`.

---

## 🚀 Instalación y Uso (Desarrollo)

Si quieres ejecutar el proyecto desde el código fuente:

1.  **Clona el repositorio:**
    ```bash
    git clone [https://github.com/tu-usuario/tu-repositorio.git](https://github.com/tu-usuario/tu-repositorio.git)
    cd tu-repositorio
    ```

2.  **Crea y activa un entorno virtual:**
    ```bash
    python -m venv .venv
    # En Windows (CMD/PowerShell)
    .\.venv\Scripts\activate
    # En macOS/Linux
    source .venv/bin/activate
    ```

3.  **Instala las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Prepara la librería de VLC (¡Paso Crucial!)**
    Este proyecto está configurado para encontrar los archivos de VLC en una carpeta `vlc_lib` en la raíz del proyecto.
    * Crea una carpeta llamada `vlc_lib` en la raíz.
    * Ve a la carpeta de instalación de VLC 64 bits (ej. `C:\Program Files\VideoLAN\VLC`).
    * Copia los siguientes archivos y carpetas a tu `vlc_lib`:
        * `libvlc.dll`
        * `libvlccore.dll`
        * La carpeta `plugins` (completa)

5.  **Ejecuta la aplicación:**
    ```bash
    python app.py
    ```

---

## 📦 Compilación (Crear el `.exe`)

El proyecto está configurado para compilarse en un **único archivo `.exe`** usando `PyInstaller` y el archivo `.spec`.

1.  **Asegúrate de tener todo instalado** (incluyendo `pyinstaller`):
    ```bash
    pip install -r requirements.txt
    ```

2.  **Verifica la carpeta `vlc_lib`:** Asegúrate de que tu carpeta `vlc_lib` esté completa (ver paso 4 de instalación). El `YTMusicClient.spec` está configurado para empaquetar esta carpeta *dentro* del `.exe`.

3.  **Ejecuta el script de compilación:**
    (Este script simplemente limpia builds anteriores y llama a PyInstaller con el archivo `.spec`).
    ```powershell
    .\build-release.ps1
    ```

4.  ¡Listo! Encontrarás tu ejecutable final en la carpeta `dist/YTMusicClient.exe`.

---

## 🛑 Cosas a Tener en Cuenta

* **Arquitectura de VLC:** No puedo enfatizar esto lo suficiente. Si la aplicación falla al iniciarse con un error de `libvlc.dll` o `ctypes`, es 99% seguro que es un conflicto entre la versión de 32 bits y 64 bits de VLC. **Usa 64 bits para todo** (Python, la instalación de VLC y los archivos en `vlc_lib`).

* **Inicio de Sesión:** La ventana de bienvenida detecta los navegadores instalados con una sesión de YouTube abierta (Firefox, Chrome, Edge, Brave, Opera, Vivaldi…) y permite entrar con un clic. Si no funciona (los navegadores basados en Chromium cifran sus cookies y a veces no se pueden leer), queda la opción manual «Pegar cURL o cookies», que acepta: un cURL de cualquier navegador (F12 -> Red -> `browse` -> Copiar como cURL, en formato bash, cmd de Windows o PowerShell), las cabeceras de la petición copiadas como texto, una cadena de cookies, un `cookies.txt` o un JSON exportado con Cookie-Editor. Solo es imprescindible la cookie de sesión (`__Secure-3PAPISID`); el resto de cabeceras se completan solas. Con sesión iniciada la ventana de bienvenida se omite en los siguientes arranques.

* **Actualizaciones de `yt-dlp`:** La reproducción de audio depende de `yt-dlp` para obtener la URL del stream. Si YouTube cambia su API interna, la reproducción puede dejar de funcionar. Si esto pasa, la solución suele ser actualizar `yt-dlp`:
    ```bash
    pip install --upgrade yt-dlp
    ```
    (Si estás usando el `.exe` compilado, tendrías que recompilarlo con la nueva versión de `yt-dlp`).

---

## 🧱 Arquitectura

El código sigue una arquitectura por capas; las dependencias apuntan siempre hacia adentro y solo `bootstrap.py` conoce todas las clases concretas.

```
app.py            Arranque: logging, QApplication, login y ventana principal
bootstrap.py      Raíz de composición: construye y conecta servicios, presenters y vistas
config.py         Rutas y parámetros ajustables (buffer de VLC, tamaño de cola de radio, etc.)

domain/           Lógica pura, sin red ni disco: PlayQueue, StreamCache, modelos, parseo de letras/búsquedas
infra/            Detalles técnicos: TaskRunner (hilos), ytmusicapi, yt-dlp, VLC, miniaturas, JSON en disco
services/         Casos de uso: reproducción, catálogo, biblioteca, letras, autenticación, sesión, streams
presenters/       Conectan cada vista con sus servicios (una responsabilidad por presenter)
ui/               Solo widgets y señales; no conocen servicios
tests/            Pruebas unitarias, de UI y de presenters; tests/test_live_flows.py usa la red real
```

Decisiones clave:

* **Concurrencia:** `infra/concurrency.TaskRunner` ejecuta trabajo en un `QThreadPool` y entrega los resultados en el hilo principal mediante una señal en cola. *No* uses `threading.Thread` + `QTimer.singleShot(0, fn)`: esa forma de dos argumentos publica en el bucle de eventos del hilo que la llama, y un hilo de Python no tiene ninguno, así que el callback nunca se ejecuta. Con una `key`, solo se entrega el último resultado de cada clave (sin condiciones de carrera entre chips o búsquedas).
* **Reproducción:** `StreamService` usa dos pools (reproducir ahora nunca espera detrás de precargas), deduplica peticiones, promueve una precarga en cola si el usuario la pide, y cachea URLs según su `expire=` real. Al pulsar una canción suena en cuanto se resuelve su stream, mientras las recomendaciones de la radio se cargan en paralelo.
* **Objetos de Python conectados a señales:** PySide solo mantiene referencias débiles a métodos enlazados de objetos que no son `QObject`; por eso `bootstrap.UserInterface` retiene los presenters.

## 🧪 Pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest                       # unitarias, UI y presenters (sin red)

# Flujos completos contra YouTube Music real y VLC (lentas, requieren red):
set YTMUSIC_LIVE_TESTS=1 && python -m pytest tests/test_live_flows.py -q -s
```

Los errores y avisos se registran en `ytmusic-client.log` (junto al ejecutable); la interfaz muestra un aviso emergente cuando algo falla.

## Letras

Las letras se buscan en varios proveedores, en orden, y gana la primera respuesta sincronizada (si nadie la tiene, se muestra texto plano):

1. **Better Lyrics** ([API](https://github.com/better-lyrics/api)): sincronía por sílaba/palabra (TTML). Sin clave solo responde lo que tiene en caché; para el resto hace falta una clave de API, que sus autores entregan por proyecto.
2. **LRCLIB** ([lrclib.net](https://lrclib.net)): gratuito, sincronizado por línea.
3. **YouTube Music**: la letra que trae YouTube (normalmente sin tiempos).

Para cambiar el orden o añadir tu clave, crea `lyrics_settings.json` junto a `app.py` (está en `.gitignore`):

```json
{
  "providers": ["betterlyrics", "lrclib", "youtube"],
  "better_lyrics_api_key": ""
}
```

También se puede usar la variable de entorno `BETTER_LYRICS_API_KEY`. Cuando la letra trae tiempos por palabra, la pestaña *Letra* ilumina cada palabra a medida que se canta, y debajo aparece el proveedor. Un proveedor que falla se omite durante 5 minutos.
