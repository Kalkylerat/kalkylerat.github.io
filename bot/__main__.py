"""Kullanım: python -m bot [otomatik|nabiz|tani|likely|flood|...] (komut listesi main() içinde)"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import analiz, config, denetci, direktor, etkilesim, flood, flood_ig, flood_yetki, football, gorsel, kayit, kit, likely, likely_gorsel, likely_yetki, oddsapi, onay, panel, saglik, temizlik, tweets, yorum, firsat

# Çalışma sırasında yakalanan hatalar: alarm issue'suna yazılır (SÖZLEŞME C2). Alarm iletilemediyse iş "başarısız"
# işaretlenir; iletildiyse işaretlenmez: GitHub'ın "Run failed" e-postası ve nöbetçi alarmı aynı hatayı tekrarlamasın.
HATALAR: list[str] = []


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


def _lig_adi(m: dict, ayar) -> str:
    """Sponsor adında bahis sitesi geçen ligler görselde/tweette ülke adıyla gösterilir."""
    yasakli = [b.lower() for b in ayar.oran_bahiscileri + [ayar.keskin_bahisci]] + ["bet", "casino"]
    if any(y in m["lig"].lower() for y in yasakli):
        return f'{m.get("ulke") or "League"} league'
    return m["lig"]


def _sabah_penceresi(simdi: datetime, ayar) -> bool:
    """Planlı sabah çalışmasından (her gün 07:17 yerel) 20 dk sonra ile akşam 21:00 arası: sabah çalışması atlandıysa
    nabız günün analizini hazırlar (erken maçlar kaçmasın diye analiz sabah erken; geç kalırsa yine de yapılır)."""
    yerel = simdi.astimezone(ZoneInfo(ayar.saat_dilimi))
    dk = yerel.hour * 60 + yerel.minute
    return config.SABAH_YEREL_DK + 20 <= dk <= 21 * 60


ANALIZ_ISTATISTIK_MAX = 300  # analiz günü en fazla bu kadar istatistik isteği (Pro: günde 7.500 hak)


def analiz_gunu(ayar, gunler: list[dict], bugun: str, simdi: datetime, api=None) -> dict | None:
    """Analiz konsepti: kupon yok. Günün bütün maçları analiz edilir (data/analiz/<tarih>.json); öne çıkan maçların
    kartları gün içinde X'te paylaşılır (etkilesim). Takım istatistiği yalnızca oranı olmayan maçlar için istenir."""
    if kayit.bul(gunler, bugun):
        print(f"{bugun} için kayıt zaten var.")
        return None
    api = api or _api(ayar)
    try:
        maclar = football.gunun_maclari(api, bugun, ayar.ligler, ayar.saat_dilimi, 30, 10_000, simdi, tum_ligler=True)
        oranlar = football.toplu_oranlar(api, bugun, ayar.saat_dilimi, ayar.max_oran_sayfasi)
    except football.ApiHatasi as e:
        if not os.environ.get("ODDS_API_KEY"):
            _hata("Analiz taraması", e)
            return None
        _ozet_yaz(f"⚠️ API-Football kullanılamadı ({e}); yedek kaynak The Odds API.")
        maclar, oranlar = oddsapi.tara(oddsapi.OddsApi(config.env("ODDS_API_KEY")), bugun, ayar, simdi, yaz=_ozet_yaz)
    # Her maç için takım istatistiği de istenir (maç başına 1 istek): piyasayla karşılaştırma ve oranı olmayan
    # maçların analizi için. Hak biterse kalan maçlar yalnızca piyasayla analiz edilir.
    analizler, istatistik_hakki = [], ANALIZ_ISTATISTIK_MAX
    for m in maclar:
        ist = None
        if istatistik_hakki > 0 and "odds_id" not in m:
            istatistik_hakki -= 1
            try:
                ist = football.istatistik_al(api, m["fixture_id"])
            except football.ApiHatasi as e:
                print(f"İstatistik alınamadı: {e}")
                istatistik_hakki = 0
        a = analiz.mac_analizi(m, oranlar.get(m["fixture_id"]), ist, ayar)
        if a:
            a["lig"] = _lig_adi(m, ayar)
            analizler.append(a)
    klasor = config.DATA_FILE.parent / "analiz"
    klasor.mkdir(parents=True, exist_ok=True)
    (klasor / f"{bugun}.json").write_text(json.dumps(analizler, ensure_ascii=False) + "\n", encoding="utf-8")
    one = analiz.one_cikanlar(analizler, ayar.ligler)
    buyuk = [a for a in analizler if (analiz.onemli(a) or a.get("lig_id") in ayar.ligler) and a["guven"] != "dusuk"
             and datetime.fromisoformat(a["baslama"]) > simdi]
    gun = {"yogun": len(buyuk) >= config.YOGUN_MAC_ESIGI,  # maç çoksa hafta içi de yoğun gün temposu (B4)
           "id": bugun, "tarih": bugun, "olusturma": simdi.isoformat(timespec="seconds"),
           "konsept": "analiz", "taranan": len(maclar),
           "analiz_sayisi": len(analizler), "vitrin": etkilesim.vitrin(maclar, oranlar, ayar, simdi),
           "analizler": one,
           "tablo": [analiz.ozet(a) for a in analiz.tablo_secimi(  # günün büyük maçları tabloda (kartı olsa da)
               analizler, ayar.ligler, en_erken=(simdi + timedelta(minutes=90)).isoformat())],
           "ayrisma": [analiz.ozet(a) for a in analiz.ayrisma_secimi(analizler)],
           "kiyas": [analiz.ozet(a) for a in analiz.kiyas_secimi(  # ikinci tablo: oran ve istatistik yan yana
               analizler, ayar.ligler, en_erken=(simdi + timedelta(hours=2)).isoformat())]}
    gunler.append(gun)
    guven = {g: sum(a["guven"] == g for a in analizler) for g in ("yuksek", "orta", "dusuk")}
    ayrisan = [a for a in analizler if analiz.dikkat_cekici(a)]
    if ayrisan:
        _ozet_yaz("İstatistiğin piyasadan ayrıştığı maçlar: " + "; ".join(
            f'{a["ev"]} v {a["dep"]} {c["ad"]} piyasa %{100 * c["piyasa"]:.0f} / istatistik %{100 * c["istatistik"]:.0f}'
            for a in ayrisan[:15] for c in [analiz.dikkat_cekici(a)]))
    _ozet_yaz(f"### {bugun}: {len(maclar)} maç tarandı, {len(analizler)} maç analiz edildi "
              f"(güven yüksek {guven['yuksek']}, orta {guven['orta']}, düşük {guven['dusuk']}).\n"
              "Öne çıkanlar: " + ", ".join(f'{a["ev"]} v {a["dep"]} ({a["lig"]})' for a in gun["analizler"]))
    if os.environ.get("GH_TOKEN"):
        try:  # Mr. Likely (ikinci hesap): aynı taramadan günün adayları ve kuponlar; bilgi issue olarak gider
            if "odds_id" not in (maclar[0] if maclar else {}):
                _likely_buyuk_oranlar(api, analizler, oranlar)
            likely.sabah(ayar, analizler, oranlar, simdi, onay.GitHub(), yaz=_ozet_yaz)
        except Exception as e:
            _hata("Mr. Likely paketi", e)
    return gun


