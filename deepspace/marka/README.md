# Deep Space Log marka kiti (G16)

Sahibi 11 Kasım 2026'da onayladı. Renk seçimi bize bırakıldı: **A, film tonu yok** (`marka.toml [filtre] secim = ""`).
Kehribar (`#e8c48a`) yalnız vurgu: başlık altı çizgi ve etiket.

| Dosya | Ne | Kullanım |
|---|---|---|
| `kaynak/A2.png` | Ana görsel (ElevenLabs flux-3-image, 1360x768) | Banner, profil, kit sayfası bundan üretilir |
| `banner.jpg` | 2560x1440, yazı ortadaki 1546x423 güvenli alanda | YouTube kanal başlığı |
| `profil.png` | 800x800, ortada PROBE-7 (98 px dairede seçilir) | Kanal profil resmi |
| `filigran.png` | 150x150 şeffaf | Studio > Özelleştirme > Video filigranı |
| `marka_kitabi.jpg` | Tek sayfa özet | Sahibine ve ajanlara referans |

- Yeniden üretmek: `py -m deepspace.gorev kanal` (ya da `marka_kiti.uret()`).
- Kapak şablonu (`yazi.kapak_katmani`, `marka.toml [sablon]`): ortada harf aralıklı ince başlık (Space Mono), kehribar
  çizgi ve kalın kehribar etiket, gökte küçük PROBE-7. 3 düzen: başlık üstte, başlık altta, etiket önde. En fazla 3
  kelime (G7): başlık seri adı (`DEEP FOCUS`), etiket süre (`2H`). Hedef adı ve görev numarası video başlığındadır.
- Bu klasördeki her dosya (ve `marka.toml`) marka özetine girer; biri değişirse marka istasyonu yeniden denetlenir,
  sahibinin onayı yenilenir ve sonraki istasyonların kararları geçersiz olur. `taslak/` özete girmez.
