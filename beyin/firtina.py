"""Üç uzmanlı beyin fırtınası: nasıl bir X hesabı açalım?

Akış (her adım ayrı Claude çağrısı; uzmanlar birbirinin yazdıklarını görür):
  1. Öneri     – her uzman, güncel bilgiyi web'de kontrol ederek 2 fikir yazar (A1, A2, B1, ...).
  2. Denetim   – her uzman diğer ikisinin fikirlerini eleştirir (web'de doğrulayarak).
  3. Düzeltme  – her uzman eleştirilere göre kendi fikirlerini düzeltir, gerekirse geri çeker.
  4. Oylama    – her uzman diğerlerinin fikirlerini kriterlere göre puanlar (kendi fikrine puan veremez).
  5. Ortak karar – en yüksek puanlı fikirler üzerinden yazman ortak bir karar taslağı yazar,
                   üç uzman onaylar ya da itiraz eder; itiraz varsa taslak düzeltilir (en fazla 2 kez).
"""

import hashlib
import json
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import anthropic

KOK = Path(__file__).resolve().parent
ISTEKLER = KOK / "istekler.md"
KARARLAR = KOK / "kararlar"
AYAR_DOSYASI = KOK.parent / "ayarlar.toml"
# Yarım kalan tartışma (API sınırı, zaman aşımı): sonraki çalışma aynı isteklerle buradan devam eder.
DEVAM = KARARLAR / "devam.json"

WEB_ARAMA = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}
MAX_DUZELTME = 2
FINAL_ADAY = 2

# Ağırlıklar toplamı 1. Her kriter 1–10; risk ve maliyette 10 = en güvenli / en ucuz.
KRITERLER = {
    "gelir": ("Gerçekçi gelir potansiyeli ve ilk gelirin ne kadar çabuk geleceği", 0.25),
    "otomasyon": ("Ne kadar tam otomatik çalışır, sahibin günlük yükü ne kadar az", 0.25),
    "buyume": ("X'te kendi kendine büyüme (takipçi, gösterim) potansiyeli", 0.20),
    "risk": ("Hesap kapanması, X kuralları, yasal risk (10 = çok güvenli)", 0.20),
    "maliyet": ("Aylık işletme maliyeti bütçeye uygunluğu (10 = çok ucuz)", 0.10),
}


@dataclass(frozen=True)
class Uzman:
    harf: str
    ad: str
    bakis: str


UZMANLAR = [
    Uzman("A", "Büyüme Uzmanı",
          "X algoritmasını, kitle psikolojisini ve viral içerik formatlarını çok iyi bilirsin. Senin için asıl soru: "
          "bu hesap sıfırdan, reklam ve hile olmadan, sadece içerikle nasıl binlerce gerçek takipçiye ulaşır? "
          "Hangi niş yeterince büyük ama henüz doymamış, hangi paylaşım formatı otomatik üretilse bile değerli olur?"),
    Uzman("B", "Gelir Uzmanı",
          "İnternet hesaplarının nasıl paraya dönüştüğünü bilirsin: X gelir paylaşımı ve abonelikler, affiliate, "
          "sponsorluk, dijital ürün, bülten, veri/araç satışı. Senin için asıl soru: bu hesap kaçıncı ayda, "
          "hangi kanallardan, ayda gerçekçi olarak ne kadar kazandırır ve gelir tek kaynağa bağlı kalmaz mı?"),
    Uzman("C", "Otomasyon ve Risk Uzmanı",
          "Kalkylerat'ı kuran mühendissin: GitHub Actions, Python, Claude API, X API, ücretsiz ve ucuz veri "
          "API'leri. Aynı zamanda X kurallarını (otomasyon, spam, platform manipülasyonu), telif ve reklam "
          "mevzuatını bilirsin. Senin için asıl soru: bu fikir sahip hiçbir şey yapmadan her gün kaliteli "
          "çalışabilir mi, veri kaynağı güvenilir ve ucuz mu, hesap ya da sahip başını belaya sokar mı?"),
]
YAZMAN = Uzman("Y", "Yazman",
               "Tarafsız toplantı yazmanısın. Kendi fikrin yok; üç uzmanın ortak noktalarını ve itirazlarını "
               "dürüstçe tek bir karara dönüştürürsün.")

