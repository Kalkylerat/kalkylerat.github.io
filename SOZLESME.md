# Kalkylerat sözleşmesi: üzerinde anlaştığımız kurallar

Bu dosya botun **değişmez** davranışıdır. Her madde koda ve bir teste bağlıdır:

- `tests/test_sozlesme.py` her maddeyi ayrı ayrı denetler. Biri bozulursa test kırmızı yanar, bot o değişiklikle
  çalışmaz ve alarm gelir.
- `bot/saglik.py` aynı maddeleri canlı yayında ölçer. Sapma olursa GitHub "alarm" issue'su açılır ve sahibi
  etiketlenir.

Bir kuralı değiştirmek isterseniz önce burayı, sonra testi, en son kodu değiştirin. Sessizce değişen kural olmaz.

## A. İçerik

| # | Kural | Test | Canlı denetim |
|---|---|---|---|
| A1 | Postta adı geçen **her maçın kendi yüzdeleri** yazılır (en az iki); yüzdesiz maç adı yok. | `test_A1` | denetçi (paylaşmadan önce) |
| A2 | Rakamlar kayıttakiyle aynı; direktör (yapay zekâ) bir yüzdeyi atamaz, uyduramaz. | `test_A2` | denetçi |
| A3 | **Olasılık, seçim değil**: her pazar bütün taraflarıyla (Ev % · Beraberlik % · Dep %), her kartta "not picks"; ✅/❌, "wrong", "our pick" yok. | `test_A3` | `saglik` (seçim dili) |
| A4 | **Oran ve takım istatistiği yan yana**; istatistik yoksa nedeni yazılır. | `test_A4` | — |
| A5 | Her sayıda % işareti; kısaltma yok ("O2.5", "BTTS" değil "Over 2.5 goals", "Both teams score"). | `test_A5` | `saglik` (kısaltma) |
| A6 | Görsellerde yüzdesiz rakam yok (en olası skorun da yüzdesi var). | `test_A6` | — |
| A7 | Maç sonu postu: olan ve maç öncesi yüzdesi ("Our pre-match chance of what happened"). | `test_A7` | `saglik` |
| A8 | Link yok, bahis/kesinlik dili yok, her post "18+" satırıyla biter, 280 sınırı. | `test_A8` | denetçi |

## B. Zamanlama

