# Üçüncü hesap: beş otonom X sayfası önerisi (online alışveriş kitlesi)

Durum (7 Ekim 2026): **karar bekliyor.** Hiçbir kod yazılmadı. Çalışan iki otomasyona (Kalkylerat ve Mr. Likely)
dokunulmadı; bu dosya yalnızca plan ve araştırma kaydıdır. Sahibi bir seçeneği onaylayınca sırayla SOZLESME.md
(yeni bölüm), test, kod yazılır.

---

## 1. Araştırmanın dürüst özeti

### 1.1 "İnternette en çok alışveriş yapan kesim" — veri tutarsız

Kaynaklar birbirini tutmuyor; çoğu pazarlama blogu, birincil veri değil. Ölçtükleri şey farklı (haftalık
kullanım, sipariş başına tutar, yıllık toplam), o yüzden sıralamaları kıyaslanamaz. Güvenilmeyecek iddialar da
var (bir kaynak Gen X için "yıllık ~70.000 $ online harcama" diyor — gerçekçi değil).

Birden fazla kaynakta **tutarlı** olan üç sinyal:

| Sinyal | Bulgu | Bizim için anlamı |
|---|---|---|
| **Gelir** (en net sinyal) | Yüksek gelirli haneler online'da düşük gelirlilerden **2,6x** fazla harcıyor | Hedef demografi yaş değil **gelir**: pahalı ürün kategorisi seç |
| **Yaş** | ABD e-ticaretinin ~**%36**'sı milenyaller; penetrasyon **25–44**'te zirve | 25–44, kendi parasını harcayan, araştırma yapan kesim |
| **Sipariş başına tutar** | Erkeklerde ~220 $, kadınlarda ~151 $ (kaynaklar çelişiyor); kadınlar alışveriş sayısında önde | Cinsiyet ayrımı zayıf sinyal, kategori ayrımı güçlü |

**Sonuç:** "en çok alışveriş yapan kesim"i cinsiyet/yaşla değil **"yüksek gelirli, 25–44, satın almadan önce
araştıran"** diye tanımlamalıyız. Bu kesimin davranışı bizim için iyi haber: **satın almadan önce arama yapıyorlar.**

### 1.2 Bu kesimin en çok aradığı kelimeler (yüksek niyet)

Arama hacmi tablolarının 2026 için güvenilir bir kaynağı yok (Semrush/Ahrefs gerekir), ama **niyet kalıpları**
birden fazla kaynakta aynı. Satın almaya en yakın dört kalıp:

1. **"best …"** — kategoriyi biliyor, ürünü seçiyor
2. **"X vs Y"** — iki ürün arasında sıkışmış
3. **"review", "rating", "… worth it"** — ikna olmak istiyor (örn. "is X worth it")
4. **"… price", "discount", "deal"** — **harekete geçmeye hazır**, en değerli grup

Ayrıca: düşük hacimli + yüksek CPC bir kelime, yüksek hacimli + sıfır CPC bir kelimeden daha çok kazandırır
(örn. 200 arama × 6 $ CPC > 50.000 arama × 0,02 $ CPC). Yani **az ama parası olan arama** peşindeyiz — bu,
"az ama sağlam oyun" felsefemizin aynısı.

Amazon'da en çok aranan ürünler (Eylül 2026, ~12 milyar sorgu) bu kesimin kategorilerini gösteriyor:
air fryer, magnesium, Roku, blackout curtains, gaming PC, office chair, electric bike, vitamin C.

### 1.3 EN ÖNEMLİ BULGU: X'in kendi ödeme programı bize KAPALI

Bu, planın temelini değiştiren bulgu:

- **Creator Revenue Sharing kapandı.** Yeni kayıt 7 Ağustos 2026'da, programın kendisi **7 Eylül 2026**'da bitti.
- Yerine **Original Content Rewards** geldi. Şartları: Premium aboneliği, 500 doğrulanmış takipçi, son 90 günde
  **500.000 ana akış görüntülenmesi** (yanıtlar sayılmaz), düzenli **özgün** paylaşım.
- Program açıkça şunları **ödeme dışı** tutuyor: kopyalanan ya da az değiştirilmiş postlar, **otomatik postlar**
  ve başkalarının işini **derleyen** içerik.

**Sonuç: otonom bir sayfa X'ten para kazanamaz.** "Bot paylaşır, X öder" planı ölü. Para X'in dışında
kazanılacak; X sayfası **huninin tepesi**, ürünün kendisi değil. (Karşılaştırma: bugün post başına ~5,6
görüntülenme alıyoruz; 90 günde 500.000 eşiği bizim için zaten ulaşılabilir değil.)

### 1.4 Link paradoksu ve ban riski

Ortaklık (affiliate) linki gerektirir; ama:

- **Link erişimi düşürür** ve X API maliyetini ~13x artırır (kendi kuralımız: ana postta link yok).
- **Şubat 2026**: X ücretli tanıtım için açık etiket zorunlu kıldı; kapsamda **ortaklık linkleri ve referans
  kodları** var. Etiketlemezsen otomatik uyarı → **hesap kapatma**.
- **Şubat 2026 (23 Şubat)**: API ile yanıt atmak kısıtlandı — yalnızca orijinal yazar seni etiketlerse ya da
  alıntılarsa yanıt atabilirsin. (Bizim D3 kuralımız bunu zaten yasaklıyordu; artık teknik olarak da kapalı.)
- X otomasyon kuralları: rastgele postlara ortaklık linkiyle yanıt = spam; **birden fazla hesapta aynı içerik** =
  platform manipülasyonu.
- İzinli olan: **bilgi veren zamanlanmış içerik** (haber, hava, borsa fiyatları) ve **kullanıcının kendi
  istediği** ürün önerisi.

Bizim mevcut düzenimiz (Automated etiketi, kendi postlarına yanıt, linksiz ana post, ≤1 hashtag) bu kuralların
**tam ortasında** duruyor. Yeni sayfa da aynı iskeletle kurulmalı.

### 1.5 Ortaklık geliri: 2026'da zayıfladı, ama Nordik tarafı sağlam

