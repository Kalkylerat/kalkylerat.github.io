"""Mr. Likely canlı denetimi (SOZLESME G): her nabızda kayıt sahibinin ilkelerine göre taranır; sapma GitHub alarm
issue'su olarak sahibine gider (Kalkylerat'ın saglik.py'siyle aynı issue ve aynı "bir kez bildir" kaydı).

25 Ekim 2026'ya kadar Mr. Likely için canlı alarm yoktu: Barcelona v Real Madrid'in plandan düşmesi, sonuç postunun
30 saat beklemesi, kısaltılmış oyun adı ancak sahibi fark edince bulundu. Bu modül onları ve benzerlerini kendisi
yakalar. Yalnızca okur; X'e ve API'ye istek atmaz (maliyet yok)."""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import analiz, denetci
from .tweets import ANSVAR, LIMIT, uzunluk

PLAN_PAYI = timedelta(minutes=30)      # planlanan post bu kadar gecikirse alarm
SONUC_GECIKME = timedelta(hours=6)     # kuponun son maçı başlayalı bu kadar olduysa ve sonuç postu yoksa alarm
SONUC_PAYI = timedelta(minutes=30)     # kupon sonuçlandı (metni hazır) ama bu kadar süredir sonuç postu yoksa alarm
KISA = re.compile(r"(?<![\w.])(?:1X|X2|BTTS)(?![\w.])")
DOLU = ("gecti", "denetci", "tekrar", "uzun")  # tweet_id yerine yazılan "atılmadı" işaretleri


def dev_mac(a: dict) -> bool:
    """İki takımı da taraftar etiketli büyük kulüp ya da milli takım: El Clásico, derbi, büyük milli maç (SOZLESME G1)."""
    from .tweets import KULUP_ETIKETLERI, MILLI_ETIKETLER
    return all(t.lower().strip() in KULUP_ETIKETLERI or t.lower().strip() in MILLI_ETIKETLER for t in (a["ev"], a["dep"]))


def metin_ihlalleri(metin: str, onsekiz: bool = True) -> list[str]:
    """Paylaşılmış bir Mr. Likely metninin ortak kurallara aykırılıkları (G2–G4)."""
    ihlal = []
    if uzunluk(metin) > LIMIT:
        ihlal.append(f"{uzunluk(metin)} karakter")
    if denetci._SITE.search(metin):
        ihlal.append("bahis sitesi adı")
    if denetci._LINK.search(metin) or re.search(r"#\w", metin):
        ihlal.append("link/@/etiket")
    if denetci._KESINLIK.search(metin):
        ihlal.append("kesinlik dili")
    if denetci.KISALTMA.search(metin) or KISA.search(re.sub(r"Double chance (1X|X2|12)", "", metin)):
        ihlal.append("kısaltılmış oyun adı")
    if onsekiz and not metin.rstrip().splitlines()[-1].startswith("18+"):
        ihlal.append("18+ satırı yok")
    return ihlal


def _paylasilan_metinler(g: dict) -> list[tuple[str, str, bool]]:
    m = []
    for k in g.get("secilen", []):
        if k.get("tweet_id") and k.get("metin"):
            m.append((f'kupon {k["ad"]}', k["metin"], True))
        if k.get("sonuc_tweet_id") and k.get("sonuc_metni") and not g.get("toplu_sonuc"):
            m.append((f'sonuç {k["ad"]}', k["sonuc_metni"], True))
    m += [("tek sonuç postu", t["metin"], True) for t in g.get("toplu_sonuc", [])]  # E9
    for x in g.get("maclar", []):
        hikaye = x.get("hikaye_metin") or []
        if x.get("zaman") and x.get("metin"):  # flood'da 18+ yalnızca zincirin son postunda (25 Ekim 2026)
            m.append((f'maç {x["ev"]} v {x["dep"]}', x["metin"], not hikaye))
        m += [(f'hikaye {x["ev"]} v {x["dep"]}', t, i == len(hikaye) - 1) for i, t in enumerate(hikaye)]
    for b in g.get("bilgi", []):
        if b.get("zaman") and b.get("metin"):
            m.append((f'bilgi {b["tur"]}', b["metin"], True))
    if (g.get("duyuru") or {}).get("zaman"):
        m.append(("sabah duyurusu", g["duyuru"]["metin"], True))
    if (g.get("kasa") or {}).get("metin"):
        m.append(("kasa grafiği", g["kasa"]["metin"], True))
    return m


