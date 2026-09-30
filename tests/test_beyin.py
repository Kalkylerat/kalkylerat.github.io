import json
from datetime import datetime, timezone
from types import SimpleNamespace

from beyin import firtina


def _mesaj(metin, stop="end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=metin)], stop_reason=stop, stop_details=None,
        usage=SimpleNamespace(input_tokens=100, output_tokens=50, cache_read_input_tokens=0,
                              cache_creation_input_tokens=0),
    )


class SahteClaude:
    """Oylamada B2 ve C1'i öne çıkarır; ilk taslağa Gelir Uzmanı itiraz eder, ikinci taslak oybirliğiyle geçer."""

    def __init__(self):
        self.cagrilar = []
        self.taslak = 0
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **k):
        self.cagrilar.append(k)
        sistem, gorev = k["system"], k["messages"][0]["content"]
        sema = k["output_config"].get("format", {}).get("schema")
        if sema and "puanlar" in sema["properties"]:
            hedefler = sema["properties"]["puanlar"]["items"]["properties"]["fikir"]["enum"]
            puan = lambda f: 9 if f in ("B2", "C1") else 4  # noqa: E731
            msg = _mesaj(json.dumps({"puanlar": [
                {"fikir": f, **{kr: puan(f) for kr in firtina.KRITERLER}, "yorum": "ok"} for f in hedefler]}))
        elif sema:
            itiraz = "Gelir Uzmanı" in sistem and "1. taslak" in gorev
            msg = _mesaj(json.dumps({"onay": not itiraz, "gerekce": "gerekçe", "gerekli_degisiklik": "gelir planı"}))
        elif "Yazman" in sistem:
            self.taslak += 1
            msg = _mesaj(f"# Karar: Hesap\n{self.taslak}. taslak")
        elif k.get("tools") and len(k["messages"]) == 1:
            msg = _mesaj("araştırıyorum", stop="pause_turn")
        else:
            msg = _mesaj(f"yanıt ({sistem.split('.')[0]})")
        return _Baglam(msg)


class _Baglam:
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.msg


def test_beyin_firtinasi_tum_turlar(tmp_path, monkeypatch):
    monkeypatch.setattr(firtina, "KARARLAR", tmp_path)
    client = SahteClaude()
    t = firtina.Toplanti(client=client, istekler="Yeni X hesabı.", ek_not="Türkçe olsun",
                         simdi=datetime(2026, 10, 1, tzinfo=timezone.utc))
    ozet, tutanak = t.calistir()

    # Kimse kendi fikrine puan vermez.
    for c in client.cagrilar:
        sema = c["output_config"].get("format", {}).get("schema")
        if sema and "puanlar" in sema["properties"]:
            harf = next(u.harf for u in firtina.UZMANLAR if f"ekibin {u.ad}" in c["system"])
            assert not any(f.startswith(harf) for f in sema["properties"]["puanlar"]["items"]["properties"]["fikir"]["enum"])
    # Web araması yalnızca öneri ve denetim turlarında; pause_turn sonrası devam edilir.
    webli = [c for c in client.cagrilar if c.get("tools")]
    assert len(webli) == 12 and all(len(c["messages"]) in (1, 2) for c in webli)
    assert "Türkçe olsun" in client.cagrilar[0]["system"]
    # Finalistler en yüksek puanlılar; itiraz sonrası 2. taslak oybirliğiyle kabul.
    gorevler = [c["messages"][0]["content"] for c in client.cagrilar]
    assert sum("Finale kalanlar: C1, B2" in g or "Finale kalanlar: B2, C1" in g for g in gorevler) == 3
    assert "2. taslak" in ozet and "oybirliğiyle" in ozet
    assert "❌ İtiraz" in tutanak and "| B2 |" in ozet

    karar, tut = firtina.kaydet(ozet, tutanak, t.simdi)
    assert karar.name == "2026-10-01-0000-karar.md" and tut.exists()
