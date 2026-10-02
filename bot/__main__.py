"""Kullanım: python -m bot [otomatik|tahmin|yayinla|sonuc|panel|demo|tani|onizleme|duzelt|sabit]"""

import argparse
import copy
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import analiz, config, denetci, direktor, editor, etkilesim, football, gorsel, kayit, model, oddsapi, onay, panel, temizlik, tweets
from .model import adaylari_uret, bet_builder, etiketler

# Çalışma sırasında yakalanan hatalar: iş sonunda "başarısız" işaretlenir, GitHub sahibine e-posta atar.
HATALAR: list[str] = []
# Son taramanın maçları ve oranları: kupon dışı paylaşımlar (günün maçları, anket) bunlardan hazırlanır.
SON_TARAMA: dict = {}

GUVENLI_LIMIT = 10
# Sabah taramasından sonra gün içi sonuç kontrolleri ve elle komutlar için ayrılan istek (tek çalışmalık istisnayla değişebilir).
API_YEDEK = int(config.istisnalar().get("api_yedek", 25))


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


def tahmin(ayar, api, sec, gunler: list[dict], bugun: str, simdi: datetime,
           gun_id: str | None = None, haric_takimlar: set[str] | None = None) -> dict | None:
    """gun_id/haric_takimlar: aynı gün ek kupon (ayrı kayıt); o gün kuponda olan takımların maçları alınmaz."""
    gun_id = gun_id or bugun
    if kayit.bul(gunler, gun_id):
        print(f"{gun_id} için kayıt zaten var, atlanıyor.")
        return None
    SON_TARAMA.clear()
    try:
        maclar = football.gunun_maclari(api, bugun, ayar.ligler, ayar.saat_dilimi,
                                        ayar.min_dakika_once, 10_000, simdi, tum_ligler=ayar.tum_ligler)
    except football.ApiHatasi as e:
        maclar = None
        yedek_neden = f"API-Football maç listesi alınamadı: {e}"
    if maclar is not None:
        print(f"{len(maclar)} uygun maç bulundu.")
    try:
        if maclar is None:
            raise HakYetmiyor(yedek_neden)
        mac_map, adaylar = _toplu_tara(ayar, api, maclar, bugun)
    except HakYetmiyor as e:
        # API-Football kullanılamıyor (hak bitti / hesap sorunu): yedek kaynak The Odds API.
        if not os.environ.get("ODDS_API_KEY"):
            _hata("Tarama", e)
            return None
        _ozet_yaz(f"⚠️ {e} — yedek oran kaynağı (The Odds API) kullanılıyor.")
        try:
            mac_map, adaylar = _odds_tara(ayar, bugun, simdi)
        except oddsapi.OddsApiHatasi as e2:
            _hata("Tarama (The Odds API)", e2)
            return None
    except football.ApiHatasi as e:
        # Toplu tarama çalışmazsa eski yöntem: izinli liglerden maç maç (maç başına 2 istek, yedeğe dokunmadan).
        print(f"Toplu oran taraması yapılamadı ({e}); maç maç taramaya geçiliyor.")
        kalan = football.kalan_istek(api) if hasattr(api, "session") else None
        adet = ayar.max_mac_tarama if kalan is None else max(0, min(ayar.max_mac_tarama, (kalan - API_YEDEK) // 2))
        izinli = [m for m in maclar if m["lig_id"] in ayar.ligler][:adet]
        mac_map, adaylar = _mac_mac_tara(ayar, api, izinli)
    if haric_takimlar:
        adaylar = [a for a in adaylar if not {mac_map[a["fixture_id"]]["ev"].lower(),
                                               mac_map[a["fixture_id"]]["dep"].lower()} & haric_takimlar]
    guvenli = sorted((a for a in adaylar if a["tur"] == "guvenli"), key=lambda a: a["adil_olasilik"], reverse=True)
    deger = sorted((a for a in adaylar if a["tur"] == "deger"), key=lambda a: a["deger"], reverse=True)
    adaylar = guvenli[:GUVENLI_LIMIT] + deger[:DEGER_LIMIT]
    print(f"{len(guvenli)} güvenli, {len(deger)} değer adayı; API isteği: {api.istek_sayisi}")

    gun = {"id": gun_id, "tarih": bugun, "olusturma": simdi.isoformat(timespec="seconds"),
           "baslik": "", "secimler": [], "sonuc": None, "tweet_id": None,
           "para": ayar.para_birimi, "yuzde": ayar.oyun_yuzdesi}
    if SON_TARAMA:
        gun["taranan"] = len(SON_TARAMA["maclar"])
        gun["vitrin"] = etkilesim.vitrin(SON_TARAMA["maclar"], SON_TARAMA["oranlar"], ayar, simdi)
    if adaylar:
        for fid in {a["fixture_id"] for a in adaylar if "odds_id" not in mac_map[a["fixture_id"]]}:
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
    kupon_nosu = {i: n for n, k in enumerate(karar["kuponlar"]) for i in k["aday_idler"]}
    for s in karar["secimler"]:
        a = aday_map[s["aday_id"]]
        m = mac_map[a["fixture_id"]]
        gun["secimler"].append({
            "fixture_id": a["fixture_id"], "lig": _lig_adi(m, ayar), "ulke": m.get("ulke", ""), "ev": m["ev"], "dep": m["dep"],
            "baslama": m["baslama"],
            "saat": datetime.fromisoformat(m["baslama"]).astimezone(ZoneInfo(ayar.saat_dilimi)).strftime("%H:%M %Z"),
            "olasi_skor": a["olasi_skor"], "pazar": a["pazar"], "tur": a["tur"], "etiket": a["etiket"],
            # Oyunlar tek tek oynanmaz (stake 0); yatırım kupon başınadır.
            "kisa": a["kisa"], "oran": a["oran"], "stake": 0, "kupon_no": kupon_nosu[s["aday_id"]],
            "bolag": a["bolag"], "oranlar": a.get("oranlar", {}), "adil_olasilik": a["adil_olasilik"], "adil_kaynak": a["adil_kaynak"],
            "model_olasilik": a["model_olasilik"], "deger": a["deger"], "beklenen_gol": a["beklenen_gol"],
            "yorum": editor.celiskisiz_yorum(editor.temiz_yorum(s["yorum"], ayar.oran_bahiscileri + [ayar.keskin_bahisci]),
                                             [a["pazar"]]),
            "durum": "bekliyor", "skor": None,
            **{k: m[k] for k in ("odds_id", "odds_spor") if k in m},  # sonuç yedek kaynaktan sorulur
        })
    gun["secimler"] = bet_builder_birlestir(gun["secimler"])
    gun["secimler"].sort(key=lambda s: s["baslama"])
    # Kuponlar ilk maçlarının saatine göre sıralanır.
    nolar = sorted({s["kupon_no"] for s in gun["secimler"]},
                   key=lambda n: min(s["baslama"] for s in gun["secimler"] if s["kupon_no"] == n))
    gun["kuponlar"] = [{"ayaklar": [i for i, s in enumerate(gun["secimler"]) if s["kupon_no"] == n],
                        "durum": None} for n in nolar]
    # Denetçi: söylenen her şey seçimle tutarlı mı? Sorunlu cümle atılır, çelişkili seçimin kuponu çıkar.
    denetci.denetle(gun, ayar, yaz=_ozet_yaz, yz=ayar.direktor_aktif and bool(os.environ.get("ANTHROPIC_API_KEY")))
    if not gun["kuponlar"]:
        gun.update(secimler=[], sonuc="pas", pas_nedeni="Denetçi seçimleri tutarsız buldu; paylaşılmadı.")
        gunler.append(gun)
        _ozet_yaz(f"### {bugun}: denetçi kuponları durdurdu")
        return None
    stakeler = kayit.stakeler(gunler, ayar.kasa_baslangic, ayar.oyun_yuzdesi, len(gun["kuponlar"]))
    for k, (kasa_, stake) in zip(gun["kuponlar"], stakeler):
        k["kasa"], k["stake"] = kasa_, stake
    gun["baslik"] = karar["baslik"].strip()
    gun["yanit_onerileri"] = editor.yanit_onerilerini_hazirla(
        karar.get("yanit_onerileri") or [], mac_map, ayar.oran_bahiscileri + [ayar.keskin_bahisci])
    taslak = "\n\n".join(tweets.gun_floodu(gun, kayit.ozet(gunler, ayar.kasa_baslangic)))
    _ozet_yaz(f"### {bugun} taslak\n```\n{taslak}\n```")
    parcalar = kayit.kuponlara_bol(gun, gunler)  # her kupon ayrı kayıt, ayrı paylaşım
    gunler.extend(parcalar)
    return parcalar[0]


def _onaya_gonder(ayar, gunler: list[dict], bugun: str, simdi: datetime) -> list[dict]:
    """Bugünün henüz onaya gönderilmemiş kuponlarını onaya yollar; cevapsız kalırlarsa 30 dk arayla paylaşılırlar."""
    bekleyen = [g for g in gunler if g["tarih"] == bugun and g["secimler"] and not g.get("tweet_id")
                and not g.get("onay") and g.get("sonuc") is None]
    for i, g in enumerate(bekleyen):
        onay.onay_iste(g, gunler, ayar, simdi, gecikme_dk=30 * i)
        denetim = (g.get("onay") or {}).get("denetim") or {}
        if denetim.get("engel"):
            # Hatalı post paylaşılmaz; iş "başarısız" işaretlenir, GitHub sahibine e-posta atar.
            _hata(f"Denetçi ({g['id']})", RuntimeError("; ".join(denetim["engel"])))
            continue
        _ozet_yaz(f"Onay istendi ({g['id']}); cevap yoksa {(g.get('onay') or {}).get('son')} (UTC) otomatik paylaşılacak.")
    return bekleyen


def _incele(ayar, api, m: dict, bahisciler: dict, mac_map: dict, adaylar: list) -> None:
    ist = football.istatistik_al(api, m["fixture_id"])
    if not ist:
        _ozet_yaz(f'Elendi: {m["ev"]} v {m["dep"]} — takım istatistiği yok.')
        return
    mac_adaylari = adaylari_uret(m, bahisciler, ist, ayar, guvenilir_lig=m["lig_id"] in ayar.ligler)
    if not mac_adaylari:
        neden = "istatistik yetersiz (az maç)" if not model.veri_yeterli(ist) else "gol modeli piyasayla uyuşmadı"
        _ozet_yaz(f'Elendi: {m["ev"]} v {m["dep"]} — {neden}.')
    if mac_adaylari:
        mac_map[m["fixture_id"]] = {**m, "istatistik": ist}
        adaylar += mac_adaylari


def _toplu_tara(ayar, api, maclar: list[dict], bugun: str) -> tuple[dict, list]:
    """1) Günün bütün oranları toplu çekilir, 2) piyasaya göre en umut vadeden maçlar detaylı incelenir."""
    # Günlük hak koruması: gün içindeki sonuç kontrolleri ve elle komutlar için en az API_YEDEK istek kalsın.
    # Ücretsiz plan: tarihle toplu oran en fazla 3 sayfa (30 maç); lig filtresi güncel sezonda kapalı; maç başına
    # oran açık (1 istek). Plan: 3 toplu sayfa + kalan haktan (yedek ve detay payı düşülerek) maç maç tamamlama.
    kalan = football.kalan_istek(api) if hasattr(api, "session") else None
    detay_payi = 2 * ayar.max_detay_mac
    if kalan is not None:
        print(f"API-Football: bugün {kalan} istek kalmış.")
        if kalan - API_YEDEK < ayar.max_oran_sayfasi + 4:
            raise HakYetmiyor(f"günlük istek hakkı tarama için yetmiyor (kalan {kalan})")
        detay_payi = min(detay_payi, kalan - API_YEDEK - ayar.max_oran_sayfasi)
    oranlar = football.toplu_oranlar(api, bugun, ayar.saat_dilimi, ayar.max_oran_sayfasi)
    if not oranlar:
        raise football.ApiHatasi("toplu taramada hiç oran gelmedi")
    SON_TARAMA.update(maclar=maclar, oranlar=oranlar)
    # Toplu taramaya girmeyen maçlar (önce izinli ligler) hak yettiğince tek tek tamamlanır.
    eksik = [m for m in maclar if m["fixture_id"] not in oranlar]
    kalan = football.kalan_istek(api) if hasattr(api, "session") else None
    butce = 0 if kalan is None else max(0, kalan - API_YEDEK - detay_payi)
    print(f"Maç maç oran tamamlama: {min(butce, len(eksik))} maç")
    for m in eksik[:butce]:
        try:
            b = football.oranlari_al(api, m["fixture_id"])
        except football.ApiHatasi as e:
            print(f"Eksik oran tamamlama durdu: {e}")
            break
        if b:
            oranlar[m["fixture_id"]] = b
    # Ön eleme teşhisi: neden elendiklerini görmek için
    adlar = {b.lower() for b in ayar.oran_bahiscileri}
    pin = sum(any(a.lower() == ayar.keskin_bahisci.lower() for a in o) for o in oranlar.values())
    b365 = sum(any(a.lower() == "bet365" for a in o) for o in oranlar.values())
    uc = sum(sum(a.lower() in adlar for a in o) >= ayar.min_oran_bahiscisi for o in oranlar.values())
    _ozet_yaz(f"Oran teşhisi: {len(oranlar)} maçta Pinnacle {pin}, Bet365 {b365}, "
              f"listeden ≥{ayar.min_oran_bahiscisi} site {uc}.")
    puanli = []
    for m in maclar:
        if m["fixture_id"] in oranlar:
            puan = model.on_eleme_puani(oranlar[m["fixture_id"]], ayar, m["lig_id"] in ayar.ligler)
            if puan is not None:
                puanli.append((puan, m))
    puanli.sort(key=lambda x: x[0], reverse=True)
    if not puanli:  # teşhis: kurala en çok yaklaşan pazarlar (değer = oran × adil ihtimal − 1)
        yakin = []
        for m in maclar:
            if m["fixture_id"] not in oranlar:
                continue
            adil, _ = model.adil_olasiliklar(oranlar[m["fixture_id"]], ayar.keskin_bahisci)
            for pazar, (oran, _, _d) in model.piyasa_oranlari(oranlar[m["fixture_id"]], ayar.oran_bahiscileri,
                                                               ayar.oran_yontemi).items():
                if pazar in adil and adil[pazar] >= 0.6 and ayar.oran_min <= oran <= ayar.oran_max:
                    en_iyi = max(_d.values())
                    yakin.append((adil[pazar] * oran - 1, f'{m["ev"]} v {m["dep"]} {pazar} medyan {oran:.2f} '
                                  f'(en iyi {en_iyi:.2f}, değer {adil[pazar] * en_iyi - 1:+.3f}) p={adil[pazar]:.2f}'))
        yakin.sort(reverse=True)
        _ozet_yaz("Kurala en yakın 5 pazar: " + "; ".join(f"{d:+.3f} {t}" for d, t in yakin[:5]))
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


def _odds_tara(ayar, bugun: str, simdi: datetime) -> tuple[dict, list]:
    """Yedek kaynak: bugünün oranları The Odds API'den; takım istatistiği olmadan piyasa tabanlı adaylar."""
    api = oddsapi.OddsApi(config.env("ODDS_API_KEY"))
    maclar, oranlar = oddsapi.tara(api, bugun, ayar, simdi, yaz=_ozet_yaz)
    SON_TARAMA.update(maclar=maclar, oranlar=oranlar)
    mac_map, adaylar = {}, []
    for m in maclar:
        if m["fixture_id"] not in oranlar:
            continue
        mac_adaylari = oddsapi.adaylar(m, oranlar[m["fixture_id"]], ayar)
        if mac_adaylari:
            mac_map[m["fixture_id"]] = {**m, "not": "No team form data today: expected goals and most likely score "
                                                    "are implied by the sharp betting market."}
            adaylar += mac_adaylari
    ligler = sorted({m["lig"] for m in maclar})
    _ozet_yaz(f"The Odds API taraması: {len(maclar)} maç ({', '.join(ligler)}), {len(oranlar)} maçın oranı, "
              f"{len(mac_map)} maçta aday; harcanan kredi {api.harcanan}, kalan {api.kalan}.")
    if True:  # teşhis: yüksek ihtimalli pazarlar ve neden elendikleri (değer = en iyi oran × adil ihtimal − 1)
        yakin = []
        for m in maclar:
            b = oranlar.get(m["fixture_id"])
            if not b:
                continue
            adil, kaynak = model.adil_olasiliklar(b, ayar.keskin_bahisci)
            for pazar, (oran, _, d) in model.piyasa_oranlari(b, ayar.oran_bahiscileri, ayar.oran_yontemi).items():
                if pazar in adil and adil[pazar] >= 0.6:
                    neden = ("oran düşük" if oran < ayar.oran_min else "oran yüksek" if oran > ayar.oran_max
                             else f"{len(d)} site" if len(d) < ayar.min_oran_bahiscisi else "")
                    yakin.append((adil[pazar] * oran - 1, f'{m["ev"]} v {m["dep"]} {pazar} {oran:.2f} '
                                  f'p={adil[pazar]:.2f} ({len(d)} site, {kaynak[pazar]}{", " + neden if neden else ""})'))
        yakin.sort(reverse=True)
        _ozet_yaz("Yüksek ihtimalli pazarlar (en iyi 12): " + "; ".join(f"{v:+.3f} {t}" for v, t in yakin[:12]))
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
                                   "kupon_no", "odds_id", "odds_spor") if k in ilk},
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
    for t in x.son_tweetler(adet=10, yanitsiz=True):
        metin = t["text"].lstrip("⚽ ")
        ilk = metin.splitlines()[0] if metin else ""
        # Yalnızca kupon başlıkları: "TODAY'S BIG GAMES" gibi etkileşim paylaşımları kupon sanılmaz.
        if re.match(r"TODAY'S (COUPON|\d+ COUPONS)\b", ilk) and etiket in ilk:
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
    yeni_ana = kayit.bul(gunler, bugun)
    if gun and yeni_ana and gun.get("etkilesim"):
        yeni_ana["etkilesim"] = gun["etkilesim"]  # bugün atılmış etkileşim paylaşımları tekrar atılmasın
    if yeni and ayar.onay_bekle:
        _onaya_gonder(ayar, gunler, bugun, simdi)  # yeniden seçilen kuponlar da önce onaya gelir
        return True
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
    # Yedek kaynaktan (The Odds API) seçilen maçların sonucu da oradan sorulur.
    yedek = {s["fixture_id"]: s for g in gunler for s in g["secimler"] if s.get("odds_id")}
    yedek_ids = [i for i in ids if i in yedek]
    af_ids = [i for i in ids if i not in yedek]
    hata = None
    if yedek_ids:
        istekler: dict[str, list[str]] = {}
        for i in yedek_ids:
            istekler.setdefault(yedek[i]["odds_spor"], []).append(yedek[i]["odds_id"])
        try:
            sonuclar = oddsapi.sonuclari_al(oddsapi.OddsApi(config.env("ODDS_API_KEY")), istekler)
            kayit.sorgulandi(gunler, yedek_ids, simdi)
            for g in kayit.sonuclandir(gunler, sonuclar, simdi):
                print(f"{g['id']} sonuçlandı.")
        except Exception as e:
            hata = e
    if af_ids:
        sonuclar = football.sonuclari_al(api, af_ids, kayit.korner_fixturelari(gunler))
        kayit.sorgulandi(gunler, af_ids, simdi)
        for g in kayit.sonuclandir(gunler, sonuclar, simdi):
            print(f"{g['id']} sonuçlandı.")
    if not ids:
        print("Sonuç bekleyen maç yok.")
    if hata:
        _hata("Sonuçlar (The Odds API)", hata)
    # Kasa defteri bağımsız denetlenir: tek kuruş tutmazsa yanlış rakam paylaşılmaz, sahibine hata bildirilir.
    if any(g.get("tweet_id") and g["sonuc"] == "tamam" and not g.get("sonuc_tweet_id") for g in gunler):
        hatalar = denetci.kasa_denetimi(gunler, ayar.kasa_baslangic)
        if hatalar:
            _hata("Kasa denetimi", RuntimeError("Sonuç postları durduruldu:\n" + "\n".join(hatalar)))
            return
    # Sonuçlanıp sonuç floodu atılmamış (ya da yarım kalmış) her gün: X hatası olsa bile sonraki çalışmada tamamlanır.
    for g in kayit.duyuru_sirasi(gunler):
        if g.get("tweet_id") and g["sonuc"] == "tamam" and not g.get("sonuc_tweet_id"):
            idler = g.setdefault("sonuc_tweet_idleri", [])
            try:
                ozet = kayit.sonuc_ozeti(gunler, g, ayar.kasa_baslangic)
                metinler = tweets.sonuc_tweetleri(g, ozet)
                if not idler:
                    # Sonuç ayrı bir paylaşım (profilde ve akışta görünür; yanıtlar görünmez): sonuç kartı + kasa,
                    # kupon tweetini alıntılar. Kart yüklenemezse metin olarak gider.
                    medya = None
                    for _ in range(3):
                        try:
                            medya = [x.medya_yukle(gorsel.sonuc_gorseli(g, ozet))]
                            break
                        except Exception as e:
                            print(f"Sonuç kartı yüklenemedi: {e}")
                    if medya:
                        metinler = [tweets.gorselli_sonuc_tweeti(g, ozet)]
                        try:
                            idler.append(x.gonder(metinler[0], medya=medya, alinti=g["tweet_id"]))
                        except RuntimeError as e:
                            if "duplicate" in str(e).lower():
                                raise
                            print(f"Alıntılı görselli paylaşım reddedildi ({e}); alıntısız deneniyor.")
                            idler.append(x.gonder(metinler[0], medya=medya))
                    else:
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


