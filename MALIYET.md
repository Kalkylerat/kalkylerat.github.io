# Maliyet ve işletme — Kalkylerat, Mr. Likely, Vezir

12 Ekim 2026'da çıkarıldı. Amaç: aylık ne harcandığını ve bir değişiklik gerektiğinde ne yapılacağını
sohbet geçmişi okumadan bilmek. Sayıların bir kısmı **ölçüm**, bir kısmı **tahmin** — hangisi olduğu yazılı.

## 1. Neyi değiştirmek için ne yapılır

Üç sistem de repodan kendini anlatır; eski sohbetleri okumak gerekmez. Yeni bir Claude Code
oturumu aç, repoyu ver, ne istediğini yaz. Oturum `CLAUDE.md`'yi kendisi okur ve oradan ilgili
dosyaya gider.

| Ne değiştireceksin | Repo | Oturumun okuyacağı yer |
|---|---|---|
| Mr. Likely (kupon, karakter, görsel) | `Kalkylerat/kalkylerat.github.io` | `SOZLESME.md` E bölümü, `marka/MR_LIKELY.md`, `bot/likely.py`, `bot/likely_gorsel.py` |
| Kalkylerat postları, zamanlama, kurallar | aynı repo | `SOZLESME.md`, `.claude/skills/sosyal-medya/SKILL.md`, `bot/etkilesim.py` |
| Nöbet / sağlık kontrolü | aynı repo | `.claude/skills/nobet/SKILL.md` |
| Vezir | `Kalkylerat-desk/vezir` | `CLAUDE.md`, `KULLANIM_KILAVUZU.md`, `YENILIKLER.md` |

Kurallar (her ikisi de `CLAUDE.md`'de yazılı): Kalkylerat'ta değişiklikten önce `SOZLESME.md` okunur,
sonra `python -m pytest -q` yeşil olmalı. Vezir'de `python -m pytest -q tests` yeşil olmalı ve
kullanıcıya görünen her yenilik `YENILIKLER.md`'ye yazılır.

## 2. Aylık maliyet

### Claude (abonelik kredisi)

| Kalem | Tutar | Kaynak |
|---|---|---|
| Eski kurulum: "Kalkylerat (Do Not Delete)" kalıcı oturumu | **$466.89 toplam** (27 Eyl – 12 Eki, ~$31/gün) | ÖLÇÜM (oturum kaydı) |
| Yeni kurulum: saatlik nöbet, her saat temiz oturum, Haiku 5.5 | **~$4–6/ay** | TAHMİN |

Sebep: kalıcı oturum 319.000 token bağlam taşıyordu ve her uyanışta yeniden okunuyordu
(1,02 milyar token cache okuması). Temiz oturum bunu taşımıyor.

### Anthropic API (botların kendi anahtarı — abonelikten ayrı)

| Sistem | Model hattı | Tahmini aylık |
|---|---|---|
| Kalkylerat botu | seçim Opus 5.5 · metin/denetim Sonnet 5.5 · haftalık strateji Fable 5.1 | **$30–50** |
| Mr. Likely | aynı sabah taramasını paylaşır, kuponu sabit kurallar seçer (E6, ücretsiz) | **$3–6** (marjinal) |
| Vezir | haiku hattı (ucuz) · sonnet (uzman) · opus (derin mod) | **$12–20** (ÖLÇÜM: `ODEME_VE_LIMITLER.md`) |

Kalkylerat'ta **kod içi maliyet takibi yok**, o yüzden tahmin. Gerçek rakam:
platform.claude.com → Usage, API anahtarına göre filtrele. Vezir'de takip var: Telegram `/durum`.

Vezir'in kendi koruması: `AI_DAILY_CALL_LIMIT = 250`, `AI_DAILY_BUDGET_USD = 1.0`
(aşılırsa derin mod o gün kapanır), Anthropic'te otomatik yükleme kapalı + aylık $25 sınırı.

### Dış servisler (sabit)

| Servis | Kim kullanıyor | Aylık |
|---|---|---|
| API-Football (Pro) | Kalkylerat **ve** Mr. Likely — ek istek yok, aynı sabah taraması | **190 kr (~$19)** |
| The Odds API | Kalkylerat | plan doğrulanmadı |
| X API | Kalkylerat + Mr. Likely (2 hesap) | plan doğrulanmadı |
| GitHub Actions | Kalkylerat + nöbetçi | **0** (depo herkese açık) |
| DigitalOcean (1 GB) | Vezir | **~$6** |
| Groq (ses), SerpApi, Google API, Telegram, hava durumu | Vezir | **0** (ücretsiz katman) |

**Vezir API-Football ya da Odds API kullanmıyor** (kodda hiç geçmiyor) — o 190 kron tamamen
Kalkylerat + Mr. Likely tarafına ait ve ikisi tek abonelikten besleniyor.

### Toplam

| | Aylık |
|---|---|
| Kalkylerat + Mr. Likely | ~$52–75 + doğrulanmayan X/Odds planları |
| Vezir | ~$18–26 |
| Claude saatlik nöbet | ~$4–6 |
| **Ölçülen toplam** | **~$75–107/ay** (~800–1150 kr) + X API ve Odds API planları |

## 3. Silinmemesi gereken

**`Kalkylerat (Do Not Delete)`** adlı oturum (27 Eylül'de açılmış, sistemi kuran uzun sohbet) ve ona
bağlı devre dışı rutin **`Kalkylerat saatlik sağlık kontrolü`**. Rutin kapalı ve zararsız; silinirse
başlattığı oturumlar da silinir. Dokunmayın.

Diğer tüm sohbetler silinebilir: işletme bilgisi bu repoda (`CLAUDE.md`, `SOZLESME.md` +
`tests/test_sozlesme.py`, `.claude/skills/`, `marka/`).

## 4. Doğrulanmamış iki kalem

1. **X API planı** — `README.md` "X API hatası 402 → geliştirici kredisi bitmiş olabilir" diyor,
   yani ücretli/kredili bir katman. İki hesap günde ~30 post atıyor. Tutarı kontrol edin.
2. **The Odds API planı** — ücretsiz mi ücretli mi doğrulanmadı.
