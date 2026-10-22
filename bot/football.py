"""API-Football (api-sports.io) üzerinden maç, oran, istatistik ve sonuç toplama."""

import re
import time
from datetime import datetime, timedelta, timezone

import requests

BASE_URL = "https://v3.football.api-sports.io"

BITMIS = {"FT", "AET", "PEN"}
# İzinli liste dışındaki liglerde alınmayan maçlar: hazırlık, genç ve kadın maçlarında veri ve piyasa güvenilmez.
_GUVENILMEZ = re.compile(r"friendl|u1[6-9]\b|u2[0-3]\b|under[- ]?(1[6-9]|2[0-3])|youth|junior|women|femin|reserve|\bii\b| b$| w$",
                         re.IGNORECASE)
IPTAL = {"PST", "CANC", "ABD", "AWD", "WO"}  # SUSP/INT/TBD beklemede kalır; 3 gün sonra kayit iptal sayar

# API-Football bahis adı -> (değer -> pazar kodu)
SABIT_PAZARLAR = {
    "Match Winner": {"Home": "MS1", "Draw": "MSX", "Away": "MS2"},
    "Double Chance": {"Home/Draw": "CS1X", "Draw/Away": "CSX2", "Home/Away": "CS12"},
    "Both Teams Score": {"Yes": "KGVAR", "No": "KGYOK"},
    "First Half Winner": {"Home": "IY1", "Draw": "IYX", "Away": "IY2"},
}
# Alt/üst pazarları: bahis adı -> (üst öneki, alt öneki, izinli çizgiler)
CIZGILI_PAZARLAR = {
    "Goals Over/Under": ("UST", "ALT", {"1.5", "2.5", "3.5"}),
    "Goals Over/Under First Half": ("IYU", "IYA", {"0.5", "1.5"}),
    "Corners Over Under": ("KORU", "KORA", {"8.5", "9.5", "10.5"}),
    "Total - Home": ("EVU", "EVA", {"0.5", "1.5", "2.5"}),
    "Total - Away": ("DPU", "DPA", {"0.5", "1.5", "2.5"}),
    "Goals Over/Under - Second Half": ("YYU", "YYA", {"0.5", "1.5"}),
}


def pazar_kodu(bahis: str, deger: str) -> str | None:
    if bahis in SABIT_PAZARLAR:
        return SABIT_PAZARLAR[bahis].get(deger)
    if bahis in CIZGILI_PAZARLAR:
        ust, alt, cizgiler = CIZGILI_PAZARLAR[bahis]
        yon, _, c = deger.partition(" ")
        if c in cizgiler and yon in ("Over", "Under"):
            return (ust if yon == "Over" else alt) + c.replace(".", "")
    return None


class ApiHatasi(RuntimeError):
    pass


class ApiFootball:
    def __init__(self, key: str, session: requests.Session | None = None, aralik: float = 6.5):
        # Ücretsiz plan dakikada 10 istek kabul eder; istekler arası en az bu kadar saniye beklenir.
        self.aralik = aralik
        self.session = session or requests.Session()
        self.session.headers["x-apisports-key"] = key
        self.istek_sayisi = 0
        self._son = 0.0

    def get(self, path: str, **params) -> list:
        return self.get_body(path, **params).get("response", [])

    def get_body(self, path: str, **params) -> dict:
        """Yanıtın tamamı (sayfalama bilgisi dahil)."""
        for deneme in range(4):
            bekle = self.aralik - (time.monotonic() - self._son)
            if bekle > 0:
                time.sleep(bekle)
            r = self.session.get(f"{BASE_URL}/{path}", params=params, timeout=30)
            self._son = time.monotonic()
            self.istek_sayisi += 1
            if r.status_code == 429 and deneme < 3:
                time.sleep(60)
                continue
            r.raise_for_status()
            body = r.json()
            errors = body.get("errors")
            if errors and "rateLimit" in str(errors) and deneme < 3:
                time.sleep(60)
                continue
            if errors:
                raise ApiHatasi(f"API-Football hatası ({path}): {errors}")
            return body
        raise ApiHatasi(f"API-Football: {path} için istek sınırı aşıldı")