def kasa_duzelt(ayar, gunler: list[dict], bugun: str, simdi: datetime, x) -> int:
    """Bugünün sonuçlanmamış kuponlarının kasa/yatırılan değerlerini paylaşım sırasına göre yeniden hesaplar
    (her kupon, öncekiler düşüldükten sonra kalan kasanın %'si). Değişen ve maçı başlamamış paylaşımlar
    silinip doğru rakamlarla yeniden atılır."""
    def degistirilebilir(g):
        return (g["tarih"] == bugun and kayit.kuponlar(g) and g.get("sonuc") is None
                and all(kayit.kupon_durumu(g, k) is None for k in kayit.kuponlar(g))
                and min(datetime.fromisoformat(s["baslama"]) for s in g["secimler"]) > simdi)
    bugunkuler = sorted((g for g in gunler if degistirilebilir(g)),
                        key=lambda g: (0 if g.get("yayin") else 1, g.get("yayin") or "", g["id"]))
    digerleri = [g for g in gunler if g not in bugunkuler]
    kalan = kayit.kasa(gunler, ayar.kasa_baslangic) - kayit.acik_stake(digerleri)
    duzeltilen, yeniden_onay = 0, 0
    for g in bugunkuler:
        degisti = False
        for k in kayit.kuponlar(g):
            stake = round(kalan * ayar.oyun_yuzdesi / 100, 2)
            if abs(k["stake"] - stake) > 0.005:
                k["stake"], degisti = stake, True
            k["kasa"] = round(kalan, 2)  # yatırılan doğruysa yalnızca gösterilecek kasa eklenir, paylaşım değişmez
            kalan -= stake
        if not degisti:
            continue
        (g.get("onay") or {}).pop("kasa", None)
        if g.get("tweet_id"):
            (g.get("onay") or {}).pop("metinler", None)
            duzelt(ayar, g, x, gunler, simdi)
        elif (g.get("onay") or {}).get("durum") == "bekliyor":
            onay.onizlemeleri_sil(g["id"])
            # sahibi yeni rakamları görsün (paylaşılan = önizlenen); cevapsızlar yine 30 dk arayla çıkar
            onay.onay_iste(g, gunler, ayar, simdi, gecikme_dk=30 * yeniden_onay)
            yeniden_onay += 1
        elif (g.get("onay") or {}).get("durum") == "durduruldu":
            (g.get("onay") or {}).pop("metinler", None)  # durdurulmuş kalır; "ok" gelirse doğru rakamlarla çıkar
        duzeltilen += 1
        _ozet_yaz(f"{g['id']}: kasa " + ", ".join(f"{k['kasa']:.2f} → yatırılan {k['stake']:.2f}" for k in kayit.kuponlar(g)))
    return duzeltilen


