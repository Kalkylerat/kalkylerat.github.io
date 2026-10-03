"""Günlük yanıt kiti: sahibinin elle yanıtlaması için günün büyük maçları, aranacak X bağlantıları ve kopyalanmaya
hazır yanıt metinleri (GitHub issue'su: telefona bildirim gelir).

Neden: yeni ve küçük hesabın kendi postları dağıtıma neredeyse hiç girmez (3 Ekim: post başına ~5 görüntülenme).
Küçük hesaplar büyük hesapların maç postlarına ilk 30–60 dakikada verilen anlamlı yanıtlarla görünür olur. X otomasyon
kuralları başkalarına otomatik yanıtı yasaklar: bot yalnızca taslak hazırlar, yanıtı sahibi kendi elleriyle atar."""

from datetime import datetime, timedelta
from urllib.parse import quote

from . import analiz, config, gorsel

ETIKET = "yanit-kiti"
KLASOR = config.ROOT / "docs" / "kit"
# Maç postlarına sık yanıt gelen büyük futbol hesapları (aramada bunların postlarını öne çıkarmak için)
BUYUK_HESAPLAR = ("OptaJoe", "OptaAnalyst", "Squawka", "ESPNFC", "brfootball", "FabrizioRomano", "FootballTweet",
                  "TrollFootball", "433", "goal", "SkySportsPL", "MilliTakimlar", "TFF_Org")


def _pct(p: float) -> str:
    return f"{100 * p:.0f}%"


def yanitlar(a: dict) -> list[str]:
    """Bir maç için 2–3 kısa, insan gibi yanıt taslağı (yalnızca kayıttaki rakamlar; seçim/bahis dili yok)."""
    p = a["p"]
    skor, p_skor = a["skorlar"][0]
    ev, dep = a["ev"], a["dep"]
    taslak = [f"Our model has {ev} {_pct(p['MS1'])}, draw {_pct(p['MSX'])}, {dep} {_pct(p['MS2'])}. "
              f"Likeliest score {skor}, but only {_pct(p_skor)}. Feels about right?",
              f"Over 2.5 goals sits at {_pct(p['UST25'])} for this one, both teams scoring {_pct(p['KGVAR'])}. "
              f"More goals than that or a tight game?"]
    c = (a.get("karsilastirma") or [None])[0]
    if c and abs(analiz.fark_puani(c)) >= 8:
        taslak.append(f"Odd one: the odds give {c['ad']} {_pct(c['piyasa'])}, team stats say {_pct(c['istatistik'])}. "
                      f"Which would you trust here?")
    return taslak


def kit_metni(gun: dict, maclar: list[dict], saatler: list[str], resimler: list[str]) -> str:
    satirlar = [f"Günün yanıt kiti ({gun['tarih']}). Hesap yalnızca kendi postlarıyla görünmüyor; büyüme büyük hesapların "
                "maç postlarına verilen yanıtlardan gelir. Her maç için: aramayı aç, en çok etkileşim alan **yeni** "
                "(son 1 saat) postu bul, taslaklardan birini kendi cümlenle düzelt, kart görselini ekleyip yanıtla. "
                "Günde 10–20 yanıt, maç saatinden 1–2 saat önce en iyisi. Yanıt gelirse geri yaz (sohbet en güçlü sinyal).",
                "", "**Hızlı kurallar:** link yok, hashtag yok, aynı metni iki kez yapıştırma, tartışmaya girme.", ""]
    hesaplar = " OR ".join(f"from:{h}" for h in BUYUK_HESAPLAR)
    for a, saat, resim in zip(maclar, saatler, resimler):
        ara = quote(f'{a["ev"]} {a["dep"]}')
        buyuk = quote(f'({a["ev"]} OR {a["dep"]}) ({hesaplar})')
        satirlar += [f"### 🆚 {a['ev']} v {a['dep']} · {saat}",
                     f"- 🔎 [Bu maçla ilgili popüler postlar](https://x.com/search?q={ara}&f=top) · "
                     f"[son postlar](https://x.com/search?q={ara}&f=live) · "
                     f"[büyük hesapların postları](https://x.com/search?q={buyuk}&f=live)",
                     *(f"- 💬 `{t}`" for t in yanitlar(a)),
                     f"- 🖼️ Kart: {resim}" if resim else "", ""]
    return "\n".join(s for s in satirlar if s is not None)


def gonder(gun: dict, ayar, gh, saat, simdi: datetime, ham_url: str, yaz=print) -> int | None:
    """Bugünün kiti gönderilmediyse issue açar; kart görsellerini docs/kit/<tarih>/ altına yazar (7 günden eskiler
    silinir). Açılan issue numarası ya da None."""
    if gun.get("yanit_kiti") or gun.get("konsept") != "analiz":
        return None
    maclar = [a for a in gun.get("analizler") or [] if datetime.fromisoformat(a["baslama"]) > simdi][:6]
    if not maclar:
        return None
    klasor = KLASOR / gun["tarih"]
    klasor.mkdir(parents=True, exist_ok=True)
    resimler = []
    for a in maclar:
        dosya = klasor / f'{a["fixture_id"]}.png'
        dosya.write_bytes(gorsel.analiz_karti(a, saat(a), "en"))
        resimler.append(f"{ham_url}/docs/kit/{gun['tarih']}/{dosya.name}")
    sinir = (simdi - timedelta(days=7)).date().isoformat()
    for eski in KLASOR.iterdir():
        if eski.is_dir() and eski.name < sinir:
            for f in eski.iterdir():
                f.unlink()
            eski.rmdir()
    govde = (f"@{ayar.alarm_kime} " if ayar.alarm_kime else "") + kit_metni(gun, maclar, [saat(a) for a in maclar], resimler)
    no = gh.issue_ac(f"💬 Yanıt kiti {gun['tarih']}", govde, ETIKET)
    gun["yanit_kiti"] = {"issue": no, "zaman": simdi.isoformat(timespec="seconds")}
    yaz(f"Yanıt kiti gönderildi (issue #{no}).")
    return no
