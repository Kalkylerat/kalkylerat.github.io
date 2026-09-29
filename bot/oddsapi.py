"""The Odds API (the-odds-api.com): API-Football çalışmadığında yedek oran ve sonuç kaynağı.

Ücretsiz plan ayda 500 kredi. Lig ve maç listesi (sports, events) kredi harcamaz; oran isteği pazar × bölge
başına 1 kredi (h2h + totals, "eu" bölgesi = 2 kredi / lig), sonuç isteği (daysFrom ile) 2 kredi / lig.
Bu kaynakta takım istatistiği yok: beklenen goller piyasanın (maç sonucu + 2,5 gol) adil ihtimallerinden çıkarılır."""

import math
import re
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from . import model

BASE_URL = "https://api.the-odds-api.com/v4"
BOLGE = "eu"  # Pinnacle + William Hill, BetVictor, Unibet, 888Sport, Betsson, NordicBet
PAZARLAR = "h2h,totals"
# Bahisçi anahtarı -> ayarlar.toml'daki ad (oran_bahiscileri ve keskin bahisçi bu adlarla eşleşir)
BAHISCI_ADLARI = {
    "pinnacle": "Pinnacle", "williamhill": "William Hill", "betvictor": "BetVictor", "unibet_eu": "Unibet",
    "sport888": "888Sport", "betsson": "Betsson", "nordicbet": "NordicBet", "betway": "Betway",
}
# Ayarlar.toml'daki izinli liglerin karşılığı (öncelik sırası). Listede olmayan ligler Pinnacle şartıyla taranır.
IZINLI_SPORLAR = [
    "soccer_epl", "soccer_spain_la_liga", "soccer_italy_serie_a", "soccer_germany_bundesliga", "soccer_france_ligue_one",
    "soccer_uefa_champs_league", "soccer_uefa_europa_league", "soccer_uefa_europa_conference_league",
    "soccer_uefa_nations_league", "soccer_efl_champ", "soccer_germany_bundesliga2", "soccer_italy_serie_b",
    "soccer_spain_segunda_division", "soccer_france_ligue_two", "soccer_netherlands_eredivisie",
    "soccer_portugal_primeira_liga", "soccer_belgium_first_div", "soccer_spl", "soccer_turkey_super_league",
    "soccer_sweden_allsvenskan", "soccer_norway_eliteserien", "soccer_denmark_superliga",
    "soccer_austria_bundesliga", "soccer_switzerland_superleague", "soccer_england_league1",
    "soccer_sweden_superettan",
]
_GUVENILMEZ = re.compile(r"friendl|women|youth|u1[6-9]\b|u2[0-3]\b|reserve", re.IGNORECASE)
# Aylık 500 kredinin korunması: tarama başına en fazla bu kadar kredi, ve sonuçlar için hep bu kadar kredi kalır.
MAX_TARAMA_KREDISI = 20
# Yüksek ihtimalli pazarlar (çifte şans, 1,5 üst/alt, karşılıklı gol) yalnızca maç başına istenebilir:
# maç başına 3 kredi; favorisi en belirgin (ya da gol beklentisi en uç) en fazla EK_MAC maç için.
# Aylık 500 kredi: günde ~2-6 (lig oranları) + 9 (ek pazar) + 2-4 (sonuç) ≈ 400-450.
EK_PAZARLAR = "double_chance,alternate_totals,btts"
EK_MAC = 3
YEDEK_KREDI = 40


class OddsApiHatasi(RuntimeError):
    pass


def fixture_id(odds_id: str) -> int:
    """Kayıtta ve Claude şemasında tamsayı kimlik kullanılır; The Odds API kimliğinden (onaltılık) türetilir.
    48 bit: JavaScript'te de güvenli, API-Football kimlikleriyle (milyonlar) çakışmaz."""
    return int(odds_id[:12], 16)


