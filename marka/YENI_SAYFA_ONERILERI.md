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
