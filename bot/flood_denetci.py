"""Tiny Fixes (SOZLESME F) kural bekçisi: bir flood ya da carousel paylaşılmadan önce kodla denetlenir.

Yazar (yapay zekâ) kuralı çiğneyebilir; bu modül çiğnenen her kuralı yakalar ve boş olmayan bir sorun listesi döner.
Sorun varsa post çıkmaz. Hiçbir kural yapay zekâya bırakılmaz."""

import re

from .direktor import sayilar_dogru, yz_izi
from .tweets import LIMIT, uzunluk

KAYIT_TURLERI = ("fix", "news", "library")
FLOOD_MIN, FLOOD_MAX = 5, 9
KART_MIN, KART_MAX = 2, 4          # kart postu: ana post + 1-3 yanıt (F8)
KART_BASLIK_MAX, KART_SATIR_MAX = 90, 170
IG_SLAYT_MIN, IG_SLAYT_MAX = 2, 10
IG_CAPTION_MAX = 2200
IG_ETIKET_MAX = 5
GUNLUK_BIRIM = 4
GUNLUK_IG = 3

# Abartı ve tıklama tuzağı dili (F8). "Game-changer" yazan hesap güvenilir görünmez.
ABARTI = re.compile(r"\b(game[- ]?chang\w*|insane|mind[- ]?blow\w*|revolutioni[sz]\w*|you won'?t believe|unbelievable|"
                    r"jaw[- ]?dropping|shocking|must[- ]?see|changes everything|blow(s|n)? your mind|next level|"
                    r"nobody is talking about|here'?s why you need)\b", re.IGNORECASE)
# Etkileşim tuzağı: X bunu erişimde cezalandırır (sosyal-medya rehberi).
TUZAK = re.compile(r"\b(rt if|retweet if|like if|follow (me )?for|reply yes|comment yes|tag (a|your) friend|"
                   r"like and (share|retweet)|share if you)\b", re.IGNORECASE)
# F3: kayıtta olmayan kişisel deneyim ve otorite iddiaları.
SAHTE_DENEYIM = re.compile(r"\b(i'?ve been using|i have been using|i'?ve used \w+( \w+)? for \w+ (months?|years?|weeks?)|"
                           r"my (clients?|customers?|students?|team|startup)|in my \d+ years|"
                           r"i (tested|tried|ran|reviewed) (\d+|dozens|hundreds|every)\b|i'?ve (built|shipped|run) (\d+|dozens|hundreds)|"
                           r"after (testing|trying|reviewing) (\d+|dozens|hundreds))", re.IGNORECASE)
# Etiket kuralı: trend/yayılma etiketi yok (D1'in aynısı).
GENEL_ETIKET = {"#trending", "#viral", "#fyp", "#breaking", "#breakingnews", "#trend", "#explore", "#follow", "#like",
                "#followme", "#instagood", "#love", "#news", "#foryou", "#foryoupage", "#reels"}
LINK = re.compile(r"https?://|www\.|\b[\w-]+\.(com|io|ai|org|net|co|app|dev|me|ly)\b", re.IGNORECASE)
URL = re.compile(r"https?://\S+", re.IGNORECASE)
ETIKET = re.compile(r"(?<!\w)#\w+")

# F5 güvenli alan: bu konularda bot taslak bile yazmaz. Kasıtlı geniş: şüphede paylaşılmaz, sahibi elle yazabilir.
GUVENSIZ = {
    "sağlık": r"health|medic\w*|drug|dosage|symptom|diagnos\w*|cancer|vaccin\w*|therap\w*|disease|covid|supplement|"
              r"pregnan\w*|surgery|depress\w*|suicid\w*|diet|weight loss|mental health|prescription",
    "hukuk": r"lawsuit|sued?\b|sues\b|legal advice|attorney|lawyer|court\b|judge\b|ruling|custody|divorce|immigration|"
             r"copyright (case|claim)|indict\w*",
    "finans": r"invest(?:ing|ment|ments|or|ors|ed)?\b|stock tips?|crypto\w*|bitcoin|trading|forex|loans?\b|mortgage|retirement|portfolio|"
              r"financial advice|tax (return|advice|filing)|buy the dip",
    "trajedi": r"killed|dies\b|died\b|death|shooting|terror\w*|bomb\w*|earthquake|hurricane|massacre|hostage|"
               r"airstrike|missile|plane crash|car crash|tragedy|victims?",
    "siyaset": r"election|ballot|voting|\bvote\b|senate|congress|parliament|democrat\w*|republican\w*|trump|biden|harris|"
               r"campaign trail|politic\w*|ceasefire|sanctions?|invasion|referendum",
    "kişi iddiası": r"alleg\w+|accused|scandal|arrest\w*|charged with|affair|fraud|harass\w*|leaked (photos|nudes)",
}
_GUVENSIZ = {k: re.compile(r"\b(" + v + r")", re.IGNORECASE) for k, v in GUVENSIZ.items()}

