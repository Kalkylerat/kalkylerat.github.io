---
name: sosyal-medya
description: X (Twitter) büyüme ve içerik uzmanı — Kalkylerat hesabının paylaşımlarını, etkileşimini ve büyüme stratejisini tasarlarken, tweet metni/görseli/zamanlaması değiştirilirken veya "nasıl daha çok takipçi/etkileşim alırız" sorulduğunda kullan.
---

# Kalkylerat – X büyüme rehberi

Hesap: @kalkylerat. İngilizce, geniş futbol kitlesi. **Konsept: analiz** (Ekim 2026'dan beri; kupon, stake,
kasa yok). Her gün bütün maçlar analiz edilir (`bot/analiz.py`, data/analiz/<tarih>.json); X'te sabah tablosu, analiz
kartları (`gorsel.analiz_karti`; yoğun günde 30'a kadar), maç bitince kartın alıntısıyla maç sonu postu
(`etkilesim.analiz_takibi`), tablo altına sonuç yanıtları, anket, günün maçları, iki bilgi postu. Kurallar SOZLESME.md.
Plan: Türkçe hesap (@kalkyleratTR, altın palet) ve bütün analizler için ücretli kanal. Kupon yalnızca Mr. Likely'de.
Bot: `bot/etkilesim.py` (paylaşım akışı), `bot/tweets.py` (metinler), `bot/gorsel.py` (görseller),
zamanlama `.github/workflows/kalkylerat.yml`.

## Değişmez kurallar (her öneride önce bunları kontrol et)
- Sahibinin adı hiçbir yerde görünmez. Bahis sitesi adı / linki / reklamı yok. Her postta "18+" satırı.
- Kesinlik dili yok ("lock", "sure", "guaranteed"). İhtimallerle konuş.
- Otomatik olarak başkalarına yanıt, etiketleme (@), DM, beğeni, takip YOK (X otomasyon kuralı; hesap kapanır).
  Başkalarının tweetlerine yanıtları sahibi elle yapar; bot en fazla öneri metni hazırlar.
- Maç başladıktan sonra paylaşım silinmez; tutmayan analiz de maç sonu postunda aynı görünürlükle yazılır.
- Botun tweetlerine link koyma (X linkli tweetin erişimini düşürür, API ücreti ~13x). Link gerekiyorsa yanıtta.

## Algoritma gerçekleri (2026)
- Yanıtlar beğeniden ~15x ağır; ilk 30–60 dakikadaki etkileşim hızı dağıtımı belirler.
- Konu tutarlılığı (hep futbol/istatistik) öneri motorunda hesabı doğru kitleye bağlar.
- Hesap itibar puanı düşükse günde yalnızca birkaç tweet dağıtıma girer: spam benzeri davranıştan, aynı metni
  tekrarlamaktan, etkileşim tuzağından ("RT yap", "beğen kazan") kaçın. Premium erişimi artırır.
- Anlamlı, bilgi veren yanıtlar öne çıkar; tek kelimelik/genel yanıtlar filtrelenir.
- Yerel video (<2:20) en yüksek erişimli format; görseller metinden iyidir.
- Yanıt > repost ≈ bookmark > beğeni; "ilgilenmiyorum", sessize alma, şikâyet ağır ceza. Tablolar ve sayılar
  bookmark aldırır (kaydedilecek içerik). Ayrıntı: references/x-algoritma.md (sergebulaev/x-skills, MIT).
- Birbirine çok benzeyen postlar benzerlik cezası alır: hafta sonu 15 dakikalık kart akışında kapanış sorusu maça
  özel ve dönüşümlü (etkilesim.kart_sorusu); aynı kalıp art arda gitmesin.
- Yapay zekâ izleri erişimi ve güveni düşürür: "The result?", "Here's what", "It's not X, it's Y", samimiyet
  ilanları, aynı postta 3+ yapay zekâ kelimesi (significant, crucial, notably, leverage…), 1'den fazla uzun tire.
  Direktör metninde varsa kod şablona döner (direktor.yz_izi).
- Hashtag: kaynak rehber 0–1 öneriyor (2+ spam gibi okunabilir). Bizde kart postunda en fazla 2, liste postunda
  sahibinin isteğiyle maçların taraftar etiketleri var; etkileşim verisine göre azaltmayı değerlendir.
- Kapanış: genel "ne düşünüyorsun?" yerine belirli soru; tek bir net çağrı (yanıt, kaydet ya da repost), hepsi değil.

## X kuralları: ban riskine karşı kodda sabit olanlar (her değişiklikte koru)
- Hesap "Automated" etiketi taşımalı ve sahibinin insan hesabına bağlı olmalı (X ayarı; sahibi elle açar).
- Başkalarına otomatik yanıt, etiketleme, DM, takip, beğeni YOK. Bot yalnızca kendi postlarına yanıt/alıntı yapar;
  başkalarına yanıtlar yanıt kitiyle sahibi tarafından elle, metni değiştirilerek atılır.
- Trend konularda otomatik post yok; otomatik postta en fazla 1 ilgili hashtag (liste postunda 2), genel/trend
  etiketi (#Football, #FootballPredictions) yok (tweets.LISTE_ETIKET_SINIRI, etiket_satiri).
- Aynı metin aynı gün iki kez paylaşılmaz (etkilesim._TekrarKorumasi); günde en fazla 40 post (maç sonu ve tablo
  yanıtları hariç), postlar arası en az 13 dk (yoğun gün) / 45 dk (normal gün); tablo yanıtları nabız başına en fazla 3.
- Topluluğa günde yalnızca tablo ve oran/istatistik postu; kartlar gitmez.
- Yalnızca resmi API; kazıyıcı, tarayıcı otomasyonu, Cloudflare atlatma yok.
- Bahis dili yok, kesinlik dili yok, link yok (denetçi + direktör kuralları).

## Ölçülen durum (3 Ekim 2026, `metrik` komutu → data/metrikler.json)
- 37 post, post başına ~5,6 görüntülenme, 1 takipçi, 0 takip edilen, 0 beğeni. Yayın tek başına görünürlük getirmiyor.
- Kaldıraçlar: (1) sahibinin elle, büyük hesapların maç postlarına ilk 30–60 dakikada yanıtları (bot "yorum
  fırsatları" hazırlar: firsat.py, madde 5; kapalıyken eski "yanıt kiti", kit.py); (2) X Toplulukları ([topluluk] id, API community_id); (3) hesabın insan
  gibi davranması: ilgili 50–100 hesabı takip, beğeni, sohbet (otomatikleştirilemez, X kuralı).
- Otomatik takip/beğeni/yanıt yapan araçlar (XActions, Cloudflare atlatan kazıyıcılar) X kurallarına aykırı:
  hesabı kapatır. Kullanılmaz.

## Kalkylerat için işe yarayanlar
1. **Şeffaflık** en büyük koz: her kartın maç sonu postu, tutsa da tutmasa da maç öncesi yüzdeyle aynı görünürlükte.
   Pazartesi haftalık karne (`etkilesim.hafta_ozeti`, SOZLESME A9): kartların ana yüzdeleri ortalaması, kaçının olduğu,
   oran mı istatistik mi olana yakındı; günlük "Who's right: the odds or the stats?" sorusunun haftalık cevabı.
2. **Her gün aynı ritim**: sabah tablo, gün boyu kartlar, akşam tablo ve sonuçlar; alışkanlık yaratır.
3. **İlk satır hikâye** (22 Ekim 2026): kart ve post maçın tek cümlelik hikâyesiyle açılır (`analiz.hikaye`; en güçlüsü
   "oranlar X diyor, takım istatistiği Y diyor"). Akışta durduran şey "MATCH CHANCES" etiketi ya da rakam yığını değil.
   Direktör hikâyeyle açmazsa şablon gider (`direktor.hikaye_basta`). Kartta renk tek anlam taşır.
4. **Yoruma davet eden gerçek soru** (etkilesim.kart_sorusu): maça özel, dönüşümlü; tuzak kurma.
5. **İlk saat**: sahibi paylaşımdan sonraki 30–60 dk'da gelen yorumlara @kalkylerat'tan kısa, bilgi veren cevaplar yazar.
   Yorum kiti (`bot/yorum.py`, SOZLESME D3): yeni yorumlar gündüz 30 dk'da bir okunur, "💬 Yorumlar" issue'suna 3 cevap
   taslağıyla düşer (telefona bildirim). Bot cevap atmaz; sahibi taslağı düzeltip elle atar.
6. **Günlük elle yanıt**: büyük futbol hesaplarının maç tweetlerine 10–20 anlamlı yanıt (istatistik, kısa gerekçe).
   Yorum fırsatları (`bot/firsat.py`, SOZLESME D3): bot bu postları kendisi bulur (X arama, `[buyume]` ayarı),
   "🚀 Yorum fırsatları" issue'suna bağlantı + 2 taslakla gönderir; sahibi yapıştırıp elle atar. Eski yanıt kiti
   (arama bağlantıları) fırsatlar açıkken gönderilmez.
7. **Kilometre taşları** (1. ay, 1.000 analiz) ayrı tweet ve sabit tweet güncellemesi.
8. **Soru posta uygun olmalı**: tek maçlık postta çoğul ya da karşılaştırma sorusu sorulmaz; soru o maçın adıyla
   sorulur ("How did you read Wales v Norway?").
9. **Günlük bilgi postu** (`bot/bilgi.py`, 20 konu sırayla): oran = olasılık, marj, oran hareketi, kombine, seriler,
   en olası gol sayısı, 0-0, kalesini gole kapatma, Poisson, en olası skor, xG, örneklem, kapanış oranı… Sayıların hepsi tanım gereği doğru ya da
   kodda hesaplanmış; istatistik iddiası yok. Direktör doğal dille yazar ama olgularda olmayan sayı kullanamaz (kod
   denetler). Sonunda gerçek bir soru. Robot gibi değil: her gün farklı açılış, kalıp cümle yok.
10. **Hashtag:** taraftarların zaten kullandığı etiketler (`tweets.MILLI_ETIKETLER`: #BizimÇocuklar, #ThreeLions,
    #LesBleus...; kulüpler: #Arsenal, #COYS...). Uydurma kod etiketi (#FRAITA) yok. Liste postu (günün analiz tablosu)
    istisna (sahibinin kararı): tablodaki maçların takım etiketleri + turnuva + #Football #FootballPredictions, en
    fazla 8. Bahis etiketleri (#BettingTips) hiçbir postta yok. Diğer postlarda en fazla 1–2 ve yalnızca büyük turnuva/lig için (#UCL, #PremierLeague); her tweette değil.

## Öneri verirken
- Önce "otomatik mi, elle mi" ayır; otomatik olanı yukarıdaki kurallara göre denetle.
- Her tweet ≤280 ağırlıklı karakter (`tweets.uzunluk`), `@` yok, testleri güncelle, denetçiye kontrol ettir.
- Maliyet: tweet başına ~$0.015, görsel yükleme ek; günlük tweet sayısını gereksiz artırma.
