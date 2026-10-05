import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "spel.json"
PANEL_FILE = ROOT / "docs" / "index.html"
HAFTA_FILE = ROOT / "data" / "haftalik.json"


@dataclass(frozen=True)
class Ayarlar:
    saat_dilimi: str
    ligler: list[int]
    max_mac_tarama: int
    tum_ligler: bool
    max_oran_sayfasi: int
    max_detay_mac: int
    istek_araligi_sn: float
    max_oyun: int
    max_oyun_mac_basina: int
    max_kupon: int
    guvenli_min_olasilik: float
    guvenli_min_deger: float
    deger_min_olasilik: float
    deger_min_deger: float
    oran_min: float
    oran_max: float
    model_tolerans: float
    min_dakika_once: int
    kasa_baslangic: float
    oyun_yuzdesi: float
    para_birimi: str
    keskin_bahisci: str
    oran_bahiscileri: list[str]
    oran_yontemi: str
    min_oran_bahiscisi: int
    zorunlu_bahisciler: list[str]
    keskinsiz_ek_marj: float
    claude_model: str
    claude_effort: str
    otomatik_paylas: bool
    onay_bekle: bool
    onay_suresi_dk: int
    direktor_aktif: bool = True
    direktor_model: str = "claude-sonnet-5-5"
    direktor_effort: str = "medium"
    direktor_strateji_model: str = "claude-fable-5-1"
    direktor_strateji_effort: str = "high"
    # "kupon": eski düzen (kupon + sanal kasa). "analiz": kupon yok; günlük maç analizi kartları.
    konsept: str = "kupon"
    # Yoğun gün (ör. maç dolu Cumartesi): postlar arası daha kısa, öne çıkan kart sayısı akşam maçlarıyla genişler.
    yogun_gunler: tuple = ()
    yogun_aralik_dk: int = 15
    yogun_kart: int = 20
    yogun_ek_ligler: tuple = ()
    yogun_hafta_sonu: bool = False  # Cumartesi ve Pazar her zaman yoğun gün
    alarm_kime: str = ""
    topluluk_id: str = ""
    gunluk_post_siniri: int = 24  # etkileşim postları (maç sonu yanıtları hariç) günde en fazla  # X Topluluğu kimliği: tablo, kıyas ve kart postları oraya da gider (hesap üye olmalı)  # sorun olunca GitHub issue'sunda etiketlenecek kullanıcı (bildirim gider)


# Tek çalışmalık istisna (elle çalıştırmada "ek" alanı): ör. "guvenli_min_deger=-0.03 api_yedek=8".
# Yalnızca bu sayısal ayarlar değiştirilebilir; ayarlar.toml'a dokunulmaz, sonraki çalışma normal kurallarla döner.
ISTISNA_ALANLARI = {"guvenli_min_deger", "deger_min_deger", "keskinsiz_ek_marj", "model_tolerans", "api_yedek"}


def istisnalar() -> dict[str, float]:
    sonuc = {}
    for parca in os.environ.get("BOT_EK", "").split():
        ad, _, deger = parca.partition("=")
        if ad in ISTISNA_ALANLARI:
            sonuc[ad] = float(deger)
    return sonuc


def yukle(path: Path = ROOT / "ayarlar.toml") -> Ayarlar:
    ayar = _yukle(path)
    ek = {k: v for k, v in istisnalar().items() if k != "api_yedek"}
    if ek:
        from dataclasses import replace
        print(f"Tek çalışmalık istisna: {ek}")
        ayar = replace(ayar, **ek)
    return ayar


def _yukle(path: Path) -> Ayarlar:
    with open(path, "rb") as f:
        t = tomllib.load(f)
    s, kasa = t["strateji"], t["kasa"]
    return Ayarlar(
        saat_dilimi=t["genel"]["saat_dilimi"],
        ligler=list(t["ligler"]["izinli"]),
        max_mac_tarama=int(t["ligler"]["max_mac_tarama"]),
        tum_ligler=bool(t["ligler"]["tum_ligler"]),
        max_oran_sayfasi=int(t["ligler"]["max_oran_sayfasi"]),
        max_detay_mac=int(t["ligler"]["max_detay_mac"]),
        istek_araligi_sn=float(t["ligler"]["istek_araligi_sn"]),
        max_oyun=int(s["max_oyun"]),
        max_oyun_mac_basina=int(s["max_oyun_mac_basina"]),
        max_kupon=int(s["max_kupon"]),
        guvenli_min_olasilik=float(s["guvenli_min_olasilik"]),
        guvenli_min_deger=float(s["guvenli_min_deger"]),
        deger_min_olasilik=float(s["deger_min_olasilik"]),
        deger_min_deger=float(s["deger_min_deger"]),
        oran_min=float(s["oran_min"]),
        oran_max=float(s["oran_max"]),
        model_tolerans=float(s["model_tolerans"]),
        min_dakika_once=int(s["min_dakika_once"]),
        kasa_baslangic=float(kasa["baslangic"]),
        oyun_yuzdesi=float(kasa["oyun_yuzdesi"]),
        para_birimi=kasa["para_birimi"],
        keskin_bahisci=t["bahisciler"]["keskin"],
        oran_bahiscileri=list(t["bahisciler"]["oran_bahiscileri"]),
        oran_yontemi=t["bahisciler"].get("oran_yontemi", "medyan"),
        min_oran_bahiscisi=int(t["bahisciler"]["min_oran_bahiscisi"]),
        zorunlu_bahisciler=list(t["bahisciler"]["zorunlu_bahisciler"]),
        keskinsiz_ek_marj=float(t["bahisciler"]["keskinsiz_ek_marj"]),
        claude_model=t["claude"]["model"],
        claude_effort=t["claude"]["effort"],
        otomatik_paylas=bool(t["yayin"]["otomatik_paylas"]),
        onay_bekle=bool(t["yayin"]["onay_bekle"]),
        onay_suresi_dk=int(t["yayin"]["onay_suresi_dk"]),
        konsept=t.get("konsept", {}).get("mod", "kupon"),
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