# F5 tek istisnası (15 Ekim 2026, sahibinin onayı): cihaz/uygulama hakkındaki gündelik ifadeler trajedi sayılmaz. Yalnızca
# kalıp eşleşirse ("phone died", "killed my battery", "death of my charger"); kelimenin yakında geçmesi yetmez
# ("Man killed after phone explodes" elenir). Diğer kategoriler istisnasız.
_CIHAZ = (r"(phones?|iphones?|androids?|batter(y|ies)|laptops?|computers?|pcs?|macs?|macbooks?|tablets?|ipads?|apps?|"
          r"browsers?|tabs?|chargers?|routers?|wi-?fi|screens?|keyboards?|mouse|printers?|hard ?drives?|ssds?|disks?|"
          r"consoles?|headphones?|earbuds|airpods|watch(es)?|smartwatch(es)?|chromebooks?|devices?)")
_TEKNIK = [re.compile(r"\b" + _CIHAZ + r"(\s+\w+){0,2}\s+(dies|died|dying)\b", re.IGNORECASE),
           re.compile(r"\bkilled\s+(my|the|your|our|its)\s+(\w+\s+)?" + _CIHAZ + r"\b", re.IGNORECASE),
           re.compile(r"\bdeath\s+of\s+(my|the|your|our)\s+(\w+\s+)?" + _CIHAZ + r"\b", re.IGNORECASE)]


def _teknik_ifadeleri_cikar(metin: str) -> str:
    for kalip in _TEKNIK:
        metin = kalip.sub(" ", metin)
    return metin

# "7 prompts", "5 steps": liste boyutu bir olgu iddiası değil, yapıdır. Süre, yüzde, fiyat gibi sayılar yapı değildir.
_YAPI_SAYI = re.compile(r"\b\d{1,2}\s+(steps?|prompts?|ways|things|tools?|lines?|tips|rules|questions|mistakes|examples?|"
                        r"points|ideas|templates?|slides?|posts?|parts?|moves)\b|^\s*\d{1,2}[./)]\s", re.IGNORECASE | re.MULTILINE)

MODEL_ADLARI = {"claude-sonnet-5-5": "Claude Sonnet 5.5", "claude-haiku-5-5": "Claude Haiku 5.5",
                "claude-opus-5-5": "Claude Opus 5.5", "claude-fable-5-1": "Claude Fable 5.1"}


def model_adi(model_id: str) -> str:
    return MODEL_ADLARI.get(model_id, model_id)


def alan_adi(url: str) -> str:
    """Bağımsızlık için kaydedilebilir alan adı: www ve alt alan adı atılır (blog.example.co.uk -> example.co.uk)."""
    host = re.sub(r"^[a-z]+://", "", url.strip().lower()).split("/")[0].split("?")[0].split(":")[0]
    parcalar = [p for p in host.split(".") if p]
    if len(parcalar) >= 3 and len(parcalar[-1]) == 2 and parcalar[-2] in {"co", "com", "org", "net", "gov", "ac"}:
        return ".".join(parcalar[-3:])
    return ".".join(parcalar[-2:]) if len(parcalar) >= 2 else host


def bagimsiz_alan_sayisi(urller) -> int:
    return len({alan_adi(u) for u in urller if u})


def guvensiz_alan(metin: str) -> list[str]:
    """F5: metinde geçen güvensiz konu kategorileri (boşsa güvenli)."""
    metin = metin or ""
    temiz = _teknik_ifadeleri_cikar(metin)  # istisna yalnızca trajedi kategorisine uygulanır
    return [ad for ad, kalip in _GUVENSIZ.items() if kalip.search(temiz if ad == "trajedi" else metin)]


