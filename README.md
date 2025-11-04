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

* **Inicio de Sesión:** El inicio de sesión es un proceso manual. Debes copiar las cabeceras cURL de tu navegador (Chrome F12 -> Red -> `browse` -> Copiar como cURL) y pegarlas en el diálogo de inicio de sesión. Esto se debe a que YouTube Music usa un inicio de sesión complejo (OAuth) que es difícil de automatizar.

* **Actualizaciones de `yt-dlp`:** La reproducción de audio depende de `yt-dlp` para obtener la URL del stream. Si YouTube cambia su API interna, la reproducción puede dejar de funcionar. Si esto pasa, la solución suele ser actualizar `yt-dlp`:
    ```bash
    pip install --upgrade yt-dlp
    ```
    (Si estás usando el `.exe` compilado, tendrías que recompilarlo con la nueva versión de `yt-dlp`).
