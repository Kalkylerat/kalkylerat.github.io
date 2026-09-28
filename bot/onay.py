"""Paylaşım öncesi onay: kupon hazırlanınca GitHub'da önizlemeli bir "issue" açılır.
Sahibi "ok" yazarsa hemen, "iptal" yazarsa hiç paylaşılmaz; cevap gelmezse son saatte otomatik paylaşılır."""

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from . import config, gorsel, kayit, tweets

ONIZLEME_KLASORU = config.ROOT / "docs" / "onizleme"
ISTEK_DOSYASI = config.ROOT / "onay_istegi.md"  # iş akışı bu dosya varsa issue açar
ETIKET = "onay"
OK = ("ok", "okay", "onay", "onayla", "evet", "paylas", "paylaş", "yes")
IPTAL = ("iptal", "hayir", "hayır", "cancel", "no")


def karar(metin: str) -> str | None:
    kelime = metin.strip().lower().split()[0].strip(".!,") if metin.strip() else ""
    if kelime in OK:
        return "ok"
    if kelime in IPTAL:
        return "iptal"
    return None


def _ham_url(yol: str) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "Kalkylerat/kalkylerat.github.io")
    dal = os.environ.get("GITHUB_REF_NAME", "claude/twitter-football-predictions-ywwfxw")
    return f"https://raw.githubusercontent.com/{repo}/{dal}/{yol}"


def istek_hazirla(gun: dict, gunler: list[dict], ayar, simdi: datetime, test: bool = False) -> str:
    """Önizleme görsellerini kaydeder ve issue metnini ISTEK_DOSYASI'na yazar. Başlığı döndürür."""
    ozet = kayit.ozet(gunler, ayar.kasa_baslangic)
    liste = kayit.kuponlar(gun)
    ONIZLEME_KLASORU.mkdir(parents=True, exist_ok=True)
    resimler = []
    for sira, kupon in enumerate(liste, 1):
        ad = f'{gun["id"]}-{sira}.png'
        (ONIZLEME_KLASORU / ad).write_bytes(gorsel.kupon_gorseli(gun, kupon, ozet["kasa"], sira, len(liste)))
        resimler.append(_ham_url(f"docs/onizleme/{ad}"))
    ana, *yanitlar = tweets.gun_floodu(gun, ozet, gorselli=True)
    son = datetime.fromisoformat(gun["onay"]["son"]).astimezone(ZoneInfo(ayar.saat_dilimi))
    baslik = f'{"TEST – " if test else ""}Onay: {gun["tarih"]} kuponu'
    parcalar = [
        f"**{'TEST: hiçbir şey paylaşılmayacak. ' if test else ''}Cevap olarak yazın:**",
        "- `ok` → hemen X'te paylaşılır",
        "- `iptal` → bugün paylaşılmaz",
        f"- Cevap yoksa **{son:%H:%M}** (İsveç saati) otomatik paylaşılır." if not test else "- Test: cevap gelmezse bir şey olmaz.",
        "", "---", "### Tweet 1 (ana tweet)", "```", ana, "```",
        *[f"![Kupon {i}]({u})" for i, u in enumerate(resimler, 1)],
    ]
    for i, metin in enumerate(yanitlar, 2):
        parcalar += [f"### Tweet {i} (yanıt)", "```", metin, "```"]
    ISTEK_DOSYASI.write_text(f"{baslik}\n" + "\n".join(parcalar) + "\n", encoding="utf-8")
    return baslik


def onay_iste(gun: dict, gunler: list[dict], ayar, simdi: datetime) -> None:
    ilk = min(datetime.fromisoformat(s["baslama"]) for s in gun["secimler"])
    # En geç ilk maçtan 2 saat önce paylaşılsın; sahibe en fazla onay_suresi_dk süre tanınır.
    son = min(simdi + timedelta(minutes=ayar.onay_suresi_dk), ilk - timedelta(minutes=120))
    gun["onay"] = {"durum": "bekliyor", "son": max(son, simdi).isoformat(timespec="seconds")}
    istek_hazirla(gun, gunler, ayar, simdi)


