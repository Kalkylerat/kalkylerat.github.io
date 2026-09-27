"""Kullanım: python -m bot [otomatik|tahmin|yayinla|sonuc|panel|demo|tani|onizleme]"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import config, editor, football, kayit, panel, tweets
from .model import adaylari_uret, bet_builder, kombi_kur

GUVENLI_LIMIT = 10
DEGER_LIMIT = 6


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
    maclar = football.gunun_maclari(api, bugun, ayar.ligler, ayar.saat_dilimi,
                                    ayar.min_dakika_once, ayar.max_mac_tarama, simdi)
    print(f"{len(maclar)} uygun maç bulundu.")
    mac_map, adaylar = {}, []
    for m in maclar:
        try:
            bahisciler = football.oranlari_al(api, m["fixture_id"])
            ist = football.istatistik_al(api, m["fixture_id"]) if bahisciler else None
        except football.ApiHatasi as e:
            # Günlük istek sınırı dolarsa o ana kadar taranan maçlarla devam edilir.
            print(f"Tarama erken bitti: {e}")
            break
        if not bahisciler or not ist:
            continue
        mac_adaylari = adaylari_uret(m, bahisciler, ist, ayar)
        if mac_adaylari:
            mac_map[m["fixture_id"]] = {**m, "istatistik": ist}
            adaylar += mac_adaylari
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
        karar = sec(mac_map, adaylar, ayar)
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
    for s in karar["secimler"]:
        a = aday_map[s["aday_id"]]
        m = mac_map[a["fixture_id"]]
        gun["secimler"].append({
            "fixture_id": a["fixture_id"], "lig": m["lig"], "ev": m["ev"], "dep": m["dep"],
            "baslama": m["baslama"],
            "saat": datetime.fromisoformat(m["baslama"]).astimezone(ZoneInfo(ayar.saat_dilimi)).strftime("%H:%M %Z"),
            "olasi_skor": a["olasi_skor"], "pazar": a["pazar"], "tur": a["tur"], "etiket": a["etiket"],
            "kisa": a["kisa"], "oran": a["oran"], "stake": stake,
            "bolag": a["bolag"], "adil_olasilik": a["adil_olasilik"], "adil_kaynak": a["adil_kaynak"],
            "model_olasilik": a["model_olasilik"], "deger": a["deger"], "beklenen_gol": a["beklenen_gol"],
            "yorum": s["yorum"].strip(), "durum": "bekliyor", "skor": None,
        })
    gun["secimler"] = bet_builder_birlestir(gun["secimler"])
    gun["secimler"].sort(key=lambda s: s["baslama"])
    ayaklar = kombi_kur(gun["secimler"], ayar)
    if ayaklar:
        gun["kombi"] = {"ayaklar": ayaklar, "stake": stake, "durum": None}
    gun["baslik"] = karar["baslik"].strip()
    gunler.append(gun)

    taslak = "\n\n".join([tweets.gun_tweeti(gun, kayit.ozet(gunler, ayar.kasa_baslangic))] + tweets.analiz_tweetleri(gun))
    _ozet_yaz(f"### {bugun} taslak\n```\n{taslak}\n```")
    return gun


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
            **{k: ilk[k] for k in ("fixture_id", "lig", "ev", "dep", "baslama", "saat", "olasi_skor", "stake", "beklenen_gol")},
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


def yayinla(ayar, gun: dict, x, gunler: list[dict], simdi: datetime) -> bool:
    if gun.get("tweet_id") or not gun["secimler"]:
        return False
    ilk = min(datetime.fromisoformat(s["baslama"]) for s in gun["secimler"])
    if ilk <= simdi:
        print("İlk maç başlamış; şeffaflık için bu oyunlar artık yayınlanmaz.")
        return False
    gun["tweet_id"] = x.gonder(tweets.gun_tweeti(gun, kayit.ozet(gunler, ayar.kasa_baslangic)))
    gun["yayin"] = simdi.isoformat(timespec="seconds")
    onceki = gun["tweet_id"]
    gun["analiz_tweet_idleri"] = []
    for metin in tweets.analiz_tweetleri(gun):
        onceki = x.gonder(metin, yanit=onceki)
        gun["analiz_tweet_idleri"].append(onceki)
    print(f"Yayınlandı: tweet {gun['tweet_id']}")
    return True


def sonuc(ayar, api, x, gunler: list[dict], simdi: datetime) -> None:
    ids = kayit.bekleyen_fixturelar(gunler, simdi)
    if not ids:
        print("Sonuç bekleyen maç yok.")
        return
    sonuclar = football.sonuclari_al(api, ids, kayit.korner_fixturelari(gunler))
    for g in kayit.sonuclandir(gunler, sonuclar, simdi):
        print(f"{g['id']} sonuçlandı.")
        if g.get("tweet_id") and not g.get("sonuc_tweet_id"):
            ozet = kayit.ozet(gunler, ayar.kasa_baslangic)
            g["sonuc_tweet_id"] = x.gonder(tweets.sonuc_tweeti(g, ozet), yanit=g["tweet_id"])


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
        r = _x_client().session.get("https://api.x.com/2/users/me", timeout=30)
        satirlar.append(f"- X: {r.status_code} {r.json().get('data', {}).get('username') or r.text[:200]}")
    except Exception as e:
        satirlar.append(f"- X hatası: {e}")
    try:
        m = anthropic.Anthropic().models.retrieve(ayar.claude_model)
        satirlar.append(f"- Anthropic: model {m.id} erişilebilir")
    except Exception as e:
        satirlar.append(f"- Anthropic hatası: {e}")
    _ozet_yaz("\n".join(satirlar))


def demo(ayar) -> None:
    ornek = config.ROOT / "ornek"
    api = football.DemoApi(ornek / "api_football.json")
    simdi = datetime.fromisoformat(api.data["simdi"])
    bugun = simdi.astimezone(ZoneInfo(ayar.saat_dilimi)).date().isoformat()
    gunler: list[dict] = []
    x = tweets.KonsolClient()
    gun = tahmin(ayar, api, _secici(), gunler, bugun, simdi)
    if gun:
        yayinla(ayar, gun, x, gunler, simdi)
        sonuc(ayar, api, x, gunler, simdi + timedelta(days=1))
    panel.olustur(gunler, ornek / "demo_panel.html", ayar)
    print(f"\nÖzet: {kayit.ozet(gunler, ayar.kasa_baslangic)}\nPanel önizlemesi: ornek/demo_panel.html")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="bot")
    p.add_argument("komut", choices=["otomatik", "tahmin", "yayinla", "sonuc", "panel", "demo", "tani", "onizleme"])
    args = p.parse_args(argv)
    ayar = config.yukle()

    if args.komut == "demo":
        demo(ayar)
        return 0
    if args.komut == "tani":
        tani(ayar)
        return 0
    if args.komut == "onizleme":
        onizleme(ayar)
        return 0

    gunler = kayit.yukle(config.DATA_FILE)
    simdi = kayit.simdi_utc()
    bugun = simdi.astimezone(ZoneInfo(ayar.saat_dilimi)).date().isoformat()
    try:
        if args.komut in ("otomatik", "sonuc"):
            sonuc(ayar, _api(ayar), _x_client(), gunler, simdi)
        if args.komut in ("otomatik", "tahmin"):
            gun = tahmin(ayar, _api(ayar), _secici(), gunler, bugun, simdi)
            if gun and ayar.otomatik_paylas:
                yayinla(ayar, gun, _x_client(), gunler, simdi)
        if args.komut == "yayinla":
            gun = kayit.bul(gunler, bugun)
            if not gun or not yayinla(ayar, gun, _x_client(), gunler, simdi):
                print("Yayınlanacak bugünkü taslak yok.")
    finally:
        # Tweet atıldıktan sonra hata olsa bile kimlikler kaydedilir; tekrar paylaşım olmaz.
        kayit.kaydet(config.DATA_FILE, gunler)
        panel.olustur(gunler, config.PANEL_FILE, ayar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
