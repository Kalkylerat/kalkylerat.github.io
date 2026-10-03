# İkinci hesap — içerik stratejisi

Kalkylerat (futbol) olduğu gibi devam eder. Bu, ayrı ve yeni bir hesap.
Kriterler: para kazanma, etkileşim, legal, mümkün olduğunca otonom.

## 1. Mevcut hesapların içerik stratejisi (tersine mühendislik)

@azed_ai, @umesh_ai ve benzerlerinin post anatomisi:

1. **Tek kahraman görsel** (ya da 2×2 sonuç ızgarası) + promptun tam metni postun içinde, düz yazı.
2. **Prompt bir şablon, değişkenler köşeli parantezde:** `[SUBJECT]`, `[PART]`, `[HIGHLIGHTED_PART]`.
   Ürün promptun kendisi değil, okuyucunun kendi konusunu yerine koyabilmesi.
3. **Prompt iç yapısı sabit sırada:** kamera/cihaz → sahne → ışık → özne → ortam →
   teknik kalite işaretleri ("no airbrushing", "realistic skin texture") → negatif talimatlar.
4. **Spesifiklik işaretleri:** tam saat (9:41), en-boy oranı en başta, marka/estetik referansı
   ("Taobao", "GTA 6", "1980s propaganda").
5. **Tekrarlayan kategoriler:** fotogerçekçilik, oyun ekran görüntüsü, UI/uygulama arayüzü,
   tipografi/poster, tarihsel mashup, infografik. **Hepsi portre değil** — bu bizim için önemli.
6. **Format:** öncesi/sonrası tek görseli istikrarlı biçimde geçiyor; carousel ve "cheat sheet"
   erişim ve kaydetme tarafında diğer formatları eziyor.
7. **Tempo:** günde bir prompt.
8. **Gelir:** elçilik/marka ortaklığı (ikisi de Adobe elçisi).

## 2. Boşluk: yayınladıkları promptlar tekrarlanamıyor

Bu bir tahmin değil, teknik olarak bilinen bir şey:

- Modeller varsayılan olarak **rastgele seed** kullanır; her çalıştırma farklı gürültüden başlar.
- Her modelin **metin kodlayıcısı kelimeleri farklı ağırlıklandırır** — aynı prompt modeller arası aynı değil.
- **Belirsiz stil kelimeleri** ("cinematic vibes", "aesthetic") modelin boşluğu kendi varsayımıyla
  doldurmasına yol açar; her denemede farklı doldurur.

Bilinen çözüm: **seed'i kilitle, model sürümünü sabitle, belirsiz stil kelimelerini at,
çerçeve/ışık/oran gibi kısıtları her seferinde açıkça yaz.**

Yani piyasadaki promptların çoğu, *yapısı gereği* okuyucuda aynı sonucu vermiyor. İnsanlar
promptu kopyalıyor, sonuç çıkmıyor, promptu suçluyor. **Çözülmemiş acı tam burada.**

## 3. Eklediğimiz şey: "locked prompt"

Hesabın tek cümlelik tanımı:

> Viral promptları alıp tekrarlanabilir hale getiriyoruz, ve kaç denemede tuttuğunu yazıyoruz.

Rakip "işte güzel bir prompt" diyor. Biz "işte 12 denemenin 12'sinde aynı sonucu veren prompt,
ve orijinali neden 12'de 5'te kalıyordu" diyoruz. Kitlenin **kalite** olarak göreceği fark bu:
mutfakta test edilmiş tarif ile internetten kopyalanmış tarif arasındaki fark.

## 4. Post formatları

### A) Günlük ana post — "Locked prompt"
```
[2×2 ızgara: dört ayrı denemede aynı sonuç]

LOCKED ✅ 12/12
model: <ad> <sürüm> · seed: 4471 · 3:4

<promptun tam metni, değişkenler [KÖŞELİ] parantezde>

Orijinal viral hali: 12'de 5. Değişen: "cinematic vibes" çıktı,
rim-light açısı ve odak uzaklığı açıkça yazıldı.
```
İmza post. Hiç kimse tekrarlanabilirlik satırı yayınlamıyor.

### B) "Prompt teşhisi" (2 günde bir)
Viral bir promptu alıp **neden** bozulduğunu göstermek: 15 denemede 7, bozulma deseni
(gözlük varsa, yan profilde, koyu tenli öznede), sonra düzeltilmiş hali.
Etkileşim motoru bu: veriye dayalı, kavgasız tartışma.

### C) Haftalık carousel — "cheat sheet"
Araştırma net: carousel + cheat sheet erişim ve **kaydetme**de her formatı geçiyor.
Haftanın 7 locked promptu tek karta. Kaydetme algoritma için altın, ve ücretli paketin doğal fragmanı.

### D) "Aynı prompt, 3 model" (haftada 1)
Aynı locked prompt üç görsel modelde. Kalkylerat'ın DNA'sı: fiyat/performans.
Hangi model tuttu, kaça, kaç saniyede.

### E) Aylık "bozulma atlası"
Hangi prompt ailesi hangi girdide bozuluyor. Satılacak/alıntılanacak arşiv varlığı bu.

## 5. Kalite sinyalleri (bedava, ama premium okunur)

