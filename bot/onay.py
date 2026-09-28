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
OK = {"ok", "okay", "onay", "onayla", "onaylıyorum", "evet", "tamam", "paylas", "paylaş", "yes"}
IPTAL = {"iptal", "hayir", "hayır", "cancel"}
YETKILI = {"OWNER", "MEMBER", "COLLABORATOR"}


def karar(metin: str) -> str | None:
    """Mesajdaki kelimelere bakar; "iptal" her zaman önceliklidir (yanlışlıkla paylaşmaktansa paylaşmamak)."""
    kelimeler = {k.strip(".!,?:;") for k in metin.lower().split()}
    if kelimeler & IPTAL:
        return "iptal"
    if kelimeler & OK:
        return "ok"
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
    # Paylaşım, önizlemede gösterilenin birebir aynısı olsun: metinler ve görseldeki kasa burada sabitlenir.
    if not test:
        gun["onay"]["metinler"] = [ana, *yanitlar]
        gun["onay"]["kasa"] = ozet["kasa"]
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
        try:
            r = self.s.get(self._url(f"collaborators/{kullanici}/permission"), timeout=30)
            return r.ok and r.json().get("permission") in ("admin", "maintain", "write")
        except requests.RequestException:
            return False

    def kapat(self, no: int, mesaj: str) -> None:
        self.s.post(self._url(f"issues/{no}/comments"), json={"body": mesaj}, timeout=30).raise_for_status()
        self.s.patch(self._url(f"issues/{no}"), json={"state": "closed"}, timeout=30).raise_for_status()


def sahibin_karari(gh, no: int) -> str | None:
    """Deponun sahibi/üyesi/ortağının son geçerli cevabı ("ok" / "iptal"); başkalarının yorumları sayılmaz."""
    sonuc = None
    for y in gh.yorumlar(no):
        k = karar(y.get("body") or "")
        if k and (y.get("author_association") in YETKILI or gh.yetkili(y["user"]["login"])):
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
        if not gun or gun["onay"]["durum"] != "bekliyor":
            gh.kapat(no, "Bu istek artık geçerli değil (kupon zaten paylaşıldı, iptal edildi ya da kayıt yok).")
            continue
        if gun.get("tweet_id"):
            # Önceki deneme floodun ortasında kesildi: kararı beklemeden eksik yanıtlar tamamlanır.
            yayinla(ayar, gun, x, gunler, simdi)
            gun["onay"]["durum"] = gun["onay"].get("sonuc_durumu", "onaylandi")
            gh.kapat(no, f"🚀 Paylaşıldı: https://x.com/kalkylerat/status/{gun['tweet_id']}")
            continue
        if k == "iptal":
            gun["onay"]["durum"] = "iptal"
            gun["sonuc"] = "pas"
            gun["pas_nedeni"] = "Paylaşım öncesi iptal edildi."
            onizlemeleri_sil(gun["id"])
            gh.kapat(no, "🛑 İptal edildi: bugün paylaşım yok. Oyunlar rekora girmez.")
        elif k == "ok" or simdi >= datetime.fromisoformat(gun["onay"]["son"]):
            yeni_durum = "onaylandi" if k == "ok" else "otomatik"
            gun["onay"]["sonuc_durumu"] = yeni_durum  # X hatası olursa durum "bekliyor" kalır, sonraki kontrol tekrar dener
            ilk = min(datetime.fromisoformat(s["baslama"]) for s in gun["secimler"])
            # Önizlemedeki görsellerle paylaşılır; görsel yüklenemezse sonraki kontrolde tekrar denenir.
            # Ancak ilk maça 1 saatten az kaldıysa kupon hiç çıkmamaktansa metin olarak paylaşılır.
            gorsel_sart = simdi < ilk - timedelta(minutes=60)
            sonuc = yayinla(ayar, gun, x, gunler, simdi, gorsel_sart=gorsel_sart)
            if sonuc == "gorsel_bekle":
                print("Görsel yüklenemedi; önizlemeyle aynı olsun diye sonraki kontrolde tekrar denenecek.")
                continue
            if sonuc:
                gun["onay"]["durum"] = yeni_durum
                onizlemeleri_sil(gun["id"])
                gh.kapat(no, f"🚀 Paylaşıldı ({'onayla' if k == 'ok' else 'süre dolduğu için otomatik'}): "
                             f"https://x.com/kalkylerat/status/{gun['tweet_id']}")
            else:
                # Tek sebep: ilk maç başlamış (paylaşım artık şeffaf olmaz). Gün pas olur, hata bildirilir.
                gun["onay"]["durum"] = "kacirildi"
                gun["sonuc"] = "pas"
                gun["pas_nedeni"] = "Onay süresi içinde paylaşılamadı."
                onizlemeleri_sil(gun["id"])
                gh.kapat(no, "⚠️ Paylaşılamadı: ilk maç başlamış. Bugün paylaşım yok.")
                raise RuntimeError(f"{gun['id']} kuponu zamanında paylaşılamadı")
