import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "spel.json"
PANEL_FILE = ROOT / "docs" / "index.html"


@dataclass(frozen=True)
class Ayarlar:
    saat_dilimi: str
    ligler: list[int]
    tum_ligler: bool
    max_oran_sayfasi: int
    istek_araligi_sn: float
    deger_min_olasilik: float
    deger_min_deger: float
    model_tolerans: float
    min_dakika_once: int
    keskin_bahisci: str
    oran_bahiscileri: list[str]
    oran_yontemi: str
    min_oran_bahiscisi: int
    zorunlu_bahisciler: list[str]
    keskinsiz_ek_marj: float
    claude_model: str
    direktor_aktif: bool = True
    direktor_model: str = "claude-sonnet-5-5"
    direktor_effort: str = "medium"
    direktor_strateji_model: str = "claude-fable-5-1"
    direktor_strateji_effort: str = "high"
    # Yoğun gün (ör. maç dolu Cumartesi): postlar arası daha kısa, öne çıkan kart sayısı akşam maçlarıyla genişler.
    yogun_gunler: tuple = ()
    yogun_aralik_dk: int = 15
    yogun_kart: int = 20
    yogun_ek_ligler: tuple = ()
    yogun_hafta_sonu: bool = False  # Cumartesi ve Pazar her zaman yoğun gün
    alarm_kime: str = ""
    topluluk_id: str = ""
    # Aday havuzu eşikleri (model._piyasa_adaylari): Mr. Likely kendi değerleriyle ezer (likely.havuz).
    guvenli_min_olasilik: float = 0.65
    guvenli_min_deger: float = -0.04
    oran_min: float = 1.20
    oran_max: float = 2.60
    gunluk_post_siniri: int = 24  # etkileşim postları (maç sonu yanıtları hariç) günde en fazla  # X Topluluğu kimliği: tablo, kıyas ve kart postları oraya da gider (hesap üye olmalı)  # sorun olunca GitHub issue'sunda etiketlenecek kullanıcı (bildirim gider)


# Tek çalışmalık istisna (elle çalıştırmada "ek" alanı): ör. "deger_min_deger=0.02".
# Yalnızca bu sayısal ayarlar değiştirilebilir; ayarlar.toml'a dokunulmaz, sonraki çalışma normal kurallarla döner.
ISTISNA_ALANLARI = {"deger_min_deger", "keskinsiz_ek_marj", "model_tolerans"}


def istisnalar() -> dict[str, float]:
    sonuc = {}
    for parca in os.environ.get("BOT_EK", "").split():
        ad, _, deger = parca.partition("=")
        if ad in ISTISNA_ALANLARI:
            sonuc[ad] = float(deger)
    return sonuc


def yukle(path: Path = ROOT / "ayarlar.toml") -> Ayarlar:
    ayar = _yukle(path)
    ek = istisnalar()
    if ek:
        from dataclasses import replace
        print(f"Tek çalışmalık istisna: {ek}")
        ayar = replace(ayar, **ek)
    return ayar


def _yukle(path: Path) -> Ayarlar:
    with open(path, "rb") as f:
        t = tomllib.load(f)
    s = t["strateji"]
    return Ayarlar(
        saat_dilimi=t["genel"]["saat_dilimi"],
        ligler=list(t["ligler"]["izinli"]),
        tum_ligler=bool(t["ligler"]["tum_ligler"]),
        max_oran_sayfasi=int(t["ligler"]["max_oran_sayfasi"]),
        istek_araligi_sn=float(t["ligler"]["istek_araligi_sn"]),
        deger_min_olasilik=float(s["deger_min_olasilik"]),
        deger_min_deger=float(s["deger_min_deger"]),
        model_tolerans=float(s["model_tolerans"]),
        min_dakika_once=int(s["min_dakika_once"]),
        keskin_bahisci=t["bahisciler"]["keskin"],
        oran_bahiscileri=list(t["bahisciler"]["oran_bahiscileri"]),
        oran_yontemi=t["bahisciler"].get("oran_yontemi", "medyan"),
        min_oran_bahiscisi=int(t["bahisciler"]["min_oran_bahiscisi"]),
        zorunlu_bahisciler=list(t["bahisciler"]["zorunlu_bahisciler"]),
        keskinsiz_ek_marj=float(t["bahisciler"]["keskinsiz_ek_marj"]),
        claude_model=t["claude"]["model"],
        yogun_gunler=tuple(str(g) for g in t.get("yogun", {}).get("gunler", [])),
        yogun_aralik_dk=int(t.get("yogun", {}).get("aralik_dk", 15)),
        yogun_kart=int(t.get("yogun", {}).get("kart", 20)),
        yogun_ek_ligler=tuple(t.get("yogun", {}).get("ek_ligler", [])),
        yogun_hafta_sonu=bool(t.get("yogun", {}).get("hafta_sonu", False)),
        alarm_kime=str(t.get("alarm", {}).get("kime", "")),
        topluluk_id=str(t.get("topluluk", {}).get("id", "")).strip(),
        gunluk_post_siniri=int(t.get("yogun", {}).get("gunluk_sinir", 24)),
        **({"direktor_aktif": bool(t["direktor"].get("aktif", True)),
            "direktor_model": t["direktor"].get("gunluk_model", "claude-sonnet-5-5"),
            "direktor_effort": t["direktor"].get("gunluk_effort", "medium"),
            "direktor_strateji_model": t["direktor"].get("strateji_model", "claude-fable-5-1"),
            "direktor_strateji_effort": t["direktor"].get("strateji_effort", "high")} if "direktor" in t else {}),
    )


YOGUN_MAC_ESIGI = 8  # hafta içi de bu kadar büyük/izinli lig maçı varsa gün yoğundur (SÖZLEŞME B4)
SABAH_YEREL_DK = 7 * 60 + 17  # sabah analizi her gün 07:17 (İsveç saati; workflow cron'u ile aynı, SÖZLEŞME B5)


def yogun_mu(ayar, tarih: str, gun: dict | None = None) -> bool:
    """Yoğun gün mü: listede, (açıksa) Cumartesi/Pazar ya da sabah analizinde çok maç bulunan gün (gun["yogun"])."""
    from datetime import date
    return tarih in getattr(ayar, "yogun_gunler", ()) or bool(gun and gun.get("yogun")) or (
        getattr(ayar, "yogun_hafta_sonu", False) and date.fromisoformat(tarih).weekday() >= 5)


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} tanımlı değil. GitHub > Settings > Secrets and variables > Actions altına ekleyin.")
    return value
