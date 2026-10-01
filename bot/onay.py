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
# "iptal" = "bir hata var, dur": kupon bekletilir (paylaşılmaz), sahibi hatayı Claude'a söyler, düzeltilince
# yeni önizleme gelir. Düzeltme gelmezse o gün paylaşım olmaz.
IPTAL = {"iptal", "hayir", "hayır", "cancel", "dur", "durdur", "bekle"}
YETKILI = {"OWNER", "MEMBER", "COLLABORATOR"}


def karar(metin: str) -> str | None:
    """Mesajdaki kelimelere bakar; "iptal" her zaman önceliklidir (yanlışlıkla paylaşmaktansa paylaşmamak)."""
    kelimeler = [k.strip(".!,?:;") for k in metin.lower().split()]
    if set(kelimeler) & IPTAL:
        return "iptal"
    # Onay yalnızca mesaj "ok" ile başlıyorsa: "not ok", "ok değil" onay sayılmaz.
    if kelimeler and kelimeler[0] in OK and not {"değil", "degil", "not", "no"} & set(kelimeler):
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
        surum = gun.get("onay", {}).get("surum", 1)
        ad = f'{gun["id"]}-{sira}-v{surum}.png'  # her önizleme yeni dosya: GitHub eski resmi önbellekten göstermesin
        (ONIZLEME_KLASORU / ad).write_bytes(gorsel.kupon_gorseli(gun, kupon, ozet["kasa"], sira, len(liste)))
        resimler.append(_ham_url(f"docs/onizleme/{ad}"))
    ana, *yanitlar = tweets.gun_floodu(gun, ozet, gorselli=True)
    # Paylaşım, önizlemede gösterilenin birebir aynısı olsun: metinler ve görseldeki kasa burada sabitlenir.
    if not test:
        gun["onay"]["metinler"] = [ana, *yanitlar]
        gun["onay"]["kasa"] = ozet["kasa"]
    son = datetime.fromisoformat(gun["onay"]["son"]).astimezone(ZoneInfo(ayar.saat_dilimi))
    baslik = f'{"TEST – " if test else ""}Onay: {gun["id"]} kuponu'
    parcalar = [
        f"**{'TEST: hiçbir şey paylaşılmayacak. ' if test else ''}Cevap olarak yazın:**",
        "- `ok` → hemen X'te paylaşılır",
        "- `iptal` → paylaşım **durur** (hata var demek). Hatayı Claude'a yazın; düzeltilince yeni önizleme gelir.",
        f"- Cevap yoksa **{son:%H:%M}** (İsveç saati) otomatik paylaşılır." if not test else "- Test: cevap gelmezse bir şey olmaz.",
        "", "---", "### Tweet 1 (ana tweet)", "```", ana, "```",
        *[f"![Kupon {i}]({u})" for i, u in enumerate(resimler, 1)],
    ]
    for i, metin in enumerate(yanitlar, 2):
        parcalar += [f"### Tweet {i} (yanıt)", "```", metin, "```"]
    if gun.get("yanit_onerileri"):
        parcalar += ["", "---", "## 💬 Elle yazabileceğin yanıtlar",
                     "Arama linkinden o maçın tweetlerini aç, büyük hesapların tweetlerine @kalkylerat'tan yapıştır:"]
        for o in gun["yanit_onerileri"]:
            parcalar += [f"**{o['mac']}** · [X'te ara]({o['arama']})", "```", o["metin"], "```"]
    ISTEK_DOSYASI.write_text(f"{baslik}\n" + "\n".join(parcalar) + "\n", encoding="utf-8")
    return baslik


