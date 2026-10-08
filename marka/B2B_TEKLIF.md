# Flow Event — "Lokalt synlig" hizmeti (İsveç, B2B)

Durum (8 Ekim 2026): **plan, onay bekliyor.** Hedef: **yan gelir (100–500 €/ay).**
Karar gerekçesi `YENI_SAYFA_ONERILERI.md` Ek 1–4'te.

**v2 notu:** Sahibi 7 Ekim'de üç haklı itiraz getirdi: (1) coğrafya belirsiz, (2) "her gün menü
değiştiren restoran" zayıf kanca — çoğu işletmenin günlük değişen verisi yok, (3) web sitesi
olmayanlara web sitesi verilmeli. Araştırma üçünü de doğruladı ve ürünü değiştirdi. v1
("otomatik içerik + rapor") bu belgede yerini v2'ye bıraktı.

---

## 1. v1 neden yanlıştı

v1 "her gün otomatik sosyal paylaşım" satıyordu. İki hatası vardı:

1. **Günlük değişen veri varsayımı.** Restoranın sabit menüsü var, kuaförün sabit fiyatı var.
   Günlük içerik üretecek veri yok; zorlarsan uydurma içerik üretirsin.
2. **Yanlış acıyı hedefliyordu.** Küçük işletmenin acısı "her gün paylaşmıyoruz" değil.
   Gerçek acı: **müşteri bizi bulamıyor, ya da yanlış bilgi buluyor.**

## 2. Araştırmanın değiştirdiği iki şey

**(a) İsveç küçük işletmelerinin ~yarısının web sitesi yok.**
STRATO/YouGov (Ocak 2025): sadece **%55'inin** kendi sitesi var (n=216, küçük örneklem — işaret
sayılmalı). Visma 2016: %44 yok, 2019: %38 yok. Sebep: zaman yokluğu, bilgi eksikliği, maliyet
korkusu. Sitesi olmayanların sadece **%18'i** önümüzdeki yıl yatırım yapmayı planlıyor.

**Ve en önemli satış bulgusu:** Visma 2019'da işletmelerin **%62'si "web sitesi satışı artırır
diye düşünmüyorum"** demiş. "Pahalı" diyen sadece %18. Yani **itiraz fiyat değil, inanç.**
→ **Web sitesi satmayacağız. "Daha fazla müşteri seni arayacak" satacağız; site onun parçası.**

**(b) Yorumlar, web sitesinden daha güçlü kaldıraç.**
Google'ın lokal paketi (aramada en üstteki 3 işletme), Maps ve bilgi paneli lokal görünürlüğü
belirliyor. Kaynak şunu söylüyor: **30 güncel yorumu olan işletme, 3 yorumu olandan belirgin
şekilde yukarıda çıkıyor.** Lokal görünürlük için gereken üçlü: **tam Google profili + güncel
yorumlar + hızlı mobil site.**

## 3. v2: ne satıyoruz

> **"Lokalt synlig" — müşteri seni ararken bulsun, doğru bilgiyi görsün, yorumları artsın.**

Dört parça, değer sırasına göre (en değerli en üstte):

| # | Parça | Neden değerli | Otomasyon |
|---|---|---|---|
| 1 | **Yorum motoru** | 30 yorum vs 3 yorum = lokal sıralamada belirgin fark. Doğrudan müşteri demek | Tezgaha QR / hizmet sonrası SMS ile **herkesten** yorum istenir; gelen her yoruma yanıt taslağı Claude yazar, işletme onaylar |
| 2 | **Google profili bakımı** | Yanlış çalışma saati = müşteri gelir, kapalı bulur, 1 yıldız verir. İsveç'te röda dagar bol | Tatil öncesi saat kontrolü, fotoğraf, bilgi güncelliği. İlk müşterilerde **elle** (biz "manager" olarak eklenir) |
| 3 | **Hızlı mobil web sitesi** | İşletmelerin ~%45'inde yok. Ara/rezervasyon butonu, tek sayfa, hızlı | Şablondan kurulur, içeriği Claude yazar, GitHub Pages'te barınır (maliyet ~0) |
| 4 | **İzleme + aylık karne** | Site düşerse, profil bozulursa **önce biz** haber alırız | Nöbetçi + alarm (mevcut `saglik.py` / `nobet.yml` deseni) |

**Sosyal paylaşım artık başlık değil, yan ürün.** İsteyene eklenir (ek ücret), ama ana vaat değil —
çünkü değer sıralamasında en altta.

## 4. Neden bu bize uygun: karnenin müşteriye uygulanması

Bu işin en güçlü tarafı, Mustafa'nın zaten sahip olduğu şeyle örtüşmesi: **ölçüp dürüstçe
raporlamak.** Google profili gerçek metrik veriyor (profil görüntülenmesi, arama tıklaması, yol
tarifi isteği, yorum sayısı). Yani her ay şunu gönderebiliyoruz:

> *"Eylül: yorum 3 → 11. Profil görüntülenmesi +%40. Telefon tıklaması 18 → 34."*