def _f(x) -> float:
    try:
        return float(str(x).rstrip("%"))
    except (TypeError, ValueError):
        return 0.0


def gunun_maclari(api, tarih: str, ligler: list[int], saat_dilimi: str,
                  min_dakika_once: int, limit: int, simdi: datetime | None = None,
                  tum_ligler: bool = False) -> list[dict]:
    """Başlamamış maçlar; önce izinli ligler (listedeki sırayla). tum_ligler: diğer ligler de sona eklenir."""
    simdi = simdi or datetime.now(timezone.utc)
    esik = simdi + timedelta(minutes=min_dakika_once)
    sira = {lig: i for i, lig in enumerate(ligler)}
    maclar = []
    for f in api.get("fixtures", date=tarih, timezone=saat_dilimi):
        lig_id = f["league"]["id"]
        if (lig_id not in sira and not tum_ligler) or f["fixture"]["status"]["short"] != "NS":
            continue
        if lig_id not in sira and any(_GUVENILMEZ.search(ad or "") for ad in
                                      (f["league"]["name"], f["teams"]["home"]["name"], f["teams"]["away"]["name"])):
            continue
        baslama = datetime.fromisoformat(f["fixture"]["date"])
        if baslama < esik:
            continue
        maclar.append({
            "fixture_id": f["fixture"]["id"],
            "lig_id": lig_id,
            "sezon": f["league"].get("season"),
            "lig": f["league"]["name"],
            "ulke": f["league"].get("country", ""),
            "ev": f["teams"]["home"]["name"],
            "dep": f["teams"]["away"]["name"],
            "baslama": baslama.isoformat(),
        })
    maclar.sort(key=lambda m: (sira.get(m["lig_id"], len(sira)), m["baslama"]))
    return maclar[:limit]


def _bahisci_oranlari(kayitlar: list[dict]) -> dict[str, dict[str, float]]:
    """API odds kayıtları -> bahisçi adı -> {pazar kodu -> oran}."""
    sonuc: dict[str, dict[str, float]] = {}
    for kayit in kayitlar:
        for bm in kayit.get("bookmakers", []):
            oranlar = sonuc.setdefault(bm["name"], {})
            for bet in bm.get("bets", []):
                for v in bet["values"]:
                    kod = pazar_kodu(bet["name"], str(v["value"]))
                    if kod and _f(v["odd"]) > 1.0:
                        oranlar[kod] = _f(v["odd"])
    return {ad: o for ad, o in sonuc.items() if o}


def oranlari_al(api, fixture_id: int) -> dict[str, dict[str, float]]:
    """bahisçi adı -> {pazar kodu -> oran}. Tek istekte tüm bahisçiler gelir."""
    return _bahisci_oranlari(api.get("odds", fixture=fixture_id))


def toplu_oranlar(api, tarih: str, saat_dilimi: str, max_sayfa: int) -> dict[int, dict[str, dict[str, float]]]:
    """Günün bütün maçlarının oranları, sayfa başına 10 maç (maç başına ayrı istek yerine).
    fixture_id -> bahisçi oranları. Sayfa sınırı ya da istek hakkı biterse o ana kadar toplananlar döner."""
    sonuc: dict[int, dict[str, dict[str, float]]] = {}
    sayfa, toplam = 1, 1
    tz = {"timezone": saat_dilimi}
    while sayfa <= min(toplam, max_sayfa):
        try:
            body = api.get_body("odds", date=tarih, page=sayfa, **tz)
        except ApiHatasi as e:
            if tz and "timezone" in str(e).lower():
                tz = {}  # bu uçta saat dilimi desteklenmiyorsa UTC tarihiyle devam
                continue
            if not sonuc:
                raise
            print(f"Toplu oran taraması {sayfa}. sayfada durdu: {e}")
            break
        toplam = int((body.get("paging") or {}).get("total") or 1)
        for kayit in body.get("response", []):
            oranlar = _bahisci_oranlari([kayit])
            if oranlar:
                # Aynı maç birden fazla kayıtta gelebilir (bahisçiler kayıtlara bölünmüş): üzerine yazılmaz, birleştirilir.
                mevcut = sonuc.setdefault(kayit["fixture"]["id"], {})
                for ad, pazarlar in oranlar.items():
                    mevcut.setdefault(ad, {}).update(pazarlar)
        sayfa += 1
    print(f"Toplu oran taraması: {sayfa - 1}/{toplam} sayfa, {len(sonuc)} maç")
    return sonuc