def onay_iste(gun: dict, gunler: list[dict], ayar, simdi: datetime) -> None:
    """İlk önizleme ya da düzeltmeden sonra yeni önizleme (sürüm artar, süre yeniden başlar)."""
    ilk = min(datetime.fromisoformat(s["baslama"]) for s in gun["secimler"])
    # En geç ilk maçtan 2 saat önce paylaşılsın; sahibe en fazla onay_suresi_dk süre tanınır.
    son = min(simdi + timedelta(minutes=ayar.onay_suresi_dk), ilk - timedelta(minutes=120))
    # Düzeltme sonrası da sahibine en az 30 dk bakma süresi (ama ilk maçtan en geç 1 saat önce).
    son = min(max(son, simdi + timedelta(minutes=30)), ilk - timedelta(minutes=60))
    surum = (gun.get("onay") or {}).get("surum", 0) + 1
    gun["onay"] = {"durum": "bekliyor", "son": max(son, simdi).isoformat(timespec="seconds"), "surum": surum}
    istek_hazirla(gun, gunler, ayar, simdi)


class GitHub:
    def __init__(self, token: str | None = None, repo: str | None = None):
        self.repo = repo or os.environ.get("GITHUB_REPOSITORY", "")
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token or os.environ.get('GH_TOKEN', '')}",
                               "Accept": "application/vnd.github+json"})

    def _url(self, yol: str) -> str:
        return f"https://api.github.com/repos/{self.repo}/{yol}"

    def istekler(self) -> list[dict]:
        """Son onay istekleri (açık ve kapalı; elle kapatılan istek de kontrol edilir)."""
        r = self.s.get(self._url("issues"), params={"labels": ETIKET, "state": "all", "per_page": 20}, timeout=30)
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

    def yorum(self, no: int, mesaj: str) -> None:
        self.s.post(self._url(f"issues/{no}/comments"), json={"body": mesaj}, timeout=30).raise_for_status()

    def kapat(self, no: int, mesaj: str) -> None:
        self.yorum(no, mesaj)
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
    """Onay bekleyen kuponları işler: karar varsa uygular, yoksa ve süre dolduysa otomatik paylaşır.
    İstek elle kapatılmış olsa bile ("gördüm") kupon beklemede sayılır; kapatmak iptal demek değildir."""
    istekler = gh.istekler()
    for issue in istekler:
        if issue["title"].startswith("TEST") and issue.get("state", "open") == "open":
            k = sahibin_karari(gh, issue["number"])
            if k:
                gh.kapat(issue["number"], f"✅ Test tamam: `{k}` alındı. Gerçek günde bu cevapla kupon "
                                          f"{'hemen paylaşılırdı' if k == 'ok' else 'paylaşılmazdı'}. Hiçbir şey paylaşılmadı.")
                onizlemeleri_sil("test")
    bekleyenler = [g for g in gunler if (g.get("onay") or {}).get("durum") in ("bekliyor", "durduruldu")]
    for issue in istekler:  # geçersiz kalmış açık istekler kapatılır
        if (issue.get("state", "open") == "open" and not issue["title"].startswith("TEST")
                and not any(issue["title"].endswith(f'{g["id"]} kuponu') for g in bekleyenler)):
            gh.kapat(issue["number"], "Bu istek artık geçerli değil (kupon zaten paylaşıldı, iptal edildi ya da kayıt yok).")
    for gun in bekleyenler:
        # En yeni istek geçerlidir (düzeltmeden sonra yeni önizleme açılır); eski aynı günlü istekler kapatılır.
        ayni = sorted((i for i in istekler if not i["title"].startswith("TEST")
                       and i["title"].endswith(f'{gun["id"]} kuponu')), key=lambda i: i["number"], reverse=True)
        for eski in ayni[1:]:
            if eski.get("state", "open") == "open":
                gh.kapat(eski["number"], "Yerine yeni önizleme açıldı.")
        issue = ayni[0] if ayni else None
        no = issue["number"] if issue else None
        _isle(ayar, gh, x, gunler, gun, no, sahibin_karari(gh, no) if no else None, simdi, yayinla)


def _zaten_var(x, gun: dict) -> str | None:
    from .__main__ import zaten_paylasildi
    if gun.get("ek"):
        return None  # ek kupon: o günün ana kuponu X'te zaten var, onunla karıştırılmaz
    try:
        return zaten_paylasildi(x, gun["tarih"])
    except Exception:
        return None