class GitHub:
    def __init__(self, token: str | None = None, repo: str | None = None):
        self.repo = repo or os.environ.get("GITHUB_REPOSITORY", "")
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token or os.environ.get('GH_TOKEN', '')}",
                               "Accept": "application/vnd.github+json"})

    def _url(self, yol: str) -> str:
        return f"https://api.github.com/repos/{self.repo}/{yol}"

    def acik_istekler(self) -> list[dict]:
        r = self.s.get(self._url("issues"), params={"labels": ETIKET, "state": "open", "per_page": 20}, timeout=30)
        r.raise_for_status()
        return r.json()

    def yorumlar(self, no: int) -> list[dict]:
        r = self.s.get(self._url(f"issues/{no}/comments"), params={"per_page": 100}, timeout=30)
        r.raise_for_status()
        return r.json()

    def yetkili(self, kullanici: str) -> bool:
        r = self.s.get(self._url(f"collaborators/{kullanici}/permission"), timeout=30)
        return r.ok and r.json().get("permission") in ("admin", "maintain", "write")

    def kapat(self, no: int, mesaj: str) -> None:
        self.s.post(self._url(f"issues/{no}/comments"), json={"body": mesaj}, timeout=30).raise_for_status()
        self.s.patch(self._url(f"issues/{no}"), json={"state": "closed"}, timeout=30).raise_for_status()


def sahibin_karari(gh, no: int) -> str | None:
    """Yazma yetkisi olan birinin son geçerli cevabı ("ok" / "iptal"); başkalarının yorumları sayılmaz."""
    sonuc = None
    for y in gh.yorumlar(no):
        k = karar(y.get("body") or "")
        if k and gh.yetkili(y["user"]["login"]):
            sonuc = k
    return sonuc


def onizlemeleri_sil(gun_id: str) -> None:
    for yol in ONIZLEME_KLASORU.glob(f"{gun_id}-*.png"):
        yol.unlink()


def kontrol(ayar, gh, x, gunler: list[dict], simdi: datetime, yayinla) -> None:
    """Açık onay isteklerini işler: karar varsa uygular, yoksa ve süre dolduysa otomatik paylaşır."""
    for issue in gh.acik_istekler():
        baslik, no = issue["title"], issue["number"]
        k = sahibin_karari(gh, no)
        if baslik.startswith("TEST"):
            if k:
                gh.kapat(no, f"✅ Test tamam: `{k}` alındı. Gerçek günde bu cevapla kupon "
                             f"{'hemen paylaşılırdı' if k == 'ok' else 'paylaşılmazdı'}. Hiçbir şey paylaşılmadı.")
                onizlemeleri_sil("test")
            continue
        gun = next((g for g in gunler if g.get("onay") and baslik.endswith(f'{g["tarih"]} kuponu')), None)
        if not gun or gun.get("tweet_id") or gun["onay"]["durum"] != "bekliyor":
            gh.kapat(no, "Bu istek artık geçerli değil (kupon zaten paylaşıldı ya da kayıt yok).")
            continue
        if k == "iptal":
            gun["onay"]["durum"] = "iptal"
            gun["sonuc"] = "pas"
            gun["pas_nedeni"] = "Paylaşım öncesi iptal edildi."
            onizlemeleri_sil(gun["id"])
            gh.kapat(no, "🛑 İptal edildi: bugün paylaşım yok. Oyunlar rekora girmez.")
        elif k == "ok" or simdi >= datetime.fromisoformat(gun["onay"]["son"]):
            gun["onay"]["durum"] = "onaylandi" if k == "ok" else "otomatik"
            if yayinla(ayar, gun, x, gunler, simdi):
                onizlemeleri_sil(gun["id"])
                gh.kapat(no, f"🚀 Paylaşıldı ({'onayla' if k == 'ok' else 'süre dolduğu için otomatik'}): "
                             f"https://x.com/kalkylerat/status/{gun['tweet_id']}")
            else:
                gh.kapat(no, "⚠️ Paylaşılamadı (ilk maç başlamış olabilir). Ayrıntı için çalışmanın özet sayfasına bakın.")