def liste_simdi(ayar, gunler: list[dict], bugun: str, simdi: datetime, x) -> str | None:
    """Elle: günün kalan önemli maçlarının listesini (analiz tablosu, bütün maç etiketleriyle) şimdi paylaşır.
    Kartı olan maçlar da girer; ayrı etkileşim kaydı (tablo_N) olarak saklanır. Altına henüz sonuç gelmemiş otomatik
    sabah tablosu ve önceki elle liste silinir (yanlış seçilmiş tablo düzeltilir)."""
    gun = kayit.bul(gunler, bugun)
    dosya = config.DATA_FILE.parent / "analiz" / f"{bugun}.json"
    if not gun or not dosya.exists():
        raise RuntimeError("Bugünün analizi yok; önce sabah taraması.")
    tum = json.loads(dosya.read_text(encoding="utf-8"))
    liste = analiz.tablo_secimi(tum, ayar.ligler, en_erken=(simdi + timedelta(minutes=15)).isoformat(), lig_basina=4)
    if len(liste) < 3:
        raise RuntimeError("Listeye girecek kadar maç kalmadı.")
    # Elle istenen liste editör onaylı şablonla gider (direktör yeniden yazmaz). Bugünün önceki elle listesi silinir.
    metin = etkilesim.tablo_tweeti(gun, liste, ayar)
    png = gorsel.analiz_tablosu(liste, bugun, [etkilesim._saat(a, ayar) for a in liste], "en")
    hata = denetci.analiz_kontrolu("tablo", metin, liste, ayar, png)
    if hata:
        raise RuntimeError("Denetçi listeyi durdurdu: " + " ".join(hata))
    durum = gun.setdefault("etkilesim", {})
    for k, e in list(durum.items()):  # önceki elle liste ve henüz sonucu gelmemiş otomatik sabah tablosu yerine geçer
        if e.get("durum") == "paylasildi" and e.get("tweet_id") and (
                (k.startswith("tablo_") and e.get("elle")) or (k == "tablo" and not e.get("sonuclar"))):
            x.sil(e["tweet_id"])
            durum[k] = {**e, "durum": "silindi"}
    tid = x.gonder(metin, medya=[x.medya_yukle(png)])
    anahtar = next(f"tablo_{n}" for n in range(2, 99) if f"tablo_{n}" not in durum)
    durum[anahtar] = {"durum": "paylasildi", "tweet_id": tid, "zaman": simdi.isoformat(timespec="seconds"), "elle": True,
                      "maclar": [a["fixture_id"] for a in liste]}
    _ozet_yaz(f"Liste paylaşıldı ({anahtar}): https://x.com/kalkylerat/status/{tid}\n```\n{metin}\n```")
    return tid


def kiyas_simdi(ayar, gunler: list[dict], bugun: str, simdi: datetime, x) -> str | None:
    """Elle: ikinci tabloyu (oran ve takım istatistiği yan yana, istatistiği olan büyük maçlar) şimdi paylaşır.
    Bugünün önceki elle kıyas postu silinir; ayrı kayıt (ayrisma_N, elle) olarak saklanır."""
    gun = kayit.bul(gunler, bugun)
    dosya = config.DATA_FILE.parent / "analiz" / f"{bugun}.json"
    if not gun or not dosya.exists():
        raise RuntimeError("Bugünün analizi yok; önce sabah taraması.")
    tum = json.loads(dosya.read_text(encoding="utf-8"))
    kiyas = analiz.kiyas_secimi(tum, ayar.ligler, en_erken=(simdi + timedelta(minutes=15)).isoformat())
    if len(kiyas) < 3:
        raise RuntimeError("İstatistiği olan yeterli maç kalmadı.")
    gecici = {**gun, "kiyas": kiyas}
    metin = etkilesim.ayrisma_tweeti(gecici, ayar, simdi)
    if not metin:
        raise RuntimeError("Kıyas metni oluşturulamadı.")
    png = gorsel.kiyas_tablosu(kiyas, bugun, [etkilesim._saat(a, ayar) for a in kiyas], "en")
    hata = denetci.analiz_kontrolu("ayrisma", metin, kiyas, ayar, png)
    if hata:
        raise RuntimeError("Denetçi kıyas postunu durdurdu: " + " ".join(hata))
    durum = gun.setdefault("etkilesim", {})
    for k, e in list(durum.items()):
        if k.startswith("ayrisma_") and e.get("elle") and e.get("durum") == "paylasildi":
            x.sil(e["tweet_id"])
            durum[k] = {**e, "durum": "silindi"}
    tid = x.gonder(metin, medya=[x.medya_yukle(png)])
    anahtar = next(f"ayrisma_{n}" for n in range(2, 99) if f"ayrisma_{n}" not in durum)
    durum[anahtar] = {"durum": "paylasildi", "tweet_id": tid, "zaman": simdi.isoformat(timespec="seconds"), "elle": True}
    _ozet_yaz(f"Kıyas tablosu paylaşıldı ({anahtar}): https://x.com/kalkylerat/status/{tid}\n```\n{metin}\n```")
    return tid


def takip_yenile(ayar, gunler: list[dict], simdi: datetime, x) -> int:
    """Elle: son iki günün yayındaki maç sonu alıntılarını siler ve yeni biçimle (olanın maç öncesi yüzdesi, seçim
    dili yok) hemen yeniden paylaşır."""
    yenilenen = 0
    for g in gunler[-2:]:
        for tur, e in (g.get("etkilesim") or {}).items():
            t = e.get("takip") or {}
            if tur.startswith("analiz_") and t.get("durum") == "paylasildi":
                x.sil(t["tweet_id"])
                e["eski_takip"] = t
                del e["takip"]
                yenilenen += 1
        etkilesim.analiz_takibi(g, ayar, x, simdi, lambda m: _mac_sonuclari(ayar, m), yaz=_ozet_yaz,
                                yazar=_direktor_yazar(ayar))
    _ozet_yaz(f"Maç sonu alıntıları yenilendi: {yenilenen} silindi, yeni biçimle yeniden paylaşıldı.")
    return yenilenen


def analiz_secimlerini_tamamla(ayar, gun: dict | None) -> None:
    """Eski sürümün oluşturduğu analiz gününe tablo ve ayrışma seçimlerini ekler; henüz kart paylaşılmadıysa
    öne çıkan maç sayısını da günceller (aynı post iki kez çıkmaz)."""
    if not gun or gun.get("konsept") != "analiz" or "tablo" in gun:
        return
    dosya = config.DATA_FILE.parent / "analiz" / f'{gun["tarih"]}.json'
    if not dosya.exists():
        return
    tum = json.loads(dosya.read_text(encoding="utf-8"))
    if not any(t.startswith("analiz_") for t in gun.get("etkilesim") or {}):
        gun["analizler"] = analiz.one_cikanlar(tum, ayar.ligler)
    gun["tablo"] = [analiz.ozet(a) for a in analiz.tablo_secimi(
        tum, ayar.ligler, en_erken=(kayit.simdi_utc() + timedelta(minutes=90)).isoformat())]
    gun["ayrisma"] = [analiz.ozet(a) for a in analiz.ayrisma_secimi(tum)]
    gun["kiyas"] = [analiz.ozet(a) for a in analiz.kiyas_secimi(
        tum, ayar.ligler, en_erken=(kayit.simdi_utc() + timedelta(hours=2)).isoformat())]


def _mac_sonuclari(ayar, maclar: list[dict]) -> dict:
    """Kupon dışı maçların sonucu, maçın geldiği kaynaktan (The Odds API ya da API-Football)."""
    istekler: dict[str, list[str]] = {}
    for m in maclar:
        if m.get("odds_id"):
            istekler.setdefault(m["odds_spor"], []).append(m["odds_id"])
    sonuc = oddsapi.sonuclari_al(oddsapi.OddsApi(config.env("ODDS_API_KEY")), istekler) if istekler else {}
    af = [m["fixture_id"] for m in maclar if not m.get("odds_id")]
    if af:
        sonuc.update(football.sonuclari_al(_api(ayar), af))
    return sonuc