def _isle(ayar, gh, x, gunler, gun, no, k, simdi, yayinla) -> None:
    def bildir(mesaj):
        if no:
            gh.kapat(no, mesaj)

    if gun.get("tweet_id"):
        # Önceki deneme floodun ortasında kesildi: kararı beklemeden eksik yanıtlar tamamlanır.
        yayinla(ayar, gun, x, gunler, simdi)
        gun["onay"]["durum"] = gun["onay"].get("sonuc_durumu", "onaylandi")
        bildir(f"🚀 Paylaşıldı: https://x.com/kalkylerat/status/{gun['tweet_id']}")
        return
    ilk = min(datetime.fromisoformat(s["baslama"]) for s in gun["secimler"])
    if k == "iptal":
        if gun["onay"]["durum"] != "durduruldu":
            gun["onay"]["durum"] = "durduruldu"
            if no:
                gh.yorum(no, "⏸️ Durduruldu, paylaşılmayacak. Hatayı Claude'a yazın; düzeltilince yeni önizleme gelir. "
                             "Bu haliyle paylaşmak isterseniz `ok` yazın.")
        if simdi >= ilk - timedelta(minutes=60):
            # Düzeltme maçlardan önce yetişmedi: bugün paylaşım yok, rekora girmez.
            gun["onay"]["durum"] = "iptal"
            gun["sonuc"] = "pas"
            gun["pas_nedeni"] = "Hata düzeltilemeden maç saati geldi; paylaşılmadı."
            onizlemeleri_sil(gun["id"])
            bildir("🛑 Düzeltme maçlardan önce yetişmedi: bugün paylaşım yok.")
    elif k == "ok" or (gun["onay"]["durum"] == "bekliyor" and simdi >= datetime.fromisoformat(gun["onay"]["son"])):
        yeni_durum = "onaylandi" if k == "ok" else "otomatik"
        gun["onay"]["sonuc_durumu"] = yeni_durum  # X hatası olursa durum "bekliyor" kalır, sonraki kontrol tekrar dener
        # Önizlemedeki görsellerle paylaşılır; görsel yüklenemezse sonraki kontrolde tekrar denenir.
        # Ancak ilk maça 1 saatten az kaldıysa kupon hiç çıkmamaktansa metin olarak paylaşılır.
        gorsel_sart = simdi < ilk - timedelta(minutes=60)
        onceki = _zaten_var(x, gun)
        if onceki:  # kayıt kaybolmuş ama kupon X'te: ikinci kez atılmaz, kayıt düzeltilir
            gun["tweet_id"], gun["onay"]["durum"] = onceki, yeni_durum
            bildir(f"🚀 Zaten paylaşılmış: https://x.com/kalkylerat/status/{onceki}")
            return
        sonuc = yayinla(ayar, gun, x, gunler, simdi, gorsel_sart=gorsel_sart)
        if sonuc == "gorsel_bekle":
            print("Görsel yüklenemedi; önizlemeyle aynı olsun diye sonraki kontrolde tekrar denenecek.")
            return
        if sonuc:
            gun["onay"]["durum"] = yeni_durum
            onizlemeleri_sil(gun["id"])
            bildir(f"🚀 Paylaşıldı ({'onayla' if k == 'ok' else 'süre dolduğu için otomatik'}): "
                   f"https://x.com/kalkylerat/status/{gun['tweet_id']}")
        else:
            # Tek sebep: ilk maç başlamış (paylaşım artık şeffaf olmaz). Gün pas olur, hata bildirilir.
            gun["onay"]["durum"] = "kacirildi"
            gun["sonuc"] = "pas"
            gun["pas_nedeni"] = "Onay süresi içinde paylaşılamadı."
            onizlemeleri_sil(gun["id"])
            bildir("⚠️ Paylaşılamadı: ilk maç başlamış. Bugün paylaşım yok.")
            raise RuntimeError(f"{gun['id']} kuponu zamanında paylaşılamadı")