class OddsApi:
    def __init__(self, key: str, session: requests.Session | None = None, aralik: float = 1.2, uyku=time.sleep):
        self.key = key
        self.session = session or requests.Session()
        self.kalan: int | None = None
        self.harcanan = 0
        self.aralik = aralik
        self.uyku = uyku
        self._son = 0.0

    def get(self, path: str, **params):
        # Ücretsiz plan art arda isteklere 429 ("Requests are too frequent") döner: istekler aralıklı atılır,
        # 429 gelirse artan beklemeyle tekrar denenir.
        for deneme in range(5):
            bekle = self.aralik - (time.monotonic() - self._son)
            if bekle > 0:
                self.uyku(bekle)
            r = self.session.get(f"{BASE_URL}/{path}", params={"apiKey": self.key, **params}, timeout=30)
            self._son = time.monotonic()
            if r.status_code != 429 or deneme == 4:
                break
            self.uyku(2 * (deneme + 1))
        if r.headers.get("x-requests-remaining") is not None:
            self.kalan = int(float(r.headers["x-requests-remaining"]))
        self.harcanan += int(float(r.headers.get("x-requests-last", 0) or 0))
        if r.status_code != 200:
            # Hata mesajında URL (anahtar içerir) yazılmaz.
            try:
                mesaj = r.json().get("message", "")
            except ValueError:
                mesaj = r.text[:200]
            raise OddsApiHatasi(f"The Odds API {path.split('/')[-1]}: HTTP {r.status_code} {mesaj}")
        return r.json()