- **Amazon Associates 2026'da komisyonu %50'ye kadar kesti** (ABD'de ~9 Mart 2026). Premium kategoriler
  %10 → %4–5. Kilometre taşı teşvikleri çoğu yayıncı için kaldırıldı, **genel oran kartı artık herkese açık
  değil** (hesap bazlı). Yeni hesap ilk **180 günde 3 satış** yapmazsa pasifleşiyor. Ödeme ayı kapanışından
  ~60 gün sonra. Reklamla/boost ile ortaklık linki tanıtmak yasak.
- **Adtraction** (Stockholm merkezli, İsveç): yayıncı kategorileri arasında **fiyat karşılaştırma siteleri**
  açıkça var. Adrecord'u (2024, 27 MSEK) ve Affiliate Future'ı (2025) satın aldı. Yayıncı kaydı ücretsiz.
- **Awin Nordics**: tek şart "bir reklamverene link verebilmek"; başvurular uyum ekibinden geçiyor; fiyat
  karşılaştırma açık bir kategori. ~1 EUR iade edilebilir güvence bedeli. Komisyonu reklamveren belirliyor
  (örnek: 100 €'da %6).

**Sahibi için önemli:** Adtraction/Awin İsveç tarafında fatura kesilebilir gelirdir; **Flow Event (enskild firma)**
üzerinden düzgün muhasebeleşir (moms dahil). Amazon.se oranları hesap bazlı, önceden bilinemez.

### 1.6 Kopyalanacak kanıtlanmış modeller

| Hesap / şirket | Ne yapıyor | Para nasıl geliyor | Bizim için ders |
|---|---|---|---|
| **Going** (eski Scott's Cheap Flights) | Uçuş fırsatı bülteni; **her fırsatı insan eli kontrol ediyor** | **Abonelik** (49 $/yıl Premium, 199 $ Elite), komisyon **değil**; bedava kademe reklamla | Kitle **filtrelenmiş kıtlık** için para veriyor. Başlangıç: 3,5 ayda 646 ücretli abone; 2016 sonunda ~29.6k ücretli + 204k bedava, ~963k $ satış. Pandemide çok yıllık abonelikle sadece %5 düşmüş. |
| **Wario64** (oyun fırsatları, X) | Gün boyu fırsat postu | **Amazon ortaklığı**; profilde zorunlu ifşa, postlarda `#ad` | Ortaklık işliyor ama **ölçek ve hız** gerektiriyor; otomasyonu doğrulanmış değil, forum spekülasyonu |
| **Slickdeals** | Topluluk fırsat sitesi | Editörler popüler olacak fırsatın linkini **ortaklık linkine çeviriyor**; reklam + öne çıkarma | Komisyon tahminleri %1–15 arası, hepsi üçüncü taraf tahmini. Ana sayfa "satılık değil" ama "markalardan ödeme alabiliriz" de yazıyor |
| **Keepa** (altyapı) | Amazon fiyat geçmişi | API aboneliği | **Bizim için veri kaynağı**: ASIN başına 1 token, `stats` ve 90 günlük ortalama **ek ücretsiz**; Starter ~49 €/ay ≈ 892.800 token/ay → günde ~10.000 ürün rahat. `avg90 = -1` "veri yok" demek, kodda ele alınmalı |

---

## 2. Neden bizim motorumuz bu işe uyuyor (konsept eşleşmesi)

Mevcut motorun kalbi şu: **adil fiyat ↔ teklif edilen fiyat → değer yüzdesi → şeffaf karne.**

Alışveriş tarafında bunun birebir karşılığı var:

| Kalkylerat (bugün) | Alışveriş sayfası (yarın) |
|---|---|
| Keskin piyasanın marjsız adil olasılığı | Keepa 90 günlük ortalama = **adil fiyat** |
| Bahisçinin verdiği oran | Etiketteki "indirimli" fiyat |
| Değer % (oran vs adil fiyat) | **Gerçek indirim %** (fiyat vs 90 günlük ortalama) |
| A3: "olasılık, seçim değil" | "ölçüm, tavsiye değil" |
| Maç sonu karnesi (`kayit.py`) | Fiyat gerçekten düştü mü karnesi |
| `gorsel.analiz_karti` kart görseli | Fiyat kartı görseli |
| `denetci.py` (uydurma sayı yok) | Aynısı: kayıtta olmayan fiyat yazılmaz |
| `nobet.yml` 7 dk nöbet + `saglik.py` alarm | Fiyat düşüşünü dakikasında yakalama |
| `docs/index.html` herkese açık panel | **Para kazanan sayfa** (linkin konacağı yer) |

Yani yeniden yazılacak şey veri kaynağı ve metin; **motor, denetçi, nöbetçi, alarm, kart, karne ve panel
olduğu gibi duruyor.** Bu, beş seçeneğin hepsinde en büyük avantajımız.

---

## 3. Beş öneri

Hepsinde değişmeyen iskelet (D bölümü kuralları): Automated etiketi, sahibinin insan hesabına bağlı, başkalarına
otomatik yanıt/etiket/DM/takip/beğeni yok, ana postta link yok, ≤1 hashtag, aynı metin günde iki kez yok,
uydurma sayı yok, her postta ifşa satırı.

### Seçenek 1 — "Gerçek İndirim Denetçisi" (fake-discount auditor) ⭐ önerim

**Ne yapar:** Keepa'dan 90 günlük ortalamayı alır, "%40 indirim" diyen etiketi denetler ve **gerçek indirimi**
yüzdeyle yazar. Günde 3–6 kart: "Bu ürün '%40 indirimde'. 90 günlük ortalamaya göre gerçek indirim %6."
Ara ara da gerçek dipleri yakalar: "180 günün en düşüğü, gerçek indirim %31."

- **Aranan kelime eşleşmesi:** "price", "discount", "deal", "price history" — en değerli grup
- **Para yolu:** X bedava huni → `docs/` panelinde kategori sayfaları (arama trafiği) → Adtraction/Awin
  ortaklığı panelde (X postunda değil, erişim düşmesin) → sonra Going modeli ücretli kademe (takip listesi alarmı)
- **Neden en güçlü:** matematik birebir aynı, kod devri en ucuz; "şeffaf karne" kozumuz burada da en büyük koz;
  bahis/hukuk riski **yok** (7258 sorunu yok, avukat beklemeye gerek yok)
- **Risk:** Keepa 49 €/ay sabit gider; Amazon oran kesintisi; panel trafiği sıfırdan kurulacak

### Seçenek 2 — "Buna değer mi?" endeksi (Worth-It Index)

**Ne yapar:** Trend ürüne 0–100 "değer mi" endeksi verir: fiyat geçmişi + yorum sayısı/puan eğilimi +
kategori ortalaması. A3'ün alışveriş hali: **"endeks, tavsiye değil"**; her sayının yanında yüzde.

- **Aranan kelime eşleşmesi:** en yüksek niyet üçlüsü — "best", "X vs Y", "worth it"
- **Para yolu:** panelde kalıcı karşılaştırma sayfaları (SEO, yüksek CPC) → ortaklık; sonra "endeksi sor" ücretli
- **Güçlü yanı:** içerik bayatlamaz (evergreen), arama niyetiyle örtüşme en yüksek
- **Risk:** Keepa'nın ötesinde yorum/puan verisi gerekiyor (ek kaynak + ek maliyet); puanlama savunulabilir
  olmalı, yoksa "uydurma skor" olur ve denetçi felsefemize aykırı düşer

### Seçenek 3 — "Düşüş Nöbetçisi" (Drop Watch) — Wario64 + Going şekli

**Ne yapar:** **Tek dar kategori** seçer (örn. kahve makinesi, oyuncu donanımı, bebek ürünü) ve gerçek fiyat
dibini **dakikalar içinde** duyurur: "180 günün en düşüğü." B1 kuralının birebir hali (düdükten 5–15 dk sonra →
düşüşten 5–15 dk sonra); 7 dakikalık nöbetçimiz ve alarmımız buna hazır.

- **Para yolu:** en hızlı nakit (alarm → tıklama → komisyon); kıtlık doğal olarak ücretli kademeye çıkar (Going)
- **Güçlü yanı:** `nobet.yml` + `saglik.py` altyapısı doğrudan uyuyor; kanıtlanmış model
- **Risk (en yüksek):** **en çok linke bağımlı** seçenek → erişim cezası + Şubat 2026 ifşa zorunluluğu + spam
  sınırına en yakın; rekabet en sert; dar kategoriyi iyi seçmek şart

### Seçenek 4 — Mevcut konsepti geliştirme: "Veri kartı fabrikası"

**Ne yapar:** Motoru olduğu gibi bırakır, **alanı değiştirir**: `analiz.py`'nin adil fiyat + kart + karne hattını
yeniden kullanılabilir bir "veri kartı" hattına çıkarır ve bahis komşuluğu olmayan, yüksek CPC'li bir para
alanında sayfa açar (İsveç elektrik/enerji fiyatı, uçuş fiyatı adilliği, faiz/mevduat oranları).

- **Güçlü yanı:** kodun ~%80'i aynı; 25–44 yüksek gelirli kitle; Adtraction/Awin'in güçlü olduğu İsveç pazarı;
  gelir Flow Event üzerinden temiz faturalanır
- **Risk:** finansal içeriğin kendi uyum yükü var (Finansinspektionen) — Türkçe hesapta 7258 için beklediğimiz
  gibi burada da önce **hukuki görüş** gerekir. Enerji/uçuş tarafı bu riskten muaf.

### Seçenek 5 — "Pazar nerede yanılıyor": linksiz, ücretli kademe (Going'in asıl dersi)

**Ne yapar:** Tek motor, iki vitrin. X sayfası **hiç link vermez**: yalnızca yöntemi ve günün en büyük
fiyat–değer **sapmasını** paylaşır. Para ortaklıktan değil, **dijital abonelikten** gelir (endeks erişimi,
haftalık PDF, veri/API).

- **Güçlü yanı:** ana postta link yok → erişim cezası yok, ortaklık uyumu yok, Amazon oran riski yok;
  Going'in kanıtladığı yol (gelirin tamamı abonelikten); Flow Event dijital abonelik satabilir (moms)
- **Risk:** paraya en yavaş giden yol; önce kitle şart; ücretli kademenin sürekli gerçek değer üretmesi gerekir

---

## 4. Karşılaştırma

| | 1. Gerçek İndirim | 2. Değer mi Endeksi | 3. Düşüş Nöbetçisi | 4. Veri Kartı Fabrikası | 5. Linksiz Abonelik |
|---|---|---|---|---|---|
| Kod devri | **en yüksek** | yüksek | yüksek | **en yüksek** | yüksek |
| Yeni veri maliyeti | Keepa ~49 €/ay | Keepa + yorum verisi | Keepa ~49 €/ay | alana göre | Keepa ~49 €/ay |
| Aranan kelime uyumu | yüksek (deal/price) | **en yüksek** (best/vs/worth) | orta (ürün adı) | orta | düşük |
| Paraya varış hızı | orta | orta | **en hızlı** | orta | **en yavaş** |
| X ban riski | düşük | düşük | **yüksek** | düşük | **en düşük** |
| Hukuki risk | yok | yok | yok | finans ise **var** | yok |
| Tavan | yüksek | yüksek | orta (rekabet) | yüksek | **en yüksek** |

**Önerim: 1 ile başlamak, 5'i hedef almak.** Seçenek 1 motorun matematiğini hiç değiştirmeden çalışır, hukuki
riski yoktur ve "şeffaf denetçi" kimliğimizi alışveriş alanına taşır. Kitle oluştukça 5'in ücretli kademesi
aynı sayfanın üstüne kurulur — Going'in yaptığı tam olarak budur. 3 en hızlı para ama ban riski en yüksek,
sahibinin iki çalışan hesabını riske atmaya değmez.

---

## 5. Onay gelirse sıra (kural: önce sözleşme, sonra test, sonra kod)

1. SOZLESME.md'ye yeni bölüm (F): seçilen sayfanın değişmez kuralları — ifşa satırı, linksiz ana post,
   uydurma fiyat yasağı, karne zorunluluğu
2. `tests/test_sozlesme.py`'ye her madde için ayrı test
3. Veri kaynağı: Keepa anahtarı GitHub secret (`KEEPA_API_KEY`), `avg90 = -1` ele alınır
4. Kod: `bot/fiyat.py` (adil fiyat), kart görseli, `denetci` kuralları, panel sayfası
5. **Çalışan iki hesabın kodu ve workflow'ları değişmez**; yeni sayfa ayrı modül ve ayrı X anahtarlarıyla çalışır

## 6. Sahibinin karar vermesi gerekenler

1. **Hangi seçenek** (ya da hangi ikisinin birleşimi)
2. **Kategori / pazar**: İsveç mi, İngilizce küresel mi (Amazon.se oranları hesap bazlı, önceden bilinemez)
3. **Keepa 49 €/ay** sabit gider onayı
4. **Ortaklık ağı**: Adtraction (İsveç, fiyat karşılaştırma açık kategori) → Flow Event faturası
5. Seçenek 4 finans alanıysa: **hukuki görüş** önce

---

## Kaynaklar

Demografi: [Capital One Shopping](https://capitaloneshopping.com/research/online-shopping-demographics/) ·
[Tidio](https://www.tidio.com/blog/online-shopping-statistics/) ·
[WebFX](https://www.webfx.com/blog/marketing/online-shopping-statistics/) ·
[SQ Magazine](https://sqmagazine.co.uk/online-shopping-statistics/) ·
[Mintel](https://store.mintel.com/report/us-gen-z-millennial-online-shopping-behaviors-market-report)

Aranan kelimeler: [Glimpse – Amazon'da en çok aranan ürünler](https://meetglimpse.com/top-searched/most-searched-products-on-amazon/) ·
[Mainstreethost – ticari niyet](https://www.mainstreethost.com/blog/commercial-intent-keywords/) ·
[AIOSEO](https://aioseo.com/commercial-intent-keywords/)

X ödeme ve kurallar: [X – Original Content Rewards](https://help.x.com/en/using-x/original-content-rewards) ·
[X – Creator Revenue Sharing (kapandı)](https://help.x.com/en/using-x/creator-revenue-sharing) ·
[X Creators duyurusu](https://x.com/XCreators/status/2085835082166653393) ·
[X – Otomasyon kuralları](https://help.x.com/en/rules-and-policies/x-automation) ·
[X – Developer Policy](https://docs.x.com/developer-terms/policy) ·
[API yanıt kısıtı, Şubat 2026](https://piunikaweb.com/2026/02/24/x-api-blocks-automated-spam-replies/) ·
[Ücretli tanıtım ifşası](https://www.kucoin.com/news/articles/x-platform-new-promotion-disclosure-rules-compliance-shift-for-decentralized-content-crypto-marketing)

Ortaklık: [Amazon komisyon kesintisi – Adweek](https://www.adweek.com/media/amazon-associates-affiliate-rate-cuts-publishers/) ·
[eMarketer](https://www.emarketer.com/content/amazon-cuts-affiliate-commissions-by-up-50--raising-pressure-on-publishers) ·
[Geniuslink – sosyal medyada Amazon linki](https://geniuslink.com/blog/promote-amazon-affiliate-links-on-social-media/) ·
[Awin Nordics yayıncı](https://www.awin.com/nordics/publishers) ·
[Adtraction](https://en.wikipedia.org/wiki/Adtraction)

Kanıtlanmış modeller: [Going (Wikipedia)](https://en.wikipedia.org/wiki/Going_(company)) ·
[CNBC – Scott's Cheap Flights](https://www.cnbc.com/2016/11/29/how-a-29-year-old-turned-an-obsession-with-cheap-plane-tickets-into-a-1-million-business-in-under-2-years.html) ·
[Indie Hackers röportajı](https://www.indiehackers.com/podcast/164-scott-keyes-of-scotts-cheap-flights) ·
[Wario64 (X)](https://x.com/Wario64) ·
[Slickdeals – Harvard D3](https://d3.harvard.edu/platform-digit/submission/slickdeals-monetizing-frugality/)

Veri kaynağı: [Keepa – Plans & Tokens](https://keepa.com/api-docs/plans-tokens.html) ·
[Keepa – Statistics Object](https://keepa.com/api-docs/statistics-object.html) ·
[Keepa – Product Request](https://keepa.com/api-docs/product.html)

---

# Ek: Seçenek 1'in maliyeti ve ilk 6 ayın gerçekçi getirisi

(7 Ekim 2026 hesabı. Fiyatlar aşağıdaki kaynaklardan; Keepa ve Awin rakamları üçüncü taraf, kendi hesabımızdan
doğrulanmadı — kurmadan önce teyit edilecek.)

## A. Aylık maliyet

Varsayım: günde 10 post (ayda ~300), günde 300–500 ürün denetimi.

| Kalem | Aylık | Not |
|---|---|---|
| **Keepa Pro** | **29,00 €** | 1 token/dk = günde 1.440 ürün. API Starter 49 €/ay (20 token/dk) — bize gerek yok |
| X API | 4,14 € | deponun **kendi ölçümü**: ~0,015 $/gönderi (README) |
| Anthropic API | 3,00 € | Sonnet 5.5 post metni + haftalık Opus 5.5 raporu. Haiku 5.5 ile 0,64 € |
| Alan adı | 1,00 € | 12 €/yıl, panelin güvenilirliği için |
| GitHub Actions + Pages | 0,00 € | depo açık → bedava |
| Adtraction / Awin | 0,00 € | ~1 € tek seferlik depozito |
| Bülten (bedava kademe) | 0,00 € | ~1.000 aboneye kadar |
| **Toplam** | **37,14 €** | |
| + X Premium (opsiyonel) | +8,50 € | → 45,64 €. Erişimi artırır; ödeme programı için **değil** (bkz. 1.3) |

**6 aylık toplam: ~223 €** (Premium dahil ~274 €).

## B. İlk 6 ayın getirisi

Çıkış noktası uydurma değil: **kendi ölçümümüz** (`data/metrikler.json`, 3 Ekim 2026) — 37 post, post başına
~5,6 görüntülenme, 1 takipçi. Yeni hesap da buradan başlar.

Huni: panel ziyareti → %25 dışa tıklama → %2 satış → ~100 € sepet → %4 komisyon (Amazon 2026 kesintisi sonrası).

| Senaryo | Ay 6 takipçi | Ay 6 geliri | **6 aylık toplam gelir** | Net (maliyet 223 €) |
|---|---|---|---|---|
| **Kötü** — bot tek başına, elle etkileşim yok | ~80 | 0,8 €/ay | **2 €** | −221 € |
| **Gerçekçi** — sahibi günde 10–15 dk elle yanıt | ~550 | 8,4 €/ay | **22 €** | −200 € |
| **İyi** — bir post patlar + uzun kuyruk SEO | ~2.200 | 49,5 €/ay | **132 €** | −91 € |

**Başabaş:** aylık 37 € için **~9 satış/ay** = ~464 dışa tıklama = **~1.857 panel ziyareti/ay** gerekiyor.
Gerçekçi senaryoda bu ay 6'da değil, kabaca **ay 12–18**'de geliyor.

**Dürüst cevap: Seçenek 1 ilk 6 ayda kâr etmez.** Hiçbir senaryoda etmiyor. 6 ayın çıktısı para değil **varlık**:
kitle, panel, şeffaf karne ve biriken fiyat geçmişi. (Going da öyle kurulmuş: ücretli kademe Ağustos 2015'te
açılmış, 3,5 ayda 646 abone — ama zaten büyük bir bedava bülten listesinin üstüne.)

## C. Maliyeti %80 düşüren yol: Keepa'yı hiç almamak

Maliyetin **%78'i tek kalem** (Keepa 29 €). Ve kaçınılabilir: **Awin Create-a-Feed** yayıncılara ~200 milyon
ürünün akışını veriyor ve akışta **indirim dahil fiyat** ile derin link var. Yani:

- **Ay 1–3:** Keepa yok. Awin akışından fiyatları her gün kendimiz kaydederiz. Kart şöyle der: *"takibe
  başladığımızdan beri (N gün) en düşük"* — yüzdeli, dürüst, ve her gün daha değerli olur. **Kuralımıza da uygun:
  resmî API, kazıyıcı yok** (SOZLESME D).
- **Ay 4+:** 90+ günlük **kendi** geçmişimiz var → Keepa'ya hiç gerek kalmaz. Üstelik bu geçmiş bizim
  varlığımız olur, kiraladığımız veri değil.

| | Variant A (Keepa Pro) | **Variant B (Awin akışı)** |
|---|---|---|
| Ay 1–3 aylık | 37,14 € | **5,78 €** (Haiku ile) |
| Ay 4–6 aylık | 37,14 € | **8,14 €** |
| **6 aylık maliyet** | **223 €** | **42 €** |
| Gerçekçi gelirle net | −201 € | **−20 €** |
| Başabaş | ~1.857 ziyaret/ay | **~407 ziyaret/ay** |

Variant B gerçekçi senaryoda 6 ayda **neredeyse başabaş**. Bedeli: ilk 90 gün "90 günlük ortalama" diyemeyiz.

**Variant B'nin sınırı:** Awin akışı günde bir yenilenir, yani **gün içi** fiyat düşüşünü kaçırır. Seçenek 1 için
sorun değil (sahte indirim denetimi günlük veriyle çalışır); **Seçenek 3 (Düşüş Nöbetçisi) için ölümcül** —
o seçenek dakika hassasiyeti ister, yani Keepa API (49 €/ay) zorunlu olur. Maliyet açısından da Seçenek 1 > 3.

## D. Teyit edilecekler (kurmadan önce)

1. **Awin Create-a-Feed yayıncılar için bedava mı?** Kaynaklar üyeliğin kapı olduğunu söylüyor ama ücret
   konusunda net değil. Awin'e doğrudan sorulacak. Adtraction'ın akış karşılığı hiç bilinmiyor.
2. **Keepa Pro'nun 1 token/dk'sı** gerçekten API'ye gidiyor mu (kaynaklar "test için" diyor) — Keepa'ya sorulacak.
   Token 60 dakikada sönüyor, biriktirilemiyor: en fazla 60'lık kova.
3. **Amazon Associates 180 günde 3 satış** eşiği: kötü senaryoda tutmayız ve hesap pasifleşir. Adtraction/Awin'de
   böyle bir eşik yok → **birincil ağ Adtraction olmalı, Amazon ikincil.**
4. Awin'in hangi İsveç satıcılarının akışına erişim verdiği (program onayı gerekiyor).

## E. Bu rakamların değiştirdiği karar

Önerim güncellendi: **Seçenek 1, Variant B ile başla.** Yani ilk 3 ay veri için **hiç para ödeme** (aylık ~6 €),
kendi fiyat geçmişini biriktir, kitlenin büyüyüp büyümediğini gör. Büyüyorsa ay 4'te karar ver: kendi geçmişin
zaten yeter. Büyümüyorsa 42 € kaybetmiş olursun, 223 € değil.

Ek kaynaklar: [Keepa Pro fiyatı](https://revenuegeeks.com/software/keepa/pricing) ·
[Keepa API token maliyeti](https://revenuegeeks.com/software/keepa/api) ·
[Awin – ürün akışına erişim](https://success.awin.com/s/article/How-can-I-access-a-Product-Feed?language=en_US) ·
[Awin – yayıncı akışı geliştirici rehberi](https://help.awin.com/developers/docs/product-feed-publisher-guide-intro) ·
[Awin yayıncı araçları](https://www.awin.com/us/publishers/tools)

---

# Ek 2: Karar — Variant B. Etkileşim konsepti, örnek sayfalar ve yasal dayanak

Sahibinin kararı (7 Ekim 2026): **Variant B (6 ayda ~42 €)**. Gerekçesi: indirimler saatlik değil, anında
indirim kovalamak başta gereksiz. **Bu gerekçe araştırmayla doğrulandı** — hatta sandığımızdan daha güçlü.

## 1. Sahibinin gerekçesi neden doğru: dolandırıcılık haftalar sürüyor

Prisjakt Ekim 2025'te **~3 milyon fiyatı** taradı: nenet butik fiyatlarının **%13'ü Ekim'de %10'dan fazla
yükselmiş** (en çok giyim/ayakkabı, beyaz eşya, TV). Mekanizma şu: **butikler fiyatı kampanyadan haftalar önce
yükseltiyor**, böylece "son 30 günün en düşük fiyatı" rea anındaki fiyattan yine yüksek kalıyor. SVT bunu haber
yaptı ("Nya Black Friday-fusket: Så rundar butiken lagen").

Yani hile **gün içi değil, hafta ölçeğinde** işliyor. Günlük anlık görüntü (snapshot) bu hileyi yakalamak için
**yeterli ve doğru çözünürlük**. Dakika hassasiyeti bu işe hiçbir şey katmıyor. Karar doğru.

## 2. Ama üç şey eksikti (ikisi planı iyileştiriyor)

### 2.1 Ölçüt 90 gün değil, **30 gün** — ve bu bir kanun

**Prisinformationslagen 2022'de güncellendi:** bir firma fiyat indirdiğinde **son 30 günün en düşük fiyatını**
belirtmek zorunda, ve yüzde o fiyattan hesaplanmak zorunda. Konsumentverket rehberi daha da katı: "% indirim"
herhangi bir "orijinal fiyattan" hesaplanamaz, etiketi ne olursa olsun.

Bu, planı iki yerden iyileştiriyor:
- **Variant B'nin bekleme süresi 90 gün değil ~30 gün.** Bir ayda yayına hazır oluruz, üç ayda değil.
- **Ölçütümüz bizim kanaatimiz değil, kanun.** "Bence kötü fırsat" demiyoruz (öznel, hukuken riskli);
  "kanun 30 günün en düşüğünden hesaplamayı şart koşuyor; bizim günlük kaydımız o fiyatı X kr görmüş" diyoruz.
  Bu, **A2 kuralımızın** (uydurma sayı yok) yeni alandaki birebir karşılığı.

### 2.2 Kayda **bugün** başlamak gerekiyor — geriye dönük doldurulamaz

Hile Ekim'de fiyat yükseltmekle başlıyor; **Black Week 2026 Kasım sonunda.** Bugün 7 Ekim.
Bu hafta kaydetmeye başlarsak Black Week'e **~7 haftalık kendi geçmişimizle** gireriz ve Prisjakt'ın belgelediği
Ekim şişirmesini tam olarak yakalarız. Başlamazsak yılın en değerli içerik anını bir yıl erteleriz.

**Bu yüzden ilk iş paylaşım botu değil, fiyat kaydedicisi.** X hesabı, kart, metin — hepsi sonra gelebilir.
Kaydedici ucuz, sessiz ve her gün değer biriktiriyor.

### 2.3 Üç teknik/etik tuzak

| Tuzak | Ne yapılacak |
|---|---|
| **Günlük snapshot ≠ "hiç olmadığı kadar düşük"** | Metin hep "günlük kaydımıza göre" der. A2'nin aynısı: elimizde olmayanı iddia etmeyiz |
| **Akıştaki fiyat ≠ kasadaki fiyat** (kargo, kuponu, üye fiyatı) | Akışta kargo dahil fiyat var; yine de "akışta görülen fiyat" diye çerçevelenir |
| **Çıkar çatışması: denetlediğimiz satıcıdan komisyon alıyoruz** | **En ciddi olanı.** Aşağıda ayrı madde |

### 2.4 Çıkar çatışması (sahibinin dikkatine)

Awin/Adtraction komisyonu **denetlediğimiz satıcılardan** gelir. Şeffaflık markası kuran bir sayfa için bu
gizlendiğinde ölümcül; kitle fark eder. Prisjakt'ta da aynı sorun var (karşılaştırma sitesi + ortaklık geliri).

Çözüm, kurala bağlanmalı: **komisyon neyin denetlendiğine asla karar vermez**, ortaklık ilişkisi her sayfada
yazılı olur, ve sahte indirim bulduğumuz satıcıyı komisyon aldığımız için yumuşatmayız. Uzun vadede gerçek
çözüm **Seçenek 5**: gelir komisyondan değil abonelikten (Going'in modeli). Yani ilk planımızdaki "1 ile başla,
5'i hedefle" rotası bu yüzden de doğru.

## 3. Örnek alacağımız sayfalar (sahibinin sorusu)

Dürüst cevap: **tam bu işi yapan otonom bir sayfa bulamadım.** Parçaları yapan dördü var; konsept bunların
birleşimi.

| Kaynak | Ne yapıyor | Bizim alacağımız |
|---|---|---|
| **Prisjakt** (İsveç) | ~3 milyon fiyatı tarayıp Ekim şişmesini raporluyor; SVT haber yapıyor, bakan yorum yapıyor | **İçeriğin kendisi.** Ama onlar bunu **yılda bir, PR için** yapıyor — **her gün yapan yok.** Boşluk bu. TikTok'ta 18,7 bin takipçi; X'te varlık bulamadım |
| **HotUKDeals / Pepper** (Dealabs, mydealz, **Pepper Deals SE**) | Fırsat 0°'den başlar, topluluk **sıcak/soğuk** oylar; 100° = HOT DEAL + Trending. İlk **10 dakika sıcaklık gizli** (sürü etkisi olmasın). Oyla birlikte yorum yazmak teşvik ediliyor | **Etkileşim mekaniği.** Kanıtlanmış: kitle fırsatı *oylamak* istiyor |
| **Konsumentverket / DGCCRF / ACCC** | İsveç: geçen yıl **e-ticaretin %40'ı** 30 gün kuralını ihlal etmiş. Black Friday'de 10 şirkete (Åhléns, XXL, Stadium, Webhallen, Power, Nakd, Bygghemma, Nordic Nest, Blomsterlandet, Soffadirekt) toplam 22 MSEK ceza riski; Mio ve Jysk soruşturması. Fransa: **Shein 40 M€** (ürünlerin %57'sinde indirim yokmuş), Boohoo 2,3 M€ | **Otorite ve haber çıpası.** Konu İsveç'te canlı ve kitle zaten kızgın. Ayrıca **%40 ihlal oranı** = içerik kuyusu asla kurumaz |
| **@BuyHatke** (X, Hindistan) | "Sahte indirim" dili + gerçek fiyat düşüşü uygulaması | X'te bu dilin işlediğinin kanıtı; ama reklam ağırlıklı, denetçi değil |
| **Sihoo Australia** | Her ürününde **90 günlük fiyat geçmişini kendisi yayınlıyor** | Şeffaflığın pazarlama kozu olduğunun kanıtı |

**Konseptin bir cümlesi:** *Prisjakt'ın içeriği + HotUKDeals'in oylama mekaniği + bizim şeffaf karnemiz,
her gün, bir bot tarafından, kanunun ölçütüne göre.*

## 4. Etkileşim konsepti: "Rea eller bluff?" (günlük döngü)

Sahibinin şartı: etkileşime açık olmalı. Mekanik, **mevcut kodun zaten yaptığı** şey:

1. **Sabah — anket postu** (verdict YOK): ürün + reklam edilen indirim. *"Bu mont −%40 diye duyuruldu.
   30 günlük kaydımıza göre gerçek indirim ___. Sence: gerçek mi, bluff mu?"*
   → `etkilesim.anket` **zaten var**.
2. **Akşam — ifşa postu**, sabahki anketi **alıntılayarak**: kart görseli, gerçek rakamlar, kanunun ne istediği.
   → `etkilesim.analiz_takibi` ("ne dedik, ne oldu" alıntısı) **zaten var**.

Neden işler (sosyal-medya skill'inin ölçtükleri): **yanıt beğeniden ~15x ağır**, ilk 30–60 dakikadaki hız
dağıtımı belirliyor, **tablo ve sayı bookmark aldırıyor**. Anket, D3'ü bozmadan yanıt üreten en ucuz yol:
başkalarına biz yanıt vermiyoruz, onlar bizim postumuza geliyor.

Benzerlik cezasına karşı dönüşümlü formatlar:
- **"30 günün en düşüğünü tahmin et"** — sayı tahmini, yanıt getirir
- **Haftalık tablo**: "bu hafta N indirim denetledik, %X'i 30 gün kuralını karşılamadı" → bookmark
- **Aylık karne**: kendi şeffaflık karnemiz, futboldaki karnenin aynısı
- **"Fiyat readan önce yükseldi"** — Ekim kalıbı; SVT'nin haber yaptığı format, en viral olanı
- **Black Week = finalimiz.** Bütün yıl Kasım sonuna çalışır (futbolda maç takvimi neyse, bu o)

## 5. Onay bekleyen: SOZLESME F bölümü taslağı

Kod yazılmadan önce sahibinin onaylaması gereken değişmez kurallar:

| # | Taslak kural |
|---|---|
| F1 | Her kart **kanunun ölçütünü** yazar: son 30 günün en düşük fiyatı, reklam edilen referans fiyat, **gerçek indirim %**. Üçü de kayıttan; uydurma fiyat yok (A2'nin karşılığı) |
| F2 | **"Günlük kaydımıza göre"** ibaresi zorunlu. 30 günümüz yoksa kaç günümüz varsa o yazılır |
| F3 | **Ölçüm, tavsiye değil** (A3'ün karşılığı): "al/alma" yok, "kaçırma" yok, aciliyet dili yok |
| F4 | **Komisyon neyin denetlendiğine karar vermez.** Ortaklık ilişkisi panelde ve profilde yazılı; komisyon aldığımız satıcıyı yumuşatmayız |
| F5 | Ana postta **link yok** (erişim + Şubat 2026 ifşa kuralı). Link panelde |
| F6 | Satıcı adı geçtiğinde yalnızca **kendi ölçtüğümüz sayı** ve **kanunun metni** söylenir; suç isnadı yok, hüküm vermeyiz. Konsumentverket yetkili merci, biz değiliz |
| F7 | Mevcut iki hesabın kodu ve workflow'ları değişmez; yeni sayfa ayrı modül, ayrı X anahtarları |

**F6 için not:** doğru fiyatı bildirmek hukuken güvenlidir, ama tanınmış bir satıcıyı "kanunu çiğniyor" diye
adlandırmak farklı bir iddiadır. Türkçe hesapta 7258 için beklediğimiz gibi, **büyük satıcı adı geçecekse
önce hukuki görüş** alınmalı. Sayı + kanun metni çerçevesi bu riski en aza indirir.

## 6. Önerilen sıra

1. **Bu hafta: fiyat kaydedicisi** (`bot/fiyat.py`) — Awin akışından günlük snapshot, `data/fiyat/` altına.
   X hesabı, kart, metin gerekmez. Black Week'e 7 haftalık geçmişle girmek için tek şart bu.
2. Awin yayıncı kaydı + akış erişiminin bedava olduğunun teyidi (Ek 1 §D).
3. ~30 gün sonra: SOZLESME F bölümü → testler → kart görseli → anket/ifşa döngüsü → panel.
4. Black Week: yılın en büyük içerik anı, elimizde gerçek veriyle.

Ek kaynaklar: [Prisjakt: 3 milyon fiyat, %13 Ekim'de yükseldi (Market)](https://www.market.se/retailtrender/trender/ny-rapport-flaggar-for-hojda-priser-under-bade-black-friday-och-julhandeln/) ·
[SVT: Nya Black Friday-fusket](https://www.svt.se/nyheter/inrikes/nya-black-friday-fusket-sa-rundar-butiken-lagen) ·
[Bird & Bird: Sweden – Omnibus Directive](https://www.twobirds.com/en/trending-topics/omnibus-directive/omnibus-directive-countries/sweden) ·
[Bird & Bird: İsveç fiyat bilgisi rehberi 2024](https://www.twobirds.com/en/insights/2024/sweden/clarity-on-price-transparency-new-guidance-on-price-indication-in-sweden) ·
[EU Komisyonu: Madde 6a rehberi](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX%3A52021XC1229%2806%29) ·
[Konsumentverket Black Friday uyarısı (10 şirket)](https://swedenherald.com/article/consumer-ombudsman-warns-ten-companies-for-misleading-black-friday-prices) ·
[Mio, Jysk soruşturması](https://www.interiordaily.com/article/9636218/swedish-consumer-agency-targets-mio-jysk-and-other-furniture-retailers-over-sale-fraud-allegations/) ·
[Shein 40 M€ cezası](https://www.yahoo.com/news/france-fines-chinese-retailer-shein-153232791.html) ·
[Boohoo cezası](https://www.retaildetail.eu/news/fashion/misleading-discounts-land-boohoo-a-fine-in-the-millions/) ·
[HotUKDeals: sıcaklık ve oylama](https://help.hotukdeals.com/help/using-your-vote) ·
[HotUKDeals: sıcaklık ne demek](https://help.hotukdeals.com/help/votes-and-temperature-03f53346) ·
[Nordic Black Friday Report 2025](https://uutishuone.hintaopas.fi/posts/pressreleases/nordic-black-friday-report-2025-shoppers-driv) ·
[@BuyHatke (X)](https://x.com/BuyHatke/status/2105226352140181605)

---

# Ek 3: Düzeltme — kanıtı en sağlam model ve kategori hatası

Sahibinin itirazı (7 Ekim 2026): *"Daha önce başarılı olan, doğruluğu kanıtlanmış, para kazanma ihtimali yüksek
bir sayfanın konseptini geliştirip yapacağız."*

**İtiraz yerinde ve Ek 2'nin zayıf noktasını buldu.** Ek 2'de gösterdiğim kanıt "içerik haber oluyor" (Prisjakt)
ve "mekanik etkileşim getiriyor" (HotUKDeals) idi. **O konseptle para kazandığı belgelenmiş bir sayfa
göstermedim.** Boşluk olması, orada para olduğunu kanıtlamaz — tersine, boşluk bazen orada para olmadığı için
boştur. Aşağıdaki araştırma bu yüzden yapıldı.

## 1. Belgelenmiş para: kim kazandı, ne kadar

En sağlam kanıttan en zayıfa:

| Sayfa | Kanıt | Model |
|---|---|---|
| **NerdWallet** (Nasdaq: NRDS) | **Denetlenmiş SEC dosyası: 2025 cirosu 836,6 M$, GAAP net kâr 48,7 M$, +%22** | Rehber/karşılaştırma içeriği → finansal ürün komisyonu |
| **MoneySavingExpert** | 2003'te **100 £** ile kuruldu, 2012'de **87 M£'a kadar** satıldı; 13–16 M aylık ziyaretçi | Önce rehber yazılır, **sonra** ortaklık linki aranır; link yoksa ürün yine önerilir. Gelirin **%59'u tek ortaktan** (yoğunlaşma riski) |
| **Compricer** (🇸🇪) | Schibsted 2013'te **135 MSEK** ödedi (işletme kârı ~12–13 MSEK); toplamın ~çeyrek milyar SEK'e çıktığı bildirildi | İsveç karşılaştırma sitesi — **bizim ölçeğimize en yakın kanıt** |
| **Elskling** (🇸🇪) | ~150 şirketten ~5.000 elektrik sözleşmesi; **üç kez el değiştirdi** (Schibsted 2015 → Zmarta 2018 → Axo 2025) | Biri siteden geçiş yaptığında elektrik şirketi komisyon öder |
| **The Points Guy** | 2012'de 20–28 M$ (kaynaklar çelişiyor) → Bankrate → Red Ventures 1,4 Mrd$ | Kredi kartı komisyonu. Özel şirket, rakamlar doğrulanamıyor |
| **Going** | 2016'da ~963 bin $ satış | **Abonelik** (komisyon değil) |

**Ortak nokta:** hepsi **karşılaştırma/doğrulama içeriği + eylem başına komisyon**. Hiçbiri X'ten para
kazanmıyor; X/sosyal yalnızca huni. Bu, Ek 1 §1.3'teki bulguyla birebir aynı.

## 2. Benim hatam: €4/satış bir konsept problemi değil, **kategori** problemi

| Kategori | Gelir/eylem | Dönüşüm | **Gelir/tıklama** | Kaynak |
|---|---|---|---|---|
| Fiziksel ürün (100 € sepet, %4) | 4,00 € | %2,0 | **0,08 €** | Amazon %1–10; e-ticaret EPC 0,08–0,35 $ |
| **Elektrik sözleşmesi geçişi** | **45,00 €** | %1,5 | **0,67 €** | 30–60 £/çift yakıt geçişi |
| Sigorta lead | 76,26 € | %1,0 | 0,76 € | ort. 82,89 $/dönüşüm |

**Bir elektrik geçişi ≈ 11 fiziksel ürün satışı.** Aynı trafik, aynı emek, aynı bot.

## 3. Sayılar: aynı huni, iki kategori

Maliyet **daha da düşük**, çünkü veri bedava: `elprisetjustnu.se` **açık ve bedava API**, SE1–SE4,
1 Ekim 2025'ten beri **15 dakikalık** çözünürlük. Resmî API → kazıyıcı yasağımıza uygun.

| Kalem | Aylık |
|---|---|
| elprisetjustnu.se API | **0,00 €** |
| X API (300 post) | 4,14 € |
| Anthropic API | 3,00 € |
| Alan adı | 1,00 € |
| **Toplam** | **8,14 €** → 6 ayda **49 €** |

| | A) Sahte indirim (fiziksel ürün) | **B) Elektrik sözleşmesi karnesi** |
|---|---|---|
| Ay 6 geliri | 8,40 €/ay | **70,88 €/ay** |
| **6 aylık gelir** | 22 € | **189 €** |
| 6 aylık net | **−26 €** | **+140 €** |
| Başabaş | 2,0 satış/ay | **0,18 geçiş/ay** (~6 ayda 1 geçiş tüm masrafı karşılar) |

**Aynı trafikle 8,4x gelir — ve ilk kez 6 ayda artıda biten seçenek.**

## 4. Neden bizim motorumuza en iyi uyan alan bu

| Kalkylerat (bugün) | Elektrik sayfası |
|---|---|
| Keskin piyasanın adil olasılığı | **Spot fiyat** = adil fiyat (bedava, 15 dk) |
| Bahisçinin verdiği oran | **Sabit sözleşmenin** teklif ettiği fiyat |
| Değer % (oran vs adil fiyat) | Sabit mi spot mu — **fark %** |
| **Maç sonu karnesi** | **"Ocak'ta sabit pahalı dedik; ne oldu" karnesi** |
| `nobet.yml` 7 dk nabız | 15 dk'da yenilenen fiyat |
| Anket → ifşa döngüsü | "Sence bu ay sabit mi spot mu kazandı?" → akşam cevap |

Futbolda yaptığımız şeyin **birebir aynısı**: piyasa bir fiyat veriyor, biz adil fiyatı hesaplıyoruz, farkı
yüzdeyle yazıyoruz, sonra kim haklıydı diye karne tutuyoruz. Kupon/bahis dili yok, hukuki risk yok.

## 5. Dürüst riskler

1. **Kanıtlanmış model şu anda bozuluyor.** NerdWallet'ın kendi dosyasında: tüketiciler aramadan **AI
   Overviews ve LLM'lere** kayıyor, "organik aramada sert düşüş", **kredi kartı geliri −%24**. Sonuç:
   **SEO'ya bağımlı bir varlık kurmayacağız.** Savunulabilir olan doğrudan kitle (X + bülten) — Going'in
   kanıtladığı yol. Bu, fikir değil, denetlenmiş dosyadan çıkan strateji.
2. **Rekabet güçlü ve köklü.** Elskling, Compricer; üstüne **Elpriskollen** (Energimarknadsinspektionen'in
   aracı) bedava ve **komisyon almıyor**. Onlarla *karşılaştırmada* yarışamayız. Edge'imiz **karne**:
   "ne tavsiye edilmişti, ne oldu"yu tutan kimse yok. Bu bizim zaten kanıtlanmış formatımız.
3. **Nord Pool lisansı teyit edilmeli.** Bir forumda spot fiyatın izinsiz yeniden yayınının lisans
   gerektirdiği belirtilmiş; elprisetjustnu verisinin Nord Pool mu ENTSO-E mi olduğu tartışılmış.
   Kaynak eski ve yetkili değil. **CC BY 4.0 altında yayınlayan alternatifler var.** Kurmadan önce netleşecek.
4. Komisyon çıkar çatışması Ek 2 §2.4'teki haliyle aynen geçerli (F4 kuralı).

## 6. Güncellenen öneri

**Seçenek 4'ün (veri kartı fabrikası) elektrik alanındaki hali: "spot vs sabit karnesi".**
Kanıtlanmış model (karşılaştırma + komisyon: NerdWallet denetlenmiş, Compricer/Elskling İsveç'te satılmış),
kanıtlanmış birim ekonomisi (geçiş başına 30–60 £), bedava resmî veri, bizim tam motorumuz, bizim tam karne
mekaniğimiz, düşük hukuki risk, ve geliri ölmekte olan SEO'ya bağlı değil.

Sahte indirim konsepti (Ek 2) **çöpe gitmiyor**: aynı motorun ikinci vitrini olarak sonra eklenebilir —
ama birim ekonomisi 11 kat zayıf olduğu için **ilk sayfa o olmamalı.**

Ek kaynaklar: [NerdWallet 2025 tam yıl sonuçları (SEC 8-K)](https://www.sec.gov/Archives/edgar/data/1625278/000162527825000017/earningsreleaseq4fy24.htm) ·
[NerdWallet yatırımcı bülteni](https://investors.nerdwallet.com/news-releases/news-release-details/nerdwallet-reports-fourth-quarter-and-full-year-2025-results) ·
[MSE satışı (The Register)](https://www.theregister.com/2012/06/06/moneysavingexpert_sold_to_moneysupermarket/) ·
[MSE: bu site nasıl finanse ediliyor](https://www.moneysavingexpert.com/site/moneysavingexpert-finance/) ·
[Schibsted, Compricer'ı 135 MSEK'e aldı](https://www.ehandel.se/schibsted-koper-compricer-for-135-miljoner-kronor_2964-html) ·
[Compricer kâr patlaması (Breakit)](https://www.breakit.se/artikel/1182/vinstexplosion-i-compricer-forra-agarna-kan-fa-kvarts-miljard) ·
[Elskling nasıl çalışır](https://elbyte.se/Elskling) ·
[elprisetjustnu.se — açık ve bedava elpris API](https://www.elprisetjustnu.se/elpris-api) ·
[Ortaklık komisyon ölçütleri (dikey bazında)](https://track360.io/blog/affiliate-marketing-benchmarks-kpis-by-vertical-2026) ·
[Enerji geçişi komisyonu (The Energy Shop)](https://www.theenergyshop.com/affiliates) ·
[Bankrate/Red Ventures 1,4 Mrd$ (SEC)](https://www.sec.gov/Archives/edgar/data/0001518222/000151822217000021/rate-20170703xex99_1.htm)
