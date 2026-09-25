import os
import shutil
import sys

import pefile

KEEP_MODULES = {
    "QtCore", "QtDataVisualization", "QtGui", "QtNetwork", "QtOpenGL", "QtOpenGLWidgets", "QtPrintSupport",
    "QtSvg", "QtWebChannel", "QtWebEngineCore", "QtWebEngineWidgets", "QtWidgets",
}
KEEP_LOCALES = {"en-US", "es", "es-419"}
DROP_DIRS = ("qml", "qmltooling")
DROP_PAKS = ("qtwebengine_devtools_resources.pak", "qtwebengine_devtools_resources.debug.pak",
             "qtwebengine_resources.debug.pak", "v8_context_snapshot.debug.bin")


def _size(path: str) -> int:
    return os.path.getsize(path) if os.path.exists(path) else 0


def _remove(path: str, freed: list) -> None:
    freed[0] += _size(path)
    os.remove(path)


def _imports(path: str) -> set:
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
    names = {entry.dll.decode().lower() for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", [])}
    pe.close()
    return names


# recortar bundle qt sin usar
def prune(root: str) -> int:
    qt = os.path.join(root, "PySide6")
    freed = [0]

    for name in os.listdir(qt):
        if name.endswith(".pyd") and name[:-4] not in KEEP_MODULES:
            _remove(os.path.join(qt, name), freed)

    for name in DROP_DIRS:
        target = os.path.join(qt, name)
        for base, _dirs, files in os.walk(target):
            for file in files:
                freed[0] += _size(os.path.join(base, file))
        if os.path.isdir(target):
            shutil.rmtree(target)

    resources = os.path.join(qt, "resources")
    for name in DROP_PAKS:
        path = os.path.join(resources, name)
        if os.path.exists(path):
            _remove(path, freed)

    translations = os.path.join(qt, "translations")
    for base, _dirs, files in os.walk(translations):
        for file in files:
            if file.endswith(".qm") or (file.endswith(".pak") and file[:-4] not in KEEP_LOCALES):
                _remove(os.path.join(base, file), freed)

    available = {n.lower(): os.path.join(qt, n) for n in os.listdir(qt) if n.lower().endswith(".dll")}
    pending = [os.path.join(qt, n) for n in os.listdir(qt) if n.endswith((".pyd", ".exe"))]
    for base, _dirs, files in os.walk(os.path.join(qt, "plugins")):
        pending += [os.path.join(base, f) for f in files if f.endswith(".dll")]
    pending += [p for n, p in available.items() if not n.startswith("qt6")]

    reached = set()
    while pending:
        path = pending.pop()
        for dll in _imports(path):
            if dll in available and dll not in reached:
                reached.add(dll)
                pending.append(available[dll])

    for name, path in available.items():
        if name.startswith("qt6") and name not in reached:
            _remove(path, freed)
    return freed[0]


if __name__ == "__main__":
    internal = os.path.join(sys.argv[1], "_internal")
    print(f"recortado: {prune(internal) / 1024 / 1024:.0f} MB")
