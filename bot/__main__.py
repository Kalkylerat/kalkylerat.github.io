"""Kullanım: python -m bot [otomatik|tahmin|yayinla|sonuc|panel|demo|tani|onizleme|duzelt|sabit]"""

import argparse
import copy
import json
import os
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import config, editor, football, gorsel, kayit, model, onay, panel, tweets
from .model import adaylari_uret, bet_builder, etiketler

# Çalışma sırasında yakalanan hatalar: iş sonunda "başarısız" işaretlenir, GitHub sahibine e-posta atar.
HATALAR: list[str] = []

GUVENLI_LIMIT = 10
API_YEDEK = 25  # sabah taramasından sonra gün içi sonuç kontrolleri ve elle komutlar için ayrılan istek


class HakYetmiyor(RuntimeError):
    """Günlük API hakkı taramaya yetmiyor; yedeğe dokunulmaz."""
DEGER_LIMIT = 6


def _hata(adim: str, e: Exception) -> None:
    HATALAR.append(f"{adim}: {e}")
    _ozet_yaz(f"❌ {adim} başarısız: {e}")


def _ozet_yaz(metin: str) -> None:
    """GitHub Actions özet sayfasına yazar; telefondan taslağı görmek için."""
    print(metin)
    yol = os.environ.get("GITHUB_STEP_SUMMARY")
    if yol:
        with open(yol, "a", encoding="utf-8") as f:
            f.write(metin + "\n\n")