def sorunlar(veri: dict, analizler: list[dict], simdi: datetime, ayar, cfg) -> list[tuple[str, str]]:
    """(anahtar, açıklama): saglik.bildir ile aynı biçim. analizler: bugünün analiz kaydı (dev maç denetimi için)."""
    if not cfg.aktif or cfg.mod != "otomatik":
        return []
    tz = ZoneInfo(ayar.saat_dilimi)
    bugun = simdi.astimezone(tz).date().isoformat()
    bulunan = []
    for g in veri.get("gunler", [])[-2:]:
        t = g["tarih"]
        # G1: dev maç günün maçı postlarında (plan yapıldıysa)
        if t == bugun and g.get("oto") and "maclar" in g and cfg.oto_mac_sayisi:
            planli = {m["fixture_id"] for m in g["maclar"]}
            # Günde tek maç postunda (E9) yer bir dev maça gittiyse ikinci dev maç kaçmış sayılmaz
            dolu = len(planli) >= cfg.oto_mac_sayisi and any(dev_mac(a) and a["fixture_id"] in planli for a in analizler)
            for a in ([] if dolu else analizler):
                if dev_mac(a) and a.get("kaynak") == "piyasa" and a["fixture_id"] not in planli \
                        and datetime.fromisoformat(a["baslama"]) > simdi:
                    bulunan.append((f'{t}:likely:dev:{a["fixture_id"]}',
                                    f'🏟️ Mr. Likely {t}: dev maç {a["ev"]} v {a["dep"]} günün maçı postlarında yok'))
        # Kuponlar: zamanında paylaşıldı mı, sonuç postu çıktı mı, fiyat tek siteden mi
        for k in g.get("secilen", []):
            ad = f'Mr. Likely {t} {k["ad"]}'
            if k.get("oto") and not k.get("tweet_id") and k.get("paylas") and \
                    simdi > datetime.fromisoformat(k["paylas"]) + PLAN_PAYI:
                bulunan.append((f'{t}:likely:kupon:{k["ad"]}', f'⏰ {ad}: planlanan saatten 30 dk geçti, kupon paylaşılmadı'))
            if k.get("tweet_id") and not k.get("sonuc_tweet_id") and k.get("ayaklar"):
                son = max(datetime.fromisoformat(a["baslama"]) for a in k["ayaklar"])
                hazir = k.get("sonuc_hazir")
                from . import likely
                if hazir and k.get("sonuc_metni") and simdi > datetime.fromisoformat(hazir) + SONUC_PAYI and (
                        not cfg.oto_sonuc_tek or likely.tek_sonuc_hazir(g, simdi - SONUC_PAYI)):
                    # 28 Ekim 2026: sonuçlanan 4 kuponun postu 3 saat çıkmadı, 6 saatlik alarm gece yarısından sonraydı
                    bulunan.append((f'{t}:likely:sonuc_hazir:{k["ad"]}',
                                    f'⏰ {ad}: kupon sonuçlandı ({k["durum"]}) ama 30 dk\'dır sonuç postu çıkmadı'))
                elif simdi > son + SONUC_GECIKME:
                    bulunan.append((f'{t}:likely:sonuc:{k["ad"]}',
                                    f'⏰ {ad}: son maç başlayalı 6 saat oldu, sonuç postu hâlâ yok ({k["durum"]})'))
            if k.get("tweet_id") and t >= "2026-10-25" and cfg.oran_sitesi and any(
                    a.get("oran_kaynagi") != cfg.oran_sitesi for a in k["ayaklar"]):
                bulunan.append((f'{t}:likely:site:{k["ad"]}', f'💱 {ad}: ayak fiyatı {cfg.oran_sitesi} dışından'))
            for a in k.get("ayaklar", []):
                if a.get("sonucsuz") or a.get("ertelendi"):
                    bulunan.append((f'{t}:likely:ayak:{a["fixture_id"]}',
                                    f'ℹ️ {ad}: {a["ev"]} v {a["dep"]} sonucu gelmedi ya da ertelendi '
                                    f'({"postponed, void" if a.get("ertelendi") else "no result yet"} yazıldı)'))
        if g.get("kacan"):
            for x in g["kacan"]:
                bulunan.append((f'{t}:likely:kacan:{x["ad"]}', f'⏰ Mr. Likely {t} {x["ad"]}: zamanında paylaşılamadı, atlandı'))
        # Sabah duyurusu: kupon paylaşıldıysa duyuru gitmiş olmalı
        if t >= "2026-10-25" and g.get("oto") and any(k.get("tweet_id") for k in g.get("secilen", [])) and \
                not str((g.get("duyuru") or {}).get("tweet_id") or "").isdigit():
            bulunan.append((f'{t}:likely:duyuru', f'📣 Mr. Likely {t}: sabah duyurusu gitmedi ({(g.get("duyuru") or {}).get("tweet_id", "yok")})'))
        # Günün maçı postları ve hikaye flood'u
        for m in g.get("maclar", []):
            ad = f'Mr. Likely {t} maç {m["ev"]} v {m["dep"]}'
            if m.get("tweet_id") in DOLU:
                bulunan.append((f'{t}:likely:mac:{m["fixture_id"]}', f'🛑 {ad}: atılmadı ({m["tweet_id"]})'))
            elif not m.get("tweet_id") and simdi > datetime.fromisoformat(m.get("baslama") or m["saat"]) - timedelta(minutes=25):
                # maç postu başka bir posta yer açmak için kayabilir; alarm yalnızca kaçtıysa (son saat: maçtan 30 dk önce)
                bulunan.append((f'{t}:likely:mac:{m["fixture_id"]}', f'⏰ {ad}: maç başlamak üzere, post paylaşılmadı (kaçtı)'))
            elif m.get("hikaye") and m.get("zaman") and not m.get("hikaye_ids"):
                bulunan.append((f'{t}:likely:hikaye:{m["fixture_id"]}', f'ℹ️ {ad}: hikaye flood\'u çıkmadı (veri alınamadı), tek post gitti'))
        # Kasa grafiği: kupon günü bitince, en geç ertesi sabah
        duyuru = (veri.get("kasa_duyuru") or {}).get("tarih")
        if cfg.oto_kasa and duyuru and t >= duyuru and any(k.get("tweet_id") for k in g.get("secilen", [])):
            son_an = datetime.fromisoformat(t).replace(tzinfo=tz) + timedelta(days=1, hours=9, minutes=30)
            kasa = g.get("kasa") or {}
            if kasa.get("tweet_id") in DOLU:
                bulunan.append((f'{t}:likely:kasa', f'🛑 Mr. Likely {t}: kasa grafiği atılmadı ({kasa["tweet_id"]})'))
            elif not kasa and simdi > son_an:
                bulunan.append((f'{t}:likely:kasa', f'⏰ Mr. Likely {t}: kasa grafiği ertesi sabah 09:30\'a kadar çıkmadı'))
        # G2–G4: paylaşılmış her metin kurallara uyuyor mu
        for ne, metin, onsekiz in _paylasilan_metinler(g):
            ihlal = metin_ihlalleri(metin, onsekiz)
            if ihlal:
                bulunan.append((f'{t}:likely:metin:{ne}', f'📏 Mr. Likely {t} {ne}: paylaşılan metin kural dışı: {", ".join(ihlal)}'))
    return bulunan