def _zaman(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def futbol_sporlari(api: OddsApi) -> list[dict]:
    """Aktif futbol ligleri (kredi harcamaz); önce izinli ligler."""
    sira = {k: i for i, k in enumerate(IZINLI_SPORLAR)}
    sporlar = [s for s in api.get("sports")
               if s.get("group") == "Soccer" and s.get("active") and not s.get("has_outrights")
               and not _GUVENILMEZ.search(f'{s.get("title", "")} {s.get("description", "")}')]
    return sorted(sporlar, key=lambda s: sira.get(s["key"], len(sira)))


def gun_penceresi(tarih: str, saat_dilimi: str, min_dakika_once: int, simdi: datetime) -> tuple[datetime, datetime]:
    """Bugün oynanacak ve en az min_dakika_once sonra başlayacak maçlar (yerel gün sonuna kadar)."""
    gun_sonu = datetime.fromisoformat(tarih).replace(tzinfo=ZoneInfo(saat_dilimi)) + timedelta(days=1)
    return simdi + timedelta(minutes=min_dakika_once), gun_sonu


def bahisci_oranlari(etkinlik: dict) -> dict[str, dict[str, float]]:
    """Etkinlik -> bahisçi adı -> {pazar kodu -> oran} (API-Football yapısıyla aynı)."""
    ev, dep = etkinlik["home_team"], etkinlik["away_team"]
    sonuc: dict[str, dict[str, float]] = {}
    for bm in etkinlik.get("bookmakers", []):
        ad = BAHISCI_ADLARI.get(bm["key"], bm.get("title") or bm["key"])
        oranlar = sonuc.setdefault(ad, {})
        for pazar in bm.get("markets", []):
            for o in pazar.get("outcomes", []):
                fiyat = float(o.get("price") or 0)
                if fiyat <= 1.0:
                    continue
                if pazar["key"] == "h2h":
                    kod = {ev: "MS1", dep: "MS2", "Draw": "MSX"}.get(o["name"])
                elif pazar["key"] in ("totals", "alternate_totals") and o.get("point") in (1.5, 2.5, 3.5):
                    kod = ("UST" if o["name"] == "Over" else "ALT") + str(int(o["point"] * 10))
                elif pazar["key"] == "btts":
                    kod = {"Yes": "KGVAR", "No": "KGYOK"}.get(o["name"])
                elif pazar["key"] == "double_chance":
                    kod = _cifte_sans(o["name"], ev, dep)
                else:
                    kod = None
                if kod:
                    oranlar[kod] = fiyat
    return {ad: o for ad, o in sonuc.items() if o}


def _cifte_sans(ad: str, ev: str, dep: str) -> str | None:
    """"Spain/Draw", "Draw or Croatia" gibi adlardan çifte şans kodu (yazım biçiminden bağımsız)."""
    ad = ad.lower()
    var = (ev.lower() in ad, "draw" in ad, dep.lower() in ad)
    return {(True, True, False): "CS1X", (False, True, True): "CSX2", (True, False, True): "CS12"}.get(var)


def ima_edilen_goller(adil: dict[str, float]) -> tuple[float, float] | None:
    """Piyasanın adil ihtimallerine (ev kazanır, deplasman kazanır, 2,5 üst) en iyi uyan Poisson beklenen golleri."""
    if not all(k in adil for k in ("MS1", "MS2")):
        return None
    ust = adil.get("UST25")
    lamlar = [i / 20 for i in range(4, 71)]
    dagilim = {l: [math.exp(-l) * l ** k / math.factorial(k) for k in range(11)] for l in lamlar}
    en_iyi, en_az = None, float("inf")
    for le in lamlar:
        pe = dagilim[le]
        for ld in lamlar:
            pd = dagilim[ld]
            p1 = sum(pe[a] * sum(pd[:a]) for a in range(1, 11))
            p2 = sum(pd[b] * sum(pe[:b]) for b in range(1, 11))
            hata = (p1 - adil["MS1"]) ** 2 + (p2 - adil["MS2"]) ** 2
            if ust is not None:
                alti = sum(pe[a] * sum(pd[:3 - a]) for a in range(3))
                hata += (1 - alti - ust) ** 2
            if hata < en_az:
                en_iyi, en_az = (le, ld), hata
    return en_iyi


def tara(api: OddsApi, tarih: str, ayar, simdi: datetime, kredi: int = MAX_TARAMA_KREDISI,
         yaz=print) -> tuple[list[dict], dict]:
    """Bugünün maçları ve oranları. (maçlar, fixture_id -> bahisçi oranları) döner; maç kaydı API-Football'daki
    alanlara ek olarak kaynak bilgisini ("odds_spor", "odds_id") taşır."""
    bas, son = gun_penceresi(tarih, ayar.saat_dilimi, ayar.min_dakika_once, simdi)
    zaman = {"commenceTimeFrom": _zaman(bas), "commenceTimeTo": _zaman(son)}
    maclar, oranlar = [], {}
    for spor in futbol_sporlari(api):
        izinli = spor["key"] in IZINLI_SPORLAR
        if not izinli and not ayar.tum_ligler:
            continue
        etkinlikler = api.get(f'sports/{spor["key"]}/events', **zaman)  # kredi harcamaz
        if not etkinlikler:
            continue
        if api.kalan is not None and api.kalan - 2 < YEDEK_KREDI:
            yaz(f"The Odds API: kalan kredi {api.kalan}; sonuçlar için yedek korunuyor, tarama durdu.")
            break
        if api.harcanan + 2 > kredi:
            yaz(f"The Odds API: tarama kredisi ({kredi}) doldu; kalan ligler atlandı.")
            break
        for e in api.get(f'sports/{spor["key"]}/odds', regions=BOLGE, markets=PAZARLAR, oddsFormat="decimal", **zaman):
            if _GUVENILMEZ.search(f'{e["home_team"]} {e["away_team"]}'):
                continue
            fid = fixture_id(e["id"])
            maclar.append({
                "fixture_id": fid, "odds_id": e["id"], "odds_spor": spor["key"],
                # Kaynağın kendi lig kimliği yok: izinli ligler ayarlardaki ilk lig kimliğiyle "güvenilir" işaretlenir.
                "lig_id": ayar.ligler[0] if izinli else -1,
                "lig": spor.get("title") or spor["key"], "ulke": "", "sezon": None,
                "ev": e["home_team"], "dep": e["away_team"],
                "baslama": datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")).isoformat(),
            })
            b = bahisci_oranlari(e)
            if b:
                oranlar[fid] = b
    ek_pazarlari_ekle(api, maclar, oranlar, ayar, yaz)
    return maclar, oranlar


def _belirginlik(bahisciler: dict, keskin: str) -> float:
    """Maçın ne kadar "tek yönlü" olduğu: en büyük favori ihtimali ya da 2,5 gol üst/alt ihtimali."""
    adil, _ = model.adil_olasiliklar(bahisciler, keskin)
    return max([adil.get(k, 0) for k in ("MS1", "MS2", "UST25", "ALT25")] or [0])


def ek_pazarlari_ekle(api: OddsApi, maclar: list[dict], oranlar: dict, ayar, yaz=print) -> None:
    """En belirgin maçlar için çifte şans / alternatif gol çizgileri / karşılıklı gol oranlarını ekler."""
    adaylar = sorted((m for m in maclar if m["fixture_id"] in oranlar),
                     key=lambda m: _belirginlik(oranlar[m["fixture_id"]], ayar.keskin_bahisci), reverse=True)
    eklenen = 0
    for m in adaylar[:EK_MAC]:
        if api.kalan is not None and api.kalan - 3 < YEDEK_KREDI:
            yaz(f"The Odds API: kalan kredi {api.kalan}; ek pazarlar atlandı.")
            break
        try:
            e = api.get(f'sports/{m["odds_spor"]}/events/{m["odds_id"]}/odds', regions=BOLGE, markets=EK_PAZARLAR,
                        oddsFormat="decimal")
        except OddsApiHatasi as h:
            yaz(f"Ek pazarlar alınamadı ({m['ev']} v {m['dep']}): {h}")
            continue
        for ad, o in bahisci_oranlari(e).items():
            oranlar[m["fixture_id"]].setdefault(ad, {}).update(o)
        eklenen += 1
    yaz(f"Ek pazarlar (çifte şans, gol çizgileri, karşılıklı gol): {eklenen} maç.")


def adaylar(m: dict, bahisciler: dict, ayar) -> list[dict]:
    """İstatistiksiz aday üretimi: değer kuralları aynı; beklenen goller piyasadan çıkarılır. Bu kaynakta
    Bet365 yok, o yüzden "zorunlu bahisçi" yerine listeden en az min_oran_bahiscisi site aranır."""
    from dataclasses import replace
    ayar = replace(ayar, zorunlu_bahisciler=[])
    guvenilir = m["lig_id"] in ayar.ligler
    piyasa = list(model._piyasa_adaylari(bahisciler, ayar, guvenilir))
    adil, _ = model.adil_olasiliklar(bahisciler, ayar.keskin_bahisci)
    goller = ima_edilen_goller(adil) if piyasa else None
    if goller is None:
        return []
    lam_ev, lam_dep = goller
    olas = model.model_olasiliklari(lam_ev, lam_dep)
    skor, skor_p = model.en_olasi_skor(lam_ev, lam_dep)
    sonuc = []
    for pazar, oran, bolag, bahisci_oranlari, p, deger, tur, kaynak in piyasa:
        uzun, kisa = model.etiketler(pazar, m["ev"], m["dep"])
        sonuc.append({
            "aday_id": f'{m["fixture_id"]}-{pazar}', "fixture_id": m["fixture_id"], "pazar": pazar, "tur": tur,
            "etiket": uzun, "kisa": kisa, "oran": oran, "bolag": bolag, "oranlar": bahisci_oranlari,
            "adil_olasilik": round(p, 3), "adil_oran": round(1 / p, 2), "adil_kaynak": kaynak,
            "model_olasilik": round(olas[pazar], 3) if pazar in olas else None, "deger": round(deger, 3),
            "beklenen_gol": [round(lam_ev, 2), round(lam_dep, 2)],
            "olasi_skor": skor, "olasi_skor_olasilik": round(skor_p, 3),
        })
    sonuc.sort(key=lambda a: (a["tur"] == "deger", a["deger"] if a["tur"] == "deger" else a["adil_olasilik"]),
               reverse=True)
    return sonuc[:4]


def sonuclari_al(api: OddsApi, istekler: dict[str, list[str]]) -> dict[int, dict]:
    """spor -> [odds_id]; fixture_id -> {"durum", "skor", "iy", "korner"} (football.sonuclari_al ile aynı yapı).
    İlk yarı skoru ve korner bu kaynakta yok (bu kaynaktan o pazarlar zaten seçilmez)."""
    sonuc: dict[int, dict] = {}
    for spor, idler in istekler.items():
        for e in api.get(f"sports/{spor}/scores", daysFrom=3, eventIds=",".join(idler)):
            fid = fixture_id(e["id"])
            skorlar = {s["name"]: s["score"] for s in e.get("scores") or []}
            if e.get("completed") and e["home_team"] in skorlar and e["away_team"] in skorlar:
                sonuc[fid] = {"durum": "bitti", "skor": (int(skorlar[e["home_team"]]), int(skorlar[e["away_team"]])),
                              "iy": None, "korner": None}
            else:
                sonuc[fid] = {"durum": "bekliyor", "skor": None}
    return sonuc
