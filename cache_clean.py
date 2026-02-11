import json
import os
from datetime import datetime, timedelta


def clean_cache():
    """Limpia el caché de streams expirados"""

    # Buscar el archivo de estado
    possible_locations = [
        "queue_and_cache.json",
        os.path.join(os.path.dirname(__file__), "queue_and_cache.json"),
        os.path.expanduser("~/.ytmusic_player/queue_and_cache.json"),
    ]

    cache_file = None
    for location in possible_locations:
        if os.path.exists(location):
            cache_file = location
            print(f"✅ Encontrado: {cache_file}")
            break

    if not cache_file:
        print("❌ No se encontró el archivo de caché")
        print("   Archivos buscados:")
        for loc in possible_locations:
            print(f"   - {loc}")
        return False

    try:
        # Leer el archivo
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"\n📊 Estado actual:")
        print(f"   Cola: {len(data.get('queue', []))} canciones")
        print(f"   Índice actual: {data.get('current_index', -1)}")
        print(f"   Caché de streams: {len(data.get('stream_cache', {}))} URLs")

        # Limpiar el caché de streams
        old_cache_count = len(data.get('stream_cache', {}))
        data['stream_cache'] = {}

        # Guardar
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Caché limpiado:")
        print(f"   Eliminados: {old_cache_count} streams expirados")
        print(f"   La cola y la posición actual se mantienen")
        print(f"\n💡 Ahora ejecuta: python app.py")
        print(f"   Las canciones se descargarán de nuevo cuando las reproduzcas")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("LIMPIADOR DE CACHÉ DE STREAMS")
    print("=" * 60)
    print("\nEste script elimina los URLs de YouTube expirados")
    print("manteniendo tu cola de reproducción intacta.\n")

    clean_cache()

    print("\n" + "=" * 60)