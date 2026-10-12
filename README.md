# Kalkylerat — futbol analiz botları

İki otomatik X hesabı, GitHub Actions üzerinde kendi kendine çalışır:

- **@kalkylerat** (analiz): her sabah günün maçlarını analiz eder; X'te sabah tablosu, analiz kartları (oran ve
  takım istatistiği yan yana, yüzdelerle), maç bitince maç sonu postu, tablo altına sonuçlar, anket ve bilgi postları.
  Kupon, kasa ya da bahis tavsiyesi yok.
- **Mr. Likely** (kupon): aynı sabah taramasından sabit kurallarla günde en fazla 3 kupon, maçlar bitince sonuç postu,
  günde en fazla 4 bilgi postu. Karakter ve kurulum: [marka/MR_LIKELY.md](marka/MR_LIKELY.md).

## Nerede ne var
| | |
|---|---|
| Değişmez kurallar (içerik, zamanlama, X kuralları, Mr. Likely) | [SOZLESME.md](SOZLESME.md) |
| Claude ile çalışma kuralları | [CLAUDE.md](CLAUDE.md) |
| Saatlik nöbet, alarmlar, tuzaklar | [.claude/skills/nobet/SKILL.md](.claude/skills/nobet/SKILL.md) |
| X büyüme rehberi | [.claude/skills/sosyal-medya/SKILL.md](.claude/skills/sosyal-medya/SKILL.md) |
| Profil metinleri ve görseller | [marka/](marka/) |
| Ayarlar | `ayarlar.toml` |

## Nasıl çalışır
- `.github/workflows/kalkylerat.yml`: sabah analizi her gün 05:17 UTC; nabız ~7 dakikada bir (paylaşımlar, maç
  sonu postları, tablo sonuçları).
- `.github/workflows/nobet.yml`: nöbetçi; nabız durursa yeniden başlatır.
- Sağlık kontrolü her nabızda: sorun olursa GitHub'da `alarm` etiketli issue açılır, sahibine bildirim gelir.
- Saatlik Claude rutini ("Kalkylerat saatlik nöbet", Sonnet): `python -m bot.durum` ile kontrol eder, sorun varsa
  düzeltir ve telefona bildirim gönderir.
- GitHub'da her gün `💬 Yanıt kiti` (elle yanıtlar için taslak) ve `🎩 Mr. Likely` issue'su, her Pazartesi X Direktörü
  raporu açılır; yenisi açılınca eskisi kendiliğinden kapanır.

## Anahtarlar (Settings → Secrets and variables → Actions)
| İsim | Değer |
|---|---|
| `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET` | @kalkylerat X uygulaması (Read and write) |
| `X_LIKELY_API_KEY`, `X_LIKELY_API_SECRET`, `X_LIKELY_ACCESS_TOKEN`, `X_LIKELY_ACCESS_SECRET` | Mr. Likely hesabı |
| `API_FOOTBALL_KEY` | API-Football |
| `ODDS_API_KEY` | The Odds API (oranlar) |
| `ANTHROPIC_API_KEY` | Claude API (metin yazımı ve denetçi) |

## Test
```bash
pip install -r requirements.txt
python -m pytest -q      # sözleşme testleri dahil, hepsi yeşil olmalı
python -m bot.durum      # bugünün paylaşım durumu (yalnızca okur)
```

## Sorun giderme
- **"X API hatası 401/403"** → App izni "Read and write" değil ya da Access Token izin değişikliğinden önce üretilmiş.
  Tokeni yeniden üretip secret'ı güncelleyin.
- **"X API hatası 402"** → X geliştirici kredisi bitmiş olabilir.
- **"API-Football hatası … plan/season"** → plan güncel sezonu vermiyor.
