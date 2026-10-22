# Projeler: durum ve açık işler

Bu depodaki projelerin tek sayfalık özetleri (22 Ekim 2026). Her dosyada durum, kararlar, açık işler ve yeni bir
Claude oturumuna yapıştırılacak ilk mesaj var. Bir iş bitince ilgili dosyanın **Durum** satırını ve açık işler listesini
güncelle.

| Proje | Dosya | Durum | Sıradaki adım |
|---|---|---|---|
| Kalkylerat (analiz, X) | [kalkylerat.md](kalkylerat.md) | çalışıyor | e-posta yağmuru düzeltmesini ana dala al |
| Mr. Likely (kupon, X) | [mr-likely.md](mr-likely.md) | çalışıyor, otomatik | sabah duyuru postunu ana dala al |
| Tiny Fixes (yapay zekâ, X + Instagram) | [tiny-fixes.md](tiny-fixes.md) | kod hazır, `mod = "kapali"` | sahibinin kurulum adımları |
| YouTube kanalı (Tiny Fixes) | [youtube.md](youtube.md) | tasarım | yüz düzeni kararı |

Değişmez kurallar her zaman `SOZLESME.md`'de; bu klasör yalnızca durum özetidir, kural koymaz.

## Ana dala alınmamış dallar

Bot `claude/twitter-football-predictions-ywwfxw` dalından çalışır. Aşağıdakiler o dalda yok:

| Dal | Tarih | İçerik |
|---|---|---|
| `claude/email-notification-cleanup-314g6n` | 16 Ekim | Bildirimler tek kanal (C2): X 503/kopya döngüsü, nöbetçi alarm yağmuru, tablo sonuç gecikmesi |
| `claude/daily-coupon-teaser-2bolvm` | 21 Ekim | Mr. Likely sabah duyuru postu ("bugün N kupon"), testleriyle |
| `ccr-53dc4a08-tzpiit` | 12 Ekim | `MALIYET.md` (aylık maliyet ve işletme devir notu) |
| `claude/x-page-automation-monetization-7mjcki` | 8 Ekim | `marka/B2B_TEKLIF.md` (fikir, bot dışı) |
| `claude/three-agent-brainstorm-automation-sdb84b` | 1 Ekim | `beyin/firsat-botu.md` (İsveççe fırsat botu devir notu, fikir) |
| `claude/chrome-music-generation-9cyq2h` | 1 Ekim | `suno/` (Suno müzik skill'i, bot dışı) |

İlk ikisi doğrudan botu etkiler. Birleştirmeden önce ana dalla çakışmasına bakılmalı ve `python -m pytest -q` yeşil olmalı.

## Silinmeyecekler

- "Kalkylerat (Do Not Delete)" oturumu ve ona bağlı, devre dışı "Kalkylerat saatlik sağlık kontrolü" rutini. Bir rutini
  silmek başlattığı oturumları da siler.