def plan_ozeti(gun: dict, analizler: list[dict], ayar) -> list[str]:
    """Sabah bildirimine: bugünün dev ve büyük maçları nerede (maç postu saati, kupon). Sahibi sabah görür."""
    tz = ZoneInfo(ayar.saat_dilimi)
    maclar = {m["fixture_id"]: m for m in gun.get("maclar", [])}
    kupon = {a["fixture_id"]: k["ad"] for k in gun.get("secilen", []) for a in k["ayaklar"]}
    satir = []
    for a in sorted((a for a in analizler if analiz.onemli(a)), key=lambda a: (not dev_mac(a), a["baslama"])):
        m = maclar.get(a["fixture_id"])
        yer = (f'maç postu {datetime.fromisoformat(m["saat"]).astimezone(tz).strftime("%H:%M")}'
               + (" (Match of the day)" if m.get("gunun_maci") else "") + (" + hikaye" if m.get("hikaye") else "")
               if m else "maç postu YOK")
        yer += f' · kupon: {kupon[a["fixture_id"]]}' if a["fixture_id"] in kupon else " · kuponda yok"
        satir.append(f'{"🏟️ " if dev_mac(a) else ""}{a["ev"]} v {a["dep"]}: {yer}')
    return satir


def canli(ayar, simdi: datetime) -> list[tuple[str, str]]:
    """Nabızdan ve nöbet kontrolünden çağrılır: kayıt ve bugünün analizi okunur. Hata paylaşımı durdurmaz, sessiz de kalmaz."""
    import json
    from . import config, likely
    try:
        bugun = simdi.astimezone(ZoneInfo(ayar.saat_dilimi)).date().isoformat()
        dosya = config.ROOT / "data" / "analiz" / f"{bugun}.json"
        analizler = json.loads(dosya.read_text(encoding="utf-8")) if dosya.exists() else []
        return sorunlar(likely.yukle(), analizler, simdi, ayar, likely.ayar_yukle())
    except Exception as e:
        return [(f"{simdi.date()}:likely:denetim:{str(e)[:60]}", f"⚠️ Mr. Likely canlı denetimi çalışmadı: {e}")]