def sonuc_duzelt(ayar, gunler: list[dict], bugun: str, simdi: datetime, x) -> int:
    """Bugünün bütün sonuç postlarını siler ve paylaşım sırasıyla yeniden atar: her post bir öncekinin
    kasasından devam eder (zaman akışında kasa kuponlar kapandıkça adım adım güncellenir)."""
    duzeltilen = 0
    tarihler = [g["tarih"] for g in gunler if g.get("sonuc_tweet_idleri")]
    if bugun not in tarihler and tarihler:
        bugun = max(tarihler)  # gece yarısını geçtiyse: en son sonuç atılan gün
    for g in [g for g in gunler if g["tarih"] == bugun and g.get("sonuc_tweet_idleri")]:
        for tid in reversed(g["sonuc_tweet_idleri"]):
            if tid != "x-mukerrer":
                x.sil(tid)
        g["sonuc_tweet_idleri"], g["sonuc_tweet_id"] = [], None
        duzeltilen += 1
        _ozet_yaz(f"{g['id']}: sonuç postu silindi, sırayla yeniden paylaşılacak.")
    if duzeltilen:
        sonuc(ayar, None, x, gunler, simdi)
    return duzeltilen


def skor_duzelt(gunler: list[dict], bugun: str, simdi: datetime, x) -> int:
    """Bugün paylaşılmış gerekçe yanıtlarından en olası skoru seçimle çelişenleri (maç başlamadıysa) düzeltir:
    ilk çelişkili yanıttan sonuna kadar silinip doğru metinle aynı zincire yeniden atılır."""
    duzeltilen = 0
    for g in [g for g in gunler if g["tarih"] == bugun and g.get("tweet_id") and g.get("analiz_tweet_idleri")]:
        celiskili = [i for i, s in enumerate(g["secimler"]) if tweets.skor_celiskili(s)]
        idler = g["analiz_tweet_idleri"]
        if not celiskili or celiskili[0] >= len(idler):
            continue
        k = celiskili[0]
        if any(datetime.fromisoformat(s["baslama"]) <= simdi for s in g["secimler"][k:]):
            continue
        metinler = tweets.analiz_tweetleri(g)
        for tid in reversed(idler[k:]):
            x.sil(tid)
        del idler[k:]
        onceki = idler[-1] if idler else g["tweet_id"]
        for metin in metinler[k:]:
            onceki = x.gonder(metin, yanit=onceki)
            idler.append(onceki)
        (g.get("onay") or {}).pop("metinler", None)
        duzeltilen += 1
        _ozet_yaz(f"{g['id']}: {len(metinler) - k} gerekçe yanıtı düzeltilerek yeniden atıldı.")
    return duzeltilen


