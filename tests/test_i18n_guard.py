import ast
import json
import pathlib
import re

from core import i18n

ROOT = pathlib.Path(__file__).resolve().parent.parent
GUARDED = ("ui", "presenters", "services", "domain", "infra", "core")
SKIP = {"core/i18n.py"}
SPANISH = re.compile(r"[áéíóúñÁÉÍÓÚÑ¿¡]")
PLACEHOLDER = re.compile(r"{(\w+)}")
LOG_METHODS = {"debug", "info", "warning", "error", "exception", "critical"}
# strings that match youtube titles, mood ids sent to youtube, or language endonyms
ALLOWED_CONSTANTS = {"GREETING_KEYS", "_CARD_ROW_KEYS", "LISTEN_AGAIN_KEYS", "APP_LANGUAGE_NAMES", "CONTENT_LANGUAGES",
                     "MOODS"}
# files still holding spanish literals; each extraction batch removes its own, the list ends empty
PENDING = set()


def _sources():
    for folder in GUARDED:
        for path in sorted((ROOT / folder).rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            if rel not in SKIP:
                yield rel, ast.parse(path.read_text(encoding="utf-8"))


def _ignored_nodes(tree):
    ignored = set()
    for node in ast.walk(tree):
        is_log = isinstance(node, ast.Call) and getattr(node.func, "attr", "") in LOG_METHODS
        is_allowed = isinstance(node, (ast.Assign, ast.AnnAssign)) and any(
            getattr(target, "id", "") in ALLOWED_CONSTANTS
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target]))
        is_docstring = isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant)
        if is_log or is_allowed or is_docstring:
            ignored.update(id(child) for child in ast.walk(node))
    return ignored


def spanish_literals(tree):
    ignored = _ignored_nodes(tree)
    return [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)
            and id(node) not in ignored and SPANISH.search(node.value)]


def _catalogs():
    return i18n.load(i18n.locales_dir())


def test_catalogs_have_the_same_keys_and_placeholders():
    catalogs = _catalogs()
    source = catalogs[i18n.SOURCE]
    assert source, "spanish catalog is empty"
    for lang in i18n.SUPPORTED:
        catalog = catalogs[lang]
        assert set(catalog) == set(source), (lang, sorted(set(source) ^ set(catalog))[:10])
        for key, text in catalog.items():
            assert text.strip(), (lang, key)
            assert set(PLACEHOLDER.findall(text)) == set(PLACEHOLDER.findall(source[key])), (lang, key)


def test_no_duplicate_keys_across_area_files():
    for lang in i18n.SUPPORTED:
        seen = {}
        for path in sorted((ROOT / "locales" / lang).glob("*.json")):
            for key in json.loads(path.read_text(encoding="utf-8")):
                assert key not in seen, (lang, key, seen.get(key), path.name)
                seen[key] = path.name


def test_every_t_call_uses_a_known_key():
    known = _catalogs()[i18n.SOURCE]
    missing = []
    for rel, tree in _sources():
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "t" and node.args
                    and isinstance(node.args[0], ast.Constant) and node.args[0].value not in known):
                missing.append((rel, node.args[0].value))
    assert not missing, missing


def test_no_hardcoded_spanish_outside_pending():
    leftovers = {rel: found[:3] for rel, tree in _sources()
                 if rel not in PENDING and (found := spanish_literals(tree))}
    assert not leftovers, leftovers


def _import_time_t_calls(tree):
    found = []

    def visit(node, in_function):
        for child in ast.iter_child_nodes(node):
            nested = in_function or isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
            if (not in_function and isinstance(child, ast.Call) and getattr(child.func, "id", "") == "t"):
                found.append(child.lineno)
            visit(child, nested)

    visit(tree, False)
    return found


def test_no_translation_at_import_time():
    # the language is set after every module is imported
    offenders = {rel: lines for rel, tree in _sources() if (lines := _import_time_t_calls(tree))}
    assert not offenders, offenders