ORTAK_KURALLAR = """Bir beyin fırtınası ekibindesin. Ekip, sahibin isteklerine en uygun X (Twitter) hesabı fikrini bulacak;
sonra bu fikir Kalkylerat botu gibi tam otomatik bir sisteme dönüştürülecek.

Kurallar:
- Türkçe yaz. Kısa, somut ve dürüst ol; boş övgü ve pazarlama dili yok.
- Rakam verirken (takipçi eşikleri, API fiyatları, gelir paylaşımı şartları) güncel olduğundan emin ol; emin
  değilsen web'de ara ya da "doğrulanmadı" diye belirt. Bugünün tarihi: {tarih}.
- Sahte etkileşim, spam, telif ihlali, yanıltıcı içerik ya da yasa dışı reklam içeren fikirler kabul edilemez.
- Fikirlere kimliklerine göre (A1, B2 gibi) atıf yap.

Sahibin istekleri:
{istekler}"""


@dataclass
class Kayit:
    """Toplantı tutanağı ve harcanan token. Her bölüm eklenince devam dosyasına yazılır."""
    bolumler: list[tuple[str, str]] = field(default_factory=list)
    girdi: int = 0
    cikti: int = 0
    tablo: dict[str, dict] = field(default_factory=dict)
    anahtar: str = ""
    dosya: Path | None = None

    def ekle(self, baslik: str, metin: str) -> None:
        self.bolumler.append((baslik, metin))
        print(f"✓ {baslik}", flush=True)
        self.sakla()

    def var(self, baslik: str) -> bool:
        return any(b == baslik for b, _ in self.bolumler)

    def sakla(self) -> None:
        if self.dosya:
            self.dosya.parent.mkdir(exist_ok=True)
            self.dosya.write_text(json.dumps({
                "anahtar": self.anahtar, "bolumler": self.bolumler, "tablo": self.tablo,
                "girdi": self.girdi, "cikti": self.cikti}, ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def yukle(cls, dosya: Path | None, anahtar: str) -> "Kayit":
        """Aynı isteklerle yarım kalmış bir tartışma varsa onu (5. tur hariç, o baştan yapılır) geri getirir."""
        if dosya and dosya.exists():
            d = json.loads(dosya.read_text(encoding="utf-8"))
            if d.get("anahtar") == anahtar:
                bolumler = [(b, m) for b, m in d["bolumler"] if not b.startswith("5. Tur")]
                print(f"↻ Yarım kalan tartışmadan devam: {len(bolumler)} bölüm hazır", flush=True)
                return cls(bolumler, d["girdi"], d["cikti"], d.get("tablo", {}), anahtar, dosya)
        return cls(anahtar=anahtar, dosya=dosya)

    def metin(self, *basliklar_on_ekleri: str) -> str:
        return "\n\n".join(f"## {b}\n\n{m}" for b, m in self.bolumler
                           if not basliklar_on_ekleri or b.startswith(basliklar_on_ekleri))

    def maliyet_usd(self) -> float:
        return self.girdi * 4 / 1e6 + self.cikti * 20 / 1e6


class BeyinHatasi(RuntimeError):
    pass


def _ayarlar() -> tuple[str, str]:
    with open(AYAR_DOSYASI, "rb") as f:
        claude = tomllib.load(f).get("claude", {})
    return claude.get("model", "claude-opus-5-5"), claude.get("effort", "high")


def _metin(msg) -> str:
    return "\n".join(b.text for b in msg.content if b.type == "text").strip()


class Toplanti:
    def __init__(self, client=None, istekler: str | None = None, ek_not: str = "", simdi: datetime | None = None,
                 devam: Path | None = DEVAM):
        self.client = client or anthropic.Anthropic()
        self.model, self.effort = _ayarlar()
        self.simdi = simdi or datetime.now(timezone.utc)
        istekler = istekler if istekler is not None else ISTEKLER.read_text(encoding="utf-8")
        if ek_not.strip():
            istekler += f"\n\n## Bu çalışma için sahibin ek notu\n{ek_not.strip()}"
        self.kurallar = ORTAK_KURALLAR.format(tarih=self.simdi.date().isoformat(), istekler=istekler)
        anahtar = hashlib.sha256(f"{self.model}|{istekler}".encode()).hexdigest()[:16]
        self.kayit = Kayit.yukle(devam, anahtar)

    # --- Claude çağrısı -------------------------------------------------------------------------------------

    def _sor(self, kim: Uzman, gorev: str, web: bool = False, sema: dict | None = None) -> str:
        """Tek, durumsuz çağrı: rol + ortak kurallar sistemde, o ana kadarki tutanak ve görev kullanıcı mesajında."""
        messages = [{"role": "user", "content": gorev}]
        output_config = {"effort": self.effort}
        if sema:
            output_config["format"] = {"type": "json_schema", "schema": sema}
        ek = {"tools": [WEB_ARAMA]} if web else {}
        parcalar = []
        for _ in range(6):  # web araması uzun sürerse API turu "pause_turn" ile böler; kaldığı yerden devam
            with self.client.beta.messages.stream(
                model=self.model,
                max_tokens=32000,
                system=f"Sen ekibin {kim.ad}sın. {kim.bakis}\n\n{self.kurallar}",
                messages=messages,
                output_config=output_config,
                # Güvenlik filtresi yanlışlıkla reddederse istek aynı çağrı içinde yedek modelle yeniden çalışır.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                **ek,
            ) as stream:
                msg = stream.get_final_message()
            u = msg.usage
            self.kayit.girdi += u.input_tokens + (u.cache_read_input_tokens or 0) + (u.cache_creation_input_tokens or 0)
            self.kayit.cikti += msg.usage.output_tokens
            parcalar.append(_metin(msg))
            if msg.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": msg.content})
                continue
            if msg.stop_reason == "refusal":
                raise BeyinHatasi(f"{kim.ad} yanıt vermeyi reddetti: {getattr(msg.stop_details, 'explanation', '')}")
            if msg.stop_reason == "max_tokens":
                raise BeyinHatasi(f"{kim.ad} yanıtı çok uzun, yarıda kesildi.")
            metin = "\n".join(p for p in parcalar if p).strip()
            if not metin:
                raise BeyinHatasi(f"{kim.ad} boş yanıt döndürdü.")
            return metin
        raise BeyinHatasi(f"{kim.ad} web aramasını bitiremedi.")

    def _sor_json(self, kim: Uzman, gorev: str, sema: dict) -> dict:
        metin = self._sor(kim, gorev, sema=sema)
        try:
            return json.loads(metin)
        except json.JSONDecodeError as e:
            raise BeyinHatasi(f"{kim.ad} geçersiz JSON döndürdü: {e}") from e

    # --- Turlar ---------------------------------------------------------------------------------------------

    def oneriler(self) -> None:
        for u in UZMANLAR:
            baslik = f"1. Tur – {u.ad} ({u.harf}1, {u.harf}2)"
            if self.kayit.var(baslik):
                continue
            gorev = (
                f"1. tur: bağımsız öneri. Diğer uzmanların ne önereceğini bilmiyorsun.\n\n"
                f"Sahibin isteklerine uyan **tam 2 farklı** X hesabı fikri yaz: {u.harf}1 ve {u.harf}2. Her fikir için:\n"
                "- **Ad ve tek cümlelik özet**\n"
                "- **Niş ve hedef kitle** (dil, ülke, kim takip eder, neden)\n"
                "- **Günlük içerik:** ne paylaşılır, hangi saatlerde, bir örnek tweet\n"
                "- **Veri kaynağı / içerik hammaddesi** ve maliyeti\n"
                "- **Büyüme yolu:** ilk 1.000 takipçi nasıl gelir\n"
                "- **Gelir modeli:** hangi kanallar, hangi eşikler, ayda gerçekçi rakam (3., 6. ve 12. ay)\n"
                "- **Otomasyon:** sahip ne yapar, bot ne yapar\n"
                "- **En büyük risk** ve önlemi\n"
                "Rakamları web'de doğrula."
            )
            self.kayit.ekle(baslik, self._sor(u, gorev, web=True))

    def denetim(self) -> None:
        tutanak = self.kayit.metin("1. Tur")
        for u in UZMANLAR:
            baslik = f"2. Tur – {u.ad} denetliyor"
            if self.kayit.var(baslik):
                continue
            gorev = (
                f"2. tur: çapraz denetim. İlk turda yazılan bütün fikirler:\n\n{tutanak}\n\n---\n\n"
                f"Senin fikirlerin {u.harf}1 ve {u.harf}2. **Diğer uzmanların 4 fikrini** kendi uzmanlık açından sert ama "
                "adil bir şekilde denetle. Her fikir için: en güçlü yanı, en ciddi zayıflığı (şüpheli rakamları web'de "
                "kontrol et), bu haliyle işe yarar mı, ve fikri kurtaracak somut değişiklik. En sonda: sence en umut "
                "verici 2 fikir hangisi (kendi fikrin de olabilir, gerekçesiyle)."
            )
            self.kayit.ekle(baslik, self._sor(u, gorev, web=True))

    def duzeltme(self) -> None:
        tutanak = self.kayit.metin("1. Tur", "2. Tur")
        for u in UZMANLAR:
            baslik = f"3. Tur – {u.ad} son hali ({u.harf}1, {u.harf}2)"
            if self.kayit.var(baslik):
                continue
            gorev = (
                f"3. tur: düzeltme. Şimdiye kadarki tutanak:\n\n{tutanak}\n\n---\n\n"
                f"Eleştirileri dikkate alarak kendi fikirlerin {u.harf}1 ve {u.harf}2'nin **son halini** yaz (aynı başlıklar, "
                "daha kısa). Haklı eleştirileri kabul et, haksız bulduklarına kısaca cevap ver. Bir fikir kurtarılamıyorsa "
                "'GERİ ÇEKİLDİ' yaz ve yerine başka bir uzmanın fikrini güçlendiren bir birleşim önerebilirsin "
                "(ör. 'A2 + C1'), yine de kendi kimliğinle yaz."
            )
            self.kayit.ekle(baslik, self._sor(u, gorev))

    def oylama(self) -> dict[str, dict]:
        if self.kayit.var("4. Tur – Oylama") and self.kayit.tablo:
            return self.kayit.tablo
        son_haller = self.kayit.metin("3. Tur")
        denetimler = self.kayit.metin("2. Tur")
        oylar: dict[str, list[dict]] = {}
        satirlar = []
        for u in UZMANLAR:
            hedefler = [f"{d.harf}{i}" for d in UZMANLAR if d is not u for i in (1, 2)]
            sema = _oy_semasi(hedefler)
            gorev = (
                f"4. tur: gizli oylama. Denetimler:\n\n{denetimler}\n\n---\n\nFikirlerin son halleri:\n\n{son_haller}\n\n---\n\n"
                f"Şu fikirleri puanla: {', '.join(hedefler)} (kendi fikirlerine puan veremezsin). Her kriter 1–10:\n"
                + "\n".join(f"- {k}: {a}" for k, (a, _) in KRITERLER.items())
                + "\nGeri çekilmiş fikirlere her kriterde 1 ver. Sahibin isteklerine uyumu esas al, fikrin sahibine değil."
            )
            sonuc = self._sor_json(u, gorev, sema)
            for p in sonuc["puanlar"]:
                if p["fikir"] in hedefler:
                    oylar.setdefault(p["fikir"], []).append(p)
                    satirlar.append(f"- **{u.ad} → {p['fikir']}:** "
                                    + ", ".join(f"{k} {p[k]}" for k in KRITERLER) + f" — {p['yorum']}")
        tablo = _puan_tablosu(oylar)
        self.kayit.tablo = tablo
        self.kayit.ekle("4. Tur – Oylama", "\n".join(satirlar) + "\n\n" + _tablo_md(tablo))
        return tablo

    def ortak_karar(self, tablo: dict[str, dict]) -> tuple[str, bool]:
        adaylar = [f for f, _ in sorted(tablo.items(), key=lambda x: -x[1]["toplam"])[:FINAL_ADAY]]
        tutanak = self.kayit.metin("3. Tur", "4. Tur")
        gorusler = []
        for u in UZMANLAR:
            gorev = (
                f"5. tur: ortak karar. Tutanak:\n\n{tutanak}\n\n---\n\nFinale kalanlar: {', '.join(adaylar)}.\n"
                "Sahibe hangisini (ya da hangi birleşimi) önermeliyiz? Kısa ve net pozisyonunu yaz: seçimin, "
                "gerekçen ve karar için olmazsa olmaz şartın (en fazla 3 madde)."
            )
            gorus = self._sor(u, gorev)
            gorusler.append(f"### {u.ad}\n\n{gorus}")
        self.kayit.ekle("5. Tur – Pozisyonlar", "\n\n".join(gorusler))

        taslak = self._sor(YAZMAN, (
            f"Tutanak:\n\n{self.kayit.metin('3. Tur', '4. Tur', '5. Tur')}\n\n---\n\n"
            "Üç uzmanın pozisyonlarını birleştirerek sahibe sunulacak **ortak kararı** yaz. Biçim:\n"
            f"# Karar: <hesabın adı / konsepti>\n{_KARAR_BICIMI}"
        ))
        for tur in range(MAX_DUZELTME + 1):
            itirazlar = []
            onaylar = []
            for u in UZMANLAR:
                oy = self._sor_json(u, (
                    f"Yazmanın ortak karar taslağı:\n\n{taslak}\n\n---\n\n"
                    "Bu taslağı onaylıyor musun? Ancak sahibin isteklerine ciddi şekilde aykırıysa, önemli bir risk "
                    "atlanmışsa ya da olmazsa olmaz şartın karşılanmamışsa itiraz et; üslup ve küçük ayrıntılar için "
                    "itiraz etme."
                ), _ONAY_SEMASI)
                onaylar.append(f"- **{u.ad}:** {'✅ Onay' if oy['onay'] else '❌ İtiraz'} — {oy['gerekce']}")
                if not oy["onay"]:
                    itirazlar.append(f"{u.ad}: {oy['gerekce']} Gereken değişiklik: {oy['gerekli_degisiklik']}")
            self.kayit.ekle(f"5. Tur – Onay ({tur + 1}. taslak)", "\n".join(onaylar))
            if not itirazlar or tur == MAX_DUZELTME:
                break
            taslak = self._sor(YAZMAN, (
                f"Önceki taslağın:\n\n{taslak}\n\n---\n\nİtirazlar:\n" + "\n".join(f"- {i}" for i in itirazlar)
                + f"\n\nİtirazları gidererek kararı aynı biçimde yeniden yaz:\n# Karar: <hesabın adı / konsepti>\n{_KARAR_BICIMI}"
            ))
        oybirligi = not itirazlar
        return taslak, oybirligi

    def calistir(self) -> tuple[str, str]:
        self.oneriler()
        self.denetim()
        self.duzeltme()
        tablo = self.oylama()
        karar, oybirligi = self.ortak_karar(tablo)
        durum = "Üç uzmanın oybirliğiyle" if oybirligi else "Oy çokluğuyla (itirazlar tutanakta)"
        ozet = (f"{karar}\n\n---\n\n**Karar şekli:** {durum}.\n\n## Puan tablosu\n\n{_tablo_md(tablo)}\n\n"
                f"_Harcanan: ~{self.kayit.girdi:,} girdi + {self.kayit.cikti:,} çıktı token, "
                f"yaklaşık {self.kayit.maliyet_usd():.2f}$ (web aramaları hariç)._")
        tutanak = f"# Beyin fırtınası tutanağı ({self.simdi:%Y-%m-%d %H:%M} UTC)\n\n{self.kayit.metin()}"
        return ozet, tutanak


_KARAR_BICIMI = """**Tek cümlede:** ...
## Neden bu fikir
## Hesap kimliği (ad önerileri, dil, biyografi, görsel tarz)
## Günlük otomatik akış (saat saat; bot ne yapar, sahip ne yapar)
## Veri ve içerik kaynakları (API adı, ücretsiz/ücretli, aylık maliyet)
## Büyüme planı (ilk 30 gün, 3. ay, 6. ay hedefleri)
## Gelir planı (kanallar, eşikler, 3/6/12. ay gerçekçi tahmin)
## Riskler ve önlemler
## Elenen fikirler ve neden elendi (her biri tek satır)
## Kurulum için sahipten gerekenler (hesaplar, anahtarlar, tahmini süre)"""

_ONAY_SEMASI = {
    "type": "object",
    "properties": {
        "onay": {"type": "boolean"},
        "gerekce": {"type": "string"},
        "gerekli_degisiklik": {"type": "string"},
    },
    "required": ["onay", "gerekce", "gerekli_degisiklik"],
    "additionalProperties": False,
}


def _oy_semasi(hedefler: list[str]) -> dict:
    puan = {k: {"type": "integer", "enum": list(range(1, 11))} for k in KRITERLER}
    return {
        "type": "object",
        "properties": {
            "puanlar": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"fikir": {"type": "string", "enum": hedefler}, **puan, "yorum": {"type": "string"}},
                    "required": ["fikir", *KRITERLER, "yorum"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["puanlar"],
        "additionalProperties": False,
    }


def _puan_tablosu(oylar: dict[str, list[dict]]) -> dict[str, dict]:
    """Her fikir için kriter ortalamaları ve ağırlıklı toplam (10 üzerinden)."""
    tablo = {}
    for fikir, liste in oylar.items():
        ort = {k: sum(p[k] for p in liste) / len(liste) for k in KRITERLER}
        ort["toplam"] = round(sum(ort[k] * a for k, (_, a) in KRITERLER.items()), 2)
        tablo[fikir] = ort
    return dict(sorted(tablo.items(), key=lambda x: -x[1]["toplam"]))


def _tablo_md(tablo: dict[str, dict]) -> str:
    bas = "| Fikir | " + " | ".join(f"{k} (%{int(a * 100)})" for k, (_, a) in KRITERLER.items()) + " | **Toplam** |"
    ayr = "|---" * (len(KRITERLER) + 2) + "|"
    satir = [f"| {f} | " + " | ".join(f"{p[k]:.1f}" for k in KRITERLER) + f" | **{p['toplam']:.2f}** |"
             for f, p in tablo.items()]
    return "\n".join([bas, ayr, *satir])


def kaydet(ozet: str, tutanak: str, simdi: datetime) -> tuple[Path, Path]:
    KARARLAR.mkdir(exist_ok=True)
    ad = f"{simdi:%Y-%m-%d-%H%M}"
    karar_yolu, tutanak_yolu = KARARLAR / f"{ad}-karar.md", KARARLAR / f"{ad}-tutanak.md"
    karar_yolu.write_text(ozet + f"\n\nTam tartışma: [{tutanak_yolu.name}]({tutanak_yolu.name})\n", encoding="utf-8")
    tutanak_yolu.write_text(tutanak + "\n", encoding="utf-8")
    return karar_yolu, tutanak_yolu
