---
name: sosyal-medya
description: X (Twitter) büyüme ve içerik uzmanı — Kalkylerat hesabının paylaşımlarını, etkileşimini ve büyüme stratejisini tasarlarken, tweet metni/görseli/zamanlaması değiştirilirken veya "nasıl daha çok takipçi/etkileşim alırız" sorulduğunda kullan.
---

# Kalkylerat – X büyüme rehberi

Hesap: @kalkylerat. İngilizce, geniş futbol kitlesi. **Konsept (Ekim 2026'dan beri): analiz** — kupon, stake,
kasa yok. Her gün bütün maçlar analiz edilir (`bot/analiz.py`, data/analiz/<tarih>.json); X'te günde 3 analiz kartı
(`gorsel.analiz_karti`), maç bitince kartın alıntısıyla "ne dedik, ne oldu" (`etkilesim.analiz_takibi`), anket,
günün maçları, bilgi postu. Plan: Türkçe hesap (@kalkyleratTR, altın palet) ve bütün analizler için ücretli kanal.
Eski kupon düzeni `ayarlar.toml` konsept.mod = "kupon" ile geri açılabilir; aşağıdaki kupon maddeleri o düzen içindir.
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

## Ölçülen durum (3 Ekim 2026, `metrik` komutu → data/metrikler.json)
- 37 post, post başına ~5,6 görüntülenme, 1 takipçi, 0 takip edilen, 0 beğeni. Yayın tek başına görünürlük getirmiyor.
- Kaldıraçlar: (1) sahibinin elle, büyük hesapların maç postlarına ilk 30–60 dakikada yanıtları (bot her sabah
  "yanıt kiti" issue'su hazırlar: kit.py); (2) X Toplulukları ([topluluk] id, API community_id); (3) hesabın insan
  gibi davranması: ilgili 50–100 hesabı takip, beğeni, sohbet (otomatikleştirilemez, X kuralı).
- Otomatik takip/beğeni/yanıt yapan araçlar (XActions, Cloudflare atlatan kazıyıcılar) X kurallarına aykırı:
  hesabı kapatır. Kullanılmaz.

## Kalkylerat için işe yarayanlar
1. **Şeffaf rekor** en büyük koz: kazanç ve kayıp aynı görünürlükte, haftalık özet, zamanla kasa grafiği.
2. **Her gün aynı saatlerde** (hafta içi öğle, hafta sonu sabah) kupon + gece sonuç: alışkanlık yaratır.
3. **Yoruma davet eden gerçek soru** (tweets.KUPON_SORULARI) — fikir sor, tuzak kurma. Soruları haftalık döndür.
4. **İlk saat**: sahibi paylaşımdan sonraki 30–60 dk'da gelen yorumlara @kalkylerat'tan kısa, bilgi veren cevaplar yazar.
5. **Günlük elle yanıt**: büyük futbol hesaplarının maç tweetlerine 10–20 anlamlı yanıt (istatistik, kısa gerekçe).
6. **Kilometre taşları** (ilk 10 kupon, %X kasa, 1. ay) ayrı tweet ve sabit tweet güncellemesi.
7. **Doğru tahmin, kötü fiyat** ("GOOD CALL, POOR PRICE", `etkilesim.deger_tweeti`): kazanmasını beklediğimiz ama
   oranı adil oranımızın altında olduğu için kupona koymadığımız maçlar (ör. Almanya %80, oran 1.20, adil 1.25).
   Disiplini gösterir ("olası sonuç ≠ değerli bahis"), maç bitince "haklı mıydık" konuşması doğurur. Tavsiye değildir:
   "kuponda değil" çerçevesi, ihtimal + oran + adil oran ve 18+ satırı hep durur; "oynayın" denmez.
   Maçlar bitince bu post **alıntılanır** ("HOW THEY ENDED", `etkilesim.deger_takibi`): skorlar, tahminin tutup
   tutmadığı ve fiyatın neden yine de önemli olduğu tek satırda (ör. "€100 on each made just +€50"). Haklı da çıksak
   yanılsak da paylaşılır: şeffaflık hesabın kozu.
8. **Soru kuponla tutarlı olmalı**: tek maçlık kuponda çoğul ya da karşılaştırma sorusu sorulmaz ("hangi sonuç
   şaşırttı?" — başka maç yok). Tek maçta soru o maçın adıyla sorulur ("How did you read Wales v Norway?").
9. **Günlük bilgi postu** (`bot/bilgi.py`, 20 konu sırayla): oran = olasılık, marj, değer, kombine, kayıp serileri,
   %1 kasa, Kelly, Asya handikapı, Poisson, xG, örneklem, kapanış oranı… Sayıların hepsi tanım gereği doğru ya da
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
