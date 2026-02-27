import json
import os

from platform_utils import get_config_dir, get_base_dir


def clean_cache():
    config_dir = get_config_dir()
    base_dir = get_base_dir()

    possible_locations = [
        os.path.join(config_dir, "queue_and_cache.json"),
        os.path.join(base_dir, "queue_and_cache.json"),
        "queue_and_cache.json",
        os.path.expanduser("~/.ytmusic_player/queue_and_cache.json"),
    ]

    cache_file = None
    for location in possible_locations:
        if os.path.exists(location):
            cache_file = location
            print(f"Encontrado: {cache_file}")
            break

    if not cache_file:
        print(" No se encontró el archivo de caché")
        for loc in possible_locations:
            print(f"   - {loc}")
        return False

    try:
        # read file
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"\n📊 Estado actual:")
        print(f"   Cola: {len(data.get('queue', []))} canciones")
        print(f"   Índice actual: {data.get('current_index', -1)}")
        print(f"   Caché de streams: {len(data.get('stream_cache', {}))} URLs")

        # clean stream cache
        data['stream_cache'] = {}

        # save
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True

    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":

    clean_cache()