**Aylık ücretin iptal edilmemesinin sebebi bu.** Rakipler "paylaşım yaptık" diyor; biz
"müşteri sayın şu kadar arttı, işte rakamlar" diyoruz. Futbol botundaki karne felsefesinin
birebir aynısı, sadece müşteri için.

## 5. Coğrafya: sahibinin 1. sorusu

**Sadece Strömstad değil — ama "global" de değil.** Ürün doğası gereği lokal: Google lokal arama,
İsveççe dil, İsveç faturası. Üç halka:

| Halka | Neden | Ne zaman |
|---|---|---|
| **1. Strömstad / Tanum** | **Güven.** İsveçli küçük işletme tanıdığı kişiden alır; kapıdan girebilirsin. İlk referans ikinciyi satar | **Şimdi** |
| **2. Türk/göçmen işletmeleri, İsveç geneli** | **Senin asıl kozun.** Pizzeria, berber, bakkal, restoran: çoğunun sitesi yok, Google saati yanlış, İsveççe varlığı yok. İsveçli ajanslar dil ve güven bariyeri yüzünden onlara satamıyor. **Sen iki dili de konuşuyorsun.** Uzaktan teslim edilebilir, yani Strömstad'ın küçüklüğü sorun olmaktan çıkıyor | Ay 2–3 |
| **3. İsveç geneli, nişsiz** | Rekabet sert, güven avantajı yok | Sonra, ya da hiç |

**Halka 2 bu planın en değerli fikri.** Kıt kaynak pazar büyüklüğü değil, **güven.** 5 müşteri
için koca pazara ihtiyaç yok; dil ve kültür avantajı olan bir nişe ihtiyaç var.

## 6. Fiyat ve cebine giren

**Kurulum 9 900 kr + 1 795 kr/ay** (moms hariç). Web sitesi dahil olduğu için v1'den yüksek.

| Müşteri | Brüt/ay | Yıllık gelir | **Cebe/ay** |
|---|---|---|---|
| 1 | 1 795 kr | 31 440 kr | **1 286 kr ≈ 113 €** |
| 2 | 3 590 kr | 62 880 kr | **≈ 238 €** |
| 3 | 5 385 kr | 94 320 kr | **4 130 kr ≈ 362 €** |
| 5 | 8 975 kr | 157 200 kr | **6 974 kr ≈ 612 €** |

**Yan gelir hedefi (100–500 €/ay) = 1 ila 3 müşteri.**

Pazar karşılaştırması — fiyatımız kasten altta:

| | Fiyat |
|---|---|
| Küçük web stüdyoları | 25 000–60 000 kr + 500–1 500 kr/ay |
| Orta ajanslar | 50 000–120 000 kr + 1 500–4 000 kr/ay |
| SmedjaAI (otomasyon) | 9 995–29 995 kr + 995–4 995 kr/ay |
| Aylık web paketleri | 995–2 995 kr/ay |
| **Sen** | **9 900 kr + 1 795 kr/ay** |

Varsayımlar: aylık ~250 kr gider, NE'de %25 schablonavdrag, egenavgifter %28,97, kommunalskatt
~%32. **Vergi tahmini — muhasebeciye teyit.** Moms müşteriden alınır, Skatteverket'e gider.

## 7. Teknik kararlar (ilk müşteriler için en az hareketli parça)

1. **Google Business Profile API'yi ŞİMDİ kurmuyoruz.** Erişim elle onay istiyor: doğrulanmış ve
   60+ gün aktif profil, Google Cloud projesi, iş web sitesi, ~14 gün inceleme; onay **proje
   başına**; `business.manage` hassas kapsam, uygulama doğrulaması gerekiyor. **İlk 5 müşteride
   gereksiz:** profile "manager" olarak eklenip elle/yarı otomatik yönetiriz, bedava ve anında.
   API 10+ müşteride kendini amorti eder.
2. **Web sitesi GitHub Pages'te** — barındırma bedava, kendi panelimizde kanıtlanmış.
3. **Instagram otomatik paylaşım yok** (Meta onay süreci). İsteyene hazır gönderi gider.
4. **Yorum isteme kuralı:** Google **teşvikli** yorumu ve yalnızca mutlu müşteriden yorum
   isteme ("gating") uygulamalarını yasaklıyor. **Kuralımız: herkesten istenir, hiçbir teşvik
   verilmez.** Kesin politika metni kurulumdan önce doğrulanacak.
5. **SMS/GDPR:** müşteri ilişkisi işletmenin; biz aracı yazılımı veriyoruz. Yasal dayanak ve
   metin kurulumdan önce kontrol edilecek.

## 8. Flow Event tarafı — zaten hazırsın