def kayit_metni(kayit: dict) -> str:
    """Olgu kaydının düz metni: sayıların kaynağı. Denenen komutun çıktısı ve süresi de gerçek olgudur (F2)."""
    parcalar = [kayit.get("konu", "")] + [o.get("metin", "") for o in kayit.get("olgular") or []]
    d = kayit.get("denendi") or {}
    parcalar += [d.get("komut", ""), d.get("cikti", ""), d.get("sure", ""), model_adi(d.get("model", "")), d.get("sinir", ""),
                 d.get("duz_soru", ""), d.get("duz_cikti", ""), d.get("once", ""), d.get("sonra", "")]
    arac = kayit.get("arac") or {}
    parcalar += [arac.get("ad", "")]
    return "\n".join(p for p in parcalar if p)


def kayit_kontrol(kayit: dict) -> list[str]:
    """F1 ve F5: olgu kaydı yeterli kaynaklı ve güvenli alanda mı?"""
    sorun = []
    tur = kayit.get("tur")
    if tur not in KAYIT_TURLERI:
        return [f"bilinmeyen tür: {tur}"]
    if not (kayit.get("konu") or "").strip():
        sorun.append("konu yok")
    kat = guvensiz_alan(kayit_metni(kayit))
    if kat:
        sorun.append("güvensiz alan (F5): " + ", ".join(kat))
    if tur == "library":
        return sorun + _denendi_sorunlari(kayit)  # evergreen: olgu iddiası yok, kaynak gerekmez; komut yine denenmiş olmalı
    olgular = kayit.get("olgular") or []
    gerek = 2 if tur == "news" else 1
    if len(olgular) < gerek:
        sorun.append(f"en az {gerek} doğrulanmış olgu gerekli, {len(olgular)} var (F1)")
    for o in olgular:
        n = bagimsiz_alan_sayisi(o.get("kaynaklar") or [])
        if n < 2:
            sorun.append(f"olgu 2 bağımsız kaynakta doğrulanmamış (F1): {o.get('metin', '')[:70]}")
    if tur == "fix":
        sorun += _denendi_sorunlari(kayit)
    return sorun


def _denendi_sorunlari(kayit: dict) -> list[str]:
    d = kayit.get("denendi") or {}
    sorun = []
    if not (d.get("komut") and d.get("cikti") and d.get("model")):
        sorun.append("komut gerçekten çalıştırılmamış (F2)")
    if not (d.get("sinir") or "").strip():
        sorun.append("denenen komutun sınırı yazılmamış (F2)")
    if not (d.get("duz_cikti") and d.get("once") and d.get("sonra")) or d.get("fark") != "belirgin":
        sorun.append("düz soru çalıştırılmamış ya da fark belirgin değil (F15)")
    return sorun


def _yapisiz(metin: str) -> str:
    return _YAPI_SAYI.sub(" ", metin)


def _metin_sorunlari(metin: str, kaynak: str, ad: str, sinir: int | None = None) -> list[str]:
    sorun = []
    if not metin.strip():
        return [f"{ad}: boş"]
    if sinir is not None and uzunluk(metin) > sinir:
        sorun.append(f"{ad}: {uzunluk(metin)} karakter, sınır {sinir}")
    if "@" in metin:
        sorun.append(f"{ad}: '@' var (F7)")
    if ABARTI.search(metin):
        sorun.append(f"{ad}: abartı dili: {ABARTI.search(metin).group(0)} (F8)")
    if TUZAK.search(metin):
        sorun.append(f"{ad}: etkileşim tuzağı: {TUZAK.search(metin).group(0)}")
    if SAHTE_DENEYIM.search(metin):
        sorun.append(f"{ad}: kayıtta olmayan kişisel deneyim: {SAHTE_DENEYIM.search(metin).group(0)} (F3)")
    iz = yz_izi(metin)
    if iz:
        sorun.append(f"{ad}: yapay zekâ izi: {iz[0]} (F8)")
    if not sayilar_dogru(_yapisiz(metin), kaynak):
        sorun.append(f"{ad}: kayıtta olmayan rakam (F1)")
    kat = guvensiz_alan(metin)
    if kat:
        sorun.append(f"{ad}: güvensiz alan: {', '.join(kat)} (F5)")
    return sorun