- Her postta **model + sürüm + seed + oran** yazılı. Kimse yazmıyor.
- **Tekrarlanabilirlik oranı her zaman açık** — kötü olsa da. Kalkylerat'ın şeffaf rekor kozu.
- **Başarısız denemeler de gösterilir.** Güvenin kaynağı bu.
- Tek tip kart tasarımı (`bot/gorsel.py` hazır).
- **Postta link yok** (hem $0.20 yerine $0.015, hem erişim). Link bio ve sabit tweette.
- AI beyanı + makine-okunur işaretleme (AI Act) **güven sinyali olarak** sunulur, mecburiyet gibi değil.
- Uydurma hashtag yok; en fazla 1–2 gerçek etiket.

## 6. Legal — temiz kurulum

Kritik tasarım kararı: **biz hizmet satmıyoruz, prompt yayınlıyoruz.**
Okuyucu promptu kendi fotoğrafına kendi uygular. **Hiçbir kullanıcı fotoğrafı bize gelmez,
sistemimize girmez, saklanmaz.** GDPR veri sorumlusu yükü böylece hiç doğmuyor.

- Test seti: **sentetik (AI üretimi) yüzler + lisanslı stok.** Gerçek, tanınabilir üçüncü kişi yok.
  Sahibinin kendi fotoğrafı da kullanılmaz (hesap anonim kalır — mevcut kural).
- **Portre olmayan kategorilerle başlanır** (poster/tipografi, UI, ürün, oyun, infografik):
  kişisel veri sorunu sıfır, ve bu kategoriler zaten rakiplerin repertuarında.
  Portre kategorisi sentetik yüzlerle eklenir.
- Müstehcen/cinselleştirilmiş içerik, siyasi figür, çocuk görseli, gerçek kişi benzerliği: **mutlak yasak, kodda sabit.**
- Her görselde AI işaretlemesi (AI Act madde 50).

## 7. Para — geliş sırasına göre

| Sıra | Yol | Eşik | Not |
|---|---|---|---|
| 1 | **Affiliate** | ~800 takipçi | Somut örnek: 800 takipçi, $49/ay araca 15 dönüşüm × %30 = **$220/ay** |
| 2 | **Prompt paketi** | ~1–2K takipçi | Piyasada $9. **Bizimki her promptun tekrarlanabilirlik oranı yazılı tek paket** → $19–29 savunulabilir |
| 3 | Sponsorluk | hacim ister | Görsel AI araçları bu nişte aktif sponsor |
| 4 | Arşiv → B2B | 6+ ay | Ajanslara güvenilir prompt kütüphanesi |

**Çıkar çatışması kuralı:** D formatında modelleri karşılaştırıyoruz. O yüzden
**sıraladığımız modellerin/araçların affiliate'i alınmaz.** Affiliate yalnızca sıralamaya
girmeyen yan araçlardan (upscaler, stok, editör). Sıralama parayı asla takip etmez.

## 8. Otonomi

Bot: prompt havuzundan seçer → N deneme × M konu × K model üretir → sonucu puanlar →
tekrarlanabilirlik oranını hesaplar → kartı üretir → denetçiden geçirir → paylaşır → arşive yazar.

**Tek gerçek zorluk puanlama:** "çıkan görsel promptu karşılıyor mu". İki katmanlı çözüm:
(a) deterministik kontroller (oran doğru mu, yüz korunmuş mu, metin okunur mu),
(b) görü modeliyle hakem. İlk hafta elle kalibre edilir, sonra otonom.

Sana kalan: `marka/NIS_ARASTIRMA.md`'deki A/B seçimi. Elle yanıt yazarsan hızlı büyür,
yazmazsan yavaş. Kod ikisinde de aynı — ama **Kalkylerat da zaman istiyor**, iki hesaba
birlikte günde 20–30 dk ayırmak gerçekçi değil. Biri otonom (B), diğeri elle beslenir (A).

## 9. Maliyet — dikkatli olunacak tek kalem

Tekrarlanabilirlik testi görsel yakar: 1 prompt × 12 deneme = 12 görsel.
Görsel başına kabaca $0.03–0.20 → **prompt başına $0.36–2.40.**
Günde ~15–20 görselle **ayda $15–120.** Aralık geniş; ilk ay ölçülüp sabitlenecek.

| Kalem | Aylık |
|---|---|
| Görsel üretim | $15–120 (ölçülecek) |
| Claude (direktör + puanlama) | $25–40 |
| X API (ikinci hesap, ~5 post/gün) | ~$5 + medya yükleme (teyit edilecek) |
| X Premium (ikinci hesap) | $8 |
| **Toplam** | **~$55–175** |

Azaltma: toplu denemeler ucuz modelde, pahalı model yalnızca D formatında.
Affiliate ~800 takipçide $220/ay getirebildiği için başabaş erken gelebilir.

## 10. İsim önerisi

| Ad | Neden |
|---|---|
| **Promptproof** (öneri) | Tek kelime, "kanıtlanmış/su geçirmez" çağrışımı, ürünü anlatıyor, İngilizce, markalaşır |
| Locked Prompt | Çok açık, imza postun adı zaten bu |
| Reprompt | Kısa ama "tekrar sor" anlamı yanlış yöne çekiyor |

**Kullanıcı adı müsaitliği kontrol edilmedi** — X elle kontrol edilecek.
