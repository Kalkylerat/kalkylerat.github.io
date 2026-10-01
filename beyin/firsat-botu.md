# Fırsat botu: proje özeti ve devir notu

Bu dosya, 30 Eylül – 1 Ekim 2026 tarihli beyin fırtınası sohbetinin kararlarını taşır. Yeni bir Claude Code
oturumu bu dosyayı okuyarak işe başlamalı. Sohbetin geri kalanını göremez; gereken her şey burada.

## Sahibin istekleri (kesin)
- **Amaç:** Para getiren, tam otomatik bir X (Twitter) hesabı. Sahip X'i bir otomasyon deneme alanı olarak
  görüyor; para gelirse güzel, ama sistemin kendisi de önemli.
- **Dil:** İsveççe. Hedef kitle İsveç'te alışveriş yapan insanlar.
- **Dürüstlük:** İnsanları yanıltmak yok. Sahte indirim, sahte "son 3 ürün" baskısı, uydurma rakam yok.
- **Maliyet:** Çok düşük kalmalı. Günlük işte Claude API kullanılmayacak (önceki bir denemede API ~9$ yaktı,
  sahip bundan rahatsız oldu). Metni ve rakamları kod üretir. Anthropic hesabının aylık sınırı 15$ ve
  Kalkylerat botu da aynı anahtarı kullanıyor.
- **Hatasızlık:** Sahip "hatasız" istiyor. Yanlış fiyat ya da yanlış ürün paylaşmaktansa hiç paylaşmamak
  tercih edilir. Her şüpheli durumda bot susar ve GitHub issue açar.
- **Sahibin yükü:** Günde birkaç dakikadan az. İsteğe bağlı onay (Kalkylerat'taki "ok/iptal" issue akışı).
- **Anonimlik:** Sahibin adı görünmez. Otomasyon etiketi takma adlı ayrı bir yönetici hesabına bağlanır.

## Konsept
Mağazaların ürün verisini her gün tarayan, **gerçek** fiyat düşüşlerini bulan ve kart görseliyle paylaşan
İsveççe fırsat hesabı. Her paylaşım satın alınabilir bir ürün; gelir ortaklık (affiliate) komisyonundan gelir.

Örnek tweet:
> 🔥 Sony WH-1000XM5: 3 990 kr → 2 790 kr (−30 %)
> Lägsta priset på 90 dagar · Hos [butik]
> Annons: länk i svaret

## Neden bu fikir (kısa gerekçe)
- Etkileşim tek başına para değil; para satın alma niyetinden gelir. Fırsat arayan takipçi zaten almaya hazır.
- Elenen fikirler ve nedenleri: Elpris (kitle küçük), borsa/altın sinyalleri (AB yatırım tavsiyesi kuralları,
  ESMA 2024 uyarısı), bulmaca hesabı (etkileşim var, para yolu zayıf), bahis ortaklığı (sahip istemiyor).
- X'in kendi ödeme programı otomatik içeriğe ödeme yapmıyor (Creator Revenue Sharing 7 Eylül 2026'da kapandı;
  yerine gelen Original Content Rewards otomatik içeriği dışlıyor). Gelir yalnızca X dışından gelecek.

## Kalkylerat'tan kopyalanacak sistem
Kalkylerat (`Kalkylerat/kalkylerat.github.io`) şu anda son düzenlemelerini alıyor. Kopya, ana daldaki **son**
halinden alınmalı ve **ayrı bir repoda** kurulmalı (iki bot birbirini bozmasın).

| Kalkylerat'ta | Fırsat botunda |
|---|---|
| `.github/workflows/kalkylerat.yml` zamanlama, nabız, onay issue'su, kayıt commit'i | Aynı yapı |
| `bot/onay.py` ("ok"/"iptal" onayı) | Aynen |
| `bot/gorsel.py` (Pillow kart) | Aynı sistem, yeni tasarım: ürün görseli, eski/yeni fiyat, indirim |
| `bot/tweets.py` (metin, 280 karakter kontrolü) | İsveççe fırsat metinleri |
| `bot/kayit.py`, `data/*.json` | Fiyat geçmişi ve paylaşılanlar kaydı |
| `bot/panel.py`, `docs/` (GitHub Pages) | Fırsat sitesi: güncel fırsatlar, ortaklık linkleri |
| `bot/football.py`, `bot/oddsapi.py`, `bot/model.py` | **Yerine:** ürün verisi kaynağı + fiyat geçmişi analizi |
| `bot/editor.py` (Claude ile seçim) | **Kaldırılır.** Seçim kural tabanlı |
| `tests/` | Yeni modüller için aynı titizlikte testler |

