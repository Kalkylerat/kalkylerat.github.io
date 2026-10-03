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
| B4 | **Cumartesi ve Pazar yoğun gün**: postlar arası ≥28 dk, günde en fazla 24 post, kart listesi akşam maçlarıyla genişler, akşam tablosu. | `test_B4` | `saglik`: sırada post varken durgunluk alarmı |
| B5 | Sabah analizi her gün yapılır; yanıt kiti her sabah gelir. | `test_B5` | `saglik`: 10:00 UTC'de analiz yoksa alarm |

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