def _likely_sonuc_al(ayar):
    """Mr. Likely kuponlarının maç sonuçları (korner pazarı varsa korner sayısıyla), maçın geldiği kaynaktan."""
    def al(maclar: list[dict], korner_idleri: set[int]) -> dict:
        sonuc = _mac_sonuclari(ayar, [m for m in maclar if m.get("odds_id")])
        af = [m["fixture_id"] for m in maclar if not m.get("odds_id")]
        if af:
            sonuc.update(football.sonuclari_al(_api(ayar), af, korner_idleri))
        return sonuc
    return al


def _likely_yazici(ayar):
    """Mr. Likely metinlerini karakterin sesiyle yazar; Claude anahtarı yoksa şablon kullanılır."""
    if ayar.direktor_aktif and os.environ.get("ANTHROPIC_API_KEY"):
        return lambda sablon, zorunlu: likely.ses_yaz(ayar, sablon, zorunlu, yaz=_ozet_yaz)
    return None


def _likely_tazele(ayar, simdi: datetime) -> None:
    """Öğlen tazeleme (SOZLESME E6): sabah eksik kalan kuponlar güncel oranlarla, aynı kurallarla tamamlanır.
    Günde bir kez: toplu oran sayfaları + oranı eksik büyük maçlar (en fazla ~55 istek)."""
    bugun = simdi.astimezone(ZoneInfo(ayar.saat_dilimi)).date().isoformat()
    try:
        dosya = config.DATA_FILE.parent / "analiz" / f"{bugun}.json"
        analizler = json.loads(dosya.read_text(encoding="utf-8"))
        api = _api(ayar)
        oranlar = football.toplu_oranlar(api, bugun, ayar.saat_dilimi, ayar.max_oran_sayfasi)
        _likely_buyuk_oranlar(api, analizler, oranlar)
        sayim = Counter(len(b) for b in oranlar.values())
        _ozet_yaz("Mr. Likely öğlen tazeleme: maç başına bahisçi sayısı " + ", ".join(f"{n}: {m} maç" for n, m in sorted(sayim.items())))
        likely.ek_kupon(ayar, analizler, oranlar, simdi, onay.GitHub(), yaz=_ozet_yaz)
    except Exception as e:
        _hata("Mr. Likely öğlen tazeleme", e)


def _likely_buyuk_oranlar(api, analizler: list[dict], oranlar: dict, en_fazla: int = 25) -> int:
    """Toplu oran taramasında oranı gelmeyen BÜYÜK maçların oranını tek tek ister (maç başına 1 istek): Mr. Likely
    büyük maçları kaçırmasın. Eklenen maç sayısını döndürür."""
    def yetersiz(b: dict | None) -> bool:  # oran yok, bahisçi az ya da keskin bahisçi eksik: aday çıkmaz
        return not b or len(b) < 4 or not any(ad.lower() == config.yukle().keskin_bahisci.lower() for ad in b)
    eksik = [a for a in analizler if analiz.onemli(a) and yetersiz(oranlar.get(a["fixture_id"])) and "odds_id" not in a][:en_fazla]
    eklenen = 0
    for a in eksik:
        try:
            b = football.oranlari_al(api, a["fixture_id"])
        except football.ApiHatasi as e:
            print(f"Büyük maç oranı alınamadı ({a['ev']} v {a['dep']}): {e}")
            break
        if len(b) > len(oranlar.get(a["fixture_id"]) or {}):
            oranlar[a["fixture_id"]] = b
            eklenen += 1
    if eksik:
        _ozet_yaz(f"Mr. Likely: toplu taramada oranı eksik {len(eksik)} büyük maçtan {eklenen} tanesinin oranı tek tek alındı.")
    return eklenen


def _x_likely():
    """Mr. Likely hesabının X istemcisi. Önce hesabın mevcut uygulamaya verdiği izin (data/likely_x.enc, şifreli);
    yoksa ayrı uygulama anahtarları (X_LIKELY_*). İkisi de yoksa None."""
    if os.environ.get("X_API_SECRET"):
        kayit_ = likely_yetki.anahtarlar(os.environ["X_API_SECRET"])
        if kayit_:
            return tweets.XClient(config.env("X_API_KEY"), config.env("X_API_SECRET"), kayit_["token"], kayit_["secret"])
    if os.environ.get("X_LIKELY_ACCESS_TOKEN"):
        return tweets.XClient(config.env("X_LIKELY_API_KEY"), config.env("X_LIKELY_API_SECRET"),
                              config.env("X_LIKELY_ACCESS_TOKEN"), config.env("X_LIKELY_ACCESS_SECRET"))
    return None


def likely_yetki_komutu(ayar) -> None:
    """Mr. Likely hesabının uygulamaya paylaşım izni: "ek" boşsa izin bağlantısı issue olarak gelir; "ek" alanına
    dönülen adres yapıştırılırsa izin tamamlanır ve anahtar şifreli kaydedilir (loglara anahtar yazılmaz)."""
    gh = onay.GitHub()
    parca = likely_yetki.coz(os.environ.get("BOT_EK", ""))
    try:
        if parca:
            hesap = likely_yetki.tamamla(config.env("X_API_KEY"), config.env("X_API_SECRET"), *parca)
            mesaj = (f"✅ Mr. Likely paylaşım izni tamam: @{hesap}. Anahtar depoda şifreli duruyor; bot bundan sonra bu hesapta "
                     "paylaşabilir. Hesapta \"Automated\" etiketi açık olmalı.")
            gh.issue_ac("🎩 Mr. Likely: paylaşım izni tamam", (f"@{ayar.alarm_kime} " if ayar.alarm_kime else "") + mesaj, likely.ETIKET)
        else:
            url = likely_yetki.baslat(config.env("X_API_KEY"), config.env("X_API_SECRET"))
            mesaj = ("Mr. Likely hesabının paylaşım izni için:\n\n1. Tarayıcıda X'e **Mr. Likely hesabıyla** giriş yapmış ol.\n"
                     f"2. Şu bağlantıyı aç ve **Authorize app**'e bas: {url}\n"
                     "3. Sayfa github.com'a döner; adres çubuğundaki adresin tamamını kopyalayıp Claude'a gönder.\n\n"
                     "Bağlantı birkaç dakika geçerlidir.")
            gh.issue_ac("🎩 Mr. Likely: paylaşım izni bağlantısı", (f"@{ayar.alarm_kime} " if ayar.alarm_kime else "") + mesaj, likely.ETIKET)
        _ozet_yaz(mesaj)
    except Exception as e:
        _hata("Mr. Likely paylaşım izni", e)


