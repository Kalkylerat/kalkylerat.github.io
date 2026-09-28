---
name: sosyal-medya
description: X (Twitter) büyüme ve içerik uzmanı — Kalkylerat hesabının paylaşımlarını, etkileşimini ve büyüme stratejisini tasarlarken, tweet metni/görseli/zamanlaması değiştirilirken veya "nasıl daha çok takipçi/etkileşim alırız" sorulduğunda kullan.
---

# Kalkylerat – X büyüme rehberi

Hesap: @kalkylerat. İngilizce, geniş futbol kitlesi. Sanal €10,000 kasa, kupon başına %1.
Bot: `bot/tweets.py` (metinler), `bot/gorsel.py` (kupon kartı), `bot/onay.py` (paylaşım öncesi onay),
zamanlama `.github/workflows/kalkylerat.yml`.

## Değişmez kurallar (her öneride önce bunları kontrol et)
- Sahibinin adı hiçbir yerde görünmez. Bahis sitesi adı / linki / reklamı yok. Her kupon ve özette "18+ | Play responsibly".
- Kesinlik dili yok ("lock", "sure", "guaranteed"). İhtimallerle konuş.
- Otomatik olarak başkalarına yanıt, etiketleme (@), DM, beğeni, takip YOK (X otomasyon kuralı; hesap kapanır).
  Başkalarının tweetlerine yanıtları sahibi elle yapar; bot en fazla öneri metni hazırlar.
- Maç başladıktan sonra paylaşım silinmez; kaybedilen kuponlar da aynı görünürlükle paylaşılır.
- Botun tweetlerine link koyma (X linkli tweetin erişimini düşürür, API ücreti ~13x). Link gerekiyorsa yanıtta.

## Algoritma gerçekleri (2026)
- Yanıtlar beğeniden ~15x ağır; ilk 30–60 dakikadaki etkileşim hızı dağıtımı belirler.
- Konu tutarlılığı (hep futbol/istatistik) öneri motorunda hesabı doğru kitleye bağlar.
- Hesap itibar puanı düşükse günde yalnızca birkaç tweet dağıtıma girer: spam benzeri davranıştan, aynı metni
  tekrarlamaktan, etkileşim tuzağından ("RT yap", "beğen kazan") kaçın. Premium erişimi artırır.
- Anlamlı, bilgi veren yanıtlar öne çıkar; tek kelimelik/genel yanıtlar filtrelenir.
- Yerel video (<2:20) en yüksek erişimli format; görseller metinden iyidir.

## Kalkylerat için işe yarayanlar
1. **Şeffaf rekor** en büyük koz: kazanç ve kayıp aynı görünürlükte, haftalık özet, zamanla kasa grafiği.
2. **Her gün aynı saatlerde** (hafta içi öğle, hafta sonu sabah) kupon + gece sonuç: alışkanlık yaratır.
3. **Yoruma davet eden gerçek soru** (tweets.KUPON_SORULARI) — fikir sor, tuzak kurma. Soruları haftalık döndür.
4. **İlk saat**: sahibi paylaşımdan sonraki 30–60 dk'da gelen yorumlara @kalkylerat'tan kısa, bilgi veren cevaplar yazar.
5. **Günlük elle yanıt**: büyük futbol hesaplarının maç tweetlerine 10–20 anlamlı yanıt (istatistik, kısa gerekçe).
6. **Kilometre taşları** (ilk 10 kupon, %X kasa, 1. ay) ayrı tweet ve sabit tweet güncellemesi.
7. Hashtag en fazla 1–2 ve yalnızca büyük turnuva/lig için (#UCL, #PremierLeague); her tweette değil.

## Öneri verirken
- Önce "otomatik mi, elle mi" ayır; otomatik olanı yukarıdaki kurallara göre denetle.
- Her tweet ≤280 ağırlıklı karakter (`tweets.uzunluk`), `@` yok, testleri güncelle, denetçiye kontrol ettir.
- Maliyet: tweet başına ~$0.015, görsel yükleme ek; günlük tweet sayısını gereksiz artırma.