def _takim_ozeti(t: dict) -> dict:
    lg = t.get("league") or {}
    goller = lg.get("goals") or {}
    ort_for = (goller.get("for") or {}).get("average") or {}
    ort_aga = (goller.get("against") or {}).get("average") or {}
    oynanan = ((lg.get("fixtures") or {}).get("played")) or {}
    son5 = t.get("last_5") or {}
    son5_gol = son5.get("goals") or {}
    return {
        "form": (lg.get("form") or "")[-6:],
        "oynanan_ic": int(_f(oynanan.get("home"))),
        "oynanan_dis": int(_f(oynanan.get("away"))),
        "atilan_ic_ort": _f(ort_for.get("home")),
        "atilan_dis_ort": _f(ort_for.get("away")),
        "yenilen_ic_ort": _f(ort_aga.get("home")),
        "yenilen_dis_ort": _f(ort_aga.get("away")),
        "son5_atilan_ort": _f((son5_gol.get("for") or {}).get("average")),
        "son5_yenilen_ort": _f((son5_gol.get("against") or {}).get("average")),
        "gol_yemedigi": ((lg.get("clean_sheet") or {}).get("total")),
        "gol_atamadigi": ((lg.get("failed_to_score") or {}).get("total")),
    }


def istatistik_al(api, fixture_id: int) -> dict | None:
    resp = api.get("predictions", fixture=fixture_id)
    if not resp:
        return None
    p = resp[0]
    h2h = []
    for m in (p.get("h2h") or [])[-5:]:
        g = m.get("goals") or {}
        h2h.append(f'{m["teams"]["home"]["name"]} {g.get("home")}-{g.get("away")} {m["teams"]["away"]["name"]}')
    tahmin = p.get("predictions") or {}
    return {
        "ev": _takim_ozeti(p["teams"]["home"]),
        "dep": _takim_ozeti(p["teams"]["away"]),
        "h2h_son5": h2h,
        "api_tavsiye": tahmin.get("advice"),
    }


def mac_xg(api, fixture_id: int, ev: str | None = None) -> tuple[float, float] | None:
    """Bitmiş maçın gerçek xG'si (şut kalitesinden beklenen gol; API-Football fixtures/statistics "expected_goals"),
    (ev, dep). Bazı liglerde yok ya da boş: o zaman None ve postta satır çıkmaz (uydurma rakam yok, SÖZLEŞME A7)."""
    kayitlar = api.get("fixtures/statistics", fixture=fixture_id)
    if len(kayitlar) != 2:
        return None
    if ev and ((kayitlar[1].get("team") or {}).get("name") or "").lower() == ev.lower():
        kayitlar = kayitlar[::-1]
    degerler = []
    for takim in kayitlar:
        v = next((st.get("value") for st in takim.get("statistics", []) if st.get("type") == "expected_goals"), None)
        try:
            v = float(v)
        except (TypeError, ValueError):
            return None
        if not 0 <= v < 10:
            return None
        degerler.append(round(v, 2))
    return degerler[0], degerler[1]


def korner_sayisi(api, fixture_id: int) -> int | None:
    toplam, bulundu = 0, False
    for takim in api.get("fixtures/statistics", fixture=fixture_id):
        for st in takim.get("statistics", []):
            if st.get("type") == "Corner Kicks" and st.get("value") is not None:
                toplam += int(st["value"])
                bulundu = True
    return toplam if bulundu else None


