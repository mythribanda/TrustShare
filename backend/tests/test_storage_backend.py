from app.storage_backend import delete_object, get_bytes, health, object_exists, put_bytes

def test_local_storage_roundtrip_and_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_PROVIDER", "local")
    payload = b"encrypted bytes only"
    put_bytes("a/b.enc", payload, tmp_path)
    assert object_exists("a/b.enc", tmp_path)
    assert get_bytes("a/b.enc", tmp_path) == payload
    assert health(tmp_path)["available"] is True
    delete_object("a/b.enc", tmp_path)
    assert not object_exists("a/b.enc", tmp_path)
