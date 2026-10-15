---
name: instagram
description: Instagram büyüme ve içerik uzmanı (Tiny Fixes hesabı) — carousel tasarımı, caption, etiket, zamanlama, API ile yayın kuralları ve "X'ten farkı ne" sorularında kullan; Instagram metni/görseli değişirken ya da yayın hatası incelenirken de.
---

# Instagram uzmanı (Tiny Fixes)

Hesap: Tiny Fixes (İngilizce, yapay zekâ). X'te aynı doğrulanmış kayıttan **ayrı** bir parça yazılır: X'in
sosyal-medya skill'i flood'u, bu skill carousel'i yönetir. Kurallar SOZLESME.md F bölümü; kod `bot/flood_gorsel.py`,
`bot/flood_ig.py`, `bot/flood_yazar.py`. **Kaynakların çoğu pazarlama blogudur**; "kanıtlı" işaretli olanlar Meta'nın
kendi belgesine ya da Mosseri'nin açıklamasına dayanır, "varsayım" işaretliler ölçümle öğrenilecektir.

## Algoritma (kanıtlı)
- Mosseri'nin (Ocak 2025) üç ana sinyali: **izlenme süresi, görüntüleme başına beğeni, görüntüleme başına gönderme (send)**.
  Takipçi olmayanlara erişimde gönderme en güçlü sinyal olarak anlatılıyor. Kaydetme resmî üç sinyalde yok ama
  sıralama modellerinde kullanıldığı söyleniyor.
- Instagram her yüzeyi (Feed, Reels, Explore) ayrı sıralar; Reels'te kazanan Feed'de kazanmaz.
- Özgün içerik ödüllendirilir, başkasının içeriğini derleyen "aggregator" hesaplar cezalanır (2026 kaynakları).
  Bizim içeriğimiz kendi denediğimiz çıktıdır: bu bizim farkımız.

## Biçim kararları
- **Carousel, Reels değil** (başlangıçta): video üretimi maliyet ve karmaşıklık ekler. 5–8 slayt, 4:5 (1080×1350) JPEG.
- **Slayt 1 = tüm huni.** Büyük, tek başına anlaşılan kanca + "Tested with <model>". Son slayt: tek çağrı, **kaydet ya da bir
  arkadaşına gönder** (gönderme hedefi: "bu sorunu olan birine gönder").
- Slayt başına tek fikir; komut slaytı mono fontlu kart (kopyalanabilir). Metin okunur boyutta kalır (`flood_gorsel`).
- **Slayt 2 = özet kart** (`flood_gorsel.kart_gorseli`): düz soru vs bizim komut vs sınır (F15). X'teki kart postunun
  görselinin aynısı; "Swipe for the prompt" ile okuyanı sonraki slayta taşır.
- Caption: ilk satır insanların aradığı düz kelimeler (arama kelimeleri, varsayım: caption Instagram aramasında okunur),
  ≤600 karakter, tek çağrı. Caption'a link konmaz (tıklanmaz); tek tıklanabilir adres profil bağlantısıdır.
- Etiket: en fazla 3 öneri, hard limit 5 (F8). Genel/trend etiketi yok. Varsayım: etiket menzil için az iş görür, ölçüyoruz.

## Yayın (Meta belgesine göre, kanıtlı)
- Yalnızca **Business ya da Creator** hesap; kişisel hesaba API ile paylaşılamaz. Instagram Login yolu Facebook Sayfası
  istemez; yalnızca kendi hesabımıza yayınladığımız için App Review gerekmez (Standard Access).
- 24 saatte en fazla 100 API gönderisi (üçüncü taraf kaynaklar 25 ve 50 diyor; biz günde en fazla 3 atıyoruz, kalan hakkı
  `content_publishing_limit` ile soruyoruz). Carousel tek gönderi sayılır.
- Meta görseli kendisi çeker: adres **herkese açık** ve **JPEG** olmalı. Carousel: her slayt için container, hepsi FINISHED
  olunca carousel container'ı, sonra yayın. Biz görselleri `flood-medya` dalında (`raw.githubusercontent.com`) barındırırız.
- Uzun ömürlü anahtar 60 gün geçerli; bot 30 günde bir yeniler (`flood_yetki`).

## Yapmayacaklarımız (F7 ve platform kuralları)
- Başkalarına otomatik yorum, beğeni, takip, DM, etiketleme: yok. Bot yalnızca kendi gönderisini atar.
- Takipçi/etkileşim satın alma, "pod", yorum karşılığı beğeni: yok. Aynı carousel'i iki kez atma (D2 + benzerlik).
- Gerçekçi görünen yapay zekâ görseli kullanmıyoruz (yalnızca metin kartları); yapay zekâ çıktısını "Tested with" ile açıkça
  söylüyoruz. Meta'nın yapay zekâ etiketi gereken içerik üretirsek önce sahibine sor.

## Büyüme kaldıraçları (elle, günde 20–30 dk)
1. İlk saatte gelen yorumlara cevap (bot taslak hazırlar, cevabı sahibi atar).
2. İlgili hesapların gönderilerine günde 10–15 anlamlı yorum (elle, bilgi veren).
3. Kaydedilen ve gönderilen carousel türünü ölç (`data/flood.json` → `olcum.ig`: erişim, kaydetme, gönderme) ve o biçimi çoğalt.
4. Reels'i yalnızca carousel ölçümü oturunca düşün.
