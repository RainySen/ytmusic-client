import json

import pytest

from core import i18n

CATALOGS = {"es": {"a.b": "Hola", "a.c": "Solo es", "q.n": "{n} canciones"}, "en": {"a.b": "Hi"}, "pt": {}}


@pytest.fixture(autouse=True)
def restore_language():
    yield
    i18n.set_language("es", i18n.load(i18n.locales_dir()))


def test_lookup_falls_back_to_spanish_then_to_the_key():
    i18n.set_language("en", CATALOGS)
    assert i18n.t("a.b") == "Hi"
    assert i18n.t("a.c") == "Solo es"
    assert i18n.t("x.y") == "x.y"


def test_placeholders_and_missing_values():
    i18n.set_language("es", CATALOGS)
    assert i18n.t("q.n", n=5) == "5 canciones"
    assert i18n.t("q.n") == "{n} canciones"


def test_unknown_language_uses_spanish():
    assert i18n.set_language("fr", CATALOGS) == "es"
    assert i18n.language() == "es"


@pytest.mark.parametrize("name, expected", [
    ("es_ES", "es"), ("es_419", "es"), ("es-MX", "es"), ("pt_BR", "pt"), ("pt_PT", "pt"),
    ("en_US", "en"), ("de_DE", "en"), ("", "en"),
])
def test_system_language(name, expected):
    assert i18n.system_language(name) == expected


def test_load_merges_area_files_and_skips_broken_json(tmp_path):
    folder = tmp_path / "es"
    folder.mkdir()
    (folder / "one.json").write_text(json.dumps({"one.a": "A"}), encoding="utf-8")
    (folder / "two.json").write_text(json.dumps({"two.b": "B"}), encoding="utf-8")
    (folder / "broken.json").write_text("{not json", encoding="utf-8")
    assert i18n.load(str(tmp_path))["es"] == {"one.a": "A", "two.b": "B"}


@pytest.mark.parametrize("lang, separator", [("es", ","), ("en", "."), ("pt", ",")])
def test_format_decimal_separator(lang, separator):
    i18n.set_language(lang, i18n.load(i18n.locales_dir()))
    assert i18n.t("format.decimal") == separator


def test_app_language_setting_accepts_only_supported_codes():
    from domain.settings import Settings
    assert Settings().app_language == ""
    assert Settings.from_dict({"app_language": "pt"}).app_language == "pt"
    assert Settings.from_dict({"app_language": "fr"}).app_language == ""
    assert Settings.from_dict({"app_language": 5}).app_language == ""


def test_resolve_language_prefers_the_setting_then_windows():
    from domain.settings import Settings
    assert i18n.resolve_language(Settings(app_language="en"), "es_ES") == "en"
    assert i18n.resolve_language(Settings(), "pt_BR") == "pt"
    assert i18n.resolve_language(Settings(), "de_DE") == "en"


def test_first_run_takes_the_content_language_from_the_app_language(tmp_path):
    from core.bootstrap import apply_language
    from infra.settings_repository import SettingsRepository
    from services.settings_service import SettingsService

    fresh = SettingsService(SettingsRepository(str(tmp_path / "new.json")))
    assert apply_language(fresh, settings_is_new=True, locale_name="en_US") == "en"
    assert fresh.settings.content_language == "en" and i18n.language() == "en"

    existing = SettingsService(SettingsRepository(str(tmp_path / "old.json")))
    existing.update(content_language="es")
    assert apply_language(existing, settings_is_new=False, locale_name="pt_BR") == "pt"
    assert existing.settings.content_language == "es"
