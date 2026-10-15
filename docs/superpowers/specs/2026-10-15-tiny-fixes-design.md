# Tiny Fixes: tasarım ve maliyet raporu (15 Ekim 2026)

Sahibinin isteği: trend sorunların yapay zekâ çözümleri ve yapay zekâ haberleri; X ve Instagram birlikte, her platformun
uzmanı kendi biçiminde; öncelik gelir; en düşük maliyet; günde 20–30 dakika sahip zamanı.

## Konsept
| Sütun | İçerik | Hedef | Çıkış |
|---|---|---|---|
| Fix | Trend sorun ve onu çözen, **gerçekten denenmiş** komut | kaydetme | sahibin `ok`'u (F6) |
| News | Kaynaklı yapay zekâ haberi: ne oldu, sana ne anlamı var | yanıt, repost | sahibin `ok`'u |
| Library | Evergreen komut kartı (yine denenmiş) | kaydetme, takip | otomatik (`mod = "otomatik"`) |

Fark: "Tested with <model>" ve açık sınır cümlesi (F2), iki bağımsız kaynak (F1), sahte deneyim yok (F3).

## Mimari
`flood_kaynak` → `flood_puan` → `flood_yazar.triage` → `flood_dogrula` → `flood_yazar.yaz` → `flood_denetci` → onay issue'su →
`flood` (yayın: X zinciri + Instagram carousel) → ölçüm. Ayrıntı: `.claude/skills/tiny-fixes/SKILL.md`. Mevcut parçalar yeniden
kullanıldı: `direktor._cagir` ve `yz_izi`, `onay.GitHub`, `yorum` (yorum kiti), `saglik.bildir`, `likely_yetki` akışı, `tweets.XClient`.

## Maliyet (USD/ay, tahmin)
| Kalem | Tutar | Dayanak |
|---|---|---|
| X Premium | ~8 (yıllık ~7) | üçüncü taraf kaynaklar (MacRumors vb.) |
| X API | ~8–12 | post ~0,015; okuma ~0,005; link ~0,20 (üçüncü taraf bloglar) |
| Claude API | ~15–25 | Sonnet 5.5 $2/$10, Haiku 5.5 $0,10/$0,50 per MTok; günde 2 trend + 1 evergreen birim (kendi token tahminim) |
| Instagram API | 0 | Meta belgesi; günde 3 post, sınırın altında |
| Görsel, barındırma, bülten, logo | 0 | Pillow, `flood-medya` dalı, ücretsiz katman |
| **Toplam** | **~35–45** | sıkı mod ~25 |

Doğrulanmayanlar: web arama aracının birim fiyatı, X API fiyatlarının güncelliği. İlk ay sonunda gerçek faturayla karşılaştırılır.

## Sınırlar ve açık noktalar
- Bu ortamdan Google Trends, Hacker News ve RSS adreslerine erişilemedi (proxy 403): ayrıştırıcılar örnek verilerle test edildi,
  canlı doğrulama GitHub Actions'ta ilk çalışmada yapılır. RSS adresleri doğrulanmadı.
- Instagram izin adı Meta belgelerinde iki farklı yazılmış; kurulumda canlı belgeden doğrulanır.
- Original Content Rewards: otomatik hesaplara açık olup olmadığı belirsiz; başvurmadan X'in Creator Monetization Standards sayfasından teyit.
- 15 Ekim (ikinci oturum) eklendi: ad "Tiny Fixes" ve yeni marka, öğrenme döngüsü (F10), haftalık rapor, Instagram yorum
  kiti, `flood_tani`, tembel trend doğrulaması. Depo herkese açık (doğrulandı). Instagram izin adı `instagram_business_content_publish`
  (Meta'nın güncel belgesi).
- Yapılmadı: Reels, affiliate/bülten katmanı (≈500 takipçiden sonra).
