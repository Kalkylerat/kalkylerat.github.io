# Deep Space Log marka kiti (G16)

Durum: denetimde. Sahibi 11 Kasım 2026'da taslağı onayladı (renk **A, film tonu yok**, `marka.toml [filtre] secim = ""`);
12 Kasım 2026'dan beri kanalda kayıt defteri dilindeki banner ve profil duruyor (sahibi: "koyu mod harika olmuş").
15 Kasım 2026: kit bu tasarıma eşitlendi. Kesin kayıt denetçi GEÇTİ'den sonra `gorev marka --onay` ile yapılır.
Görsel ve grafik dilinin kuralları: `.claude/skills/gorsel-dili/SKILL.md` (bölüm 7).

| Dosya | Ne | Kullanım |
|---|---|---|
| `banner.jpg` | 2560x1440 uçuş kaydı sayfası, yazı ortadaki 1546x423 güvenli alanda; `taslak/banner_defter.jpg`'nin aynısı | YouTube kanal başlığı |
| `profil.png` | 800x800, mürekkep zeminde kehribar yörünge halkası içinde "7"; `taslak/profil_defter.png`'nin aynısı (98 ve 40 px dairede seçilir) | Kanal profil resmi |
| `filigran.png` | 150x150 şeffaf: profildeki halka-7 işareti, yarı saydam mürekkep disk üstünde | Studio > Özelleştirme > Video filigranı |
| `marka_kitabi.jpg` | Tek sayfa özet: banner, profil, filigran, kapak düzeni, palet | Sahibine ve ajanlara referans |

- Yeniden üretmek: `py -m deepspace.gorev kanal` (ya da `marka_kiti.uret()`). Banner ve profil onaylı dosyaların
  bayt bayt kopyasıdır (kanaldakiyle aynı kalır); onları çizen kod `taslak/defter_kiti.py`.
- Kapak düzeni (G7, `deepspace/kapak.py`): kehribar görev numarası, altında görev adı (büyük yazı en çok 3 kelime, ör.
  `001 SEVEN WORLDS`), kehribar çizgi, küçük gerçek veri satırı (hedef, gök koordinatı, uzaklık), köşe nişanları, küçük
  `DEEP SPACE LOG · PROBE-7` imzası. Seri adı, süre ve söz veren yazı kapağa yazılmaz. Üç varyant görevin üç ayrı
  parçasının sahnesidir (`kapak_parcalari`). Kit sayfasındaki örnek yalnız düzeni gösterir (zemin mürekkep).
- PROBE-7 yalnız arayüzde ve marka işaretinde görünür (halka içinde 7; banner'daki uçuş hattında küçük baklava);
  sahneye sonda çizilmez (G1).
- Bu klasördeki her dosya (ve `marka.toml`) marka özetine girer; biri değişirse marka istasyonu yeniden denetlenir,
  sahibinin onayı yenilenir ve sonraki istasyonların kararları geçersiz olur. `taslak/` özete girmez (eski fotoğraf
  zeminli kit ve kaynağı `A2.png` orada, tarihçe olarak).
