"""Kupon dışı, etkileşime açık günlük paylaşımlar: günün maçları, günün istatistiği, doğru tahmin/kötü fiyat, anket,
radar, skor tahmini, pas günü.

Veri sabah taramasından gelir (gun["vitrin"]): ek API isteği yapılmaz. Her tür günde bir kez, kendi paylaşımlarımız
arasında en az ARALIK_DK olacak şekilde ve maç saatine göre zamanlanır; 15 dakikalık nabız çalıştırır."""

from datetime import datetime, timedelta
from itertools import product
from zoneinfo import ZoneInfo

from . import analiz, bilgi, config, gorsel, model
from .oddsapi import ima_edilen_goller
from .tweets import ANSVAR, LIMIT, etiket_satiri, ilk_sigan, liste_etiketleri, uzunluk

VITRIN_MAX = 6
ARALIK_DK = 45


def vitrin(maclar: list[dict], oranlar: dict, ayar, simdi: datetime) -> list[dict]:
    """Günün en çok ilgi çekecek maçları: önce izinli ligler, sonra en çok bahisçinin fiyatladığı (likit) maçlar."""
    liste = []
    for m in maclar:
        b = oranlar.get(m["fixture_id"])
        if not b or datetime.fromisoformat(m["baslama"]) <= simdi:
            continue
        adil, _ = model.adil_olasiliklar(b, ayar.keskin_bahisci)
        if not all(k in adil for k in ("MS1", "MSX", "MS2")):
            continue
        goller = ima_edilen_goller(adil)
        if goller is None:
            continue
        skor, _ = model.en_olasi_skor(*goller)
        izinli = m["lig_id"] in ayar.ligler
        liste.append(((izinli, len(b)), {
            "fixture_id": m["fixture_id"], "lig": m.get("lig", ""), "ulke": m.get("ulke", ""), "izinli": izinli, "ev": m["ev"], "dep": m["dep"],
            "baslama": m["baslama"], "p": {k: round(adil[k], 3) for k in ("MS1", "MSX", "MS2")},
            "beklenen_gol": [round(g, 2) for g in goller], "olasi_skor": skor,
            **{k: m[k] for k in ("odds_id", "odds_spor") if k in m},  # sonuç bu kaynaktan sorulur
        }))
    liste.sort(key=lambda x: x[0], reverse=True)
    return [v for _, v in liste[:VITRIN_MAX]]


def _saat(v: dict, ayar) -> str:
    return datetime.fromisoformat(v["baslama"]).astimezone(ZoneInfo(ayar.saat_dilimi)).strftime("%H:%M %Z")


def _etiket(v: dict) -> str:
    e = etiket_satiri([(v.get("lig"), v.get("ulke"))], [(v["ev"], v["dep"])])
    return f"\n{e}" if e else ""


def _pct(p: float) -> str:
    return f"{100 * p:.0f}%"


def _favori(v: dict) -> tuple[str, float]:
    p = v["p"]
    return (v["ev"], p["MS1"]) if p["MS1"] >= p["MS2"] else (v["dep"], p["MS2"])


def anket_maci(vit: list[dict]) -> dict | None:
    """Anket en dengeli büyük maça: herkesin bildiği sonucu oylatmak etkileşim getirmez."""
    adaylar = [v for v in vit[:4] if v.get("izinli")] or vit[:4]
    return max(adaylar, key=lambda v: min(v["p"]["MS1"], v["p"]["MS2"])) if adaylar else None


def maclar_tweeti(gun: dict, ayar) -> str:
    tarih = datetime.fromisoformat(gun["tarih"]).strftime("%-d %b")
    satirlar = []
    for v in gun["vitrin"][:4]:
        fav, p = _favori(v)
        satirlar.append(f'⚽ {v["ev"]} v {v["dep"]} · {_saat(v, ayar)}\n   our numbers: {fav} {_pct(p)}')
    for n in range(len(satirlar), 0, -1):
        etiket = etiket_satiri([(v.get("lig"), v.get("ulke")) for v in gun["vitrin"][:n]],
                               [(v["ev"], v["dep"]) for v in gun["vitrin"][:n]])
        metin = (f"🔥 TODAY'S BIG GAMES | {tarih}\n\n" + "\n".join(satirlar[:n]) +
                 "\n\nWhich one are you watching? 👇" + (f"\n{etiket}" if etiket else ""))
        if uzunluk(metin) <= LIMIT:
            return metin
    return metin


def _secenek(ad: str) -> str:
    return ad if len(ad) <= 25 else ad[:24] + "…"


