from pathlib import Path

from core.storage_provider import LocalStorageProvider, get_storage_provider


def test_local_storage_provider_saves_and_lists_files(tmp_path, monkeypatch):
    monkeypatch.setattr("core.storage_provider.INPUTS_DIR", tmp_path / "inputs")
    monkeypatch.setattr("core.storage_provider.OUTPUTS_DIR", tmp_path / "outputs")
    provider = LocalStorageProvider()

    input_path = provider.save_input("demo", "entrada", "dados.CSV", b"a")
    output_path = provider.save_output("demo", "resultado.xlsx", b"b")

    assert input_path == tmp_path / "inputs" / "demo" / "entrada.csv"
    assert output_path.exists()
    assert provider.list_outputs("demo") == [output_path]


def test_storage_backend_defaults_to_local(monkeypatch):
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    assert isinstance(get_storage_provider(), LocalStorageProvider)