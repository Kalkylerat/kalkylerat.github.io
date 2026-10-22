# Mr. Likely (kupon hesabı, X)

**Durum (22 Ekim 2026):** çalışıyor, otomatik mod. 21 Ekim: 5 kupon, 2 tuttu, 3 yattı, hepsinin sonuç postu çıktı.

## Ne yapıyor
- Kuponu sabit kurallar seçer (SOZLESME E6): toplam oran 2–4, en fazla 4 ayak, günde en fazla 5 kupon, öğlen oran
  tazeleme. Görselli kupon postu, kupon postunu alıntılayan sonuç postu, günde en fazla 4 bilgi postu, Pazartesi
  haftalık karne (kaybedenler dahil).
- Sonuç postu kuponu belirleyen geç golü anlatır ("88': 2-0. Still fine. 90+3': 3-0. Of course it was.").
- Cevap taslakları insan sesiyle (15 Ekim, PR #70). Ses ve karakter: `marka/MR_LIKELY.md`.
- Yanlış oranlı kupon maç başlamadan `likely_iptal` ile silinebilir (E5'e tek istisna, 14 Ekim).

## Açık işler
- [ ] `claude/daily-coupon-teaser-2bolvm` dalını ana dala al (21 Ekim): ilk kupondan önce "bugün N kupon" duyuru postu.
- [ ] Gölge test kararı: DC12 çıkarılsın mı, fiyat sınırı gevşesin mi? 13 Ekim'de 1–2 hafta beklenmesi kararlaştırıldı;
      rapor sabah bildiriminin sonunda. Kural gevşetmek sahibinin onayıyla (CLAUDE.md).
- Bilinen risk: `data/likely_x.enc` herkese açık depoda; anahtar `X_API_SECRET`'tan türetiliyor. O sır sızarsa bu
  token da çözülür.

## Karar geçmişi
- 13 Ekim: 6–12 Ekim sonuçları günün kuponu 5'te 2, long shot 6'da 1; DC12 7'de 3. Gölge test kuruldu, karar kuralı
  z>2. "Gala günü" reddedildi. X API 402 (kredi bitti) çözüldü.
- 14 Ekim: DC12 yasağı (E6), E7 zamanlaması (maçtan ≥45 dk önce), 2,05'lik aykırı oran → `AYKIRI_FIYAT` %8 ve +%15
  değer tavanı, `likely_iptal` (E5 istisnası).
- Yorum fırsatları günde 5 (10/13/16/18 UTC), "📋 Kopyala ve postu aç" sayfasıyla elle.
- 15 Ekim: insan sesli cevap taslakları (PR #70). 18 Ekim: günde 5 kupon + öğlen tazeleme (PR #102).

## İlk mesaj
> Mr. Likely üzerinde çalışacağız. CLAUDE.md, SOZLESME.md E bölümü, marka/MR_LIKELY.md ve projeler/mr-likely.md
> dosyalarını oku. `python -m bot.durum` ile son kuponları kontrol et, açık işleri özetle ve ilk işe geçmeden onayımı
> bekle. Kupon kurallarını bana sormadan gevşetme.
