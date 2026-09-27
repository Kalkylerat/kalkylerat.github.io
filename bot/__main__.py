"""Kullanım: python -m bot [otomatik|tahmin|yayinla|sonuc|panel|demo|tani]"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import config, editor, football, kayit, panel, tweets
from .model import adaylari_uret

ADAY_LIMIT = 12


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
        bahisciler = football.oranlari_al(api, m["fixture_id"])
        if not bahisciler:
            continue
        ist = football.istatistik_al(api, m["fixture_id"])
        if not ist:
            continue
        mac_adaylari = adaylari_uret(m, bahisciler, ist, ayar)
        if mac_adaylari:
            mac_map[m["fixture_id"]] = {**m, "istatistik": ist}
            adaylar += mac_adaylari
    adaylar = sorted(adaylar, key=lambda a: (a["adil_olasilik"], a["deger"]), reverse=True)[:ADAY_LIMIT]
    print(f"{len(adaylar)} aday, API isteği: {api.istek_sayisi}")

    gun = {"id": bugun, "tarih": bugun, "olusturma": simdi.isoformat(timespec="seconds"),
           "baslik": "", "secimler": [], "sonuc": None, "tweet_id": None}
    if adaylar:
        for fid in {a["fixture_id"] for a in adaylar}:
            mac_map[fid]["sakatlar"] = football.sakatlari_al(api, fid)
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
    for s in karar["secimler"]:
        a = aday_map[s["aday_id"]]
        m = mac_map[a["fixture_id"]]
        gun["secimler"].append({
            "fixture_id": a["fixture_id"], "lig": m["lig"], "ev": m["ev"], "dep": m["dep"],
            "baslama": m["baslama"], "pazar": a["pazar"], "etiket": a["etiket"], "kisa": a["kisa"], "oran": a["oran"],
            "bolag": a["bolag"], "adil_olasilik": a["adil_olasilik"], "adil_kaynak": a["adil_kaynak"],
            "model_olasilik": a["model_olasilik"], "deger": a["deger"], "yorum": s["yorum"].strip(),
            "durum": "bekliyor", "skor": None,
        })
    gun["secimler"].sort(key=lambda s: s["baslama"])
    gun["baslik"] = karar["baslik"].strip()
    gunler.append(gun)

    onizleme = "\n\n".join([tweets.gun_tweeti(gun, kayit.ozet(gunler))] + tweets.analiz_tweetleri(gun))
    _ozet_yaz(f"### {bugun} taslak\n```\n{onizleme}\n```")
    return gun


def yayinla(gun: dict, x, gunler: list[dict], simdi: datetime) -> bool:
    if gun.get("tweet_id") or not gun["secimler"]:
        return False
    ilk = min(datetime.fromisoformat(s["baslama"]) for s in gun["secimler"])
    if ilk <= simdi:
        print("İlk maç başlamış; şeffaflık için bu oyunlar artık yayınlanmaz.")
        return False
    gun["tweet_id"] = x.gonder(tweets.gun_tweeti(gun, kayit.ozet(gunler)))
    gun["yayin"] = simdi.isoformat(timespec="seconds")
    onceki = gun["tweet_id"]
    gun["analiz_tweet_idleri"] = []
    for metin in tweets.analiz_tweetleri(gun):
        onceki = x.gonder(metin, yanit=onceki)
        gun["analiz_tweet_idleri"].append(onceki)
    print(f"Yayınlandı: tweet {gun['tweet_id']}")
    return True


def sonuc(api, x, gunler: list[dict], simdi: datetime) -> None:
    ids = kayit.bekleyen_fixturelar(gunler, simdi)
    if not ids:
        print("Sonuç bekleyen maç yok.")
        return
    for g in kayit.sonuclandir(gunler, football.sonuclari_al(api, ids), simdi):
        print(f"{g['id']} sonuçlandı.")
        if g.get("tweet_id") and not g.get("sonuc_tweet_id"):
            g["sonuc_tweet_id"] = x.gonder(tweets.sonuc_tweeti(g, kayit.ozet(gunler)), yanit=g["tweet_id"])


def _x_client():
    return tweets.XClient(config.env("X_API_KEY"), config.env("X_API_SECRET"),
                          config.env("X_ACCESS_TOKEN"), config.env("X_ACCESS_SECRET"))


def _secici():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return editor.claude_ile_sec
    print("ANTHROPIC_API_KEY yok: kural tabanlı basit seçim kullanılıyor (yalnızca demo).")
    return editor.basit_sec


def tani(ayar) -> None:
    """Tweet atmadan tüm bağlantıları ve veri kapsamını kontrol eder."""
    import anthropic
    satirlar = ["### Tanı"]
    api = football.ApiFootball(config.env("API_FOOTBALL_KEY"))
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
        isvec = [a for a in adlar if a.lower() in {b.lower() for b in ayar.isvec_bahisciler}]
        satirlar.append(f"- Oran örneği ({ornek_fixture['ev']} – {ornek_fixture['dep']}): {len(adlar)} bahisçi; "
                        f"{ayar.keskin_bahisci} {'VAR' if keskin else 'YOK'}; İsveç lisanslı: {', '.join(isvec) or 'YOK'}")
        satirlar.append(f"  - Tüm bahisçiler: {', '.join(adlar) or '-'}")
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
        yayinla(gun, x, gunler, simdi)
        sonuc(api, x, gunler, simdi + timedelta(days=1))
    panel.olustur(gunler, ornek / "demo_panel.html")
    print(f"\nÖzet: {kayit.ozet(gunler)}\nPanel önizlemesi: ornek/demo_panel.html")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="bot")
    p.add_argument("komut", choices=["otomatik", "tahmin", "yayinla", "sonuc", "panel", "demo", "tani"])
    args = p.parse_args(argv)
    ayar = config.yukle()

    if args.komut == "demo":
        demo(ayar)
        return 0
    if args.komut == "tani":
        tani(ayar)
        return 0

    gunler = kayit.yukle(config.DATA_FILE)
    simdi = kayit.simdi_utc()
    bugun = simdi.astimezone(ZoneInfo(ayar.saat_dilimi)).date().isoformat()
    try:
        if args.komut in ("otomatik", "sonuc"):
            sonuc(football.ApiFootball(config.env("API_FOOTBALL_KEY")), _x_client(), gunler, simdi)
        if args.komut in ("otomatik", "tahmin"):
            api = football.ApiFootball(config.env("API_FOOTBALL_KEY"))
            gun = tahmin(ayar, api, _secici(), gunler, bugun, simdi)
            if gun and ayar.otomatik_paylas:
                yayinla(gun, _x_client(), gunler, simdi)
        if args.komut == "yayinla":
            gun = kayit.bul(gunler, bugun)
            if not gun or not yayinla(gun, _x_client(), gunler, simdi):
                print("Yayınlanacak bugünkü taslak yok.")
    finally:
        # Tweet atıldıktan sonra hata olsa bile kimlikler kaydedilir; tekrar paylaşım olmaz.
        kayit.kaydet(config.DATA_FILE, gunler)
        panel.olustur(gunler, config.PANEL_FILE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
