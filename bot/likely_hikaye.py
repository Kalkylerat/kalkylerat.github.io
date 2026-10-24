"""Mr. Likely günün büyük maçları için "maç hikayesi" flood'u (SOZLESME E1, sahibinin isteği 25 Ekim 2026).

Olgular yalnızca API-Football verisinden, kodla hesaplanır: eşleşme geçmişi, puan durumu, son maçlar (Avrupa dahil),
sezonun iç saha/deplasman karnesi, seriler, geç goller, sakat ve cezalılar. Her olgunun bir ilginçlik puanı var; en
ilginç olanlar seçilir. Haber sitesi metni, yorum, Opta'ya özel veri yok; kayıtta olmayan bir sayı yazılmaz.
Maliyet: büyük maç başına ~8 API-Football isteği (puan durumu lig başına bir kez), günde en fazla 4 maç."""

from datetime import datetime, timedelta

from . import denetci
from .tweets import ANSVAR, LIMIT, uzunluk

BITTI = {"FT", "AET", "PEN"}
SORULAR = ["How do you see this one going?", "Does the run go on tonight?", "Who takes this one?",
           "Anyone fancy the upset here?"]


def _sira(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


# ---------- Veri (API-Football) ----------

def veri_topla(api, m: dict, onbellek: dict | None = None) -> dict:
    """Maçın ham verisi; bir parça alınamazsa o parça boş kalır (o olgu çıkmaz). onbellek: lig puan durumu."""
    from .football import ApiHatasi
    onbellek = {} if onbellek is None else onbellek
    ham: dict = {}

    def al(ad, fn):
        try:
            ham[ad] = fn()
        except (ApiHatasi, KeyError, IndexError, TypeError, ValueError):
            ham[ad] = None

    al("mac", lambda: api.get("fixtures", id=m["fixture_id"])[0])
    lig = (ham.get("mac") or {}).get("league") or {}
    sezon, lig_id = lig.get("season"), lig.get("id") or m.get("lig_id")
    al("h2h", lambda: api.get("fixtures/headtohead", h2h=f'{m["ev_id"]}-{m["dep_id"]}', last=25))
    al("ev_son", lambda: api.get("fixtures", team=m["ev_id"], last=3))
    al("dep_son", lambda: api.get("fixtures", team=m["dep_id"], last=3))
    al("sakat", lambda: api.get("injuries", fixture=m["fixture_id"]))
    if sezon and lig_id:
        anahtar = f"{lig_id}-{sezon}"
        if anahtar not in onbellek:
            al("puan", lambda: api.get("standings", league=lig_id, season=sezon)[0]["league"]["standings"])
            onbellek[anahtar] = ham["puan"]
        ham["puan"] = onbellek[anahtar]
        al("ev_ist", lambda: api.get_body("teams/statistics", league=lig_id, season=sezon, team=m["ev_id"])["response"])
        al("dep_ist", lambda: api.get_body("teams/statistics", league=lig_id, season=sezon, team=m["dep_id"])["response"])
    return ham


# ---------- Olgular ----------

def _kazanan(f: dict) -> int | None:
    """Biten maçın kazananının takım kimliği; berabere (ya da penaltı) None."""
    if (f.get("fixture") or {}).get("status", {}).get("short") not in ("FT", "AET"):
        return None
    t = f["teams"]
    return t["home"]["id"] if t["home"].get("winner") else t["away"]["id"] if t["away"].get("winner") else None


def _h2h(ham: dict, m: dict) -> list[dict]:
    maclar = sorted((f for f in ham.get("h2h") or [] if (f.get("fixture") or {}).get("status", {}).get("short") in BITTI),
                    key=lambda f: f["fixture"]["date"], reverse=True)
    n = len(maclar)
    if n < 5:
        return []
    ev, dep = m["ev_id"], m["dep_id"]
    kaz = [_kazanan(f) for f in maclar]
    sonuc = []
    for tid, ad, rakip in ((ev, m["ev"], m["dep"]), (dep, m["dep"], m["ev"])):
        w = kaz.count(tid)
        if n >= 8 and w <= 1:
            sonuc.append({"metin": f"{ad} have won {w} of the last {n} meetings with {rakip}.", "puan": 92})
        yenilmez = next((i for i, k in enumerate(kaz) if k not in (tid, None)), n)
        if yenilmez >= 5:
            sonuc.append({"metin": f"{ad} are unbeaten in the last {yenilmez} meetings with {rakip}.", "puan": 82})
    if not sonuc:
        d = kaz.count(None)
        sonuc.append({"metin": f"Last {n} meetings: {m['ev']} {kaz.count(ev)} wins, {m['dep']} {kaz.count(dep)}, "
                               f"{d} draw{'s' * (d != 1)}.", "puan": 40})
    return sonuc


def _puan(ham: dict, m: dict) -> list[dict]:
    satirlar = {r["team"]["id"]: r for grup in ham.get("puan") or [] for r in grup}
    e, d = satirlar.get(m["ev_id"]), satirlar.get(m["dep_id"])
    if not e or not d or e.get("group") != d.get("group"):
        return []
    yazi = lambda r, ad: f"{ad} {'top' if r['rank'] == 1 else _sira(r['rank'])} on {r['points']} pts"
    metin = f"{yazi(e, m['ev'])}, {yazi(d, m['dep'])}."
    zirve = e["rank"] <= 4 and d["rank"] <= 4
    if zirve:
        metin = "A top-four clash: " + metin
    return [{"metin": metin, "puan": 74 if zirve else 50 if min(e["rank"], d["rank"]) <= 6 else 35}]


def _son_mac(f: dict, tid: int) -> str | None:
    if (f.get("fixture") or {}).get("status", {}).get("short") not in BITTI:
        return None
    ev = f["teams"]["home"]["id"] == tid
    biz, onlar = ("home", "away") if ev else ("away", "home")
    g = f.get("goals") or {}
    if g.get(biz) is None or g.get(onlar) is None:
        return None
    rakip = f["teams"][onlar]["name"]
    k = _kazanan(f)
    fiil = "won" if k == tid else "drew" if k is None else "lost"
    skor = f"{max(g[biz], g[onlar])}-{min(g[biz], g[onlar])}" if fiil != "drew" else f"{g[biz]}-{g[onlar]}"
    return f"{fiil} {skor} {'v' if ev else 'at'} {rakip}"


def _son(ham: dict, m: dict, simdi: datetime) -> list[dict]:
    parcalar, avrupa = [], 0
    lig_id = ((ham.get("mac") or {}).get("league") or {}).get("id") or m.get("lig_id")
    for anahtar, tid, ad in (("ev_son", m["ev_id"], m["ev"]), ("dep_son", m["dep_id"], m["dep"])):
        bitenler = sorted((f for f in ham.get(anahtar) or [] if f["fixture"]["status"]["short"] in BITTI),
                          key=lambda f: f["fixture"]["date"], reverse=True)
        if not bitenler:
            continue
        f = bitenler[0]
        yazi = _son_mac(f, tid)
        if not yazi:
            continue
        yakin = simdi - datetime.fromisoformat(f["fixture"]["date"]) <= timedelta(days=5)
        if yakin and (f.get("league") or {}).get("id") != lig_id:
            avrupa += 1
        parcalar.append(f"{ad} {yazi}")
    if not parcalar:
        return []
    if avrupa == 2:
        return [{"metin": f"Both played midweek: {parcalar[0]}, {parcalar[1]}.", "puan": 66}]
    return [{"metin": f"Last time out: {'; '.join(parcalar)}.", "puan": 58 if avrupa else 42}]


def _sezon(ham: dict, m: dict) -> list[dict]:
    sonuc = []
    e, d = ham.get("ev_ist") or {}, ham.get("dep_ist") or {}
    fx = lambda s, k, y: int((((s.get("fixtures") or {}).get(k) or {}).get(y)) or 0)
    oyn, kaz, ber, yen = (fx(e, k, "home") for k in ("played", "wins", "draws", "loses"))
    if oyn >= 3 and kaz == oyn:
        sonuc.append({"metin": f"{m['ev']} have won all {oyn} home games this season.", "puan": 76})
    elif oyn >= 3 and kaz == 0:
        sonuc.append({"metin": f"{m['ev']} are still waiting for a home win this season ({oyn} played).", "puan": 70})
    oyn, kaz, ber, yen = (fx(d, k, "away") for k in ("played", "wins", "draws", "loses"))
    if oyn >= 3 and yen == 0:
        sonuc.append({"metin": f"{m['dep']} are unbeaten away this season (W{kaz} D{ber}).", "puan": 66})
    elif oyn >= 3 and kaz <= 1:
        sonuc.append({"metin": f"{m['dep']} have won {kaz} of {oyn} away games this season.", "puan": 62})
    for s, ad in ((e, m["ev"]), (d, m["dep"])):
        form = (s.get("form") or "")
        seri = len(form) - len(form.rstrip(form[-1:])) if form else 0
        if form and form[-1] == "W" and seri >= 4:
            sonuc.append({"metin": f"{ad} have won their last {seri} league games.", "puan": 68})
        elif form and form[-1] == "L" and seri >= 3:
            sonuc.append({"metin": f"{ad} have lost their last {seri} league games.", "puan": 64})
        dk = ((s.get("goals") or {}).get("for") or {}).get("minute") or {}
        gec = sum(int((dk.get(k) or {}).get("total") or 0) for k in ("76-90", "91-105"))
        toplam = int((((s.get("goals") or {}).get("for") or {}).get("total") or {}).get("total") or 0)
        if gec >= 4 and toplam and gec / toplam >= 0.3:
            sonuc.append({"metin": f"{ad} have scored {gec} of their {toplam} league goals after the 75th minute.",
                          "puan": 56})
    return sonuc


def sakatlar(ham: dict, m: dict) -> str:
    """"Out: A, B (Team) · C (Team)": yalnızca API'nin sakat/cezalı listesi; takım başına en fazla 3 ad."""
    takim: dict[int, list[str]] = {}
    for s in ham.get("sakat") or []:
        p = s.get("player") or {}
        if p.get("type") == "Missing Fixture" and p.get("name"):
            takim.setdefault((s.get("team") or {}).get("id"), []).append(p["name"])
    parca = [f"{', '.join(list(dict.fromkeys(takim[tid]))[:3])} ({ad})"
             for tid, ad in ((m["ev_id"], m["ev"]), (m["dep_id"], m["dep"])) if takim.get(tid)]
    return f"🩹 Out: {' · '.join(parca)}." if parca else ""


def olgular(ham: dict, m: dict, simdi: datetime) -> list[dict]:
    """Bütün olgular, ilginçliğe göre sıralı (en ilginç önce)."""
    return sorted(_h2h(ham, m) + _puan(ham, m) + _son(ham, m, simdi) + _sezon(ham, m), key=lambda o: -o["puan"])


def postlar(ham: dict, m: dict, simdi: datetime, tohum: str = "") -> list[str]:
    """Flood'un 2. ve 3. postu (ana post likely.mac_metni). Olgu yoksa boş liste: flood yok, tek post gider."""
    hepsi = olgular(ham, m, simdi)
    if not hepsi:
        return []
    soru = SORULAR[sum(map(ord, tohum)) % len(SORULAR)]
    ikinci, kalan, n = "📋 The story:", [], 0
    for o in hepsi:  # en ilginç en fazla 3 olgu
        aday = f"{ikinci} {o['metin']}"
        if n < 3 and uzunluk(f"{aday}\n\n18+") <= LIMIT:
            ikinci, n = aday, n + 1
        else:
            kalan.append(o)
    sonuc = [f"{ikinci}\n\n18+"]
    ucuncu = [s for s in (sakatlar(ham, m), kalan[0]["metin"] if kalan else "") if s]
    if ucuncu:
        metin = "\n".join(ucuncu) + f"\n\n💬 {soru}\n\n{ANSVAR}"
        while uzunluk(metin) > LIMIT and len(ucuncu) > 1:
            ucuncu.pop()
            metin = "\n".join(ucuncu) + f"\n\n💬 {soru}\n\n{ANSVAR}"
        if uzunluk(metin) <= LIMIT:
            sonuc.append(metin)
    else:
        sonuc[0] = f"{ikinci}\n\n💬 {soru}\n\n{ANSVAR}" if uzunluk(f"{ikinci}\n\n💬 {soru}\n\n{ANSVAR}") <= LIMIT else sonuc[0]
    return [p for p in sonuc if not denetle(p)]


def denetle(metin: str) -> list[str]:
    hata = []
    if uzunluk(metin) > LIMIT:
        hata.append("280 karakteri aşıyor")
    if denetci._LINK.search(metin) or "#" in metin:
        hata.append("link, @ ya da etiket")
    if denetci._SITE.search(metin):
        hata.append("bahis sitesi adı")
    if denetci._KESINLIK.search(metin):
        hata.append("kesinlik dili")
    if not metin.rstrip().splitlines()[-1].startswith("18+"):
        hata.append("18+ satırı yok")
    return hata
