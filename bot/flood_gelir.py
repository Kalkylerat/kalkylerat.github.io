"""Tiny Fixes gelir katmanı: ayarlar, bülten taslağı, gelir rakamlarının okunması (SOZLESME F12, F14).

Model (sahibinin kararı, 15 Ekim 2026): X ve Instagram trafik getirir; para kendi sitemizden gelir. Site her
denenmiş çözümü bir sayfa olarak yayınlar, ücretsiz başlangıç paketiyle e-posta listesi (Kit) toplar, ücretli paket
(Lemon Squeezy) ve etiketli affiliate bağlantılar gelir üretir. Bot e-posta göndermez, satış yapmaz, ödeme görmez:
bülten taslağını sahibine verir; abone ve satış rakamlarını yalnızca okur (F14)."""

import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import requests

from . import config

KIT_API = "https://api.kit.com/v4"
LEMON_API = "https://api.lemonsqueezy.com/v1"


@dataclass(frozen=True)
class GelirAyar:
    site_url: str = "https://kalkylerat.github.io/tinyfixes"
    bulten_form_action: str = ""            # Kit formunun action adresi; boşsa sitede form görünmez
    bulten_email_alani: str = "email_address"
    ucretsiz_paket_adi: str = "Tiny Fixes Starter: 10 tested AI prompts"
    ucretsiz_paket_sayisi: int = 10
    urun_adi: str = "Tiny Fixes Library"
    urun_url: str = ""                      # Lemon Squeezy ürün sayfası; boşsa satın al düğmesi görünmez
    urun_fiyat: str = "$9"
    affiliate: tuple = field(default_factory=tuple)  # (("Araç", "https://..."),): yalnızca denenmiş araçlar (F4)

    @property
    def form_var(self) -> bool:
        return self.bulten_form_action.startswith("https://")

    @property
    def urun_var(self) -> bool:
        return self.urun_url.startswith("https://")


def ayar_yukle(path=config.ROOT / "ayarlar.toml") -> GelirAyar:
    with open(path, "rb") as f:
        t = tomllib.load(f).get("flood_gelir", {})
    alanlar = GelirAyar.__dataclass_fields__
    kw = {}
    for k, v in t.items():
        if k not in alanlar:
            continue
        kw[k] = tuple((str(a), str(u)) for a, u in v) if k == "affiliate" else type(GelirAyar().__getattribute__(k))(v)
    return GelirAyar(**kw)


def sayfa_url(g: GelirAyar, slug: str) -> str:
    return f"{g.site_url.rstrip('/')}/fix/{slug}.html"


def cagri_secenekleri(g: GelirAyar) -> list[str]:
    """Yazarın son post / son slayt için seçebileceği çağrılar. Link yok (F4): "profildeki bağlantı" denir."""
    secenek = ["Save this for later.", "Follow for the next tiny fix."]
    if g.form_var:
        secenek.append(f"Free pack of {g.ucretsiz_paket_sayisi} tested prompts: link in our profile.")
    return secenek


# ---------- Bülten taslağı (F12: bot göndermez) ----------

def bulten_taslagi(girdiler: list[dict], g: GelirAyar, simdi: datetime) -> tuple[str, str] | None:
    """(konu, metin): son 7 günde siteye eklenen çözümlerden haftalık bülten. Kayıttaki metin dışında iddia yok."""
    sinir = (simdi - timedelta(days=7)).date().isoformat()
    hafta = [x for x in girdiler if x.get("tarih", "") >= sinir and x.get("komut")]
    if not hafta:
        return None
    konu = f"This week's tiny fixes: {hafta[0]['baslik'][:60]}"
    s = ["Hi,", "", f"Here are this week's {len(hafta)} tested fixes. Each prompt was run on a real AI model before we "
         "posted it, and each one comes with its limit.", ""]
    for i, x in enumerate(hafta, 1):
        s += [f"{i}. {x['baslik']}", f"Tested with {x['model']}.", "", x["komut"], "", f"The limit: {x['sinir']}",
              f"Full fix: {sayfa_url(g, x['slug'])}", ""]
    s.append("If one of these helped, forward it to a friend who's stuck.")
    if g.urun_var:
        s += ["", f"Want every tested prompt in one place? {g.urun_adi} ({g.urun_fiyat}): {g.urun_url}"]
    s += ["", "Tiny Fixes"]
    return konu, "\n".join(s)


# ---------- Gelir rakamları (F14: yalnızca okuma, tahmin yok) ----------

def kit_abone(api_key: str, get=requests.get) -> int | None:
    """Kit'teki toplam abone sayısı; okunamazsa None."""
    try:
        r = get(f"{KIT_API}/subscribers", params={"include_total_count": "true", "per_page": 1},
                headers={"X-Kit-Api-Key": api_key, "Accept": "application/json"}, timeout=30)
        r.raise_for_status()
        n = (r.json().get("pagination") or {}).get("total_count")
        return int(n) if n is not None else None
    except (requests.RequestException, ValueError, TypeError):
        return None


def lemon_satis(api_key: str, baslangic: datetime, get=requests.get) -> dict | None:
    """Son siparişlerden: {'adet', 'tutar_usd'} (başlangıçtan bu yana, ödenmiş) ve 'toplam_adet'; okunamazsa None."""
    try:
        r = get(f"{LEMON_API}/orders", params={"page[size]": 100, "sort": "-created_at"},
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/vnd.api+json"}, timeout=30)
        r.raise_for_status()
        veri = r.json()
        adet, tutar = 0, 0
        for o in veri.get("data") or []:
            a = o.get("attributes") or {}
            if a.get("status") != "paid" or (a.get("created_at") or "") < baslangic.isoformat()[:19]:
                continue
            adet += 1
            tutar += int(a.get("total_usd") or 0)
        toplam = ((veri.get("meta") or {}).get("page") or {}).get("total")
        return {"adet": adet, "tutar_usd": round(tutar / 100, 2), "toplam_adet": toplam}
    except (requests.RequestException, ValueError, TypeError):
        return None


def gelir_satirlari(simdi: datetime, env: dict, get=requests.get) -> list[str]:
    """Haftalık rapor için gelir satırları. Anahtar yoksa ya da okunamazsa açıkça yazar (F14)."""
    s = []
    kit = env.get("KIT_API_KEY")
    if kit:
        n = kit_abone(kit, get)
        s.append(f"- E-posta listesi: {n} abone" if n is not None else "- E-posta listesi: okunamadı (Kit API)")
    else:
        s.append("- E-posta listesi: `KIT_API_KEY` yok, okunmadı")
    lemon = env.get("LEMON_API_KEY")
    if lemon:
        satis = lemon_satis(lemon, simdi - timedelta(days=7), get)
        s.append(f"- Satış (7 gün): {satis['adet']} adet, ${satis['tutar_usd']}" + (f" · toplam sipariş: {satis['toplam_adet']}"
                 if satis.get("toplam_adet") is not None else "") if satis else "- Satış: okunamadı (Lemon Squeezy API)")
    else:
        s.append("- Satış: `LEMON_API_KEY` yok, okunmadı")
    return s
