"""Sağlık kontrolü ve alarm: bir post kaçtıysa, durduysa ya da hata verdiyse sahibine haber verilir.

Her nabızın sonunda çalışır. Yeni sorun varsa GitHub'da "alarm" etiketli bir issue açılır (aynı gün içinde yeni
sorunlar aynı issue'ya yorum olarak eklenir) ve sahibi etiketlenir: GitHub e-postası ve mobil bildirim gelir.
Aynı sorun iki kez bildirilmez (data/alarm.json)."""

import json
import re
from datetime import datetime, timedelta

from . import config, etkilesim

DOSYA = config.DATA_FILE.parent / "alarm.json"
ETIKET = "alarm"
# SÖZLEŞME (SOZLESME.md B1): maç sonu postu düdükten 5–15 dk sonra. Düdük ≈ başlama + 1 sa 55 dk; 25 dk pay.
TAHMINI_BITIS = timedelta(hours=1, minutes=55)
MAC_SONU_PAYI = timedelta(minutes=25)
TAKIP_GECIKME = TAHMINI_BITIS + MAC_SONU_PAYI
TABLO_SONUC_SINIR = timedelta(hours=2, minutes=30)  # tablodaki maçın sonucu yanıtı (B2)
_ETIKET = re.compile(r"#\w+")
from .denetci import KISALTMA as _KISALTMA
DURGUNLUK = timedelta(minutes=20)  # yoğun günde, sırada post varken aralık + bu kadar sessizlik


def _buyuk_kart(g: dict, tur: str) -> bool:
    from .analiz import onemli
    i = int(tur.split("_")[1])
    analizler = g.get("analizler") or []
    return i < len(analizler) and onemli(analizler[i])


def _sabah_gecti(simdi: datetime, ayar) -> bool:
    """Planlı sabah çalışmasından (yerel: hafta içi 12:47, hafta sonu 10:17) 1 saat geçti mi (SÖZLEŞME B5)."""
    from zoneinfo import ZoneInfo
    yerel = simdi.astimezone(ZoneInfo(ayar.saat_dilimi))
    bas = (12 * 60 + 47) if yerel.weekday() < 5 else (10 * 60 + 17)
    return yerel.hour * 60 + yerel.minute >= bas + 60