def ayir(ayar, gunler: list[dict], bugun: str, simdi: datetime, x) -> int:
    """Bugün tek paylaşımda çıkmış çok kuponlu kayıtları (maçlar başlamadıysa) siler ve kupon başına ayrı
    paylaşıma çevirir: ilki hemen, diğerleri 30 dk arayla (nabız paylaşır). Onaylı içerik değişmez."""
    sayi = 0
    for gun in [g for g in gunler if g["tarih"] == bugun and g.get("tweet_id") and len(kayit.kuponlar(g)) > 1]:
        if min(datetime.fromisoformat(s["baslama"]) for s in gun["secimler"]) <= simdi:
            continue
        for tid in reversed([gun["tweet_id"]] + gun.get("analiz_tweet_idleri", [])):
            x.sil(tid)
        kasa_ = (gun.get("onay") or {}).get("kasa")
        for k in ("tweet_id", "analiz_tweet_idleri", "gorselli", "yayin", "onay"):
            gun.pop(k, None)
        gunler.remove(gun)
        parcalar = kayit.kuponlara_bol(gun, gunler)
        gunler.extend(parcalar)
        for i, p in enumerate(parcalar):
            son = simdi + timedelta(minutes=30 * i)
            p["onay"] = {"durum": "bekliyor", "son": son.isoformat(timespec="seconds"), "surum": 1,
                         **({"kasa": kasa_} if kasa_ else {})}
        yayinla(ayar, parcalar[0], x, gunler, simdi)
        parcalar[0]["onay"]["durum"] = "onaylandi"
        sayi += len(parcalar)
        _ozet_yaz(f"{gun['id']}: {len(parcalar)} ayrı paylaşıma bölündü; ilki paylaşıldı, diğerleri 30 dk arayla.")
    return sayi