def x_kontrol(flood: dict, kayit: dict, bugunku_metinler=()) -> list[str]:
    """X tarafı: F1, F2, F3, F4, F5, F7, F8 ve D2."""
    sorun = list(kayit_kontrol(kayit))
    x = flood.get("x") or {}
    postlar = [p for p in x.get("postlar") or []]
    kaynak = kayit_metni(kayit)
    if flood.get("bicim", "flood") == "tek":
        if len(postlar) != 1:
            sorun.append(f"tekil post 1 post olmalı, {len(postlar)} var")
    elif flood.get("bicim") == "kart":
        if not KART_MIN <= len(postlar) <= KART_MAX:
            sorun.append(f"kart postu {KART_MIN}-{KART_MAX} post olmalı, {len(postlar)} var (F8)")
        sorun += kart_kontrol(flood.get("kart"), kayit)
    elif not FLOOD_MIN <= len(postlar) <= FLOOD_MAX:
        sorun.append(f"flood {FLOOD_MIN}-{FLOOD_MAX} post olmalı, {len(postlar)} var (F8)")
    etiketler = []
    for i, p in enumerate(postlar, 1):
        sorun += _metin_sorunlari(p, kaynak, f"X {i}. post", LIMIT)
        if LINK.search(p):
            sorun.append(f"X {i}. post: ana postta link var (F4/F8)")
        etiketler += ETIKET.findall(p)
    if len(etiketler) > 1:
        sorun.append(f"flood boyunca en fazla 1 etiket, {len(etiketler)} var (F8)")
    sorun += [f"genel/trend etiketi: {e} (F8)" for e in etiketler if e.lower() in GENEL_ETIKET]
    kisa = [p.strip()[:50].lower() for p in postlar]
    if len(set(kisa)) < len(kisa):
        sorun.append("flood içinde birbirine çok benzeyen postlar var")
    bugun = {m.strip().lower() for m in bugunku_metinler}
    if any(p.strip().lower() in bugun for p in postlar):
        sorun.append("aynı metin bugün zaten paylaşılmış (D2)")
    if kayit.get("tur") in ("fix", "library"):
        d = kayit.get("denendi") or {}
        kart = flood.get("kart") or {}
        tum = (" ".join(postlar) + " " + str(kart.get("alt", ""))).lower()
        if "tested" not in tum or model_adi(d.get("model", "")).lower() not in tum:
            sorun.append("Fix postu hangi modelle denendiğini yazmıyor (F2: 'Tested with <model>')")
    sorun += _link_yaniti_sorunlari(x.get("link_yaniti"), kayit)
    return sorun


def kart_kontrol(kart: dict | None, kayit: dict) -> list[str]:
    """Kart görselinin metni (F8, F15): başlık + 2-4 satır + alt satır; aynı metin kuralları. Fix/Library kartı düz
    cevabı ve bizim cevabımızı birlikte gösterir; satırlar kayıttan gelir (yazar uyduramaz)."""
    if not kart:
        return ["kart postunun kart görseli yok (F8)"]
    sorun = []
    kaynak = kayit_metni(kayit)
    baslik, satirlar = (kart.get("baslik") or ""), kart.get("satirlar") or []
    if len(baslik) > KART_BASLIK_MAX:
        sorun.append(f"kart başlığı {len(baslik)} karakter, sınır {KART_BASLIK_MAX}")
    if not 2 <= len(satirlar) <= 4:
        sorun.append(f"kart 2-4 satır olmalı, {len(satirlar)} var")
    for i, (etiket, metin) in enumerate(satirlar, 1):
        if len(metin) > KART_SATIR_MAX:
            sorun.append(f"kart {i}. satır {len(metin)} karakter, sınır {KART_SATIR_MAX}")
    sorun += _metin_sorunlari("\n".join([baslik, kart.get("alt", "")] + [m for _, m in satirlar]), kaynak, "kart")
    if kayit.get("tur") in ("fix", "library"):
        d = kayit.get("denendi") or {}
        metinler = {m for _, m in satirlar}
        if not (d.get("once") in metinler and d.get("sonra") in metinler):
            sorun.append("kart düz cevapla bizim cevabımızı birlikte göstermiyor (F15)")
    return sorun