def sorunlar(gunler: list[dict], simdi: datetime, ayar, hatalar: list[str] = ()) -> list[tuple[str, str]]:
    """(anahtar, açıklama) listesi. Anahtar, aynı sorunun tekrar bildirilmemesi için."""
    bulunan = []
    gun_adi = simdi.date().isoformat()
    for h in hatalar:
        bulunan.append((f"{gun_adi}:hata:{h[:80]}", f"❌ Çalışma hatası: {h[:300]}"))
    for g in gunler[-2:]:
        durum = g.get("etkilesim") or {}
        for tur, e in durum.items():
            ad = tur
            if tur.startswith("analiz_") and g.get("analizler"):
                i = int(tur.split("_")[1])
                if i < len(g["analizler"]):
                    a = g["analizler"][i]
                    ad = f'kart {a["ev"]} v {a["dep"]}'
            anahtar = f'{g["tarih"]}:{tur}'
            if e.get("durum") == "hata":
                bulunan.append((anahtar + ":hata", f'❌ {g["tarih"]} {ad}: paylaşılamadı ({(e.get("hata") or "")[:200]})'))
            elif e.get("durum") == "atlandi" and e.get("neden") == "denetçi":
                bulunan.append((anahtar + ":denetci", f'🛑 {g["tarih"]} {ad}: denetçi durdurdu (kayıttaki rakamla uyuşmayan metin)'))
            elif e.get("durum") == "atlandi" and not e.get("neden") and (tur in ("tablo", "ayrisma") or (
                    tur.startswith("analiz_") and _buyuk_kart(g, tur))):  # büyük maçın kartı kaçmamalı (B6)
                bulunan.append((anahtar + ":kacti", f'⏰ {g["tarih"]} {ad}: paylaşım penceresi geçti, post çıkmadı '
                                                   f'(bot o saatlerde çalışmadı ya da sıra gelmedi)'))
            t = e.get("takip") or {}
            for fid, r in (e.get("sonuclar") or {}).items() if tur == "tablo" or tur.startswith("tablo_") else ():
                if r.get("durum") == "hata" or r.get("neden") == "denetçi":
                    bulunan.append((f"{anahtar}:{fid}:tablo_sonuc", f'❌ {g["tarih"]} {tur}: maç {fid} için tablo yanıtı '
                                                                   f'çıkmadı ({r.get("hata") or r.get("neden")})'))
            if tur.startswith("analiz_") and e.get("durum") == "paylasildi" and g.get("analizler"):
                a = g["analizler"][int(tur.split("_")[1])]
                if t.get("durum") == "hata":
                    bulunan.append((anahtar + ":takip_hata", f'❌ {ad}: maç sonu postu paylaşılamadı ({(t.get("hata") or "")[:200]})'))
                elif t.get("durum") == "atlandi" and t.get("neden") == "denetçi":
                    bulunan.append((anahtar + ":takip_denetci", f'🛑 {ad}: maç sonu postunu denetçi durdurdu'))
                elif not t and simdi > datetime.fromisoformat(a["baslama"]) + TAKIP_GECIKME:
                    bulunan.append((anahtar + ":takip_gec", f'⏰ {ad}: maç bitti ama maç sonu postu hâlâ çıkmadı '
                                                           f'(sözleşme: düdükten 5–15 dk sonra)'))
                elif t.get("durum") == "paylasildi" and t.get("zaman") and datetime.fromisoformat(t["zaman"]) > \
                        datetime.fromisoformat(a["baslama"]) + TAKIP_GECIKME:
                    dk = int((datetime.fromisoformat(t["zaman"]) - datetime.fromisoformat(a["baslama"])
                              - TAHMINI_BITIS).total_seconds() // 60)
                    bulunan.append((anahtar + ":takip_gecikti", f'⏰ {ad}: maç sonu postu düdükten ~{dk} dk sonra çıktı '
                                                               f'(sözleşme: 5–15 dk)'))
            if (tur == "tablo" or tur.startswith("tablo_")) and e.get("durum") == "paylasildi" and e.get("maclar"):
                havuz = {a["fixture_id"]: a for a in (g.get("tablo") or []) + (g.get("tablo_aksam") or [])}
                for fid in e["maclar"]:
                    a = havuz.get(fid)
                    if a and str(fid) not in (e.get("sonuclar") or {}) and \
                            simdi > datetime.fromisoformat(a["baslama"]) + TABLO_SONUC_SINIR:
                        bulunan.append((f"{anahtar}:{fid}:tablo_gec", f'⏰ {g["tarih"]} {tur}: {a["ev"]} v {a["dep"]} '
                                                                     f'bitti ama tablonun altına sonucu gelmedi'))
            metin = e.get("metin") or ""
            if e.get("durum") == "paylasildi" and metin:  # paylaşılan metin sözleşmeye uyuyor mu (A bölümü)
                from .denetci import _SECIM_DILI
                sinir = 2 if tur.startswith("tablo") else 1
                ihlal = ([f"{len(_ETIKET.findall(metin))} hashtag (en fazla {sinir})"] if len(_ETIKET.findall(metin)) > sinir else []) \
                    + (["seçim/tahmin dili"] if _SECIM_DILI.search(metin) else []) \
                    + (["kısaltma (O2.5/BTTS)"] if _KISALTMA.search(metin) else [])
                if ihlal:
                    bulunan.append((anahtar + ":kural", f'📏 {g["tarih"]} {ad}: paylaşılan metin sözleşme dışı: {", ".join(ihlal)}'))
    bugun = next((g for g in reversed(gunler) if g["tarih"] == gun_adi and g.get("konsept") == "analiz"), None)
    if ayar.konsept == "analiz" and not any(g["tarih"] == gun_adi for g in gunler) and _sabah_gecti(simdi, ayar):
        bulunan.append((f"{gun_adi}:sabah", "🌅 Bugünün sabah analizi yapılmadı (tablo, kartlar ve kit çıkmayacak)"))
    if bugun and config.yogun_mu(ayar, gun_adi):
        durum = bugun.get("etkilesim") or {}
        bekleyen = [tur for tur, erken, gec in etkilesim._plan(bugun) if tur not in durum and erken <= simdi <= gec]
        son = etkilesim._son_paylasim(bugun)
        if bekleyen and son and simdi - son > timedelta(minutes=etkilesim.aralik_dk(bugun, ayar, simdi)) + DURGUNLUK:
            dk = int((simdi - son).total_seconds() // 60)
            bulunan.append((f"{gun_adi}:durgun:{son.isoformat()}",
                            f"🔇 {dk} dakikadır post yok, sırada bekleyen var: {', '.join(bekleyen[:5])}"))
    return bulunan


def _yukle() -> dict:
    try:
        return json.loads(DOSYA.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def bildir(bulunan: list[tuple[str, str]], gh, kime: str, simdi: datetime, yaz=print) -> int:
    """Yeni sorunları GitHub issue'su olarak bildirir (günde bir issue, sonra yorum). Bildirilen sayısı."""
    kayit = _yukle()
    eski = set(kayit.get("bildirilen", []))
    yeni = [(k, m) for k, m in bulunan if k not in eski]
    if not yeni:
        return 0
    gun_adi = simdi.date().isoformat()
    saat = simdi.strftime("%H:%M UTC")
    govde = f"@{kime} bot alarmı ({saat}):\n\n" + "\n".join(f"- {m}" for _, m in yeni)
    if kayit.get("tarih") == gun_adi and kayit.get("issue"):
        gh.yorum(kayit["issue"], govde)
    else:
        kayit["issue"] = gh.issue_ac(f"⚠️ Kalkylerat alarmı {gun_adi}", govde, ETIKET)
        kayit["tarih"] = gun_adi
    kayit["bildirilen"] = sorted(eski | {k for k, _ in yeni})[-500:]
    DOSYA.write_text(json.dumps(kayit, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    yaz(f"🚨 Alarm bildirildi (issue #{kayit['issue']}):\n" + "\n".join(f"- {m}" for _, m in yeni))
    return len(yeni)
