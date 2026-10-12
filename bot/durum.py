"""Saatlik sağlık kontrolü özeti (nöbet rutini için): python -m bot.durum

Bugünün etkileşim kaydını UTC saatleriyle yazar, sözleşme sapmalarını (kaçan post, geciken maç sonu postu, eksik
tablo sonucu, 3 saat sessizlik) listeler ve günün kalanını 7 dakikalık nabızla simüle edip kaçacak post var mı söyler.
Hiçbir şey paylaşmaz, dosyaya yazmaz. Son satır "SORUN YOK" ya da "SORUN: ..." olur."""

import copy
import json
from datetime import datetime, timedelta, timezone

from . import config, etkilesim, saglik


def _utc(z):
    return datetime.fromisoformat(z).astimezone(timezone.utc).strftime("%H:%M") if z else "-"


def simule_et(gun: dict, ayar, simdi: datetime) -> list[str]:
    """Günün kalanını nabız döngüsüyle oynatır; son saatini kaçıracak türleri döndürür."""
    g = copy.deepcopy(gun)
    g.setdefault("etkilesim", {})
    son = etkilesim._son_paylasim(g)
    bitis = simdi.replace(hour=23, minute=59)
    kacan = []
    while simdi < bitis:
        if son is None or simdi >= son + timedelta(minutes=etkilesim.aralik_dk(g, ayar, simdi)):
            for tur, erken, gec in etkilesim._paylasim_sirasi(g, ayar, simdi):
                if tur in g["etkilesim"] or simdi < erken:
                    continue
                if simdi > gec:
                    g["etkilesim"][tur] = {"durum": "atlandi"}
                    kacan.append(tur)
                    continue
                g["etkilesim"][tur] = {"durum": "paylasildi", "zaman": simdi.isoformat()}
                son = simdi
                break
        simdi += timedelta(minutes=etkilesim.NABIZ_DK)
    return kacan


def main(simdi: datetime | None = None) -> None:
    simdi = simdi or datetime.now(timezone.utc)
    ayar = config.yukle()
    gunler = json.loads(config.DATA_FILE.read_text(encoding="utf-8"))
    gun = gunler[-1]
    print(f"Şimdi {simdi:%Y-%m-%d %H:%M} UTC · son kayıt {gun['tarih']} ({gun.get('konsept')}) · "
          f"yoğun={config.yogun_mu(ayar, gun['tarih'], gun)} · kart={len(gun.get('analizler') or [])}")
    analizler = gun.get("analizler") or []
    for tur, e in sorted((gun.get("etkilesim") or {}).items(), key=lambda x: x[1].get("zaman") or ""):
        ek = ""
        if tur.startswith("analiz_") and int(tur.split("_")[1]) < len(analizler):
            a = analizler[int(tur.split("_")[1])]
            t = e.get("takip") or {}
            ek = f'{a["ev"]} v {a["dep"]} (başlama {_utc(a["baslama"])}) maç sonu={t.get("durum", "-")} {_utc(t.get("zaman"))}'
        if e.get("maclar"):
            s = e.get("sonuclar") or {}
            ek += f' sonuç {sum(r.get("durum") == "paylasildi" for r in s.values())}/{len(e["maclar"])}'
        print(f'  {_utc(e.get("zaman"))} {tur:12} {e.get("durum")} {e.get("neden", "")} {ek}')
    sorunlar = [m for _, m in saglik.sorunlar(gunler, simdi, ayar)]
    atlanan = [t for t, e in (gun.get("etkilesim") or {}).items() if e.get("durum") == "atlandi"]
    if atlanan:  # büyük maç dışı kaçan kart alarm üretmez ama sahibine söylenmeli
        sorunlar.append(f"atlanan postlar: {', '.join(atlanan)}")
    if gun["tarih"] == simdi.date().isoformat():
        kacacak = simule_et(gun, ayar, simdi)
        print(f"Simülasyon (günün kalanı): {'kaçacak: ' + ', '.join(kacacak) if kacacak else 'hepsi zamanında'}")
        if kacacak:
            sorunlar.append(f"simülasyona göre kaçacak: {', '.join(kacacak)}")
    else:
        print("Bugünün sabah analizi henüz yok (05:17 UTC'de yapılır).")
    sorunlar += likely_durumu(simdi)
    print("SORUN: " + " | ".join(sorunlar) if sorunlar else "SORUN YOK")


def likely_durumu(simdi: datetime) -> list[str]:
    """Mr. Likely (SOZLESME E): bugünün ve dünün kuponları planlanan saatte paylaşıldı mı, sonuç postu çıktı mı."""
    try:
        gunler = json.loads((config.DATA_FILE.parent / "likely.json").read_text(encoding="utf-8"))["gunler"]
    except (FileNotFoundError, ValueError, KeyError):
        return ["Mr. Likely kaydı (data/likely.json) okunamadı"]
    sorunlar = []
    for g in gunler[-2:]:
        bilgi = [_utc(b.get("zaman")) for b in g.get("bilgi") or [] if b.get("zaman")]
        print(f'Mr. Likely {g["tarih"]}: {g.get("durum")} · bilgi postları {", ".join(bilgi) or "-"}')
        for k in g.get("secilen") or []:
            print(f'  {k["ad"]}: {k.get("durum")} plan {_utc(k.get("paylas"))} paylaşıldı {_utc(k.get("yayin"))} '
                  f'sonuç postu {"var" if k.get("sonuc_tweet_id") else "-"}')
            if not k.get("tweet_id") and k.get("paylas") and \
                    simdi > datetime.fromisoformat(k["paylas"]) + timedelta(minutes=30):
                sorunlar.append(f'Mr. Likely {g["tarih"]} {k["ad"]}: planlanan saatten 30 dk geçti, kupon paylaşılmadı')
            if k.get("tweet_id") and k.get("durum") in ("tuttu", "yatti") and not k.get("sonuc_tweet_id"):
                sorunlar.append(f'Mr. Likely {g["tarih"]} {k["ad"]}: kupon sonuçlandı ama sonuç postu yok')
    return sorunlar


if __name__ == "__main__":
    main()