def flood_yetki_komutu(ayar) -> None:
    """Tiny Fixes hesabının uygulamaya paylaşım izni: "ek" boşsa izin bağlantısı issue olarak gelir; "ek" alanına
    dönülen adres yapıştırılırsa izin tamamlanır ve anahtar şifreli kaydedilir (loglara anahtar yazılmaz)."""
    gh = onay.GitHub()
    parca = flood_yetki.coz(os.environ.get("BOT_EK", ""))
    kime = f"@{ayar.alarm_kime} " if ayar.alarm_kime else ""
    try:
        if parca:
            hesap = flood_yetki.tamamla(config.env("X_API_KEY"), config.env("X_API_SECRET"), *parca)
            mesaj = (f"✅ Tiny Fixes X paylaşım izni tamam: @{hesap}. Anahtar depoda şifreli duruyor. Hesapta \"Automated\" "
                     "etiketi açık olmalı. Paylaşım için ayarlar.toml → [flood] mod = \"onay\" yapın.")
        else:
            url = flood_yetki.baslat(config.env("X_API_KEY"), config.env("X_API_SECRET"))
            mesaj = ("Tiny Fixes X hesabının paylaşım izni için:\n\n1. Tarayıcıda X'e **Tiny Fixes hesabıyla** giriş yapmış ol.\n"
                     f"2. Şu bağlantıyı aç ve **Authorize app**'e bas: {url}\n"
                     "3. Sayfa github.com'a döner; adres çubuğundaki adresin tamamını kopyalayıp Claude'a gönder.\n\n"
                     "Bağlantı birkaç dakika geçerlidir.")
        gh.issue_ac("🧪 Tiny Fixes: X paylaşım izni", kime + mesaj, flood.ETIKET)
        _ozet_yaz(mesaj)
    except Exception as e:
        _hata("Tiny Fixes X izni", e)


def flood_ig_komutu(ayar) -> None:
    """Instagram anahtarını doğrular (hesap adı, hesap türü) ve şifreli kaydeder. Anahtar: IG_FLOOD_TOKEN, kimlik: IG_FLOOD_ID."""
    gh = onay.GitHub()
    kime = f"@{ayar.alarm_kime} " if ayar.alarm_kime else ""
    try:
        token, ig_id = config.env("IG_FLOOD_TOKEN"), config.env("IG_FLOOD_ID")
        ben = flood_ig.InstagramClient(token, ig_id, surum=flood.ayar_yukle().ig_surum).ben()
        if str(ben.get("account_type", "")).upper() not in ("BUSINESS", "MEDIA_CREATOR", "CREATOR"):
            raise RuntimeError(f"Hesap türü {ben.get('account_type')}: Instagram'da Business ya da Creator hesabı gerekir.")
        flood_yetki.kaydet_ig(config.env("X_API_SECRET"), token, ig_id, kayit.simdi_utc())
        mesaj = (f"✅ Tiny Fixes Instagram bağlantısı tamam: @{ben.get('username')} ({ben.get('account_type')}). Anahtar "
                 "depoda şifreli duruyor, bot süresi dolmadan yeniler.")
        gh.issue_ac("🧪 Tiny Fixes: Instagram bağlantısı", kime + mesaj, flood.ETIKET)
        _ozet_yaz(mesaj)
    except Exception as e:
        _hata("Tiny Fixes Instagram bağlantısı", e)


def flood_tani_komutu(ayar) -> None:
    """Tiny Fixes salt okunur tanı: konu kaynakları ve puanlama canlı; Claude/X/Instagram'a dokunmaz. Sonuç issue olarak gelir."""
    try:
        metin = flood.tani(yaz=_ozet_yaz)
        if os.environ.get("GH_TOKEN"):
            kime = f"@{ayar.alarm_kime} " if ayar.alarm_kime else ""
            onay.GitHub().issue_ac("🩹 Tiny Fixes tanı", kime + metin, flood.TANI_ETIKETI)
    except Exception as e:
        _hata("Tiny Fixes tanı", e)


def flood_paket_komutu(ayar) -> None:
    """Tiny Fixes paketleri (SOZLESME F13): eksik paket temalarını gerçekten dener (tema başına ~$0.04, bir kez),
    ücretsiz başlangıç paketini ve ücretli kütüphaneyi PDF olarak `urun/` klasörüne yazar (depoya girmez; iş akışı
    1 günlük çıktı olarak saklar), sitedeki ürün özetini günceller. "ek" alanı: en fazla kaç yeni tema (varsayılan hepsi)."""
    from . import flood_gelir, flood_kutuphane, flood_pdf
    gh = onay.GitHub() if os.environ.get("GH_TOKEN") else None
    kime = f"@{ayar.alarm_kime} " if ayar.alarm_kime else ""
    try:
        secret = config.env("X_API_SECRET")
        import anthropic
        simdi = kayit.simdi_utc()
        once = len(flood_kutuphane.paket_yukle(secret))
        ek = os.environ.get("BOT_EK", "").strip()
        girdiler = flood_kutuphane.paket_uret(anthropic.Anthropic(), flood.ayar_yukle(), secret, simdi,
                                              int(ek) if ek.isdigit() else len(flood_kutuphane.PAKET_TEMALARI), _ozet_yaz)
        denenen = len(girdiler) - once
        paket = flood_kutuphane.paket_girdileri(girdiler)
        g = flood_gelir.ayar_yukle()
        if len(paket) < g.ucretsiz_paket_sayisi:
            raise RuntimeError(f"Pakete girebilen denenmiş komut {len(paket)}, en az {g.ucretsiz_paket_sayisi} gerekli.")
        klasor = config.ROOT / "urun"
        klasor.mkdir(exist_ok=True)
        ucretsiz = flood_kutuphane.ucretsiz_sec(paket, g.ucretsiz_paket_sayisi)
        (klasor / "tiny_fixes_starter.pdf").write_bytes(flood_pdf.paket(ucretsiz, "Tiny Fixes Starter",
                                                         f"{len(ucretsiz)} tested AI prompts for everyday problems"))
        (klasor / "tiny_fixes_library.pdf").write_bytes(flood_pdf.paket(paket, g.urun_adi,
                                                         f"{len(paket)} tested AI prompts for work, study and home"))
        flood_kutuphane.ozet_yaz(flood_kutuphane.ozet(paket, simdi))
        flood.site_guncelle(_ozet_yaz)
        calisma = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
        mesaj = (f"📦 Tiny Fixes paketleri hazır: ücretsiz {len(ucretsiz)} komut, ücretli {len(paket)} komut. Bu çalışmada "
                 f"{denenen} tema denendi (tahmini ~${denenen * flood_kutuphane.TEMA_MALIYETI:.2f}).\n\n"
                 f"1. Bu çalışmanın sayfasını aç: {calisma} → en altta **Artifacts → tiny-fixes-paketler** (24 saat durur).\n"
                 "2. `tiny_fixes_starter.pdf` → Kit'te formun teşekkür (incentive) e-postasına dosya olarak ekle.\n"
                 f"3. `tiny_fixes_library.pdf` → Lemon Squeezy'de ürünün dosyası ({g.urun_fiyat}).\n"
                 "Dosyaları başka yerde herkese açık paylaşma: depo herkese açık olduğu için pakete depoda düz metin olarak yer yok (F13).")
        if gh:
            gh.issue_ac("📦 Tiny Fixes paketleri hazır", kime + mesaj, flood.ETIKET)
        _ozet_yaz(mesaj)
    except Exception as e:
        _hata("Tiny Fixes paketi", e)


def flood_site_komutu(ayar) -> None:
    """Tiny Fixes sitesini yeniden yazar (ücretsiz, ağ yok)."""
    try:
        degisen = flood.site_guncelle(_ozet_yaz)
        _ozet_yaz(f"Tiny Fixes sitesi: {len(degisen)} dosya güncellendi.")
    except Exception as e:
        _hata("Tiny Fixes sitesi", e)


def flood_nabiz(ayar, simdi: datetime) -> None:
    """Tiny Fixes (SOZLESME F): kapalı modda hiçbir şey yapmaz. Bir hata diğer hesapları etkilemez."""
    try:
        flood.nabiz(ayar, simdi, yaz=_ozet_yaz)
    except Exception as e:
        _hata("Tiny Fixes", e)


