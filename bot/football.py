"""API-Football (api-sports.io) üzerinden maç, oran, istatistik ve sonuç toplama."""

import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

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


class DemoApi:
    """Örnek veriyle çalışır; anahtar gerektirmez."""

    def __init__(self, path: Path):
        self.data = json.loads(path.read_text(encoding="utf-8"))
        self.istek_sayisi = 0

    def get_body(self, path: str, **params) -> dict:
        self.istek_sayisi += 1
        if path == "odds" and "date" in params:
            kayitlar = [{**k[0], "fixture": {"id": int(ad.split(":")[1])}}
                        for ad, k in self.data.items() if ad.startswith("odds:") and k]
            return {"response": kayitlar, "paging": {"current": 1, "total": 1}}
        return {"response": self.get(path, **params, _sayma=True)}

    def get(self, path: str, _sayma: bool = False, **params) -> list:
        if not _sayma:
            self.istek_sayisi += 1
        if path == "fixtures" and "id" in params:
            return [f for f in self.data["sonuclar"] if f["fixture"]["id"] == int(params["id"])]
        if path == "fixtures":
            return self.data["fixtures"]
        return self.data.get(f"{path}:{params.get('fixture')}", [])


def kalan_istek(api) -> int | None:
    """Bugün kalan API-Football isteği (/status hakka sayılmaz). Okunamazsa None."""
    try:
        durum = api.session.get(f"{BASE_URL}/status", timeout=30).json().get("response") or {}
        istek = durum.get("requests") or {}
        return int(istek["limit_day"]) - int(istek["current"])
    except Exception:
        return None


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
                sonuc[kayit["fixture"]["id"]] = oranlar
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


def sakatlari_al(api, fixture_id: int) -> list[str]:
    return [
        f'{i["team"]["name"]}: {i["player"]["name"]} ({i["player"].get("reason") or i["player"].get("type")})'
        for i in api.get("injuries", fixture=fixture_id)
    ]


def korner_sayisi(api, fixture_id: int) -> int | None:
    toplam, bulundu = 0, False
    for takim in api.get("fixtures/statistics", fixture=fixture_id):
        for st in takim.get("statistics", []):
            if st.get("type") == "Corner Kicks" and st.get("value") is not None:
                toplam += int(st["value"])
                bulundu = True
    return toplam if bulundu else None


def sonuclari_al(api, fixture_ids: list[int], korner_idleri: set[int] = frozenset()) -> dict[int, dict]:
    """fixture_id -> {"durum": "bitti"|"iptal"|"bekliyor", "skor": (ev, dep), "iy": (ev, dep), "korner": int}
    Ücretsiz plan toplu "ids" parametresine izin vermediği için maç başına bir istek atılır."""
    sonuc: dict[int, dict] = {}
    for f in (kayit for fid in fixture_ids for kayit in api.get("fixtures", id=fid)):
        fid = f["fixture"]["id"]
        kisa = f["fixture"]["status"]["short"]
        skorlar = f.get("score") or {}
        ft = skorlar.get("fulltime") or {}
        ht = skorlar.get("halftime") or {}
        if kisa in BITMIS and ft.get("home") is not None:
            sonuc[fid] = {
                "durum": "bitti",
                "skor": (int(ft["home"]), int(ft["away"])),
                "iy": (int(ht["home"]), int(ht["away"])) if ht.get("home") is not None else None,
                "korner": korner_sayisi(api, fid) if fid in korner_idleri else None,
            }
        elif kisa in IPTAL:
            sonuc[fid] = {"durum": "iptal", "skor": None}
        else:
            sonuc[fid] = {"durum": "bekliyor", "skor": None}
    return sonuc
