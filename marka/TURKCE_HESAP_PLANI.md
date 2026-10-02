# Türkçe hesap — bekleyen plan (sonra devam edilecek)

Durum (2 Ekim 2026): **beklemede.** Türkçe hesap açılmadı. Ana (İngilizce) hesap analiz konseptiyle çalışıyor.
Sonra kaldığımız yerden aynı şekilde devam edilecek.

## Karar verilmiş olanlar
- Konsept: kupon/oran/stake/kasa **yok**; yalnızca maç analizi (olasılıklar, skor dağılımı, istatistik ile piyasa
  karşılaştırması, maç sonu karnesi). İngilizce hesapla aynı motor, aynı analizler, Türkçe metin ve kart.
- Palet: antrasit zemin + altın vurgu (kazanan yeşil, kaybeden kırmızı kalır). Hazır görseller:
  `marka/kapak_tr.png`, `marka/logo_tr.png`. Kart dili hazır: `gorsel.analiz_karti(..., dil="tr")`,
  `gorsel.analiz_tablosu(..., dil="tr")`.
- Kurulum adımları ve biyografi: `marka/PROFIL_TR.md` (isim kararı değişirse güncellenecek).

## Açık kararlar (sahibinde)
1. **İsim.** Bağımsız değerlendirme "Kalkylerat"ın değişmesini önerdi; önerisi **Kalibre** (TR "kalibre",
   EN "calibre", SV "kalibrera"). Kullanıcı adları: @KalibreFC / @KalibreTR (müsaitlik kontrol edilmedi).
   Diğer adaylar: Probabol, ScoreLab/SkorLab, Poisson FC, TopMetrik. İsim değişirse iki hesap birlikte değişir.
2. **Avukat görüşmesi (7258 sayılı kanun).** Türkçe hesap ve özellikle ücretli katman, Türk bir ceza avukatının
   onayından önce açılmayacak.

## Türkçe hesaba özel kurallar (bağımsız değerlendirmeden)
- Oran, bahis, stake, Kelly, değer (value), kombine, martingale, kapanış oranı, Asya handikapı konuları **yok**.
  Bilgi postları futbol analitiği: xG, örneklem büyüklüğü, iç saha avantajı, gol dağılımı, şans.
- "Piyasa" yerine dikkatli dil (ör. "piyasa beklentisi" yerine "oranlara yansıyan beklenti" — avukata sorulacak).
- Süper Lig ve Türk takımları ağırlıklı; büyük Avrupa maçları.
- Ücretli katman: avukat açıkça onay vermeden yok. İngilizce hesap Türkçe hesabın otomasyon yöneticisi olarak
  bağlanmayabilir (hukuki ayrım; avukata sorulacak).

## Teknik yapılacaklar (anahtarlar gelince)
1. GitHub gizli anahtarları: `X_TR_API_KEY`, `X_TR_API_SECRET`, `X_TR_ACCESS_TOKEN`, `X_TR_ACCESS_SECRET`
   (Türkçe hesapla açılan ayrı developer uygulamasından).
2. Dil katmanı: analiz/tablo/ayrışma/anket/full time metinlerinin Türkçeleri; Türkçe bilgi konu listesi
   (yukarıdaki kurallara göre); Direktör'e Türkçe yazım yönergesi; denetçinin Türkçe yasak kelime listesi.
3. Etkileşim planının Türkçe hesap için ayrı kaydı (`gun["etkilesim_tr"]`), ayrı X istemcisi.
4. Testler: her Türkçe metin 280 sınırı, yasak kelimeler, Türkçe karakterler kartta.