def likely_nabiz(ayar, simdi: datetime, sonuclar: bool = True) -> None:
    """Mr. Likely: sahibinin issue yorumlarındaki seçimler ve (nabızda) biten kuponların sonuçları. X'e paylaşım yok."""
    if not os.environ.get("GH_TOKEN") or not likely.ayar_yukle().aktif:
        return
    gh = onay.GitHub()
    try:
        likely.kontrol(ayar, gh, simdi, yazici=_likely_yazici(ayar), yaz=_ozet_yaz)
    except Exception as e:
        _hata("Mr. Likely seçim kontrolü", e)
    if not sonuclar:
        return
    try:
        likely.sonuclar(ayar, _likely_sonuc_al(ayar), gh, simdi, yazici=_likely_yazici(ayar), yaz=_ozet_yaz)
        likely.eskileri_kapat(gh, simdi)
    except Exception as e:
        _hata("Mr. Likely sonuçları", e)
    if os.environ.get("API_FOOTBALL_KEY"):
        try:  # ölçüm (gölge test): havuzun bütün ayaklarının sonucu, toplu istekle; paylaşım yok
            likely.olcum_guncelle(lambda idler: football.toplu_sonuclar(_api(ayar), idler), simdi, yaz=_ozet_yaz)
        except Exception as e:  # ölçüm paylaşımı etkilemez: bir sonraki turda yeniden denenir
            _ozet_yaz(f"Mr. Likely ölçümü bu turda yapılamadı ({e}).")
    if likely.ayar_yukle().mod != "otomatik":
        return
    if os.environ.get("API_FOOTBALL_KEY") and likely.tazeleme_zamani(ayar, simdi):
        _likely_tazele(ayar, simdi)
    # Otomatik mod: Mr. Likely hesabında kupon postu, sonuç yanıtı ve günün dersi (SOZLESME E1). Anahtarlar yoksa beklenir.
    x = _x_likely()
    if x is None:
        print("Mr. Likely otomatik modda ama hesap henüz paylaşım izni vermemiş; paylaşım yapılmadı.")
        return
    for ad, adim in (("kupon paylaşımı", lambda: likely.oto_paylas(ayar, x, simdi, yazici=_likely_yazici(ayar),
                                                                     kart=likely_gorsel.kupon_karti, yaz=_ozet_yaz)),
                     ("sonuç paylaşımı", lambda: likely.oto_sonuc_paylas(ayar, x, simdi, kart=likely_gorsel.sonuc_karti, yaz=_ozet_yaz)),
                     ("bilgi postu", lambda: likely.oto_bilgi(ayar, x, simdi, yaz=_ozet_yaz))):
        try:
            adim()
        except Exception as e:
            _hata(f"Mr. Likely {ad}", e)


def _api(ayar):
    return football.ApiFootball(config.env("API_FOOTBALL_KEY"), aralik=ayar.istek_araligi_sn)


def _x_client():
    return tweets.XClient(config.env("X_API_KEY"), config.env("X_API_SECRET"),
                          config.env("X_ACCESS_TOKEN"), config.env("X_ACCESS_SECRET"))


def _direktor_yazar(ayar):
    """X Direktörü açıksa ve Claude anahtarı varsa metin yazıcı; yoksa None (şablonlar kullanılır)."""
    if ayar.direktor_aktif and os.environ.get("ANTHROPIC_API_KEY"):
        return direktor.yazar(ayar, yaz=_ozet_yaz)
    return None


def tani(ayar) -> None:
    """Tweet atmadan tüm bağlantıları ve veri kapsamını kontrol eder."""
    import anthropic
    satirlar = ["### Tanı"]
    api = _api(ayar)
    try:
        ham_durum = api.session.get(f"{football.BASE_URL}/status", timeout=30).json()
        durum = ham_durum.get("response") or {}
        durum = durum if isinstance(durum, dict) else {}
        plan = (durum.get("subscription") or {}).get("plan")
        istek = durum.get("requests") or {}
        # Depo herkese açık (loglar da): e-posta maskelenir, hangi hesap olduğu anlaşılacak kadar gösterilir.
        eposta = (durum.get("account") or {}).get("email") or ""
        maskeli = f"{eposta[:2]}***@{eposta.split('@')[-1]}" if "@" in eposta else "-"
        satirlar.append(f"- API-Football: hesap {maskeli}, plan **{plan}**, bugün {istek.get('current')}/"
                        f"{istek.get('limit_day')} istek, hatalar: {ham_durum.get('errors') or '-'}")
        _ozet_yaz(satirlar[-1])
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
        populer = Counter(f'{f["league"]["name"]} ({f["league"]["country"]}, id {f["league"]["id"]})' for f in tum).most_common(6)
        satirlar.append(f"  - {tarih} en çok maçı olan ligler: {populer}")
        satirlar.append(f"- {tarih} ham yanıt: tüm dünyada {len(tum)} maç, sezonlar {sezonlar[:5]}, "
                        f"izlenen liglerde {len(izlenen)} (durumlar: {sorted({f['fixture']['status']['short'] for f in izlenen})}), "
                        f"hatalar: {ham.get('errors') or '-'}")
        try:
            maclar = football.gunun_maclari(api, tarih, ayar.ligler, ayar.saat_dilimi, 0, 999, simdi)
        except football.ApiHatasi as e:
            satirlar.append(f"- {tarih}: maç listesi alınamadı: {e}")
            continue
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
    except Exception as e:
        satirlar.append(f"- X hatası: {e}")
    try:
        m = anthropic.Anthropic().models.retrieve(ayar.claude_model)
        satirlar.append(f"- Anthropic: model {m.id} erişilebilir")
    except Exception as e:
        satirlar.append(f"- Anthropic hatası: {e}")
    _ozet_yaz("\n".join(satirlar))


def odds_tani(ayar) -> None:
    """The Odds API: aktif futbol ligleri ve bugün (penceredeki) maç sayıları. Kredi harcamaz."""
    api = oddsapi.OddsApi(config.env("ODDS_API_KEY"))
    simdi = kayit.simdi_utc()
    bugun = simdi.astimezone(ZoneInfo(ayar.saat_dilimi)).date().isoformat()
    bas, son = oddsapi.gun_penceresi(bugun, ayar.saat_dilimi, 0, simdi)
    tum = [s for s in api.get("sports", all="true") if s.get("group") == "Soccer"]
    aktif = oddsapi.futbol_sporlari(api)
    satirlar = []
    for spor in aktif:
        e = api.get(f'sports/{spor["key"]}/events', commenceTimeFrom=oddsapi._zaman(bas), commenceTimeTo=oddsapi._zaman(son))
        if e:
            saatler = sorted(x["commence_time"][11:16] for x in e)
            satirlar.append(f'- {spor["key"]} ({spor.get("title")}): {len(e)} maç, {saatler[0]}–{saatler[-1]} UTC')
    _ozet_yaz(f"The Odds API: {len(tum)} futbol ligi tanımlı, {len(aktif)} aktif; kalan kredi {api.kalan}.\n"
              f"Bugün {bas:%H:%M}–{son:%H:%M} UTC arası maçı olan ligler:\n" + ("\n".join(satirlar) or "yok"))
    _ozet_yaz("Aktif ligler: " + ", ".join(s["key"] for s in aktif))


