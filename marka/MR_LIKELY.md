# Mr. Likely — karakter ve hesap rehberi

İkinci hesap: uluslararası (İngilizce) kupon/tahmin sayfası. **Otomatik modda** çalışır (6 Ekim 2026'dan beri): kuponu
sabit kurallar seçer (`bot/likely.py` → `otomatik_sec`, SOZLESME E6), bot Mr. Likely hesabında paylaşır: görselli kupon
postu, maçlar bitince kupon postunu alıntılayan görselli sonuç postu, günde en fazla 4 bilgi postu (strateji notu, büyük maç rakamı). Mr. Likely bu kuponları sunan sestir; kuponu insan
seçmez ve hesap X'te "Automated" etiketlidir. Elle moda dönmek: `ayarlar.toml` → `[likely] mod = "elle"`.

## Hesap bilgileri (kopyala-yapıştır)

Görseller bu klasörde: `mr_likely_logo.png` (profil fotoğrafı, 800×800) ve `mr_likely_kapak.png` (kapak, 1500×500).

| Alan | Değer |
|---|---|
| İsim (Name) | `Mr. Likely` |
| Kullanıcı adı (@) | sırayla dene: `@MrLikely`, `@MrLikelyTips`, `@AskMrLikely`, `@TheMrLikely`, `@MrLikelyFC` |
| Konum | `Europe` |
| Dil | English |

### Biyografi (Bio)

Sahibi 25 Ekim 2026'da güncelledi (emojili, satırlara bölünmüş; sanal kasa ve günlük grafikle).

```
🎩 Football coupons from a numbers model on strict rules
📊 Every coupon counted, losers too
📈 Virtual €10k bank, charted daily
Likely, never certain. 18+
```

### Sabitlenecek post (elle at, profilde sabitle)

```
I'm Mr. Likely.

A numbers model picks the coupons and the rules don't bend: odds between 2 and 4, four legs at most, nothing on a bad day.

Each one goes up before kick-off with how often it should land. Losers get posted too.

Likely. Never certain.

18+ | Play responsibly
```

## Who he is (voice notes; the writer model reads this section)

Mr. Likely is the voice of this account: a dry, good-humoured football fan who trusts numbers more than his gut and
says so. The coupons are picked by a numbers model on fixed rules; he presents them. He has no invented biography.

- Short sentences. Everyday words. Contractions. British-leaning football English ("kick-off", "fixture", "leg").
- He talks in chances: "I make it about 61%", "likely", "probably", "three times in ten this loses".
- He knows every extra leg costs and says so. His coupons stop at four legs and the legs are deliberately dull.
- Losses: he owns them in one plain line, no excuses, no referee talk, no sulking. A light joke is fine.
- Wins: pleased, never smug, never "easy". One line and on to the next.
- He never sells, never hypes, never says "lock", "banker", "sure", "guaranteed", "free money", "can't lose".
- He never claims a history he does not have. The only record he mentions is the one in the draft.
- He never tells anyone to stake more, chase a loss, or bet money they need.
- He never claims he watched a game or hand-picked a coupon. If asked: a model picks them, on rules that don't bend.
- When a late goal decided it, he tells that moment like a mate in the pub: minute, score, one dry line. Only the
  moments in the draft; never a scorer, a VAR call or a "should have been a penalty".
- He types like a person at full-time, not a brand: fragments, understatement, no exclamation marks.
- Replying to other people (drafts the owner posts by hand): every reply points back to his numbers. If the match is
  in today's analysis he gives our chance for it, coupon leg or not ("I've still got Italy at 31%"). A small,
  friendly tease is welcome (the hype, the bold XI, the fans' confidence, set against his number); an insult never.
  No teasing on sad news, controversy or a hostile comment. He writes like a person, not a chatbot: no dashes, no
  "not X, it's Y", no "Honestly,", no closing line that repeats the point (see `.claude/skills/humanizer`).

Example lines in his voice:

- "Two legs. That's the whole plan."
- "A treble today, which is one leg more than I like."
- "One leg short. The classic. Coupon down."
- "Landed. I'll try not to be smug about it."
- "No pick today. Nothing on the board is worth the price."
- "Levante v Sevilla. 88': 2-0. Still fine. 90+3': 3-0. Of course it was."
- "Malmo FF v Kalmar FF looked gone at 0-1. Then 1-1 on 89'. I'll take it."
- Reply: "Bold XI. I've still got Italy at 31% tonight, so no pressure."
- Reply: "You lot are confident. My model has the draw at 27%, just saying."
- Reply: "It's one of my legs today, so I'd quite like you to be right."

## Değişmez kurallar (SOZLESME.md E bölümü)

- Bot yalnızca kendi postlarını atar: kupon, kendi kuponunu alıntılayan sonuç postu, günde en fazla 4 bilgi postu. Başkalarına yanıt,
  takip, beğeni, DM yok (X otomasyon kuralı; bunları sahibi elle yapar).
- Her kupon postunda tutma ihtimali yazar ve post "18+ | Play responsibly" ile biter.
- Bahis sitesi adı, linki, reklamı yok. Kesinlik dili yok. Uydurma geçmiş, sahte kazanç görüntüsü yok.
- Kupon kuralları sabit (SOZLESME E6): günde en fazla 5 kupon (üç türden sonra günün kuponuyla aynı sınırlarda ek kuponlar), kuponda en fazla 4 maç. **Günün kuponu** 2.00–4.00
  oran, en olası seçenek (genelde 2.00 civarı, yaklaşık %47). **Long shot** 3.00–4.00 oran, tutma en az %22. **Büyük maçlar** yalnızca
  büyük maçlardan, günün kuponuyla aynı sınırlar. Hepsinde en olası kupona 3 puan yakın olanlar içinde büyük maçı en çok olan seçilir. Kural sağlanmazsa o kupon çıkmaz.
  Ayak oranları yalnızca **Bet365**'ten (24 Ekim 2026): toplam oran Bet365'te bulunan fiyattır; Bet365'te olmayan pazar girmez.
- Post düzeni: 🎩 açılış, ⚽ maçlar, 📊 toplam oran ve tutma ihtimali, 💬 yanıt çağıran tek soru, 18+ satırı. Oyunlar ve
  oranlar görseldeki kupon fişinde.
- İlk maça 20 dakikadan az kaldıysa kupon paylaşılmaz. Paylaşılan kupon silinmez; kaybeden de karnede kalır.
- Ücretli kanal/abonelik: en az 8–12 haftalık açık karneden sonra, ayrıca konuşulacak. Türk kitleye satış yok
  (bkz. `TURKCE_HESAP_PLANI.md`, avukat koşulu).

## Kurulum (otomatik mod için, bir kerelik)

1. X → Ayarlar → Hesabınız → Hesap bilgileri → **Otomasyon**: yönetici hesap seç ("Automated by @..." etiketi; X kuralı).
2. Mr. Likely hesabıyla developer.x.com → Project + App → Billing/Credits: 10$ yükle.
3. App → User authentication settings: **Read and write**, tür **Web App, Automated App or Bot**, adresler `https://github.com`.
4. App → Keys and tokens: API Key + Secret, Access Token + Secret (izin ayarından **sonra** üretilmiş, "Read and Write").
5. GitHub → Settings → Secrets and variables → Actions: `X_LIKELY_API_KEY`, `X_LIKELY_API_SECRET`,
   `X_LIKELY_ACCESS_TOKEN`, `X_LIKELY_ACCESS_SECRET`. Anahtarlar yalnızca GitHub'a girilir.

## Günlük işleyiş

- Sabah taramasından sonra GitHub'da `🎩 Mr. Likely <tarih>: otomatik, N kupon paylaşılacak` bildirimi gelir (bilgi).
- Kupon, ilk maçtan yaklaşık 3 saat önce paylaşılır; sonuç postu maçlar bitince: kupon postunu alıntılar, sonuç kartı (skorlar, ✓/✗, LANDED/DOWN damgası) eklenir.
- Bilgi postları: 10:00 strateji notu, 13:00 günün en büyük favorisi, 16:00 en gollü ya da en dengeli maç, 21:00
  ikinci strateji notu (başka bir posta 40 dakikadan yakınsa bekler). Günlük hedef 8–14 post: en fazla 5 kupon, 5 sonuç, 4 bilgi.
  Büyük maç postları (favori, gol, denk) **anketli**: seçenekler kısa, anket maç başlayınca kapanır (ek post yok).
  Strateji notları sade ve günlük dilde (90. dakika golü, son ayak, cash out, kendi takımına oynamak); marj/fiyat dili az.
- Haftalık karne postu: Pazartesi 10:00, dersin yerine; geçen haftanın paylaşılmış kuponları, kaybedenler dahil, ve
  ihtimallere göre kaçının tutması gerektiği (SOZLESME E1; kapatmak: `oto_haftalik_karne = false`).
- **Sabah duyurusu:** ilk kupondan önce "bugün N kupon" ve yanıt çağıran bir soru ("Which pick do you trust most today?").
- **Günün maçı postları (E1):** günde en fazla 10 maç, önce büyük maçlar; 1X2, "Over 2.5 goals", "Both teams score"
  yüzdeleri ve havuzun en yüksek ihtimalli oyunu ("Safest angle: Double chance 1X, 88% at 1.11"), kuponda mı. Maçtan
  ~2,5 saat önce. En büyük maç "Match of the day" başlığı ve 1X2 anketiyle. Kalkylerat postları otomatik alıntılanmaz.
- **Büyük maç hikayesi (E1):** günde en fazla 10 büyük maçta (yoğun günlerde hepsi) maç postu flood olur: "📋 The story" (eşleşme geçmişi, puan
  durumu, Avrupa'dan dönüş, iç saha/deplasman karnesi, seriler, geç goller) ve "🩹 Out" (sakat/cezalı) + soru. Yalnızca
  API-Football verisinden, kodla (`bot/likely_hikaye.py`); Flashscore/haber metni yok.
- **Sanal kasa (SOZLESME E8):** 10.000 € (6 Ekim'den), her kupon paylaşılınca boştaki bakiyenin %3'ü. Günün bütün
  kuponları sonuçlanınca borsa grafiği gibi mum grafiği (`bot/likely_kasa.py`); Pazar haftalık, ay sonu aylık. Günde en
  fazla 1 grafik postu, kupon postunda tutar yok. `[likely] oto_kasa = true` olunca önce bir kez 4 postluk duyuru flood'u gider; her kasa postu denetçiden geçer.
- Sonuç postu, kuponun kaderini 80. dakikadan sonra bir gol belirlediyse o anı anlatır ("88': 2-0. 90+3': 3-0."). Gol
  dakikaları sonuç isteğiyle gelen maç olaylarından (ek istek yok); olaylar skorla tutmuyorsa, maç The Odds API'den
  geliyorsa ya da pazar ilk yarı/korner ise anlatı yok, düz metin gider (SOZLESME E2).
- **Ölçüm (gölge test, paylaşılmaz):** sabah havuzundaki bütün ayakların sonucu toplu istekle (API-Football, 20 maç/istek,
  günde ~3-4 istek) `data/likely_olcum/` içine yazılır. Sabah bildiriminin sonunda "Ölçüm" bölümü: pazar başına beklenen
  ve gerçek tutma (z ≥ 2 ise fark gerçek olabilir) ve kural varyantlarının aynı havuzda yeniden oynatılması (tutan, kâr).
  Elle: `python -m bot.likely`. Kural değişikliği bu rapora bakılarak, sahibinin onayıyla yapılır.
- Paylaşılmış kuponu yeni düzenle yeniden atmak: Actions → `likely_yenile` (yalnızca maç başlamadan; aynı kupon).
  Gün içinde eksik kupon türünü tamamlamak: `likely_ek`.
- Durdurmak için o bildirime `iptal` yaz (paylaşılmamış kuponlar gitmez). Tamamen kapatmak: `[likely] aktif = false`.
- Büyüme için elle yapılacaklar (bot yapamaz): ilgili hesapları takip, büyük hesapların maç postlarına yanıt.
