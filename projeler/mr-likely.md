# Mr. Likely (kupon hesabı, X)

**Durum (24 Ekim 2026):** çalışıyor, otomatik mod. 6–23 Ekim: 46 kupon, 22 tuttu. Ayak oranları yalnızca Bet365'ten
(`claude/mr-likely-bet365` dalı, ana dala alınınca canlı).

## Ne yapıyor
- Kuponu sabit kurallar seçer (SOZLESME E6): toplam oran 2–4, en fazla 4 ayak, günde en fazla 5 kupon, öğlen oran
  tazeleme. Görselli kupon postu, kupon postunu alıntılayan sonuç postu, günde en fazla 4 bilgi postu, Pazartesi
  haftalık karne (kaybedenler dahil).
- Sonuç postu kuponu belirleyen geç golü anlatır ("88': 2-0. Still fine. 90+3': 3-0. Of course it was.").
- Cevap taslakları insan sesiyle (15 Ekim, PR #70). Ses ve karakter: `marka/MR_LIKELY.md`.
- Yanlış oranlı kupon maç başlamadan `likely_iptal` ile silinebilir (E5'e tek istisna, 14 Ekim).

## Açık işler
- [x] Sanal kasa (E8) açıldı (24 Ekim): 10.000 €, palet fiş, 4 postluk duyuru; sahibi 1. postu sabitler.
  Geçmiş (6–24 Ekim) en iyi fiyatla paylaşılan oranlardan; 25 Ekim'den itibaren yalnızca Bet365 fiyatı.
- Kupon kartında her ayağın yanında ihtimali (% likely), 24 Ekim.
- [x] Sabah duyuru postu (eski `claude/daily-coupon-teaser-2bolvm` dalı) ana dala alındı, sonunda soru (24 Ekim).
- [x] Günün maçı postları: günde en fazla 10, "safest angle" ve kupon bağı (24 Ekim). Kalkylerat'ı otomatik alıntılama
  sahibinin kararıyla yapılmadı (X koordineli hesap riski).
- [ ] `claude/daily-coupon-teaser-2bolvm` dalını ana dala al (21 Ekim): ilk kupondan önce "bugün N kupon" duyuru postu.
- [ ] Gölge test kararı: DC12 çıkarılsın mı, fiyat sınırı gevşesin mi? 13 Ekim'de 1–2 hafta beklenmesi kararlaştırıldı;
      rapor sabah bildiriminin sonunda. Kural gevşetmek sahibinin onayıyla (CLAUDE.md).
- Bilinen risk: `data/likely_x.enc` herkese açık depoda; anahtar `X_API_SECRET`'tan türetiliyor. O sır sızarsa bu
  token da çözülür.

## Karar geçmişi
- 24 Ekim: sanal kasa ve günlük/haftalık/aylık mum grafiği (E8): 10.000 €, boştaki bakiyenin %3'ü, kaybedenler dahil.
- 24 Ekim: ayak oranları yalnızca Bet365'ten (E6, sınırlar aynı; bazı günler daha az kupon çıkabilir). Önceden her
  ayağın en iyi fiyatı farklı sitelerden gelebiliyordu. Kupon kaydında ayak başına `oran_kaynagi` tutuluyor.
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

## claude.ai sohbetlerinden
- 5 Ekim akışı (elle: analiz + örnek kuponlar, sahibi seçer, hazır metin, elle yapıştırır) 6 Ekim'de tam otomatiğe
  çevrildi; gerekçe: zaman yok ve elle kupon kurarken kendi kurallarını bozuyor. Kayıt sıfırdan başladı.
- Sahibinin kendi kupon fikri: 4–5 ayak %80–90 (oran 1,12–1,20) + 1 riskli ayak; sistemin kısa kuponları uygunsa karışmaz.
- Görsel: sarı arka planda şapkalı bıyıklı yüz logo; kupon görselinde "kupon 1/2" numarası yok, boyuta göre (dörtlü,
  beşli, altılı); görseller yapay zekâ görünmemeli.

## Bulut kanalı oturumlarından (15–21 Ekim, kanal "Mr Likely yorumlarını insanileştir")
- **17–18 Ekim tek kupon nedeni:** kod ya da ses kuralı değil, veri. Sabah 07:39 oranlarında büyük maçlarda bahisçi sayısı
  bütün hafta 10'du, 17 Ekim'de 6'ya düştü. Kupon için ≥3 sitede fiyat şart; çoğu pazar 2 sitedeydi, gol pazarları
  elendi, en yüksek oran 1,36–1,38. Long shot ve büyük maçlar kuponu çıkmadı (18 büyük maçtan 3'ü geçti, çarpım 1,48).
  Eşik gevşetmeden kayıtlı sabah havuzlarıyla deneme: 11 ve 14 Ekim 5 kupon, 9 ve 16 Ekim 4; zayıf günlerde 2–3.
- **PR #102 (18 Ekim, 349 test):** ek kuponlar günün kuponuyla aynı eşikler (oran 2,00–4,00, tutma ≥%30, fiyat ≤-%8),
  aynı maç tekrarlanmaz, aralarında 40 dk (E7). Adlar: gunun-kuponu, long-shot, buyuk-maclar, gunun-kuponu-2…5.
  Tazeleme maliyeti ~55 API-Football isteği/gün (kalkylerat.md'deki "Mr. Likely ek istek atmaz" notu artık geçerli değil, bkz.
  kalkylerat.md). Bot büyük maçlarda `tani.buyukler[].bahisciler` kaydeder.
- **19 Ekim ilk gün:** 5 kupon (2,15 / 3,47 / 3×2,00–2,02), tazeleme 11:03 yerel. Akıştaki bahisçiler: Pinnacle, Bet365,
  William Hill, BetVictor, 1xBet, Marathonbet; listemizden yalnız Bet365, William Hill, BetVictor kaldı (üçü de şart).
  Betano, Unibet, Betway, 888Sport, Bwin artık gelmiyor. 1xBet/Marathonbet eklenmedi: takipçilerin çoğu erişemez.
  5 kupon her gün garanti değil. Açık: API-Football'daki düşüş kalıcı mı?
- **Duyuru postu (21 Ekim, taslak PR #116, 352 test, SOZLESME E1'e eklendi):** ~07:50 UTC'de, 11:00 tazelemesini beklemeden;
  sayı o anda hazır kupon sayısı, 5'ten azsa "Might add one later if the odds move my way." gibi biter; 0 kuponda ya da
  ilk kupon paylaşıldıysa atılmaz; günlük farklı şablon; maliyet günde 1 X yazma.
- **Yorum taslağı kodu:** `bot/firsat.py` (günde 5, 10/13/16/18 UTC) ve `bot/yorum.py` (30 dk); kupon/sonuç metni
  `bot/likely.py` (`ses_yaz`, `ses_uygun`, `SES_SISTEM`). 15 Ekim sesi üç kural: her taslak bizim yüzdemize bağlanır,
  hakaretsiz takılma serbest, uzun tire, "not X, it's Y" ve "Honestly," elenir. `.claude/skills/humanizer` eklendi.
- **Ders (sahibi kızdı, 18 Ekim):** neden bulunmuş ama kod değişmemişken bunu açık söylemeden bırakma. Her cevapta
  "teşhis mi, kod değişti mi, canlıda mı" ayrımını yaz; karar sorusunu cevapsız bırakma, hatırlat.
- Eski `mr-likely-*` dallarından 20'den fazlası bu işle ilgisiz, PR'ları kapalı.