def odds_pazar(ayar, en_fazla: int = 3) -> None:
    """The Odds API: bugünkü ilk birkaç maçta hangi bahisçi hangi pazarı (korner, gol vb.) sunuyor. Maç başına 1 kredi."""
    api = oddsapi.OddsApi(config.env("ODDS_API_KEY"))
    simdi = kayit.simdi_utc()
    bugun = simdi.astimezone(ZoneInfo(ayar.saat_dilimi)).date().isoformat()
    bas, son = oddsapi.gun_penceresi(bugun, ayar.saat_dilimi, 0, simdi)
    satirlar, kalan = [], en_fazla
    for spor in oddsapi.futbol_sporlari(api):
        if kalan <= 0:
            break
        for e in api.get(f'sports/{spor["key"]}/events', commenceTimeFrom=oddsapi._zaman(bas),
                         commenceTimeTo=oddsapi._zaman(son))[:kalan]:
            veri = api.get(f'sports/{spor["key"]}/events/{e["id"]}/markets', regions=oddsapi.BOLGE)
            kalan -= 1
            tum = sorted({m["key"] for b in veri.get("bookmakers", []) for m in b.get("markets", [])})
            satirlar.append(f'#### {e["home_team"]} v {e["away_team"]} ({spor.get("title")})\nTüm pazarlar: {", ".join(tum) or "yok"}')
            for b in veri.get("bookmakers", []):
                satirlar.append(f'- {b.get("title") or b["key"]}: {", ".join(sorted(m["key"] for m in b.get("markets", [])))}')
    _ozet_yaz("\n".join(satirlar or ["Bugün maç yok."]) + f"\n\nHarcanan kredi {api.harcanan}, kalan {api.kalan}.")


def af_pazar(ayar, en_fazla: int = 8) -> None:
    """API-Football: yarının izinli lig maçlarında hangi bahis türü kaç bahisçide var (Pinnacle/Bet365 dahil mi)."""
    from collections import defaultdict
    api = _api(ayar)
    simdi = kayit.simdi_utc()
    yarin = (simdi.astimezone(ZoneInfo(ayar.saat_dilimi)) + timedelta(days=1)).date().isoformat()
    maclar = football.gunun_maclari(api, yarin, ayar.ligler, ayar.saat_dilimi, 0, 999, simdi)
    maclar = [m for m in maclar if m["lig_id"] in ayar.ligler][:en_fazla]
    turler: dict[str, dict] = defaultdict(lambda: {"mac": set(), "bahisci": set()})
    for m in maclar:
        for k in api.get("odds", fixture=m["fixture_id"]):
            for bm in k.get("bookmakers", []):
                for bet in bm.get("bets", []):
                    turler[bet["name"]]["mac"].add(m["fixture_id"])
                    turler[bet["name"]]["bahisci"].add(bm["name"])
    satirlar = [f"{len(maclar)} maç ({yarin}): " + ", ".join(f'{m["ev"]}–{m["dep"]}' for m in maclar)]
    for ad, v in sorted(turler.items(), key=lambda x: (-len(x[1]["mac"]), -len(x[1]["bahisci"]))):
        keskin = "P" if ayar.keskin_bahisci in v["bahisci"] else "-"
        b365 = "B" if "Bet365" in v["bahisci"] else "-"
        satirlar.append(f'- {ad}: {len(v["mac"])} maç, {len(v["bahisci"])} bahisçi [{keskin}{b365}]')
    _ozet_yaz("### API-Football bahis türleri\n" + "\n".join(satirlar))


def profil() -> None:
    """X profilini okur (paylaşım yok): kullanıcı adı, bio, sabit tweet, doğrulama."""
    r = _x_client().session.get("https://api.x.com/2/users/me", params={
        "user.fields": "description,pinned_tweet_id,verified,verified_type,public_metrics",
        "expansions": "pinned_tweet_id", "tweet.fields": "text"}, timeout=30)
    veri = r.json()
    u = veri.get("data", {})
    sabit = (veri.get("includes", {}).get("tweets") or [{}])[0]
    _ozet_yaz("\n".join([
        f"- Durum: {r.status_code}", f"- Kullanıcı: @{u.get('username')}",
        f"- Doğrulama: {u.get('verified')} / {u.get('verified_type')}",
        f"- Takipçi: {(u.get('public_metrics') or {}).get('followers_count')}",
        f"- Bio: {u.get('description')!r}",
        f"- Sabit tweet: {sabit.get('id', 'YOK')} {sabit.get('text', '')[:80]!r}",
        f"- Ham: {str(veri)[:300] if r.status_code >= 400 else '-'}"]))


def metrik() -> None:
    """Son postların görüntülenme ve etkileşim rakamları + takipçi sayısı: data/metrikler.json ve özet sayfası."""
    x = _x_client()
    u = x.session.get("https://api.x.com/2/users/me", params={"user.fields": "public_metrics"}, timeout=30).json()["data"]
    tweetler = x.metrikler(100)
    veri = {"zaman": kayit.simdi_utc().isoformat(timespec="seconds"), "hesap": u.get("public_metrics"),
            "tweetler": [{"id": t["id"], "zaman": t.get("created_at"), "metin": t.get("text", "")[:120],
                          **(t.get("public_metrics") or {})} for t in tweetler]}
    (config.DATA_FILE.parent / "metrikler.json").write_text(json.dumps(veri, ensure_ascii=False, indent=1) + "\n",
                                                            encoding="utf-8")
    goruntu = [t.get("impression_count", 0) for t in veri["tweetler"]]
    _ozet_yaz(f"### Metrikler\n- Hesap: {u.get('public_metrics')}\n- Son {len(goruntu)} post: toplam görüntülenme "
              f"{sum(goruntu)}, ortalama {sum(goruntu) / max(1, len(goruntu)):.1f}, en yüksek {max(goruntu, default=0)}")


