"""API-Football (api-sports.io) üzerinden maç, oran, istatistik ve sonuç toplama."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE_URL = "https://v3.football.api-sports.io"

BITMIS = {"FT", "AET", "PEN"}
IPTAL = {"PST", "CANC", "ABD", "AWD", "WO"}

# API-Football bahis adı -> (değer -> pazar kodu)
PAZAR_ESLEME = {
    "Match Winner": {"Home": "MS1", "Draw": "MSX", "Away": "MS2"},
    "Double Chance": {"Home/Draw": "CS1X", "Draw/Away": "CSX2", "Home/Away": "CS12"},
    "Goals Over/Under": {"Over 2.5": "UST25", "Under 2.5": "ALT25"},
    "Both Teams Score": {"Yes": "KGVAR", "No": "KGYOK"},
}


class ApiHatasi(RuntimeError):
    pass


class ApiFootball:
    def __init__(self, key: str, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers["x-apisports-key"] = key
        self.istek_sayisi = 0

    def get(self, path: str, **params) -> list:
        r = self.session.get(f"{BASE_URL}/{path}", params=params, timeout=30)
        self.istek_sayisi += 1
        r.raise_for_status()
        body = r.json()
        errors = body.get("errors")
        if errors:
            raise ApiHatasi(f"API-Football hatası ({path}): {errors}")
        return body.get("response", [])


class DemoApi:
    """Örnek veriyle çalışır; anahtar gerektirmez."""

    def __init__(self, path: Path):
        self.data = json.loads(path.read_text(encoding="utf-8"))
        self.istek_sayisi = 0

    def get(self, path: str, **params) -> list:
        self.istek_sayisi += 1
        if path == "fixtures" and "ids" in params:
            ids = {int(i) for i in str(params["ids"]).split("-")}
            return [f for f in self.data["sonuclar"] if f["fixture"]["id"] in ids]
        if path == "fixtures":
            return self.data["fixtures"]
        return self.data.get(f"{path}:{params.get('fixture')}", [])


def _f(x) -> float:
    try:
        return float(str(x).rstrip("%"))
    except (TypeError, ValueError):
        return 0.0


def gunun_maclari(api, tarih: str, ligler: list[int], saat_dilimi: str,
                  min_dakika_once: int, limit: int, simdi: datetime | None = None) -> list[dict]:
    simdi = simdi or datetime.now(timezone.utc)
    esik = simdi + timedelta(minutes=min_dakika_once)
    sira = {lig: i for i, lig in enumerate(ligler)}
    maclar = []
    for f in api.get("fixtures", date=tarih, timezone=saat_dilimi):
        lig_id = f["league"]["id"]
        if lig_id not in sira or f["fixture"]["status"]["short"] != "NS":
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
    maclar.sort(key=lambda m: (sira[m["lig_id"]], m["baslama"]))
    return maclar[:limit]


def oranlari_al(api, fixture_id: int) -> dict[str, dict[str, float]]:
    """bahisçi adı -> {pazar kodu -> oran}. Tek istekte tüm bahisçiler gelir."""
    sonuc: dict[str, dict[str, float]] = {}
    for kayit in api.get("odds", fixture=fixture_id):
        for bm in kayit.get("bookmakers", []):
            oranlar = sonuc.setdefault(bm["name"], {})
            for bet in bm.get("bets", []):
                esleme = PAZAR_ESLEME.get(bet["name"])
                if not esleme:
                    continue
                for v in bet["values"]:
                    kod = esleme.get(str(v["value"]))
                    if kod and _f(v["odd"]) > 1.0:
                        oranlar[kod] = _f(v["odd"])
    return {ad: o for ad, o in sonuc.items() if o}


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


def sonuclari_al(api, fixture_ids: list[int]) -> dict[int, dict]:
    """fixture_id -> {"durum": "bitti"|"iptal"|"bekliyor", "skor": (ev, dep) | None}"""
    sonuc: dict[int, dict] = {}
    for i in range(0, len(fixture_ids), 20):
        parca = fixture_ids[i:i + 20]
        for f in api.get("fixtures", ids="-".join(str(x) for x in parca)):
            kisa = f["fixture"]["status"]["short"]
            ft = (f.get("score") or {}).get("fulltime") or {}
            if kisa in BITMIS and ft.get("home") is not None:
                sonuc[f["fixture"]["id"]] = {"durum": "bitti", "skor": (int(ft["home"]), int(ft["away"]))}
            elif kisa in IPTAL:
                sonuc[f["fixture"]["id"]] = {"durum": "iptal", "skor": None}
            else:
                sonuc[f["fixture"]["id"]] = {"durum": "bekliyor", "skor": None}
    return sonuc