def _link_yaniti_sorunlari(yanit, kayit: dict) -> list[str]:
    """F4: link yalnızca son yanıtta; affiliate ibaresi zorunlu; yalnızca denenmiş araç için."""
    if not yanit:
        return []
    sorun = _metin_sorunlari(URL.sub("", yanit), kayit_metni(kayit), "link yanıtı", LIMIT)
    urller = URL.findall(yanit)
    izinli = {u for k in kayit.get("olgular") or [] for u in k.get("kaynaklar") or []}
    arac = kayit.get("arac") or {}
    aff = arac.get("affiliate_url")
    for u in urller:
        if aff and u.rstrip(".,)") == aff:
            if "affiliate" not in yanit.lower():
                sorun.append("affiliate linkinin yanında 'affiliate' ibaresi yok (F4)")
            d = kayit.get("denendi") or {}
            if not (d.get("komut") and d.get("cikti")):
                sorun.append("denenmemiş araç için affiliate link (F4)")
        elif u.rstrip(".,)") not in izinli:
            sorun.append(f"kayıtta olmayan link: {u[:50]} (F4)")
    return sorun


def ig_kontrol(flood: dict, kayit: dict, bugunku_ig: int = 0) -> list[str]:
    """Instagram tarafı: aynı olgulardan, ayrı yazılmış carousel (F1, F3, F5, F7, F8)."""
    sorun = list(kayit_kontrol(kayit))
    ig = flood.get("ig") or {}
    slaytlar = ig.get("slaytlar") or []
    kaynak = kayit_metni(kayit)
    if not IG_SLAYT_MIN <= len(slaytlar) <= IG_SLAYT_MAX:
        sorun.append(f"carousel {IG_SLAYT_MIN}-{IG_SLAYT_MAX} slayt olmalı, {len(slaytlar)} var (F8)")
    for i, s in enumerate(slaytlar, 1):
        baslik, metin = (s.get("baslik") or ""), (s.get("metin") or "")
        if len(baslik) > 70:
            sorun.append(f"IG {i}. slayt başlığı {len(baslik)} karakter, sınır 70")
        if len(metin) > 260:
            sorun.append(f"IG {i}. slayt metni {len(metin)} karakter, sınır 260")
        sorun += _metin_sorunlari(f"{baslik}\n{metin}".strip(), kaynak, f"IG {i}. slayt")
    caption = ig.get("caption") or ""
    sorun += _metin_sorunlari(caption, kaynak, "IG caption", None)
    if len(caption) > IG_CAPTION_MAX:
        sorun.append(f"IG caption {len(caption)} karakter, sınır {IG_CAPTION_MAX} (F8)")
    if URL.search(caption):
        sorun.append("IG caption'da link var (tıklanmaz; link profil bağlantısındadır, F4)")
    etiketler = ig.get("etiketler") or ETIKET.findall(caption)
    if len(etiketler) > IG_ETIKET_MAX:
        sorun.append(f"IG en fazla {IG_ETIKET_MAX} etiket, {len(etiketler)} var (F8)")
    sorun += [f"genel/trend etiketi: {e} (F8)" for e in etiketler if e.lower() in GENEL_ETIKET]
    if kayit.get("tur") in ("fix", "library") and "tested" not in (caption + " ".join(f"{s.get('baslik', '')} {s.get('metin', '')}" for s in slaytlar)).lower():
        sorun.append("Fix carousel'i 'Tested' ibaresini taşımıyor (F2)")
    if bugunku_ig >= GUNLUK_IG:
        sorun.append(f"günde en fazla {GUNLUK_IG} Instagram postu (F8)")
    return sorun


def denetle(flood: dict, kayit: dict, bugunku_metinler=(), bugunku_ig: int = 0) -> list[str]:
    """Her iki platform; yinelenen kayıt sorunları bir kez yazılır."""
    sorun = x_kontrol(flood, kayit, bugunku_metinler)
    if flood.get("ig"):
        sorun += [s for s in ig_kontrol(flood, kayit, bugunku_ig) if s not in sorun]
    return sorun