def ek_kupon(ayar, gunler: list[dict], bugun: str, simdi: datetime) -> dict | None:
    """Aynı gün için 1-2 ek kupon: ayrı kayıt (ör. 2026-10-01-2), günün kuponundaki maçlar hariç, önce onaya gelir."""
    from dataclasses import replace
    bugunkuler = [g for g in gunler if g["tarih"] == bugun]
    if not bugunkuler:
        raise RuntimeError("Bugünün ana kaydı yok; önce sabah taraması.")
    haric = {t.lower() for g in bugunkuler for s in g["secimler"] for t in (s["ev"], s["dep"])}
    ek_id = f"{bugun}-{len(bugunkuler) + 1}"
    kalan = ayar.max_kupon - sum(len(kayit.kuponlar(g)) for g in bugunkuler if g.get("sonuc") != "pas")
    if kalan <= 0:
        _ozet_yaz(f"Ek kupon yok: bugün günlük sınıra ({ayar.max_kupon} kupon) ulaşıldı.")
        return None
    yeni = tahmin(replace(ayar, max_kupon=kalan), _api(ayar), _secici(), gunler, bugun, simdi,
                  gun_id=ek_id, haric_takimlar=haric)
    if not yeni:
        pas = kayit.bul(gunler, ek_id)
        if pas:
            gunler.remove(pas)  # ek kupon çıkmadıysa boş kayıt tutulmaz
        _ozet_yaz("Ek kupon çıkmadı: kurallara uyan yeni oyun yok.")
        return None
    yeni["ek"] = True
    _onaya_gonder(ayar, gunler, bugun, simdi)
    return yeni


