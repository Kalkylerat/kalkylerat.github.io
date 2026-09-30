import csv
import importlib.util
import json
import os
import time
from pathlib import Path

import pytest

_yol = Path(__file__).resolve().parents[1] / "suno" / "suno-muzik" / "duzenle.py"
_spec = importlib.util.spec_from_file_location("suno_duzenle", _yol)
duzenle = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(duzenle)


def _eski_yap(p):
    t = time.time() - 3600
    os.utime(p, (t, t))


def test_isaretten_sonra_inenleri_tasir(tmp_path):
    kok, indir = tmp_path / "Suno", tmp_path / "Downloads"
    indir.mkdir()
    eski = indir / "eski.mp3"
    eski.write_bytes(b"x")
    _eski_yap(eski)
    (indir / "belge.pdf").write_bytes(b"x")

    ortak = ["--kok", str(kok), "--indirilenler", str(indir)]
    duzenle.main(ortak + ["isaret"])
    (indir / "Gece Yolu.mp3").write_bytes(b"a")
    (indir / "Gece Yolu (1).mp3").write_bytes(b"b")
    sozler = tmp_path / "s.txt"
    sozler.write_text("[Chorus]\nla la", encoding="utf-8")

    duzenle.main(ortak + ["tasi", "--proje", "Yaz: Albüm", "--baslik", "Gece/Yolu",
                          "--stil", "synthwave", "--sozler-dosyasi", str(sozler), "--bekle", "0"])

    klasorler = list((kok / "Yaz Albüm").iterdir())
    assert len(klasorler) == 1 and klasorler[0].name.endswith("_GeceYolu")
    hedef = klasorler[0]
    assert sorted(p.name for p in hedef.glob("*.mp3")) == ["Gece Yolu (1).mp3", "Gece Yolu.mp3"]
    assert eski.exists() and (indir / "belge.pdf").exists()
    assert (hedef / "sozler.txt").read_text(encoding="utf-8") == "[Chorus]\nla la"
    assert json.loads((hedef / "bilgi.json").read_text(encoding="utf-8"))["stil"] == "synthwave"
    with (kok / "katalog.csv").open(encoding="utf-8-sig") as f:
        satirlar = list(csv.DictReader(f))
    assert [s["baslik"] for s in satirlar] == ["Gece/Yolu"]


def test_ozel_klasor_yapisi(tmp_path):
    kok, indir = tmp_path / "Suno", tmp_path / "Downloads"
    indir.mkdir()
    ortak = ["--kok", str(kok), "--indirilenler", str(indir)]
    duzenle.main(ortak + ["isaret"])
    (indir / "a.mp3").write_bytes(b"a")
    duzenle.main(ortak + ["tasi", "--baslik", "x", "--klasor", "Rock/../2026\\Gece: Yolu", "--bekle", "0"])
    assert (kok / "Rock" / "2026" / "Gece Yolu" / "a.mp3").exists()


def test_isaret_yoksa_durur(tmp_path):
    (tmp_path / "D").mkdir()
    with pytest.raises(SystemExit):
        duzenle.main(["--kok", str(tmp_path / "S"), "--indirilenler", str(tmp_path / "D"),
                      "tasi", "--baslik", "x", "--bekle", "0"])