| # | Kural | Test | Canlı denetim |
|---|---|---|---|
| B1 | **Maç sonu postu düdükten 5–15 dk sonra.** Sonuç maç başlamasından 1 sa 45 dk sonra sorulmaya başlanır; nöbetçi botu 7 dakikada bir çalıştırır. | `test_B1` | `saglik`: tahmini düdükten 25 dk sonra yoksa ya da geç çıktıysa alarm |
| B2 | Tablodaki **her maç bittikçe** tablo postunun altına sonucu (oran/istatistik yüzdeleriyle) gelir. | `test_B2` | `saglik`: başlamadan 2,5 saat sonra yoksa alarm |
| B3 | Maç öncesi kart, son saati yakın olan önce: bilgi postu kartı kaçırtamaz. | `test_B3` | `saglik`: kaçan kart alarmı |
| B4 | **Cumartesi, Pazar ve maçı çok olan her gün yoğun gün** (sabah analizinde 8+ büyük/izinli lig maçı varsa hafta içi de): ~15 dakikada bir post (aralık ≥13 dk; nabız 7 dakikada bir olduğundan pratikte 14 dk), günde en fazla 40 post (maç sonu ve tablo yanıtları hariç), kart listesi büyük, izinli ve ek liglerin akşam maçlarıyla genişler (en fazla 30 kart; alt lig kartı yok), kart maçtan 8 saat önceden paylaşılabilir ve sırada az post varsa postlar günün geri kalanına yayılır (öğlen boşluğu ve akşam boşluğu olmasın), akşam tablosu. | `test_B4` | `saglik`: sırada post varken durgunluk alarmı |
| B5 | **Sabah analizi her gün erken (07:17 İsveç saati)** yapılır, Asya'daki öğle maçları da kaçmaz; atlanırsa nabız gün içinde tamamlar. Yanıt kiti her sabah gelir. | `test_B5` | `saglik`: 08:17 (İsveç) sonrası analiz yoksa alarm |
| B6 | **Günün büyük maçları** (Uluslar Ligi, Avrupa kupaları, Dünya/Avrupa elemeleri, büyük 5 lig, Süper Lig, taraftar etiketli milli takım/kulüp) **her zaman kart alır**, tabloda yer alır (kartı olsa da) ve kartları önce çıkar. Büyük ve izinli liglerde **lig başına sınır yok**: ölçüt maçın veri kalitesi. Tablo en fazla 15 maç; alt ligler ancak yer kalırsa (6 maçtan azsa). | `test_B6` | `saglik`: büyük maçın kartı kaçarsa alarm |
| B7 | **Hesap sessiz kalmaz**: büyük maç olmayan günde de ek liglerin kartları (en fazla 6) öğleden sonra akşam maçları tablosu (12:00 UTC'den) ve 16:00 UTC'den sonra gece maçları tablosu çıkar (her biri en az 4 maç); 18:00–20:30 UTC arasında günün ikinci bilgi postu gelir. 08:00–21:00 UTC arasında **3 saat** hiç post/yanıt yoksa, gün türü ne olursa olsun alarm gelir. | `test_B7` | `saglik`: 3 saat sessizlik alarmı |

## C. Güvenilirlik

| # | Kural | Test | Canlı denetim |
|---|---|---|---|
| C1 | Nöbetçi: bot 7 dk'dır çalışmadıysa nabzı başlatır; 20 dk çalışmazsa ya da çalışma hata verirse alarm. | `test_C1` | nöbetçi |
| C2 | Her nabızdan sonra sağlık kontrolü; yeni sorun = alarm issue'su + sahibine bildirim, aynı sorun bir kez. | `test_C2` | — |
| C3 | Saatlik Claude kontrolü (rutin): sorun varsa düzeltir ve özet yazar. | — | rutin |

## D. X kuralları (ban yememek için)

| # | Kural | Test |
|---|---|---|
| D1 | Otomatik postta en fazla 1 ilgili hashtag (liste postunda 2); genel/trend etiket yok. | `test_D1` |
| D2 | Aynı metin aynı gün iki kez paylaşılmaz. | `test_D2` |
| D3 | Başkalarına otomatik yanıt, etiketleme, DM, takip, beğeni yok. Yanıt kiti yalnızca taslaktır. | `test_D3` |
| D4 | Topluluğa günde yalnızca tablo ve oran/istatistik postu gider. | `test_D4` |
| D5 | Hesap "Automated" etiketli, @kalkyleratkonto'ya bağlı (X ayarı, sahibi yaptı). | — |

## E. Mr. Likely (ikinci hesap)

Testler `tests/test_likely.py` içinde. Karakter ve hesap rehberi: `marka/MR_LIKELY.md`. Mod: `ayarlar.toml` → `[likely] mod`.
6 Ekim 2026: sahibinin isteğiyle hesap **otomatik moda** alındı (kuponu kurallar seçer, bot paylaşır).

| # | Kural | Test |
|---|---|---|
| E1 | **Otomatik modda** bot yalnızca kendi postlarını atar: kupon postu, kendi kupon postunu **alıntılayan** sonuç postu (sonuç kartı görseliyle; yanıt olarak değil, sahibinin isteği 7 Ekim 2026), günde en fazla 4 bilgi postu (kupon stratejisi notu ya da günün büyük maçından piyasa rakamı; rakam analiz kaydından, maç başladıktan sonra atılmaz, postlar arasında en az 40 dakika). Bot yalnızca kendi postunu siler. Başkalarına yanıt, etiketleme, DM, takip, beğeni yok. Hesap X'te "Automated" etiketlidir (X ayarı, sahibi yapar). **Elle modda** bot hiçbir şey paylaşmaz. | `test_E1` |
| E2 | Her kupon postu **tutma ihtimalini** yazar ve "18+" satırıyla biter; kesinlik dili, link, bahis sitesi adı, etiket ve kayıtta olmayan sayı (uydurma karne) yok. Karakter metni kurala uymazsa şablon kullanılır. | `test_E2` |
| E3 | Kupon oranı ve tutma ihtimali ayakların **çarpımıdır**; aynı maçtan iki oyun aynı kupona girmez. | `test_E3` |
| E4 | İlk maç başladıktan sonra kupon seçilemez; otomatik modda ilk maça 20 dakikadan az kaldıysa kupon paylaşılmaz. | `test_E4` |
| E5 | **Karne paylaşılan her kuponu sayar**; kaybeden de yazılır. Maç başladıktan sonra kupon geri alınamaz; paylaşılmış kupon postu yalnızca maç başlamadan, sahibinin komutuyla (`likely_yenile`) silinir ve **aynı kupon** yeniden paylaşılır. | `test_E5` |
| E6 | **Otomatik kupon kuralları sabittir** (oran aralıkları sahibinin kararı, 6 Ekim 2026). Ortak: günde en fazla 3 kupon; kuponda en fazla 4 maç, hepsi farklı maçtan; ayaklar en az %65 ihtimalli sağlam adaylar ya da artı değerli adaylar, oranı adil fiyatın en fazla %4 altında, ihtimali keskin piyasadan (ortalamadan değil), istatistiğin piyasadan ayrıştığı aday girmez; kuponlar aynı maçı paylaşmaz. **Günün kuponu:** toplam oran 2.00–4.00, tutma en az %30, fiyat adil fiyatın en fazla %8 altında. **Long shot:** toplam oran 3.00–4.00, tutma en az %22, fiyat adil fiyatın en fazla %10 altında, ayak oranı en az 1.30. **Büyük maçlar:** yalnızca büyük maçlardan, günün kuponuyla aynı sınırlar (sahibinin isteği, 6 Ekim 2026). Her birinde koşulu sağlayanlardan tutma ihtimali en yüksek olana 3 puan yakın olanlar içinde **büyük maçı en çok olan** seçilir. Kural sağlanmazsa o kupon o gün çıkmaz. | `test_E6` |