def _sabah_penceresi(simdi: datetime, ayar) -> bool:
    """Planlı sabah çalışmasından 20 dk sonra ile 2,5 saat sonrası arası (yerel saat, yaz/kış aynı kalır)."""
    yerel = simdi.astimezone(ZoneInfo(ayar.saat_dilimi))
    bas = (12 * 60 + 47) if yerel.weekday() < 5 else (10 * 60 + 17)
    dk = yerel.hour * 60 + yerel.minute
    return bas + 20 <= dk <= bas + 150


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
    gun = {"id": bugun, "tarih": bugun, "olusturma": simdi.isoformat(timespec="seconds"), "baslik": "",
           "secimler": [], "sonuc": "analiz", "tweet_id": None, "konsept": "analiz", "taranan": len(maclar),
           "analiz_sayisi": len(analizler), "vitrin": etkilesim.vitrin(maclar, oranlar, ayar, simdi),
           "analizler": one,
           "tablo": [analiz.ozet(a) for a in analiz.tablo_secimi(  # kartı olan maçlar tabloda tekrar edilmez
               analizler, ayar.ligler, en_erken=(simdi + timedelta(minutes=90)).isoformat(),
               haric={a["fixture_id"] for a in one})],
           "ayrisma": [analiz.ozet(a) for a in analiz.ayrisma_secimi(analizler)]}
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
    return gun