def anket(gun: dict, ayar) -> tuple[str, list[str], int] | None:
    v = anket_maci(gun["vitrin"])
    if not v:
        return None
    p = v["p"]
    metin = (f'🗳️ MATCH POLL | {v["ev"]} v {v["dep"]} · {_saat(v, ayar)}\n\nWho wins? Vote below 👇\n\n'
             f'Our numbers: {v["ev"]} {_pct(p["MS1"])} · draw {_pct(p["MSX"])} · {v["dep"]} {_pct(p["MS2"])}\n'
             f'Agree or not? Tell us why in the replies.' + _etiket(v))
    sure = datetime.fromisoformat(v["baslama"]) - datetime.fromisoformat(gun["_simdi"])
    dakika = max(5, min(10080, int(sure.total_seconds() // 60)))
    return metin, [_secenek(v["ev"]), "Draw", _secenek(v["dep"])], dakika


def olgular(tur: str, gun: dict, ayar) -> dict:
    """Direktöre verilen gerçekler: yalnızca bunlardan yazar."""
    def mac(v):
        return {"home": v["ev"], "away": v["dep"], "competition": v.get("lig"), "kickoff": _saat(v, ayar),
                "chances_home_draw_away": [round(v["p"][k], 2) for k in ("MS1", "MSX", "MS2")],
                "expected_goals_home_away": v["beklenen_gol"], "most_likely_score": v["olasi_skor"]}
    vit = gun.get("vitrin") or []
    if tur == "maclar":
        return {"date": gun["tarih"], "games": [mac(v) for v in vit[:4]]}
    if tur == "anket":
        return {"poll_options_fixed": ["home", "Draw", "away"], "game": mac(anket_maci(vit))}
    if tur == "ayrisma":
        return {"games": [{"match": f'{a["ev"]} v {a["dep"]}', "kickoff": _saat(a, ayar), "market": c["ad"],
                           "odds_chance": _pct(c["piyasa"]), "team_stats_chance": _pct(c["istatistik"])}
                          for a, c in kiyas_satirlari(gun)],
                "note": "odds = bookmaker prices with the margin removed; team stats = scoring averages. Always give "
                        "both percentages for each match. Ask who is right; no betting advice."}
    if tur == "bilgi":
        k = bilgi.gunun_konusu(gun["tarih"])
        return {"topic": k["baslik"], "facts_to_use": k["govde"], "question_idea": k["soru"],
                "accuracy_rule": "use only these facts and exactly these numbers; add no other number or claim"}
    return {"date": gun["tarih"]}


def bilgi_tweeti(gun: dict, kayma: int = 0) -> str:
    k = bilgi.gunun_konusu(gun["tarih"], kayma)
    return f'💡 {k["baslik"]}\n\n{k["govde"]}\n\n{k["soru"]}\n\n{ANSVAR}'


def _son_paylasim(gun: dict) -> datetime | None:
    zamanlar = [datetime.fromisoformat(e["zaman"]) for e in (gun.get("etkilesim") or {}).values()
                if e.get("durum") == "paylasildi" and e.get("zaman")]
    return max(zamanlar) if zamanlar else None


SAKIN_KART = 6  # SÖZLEŞME B7: büyük maç olmayan günde de en fazla bu kadar ek lig kartı
KART_PENCERESI = timedelta(hours=8)  # SÖZLEŞME B4: kart maçtan bu kadar önce paylaşılabilir (boşluk doldurur)
KART_ADIM = timedelta(minutes=20)  # yoğun günde en kötü post adımı: 13 dk aralık + 7 dk nabız
YAKIN_KART = timedelta(hours=4)  # bundan erken kart, sırada başka post yoksa çıkar


def _plan(gun: dict) -> list[tuple[str, datetime, datetime]]:
    """(tür, en erken, en geç) — sırayla; en geç geçtiyse o tür o gün atlanır."""
    plan = []
    vit = gun.get("vitrin") or []
    gun_bas = datetime.fromisoformat(gun["tarih"] + "T00:00:00+00:00")
    plan.append(("bilgi", gun_bas + timedelta(hours=9), gun_bas + timedelta(hours=19, minutes=30)))  # günlük bilgi
    # SÖZLEŞME B7: akşam (maçlar oynanırken, sonuçlardan önce) ikinci bilgi postu; akşam saatleri sessiz kalmasın
    plan.append(("bilgi_aksam", gun_bas + timedelta(hours=18), gun_bas + timedelta(hours=20, minutes=30)))
    if gun.get("hafta_ozeti"):  # SÖZLEŞME A9: Pazartesi, geçen haftanın karnesi (kayıttaki maç sonu postlarından)
        plan.append(("hafta", gun_bas + timedelta(hours=10), gun_bas + timedelta(hours=17)))
    if gun.get("konsept") == "analiz":
        # Kupon yok: günün maçları, öne çıkan maçların analiz kartları (maçtan 8 saat – 35 dk önce, en erken 08:00 UTC;
        # 15 dakikalık akışta öğleden önce boşluk kalmasın), anket.
        # Erken ilk maç (ör. Asya öğle maçı) sabit açılıştan önceyse pencere öne çekilir (en erken analiz anı),
        # yoksa pencere boş kalır ve post kaçar.
        olus = datetime.fromisoformat(gun["olusturma"]) if gun.get("olusturma") else gun_bas

        def _acilis(saat: int, ilk: datetime) -> datetime:
            return max(min(gun_bas + timedelta(hours=saat), ilk - timedelta(hours=2)), olus)

        if gun.get("tablo"):  # günün analiz tablosu (görsel): sabah, tablodaki ilk maçtan önce
            ilk = min(datetime.fromisoformat(a["baslama"]) for a in gun["tablo"])
            plan.append(("tablo", _acilis(8, ilk), ilk - timedelta(minutes=10)))
        if gun.get("tablo_gece"):  # sakin gün: gece maçlarının tablosu (B7, akşam sessiz kalmasın)
            ilk = min(datetime.fromisoformat(a["baslama"]) for a in gun["tablo_gece"])
            plan.append(("tablo_gece", gun_bas + timedelta(hours=GECE_TABLO_SAAT), ilk - timedelta(minutes=10)))
        if gun.get("tablo_aksam"):  # akşam maçlarının tablosu (hazırlandığı andan, ilk maçtan önce)
            ilk = min(datetime.fromisoformat(a["baslama"]) for a in gun["tablo_aksam"])
            plan.append(("tablo_aksam", gun_bas + timedelta(hours=12), ilk - timedelta(minutes=10)))
        elif vit:
            ilk = min(datetime.fromisoformat(v["baslama"]) for v in vit)
            plan.append(("maclar", ilk - timedelta(hours=5), ilk - timedelta(minutes=15)))
        # oran vs istatistik (ayrisma) postu 22 Ekim 2026'da kalktı (SÖZLEŞME A4)
        if vit:
            a = datetime.fromisoformat(anket_maci(vit)["baslama"])
            plan.append(("anket", a - timedelta(hours=3), a - timedelta(minutes=30)))
        kartlar = [(f"analiz_{i}", datetime.fromisoformat(a["baslama"])) for i, a in enumerate(gun.get("analizler") or [])]
        # 11 Ekim: aynı saatte başlayan çok kart 08:00'den sonraya sığmadı, biri kaçtı. Son saat sırasındaki k. post
        # en kötü k adımda çıkar; sığmıyorsa kart penceresi sabah analizinden itibaren öne çekilir (en çok 8 saat, B4).
        son_saatler = sorted([gec for _, _, gec in plan] + [b - timedelta(minutes=35) for _, b in kartlar])
        gerekli = min((gec - k * KART_ADIM for k, gec in enumerate(son_saatler, 1)), default=gun_bas)
        taban = max(min(gun_bas + timedelta(hours=8), gerekli), olus)
        for tur, b in kartlar:
            plan.append((tur, max(b - KART_PENCERESI, taban), b - timedelta(minutes=35)))
    return plan


TABLOLAR = ("tablo", "tablo_aksam", "tablo_gece")
GECE_TABLO_SAAT = 16  # SÖZLEŞME B7: sakin günde gece maçları tablosu bu saatten (UTC) sonra hazırlanır


def gece_tablosu_ekle(gun: dict, tum: list[dict], ayar, simdi: datetime) -> int:
    """Sakin günde 16:00 UTC'den sonra bir kez: sabah ve akşam tablolarında olmayan, en az 1 saat sonra başlayan
    maçların tablosu (en az 4 maç). Akşam saatleri sessiz kalmasın diye (B7); yoğun günde akşam tablosu zaten var."""
    if gun.get("konsept") != "analiz" or "tablo_gece" in gun or simdi.hour < GECE_TABLO_SAAT \
            or config.yogun_mu(ayar, gun["tarih"], gun):
        return 0
    haric = {a["fixture_id"] for a in (gun.get("tablo") or []) + (gun.get("tablo_aksam") or [])}
    liste = analiz.tablo_secimi(tum, ayar.ligler, en_erken=(simdi + timedelta(minutes=60)).isoformat(), haric=haric,
                                lig_basina=3)
    gun["tablo_gece"] = [analiz.ozet(a) for a in liste] if len(liste) >= 4 else []
    return len(gun["tablo_gece"])


def aksam_tablosu_ekle(gun: dict, tum: list[dict], ayar, simdi: datetime) -> int:
    """Bir kez: sabah tablosunda olmayan akşam maçlarının tablosu (en az 4 maç). Yoğun günde 16:00 UTC'den,
    sakin günde (öğleden sonra boşluk kalmasın, B7) 12:00 UTC'den. Paylaşımı ve maç sonu yanıtları sabah tablosu gibi."""
    acilis = 16 if config.yogun_mu(ayar, gun["tarih"], gun) else 12
    if gun.get("konsept") != "analiz" or "tablo_aksam" in gun or simdi.hour < acilis:
        return 0
    haric = {a["fixture_id"] for a in gun.get("tablo") or []}  # sabah tablosunda olmayanlar (kartlı da olabilir)
    liste = analiz.tablo_secimi(tum, ayar.ligler, en_erken=(simdi + timedelta(minutes=60)).isoformat(), haric=haric,
                                lig_basina=3)
    gun["tablo_aksam"] = [analiz.ozet(a) for a in liste] if len(liste) >= 4 else []
    return len(gun["tablo_aksam"])


def yogun_kartlari_ekle(gun: dict, tum: list[dict], ayar, simdi: datetime) -> int:
    """Kart listesi ek liglerin maçlarıyla genişler (kart penceresi kapanmamış olanlar): yoğun günde
    ayar.yogun_kart'a (günde en fazla 10), sakin günde SAKIN_KART'a kadar (SÖZLEŞME B4, B7: hesap sessiz kalmaz). Var olan
    kartların sırası değişmez (etkileşim kayıtları analiz_<sıra> ile tutulur); yeniler sona eklenir."""
    if gun.get("konsept") != "analiz":
        return 0
    analizler = gun.setdefault("analizler", [])
    tavan = ayar.yogun_kart if config.yogun_mu(ayar, gun["tarih"], gun) else SAKIN_KART
    yer = tavan - len(analizler)
    if yer <= 0:
        return 0
    yeni = analiz.ek_kart_secimi(tum, ayar.ligler, ayar.yogun_ek_ligler, {a["fixture_id"] for a in analizler},
                                 (simdi + timedelta(minutes=40)).isoformat(), yer)
    analizler.extend(yeni)
    return len(yeni)


class _TekrarKorumasi:
    """X spam kuralı: aynı metin iki kez paylaşılmaz. Bugünün kayıtlı post metinleriyle aynıysa gönderim reddedilir."""

    def __init__(self, x, gun: dict):
        self.x, self.gun = x, gun

    def __getattr__(self, ad):
        return getattr(self.x, ad)

    def gonder(self, metin: str, **k) -> str:
        eski = {e.get("metin") for e in (self.gun.get("etkilesim") or {}).values()}
        if metin.strip() in {m.strip() for m in eski if m}:
            raise RuntimeError("aynı metin bugün zaten paylaşıldı (tekrar engellendi)")
        return self.x.gonder(metin, **k)


def _gonder(x, ayar, metin: str, yaz, **k) -> str:
    """Topluluk ayarlıysa postu X Topluluğu'na (takipçilere de görünür) atar; olmazsa normal post."""
    tid = getattr(ayar, "topluluk_id", "")
    if tid:
        try:
            return x.gonder(metin, topluluk=tid, **k)
        except Exception as hata:
            yaz(f"⚠️ Topluluğa paylaşılamadı ({hata}); normal post atılıyor.")
    return x.gonder(metin, **k)


def _denetle(tur: str, metin: str, sablon: str, analizler: list[dict], ayar, png, yaz) -> str | None:
    """Denetçi (kod): direktörün metni geçmezse şablon denenir; o da geçmezse post çıkmaz (None) ve neden yazılır."""
    from . import denetci
    for aday in dict.fromkeys((metin, sablon)):
        hata = denetci.analiz_kontrolu(tur, aday, analizler, ayar, png)
        if not hata:
            return aday
        yaz(f"⚠️ Denetçi ({tur}) {'direktör metnini' if aday != sablon else 'şablonu'} durdurdu: " + " ".join(hata))
    return None


NABIZ_DK = 7  # nöbetçi botu en geç bu kadar dakikada bir çalıştırır


def _oncelik(gun: dict, simdi: datetime):
    """Paylaşım sırası anahtarı. Son paylaşım saati en yakın olan önce: maçtan önce çıkması gereken kart, gün boyu
    çıkabilen bilgi postu yüzünden kaçmasın (aralık kuralı yüzünden bir nabızda yalnızca bir post çıkar)."""
    def oncelik(t):  # büyük maçın kartı önce (SÖZLEŞME B6); diğer kartlar sıralamada 3 saat geride sayılır, ama
        tur, _, gec = t  # son saatine 1 saatten az kaldıysa geride sayılmaz (9 Ekim: bilgi postu kartı kaçırttı, B3).
        erken_kart = tur.startswith("analiz_") and simdi < gec + timedelta(minutes=35) - YAKIN_KART
        # Maça 4 saatten çok varsa kart ancak başka post yoksa (boşluk doldurur, maça yakın kalsın)
        if tur.startswith("analiz_") and gec - simdi > timedelta(hours=1):
            i = int(tur.split("_")[1])
            a = (gun.get("analizler") or [])[i] if i < len(gun.get("analizler") or []) else None
            if a is not None and not analiz.onemli(a):
                return erken_kart, gec + timedelta(hours=3)
        return erken_kart, gec
    return oncelik


def _paylasim_sirasi(gun: dict, ayar, simdi: datetime) -> list[tuple[str, datetime, datetime]]:
    """Planı paylaşım sırasına dizer: öncelikli post (büyük maç kartı, B6) ancak kalanların hepsi hâlâ son
    saatine yetişiyorsa öne geçer; yoksa son saati en yakın açık post çıkar (10 Ekim: iki büyük maç kartı öne
    geçince saati daha yakın bir kart kaçacaktı, B3)."""
    durum = gun.get("etkilesim") or {}
    sira = sorted(_plan(gun), key=_oncelik(gun, simdi))
    gecmis = [p for p in sira if p[0] not in durum and simdi > p[2]]
    acik = [p for p in sira if p[0] not in durum and p[1] <= simdi <= p[2]]
    if not acik:
        return sira
    en_az = getattr(ayar, "yogun_aralik_dk", ARALIK_DK) if config.yogun_mu(ayar, gun["tarih"], gun) else ARALIK_DK
    adim = timedelta(minutes=en_az + NABIZ_DK)  # en kötü durum: aralık doldu, sonraki nabız 7 dk sonra (10 Ekim: anket)
    bekleyen = sorted((p for p in sira if p[0] not in durum and p[2] > simdi), key=lambda p: p[2])

    def yetisir(aday):
        kalan = [gec for tur, _, gec in bekleyen if tur != aday[0]]
        return all(gec >= simdi + k * adim for k, gec in enumerate(kalan, 1))
    secilen = next((p for p in acik if yetisir(p)), min(acik, key=lambda p: p[2]))
    return gecmis + [secilen] + [p for p in sira if p is not secilen and p not in gecmis]


def aralik_dk(gun: dict, ayar, simdi: datetime) -> float:
    """Postlar arası dakika. Normal gün 45. Yoğun günde en az ayar.yogun_aralik_dk (~15 dk); sırada az post varsa
    kalanlar günün geri kalanına yayılır (öğlen hepsi tükenip akşam boş kalmasın), ama en fazla 45 dk, her post son
    saatine yetişecek kadar sık ve son saati 1 saatten yakın post varken hiç beklemeden en kısa aralık."""
    if not config.yogun_mu(ayar, gun["tarih"], gun):
        return ARALIK_DK
    en_az = getattr(ayar, "yogun_aralik_dk", ARALIK_DK)
    durum = gun.get("etkilesim") or {}
    kalan = sorted(gec for tur, _, gec in _plan(gun) if tur not in durum and gec > simdi)
    if not kalan or min(kalan) < simdi + timedelta(hours=1):
        return en_az
    yayilim = (max(kalan) - simdi).total_seconds() / 60 / len(kalan)
    # Yayılım son saatleri kaçırtmasın (9 Ekim: aynı saatte başlayan 9 kartın 6'sı kaçtı): son saat sırasındaki
    # k. post k aralık sonra çıkar ve kendi son saatine yetişmeli; nabız 7 dakikada bir olduğu için 7 dk pay.
    sikilik = min((gec - simdi).total_seconds() / 60 / k for k, gec in enumerate(kalan, 1)) - NABIZ_DK
    return max(en_az, min(yayilim, sikilik, ARALIK_DK))


def paylas(gun: dict, ayar, x, simdi: datetime, yaz=print, yazar=None) -> str | None:
    """Sıradaki etkileşim paylaşımını zamanı geldiyse atar (nabız başına en fazla bir tane).
    yazar: (tür, olgular, şablon) -> metin (X Direktörü); yoksa şablon."""
    durum = gun.setdefault("etkilesim", {})
    bugun_sayi = sum(1 for e in durum.values() if e.get("durum") == "paylasildi")
    if bugun_sayi >= getattr(ayar, "gunluk_post_siniri", 24):
        return None  # X spam kuralları: otomatik hesap günde makul sayıda post
    x = _TekrarKorumasi(x, gun)
    son = _son_paylasim(gun)
    if son and simdi < son + timedelta(minutes=aralik_dk(gun, ayar, simdi)):
        return None
    for tur, erken, gec in _paylasim_sirasi(gun, ayar, simdi):
        if tur in durum:
            continue
        if simdi > gec:
            durum[tur] = {"durum": "atlandi"}
            continue
        if simdi < erken:
            continue  # sıradaki türün saati gelmediyse, saati gelmiş bir sonraki tür beklemesin
        zaman = simdi.isoformat(timespec="seconds")
        try:
            if tur.startswith("analiz_"):
                a = gun["analizler"][int(tur.split("_")[1])]
                sablon = analiz_tweeti(a, ayar)
                metin = yazar("analiz", analiz_olgulari(a, ayar, sablon), sablon) if yazar else sablon
                if not metin:
                    durum[tur] = {"durum": "atlandi", "neden": "direktör"}
                    continue
                png = gorsel.analiz_karti(a, _saat(a, ayar), "en")
                metin = _denetle("analiz", metin, sablon, [a], ayar, png, yaz)
                if not metin:
                    durum[tur] = {"durum": "atlandi", "neden": "denetçi"}
                    continue
                tid = x.gonder(metin, medya=[x.medya_yukle(png)])  # kartlar topluluğa gitmez (günde 2 post sınırı)
            elif tur in TABLOLAR:  # sabah tablosu, akşam maçları tablosu ve (sakin günde) gece tablosu
                liste = [a for a in gun[tur] if datetime.fromisoformat(a["baslama"]) > simdi]
                if len(liste) < 4:
                    durum[tur] = {"durum": "atlandi", "neden": "yeterli maç kalmadı"}
                    continue
                sablon = tablo_tweeti(gun, liste, ayar)
                metin = yazar("tablo", tablo_olgulari(gun, liste, ayar), sablon) if yazar else sablon
                if not metin:
                    durum[tur] = {"durum": "atlandi", "neden": "direktör"}
                    continue
                png = gorsel.analiz_tablosu(liste, gun["tarih"], [_saat(a, ayar) for a in liste], "en")
                metin = _denetle("tablo", metin, sablon, liste, ayar, png, yaz)
                if not metin:
                    durum[tur] = {"durum": "atlandi", "neden": "denetçi"}
                    continue
                tid = _gonder(x, ayar, metin, yaz, medya=[x.medya_yukle(png)])
            elif tur == "ayrisma":
                sablon = ayrisma_tweeti(gun, ayar, simdi)
                if sablon is None:
                    durum[tur] = {"durum": "atlandi"}
                    continue
                metin = yazar(tur, olgular(tur, gun, ayar), sablon) if yazar else sablon
                if not metin:
                    durum[tur] = {"durum": "atlandi", "neden": "direktör"}
                    continue
                kiyas = kiyas_listesi(gun, simdi)
                png = (gorsel.kiyas_tablosu(kiyas, gun["tarih"], [_saat(a, ayar) for a in kiyas], "en")
                       if len(kiyas) >= 3 else None)
                metin = _denetle(tur, metin, sablon, (gun.get("kiyas") or []) + (gun.get("ayrisma") or []), ayar, png, yaz)
                if not metin:
                    durum[tur] = {"durum": "atlandi", "neden": "denetçi"}
                    continue
                tid = _gonder(x, ayar, metin, yaz, **({"medya": [x.medya_yukle(png)]} if png else {}))
            elif tur == "anket":
                metin, secenekler, dakika = anket({**gun, "_simdi": zaman}, ayar)
                metin = yazar(tur, olgular(tur, gun, ayar), metin) if yazar else metin
                tid = x.gonder(metin, anket={"options": secenekler, "duration_minutes": dakika})
            else:
                metin = {"bilgi": lambda: bilgi_tweeti(gun), "bilgi_aksam": lambda: bilgi_tweeti(gun, kayma=1),
                         "hafta": lambda: hafta_tweeti(gun["hafta_ozeti"]),
                         "maclar": lambda: maclar_tweeti(gun, ayar)}[tur]()
                if metin is None:  # içerik yok
                    durum[tur] = {"durum": "atlandi"}
                    continue
                sablon = metin
                if yazar and tur not in ("bilgi_aksam", "hafta"):  # akşam bilgisi onaylı şablonla, karne kayıttaki rakamla
                    metin = yazar(tur, olgular(tur, gun, ayar), metin)
                from .denetci import KISALTMA
                if metin and KISALTMA.search(metin):  # SÖZLEŞME A5: kısaltmalı metin yerine şablon (o da değilse atla)
                    metin = None if KISALTMA.search(sablon) else sablon
                if not metin:  # X Direktörü bugün bu paylaşımı uygun görmedi
                    durum[tur] = {"durum": "atlandi", "neden": "direktör"}
                    yaz(f"Etkileşim paylaşımı ({tur}): direktör bugün atlamayı seçti.")
                    continue
                tid = x.gonder(metin)
        except Exception as e:
            # Tekrar tekrar denenip hata yağmasın: bu tür bugün atlanır.
            durum[tur] = {"durum": "hata", "hata": str(e)[:300], "zaman": zaman}
            yaz(f"⚠️ Etkileşim paylaşımı ({tur}) başarısız: {e}")
            return None
        durum[tur] = {"durum": "paylasildi", "tweet_id": tid, "zaman": zaman, "metin": metin}
        if tur in TABLOLAR:  # maç sonu yanıtı için tablodaki maçlar
            durum[tur]["maclar"] = [a["fixture_id"] for a in liste]
        yaz(f"Etkileşim paylaşımı ({tur}):\n```\n{metin}\n```")
        return tur
    return None


# Maç başlamasından bu kadar sonra sonuç sorulmaya başlanır; maç bitmemişse sonraki nabızda tekrar sorulur
# (2 saat 15 dk beklemek maç sonu postunu düdükten ~40 dk sonraya bırakıyordu).
TAKIP_GECIKME = timedelta(hours=1, minutes=45)
def kart_sorusu(a: dict) -> str:
    """Kartın kapanış sorusu, o maçın kendi rakamlarıyla (genel "ne düşünüyorsun?" yerine belirli soru; X benzer
    postları geri plana atar). Maça göre sırayla değişir; yalnızca kartta olan yüzdeler kullanılır."""
    p = a["p"]
    fav_k = max(("MS1", "MS2"), key=lambda k: p[k])
    zayif_k = "MS2" if fav_k == "MS1" else "MS1"
    takim = {"MS1": a["ev"], "MS2": a["dep"]}
    skor, p_skor = a["skorlar"][0]
    sorular = [f"{takim[fav_k]} {_pct(p[fav_k])}: too high? 👇", "More or fewer than 2.5 goals? 👇",
               f"Can {takim[zayif_k]} beat {_pct(p[zayif_k])}? 👇", "What's your score? 👇"]
    return sorular[int(a.get("fixture_id") or 0) % len(sorular)]


def iki_tarafli(a: dict) -> list[str]:
    """Her pazar iki (sonuçta üç) tarafıyla: tek taraf yazılınca "seçimimiz" gibi okunuyordu. Kart seçim yapmaz,
    olasılık dağılımı verir."""
    p = a["p"]
    return [f'🏆 {a["ev"]} {_pct(p["MS1"])} · Draw {_pct(p["MSX"])} · {a["dep"]} {_pct(p["MS2"])}',
            f'⚽ Over 2.5 goals {_pct(p["UST25"])} · Under {_pct(p["ALT25"])}',
            f'🥅 Both teams score {_pct(p["KGVAR"])} · Not both {_pct(p["KGYOK"])}']


def mac_satiri(a: dict, bos: str = "🆚") -> str:
    """Postta maç satırı: takımların bayrağıyla (ülkesi biliniyorsa; taraftar kendi takımını hemen görür), yoksa bos."""
    from .tweets import bayrak
    b1, b2 = bayrak(a.get("ev_ulke")), bayrak(a.get("dep_ulke"))
    if b1 and b2:
        return f'{b1} {a["ev"]} v {a["dep"]} {b2}'
    return f'{bos} {a["ev"]} v {a["dep"]}'


def analiz_tweeti(a: dict, ayar) -> str:
    """Analiz kartıyla giden metin. İlk satırlar oranların hikâyesi (kartın manşetiyle aynı, analiz.hikaye, A10);
    sonra bayraklı maç satırı, üç pazar iki tarafıyla, maça özel soru. Takım istatistiği yok (A4); adil oran ve
    bahisçi payı yalnızca kartta (280 sınırı). Sığmazsa önce etiket, saat, "Chances," ve ikinci hikâye satırı
    düşer; maça özel soru en son (yanıtı o getirir)."""
    tur, h1, h2 = analiz.hikaye(a)
    mac = mac_satiri(a)
    tek = analiz.hikaye_tek(a)
    baslar = (f'{h1}\n{h2}\n\n{mac} · {_saat(a, ayar)}\n', f'{h1}\n{h2}\n\n{mac}\n', f'{tek}\n\n{mac}\n')
    govde = "\n".join(iki_tarafli(a))
    sorular = (kart_sorusu(a), "Your read? 👇")
    sonlar = ("\n\n💬 Chances, not picks. ", "\n\n💬 Not picks. ")
    etiket = _etiket(a)
    etiketler = dict.fromkeys((etiket, etiket.split(" ")[0] if etiket else "", ""))
    secenekler = [(son + q, et, bas) for q in sorular for bas in baslar for son in sonlar for et in etiketler]
    secenekler += [(son + q, et, f"{mac}\n") for q in sorular for son in sonlar for et in etiketler]  # son çare
    for son, et, bas in secenekler:
        metin = bas + govde + son + et + f"\n{ANSVAR}"
        if "not picks" in metin.lower() and uzunluk(metin) <= LIMIT:  # her kart postu seçim olmadığını söyler
            return metin
    metin, son = f"{mac}\n" + govde, sonlar[1] + sorular[1]
    while uzunluk(metin + son + f"\n{ANSVAR}") > LIMIT:
        metin = metin[:-1]
    return metin + son + f"\n{ANSVAR}"


def analiz_olgulari(a: dict, ayar, sablon: str | None = None) -> dict:
    # Hikâye: şablonun gerçekten açıldığı paragraf (yer darsa tek satırlık hali; direktor.hikaye_basta bununla denetler)
    hikaye = sablon.split("\n\n")[0].split("\n") if sablon and not sablon.startswith("🆚") else list(analiz.hikaye(a)[1:])
    return {"story": hikaye, "home": a["ev"], "away": a["dep"], "competition": a.get("lig"), "kickoff": _saat(a, ayar),
            "chances_both_sides": iki_tarafli(a),
            "framing": "probabilities, not picks: always give both sides of each market as in the template",
            "most_likely_score": f'{a["skorlar"][0][0]} ({_pct(a["skorlar"][0][1])})',
            "expected_goals": a["beklenen_gol"], "data_confidence": a["guven"],
            "note": "the image card shows every market; this text introduces it. No betting advice."}


def olan_sanslar(a: dict, ev: int, dep: int) -> list[dict]:
    """Maçta gerçekte ne oldu ve maçtan önce buna verdiğimiz yüzde: sonuç, 2.5 alt/üst, karşılıklı gol, skor.
    Bunlar tahmin/seçim değil olasılık: "tuttu/tutmadı" diye yazılmaz."""
    p = a["p"]
    if ev > dep:
        sonuc = ("MS1", f'{a["ev"]} win')
    elif dep > ev:
        sonuc = ("MS2", f'{a["dep"]} win')
    else:
        sonuc = ("MSX", "Draw")
    gol = ("UST25", "Over 2.5 goals") if ev + dep >= 3 else ("ALT25", "Under 2.5 goals")
    kg = ("KGVAR", "Both teams scored") if ev and dep else ("KGYOK", "Not both teams scored")
    skorlar = dict(analiz._skorlar(*a["beklenen_gol"], adet=200))
    return [{"emoji": "🏆", "ad": sonuc[1], "p": p[sonuc[0]]}, {"emoji": "⚽", "ad": gol[1], "p": p[gol[0]]},
            {"emoji": "🥅", "ad": kg[1], "p": p[kg[0]]},
            {"emoji": "🎯", "ad": f"Score {ev}-{dep}", "p": skorlar.get(f"{ev}-{dep}", 0.0)}]


def xg_metni(xg) -> str:
    """Maçın gerçek xG'si okunur halde ("1.4 – 0.9"); kısaltma yok (SÖZLEŞME A5)."""
    return f"{xg[0]:.1f} – {xg[1]:.1f}"


def surpriz_olcer(p: float) -> str:
    """Olan sonucun maç öncesi yüzdesi, sıklık diliyle (SÖZLEŞME A7): olgu, duygu iddiası değil."""
    if p < 0.35:
        return f"📉 Upset meter: {_pct(p)}, about a 1-in-{max(2, round(1 / max(p, 0.01)))} result"
    k, n = analiz.siklik(p)
    return f"🔎 That result had {_pct(p)} before kick-off, about {k} in {n}"


def analiz_takip_tweeti(a: dict, skor: str, isabet: list | None = None, xg=None) -> str:
    """Maç sonu alıntısı: bayraklı skor, sürpriz ölçer (olan sonucun maç öncesi yüzdesi, sıklık diliyle), (varsa)
    maçın gerçek xG'si, olanların maç öncesi yüzdeleri. Doğru/yanlış, ✅/❌, "seçimimiz" yok: kart seçim değil,
    olasılıktı."""
    ev, dep = (int(x) for x in skor.split("-"))
    olanlar = olan_sanslar(a, ev, dep)
    satir = [f'{o["emoji"]} {o["ad"]}: {_pct(o["p"]) if o["p"] >= 0.005 else "under 1%"}' for o in olanlar]
    xg_satiri = f"\n📐 Expected goals from shots: {xg_metni(xg)}" if xg else ""
    skor_satiri = mac_satiri(a, "⚽").replace(f' v {a["dep"]}', f' {ev}–{dep} {a["dep"]}', 1)
    olcer = "\n" + surpriz_olcer(olanlar[0]["p"])
    soru = "💬 Fair result on the chances created? 👇" if xg else "💬 Saw it coming? 👇"  # xG varsa soru onunla
    # Sığmazsa: önce açıklama, sonra başlık kısalır, sonra skor satırı, en son sürpriz ölçer; "not picks" hep kalır
    sonlar = ((True, f"\n\n💡 Chances, not picks. One match proves little.\n{soru}\n{ANSVAR}"),
              (True, f"\n\n💡 Chances, not picks.\n{soru}\n{ANSVAR}"), (True, f"\n\n💬 Not picks. {soru[2:]}\n{ANSVAR}"),
              (False, f"\n\nNot picks.\n{ANSVAR}"))
    basliklar = ("📊 Our pre-match chance of what happened:", "📊 Pre-match chances:")
    adaylar = [((not q, not o, len(satirlar) < 4, b != basliklar[0], i),
                f'🔁 FULL TIME\n{skor_satiri}{o}{xg_satiri}\n\n{b}\n' + "\n".join(satirlar) + son)
               for i, (q, son) in enumerate(sonlar) for o in (olcer, "") for b in basliklar for satirlar in (satir, satir[:3])]
    # öncelik: soru > sürpriz ölçer > skor satırı > uzun başlık > açıklama cümlesi; "not picks" hepsinde
    return ilk_sigan(*(m for _, m in sorted(adaylar, key=lambda x: x[0])))


def tablo_mac_sonu_tweeti(a: dict, ev: int, dep: int, aksam: bool = False) -> str:
    """Tablodaki bir maç bitince tablo postuna yanıt: skor, sürpriz ölçer ve olanların maç öncesi yüzdeleri
    (oranlardan; takım istatistiği yok, A4). Seçim dili yok."""
    olanlar = olan_sanslar(a, ev, dep)
    satirlar = [f'{o["emoji"]} {o["ad"]}: {_pct(o["p"]) if o["p"] >= 0.005 else "under 1%"}' for o in olanlar]
    mac = mac_satiri(a).replace(f' v {a["dep"]}', f' {ev}–{dep} {a["dep"]}', 1) + "\n"
    olcer = surpriz_olcer(olanlar[0]["p"]) + "\n\n"
    uzun = f"⚽ FULL TIME · from {'tonight' if aksam else 'this morning'}'s board\n" + mac + olcer + "📊 Our pre-match chance of what happened:\n"
    kisa = "⚽ FT · from today's board\n" + mac + "\n📊 Pre-match chance:\n"
    orta = "⚽ FT · from today's board\n" + mac + olcer + "📊 Pre-match chance:\n"
    adaylar = [uzun + "\n".join(satirlar) + "\n\n💬 Saw it coming? 👇", uzun + "\n".join(satirlar),
               orta + "\n".join(satirlar), orta + "\n".join(satirlar[:3]), kisa + "\n".join(satirlar),
               kisa + "\n".join(satirlar[:3])]
    return ilk_sigan(*(x + "\n" + ("" if x.endswith("👇") else "\n") + ANSVAR for x in adaylar))


# Tablo maç sonu yanıtları nabız başına en fazla 5: tablo en fazla 15 maç, aynı anda bitseler de hepsi 3 nabızda (~21 dk)
# çıkar (15 Ekim: 12 maç 21:00'de başladı, 3'er 3'er çıkınca sonuncusu 2,5 saat sınırını geçti, B2 alarmı geldi).
TABLO_NABIZ_YANIT = 5


def tablo_takibi(gun: dict, ayar, x, simdi: datetime, sonuc_getir, tum: list[dict] | None = None, yaz=print) -> int:
    """Günün tablosundaki (ve elle paylaşılan listedeki) her maç bittikçe tablo postuna yanıt: skor ve olanların
    maç öncesi yüzdeleri. Maç başlamasından 1 saat 50 dk sonra bakılmaya başlanır, 6 saat sonra vazgeçilir."""
    paylasilan = 0
    for tur, e in (gun.get("etkilesim") or {}).items():
        if not (tur == "tablo" or tur.startswith("tablo_")) or e.get("durum") != "paylasildi" or e.get("takip"):
            continue
        if e.get("maclar"):
            havuz = {a["fixture_id"]: a for a in (tum or []) + (gun.get("tablo") or [])}
            liste = [havuz[i] for i in e["maclar"] if i in havuz]
        elif tur == "tablo":
            liste = [a for a in gun.get("tablo") or [] if datetime.fromisoformat(a["baslama"]) > datetime.fromisoformat(e["zaman"])]
        else:
            e["takip"] = {"durum": "atlandi", "neden": "liste kaydı yok"}
            continue
        biten = e.setdefault("sonuclar", {})
        bekleyen = [a for a in liste if str(a["fixture_id"]) not in biten]
        for a in [a for a in bekleyen if simdi > datetime.fromisoformat(a["baslama"]) + timedelta(hours=6)]:
            biten[str(a["fixture_id"])] = {"durum": "atlandi", "neden": "sonuç gelmedi"}
        sorulacak = [a for a in bekleyen if datetime.fromisoformat(a["baslama"]) + timedelta(hours=1, minutes=50) < simdi
                     <= datetime.fromisoformat(a["baslama"]) + timedelta(hours=6)]
        sonuclar = sonuc_getir(sorulacak) if sorulacak else {}
        for a in sorulacak:
            if paylasilan >= TABLO_NABIZ_YANIT:
                break  # art arda yığılmasın (kalanlar sonraki nabızda)
            r = sonuclar.get(a["fixture_id"]) or {}
            if r.get("durum") == "iptal":
                biten[str(a["fixture_id"])] = {"durum": "atlandi", "neden": "maç oynanmadı"}
                continue
            if r.get("durum") != "bitti" or not a.get("beklenen_gol"):
                continue
            ev, dep = r["skor"]
            sablon = tablo_mac_sonu_tweeti(a, ev, dep, aksam=tur in ("tablo_aksam", "tablo_gece"))
            metin = _denetle("tablo_sonuc", sablon, sablon,
                             [], ayar, None, yaz)
            if not metin:
                biten[str(a["fixture_id"])] = {"durum": "atlandi", "neden": "denetçi"}
                continue
            try:
                tid = x.gonder(metin, yanit=e["tweet_id"])  # tablonun altında, zincirde
            except Exception as hata:
                biten[str(a["fixture_id"])] = {"durum": "hata", "hata": str(hata)[:300]}
                yaz(f"⚠️ Tablo maç sonu yanıtı paylaşılamadı: {hata}")
                continue
            biten[str(a["fixture_id"])] = {"durum": "paylasildi", "tweet_id": tid, "skor": [ev, dep],
                                           "zaman": simdi.isoformat(timespec="seconds")}
            yaz(f"Tablo maç sonu yanıtı:\n```\n{metin}\n```")
            paylasilan += 1
        if liste and all(str(a["fixture_id"]) in biten for a in liste):
            e["takip"] = {"durum": "tamam", "zaman": simdi.isoformat(timespec="seconds")}
    return paylasilan


def analiz_takibi(gun: dict, ayar, x, simdi: datetime, sonuc_getir, yaz=print, yazar=None, xg_getir=None) -> int:
    """Analiz kartı paylaşılan maç bitince kart postu alıntılanır: skor ve olanların maç öncesi yüzdeleri (doğru/yanlış
    dili yok; kart olasılıktı). İsabet ve Brier kaydı yalnızca iç kalibrasyon için saklanır."""
    paylasilan = 0
    for tur, e in (gun.get("etkilesim") or {}).items():
        if not tur.startswith("analiz_") or e.get("durum") != "paylasildi" or e.get("takip"):
            continue
        a = gun["analizler"][int(tur.split("_")[1])]
        baslama = datetime.fromisoformat(a["baslama"])
        if simdi < baslama + TAKIP_GECIKME:
            continue
        if simdi > baslama + timedelta(days=2):
            e["takip"] = {"durum": "atlandi", "neden": "sonuç gelmedi"}
            continue
        r = sonuc_getir([a]).get(a["fixture_id"]) or {}
        if r.get("durum") == "iptal":
            e["takip"] = {"durum": "atlandi", "neden": "maç oynanmadı"}
            continue
        if r.get("durum") != "bitti":
            continue
        ev, dep = r["skor"]
        skor = f"{ev}-{dep}"
        isabet = [bool(model.kazandi_mi(c["pazar"], ev, dep)) for c in analiz.manset(a)]
        xg = None
        if xg_getir:
            try:  # gerçek xG yoksa ya da alınamazsa post yine çıkar, yalnızca o satır olmaz
                xg = xg_getir(a)
            except Exception as hata:
                yaz(f"⚠️ Maç xG'si alınamadı ({a['ev']} v {a['dep']}): {hata}")
        sablon = analiz_takip_tweeti(a, skor, isabet, xg)
        metin = sablon
        if yazar:
            olg = {"score": skor, "home": a["ev"], "away": a["dep"],
                   "what_happened_and_its_pre_match_chance": [{"outcome": o["ad"], "chance": _pct(o["p"])}
                                                              for o in olan_sanslar(a, ev, dep)],
                   "note": "quote of our pre-match card. The card gave probabilities, not picks or predictions: never "
                           "say right, wrong, called it, our pick or ✅/❌. Say what happened and the chance it had."}
            if xg:
                olg["chances_created_expected_goals_home_away"] = xg_metni(xg)
                olg["note"] += (" Keep the chances-created line (expected goals from the shots, written in full, never "
                                "'xG'); you may compare it with the score in a few words.")
            metin = yazar("analiz_sonuc", olg, metin) or metin
            from .denetci import KISALTMA
            if KISALTMA.search(metin):  # SÖZLEŞME A5: "xG", "BTTS" gibi kısaltma yerine şablon
                metin = sablon
        metin = _denetle("analiz_sonuc", metin, sablon, [a], ayar, None, yaz)
        if not metin:
            e["takip"] = {"durum": "atlandi", "neden": "denetçi"}
            continue
        try:
            tid = x.gonder(metin, alinti=e["tweet_id"])
        except Exception as hata:
            e["takip"] = {"durum": "hata", "hata": str(hata)[:300]}
            yaz(f"⚠️ Analiz takibi paylaşılamadı: {hata}")
            continue
        brier = {"piyasa": 0.0, "istatistik": 0.0}
        for c in a.get("karsilastirma") or []:
            oldu = 1.0 if model.kazandi_mi(c["pazar"], ev, dep) else 0.0
            brier["piyasa"] += (c["piyasa"] - oldu) ** 2
            brier["istatistik"] += (c["istatistik"] - oldu) ** 2
        e["takip"] = {"durum": "paylasildi", "tweet_id": tid, "skor": skor, "isabet": isabet, **({"xg": list(xg)} if xg else {}),
                      "zaman": simdi.isoformat(timespec="seconds"),
                      **({"brier": {k: round(v, 4) for k, v in brier.items()}} if a.get("karsilastirma") else {})}
        yaz(f"Analiz takibi (alıntı):\n```\n{metin}\n```")
        paylasilan += 1
    return paylasilan


HAFTA_MIN = 30  # karne en az bu kadar maç sonu çağrısıyla (daha azı gürültü)


KALIBRASYON_MIN = 50  # bir bandın karnede yazılması için en az bu kadar çağrı
KALIBRASYON_PAZARLARI = ("MS1", "MSX", "MS2", "UST25", "ALT25", "KGVAR", "KGYOK")


def kalibrasyon(gunler: list[dict], son: str | None = None) -> list[dict]:
    """SÖZLEŞME A9: bütün kayıttaki oran yüzdelerimiz %10'luk bantlarda (kart ve tablo maçları, sonucu kayıtlı
    olanlar; tarih son'a kadar): bandın çağrı sayısı, ortalama yüzdemiz ve gerçekleşen oran. Kötüyse o da çıkar."""
    maclar: dict = {}
    for g in gunler:
        if g.get("konsept") != "analiz" or (son and g["tarih"] > son):
            continue
        e = g.get("etkilesim") or {}
        for tur, k in e.items():
            t = (k or {}).get("takip") or {}
            if tur.startswith("analiz_") and t.get("skor") and int(tur.split("_")[1]) < len(g.get("analizler") or []):
                a = g["analizler"][int(tur.split("_")[1])]
                maclar[a["fixture_id"]] = (a, tuple(int(x) for x in t["skor"].split("-")))
        for liste in ("tablo", "tablo_aksam", "tablo_gece"):
            ozetler = {a["fixture_id"]: a for a in g.get(liste) or [] if isinstance(a, dict)}
            for fid, sn in ((e.get(liste) or {}).get("sonuclar") or {}).items():
                if isinstance(sn, dict) and sn.get("skor") and int(fid) in ozetler:
                    maclar.setdefault(int(fid), (ozetler[int(fid)], tuple(sn["skor"])))
    bantlar: dict = {}
    for a, (ev, dep) in maclar.values():
        for k in KALIBRASYON_PAZARLARI:
            p = (a.get("p") or {}).get(k)
            if p is None:
                continue
            b = bantlar.setdefault(min(int(p * 10), 9), [0, 0, 0.0])
            b[0] += 1
            b[1] += bool(model.kazandi_mi(k, ev, dep))
            b[2] += p
    return [{"alt": 10 * b, "ust": 10 * b + 9, "adet": n, "ort_p": round(ps / n, 3), "olan": round(o / n, 3)}
            for b, (n, o, ps) in sorted(bantlar.items()) if n >= KALIBRASYON_MIN]


def hafta_ozeti(gunler: list[dict], tarih: str) -> dict | None:
    """SÖZLEŞME A9: tarihten önceki 7 günün karnesi, yalnızca paylaşılmış maç sonu postlarından (kayıtta ne varsa;
    olmayanlar da sayılır). Kartın üç ana çağrısı (analiz.manset): ortalama yüzdemiz ve kaçının olduğu; ve bütün
    kayıttan kalibrasyon (yüzde bantlarına göre dediğimiz ile olan)."""
    son = datetime.fromisoformat(tarih).date() - timedelta(days=1)
    ilk = son - timedelta(days=6)
    p_top = olan = adet = 0
    for g in gunler:
        if g.get("konsept") != "analiz" or not ilk.isoformat() <= g["tarih"] <= son.isoformat():
            continue
        for tur, e in (g.get("etkilesim") or {}).items():
            t = e.get("takip") or {}
            if not tur.startswith("analiz_") or t.get("durum") != "paylasildi" or not t.get("isabet"):
                continue
            for c, oldu in zip(analiz.manset(g["analizler"][int(tur.split("_")[1])]), t["isabet"]):
                p_top, olan, adet = p_top + c["p"], olan + bool(oldu), adet + 1
    if adet < HAFTA_MIN:
        return None
    return {"ilk": ilk.isoformat(), "son": son.isoformat(), "adet": adet, "olan": olan,
            "ort_p": round(p_top / adet, 3), "kalibrasyon": kalibrasyon(gunler, son.isoformat())}


def hafta_tweeti(oz: dict) -> str:
    """Pazartesi karnesi: bütün rakamlar kayıttan (hafta_ozeti); seçim/isabet dili yok, olanla yüzdemiz yan yana.
    Kalibrasyon: en çok çağrılı bantlar ("When we said 50–59%, it happened 55%")."""
    ilk, son = (datetime.fromisoformat(oz[k]) for k in ("ilk", "son"))
    aralik = f"{ilk:%-d}–{son:%-d %b}" if ilk.month == son.month else f"{ilk:%-d %b} – {son:%-d %b}"
    govde = [f"🎯 Our cards' main chances averaged {_pct(oz['ort_p'])}.",
             f"📈 Actually happened: {_pct(oz['olan'] / oz['adet'])} ({oz['olan']} of {oz['adet']})."]
    bantlar = sorted(oz.get("kalibrasyon") or [], key=lambda b: -b["adet"])
    kal = [f"{b['alt']}–{b['ust']}% → {_pct(b['olan'])} ({b['adet']} calls)"
           for b in sorted(bantlar[:3], key=lambda b: b["alt"])]
    for k in (len(kal), 2, 1, 0):
        for seffaf in ("\n\nEvery result is under its card, misses too.", ""):
            ek = ("\n\n⚖️ All season, said → happened:\n" + "\n".join(kal[:k])) if k else ""
            metin = (f"📊 OUR WEEK IN NUMBERS | {aralik}\n\n" + "\n".join(govde) + ek + seffaf
                     + "\n\n💬 Higher or lower than you expected? 👇\n" + ANSVAR)
            if uzunluk(metin) <= LIMIT:
                return metin
    return metin


def _vitrin_sirasi(a: dict) -> tuple:
    """Metinde önce taraftar etiketli (herkesin takip ettiği) takımların maçları, sonra saat sırası."""
    from .tweets import KULUP_ETIKETLERI, MILLI_ETIKETLER
    etiketli = sum(t.lower().strip() in MILLI_ETIKETLER or t.lower().strip() in KULUP_ETIKETLERI for t in (a["ev"], a["dep"]))
    return (-etiketli, a["baslama"])


def tablo_tweeti(gun: dict, liste: list[dict], ayar=None) -> str:
    """Liste postu. Kural (sabit tweetin sözü): metinde adı geçen HER maçın yüzdeleri de yazılır; yüzdesiz maç adı
    yok. Sığmazsa önce etiketler, sonra blok kısalır, sonra maç (rakamı değil, maçın kendisi) düşer. Tablonun tamamı
    (her maçın her yüzdesi) görseldedir."""
    n = gun.get("analiz_sayisi")
    basliklar = ((f"📋 Today's board: {len(liste)} from {n} analysed" if n else f"📋 Today's board: {len(liste)} matches")
                 + "\n📸 Chances, not picks: every % is in the image\n\n",
                 "📋 Today's chances, not picks · every % in the image\n\n")
    adaylar = [a for a in liste if a.get("p") and a.get("skorlar")]
    onemliler = sorted([a for a in adaylar if analiz.onemli(a)], key=_vitrin_sirasi) or adaylar[:1]
    soru = "💬 Which % surprises you? 👇\n\n"

    def blok(a: dict, seviye: int) -> str:
        sonuc, gol, kg = iki_tarafli(a)  # her pazar bütün taraflarıyla: tek taraf "seçim" gibi okunur
        skor, p_skor = a["skorlar"][0]
        if seviye == 4:  # en kısa: maç sonucunun üç tarafı (yine üç yüzde)
            return f'🆚 {a["ev"]} v {a["dep"]}\n{sonuc}\n\n'
        if seviye >= 2:  # kısa haller: saat (ve 3'te skor) görselde
            return (f'🆚 {a["ev"]} v {a["dep"]}\n{sonuc}\n{gol}\n'
                    + (f'🎯 Likeliest score {skor} ({_pct(p_skor)})\n' if seviye == 2 else "") + "\n")
        saat = f" · {_saat(a, ayar)}" if ayar else ""
        return (f'🆚 {a["ev"]} v {a["dep"]}{saat}\n{sonuc}\n{gol}\n' + (f'{kg}\n' if seviye == 0 else "")
                + f'🎯 Likeliest score {skor} ({_pct(p_skor)})\n\n')

    for adet in range(min(len(onemliler), 3), 0, -1):
        anilan = onemliler[:adet]
        # Etiketler yalnızca metinde adı geçen maçlardan (+ turnuva ve genel etiketler)
        etiketler = liste_etiketleri([(a.get("lig"), a.get("ulke")) for a in anilan], [(a["ev"], a["dep"]) for a in anilan])
        en_az = 1 if adet > 1 and etiketler else 0  # etiketsiz kalacaksa bir maç az ama etiketli
        for seviye in (0, 1, 2, 3, 4):
            govde = "".join(blok(a, seviye) for a in anilan)
            for k in range(len(etiketler), en_az - 1, -1):  # etiket, uzun başlıktan önemli
                for bas in basliklar:
                    metin = bas + govde + soru + (" ".join(etiketler[:k]) + "\n" if k else "") + ANSVAR
                    if uzunluk(metin) <= LIMIT:
                        return metin
    return basliklar[-1] + soru + ANSVAR


def tablo_olgulari(gun: dict, liste: list[dict], ayar) -> dict:
    return {"date": gun["tarih"], "matches_analysed_today": gun.get("analiz_sayisi"), "on_the_board": len(liste),
            "competitions": len({a["lig"] for a in liste}),
            "games": [{"match": f'{a["ev"]} v {a["dep"]}', "competition": a["lig"], "kickoff": _saat(a, ayar),
                       "home_draw_away": [_pct(a["p"][k]) for k in ("MS1", "MSX", "MS2")],
                       "over_2_5": _pct(a["p"]["UST25"]), "btts": _pct(a["p"]["KGVAR"]),
                       "most_likely_score": a["skorlar"][0][0]} for a in liste],
            "headline_games": [f'{a["ev"]} v {a["dep"]}' for a in sorted((a for a in liste if analiz.onemli(a)), key=_vitrin_sirasi)[:3]],
            "note": "the image shows the board; the text introduces it and names the headline games first"}


KIYAS_EMOJI = {"MS1": "🏆", "MSX": "🤝", "MS2": "🏆", "UST25": "⚽", "KGVAR": "🥅"}


def kiyas_satirlari(gun: dict, simdi: datetime | None = None, adet: int = 3) -> list[tuple[dict, dict]]:
    """Oran ile istatistiğin en çok ayrıştığı maç ve pazarlar: önce ikinci tablodaki (büyük) maçlar, yoksa eski
    ayrışma seçimi. Her maçtan bir satır."""
    kaynak = gun.get("kiyas") or gun.get("ayrisma") or []
    adaylar = [(a, (a.get("karsilastirma") or [None])[0]) for a in kaynak
               if simdi is None or datetime.fromisoformat(a["baslama"]) > simdi]
    adaylar = [(a, c) for a, c in adaylar if c]
    return sorted(adaylar, key=lambda x: -abs(analiz.fark_puani(x[1])))[:adet]


def kiyas_listesi(gun: dict, simdi: datetime) -> list[dict]:
    return [a for a in gun.get("kiyas") or [] if datetime.fromisoformat(a["baslama"]) > simdi]


def ayrisma_tweeti(gun: dict, ayar, simdi: datetime) -> str | None:
    """Oran vs takım istatistiği postu: aynı pazar için iki yüzde yan yana (ör. 2.5 üst: oran %53, istatistik %75).
    İkinci tablo (görsel) varsa metin onu tanıtır."""
    liste = kiyas_satirlari(gun, simdi)
    if len(liste) < 2:
        return None
    tablo = len(kiyas_listesi(gun, simdi))
    baslar = ([f"📊 ODDS vs TEAM STATS\n📸 {tablo} matches side by side in the image\n",
               f"📊 ODDS vs TEAM STATS\n📸 {tablo} matches in the image\n"] if tablo >= 3 else []) + ["📊 ODDS vs TEAM STATS\n"]
    satirlar = [f'🆚 {a["ev"]} v {a["dep"]}\n{KIYAS_EMOJI.get(c["pazar"], "📊")} {c["ad"]}: '
                f'💹 odds {_pct(c["piyasa"])} · 📈 stats {_pct(c["istatistik"])}' for a, c in liste]
    for n in range(len(satirlar), 1, -1):
        for bas in baslar:
            metin = (bas + "\n" + "\n\n".join(satirlar[:n])
                     + "\n\n💬 Who's right: the odds or the stats? 👇\n" + ANSVAR)
            if uzunluk(metin) <= LIMIT:
                return metin
    return None