## Fırsat seçim kuralları (hatasızlığın merkezi)
Bir ürün ancak şunların **hepsi** sağlanırsa paylaşılır:
1. Fiyat geçmişi en az 30 gün (tercihen 90) **bizim kendi kaydımızda** var. Mağazanın "önceki fiyat" iddiasına
   tek başına güvenilmez.
2. Bugünkü fiyat, son 30 günün ortanca fiyatından en az %20 düşük **ve** son 90 günün en düşüğüne eşit ya da altında.
3. Fiyat iki ardışık çekimde aynı (tek seferlik veri hatası değil).
4. Ürün stokta, link çalışıyor (HTTP 200), ürün sayfasındaki fiyat veriyle tutarlı.
5. Kategori izinli listede (elektronik, ev, spor, oyuncak vb.). Yasaklı: alkol, tütün, ilaç, kumar, yetişkin içeriği.
6. Aynı ürün son 14 günde paylaşılmamış.
7. Günde en fazla 3–5 paylaşım; en büyük gerçek indirim önce.

Şüphe durumunda (veri eksik, fiyat tutarsız, link bozuk) **paylaşım yok, issue açılır.**

İsveç marknadsföringslagen: ortaklık linki içeren her paylaşım "Annons" ya da "Reklam" ile başlar ya da açıkça
işaretlenir. Prisinformationslagen ve AB Omnibus direktifi: "önceki fiyat" olarak son 30 günün en düşük
fiyatı esas alınır. Bot bu kurala kendi geçmiş verisiyle uyar. Hukuki ayrıntılar doğrulanmalı.

## Para ve maliyet
- **Gelir:** Adtraction (İsveç ağırlıklı ağ; mağaza ürün feed'leri sunuyor) ve Amazon.se Associates.
  Komisyon tipik olarak satışın birkaç yüzdesi. **Oranlar doğrulanmadı**, başvuru sonrası görünür.
- **Link stratejisi:** X API'de linkli gönderi 0,20$, normal gönderi 0,015$ (docs.x.com pricing, 2026).
  Seçenekler: (a) yalnızca en iyi fırsatlarda linki yanıta koymak, (b) profilde tek link, GitHub Pages fırsat
  sitesi. Başlangıç: (b), en iyi 1 fırsatta (a).
- **Tahmini aylık gider:** X API ~2–20$ (link stratejisine göre), veri 0$, Claude 0$.
- **Kaba gelir hesabı (tahmin):** 2.000 kr ürün × %3 = 60 kr/satış; ayda 3–4 satış linkli tweet maliyetini karşılar.

## Açık sorular (kod yazmadan önce araştırılmalı)
1. Adtraction'daki İsveç mağazalarından hangileri **ürün feed'i** (fiyat, stok, görsel, ürün linki) veriyor?
   Feed kullanım şartları sosyal medyada paylaşıma ve fiyat geçmişi tutmaya izin veriyor mu?
2. Amazon.se Associates: Product Advertising API erişim şartı (bildiğimiz kadarıyla önce belirli sayıda satış
   gerekiyor, doğrulanmadı). Erişim yoksa Amazon başlangıçta dışarıda kalır.
3. Prisjakt/PriceRunner gibi karşılaştırma sitelerini kazımak şartlarına aykırı olabilir; **kullanılmamalı**.
4. Ürün görsellerini kart içinde kullanma izni (feed şartlarına bağlı).
5. İsveç'te rakip fırsat hesapları (X'te ve dışında) ve onların zayıf yanları.
6. X otomasyon kuralları (help.x.com bu ortamdan erişilemedi): otomatik paylaşım ve yanıtta link.

## Sahibin yapması gerekenler
1. Adtraction'a ve Amazon.se Associates'a enskild firma ile başvurmak (ücretsiz).
2. Yeni e-posta, yeni X hesabı, takma adlı yönetici hesabı, X geliştirici anahtarları (Kalkylerat README'sindeki
   adımlar).
3. Yeni repo (ör. `fyndbot`) ve GitHub Secrets.

## Çalışma kuralları (yeni oturum için)
- Önce açık soruları araştır ve sahibe kısa bir özet sun; onay al, sonra kur.
- Claude API'yi günlük akışa koyma. Pahalı araç kullanımı (web araması döngüleri) yalnızca sohbette, botta değil.
- Önce **kuru çalışma** modu: paylaşmadan, bulduğu fırsatları issue olarak gösterir. Sahip birkaç gün kontrol
  ettikten sonra paylaşım açılır.
- Testler gerçek ağa çıkmaz; her kural için test yazılır.
- Sahiple Türkçe konuş; sahip sesli yazıyor, metin bazen bozuk gelebilir.