def goller(f: dict, skor: tuple[int, int]) -> list[list] | None:
    """90 dakikanın golleri, sırayla: [[dakika, uzatma, "ev"|"dep"], ...] (uzatma: 90+3 için 3, yoksa 0).
    Maç sayfasındaki olaylardan (fixtures?id= yanıtında gelir, ek istek yok). Kendi kalesine gol bazı kayıtlarda
    golü atan oyuncunun takımına yazılır: iki yorum da denenir, toplam skorla tutan alınır. Tutmuyorsa None
    (yanlış an anlatılmasın, SOZLESME E2)."""
    olaylar = f.get("events")
    ev_id = ((f.get("teams") or {}).get("home") or {}).get("id")
    if olaylar is None or ev_id is None:
        return None
    ham = []
    for o in olaylar:
        zaman = o.get("time") or {}
        dk = zaman.get("elapsed")
        if o.get("type") != "Goal" or "Missed" in (o.get("detail") or "") or dk is None or dk > 90:
            continue  # kaçan penaltı, uzatma devreleri ve seri penaltılar 90 dakikaya girmez
        taraf = "ev" if (o.get("team") or {}).get("id") == ev_id else "dep"
        ham.append((int(dk), int(zaman.get("extra") or 0), taraf, o.get("detail") == "Own Goal"))
    ham.sort(key=lambda g: (g[0], g[1]))
    for ters in (False, True):
        liste = [[dk, ek, {"ev": "dep", "dep": "ev"}[t] if ters and kk else t] for dk, ek, t, kk in ham]
        if (sum(g[2] == "ev" for g in liste), sum(g[2] == "dep" for g in liste)) == tuple(skor):
            return liste
    return None


def _sonuc(f: dict) -> dict:
    kisa = f["fixture"]["status"]["short"]
    skorlar = f.get("score") or {}
    ft = skorlar.get("fulltime") or {}
    ht = skorlar.get("halftime") or {}
    if kisa in BITMIS and ft.get("home") is not None:
        skor = (int(ft["home"]), int(ft["away"]))
        return {"durum": "bitti", "skor": skor, "goller": goller(f, skor),
                "iy": (int(ht["home"]), int(ht["away"])) if ht.get("home") is not None else None, "korner": None}
    return {"durum": "iptal", "skor": None} if kisa in IPTAL else {"durum": "bekliyor", "skor": None}


def sonuclari_al(api, fixture_ids: list[int], korner_idleri: set[int] = frozenset()) -> dict[int, dict]:
    """fixture_id -> {"durum": "bitti"|"iptal"|"bekliyor", "skor": (ev, dep), "iy": (ev, dep), "korner": int}
    Ücretsiz plan toplu "ids" parametresine izin vermediği için maç başına bir istek atılır."""
    sonuc: dict[int, dict] = {}
    for f in (kayit for fid in fixture_ids for kayit in api.get("fixtures", id=fid)):
        fid = f["fixture"]["id"]
        sonuc[fid] = _sonuc(f)
        if sonuc[fid]["durum"] == "bitti" and fid in korner_idleri:
            sonuc[fid]["korner"] = korner_sayisi(api, fid)
    return sonuc


TOPLU_SINIR = 20  # "ids" parametresi istek başına en fazla 20 maç alır


def toplu_sonuclar(api, fixture_ids: list[int]) -> dict[int, dict]:
    """Çok maçın sonucu, 20 maç tek istekte (ücretli planın "ids" parametresi; korner yok). Toplu istek reddedilirse
    maç başına isteğe döner. Mr. Likely havuz ölçümü için: günde ~60 maç ≈ 3-4 istek."""
    sonuc: dict[int, dict] = {}
    for i in range(0, len(fixture_ids), TOPLU_SINIR):
        parca = fixture_ids[i:i + TOPLU_SINIR]
        try:
            kayitlar = api.get("fixtures", ids="-".join(map(str, parca)))
        except ApiHatasi:
            return {**sonuc, **sonuclari_al(api, fixture_ids[i:])}
        sonuc.update({f["fixture"]["id"]: _sonuc(f) for f in kayitlar})
    return sonuc
