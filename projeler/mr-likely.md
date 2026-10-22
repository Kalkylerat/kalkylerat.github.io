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

## İlk mesaj
> Mr. Likely üzerinde çalışacağız. CLAUDE.md, SOZLESME.md E bölümü, marka/MR_LIKELY.md ve projeler/mr-likely.md
> dosyalarını oku. `python -m bot.durum` ile son kuponları kontrol et, açık işleri özetle ve ilk işe geçmeden onayımı
> bekle. Kupon kurallarını bana sormadan gevşetme.