def liste_simdi(ayar, gunler: list[dict], bugun: str, simdi: datetime, x) -> str | None:
    """Elle: günün kalan önemli maçlarının listesini (analiz tablosu, bütün maç etiketleriyle) şimdi paylaşır.
    Kartı olan maçlar da girer; ayrı etkileşim kaydı (tablo_N) olarak saklanır."""
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
    durum = gun.setdefault("etkilesim", {})
    for k, e in list(durum.items()):
        if k.startswith("tablo_") and e.get("elle") and e.get("durum") == "paylasildi":
            x.sil(e["tweet_id"])
            durum[k] = {**e, "durum": "silindi"}
    png = gorsel.analiz_tablosu(liste, bugun, [etkilesim._saat(a, ayar) for a in liste], "en")
    tid = x.gonder(metin, medya=[x.medya_yukle(png)])
    anahtar = next(f"tablo_{n}" for n in range(2, 99) if f"tablo_{n}" not in durum)
    durum[anahtar] = {"durum": "paylasildi", "tweet_id": tid, "zaman": simdi.isoformat(timespec="seconds"), "elle": True}
    _ozet_yaz(f"Liste paylaşıldı ({anahtar}): https://x.com/kalkylerat/status/{tid}\n```\n{metin}\n```")
    return tid


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
        tum, ayar.ligler, en_erken=(kayit.simdi_utc() + timedelta(minutes=90)).isoformat(),
        haric={a["fixture_id"] for a in gun["analizler"]})]
    gun["ayrisma"] = [analiz.ozet(a) for a in analiz.ayrisma_secimi(tum)]


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


def _secici():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return editor.claude_ile_sec
    print("ANTHROPIC_API_KEY yok: kural tabanlı basit seçim kullanılıyor (yalnızca demo).")
    return editor.basit_sec


