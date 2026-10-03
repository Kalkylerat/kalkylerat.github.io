"""Sağlık kontrolü ve alarm: bir post kaçtıysa, durduysa ya da hata verdiyse sahibine haber verilir.

Her nabızın sonunda çalışır. Yeni sorun varsa GitHub'da "alarm" etiketli bir issue açılır (aynı gün içinde yeni
sorunlar aynı issue'ya yorum olarak eklenir) ve sahibi etiketlenir: GitHub e-postası ve mobil bildirim gelir.
Aynı sorun iki kez bildirilmez (data/alarm.json)."""

import json
from datetime import datetime, timedelta

from . import config, etkilesim

DOSYA = config.DATA_FILE.parent / "alarm.json"
ETIKET = "alarm"
TAKIP_GECIKME = timedelta(hours=3, minutes=30)  # maç başlangıcından bu kadar sonra maç sonu postu hâlâ yoksa
DURGUNLUK = timedelta(minutes=20)  # yoğun günde, sırada post varken aralık + bu kadar sessizlik


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
            elif e.get("durum") == "atlandi" and not e.get("neden") and (tur.startswith("analiz_") or tur in ("tablo", "ayrisma")):
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
                    bulunan.append((anahtar + ":takip_gec", f'⏰ {ad}: maç bitti ama maç sonu postu hâlâ çıkmadı'))
    bugun = next((g for g in reversed(gunler) if g["tarih"] == gun_adi and g.get("konsept") == "analiz"), None)
    if bugun and config.yogun_mu(ayar, gun_adi):
        durum = bugun.get("etkilesim") or {}
        bekleyen = [tur for tur, erken, gec in etkilesim._plan(bugun) if tur not in durum and erken <= simdi <= gec]
        son = etkilesim._son_paylasim(bugun)
        if bekleyen and son and simdi - son > timedelta(minutes=ayar.yogun_aralik_dk) + DURGUNLUK:
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
