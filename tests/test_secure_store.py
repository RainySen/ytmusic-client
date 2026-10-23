import json

import pytest

from infra import secure_store

SESSION = {"cookie": "SAPISID=secreto; __Secure-3PAPISID=otro", "authorization": "SAPISIDHASH 123"}

windows_only = pytest.mark.skipif(not secure_store.available(), reason="DPAPI solo existe en Windows")


@windows_only
def test_the_session_is_unreadable_on_disk_and_round_trips(tmp_path):
    path = tmp_path / "oauth.json"
    assert secure_store.write_secret_json(str(path), SESSION)
    raw = path.read_bytes()
    assert raw.startswith(secure_store.MAGIC) and b"SAPISID" not in raw
    assert secure_store.is_encrypted(str(path))
    assert secure_store.read_secret_json(str(path)) == SESSION


def test_a_plaintext_session_from_older_versions_is_still_read(tmp_path):
    path = tmp_path / "oauth.json"
    path.write_text(json.dumps(SESSION), encoding="utf-8")
    assert not secure_store.is_encrypted(str(path))
    assert secure_store.read_secret_json(str(path)) == SESSION


def test_missing_and_damaged_files_fall_back_to_the_default(tmp_path):
    assert secure_store.read_secret_json(str(tmp_path / "nope.json"), "sin datos") == "sin datos"
    damaged = tmp_path / "damaged.json"
    damaged.write_bytes(secure_store.MAGIC + b"no es un blob valido")
    assert secure_store.read_secret_json(str(damaged), None) is None
    assert secure_store.is_encrypted(str(damaged))


@windows_only
def test_a_failed_encryption_never_falls_back_to_plain_text(tmp_path, monkeypatch):
    def broken(_data):
        raise OSError("CryptProtectData failed")
    monkeypatch.setattr(secure_store, "protect", broken)
    path = tmp_path / "oauth.json"
    assert not secure_store.write_secret_json(str(path), SESSION)
    assert not path.exists()


@windows_only
def test_text_secrets_round_trip_and_unknown_tokens_are_dropped():
    token = secure_store.protect_text("clave-123")
    assert token.startswith(secure_store.TEXT_PREFIX) and "clave-123" not in token
    assert secure_store.unprotect_text(token) == "clave-123"
    assert secure_store.unprotect_text(secure_store.TEXT_PREFIX + "basura") == ""
    assert secure_store.unprotect_text("clave-antigua") == "clave-antigua"


@windows_only
def test_another_windows_user_cannot_decrypt_it(tmp_path):
    blob = secure_store.protect(b"secreto")
    assert secure_store.unprotect(blob) == b"secreto"
    with pytest.raises(OSError):
        secure_store.unprotect(blob[:-5] + b"xxxxx")
