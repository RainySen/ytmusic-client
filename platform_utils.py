"""
Utilidades para detectar y manejar diferencias entre plataformas.
"""
import os
import sys
import platform


def get_platform():
    """Find the OS"""
    system = platform.system()
    if system == "Windows":
        return "windows"
    elif system == "Linux":
        return "linux"
    elif system == "Darwin":
        return "macos"
    return "unknown"


def get_config_dir(app_name="ytmusic_client"):
    """
    Obtains the appropriate configuration directory according to the OS.
    """
    current_platform = get_platform()
    
    if current_platform == "windows":
        # Windows: C:\Users\Usuario\AppData\Roaming\ytmusic_client
        base = os.environ.get('APPDATA')
        if not base:
            base = os.path.expanduser('~')
        config_dir = os.path.join(base, app_name)
    
    elif current_platform == "linux":
        # Linux: ~/.config/ytmusic_client
        config_home = os.environ.get('XDG_CONFIG_HOME')
        if not config_home:
            config_home = os.path.expanduser('~/.config')
        config_dir = os.path.join(config_home, app_name)
    
    elif current_platform == "macos":
        # macOS: ~/Library/Application Support/ytmusic_client
        config_dir = os.path.expanduser(f'~/Library/Application Support/{app_name}')
    
    else:
        # Fallback: home directory
        config_dir = os.path.expanduser(f'~/.{app_name}')
    
    # Create the directory if it does not exist
    os.makedirs(config_dir, exist_ok=True)
    
    return config_dir


def get_cache_dir(app_name="ytmusic_client"):
    """
    obtains the appropriate cache directory according to the OS.
    """
    current_platform = get_platform()
    
    if current_platform == "windows":
        base = os.environ.get('LOCALAPPDATA')
        if not base:
            base = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'Local')
        cache_dir = os.path.join(base, app_name, 'Cache')
    
    elif current_platform == "linux":
        cache_home = os.environ.get('XDG_CACHE_HOME')
        if not cache_home:
            cache_home = os.path.expanduser('~/.cache')
        cache_dir = os.path.join(cache_home, app_name)
    
    elif current_platform == "macos":
        cache_dir = os.path.expanduser(f'~/Library/Caches/{app_name}')
    
    else:
        # Fallback
        cache_dir = os.path.expanduser(f'~/.cache/{app_name}')
    
    os.makedirs(cache_dir, exist_ok=True)
    
    return cache_dir


def get_base_dir():
    """
    Obtains the base directory
    """
    if getattr(sys, 'frozen', False):
        # Pyinstaler
        return os.path.dirname(sys.executable)
    else:
        # executed from the source code
        return os.path.dirname(os.path.abspath(__file__))


def get_vlc_instance_args():
    current_platform = get_platform()
    
    base_args = ['--no-video', '--network-caching=3000']
    
    if current_platform == "linux":
        # specify audio output
        # base_args.append('--aout=pulse')  # PulseAudio
        # base_args.append('--aout=alsa')   # ALSA
        pass
    
    return base_args


def is_executable_frozen():
    return getattr(sys, 'frozen', False)


def print_platform_info():
    print("=" * 60)
    print("INFORMACIÓN DE LA PLATAFORMA")
    print("=" * 60)
    print(f"Sistema Operativo: {platform.system()}")
    print(f"Versión: {platform.version()}")
    print(f"Arquitectura: {platform.machine()}")
    print(f"Python: {platform.python_version()}")
    print(f"Plataforma detectada: {get_platform()}")
    print(f"Ejecutable empaquetado: {is_executable_frozen()}")
    print(f"Directorio base: {get_base_dir()}")
    print(f"Directorio de config: {get_config_dir()}")
    print(f"Directorio de caché: {get_cache_dir()}")
    print("=" * 60)


if __name__ == "__main__":
    print_platform_info()
