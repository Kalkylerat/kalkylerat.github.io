import pytest


@pytest.fixture(autouse=True)
def _kopya_sayfalari_gecici_klasore(tmp_path, monkeypatch):
    """Testler docs/kit altına kopyalama sayfası bırakmasın (bot çalışması onları depoya işlerdi)."""
    from bot import kopya
    monkeypatch.setattr(kopya, "KLASOR", tmp_path / "kit")