def tahmin(ayar, api, sec, gunler: list[dict], bugun: str, simdi: datetime) -> dict | None:
    if kayit.bul(gunler, bugun):
        print(f"{bugun} için kayıt zaten var, atlanıyor.")
        return None
    try:
        maclar = football.gunun_maclari(api, bugun, ayar.ligler, ayar.saat_dilimi,
                                        ayar.min_dakika_once, 10_000, simdi, tum_ligler=ayar.tum_ligler)
    except football.ApiHatasi as e:
        _hata("Maç listesi (API-Football)", e)
        return None
    print(f"{len(maclar)} uygun maç bulundu.")
    try:
        mac_map, adaylar = _toplu_tara(ayar, api, maclar, bugun)
    except HakYetmiyor as e:
        # Hak azken eski yönteme geçmek kalanı da bitirir; sonuçlar için yedek korunur, bugün kupon çıkmaz.
        _hata("Tarama", e)
        return None
    except football.ApiHatasi as e:
        # Toplu tarama çalışmazsa eski yöntem: izinli liglerden maç maç (maç başına 2 istek, yedeğe dokunmadan).
        print(f"Toplu oran taraması yapılamadı ({e}); maç maç taramaya geçiliyor.")
        kalan = football.kalan_istek(api) if hasattr(api, "session") else None
        adet = ayar.max_mac_tarama if kalan is None else max(0, min(ayar.max_mac_tarama, (kalan - API_YEDEK) // 2))
        izinli = [m for m in maclar if m["lig_id"] in ayar.ligler][:adet]
        mac_map, adaylar = _mac_mac_tara(ayar, api, izinli)
    guvenli = sorted((a for a in adaylar if a["tur"] == "guvenli"), key=lambda a: a["adil_olasilik"], reverse=True)
    deger = sorted((a for a in adaylar if a["tur"] == "deger"), key=lambda a: a["deger"], reverse=True)
    adaylar = guvenli[:GUVENLI_LIMIT] + deger[:DEGER_LIMIT]
    print(f"{len(guvenli)} güvenli, {len(deger)} değer adayı; API isteği: {api.istek_sayisi}")

    gun = {"id": bugun, "tarih": bugun, "olusturma": simdi.isoformat(timespec="seconds"),
           "baslik": "", "secimler": [], "sonuc": None, "tweet_id": None,
           "para": ayar.para_birimi, "yuzde": ayar.oyun_yuzdesi}
    if adaylar:
        for fid in {a["fixture_id"] for a in adaylar}:
            try:
                mac_map[fid]["sakatlar"] = football.sakatlari_al(api, fid)
            except football.ApiHatasi as e:
                print(f"Sakat listesi alınamadı: {e}")
                break
        try:
            karar = sec(mac_map, adaylar, ayar)
        except Exception as e:
            # Kayıt oluşturulmaz: sorun geçince aynı gün elle "otomatik" çalıştırılabilir.
            _hata("Seçim (Claude)", e)
            return None
    else:
        karar = {"secimler": [], "gerekce_yoksa": "Kriterleri geçen yüksek ihtimalli oyun yok."}

    if not karar["secimler"]:
        gun["sonuc"] = "pas"
        gun["pas_nedeni"] = karar.get("gerekce_yoksa", "")
        gunler.append(gun)
        _ozet_yaz(f"### {bugun}: bugün oyun yok\n{gun['pas_nedeni']}")
        return None

    aday_map = {a["aday_id"]: a for a in adaylar}
    stake = round(kayit.kasa(gunler, ayar.kasa_baslangic) * ayar.oyun_yuzdesi / 100, 2)
    kupon_nosu = {i: n for n, k in enumerate(karar["kuponlar"]) for i in k["aday_idler"]}
    for s in karar["secimler"]:
        a = aday_map[s["aday_id"]]
        m = mac_map[a["fixture_id"]]
        gun["secimler"].append({
            "fixture_id": a["fixture_id"], "lig": _lig_adi(m, ayar), "ev": m["ev"], "dep": m["dep"],
            "baslama": m["baslama"],
            "saat": datetime.fromisoformat(m["baslama"]).astimezone(ZoneInfo(ayar.saat_dilimi)).strftime("%H:%M %Z"),
            "olasi_skor": a["olasi_skor"], "pazar": a["pazar"], "tur": a["tur"], "etiket": a["etiket"],
            # Oyunlar tek tek oynanmaz (stake 0); yatırım kupon başınadır.
            "kisa": a["kisa"], "oran": a["oran"], "stake": 0, "kupon_no": kupon_nosu[s["aday_id"]],
            "bolag": a["bolag"], "oranlar": a.get("oranlar", {}), "adil_olasilik": a["adil_olasilik"], "adil_kaynak": a["adil_kaynak"],
            "model_olasilik": a["model_olasilik"], "deger": a["deger"], "beklenen_gol": a["beklenen_gol"],
            "yorum": editor.temiz_yorum(s["yorum"], ayar.oran_bahiscileri + [ayar.keskin_bahisci]),
            "durum": "bekliyor", "skor": None,
        })
    gun["secimler"] = bet_builder_birlestir(gun["secimler"])
    gun["secimler"].sort(key=lambda s: s["baslama"])
    # Kuponlar ilk maçlarının saatine göre sıralanır.
    nolar = sorted({s["kupon_no"] for s in gun["secimler"]},
                   key=lambda n: min(s["baslama"] for s in gun["secimler"] if s["kupon_no"] == n))
    gun["kuponlar"] = [{"ayaklar": [i for i, s in enumerate(gun["secimler"]) if s["kupon_no"] == n],
                        "stake": stake, "durum": None} for n in nolar]
    gun["baslik"] = karar["baslik"].strip()
    gun["yanit_onerileri"] = editor.yanit_onerilerini_hazirla(
        karar.get("yanit_onerileri") or [], mac_map, ayar.oran_bahiscileri + [ayar.keskin_bahisci])
    gunler.append(gun)

    taslak = "\n\n".join(tweets.gun_floodu(gun, kayit.ozet(gunler, ayar.kasa_baslangic)))
    _ozet_yaz(f"### {bugun} taslak\n```\n{taslak}\n```")
    return gun


def _incele(ayar, api, m: dict, bahisciler: dict, mac_map: dict, adaylar: list) -> None:
    ist = football.istatistik_al(api, m["fixture_id"])
    if not ist:
        return
    mac_adaylari = adaylari_uret(m, bahisciler, ist, ayar, guvenilir_lig=m["lig_id"] in ayar.ligler)
    if mac_adaylari:
        mac_map[m["fixture_id"]] = {**m, "istatistik": ist}
        adaylar += mac_adaylari


def _toplu_tara(ayar, api, maclar: list[dict], bugun: str) -> tuple[dict, list]:
    """1) Günün bütün oranları toplu çekilir, 2) piyasaya göre en umut vadeden maçlar detaylı incelenir."""
    # Günlük hak koruması: gün içindeki sonuç kontrolleri ve elle komutlar için en az API_YEDEK istek kalsın.
    kalan = football.kalan_istek(api) if hasattr(api, "session") else None
    sayfa = ayar.max_oran_sayfasi
    if kalan is not None:
        sayfa = max(0, min(sayfa, kalan - API_YEDEK - 2 * ayar.max_detay_mac - 1))
        print(f"API-Football: bugün {kalan} istek kalmış, toplu taramaya {sayfa} sayfa ayrıldı.")
    if sayfa == 0:
        raise HakYetmiyor(f"günlük istek hakkı toplu tarama için yetmiyor (kalan {kalan})")
    oranlar = football.toplu_oranlar(api, bugun, ayar.saat_dilimi, sayfa)
    if not oranlar:
        raise football.ApiHatasi("toplu taramada hiç oran gelmedi")
    puanli = []
    for m in maclar:
        if m["fixture_id"] in oranlar:
            puan = model.on_eleme_puani(oranlar[m["fixture_id"]], ayar, m["lig_id"] in ayar.ligler)
            if puan is not None:
                puanli.append((puan, m))
    puanli.sort(key=lambda x: x[0], reverse=True)
    secilen = puanli[:ayar.max_detay_mac]
    izinli = [m for m in maclar if m["lig_id"] in ayar.ligler]
    kapsanan = sum(m["fixture_id"] in oranlar for m in izinli)
    _ozet_yaz(f"Tarama: {len(maclar)} maç, {len(oranlar)} maçın oranı okundu (izinli liglerden {kapsanan}/{len(izinli)}), "
              f"{len(puanli)} maç ön elemeyi geçti, {len(secilen)} maç detaylı incelendi: "
              + ", ".join(f'{m["ev"]} v {m["dep"]} ({m["lig"]})' for _, m in secilen))
    mac_map, adaylar = {}, []
    for _, m in secilen:
        try:
            _incele(ayar, api, m, oranlar[m["fixture_id"]], mac_map, adaylar)
        except football.ApiHatasi as e:
            print(f"Detaylı inceleme erken bitti: {e}")
            break
    return mac_map, adaylar


def _mac_mac_tara(ayar, api, maclar: list[dict]) -> tuple[dict, list]:
    mac_map, adaylar = {}, []
    for m in maclar:
        try:
            bahisciler = football.oranlari_al(api, m["fixture_id"])
            if bahisciler:
                _incele(ayar, api, m, bahisciler, mac_map, adaylar)
        except football.ApiHatasi as e:
            # Günlük istek sınırı dolarsa o ana kadar taranan maçlarla devam edilir.
            print(f"Tarama erken bitti: {e}")
            break
    return mac_map, adaylar


def _lig_adi(m: dict, ayar) -> str:
    """Sponsor adında bahis sitesi geçen ligler görselde/tweette ülke adıyla gösterilir."""
    yasakli = [b.lower() for b in ayar.oran_bahiscileri + [ayar.keskin_bahisci]] + ["bet", "casino"]
    if any(y in m["lig"].lower() for y in yasakli):
        return f'{m.get("ulke") or "League"} league'
    return m["lig"]


def bet_builder_birlestir(secimler: list[dict]) -> list[dict]:
    """Aynı maçtaki seçimleri tek bir bet builder oyununa çevirir (tek oran, tek yatırım)."""
    gruplar: dict[int, list[dict]] = {}
    for s in secimler:
        gruplar.setdefault(s["fixture_id"], []).append(s)
    sonuc = []
    for bacaklar in gruplar.values():
        if len(bacaklar) == 1:
            sonuc.append(bacaklar[0])
            continue
        oran, olasilik = bet_builder(bacaklar)
        ilk = bacaklar[0]
        sonuc.append({
            **{k: ilk[k] for k in ("fixture_id", "lig", "ev", "dep", "baslama", "saat", "olasi_skor", "stake", "beklenen_gol",
                                   "kupon_no") if k in ilk},
            "pazar": "BB", "bet_builder": True,
            "tur": "deger" if any(b["tur"] == "deger" for b in bacaklar) else "guvenli",
            "etiket": " + ".join(b["etiket"] for b in bacaklar),
            "kisa": " + ".join(b["kisa"] for b in bacaklar),
            "oran": oran, "adil_olasilik": olasilik, "deger": round(olasilik * oran - 1, 3),
            "yorum": " ".join(b["yorum"] for b in bacaklar if b["yorum"]),
            "bacaklar": [{k: b[k] for k in ("pazar", "etiket", "kisa", "oran", "adil_olasilik")} | {"durum": "bekliyor"}
                         for b in bacaklar],
            "durum": "bekliyor", "skor": None,
        })
    return sonuc


def _zincir(x, metinler: list[str], ilk_yanit: str, idler: list[str]) -> None:
    """Metinleri art arda yanıt olarak atar; önceki denemede atılanları (idler) atlar, kaldığı yerden sürer."""
    onceki = idler[-1] if idler else ilk_yanit
    for metin in metinler[len(idler):]:
        onceki = x.gonder(metin, yanit=onceki)
        idler.append(onceki)


GORSEL_BEKLE = "gorsel_bekle"


def yayinla(ayar, gun: dict, x, gunler: list[dict], simdi: datetime, gorsel_sart: bool = False) -> bool | str:
    """gorsel_sart: onaylı kupon görselsiz (önizlemeden farklı) paylaşılmasın; görsel yüklenemezse GORSEL_BEKLE döner."""
    """Günün floodunu atar. Önceki çalışma floodun ortasında kesildiyse eksik yanıtları tamamlar."""
    if not gun["secimler"]:
        return False
    ilk = min(datetime.fromisoformat(s["baslama"]) for s in gun["secimler"])
    if ilk <= simdi:
        print("İlk maç başlamış; şeffaflık için bu oyunlar artık yayınlanmaz.")
        return False
    if gun.get("tweet_id"):
        onayli = (gun.get("onay") or {}).get("metinler")
        if onayli and gun.get("gorselli"):
            ana, *devam = onayli
        else:
            ana, *devam = tweets.gun_floodu(gun, kayit.ozet(gunler, ayar.kasa_baslangic), gorselli=gun.get("gorselli", False))
        idler = gun.setdefault("analiz_tweet_idleri", [])
        if len(idler) >= len(devam):
            return False
        print(f"Yarım kalan flood tamamlanıyor ({len(idler)}/{len(devam)}).")
        _zincir(x, devam, gun["tweet_id"], idler)
        return True
    onayli = (gun.get("onay") or {}).get("metinler")
    kasa = (gun.get("onay") or {}).get("kasa", kayit.ozet(gunler, ayar.kasa_baslangic)["kasa"])
    medya = _gorsel_yukle(x, gun, kasa)
    if gorsel_sart and not medya:
        gun.pop("gorsel_eksik", None)
        return GORSEL_BEKLE
    if medya and onayli:
        ana, *devam = onayli  # önizlemede onaylanan (ya da gösterilen) metinlerin birebir aynısı
    else:
        ana, *devam = tweets.gun_floodu(gun, kayit.ozet(gunler, ayar.kasa_baslangic), gorselli=bool(medya))
    gun["tweet_id"] = x.gonder(ana, medya=medya)
    gun["gorselli"] = bool(medya)
    gun["yayin"] = simdi.isoformat(timespec="seconds")
    gun["analiz_tweet_idleri"] = []
    _zincir(x, devam, gun["tweet_id"], gun["analiz_tweet_idleri"])
    print(f"Yayınlandı: tweet {gun['tweet_id']}")
    return True


def zaten_paylasildi(x, tarih: str) -> str | None:
    """Kayıt kaybolduysa (ör. push başarısız) aynı günün kuponunu ikinci kez atmamak için hesabın son
    ana tweetlerine bakar. Bulunursa tweet kimliğini döndürür."""
    etiket = f'| {datetime.fromisoformat(tarih).strftime("%-d %b")}'
    for t in x.son_tweetler(adet=5, yanitsiz=True):
        metin = t["text"].lstrip("⚽ ")
        if metin.startswith("TODAY'S") and etiket in metin.splitlines()[0]:
            return t["id"]
    return None


GORSEL_DENEME = 4


def _gorsel_yukle(x, gun: dict, kasa: float, bekle=time.sleep) -> list[str] | None:
    """Her kupon için bir görsel yükler; geçici hatalarda (ağ, X yoğunluğu) birkaç kez tekrar dener.
    Biri bile yüklenemezse kuponlar maç başlamadan metin olarak gider ve durum özet sayfasına yazılır."""
    liste = kayit.kuponlar(gun)
    idler = []
    for sira, kupon in enumerate(liste, 1):
        png = gorsel.kupon_gorseli(gun, kupon, kasa, sira, len(liste))
        for deneme in range(1, GORSEL_DENEME + 1):
            try:
                idler.append(x.medya_yukle(png))
                break
            except Exception as e:
                print(f"Görsel {sira} yükleme denemesi {deneme}/{GORSEL_DENEME} başarısız: {e}")
                if deneme < GORSEL_DENEME:
                    bekle(15 * deneme)
        else:
            gun["gorsel_eksik"] = True
            _ozet_yaz("⚠️ Kupon görseli X'e yüklenemedi; kuponlar metin olarak paylaşıldı.")
            return None
    return idler or None


def duzelt(ayar, gun: dict, x, gunler: list[dict], simdi: datetime) -> bool:
    """Bugünün tweetlerini siler ve güncel biçimle tekrar paylaşır (maçlar başlamadıysa). Oyunlar ve kuponlar değişmez."""
    if not gun.get("tweet_id"):
        return False
    ilk = min(datetime.fromisoformat(s["baslama"]) for s in gun["secimler"])
    if ilk <= simdi:
        print("İlk maç başlamış; yayınlanmış oyunlar değiştirilemez.")
        return False
    for tid in reversed([gun["tweet_id"]] + gun.get("analiz_tweet_idleri", [])):
        x.sil(tid)
    gun["tweet_id"], gun["analiz_tweet_idleri"] = None, []
    for s in gun["secimler"]:
        # Eski kayıtlardaki etiketler güncel, sade ifadelerle yenilenir.
        for b in s.get("bacaklar") or [s]:
            b["etiket"], b["kisa"] = etiketler(b["pazar"], s["ev"], s["dep"])
        if s.get("bet_builder"):
            s["etiket"] = " + ".join(b["etiket"] for b in s["bacaklar"])
            s["kisa"] = " + ".join(b["kisa"] for b in s["bacaklar"])
    return yayinla(ayar, gun, x, gunler, simdi)


def yenile(ayar, api, sec, x, gunler: list[dict], bugun: str, simdi: datetime) -> bool:
    """Bugünün paylaşımını siler ve günün seçimini güncel kurallarla baştan yapıp paylaşır.
    Yalnızca bugünün hiçbir maçı başlamadıysa; başlamış maçın paylaşımı asla silinmez."""
    gun = kayit.bul(gunler, bugun)
    if gun and gun["secimler"]:
        ilk = min(datetime.fromisoformat(s["baslama"]) for s in gun["secimler"])
        if ilk <= simdi:
            print("Bugünün ilk maçı başlamış; paylaşım silinemez.")
            return False
    # Önce yeni seçim bir kopya üzerinde yapılır; eskisi ancak geçerli bir sonuç (yeni kupon ya da
    # "bugün kurallara uyan oyun yok") çıkarsa silinir. Hata olursa hiçbir şeye dokunulmaz.
    kopya = [g for g in gunler if g is not gun]
    yeni = tahmin(ayar, api, sec, kopya, bugun, simdi)
    if not kayit.bul(kopya, bugun):
        print("Yeni seçim yapılamadı; bugünkü paylaşım olduğu gibi bırakıldı.")
        return False
    if gun:
        for tid in reversed([gun.get("tweet_id")] + gun.get("analiz_tweet_idleri", [])):
            if tid:
                x.sil(tid)
    gunler[:] = kopya
    return bool(yeni) and yayinla(ayar, yeni, x, gunler, simdi)


def sabit_tweet(x) -> None:
    """Eski karşılama tweetlerini siler, açıklayıcı iki tweeti (ana + yanıt) atar. Sabitleme X uygulamasından yapılır."""
    for t in x.son_tweetler():
        if t["text"].startswith(tweets.ESKI_KARSILAMA):
            x.sil(t["id"])
            print(f"Eski karşılama tweeti silindi: {t['id']}")
    ana = x.gonder(tweets.SABIT_TWEETLER[0])
    x.gonder(tweets.SABIT_TWEETLER[1], yanit=ana)
    _ozet_yaz(f"Karşılama tweeti atıldı: https://x.com/kalkylerat/status/{ana} (X uygulamasından profile sabitleyin)")


def sonuc(ayar, api, x, gunler: list[dict], simdi: datetime) -> None:
    ids = kayit.bekleyen_fixturelar(gunler, simdi) if api is not None else []
    if ids:
        sonuclar = football.sonuclari_al(api, ids, kayit.korner_fixturelari(gunler))
        kayit.sorgulandi(gunler, ids, simdi)
        for g in kayit.sonuclandir(gunler, sonuclar, simdi):
            print(f"{g['id']} sonuçlandı.")
    else:
        print("Sonuç bekleyen maç yok.")
    # Sonuçlanıp sonuç floodu atılmamış (ya da yarım kalmış) her gün: X hatası olsa bile sonraki çalışmada tamamlanır.
    for g in gunler:
        if g.get("tweet_id") and g["sonuc"] == "tamam" and not g.get("sonuc_tweet_id"):
            idler = g.setdefault("sonuc_tweet_idleri", [])
            try:
                metinler = tweets.sonuc_tweetleri(g, kayit.ozet(gunler, ayar.kasa_baslangic))
                if not idler:
                    # Sonuç ayrı bir paylaşım olarak kuponu alıntılar: profilde ve akışta görünür (yanıtlar görünmez).
                    idler.append(x.gonder(metinler[0], alinti=g["tweet_id"]))
                _zincir(x, metinler, g["tweet_id"], idler)
            except RuntimeError as e:
                if "duplicate" not in str(e).lower():
                    raise
                # X tweeti almış ama yanıt kaybolmuş: aynı metin tekrar reddedilir, sonsuz denemeye girilmez.
                _ozet_yaz(f"⚠️ {g['id']} sonuç tweeti X'te zaten var (yanıtı kaybolmuş); tekrar denenmeyecek.")
                idler.append("x-mukerrer")
            g["sonuc_tweet_id"] = idler[0]


HAFTA_MIN_OYUN = 3
HAFTA_MIN_GUN = 3


def haftalik(ayar, x, gunler: list[dict], simdi: datetime, zorla: bool = False) -> bool:
    """Pazar akşamı (ya da kaçarsa Pazartesi) biten haftanın özetini bir kez paylaşır."""
    yerel = simdi.astimezone(ZoneInfo(ayar.saat_dilimi))
    if not zorla and not (yerel.weekday() == 6 and yerel.hour >= 21 or yerel.weekday() in (0, 1, 2)):
        return False  # Pazar akşamı; maçı sonuçlanmayan hafta Çarşamba'ya kadar beklenir
    pazar = (yerel - timedelta(days=(yerel.weekday() + 1) % 7)).date()
    anahtar = f"{pazar.isocalendar().year}-W{pazar.isocalendar().week:02d}"
    kayitlar = json.loads(config.HAFTA_FILE.read_text()) if config.HAFTA_FILE.exists() else {}
    if anahtar in kayitlar:
        return False
    h = kayit.hafta_ozeti(gunler, pazar.isoformat())
    if h["bekleyen"]:
        print(f"{anahtar}: haftanın {h['bekleyen']} oyunu henüz sonuçlanmadı; özet sonraki çalışmada.")
        return False
    if h["oyun"] < HAFTA_MIN_OYUN or h["gun"] < HAFTA_MIN_GUN:
        print(f"{anahtar}: haftalık özet için yeterli oyun yok ({h['gun']} gün, {h['oyun']} oyun).")
        return False
    metin = tweets.hafta_tweeti(h, kayit.ozet(gunler, ayar.kasa_baslangic), ayar.para_birimi)
    medya = None
    seyir = kayit.kasa_seyri(gunler, ayar.kasa_baslangic, pazar.isoformat())
    if len(seyir) >= 3:
        try:
            medya = [x.medya_yukle(gorsel.kasa_grafigi(seyir, ayar.kasa_baslangic, ayar.para_birimi))]
        except Exception as e:
            print(f"Kasa grafiği eklenemedi: {e}")  # özet metin olarak yine gider
    kayitlar[anahtar] = x.gonder(metin, medya=medya)
    config.HAFTA_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.HAFTA_FILE.write_text(json.dumps(kayitlar, indent=2) + "\n")
    _ozet_yaz(f"Haftalık özet paylaşıldı ({anahtar}):\n```\n{metin}\n```")
    return True


def _sabah_penceresi(simdi: datetime, ayar) -> bool:
    """Planlı sabah çalışmasından 20 dk sonra ile 2,5 saat sonrası arası (yerel saat, yaz/kış aynı kalır)."""
    yerel = simdi.astimezone(ZoneInfo(ayar.saat_dilimi))
    bas = (12 * 60 + 47) if yerel.weekday() < 5 else (10 * 60 + 17)
    dk = yerel.hour * 60 + yerel.minute
    return bas + 20 <= dk <= bas + 150


def _api(ayar):
    return football.ApiFootball(config.env("API_FOOTBALL_KEY"), aralik=ayar.istek_araligi_sn)


def _x_client():
    return tweets.XClient(config.env("X_API_KEY"), config.env("X_API_SECRET"),
                          config.env("X_ACCESS_TOKEN"), config.env("X_ACCESS_SECRET"))


def _secici():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return editor.claude_ile_sec
    print("ANTHROPIC_API_KEY yok: kural tabanlı basit seçim kullanılıyor (yalnızca demo).")
    return editor.basit_sec


def onizleme(ayar) -> None:
    """Sıradaki paylaşım gününü (sabah 10'dan önce bugün, sonra yarın) gerçek veriyle hazırlar; kaydetmez, paylaşmaz."""
    simdi = kayit.simdi_utc()
    yerel = simdi.astimezone(ZoneInfo(ayar.saat_dilimi))
    gun = (yerel if yerel.hour < 10 else yerel + timedelta(days=1)).date().isoformat()
    _ozet_yaz(f"## ÖNİZLEME – {gun} (kaydedilmez, paylaşılmaz)")
    gunler = kayit.yukle(config.DATA_FILE)
    gunler = [g for g in gunler if g["id"] != gun]
    tahmin(ayar, _api(ayar), _secici(), gunler, gun, simdi)


def tani(ayar) -> None:
    """Tweet atmadan tüm bağlantıları ve veri kapsamını kontrol eder."""
    import anthropic
    satirlar = ["### Tanı"]
    api = _api(ayar)
    try:
        durum = api.session.get(f"{football.BASE_URL}/status", timeout=30).json().get("response", {})
        plan = (durum.get("subscription") or {}).get("plan")
        istek = durum.get("requests") or {}
        satirlar.append(f"- API-Football: plan **{plan}**, bugün {istek.get('current')}/{istek.get('limit_day')} istek")
    except Exception as e:
        satirlar.append(f"- API-Football durum okunamadı: {e}")
    simdi = kayit.simdi_utc()
    tz = ZoneInfo(ayar.saat_dilimi)
    ornek_fixture = None
    for gun in range(2):
        tarih = (simdi.astimezone(tz) + timedelta(days=gun)).date().isoformat()
        ham = api.session.get(f"{football.BASE_URL}/fixtures",
                              params={"date": tarih, "timezone": ayar.saat_dilimi}, timeout=30).json()
        tum = ham.get("response", [])
        sezonlar = sorted({f["league"]["season"] for f in tum})
        izlenen = [f for f in tum if f["league"]["id"] in ayar.ligler]
        from collections import Counter
        populer = Counter(f'{f["league"]["name"]} ({f["league"]["country"]}, id {f["league"]["id"]})' for f in tum).most_common(6)
        satirlar.append(f"  - {tarih} en çok maçı olan ligler: {populer}")
        satirlar.append(f"- {tarih} ham yanıt: tüm dünyada {len(tum)} maç, sezonlar {sezonlar[:5]}, "
                        f"izlenen liglerde {len(izlenen)} (durumlar: {sorted({f['fixture']['status']['short'] for f in izlenen})}), "
                        f"hatalar: {ham.get('errors') or '-'}")
        maclar = football.gunun_maclari(api, tarih, ayar.ligler, ayar.saat_dilimi, 0, 999, simdi)
        ligler = sorted({m["lig"] for m in maclar})
        satirlar.append(f"- {tarih}: izlenen liglerde başlamamış **{len(maclar)}** maç ({', '.join(ligler) or '-'})")
        if maclar and not ornek_fixture:
            ornek_fixture = maclar[0]
    if ornek_fixture:
        bahisciler = football.oranlari_al(api, ornek_fixture["fixture_id"])
        adlar = sorted(bahisciler)
        keskin = any(a.lower() == ayar.keskin_bahisci.lower() for a in adlar)
        secili = [a for a in adlar if a.lower() in {b.lower() for b in ayar.oran_bahiscileri}]
        pazarlar = sorted({k for o in bahisciler.values() for k in o})
        satirlar.append(f"- Oran örneği ({ornek_fixture['ev']} – {ornek_fixture['dep']}): {len(adlar)} bahisçi; "
                        f"{ayar.keskin_bahisci} {'VAR' if keskin else 'YOK'}; oran bahisçileri: {', '.join(secili) or 'YOK'}")
        satirlar.append(f"  - Tüm bahisçiler: {', '.join(adlar) or '-'}")
        satirlar.append(f"  - Okunan pazarlar: {', '.join(pazarlar) or '-'}")
    try:
        r = _x_client().session.get("https://api.x.com/2/users/me", params={"user.fields": "pinned_tweet_id",
                                    "expansions": "pinned_tweet_id"}, timeout=30)
        satirlar.append(f"- X: {r.status_code} {r.json().get('data', {}).get('username') or r.text[:200]}")
        sabit = (r.json().get("includes", {}).get("tweets") or [{}])[0]
        satirlar.append(f"- Sabit tweet: {sabit.get('id', 'YOK')} {sabit.get('text', '')[:60]!r}")
        ornek_gun = next((g for g in reversed(kayit.yukle(config.DATA_FILE)) if kayit.kuponlar(g)), None)
        if ornek_gun:
            try:
                png = gorsel.kupon_gorseli(ornek_gun, kayit.kuponlar(ornek_gun)[0], ayar.kasa_baslangic)
                satirlar.append(f"- X görsel yükleme (paylaşılmaz): medya {_x_client().medya_yukle(png)}")
            except Exception as e:
                satirlar.append(f"- X görsel yükleme hatası: {e}")
    except Exception as e:
        satirlar.append(f"- X hatası: {e}")
    try:
        m = anthropic.Anthropic().models.retrieve(ayar.claude_model)
        satirlar.append(f"- Anthropic: model {m.id} erişilebilir")
    except Exception as e:
        satirlar.append(f"- Anthropic hatası: {e}")
    _ozet_yaz("\n".join(satirlar))


def oran_testi(ayar) -> None:
    """Toplu oran taramasının ücretsiz planda çalışıp çalışmadığını ölçer (paylaşım yok, ~4 istek)."""
    from collections import Counter
    api = _api(ayar)
    tz = ZoneInfo(ayar.saat_dilimi)
    yarin = (kayit.simdi_utc().astimezone(tz) + timedelta(days=1)).date().isoformat()
    satirlar = [f"### Toplu oran testi ({yarin})"]
    for params in ({"date": yarin, "timezone": ayar.saat_dilimi, "page": 1}, {"date": yarin, "page": 2}):
        try:
            body = api.session.get(f"{football.BASE_URL}/odds", params=params, timeout=30).json()
            resp = body.get("response", [])
            ligler = Counter(f'{r["league"]["name"]} ({r["league"]["country"]})' for r in resp)
            bm = sorted({b["name"] for r in resp for b in r.get("bookmakers", [])})
            satirlar.append(f"- {params}: sonuç {body.get('results')}, sayfa {body.get('paging')}, "
                            f"hata {body.get('errors') or '-'}; bahisçiler {bm[:15]}; ligler {ligler.most_common(8)}")
        except Exception as e:
            satirlar.append(f"- {params}: HATA {e}")
    try:
        durum = api.session.get(f"{football.BASE_URL}/status", timeout=30).json().get("response", {})
        satirlar.append(f"- İstek sayacı: {(durum.get('requests') or {}) if isinstance(durum, dict) else durum}")
    except Exception as e:
        satirlar.append(f"- durum okunamadı: {e}")
    _ozet_yaz("\n".join(satirlar))


def demo(ayar) -> None:
    ornek = config.ROOT / "ornek"
    api = football.DemoApi(ornek / "api_football.json")
    simdi = datetime.fromisoformat(api.data["simdi"])
    bugun = simdi.astimezone(ZoneInfo(ayar.saat_dilimi)).date().isoformat()
    gunler: list[dict] = []
    x = tweets.KonsolClient(ornek)
    gun = tahmin(ayar, api, _secici(), gunler, bugun, simdi)
    if gun:
        yayinla(ayar, gun, x, gunler, simdi)
        sonuc(ayar, api, x, gunler, simdi + timedelta(days=1))
    panel.olustur(gunler, ornek / "demo_panel.html", ayar)
    print(f"\nÖzet: {kayit.ozet(gunler, ayar.kasa_baslangic)}\nPanel önizlemesi: ornek/demo_panel.html")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="bot")
    p.add_argument("komut", choices=["otomatik", "tahmin", "yayinla", "sonuc", "panel", "demo", "tani", "onizleme", "duzelt", "sabit", "hafta", "yenile", "oran_testi",
                                          "onay_kontrol", "onay_testi", "onay_yenile", "nabiz",
                                          "sonuc_yeniden"])
    args = p.parse_args(argv)
    ayar = config.yukle()

    if args.komut == "demo":
        demo(ayar)
        return 0
    if args.komut == "tani":
        tani(ayar)
        return 0
    if args.komut == "oran_testi":
        oran_testi(ayar)
        return 0
    if args.komut == "onizleme":
        onizleme(ayar)
        return 0
    if args.komut == "sabit":
        sabit_tweet(_x_client())
        return 0

    gunler = kayit.yukle(config.DATA_FILE)
    simdi = kayit.simdi_utc()
    bugun = simdi.astimezone(ZoneInfo(ayar.saat_dilimi)).date().isoformat()
    try:
        # Her adım ayrı: sonuç ya da haftalık özet hatası günün kuponunu engellemez.
        if args.komut == "nabiz":
            # 15 dakikada bir: onay bekleyen kupon, bitmiş maçların sonuçları, haftalık özet.
            try:
                onay.kontrol(ayar, onay.GitHub(), _x_client(), gunler, simdi, yayinla)
            except Exception as e:
                _hata("Onay kontrolü", e)
        if args.komut in ("otomatik", "sonuc", "nabiz"):
            try:
                sonuc(ayar, _api(ayar), _x_client(), gunler, simdi)
            except football.ApiHatasi as e:
                if "limit" in str(e).lower():
                    # Günlük hak dolmuş: hata e-postası yağmasın, gece yarısı (UTC) sıfırlanınca sonraki kontrol dener.
                    _ozet_yaz(f"⏳ Sonuçlar ertelendi, API-Football günlük hakkı dolu: {e}")
                else:
                    _hata("Sonuçlar", e)
            except Exception as e:
                _hata("Sonuçlar", e)
            try:
                haftalik(ayar, _x_client(), gunler, simdi)
            except Exception as e:
                _hata("Haftalık özet", e)
        if args.komut == "hafta" and not haftalik(ayar, _x_client(), gunler, simdi, zorla=True):
            print("Haftalık özet paylaşılmadı (zaten var ya da yeterli oyun yok).")
        if args.komut == "nabiz" and kayit.bul(gunler, bugun) is None and _sabah_penceresi(simdi, ayar):
            # Sabah çalışması GitHub tarafından iptal edildi/atlandıysa nabız günün kuponunu hazırlar.
            _ozet_yaz("Sabah çalışması bulunamadı; nabız günün kuponunu hazırlıyor.")
            args.komut = "otomatik"
        if args.komut in ("otomatik", "tahmin"):
            kayitli = kayit.bul(gunler, bugun)
            onceki = None
            if args.komut == "otomatik" and kayitli is None:
                # Kayıt varsa zaten güvendeyiz; yalnızca kayıt hiç yoksa (kaybolmuş olabilir) hesaba bakılır.
                try:
                    onceki = zaten_paylasildi(_x_client(), bugun)
                except Exception as e:
                    _ozet_yaz(f"⚠️ Mükerrer paylaşım kontrolü yapılamadı ({e}); kayda güvenilerek devam ediliyor.")
            if onceki:
                _hata("Kupon", RuntimeError(f"bugünün kuponu X'te zaten var (tweet {onceki}) ama kayıtta yok; "
                                            "ikinci kez paylaşılmadı. Kayıt elle düzeltilmeli."))
            else:
                gun = tahmin(ayar, _api(ayar), _secici(), gunler, bugun, simdi) or kayit.bul(gunler, bugun)
                if gun and gun["secimler"] and ayar.otomatik_paylas:
                    if gun.get("tweet_id") or not ayar.onay_bekle:
                        yayinla(ayar, gun, _x_client(), gunler, simdi)  # yeni paylaşım ya da yarım floodu tamamlama
                    elif not gun.get("onay") and gun["sonuc"] is None:
                        onay.onay_iste(gun, gunler, ayar, simdi)
                        _ozet_yaz(f"Onay istendi; cevap yoksa {gun['onay']['son']} (UTC) otomatik paylaşılacak.")
        if args.komut == "onay_kontrol":
            try:
                onay.kontrol(ayar, onay.GitHub(), _x_client(), gunler, simdi, yayinla)
            except Exception as e:
                _hata("Onay kontrolü", e)
        if args.komut == "sonuc_yeniden":
            # Son sonuç paylaşımını (eski biçim: kupon altında yanıt) silip yeni biçimle (alıntı) tekrar paylaşır.
            g = next((g for g in sorted(gunler, key=lambda g: g["tarih"], reverse=True) if g.get("sonuc_tweet_idleri")), None)
            if not g:
                raise RuntimeError("Yeniden paylaşılacak sonuç yok.")
            x = _x_client()
            for tid in reversed(g["sonuc_tweet_idleri"]):
                if tid != "x-mukerrer":
                    x.sil(tid)
            g["sonuc_tweet_idleri"], g["sonuc_tweet_id"] = [], None
            sonuc(ayar, None, x, gunler, simdi)
        if args.komut == "onay_yenile":
            # Hata düzeltildikten sonra: bugünün kuponu güncel kodla yeniden hazırlanır, yeni önizleme gelir.
            gun = kayit.bul(gunler, bugun)
            if not gun or gun.get("tweet_id") or not gun["secimler"] or \
                    (gun.get("onay") or {}).get("durum") not in ("bekliyor", "durduruldu"):
                raise RuntimeError("Yenilenecek, paylaşılmamış bir onay isteği yok.")
            for s in gun["secimler"]:
                for b in s.get("bacaklar") or [s]:
                    b["etiket"], b["kisa"] = etiketler(b["pazar"], s["ev"], s["dep"])
            onay.onizlemeleri_sil(gun["id"])
            onay.onay_iste(gun, gunler, ayar, simdi)
        if args.komut == "onay_testi":
            kaynak = kayit.bul(gunler, bugun) if kayit.kuponlar(kayit.bul(gunler, bugun) or {}) else None
            kaynak = kaynak or next((g for g in reversed(gunler) if kayit.kuponlar(g)), None)
            if not kaynak:
                raise RuntimeError("Önizleme testi için kuponlu bir gün yok.")
            ornek = copy.deepcopy(kaynak)
            ornek.update(id="test", onay={"durum": "test", "son": simdi.isoformat(timespec="seconds")})
            onay.istek_hazirla(ornek, gunler, ayar, simdi, test=True)
        if args.komut == "yenile":
            try:
                if not yenile(ayar, _api(ayar), _secici(), _x_client(), gunler, bugun, simdi):
                    print("Bugün için yeni kupon paylaşılmadı (maç başlamış, hata ya da kurallara uyan oyun yok).")
            except Exception as e:
                _hata("Yenile", e)
        if args.komut == "duzelt":
            gun = kayit.bul(gunler, bugun)
            if not gun or not duzelt(ayar, gun, _x_client(), gunler, simdi):
                print("Düzeltilecek bugünkü paylaşım yok.")
        if args.komut == "yayinla":
            gun = kayit.bul(gunler, bugun)
            if not gun or not yayinla(ayar, gun, _x_client(), gunler, simdi):
                print("Yayınlanacak bugünkü taslak yok.")
    finally:
        # Tweet atıldıktan sonra hata olsa bile kimlikler kaydedilir; tekrar paylaşım olmaz.
        kayit.kaydet(config.DATA_FILE, gunler)
        panel.olustur(gunler, config.PANEL_FILE, ayar)
    return 1 if HATALAR else 0


if __name__ == "__main__":
    sys.exit(main())