def hesap_kontrol() -> None:
    """data/takip_adaylari.txt'deki X hesaplarının var olup olmadığını ve takipçi/post sayılarını kontrol eder
    (yalnızca okuma): data/takip_adaylari.json."""
    adlar = [s.strip().lstrip("@") for s in (config.DATA_FILE.parent / "takip_adaylari.txt").read_text().splitlines()
             if s.strip()]
    x = _x_client()
    bulunan, hatalar = [], []
    for i in range(0, len(adlar), 100):
        r = x.session.get("https://api.x.com/2/users/by", timeout=30, params={
            "usernames": ",".join(adlar[i:i + 100]),
            "user.fields": "public_metrics,description,verified,verified_type,created_at"})
        veri = r.json()
        bulunan += veri.get("data", [])
        hatalar += [h.get("value") or h.get("detail") for h in veri.get("errors", [])]
        if r.status_code >= 400:
            hatalar.append(f"HTTP {r.status_code}: {str(veri)[:200]}")
    (config.DATA_FILE.parent / "takip_adaylari.json").write_text(
        json.dumps({"bulunan": bulunan, "hatalar": hatalar}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    _ozet_yaz(f"### Hesap kontrolü\n- Bulunan: {len(bulunan)} / {len(adlar)}\n- Bulunamayan: {hatalar}")


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


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="bot")
    p.add_argument("komut", choices=["otomatik", "panel", "tani", "oran_testi", "onay_kontrol", "nabiz",
                                     "profil", "odds_tani", "odds_pazar", "vitrin", "af_pazar", "direktor", "temizle",
                                     "liste", "kiyas", "takip_yenile", "metrik", "hesap_kontrol", "likely",
                                     "likely_paket", "likely_yetki", "likely_ek", "likely_yenile", "likely_iptal",
                                     "flood", "flood_yetki", "flood_ig", "flood_tani", "flood_paket", "flood_site"])
    args = p.parse_args(argv)
    ayar = config.yukle()

    if args.komut == "tani":
        tani(ayar)
        return 0
    if args.komut == "profil":
        profil()
        return 0
    if args.komut == "likely_yetki":
        likely_yetki_komutu(ayar)
        return 1 if HATALAR else 0
    if args.komut == "flood_yetki":
        flood_yetki_komutu(ayar)
        return 1 if HATALAR else 0
    if args.komut == "flood_ig":
        flood_ig_komutu(ayar)
        return 1 if HATALAR else 0
    if args.komut == "flood_tani":
        flood_tani_komutu(ayar)
        return 1 if HATALAR else 0
    if args.komut == "flood_paket":
        flood_paket_komutu(ayar)
        return 1 if HATALAR else 0
    if args.komut == "flood_site":
        flood_site_komutu(ayar)
        return 1 if HATALAR else 0
    if args.komut == "odds_tani":
        odds_tani(ayar)
        return 0
    if args.komut == "odds_pazar":
        odds_pazar(ayar)
        return 0
    if args.komut == "af_pazar":
        af_pazar(ayar)
        return 0
    if args.komut == "oran_testi":
        oran_testi(ayar)
        return 0

    gunler = kayit.yukle(config.DATA_FILE)
    simdi = kayit.simdi_utc()
    bugun = simdi.astimezone(ZoneInfo(ayar.saat_dilimi)).date().isoformat()
    try:
        # Her adım ayrı: birinin hatası diğerlerini engellemez.
        if args.komut == "temizle":
            temizlik.baslat(simdi)
        if args.komut in ("temizle", "nabiz") and temizlik.durum().get("aktif"):
            try:
                temizlik.calistir(_x_client(), simdi, yaz=_ozet_yaz)
            except Exception as e:
                _hata("Temizlik", e)
        if args.komut == "nabiz" and kayit.bul(gunler, bugun):
            try:
                analiz_secimlerini_tamamla(ayar, kayit.bul(gunler, bugun))
                gun_ = kayit.bul(gunler, bugun)
                if "hafta_ozeti" not in gun_ and gun_.get("konsept") == "analiz" \
                        and datetime.fromisoformat(gun_["tarih"]).weekday() == 0:  # SÖZLEŞME A9: Pazartesi karnesi
                    gun_["hafta_ozeti"] = etkilesim.hafta_ozeti(gunler, gun_["tarih"])
                dosya = config.DATA_FILE.parent / "analiz" / f"{bugun}.json"
                if dosya.exists():  # akşam maçlarına da kart ve akşam tablosu (yoğun günde geniş; sakin günde B7)
                    eklenen = etkilesim.yogun_kartlari_ekle(kayit.bul(gunler, bugun),
                                                            json.loads(dosya.read_text(encoding="utf-8")), ayar, simdi)
                    if eklenen:
                        _ozet_yaz(f"{eklenen} maç daha kart listesine eklendi.")
                    if etkilesim.aksam_tablosu_ekle(kayit.bul(gunler, bugun), json.loads(dosya.read_text(encoding="utf-8")),
                                                    ayar, simdi):
                        _ozet_yaz("Akşam maçları tablosu hazırlandı.")
                    if etkilesim.gece_tablosu_ekle(kayit.bul(gunler, bugun), json.loads(dosya.read_text(encoding="utf-8")),
                                                   ayar, simdi):
                        _ozet_yaz("Gece maçları tablosu hazırlandı.")
                etkilesim.paylas(kayit.bul(gunler, bugun), ayar, _x_client(), simdi, yaz=_ozet_yaz,
                                 yazar=_direktor_yazar(ayar))
            except Exception as e:
                _hata("Etkileşim paylaşımı", e)
        if args.komut in ("nabiz", "otomatik") and os.environ.get("GH_TOKEN") and kayit.bul(gunler, bugun) \
                and simdi.hour >= 7 and not (firsat.ayar_yukle().aktif and firsat.ayar_yukle().gunluk_yorum > 0):
            # Yorum fırsatları açıkken eski yanıt kiti (arama bağlantıları) gönderilmez: fırsatlar postun kendisini getirir
            try:  # günlük yanıt kiti: sahibinin elle yanıtlaması için taslaklar (telefona bildirim)
                ham = f'https://raw.githubusercontent.com/{os.environ.get("GITHUB_REPOSITORY")}/{os.environ.get("GITHUB_REF_NAME")}'
                kit.gonder(kayit.bul(gunler, bugun), ayar, onay.GitHub(), lambda a: etkilesim._saat(a, ayar), simdi, ham,
                           yaz=_ozet_yaz)
            except Exception as e:
                _hata("Yanıt kiti", e)
        if args.komut == "nabiz" and os.environ.get("GH_TOKEN") and getattr(ayar, "yorum_kiti", True):
            # Yorum kiti (SÖZLEŞME D3): gelen yorumlara sahibine cevap taslakları; bot cevap atmaz
            claude = __import__("anthropic").Anthropic() if os.environ.get("ANTHROPIC_API_KEY") else None
            try:  # yorum fırsatları (büyüme ajanı): büyük hesapların postları + taslaklar; bot cevap atmaz
                if claude is not None:
                    firsat.kontrol(_x_client(), onay.GitHub(), ayar, kayit.bul(gunler, bugun), simdi, claude, yaz=_ozet_yaz)
            except Exception as e:
                _ozet_yaz(f"⚠️ Yorum fırsatları bu turda çalışmadı: {e}")
            try:  # Mr. Likely için de, kendi sesiyle; kupon ayağı olan maçta "kuponla" seçeneği
                x_l = _x_likely() if claude is not None and likely.ayar_yukle().aktif else None
                if x_l is not None:
                    lgun = next((g for g in likely.yukle()["gunler"] if g["tarih"] == bugun), None) or {}
                    kuponlar = [k for k in lgun.get("secilen", []) if k.get("tweet_id") and k.get("durum") == "bekliyor"
                                and min(datetime.fromisoformat(a["baslama"]) for a in k["ayaklar"]) > simdi]
                    firsat.kontrol(x_l, onay.GitHub(), ayar, kayit.bul(gunler, bugun), simdi, claude, yaz=_ozet_yaz,
                                   hesap="likely", kuponlar=kuponlar,
                                   kullanici=(yorum.yukle().get("likely") or {}).get("kullanici"))
            except Exception as e:
                _ozet_yaz(f"⚠️ Mr. Likely yorum fırsatları bu turda çalışmadı: {e}")
            for hesap, istemci in (("kalkylerat", _x_client), ("likely", _x_likely)):
                try:
                    x_ = istemci()
                    if x_ is not None:
                        yorum.kontrol(x_, onay.GitHub(), ayar, simdi, hesap=hesap, client=claude, yaz=_ozet_yaz,
                                     gun=kayit.bul(gunler, bugun))
                except Exception as e:  # okuma hatası paylaşımı etkilemez; sonraki kontrolde yeniden denenir
                    _ozet_yaz(f"⚠️ Yorum kiti ({hesap}) bu turda çalışmadı: {e}")
        if args.komut == "nabiz":
            for g in gunler[-2:]:  # günün tablosu: maçlar bitince skorlar ve olanların maç öncesi yüzdeleri (yanıt)
                try:
                    dosya = config.DATA_FILE.parent / "analiz" / f'{g["tarih"]}.json'
                    tum = json.loads(dosya.read_text(encoding="utf-8")) if dosya.exists() else []
                    etkilesim.tablo_takibi(g, ayar, _x_client(), simdi, lambda m: _mac_sonuclari(ayar, m), tum,
                                           yaz=_ozet_yaz)
                except Exception as e:
                    _hata("Tablo takibi", e)
        if args.komut == "nabiz":
            for g in gunler[-6:]:  # analiz kartı paylaşılan maçlar bitince: "ne dedik, ne oldu" (alıntı)
                try:
                    etkilesim.analiz_takibi(g, ayar, _x_client(), simdi, lambda m: _mac_sonuclari(ayar, m),
                                            yaz=_ozet_yaz, yazar=_direktor_yazar(ayar),
                                            xg_getir=lambda a: football.mac_xg(_api(ayar), a["fixture_id"], a["ev"]))
                except Exception as e:
                    _hata("Analiz takibi", e)
        yerel = simdi.astimezone(ZoneInfo(ayar.saat_dilimi))
        if (args.komut == "nabiz" and _direktor_yazar(ayar) and direktor.haftalik_gerekli(yerel)) or args.komut == "direktor":
            try:
                try:
                    tweetler = _x_client().metrikler()
                except Exception as e:
                    _ozet_yaz(f"⚠️ Tweet rakamları okunamadı ({e}); inceleme kupon rekoruyla yapılıyor.")
                    tweetler = []
                direktor.haftalik(ayar, gunler, tweetler, onay.GitHub(), yerel, yaz=_ozet_yaz)
            except Exception as e:
                _hata("X Direktörü haftalık inceleme", e)
        if args.komut == "liste":
            liste_simdi(ayar, gunler, bugun, simdi, _x_client())
        if args.komut == "kiyas":
            kiyas_simdi(ayar, gunler, bugun, simdi, _x_client())
        if args.komut == "metrik":
            metrik()
        if args.komut == "hesap_kontrol":
            hesap_kontrol()
        if args.komut == "takip_yenile":
            takip_yenile(ayar, gunler, simdi, _x_client())
        if args.komut == "vitrin":
            gun = kayit.bul(gunler, bugun)
            if not gun:
                raise RuntimeError("Bugünün kaydı yok; önce sabah taraması.")
            api = oddsapi.OddsApi(config.env("ODDS_API_KEY"))
            maclar, oranlar = oddsapi.tara(api, bugun, ayar, simdi, yaz=_ozet_yaz, ek=False)
            gun["taranan"] = len(maclar)
            gun["vitrin"] = etkilesim.vitrin(maclar, oranlar, ayar, simdi)
            _ozet_yaz(f"Vitrin: {len(gun['vitrin'])} maç; kredi {api.harcanan}, kalan {api.kalan}.\n" +
                      "\n".join(f'- {v["ev"]} v {v["dep"]} {v["baslama"]} {v["p"]} {v["olasi_skor"]}' for v in gun["vitrin"]))
        if args.komut == "nabiz" and kayit.bul(gunler, bugun) is None and _sabah_penceresi(simdi, ayar):
            # Sabah çalışması GitHub tarafından iptal edildi/atlandıysa nabız günün analizini hazırlar.
            _ozet_yaz("Sabah çalışması bulunamadı; nabız günün analizini hazırlıyor.")
            args.komut = "otomatik"
        if args.komut == "otomatik":
            analiz_gunu(ayar, gunler, bugun, simdi)
        if args.komut == "likely_paket":
            # Elle: bugünün Mr. Likely paketini kayıtlı analizden ve güncel oranlardan hazırlar (sabah gelmediyse).
            try:
                dosya = config.DATA_FILE.parent / "analiz" / f"{bugun}.json"
                api_ = _api(ayar)
                oranlar = football.toplu_oranlar(api_, bugun, ayar.saat_dilimi, ayar.max_oran_sayfasi)
                analizler_ = json.loads(dosya.read_text(encoding="utf-8"))
                _likely_buyuk_oranlar(api_, analizler_, oranlar)
                if not likely.sabah(ayar, analizler_, oranlar, simdi, onay.GitHub(), yaz=_ozet_yaz):
                    _ozet_yaz("Mr. Likely paketi hazırlanmadı: bugün zaten gönderilmiş ya da ayarlarda kapalı.")
            except Exception as e:
                _hata("Mr. Likely paketi", e)
        if args.komut == "likely_ek":
            # Elle: bugün eksik kalan otomatik kupon türünü (ör. long shot) güncel oranlarla tamamlar.
            try:
                dosya = config.DATA_FILE.parent / "analiz" / f"{bugun}.json"
                oranlar = football.toplu_oranlar(_api(ayar), bugun, ayar.saat_dilimi, ayar.max_oran_sayfasi)
                likely.ek_kupon(ayar, json.loads(dosya.read_text(encoding="utf-8")), oranlar, simdi, onay.GitHub(), yaz=_ozet_yaz)
            except Exception as e:
                _hata("Mr. Likely ek kupon", e)
        if args.komut == "likely_iptal":
            # Elle (SÖZLEŞME E5 istisnası): veri hatası olan bugünkü kupon maç başlamadan silinir, karneye girmez.
            # ek: kupon adı (gunun-kuponu / long-shot / buyuk-maclar), isteğe bağlı ":" sonrası neden.
            try:
                ad, _, neden = os.environ.get("BOT_EK", "").partition(":")
                x_ = _x_likely()
                if x_ is not None and ad.strip():
                    likely.veri_hatasi_iptal(ayar, x_, simdi, ad.strip(), neden.strip() or "veri hatası", yaz=_ozet_yaz)
            except Exception as e:
                _hata("Mr. Likely kupon iptali", e)
        if args.komut == "likely_yenile":
            # Elle: bugün paylaşılmış, maçı başlamamış kupon postlarını siler; güncel düzenle hemen yeniden paylaşılır.
            try:
                x_ = _x_likely()
                if x_ is not None:
                    likely.yeniden_paylas(ayar, x_, simdi, yaz=_ozet_yaz)
            except Exception as e:
                _hata("Mr. Likely yeniden paylaşım", e)
        if args.komut in ("onay_kontrol", "nabiz", "likely", "likely_ek", "likely_yenile"):
            likely_nabiz(ayar, simdi, sonuclar=args.komut != "onay_kontrol")
        if args.komut in ("onay_kontrol", "nabiz", "flood") and os.environ.get("GH_TOKEN"):
            flood_nabiz(ayar, simdi)
    finally:
        alarm_iletildi = False
        # Tweet atıldıktan sonra hata olsa bile kimlikler kaydedilir; tekrar paylaşım olmaz.
        kayit.kaydet(config.DATA_FILE, gunler)
        panel.olustur(gunler, config.PANEL_FILE, ayar)
        # Sağlık kontrolü: kaçan, duran, hata veren her şey sahibine alarm olarak bildirilir (GitHub bildirimi).
        if args.komut in ("nabiz", "otomatik") and os.environ.get("GH_TOKEN") and ayar.alarm_kime:
            try:
                saglik.bildir(saglik.sorunlar(gunler, simdi, ayar, HATALAR), onay.GitHub(), ayar.alarm_kime, simdi,
                              yaz=_ozet_yaz)
                alarm_iletildi = True
            except Exception as e:
                _ozet_yaz(f"⚠️ Alarm bildirilemedi: {e}")
    return cikis_kodu(HATALAR, alarm_iletildi)


def cikis_kodu(hatalar: list[str], alarm_iletildi: bool) -> int:
    """Hata alarm issue'suna yazıldıysa 0: sahibine tek kanaldan, bir kez (SÖZLEŞME C2). Yazılamadıysa 1: iş
    "başarısız" görünür, nöbetçi alarm açar (C1)."""
    return 1 if hatalar and not alarm_iletildi else 0


if __name__ == "__main__":
    sys.exit(main())