def onizleme(ayar) -> None:
    """Sıradaki paylaşım gününü (bugünün taraması yapılmadıysa bugün, yapıldıysa yarın) gerçek veriyle hazırlar;
    kaydetmez, paylaşmaz."""
    simdi = kayit.simdi_utc()
    yerel = simdi.astimezone(ZoneInfo(ayar.saat_dilimi))
    gunler = kayit.yukle(config.DATA_FILE)
    gun = yerel.date().isoformat()
    if kayit.bul(gunler, gun):
        gun = (yerel + timedelta(days=1)).date().isoformat()
    _ozet_yaz(f"## ÖNİZLEME – {gun} (kaydedilmez, paylaşılmaz)")
    gunler = [g for g in gunler if g["id"] != gun]
    tahmin(ayar, _api(ayar), _secici(), gunler, gun, simdi)


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
        from collections import Counter
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
                                          "sonuc_yeniden", "profil", "odds_tani", "odds_pazar", "vitrin", "ek_kupon", "af_pazar", "ayir", "kasa_duzelt", "direktor", "skor_duzelt", "sonuc_duzelt", "kasa_defteri", "temizle", "liste"])
    args = p.parse_args(argv)
    ayar = config.yukle()
    from dataclasses import replace as _degistir
    ayar = _degistir(ayar, max_kupon=direktor.gunluk_max_kupon(ayar))  # X Direktörünün günlük kupon sınırı

    if args.komut == "demo":
        demo(ayar)
        return 0
    if args.komut == "tani":
        tani(ayar)
        return 0
    if args.komut == "profil":
        profil()
        return 0
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
        if args.komut == "temizle":
            temizlik.baslat(simdi)
        if args.komut in ("temizle", "nabiz") and temizlik.durum().get("aktif"):
            try:
                temizlik.calistir(_x_client(), simdi, yaz=_ozet_yaz)
            except Exception as e:
                _hata("Temizlik", e)
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
                if ayar.konsept == "kupon":
                    haftalik(ayar, _x_client(), gunler, simdi)
            except Exception as e:
                _hata("Haftalık özet", e)
        if args.komut == "nabiz" and kayit.bul(gunler, bugun):
            try:
                analiz_secimlerini_tamamla(ayar, kayit.bul(gunler, bugun))
                diger = tuple(g["yayin"] for g in gunler if g["tarih"] == bugun and g["id"] != bugun and g.get("yayin"))
                kupondakiler = {t.lower() for g in gunler if g["tarih"] == bugun for s in g["secimler"]
                                for t in (s["ev"], s["dep"])}
                etkilesim.paylas(kayit.bul(gunler, bugun), ayar, _x_client(), simdi, yaz=_ozet_yaz,
                                 yazar=_direktor_yazar(ayar), diger_paylasimlar=diger, haric_takimlar=kupondakiler)
            except Exception as e:
                _hata("Etkileşim paylaşımı", e)
        if args.komut == "nabiz":
            for g in gunler[-6:]:  # analiz kartı paylaşılan maçlar bitince: "ne dedik, ne oldu" (alıntı)
                try:
                    etkilesim.analiz_takibi(g, ayar, _x_client(), simdi, lambda m: _mac_sonuclari(ayar, m),
                                            yaz=_ozet_yaz, yazar=_direktor_yazar(ayar))
                except Exception as e:
                    _hata("Analiz takibi", e)
        if args.komut == "nabiz":
            for g in gunler[-6:]:  # oynamadığımız "doğru tahmin, kötü fiyat" maçları bitince alıntıyla nasıl bittikleri
                try:
                    etkilesim.deger_takibi(g, ayar, _x_client(), simdi, lambda m: _mac_sonuclari(ayar, m),
                                           yaz=_ozet_yaz, yazar=_direktor_yazar(ayar))
                except Exception as e:
                    _hata("Değer takibi", e)
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
        if args.komut == "sonuc_duzelt":
            sonuc_duzelt(ayar, gunler, bugun, simdi, _x_client())
        if args.komut == "skor_duzelt":
            skor_duzelt(gunler, bugun, simdi, _x_client())
        if args.komut == "liste":
            liste_simdi(ayar, gunler, bugun, simdi, _x_client())
        if args.komut == "kasa_defteri":
            _ozet_yaz(denetci.kasa_defteri(gunler, ayar.kasa_baslangic))
            if denetci.kasa_denetimi(gunler, ayar.kasa_baslangic):
                _hata("Kasa denetimi", RuntimeError("defterde tutarsızlık var (yukarıda)"))
        if args.komut == "kasa_duzelt":
            kasa_duzelt(ayar, gunler, bugun, simdi, _x_client())
        if args.komut == "ayir":
            ayir(ayar, gunler, bugun, simdi, _x_client())
        if args.komut == "ek_kupon":
            ek_kupon(ayar, gunler, bugun, simdi)
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
        if args.komut == "hafta" and not haftalik(ayar, _x_client(), gunler, simdi, zorla=True):
            print("Haftalık özet paylaşılmadı (zaten var ya da yeterli oyun yok).")
        if args.komut == "nabiz" and kayit.bul(gunler, bugun) is None and _sabah_penceresi(simdi, ayar):
            # Sabah çalışması GitHub tarafından iptal edildi/atlandıysa nabız günün kuponunu hazırlar.
            _ozet_yaz("Sabah çalışması bulunamadı; nabız günün kuponunu hazırlıyor.")
            args.komut = "otomatik"
        if args.komut in ("otomatik", "tahmin") and ayar.konsept != "kupon":
            analiz_gunu(ayar, gunler, bugun, simdi)
        elif args.komut in ("otomatik", "tahmin"):
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
                        # yeni paylaşım ya da yarım floodu tamamlama; onaysız modda günün diğer kuponları da (ayrı postlar)
                        for g in [gun] + ([] if ayar.onay_bekle else [
                                g for g in gunler if g["tarih"] == bugun and g is not gun and g["secimler"]
                                and not g.get("tweet_id") and g.get("sonuc") is None]):
                            yayinla(ayar, g, _x_client(), gunler, simdi)
                    else:
                        _onaya_gonder(ayar, gunler, bugun, simdi)
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