| Konu | Durum |
|---|---|
| Momsregistrerad + F-skatt | **Var.** Yarın fatura kesebilirsin |
| Hizmet momsu | %25 |
| Moms beyanı | Kvartal, fakturametoden (Q4 → 12 Şubat) |
| Faturada olmalı | Tarih, numara, momsnumarası, alıcı adı+adresi, hizmet ve tarihi, moms hariç tutar, moms oranı ve tutarı, **"Godkänd för F-skatt"** |
| Gelir → NE-bilaga | **R1** |
| Claude aboneliği | **R6**; ABD satıcısı → ters yükleme: **ruta 22**, %25'i **ruta 30**, aynısı **ruta 48** |

**Hemen yapılacak:** Anthropic fatura ayarlarına Flow Event momsnumarasını (SE…01) gir.

## 9. İlk 30 gün

| Hafta | İş | Kim |
|---|---|---|
| 1 | İsveççe tek sayfa teklif: fiyat açık, "daha fazla müşteri" dilinde, site değil **sonuç** satar | Claude |
| 1 | Momsnumarası + fatura şablonu | Mustafa |
| 1 | **Vitrin:** kendi sitemiz + kendi Google profilimiz örnek olarak kurulur | Claude |
| 2 | 20 hedef listesi: Strömstad/Tanum + Türk işletmeleri. Ölçüt: **sitesi yok veya Google profili eksik/yanlış** (bu dışarıdan görülebiliyor) | Claude araştırır |
| 2–3 | Soğuk e-posta + kapıdan ziyaret. Açılış: *"Google'da profilinde şu üç şey eksik"* — somut, ücretsiz tespit | Mustafa |
| 3–4 | İlgilenene **ücretsiz tespit raporu**: profilinde ne eksik, kaç yorumu var, rakibinde kaç var | Claude üretir |
| 4 | İlk kurulum + ilk fatura | İkisi |

**KAPI: 8 haftada 1 ödeyen müşteri.**

**Satış kancası fiyat değil, ücretsiz tespit.** "Rakibinin 34 yorumu var, senin 3. Google'da
cumartesi kapalı görünüyorsun ama açıksın." Bunu dışarıdan, izinsiz, ücretsiz görebiliyoruz —
ve bu, %62'lik "web sitesi işe yaramaz" inancını kıran tek şey: somut kayıp.

## 10. Dürüst riskler

1. **Gerçek iş satış.** 20 e-postayı ve ziyaretleri Mustafa yapacak; Claude yapamaz.
2. **İnanç bariyeri (%62).** Fiyat kırmak işe yaramaz; somut tespit raporu şart.
3. **"Risk yok" yanlış.** Aylık ücret aylık sorumluluk: müşterinin sitesi düşerse Mustafa'nın
   problemi. Nöbetçi/alarm satışın parçası, süsü değil.
4. **Kapsam kayması.** "Bir de şunu ekle" ile 1 795 kr'lık iş 10 saate döner. Teklifte dahil/değil
   yazılı olmalı.
5. **Yorum politikası.** Google'ın teşvik ve gating yasağı net anlaşılmadan yorum motoru
   kurulmaz; yanlış kurulum müşterinin profilini riske atar.
6. **Örneklem zayıf.** "%45'inin sitesi yok" verisi 216 kişilik ankete dayanıyor; yön doğru ama
   kesin oran değil.
7. **Vergi hesabı tahmin.** Muhasebeciye teyit edilecek.

## 11. Medya hattı ne olacak

Kapatılmıyor, yeni yatırım almıyor. İki bot ayda ~8 € ile çalışıp karne biriktirir. Görevi:
**satış vitrini** — "halka açık, tarihli karne tutan iki canlı sistem kurdum ve işletiyorum."

---

Kaynaklar: [Vartannat småföretag saknar hemsida (STRATO/YouGov 2025)](https://driva-eget.se/artiklar/halften-av-smaforetagare-saknar-hemsida-2025) ·
[Visma: fyra av tio utan hemsida](https://media.visma.se/pressreleases/fyra-av-tio-smaafoeretagare-har-ingen-hemsida-2950501) ·
[Visma: vartannat småföretag](https://www.mynewsdesk.com/se/visma/pressreleases/vartannat-smaafoeretag-saknar-egen-hemsida-1565100) ·
[SVT: många småföretag saknar hemsida](https://www.svt.se/nyheter/lokalt/jonkoping/manga-smaforetag-saknar-hemsida) ·
[Google Företagsprofil ve lokal SEO](https://www.haarp.se/kunskap/google-foretagsprofil-lokal-seo-guide) ·
[Lokal SEO checklista](https://webraketen.se/blog/lokal-seo-smaforetag/) ·
[Google: Business Profile API prerequisites](https://developers.google.com/my-business/content/prereqs) ·
[Business Profile API overview](https://developers.google.com/my-business/content/overview?hl=en) ·
[GBP API onay kapısı](https://xovionlabs.com/blog/google-business-profile-api-hidden-gate/) ·
[AI danışman saat ücreti (Satori)](https://www.satoriml.se/blog/ai-konsult-priser-2026-vad-kostar-det) ·
[Webbyrå fiyat aralıkları (Siteflow)](https://siteflow.se/webbyra-sverige) ·
[Hemsida pris (Groundwork)](https://groundwork.se/hemsida-pris)
