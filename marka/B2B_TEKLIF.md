# Flow Event — otomasyon hizmeti teklifi (İsveç, B2B)

Durum (7 Ekim 2026): **plan, onay bekliyor.** Hedef: **yan gelir.** Karar gerekçesi
`YENI_SAYFA_ONERILERI.md` Ek 1–4'te. Bu dosya "ne satıyoruz, kaça, kime" sorusunun cevabı.

## 1. Neden bu yol (tek paragraf)

Yan gelir hedefi için aritmetik tek yeri işaret ediyor. Medya hattı 6 ayda **22–189 €** üretiyor
(saat başı 0,59–5 €). **Tek** B2B müşterisi 6 ayda **563 €** üretiyor — medya planının ~5 katı — ve
kitle, takipçi, reklam, SEO gerektirmiyor. Hedef 100–500 €/ay ise bu **1–5 müşteri** demek,
10.000 takipçi değil.

## 2. İsveç pazarı: yayınlanmış fiyatlar

| Sağlayıcı | Fiyat |
|---|---|
| AI Kollegorna | 4 900 kr/ay, kurulum 0 |
| SmedjaAI | 9 995–29 995 kr kurulum + 995–4 995 kr/ay |
| Satori | 15 000 kr kurulum + aylık |
| Synligwebb | otomasyon 13 500 kr'den; saat 900 kr |
| Aeger | 500 € audit → 2 500 € kurulum → 150 €/ay |
| UmvioTech (web) | 1 499 kr kurulum + 399–999 kr/ay |
| Groundwork (web) | 0 kurulum + 995 kr/ay |

AI danışman saat ücreti: **900–2 500 kr/saat** (küçük işletme odaklı ajanslar 900 kr).

**Pazarın en önemli özelliği: şeffaf değil.** Kaynaklardan biri açıkça şunu söylüyor — yedi İsveççe
karşılaştırma listesinin altısı, kendi listesinde birinci sırada olan şirket tarafından yazılmış ve
**sadece iki İsveçli sağlayıcı fiyatını yayınlıyor.** Bu bizim için fırsat: **fiyatı açıkça yayınlamak
başlı başına farklılaştırıcı** — ve karne felsefemizin birebir devamı.

## 3. Ne satıyoruz

Mustafa'nın **kanıtlanmış** yığını (canlıda, haftalardır çalışıyor): zamanlanmış otomasyon
(GitHub Actions + 7 dk nöbetçi), API'den veri toplama, kart/görsel üretimi, sosyal medyaya otomatik
paylaşım, **sağlık kontrolü + bozulunca alarm**, yanlış çıktıyı engelleyen denetçi katmanı, herkese
açık panel, 228 test.

Bunun işletme diline çevrilmiş hali — **tek, dar paket:**

> **"Otomatik içerik + haftalık rapor, bozulduğunda haber veren."**
> İşletmenin kendi verisi (menü, program, stok, fiyat, randevu) → her gün otomatik sosyal medya
> paylaşımı + haftalık özet raporu. Sessizce bozulmaz: bozulursa alarm gelir ve düzeltilir.

**Hedef işletme tipleri:** düzenli paylaşım yapması gereken ama yapacak kimsesi olmayanlar —
restoran (günün menüsü), gym (program), kuaför/salon (boş randevular), küçük e-ticaret (yeni ürün,
fiyat değişimi).

**Farklılaştırıcımız üç şey:** (1) fiyat açıkça yayınlı, (2) sessizce bozulmaz — nöbetçi ve alarm
dahil, (3) çalıştığının kanıtı var: halka açık, tarihli karne tutan iki canlı sistem.

## 4. Fiyat (moms hariç)

**Kurulum 7 500 kr + 1 495 kr/ay.** Kasten pazarın altında: SmedjaAI'nin en ucuz kurulumunun
(9 995) altında, AI Kollegorna'nın aylığının (4 900) çok altında — ama UmvioTech'in web paketinin
(999) üstünde, çünkü bu web sitesi değil, otomasyon + izleme.

## 5. Cebine ne giriyor (yıllık, moms hariç)

| Müşteri | Brüt/ay | Yıllık gelir | Överskott | Egenavgifter | Skatt | **Cebe/yıl** | **Cebe/ay** |
|---|---|---|---|---|---|---|---|
| 1 | 1 495 kr | 25 440 kr | 23 640 kr | 5 136 kr | 5 674 kr | **12 830 kr** | **1 069 kr ≈ 94 €** |
| 3 | 4 485 kr | 76 320 kr | 74 520 kr | 16 191 kr | 17 885 kr | **40 444 kr** | **3 370 kr ≈ 296 €** |
| 5 | 7 475 kr | 127 200 kr | 125 400 kr | 27 246 kr | 30 096 kr | **68 058 kr** | **5 671 kr ≈ 497 €** |
| 8 | 11 960 kr | 203 520 kr | 201 720 kr | 43 829 kr | 48 413 kr | **109 478 kr** | **9 123 kr ≈ 800 €** |

Varsayımlar: aylık ~150 kr işletme gideri (Claude + hosting + alan adı), NE'de %25 schablonavdrag,
egenavgifter %28,97 (2026), kommunalskatt ~%32. **Vergi tarafı tahmin — muhasebeciye teyit ettir.**
Moms (%25) müşteriden alınır ve Skatteverket'e gider; **senin gelirin değil.**

**Yan gelir hedefi 100–500 €/ay ise: 1 ila 5 müşteri.**

## 6. Flow Event tarafı — zaten hazırsın

| Konu | Durum |
|---|---|
| Momsregistrerad + F-skatt | **Var.** Yarın fatura kesebilirsin |
| Hizmet momsu | %25 (DJ hizmetiyle aynı) |
| Moms beyanı | Kvartal, fakturametoden (Q4 → 12 Şubat) |
| Faturada olması gerekenler | Tarih, numara, momsnumarası, alıcı adı+adresi, hizmet ve tarihi, moms hariç tutar, moms oranı ve tutarı, **"Godkänd för F-skatt"** |
| Gelir → NE-bilaga | **R1** (momspliktiga intäkter, moms hariç) |
| Claude/Anthropic aboneliği | Gider **R6**. ABD satıcısı → ters yükleme: tutar **ruta 22**, %25'i **ruta 30**, aynısı **ruta 48** (iş payı %100 ise net etki 0 ama **beyan zorunlu**) |

**Hemen yapılacak:** Anthropic fatura ayarlarına Flow Event'in momsnumarasını (SE…01) gir —
sonraki faturalar momssuz gelir ve sadece fiktiv moms kalır.

## 7. İlk 30 gün

| Hafta | İş | Kim |
|---|---|---|
| 1 | Paketi netleştir: tek sayfa teklif (İsveççe), fiyat açık, ne dahil ne değil | Claude yazar |
| 1 | Anthropic'e momsnumarası, fatura şablonu (F-skatt ibareli) | Mustafa |
| 2 | 20 hedef işletme listesi (Strömstad/Tanum/Göteborg çevresi, sosyal medyası zayıf olanlar) | Claude araştırır |
| 2–3 | Soğuk e-posta (İsveççe), 20 işletmeye, tek tek | Mustafa gönderir |
| 3–4 | Görüşen 1–2 işletmeye **ücretsiz demo**: kendi verisiyle 3 günlük otomatik paylaşım | Claude kurar |
| 4 | İlk fatura | Mustafa |

**KAPI: 8 haftada 1 ödeyen müşteri.** Olmazsa teklif ya fiyat yanlış; paketi değiştirip tekrar
denenir, ya da bu yol da kapanır ve dürüstçe söylenir.

## 8. Dürüst riskler

1. **Gerçek iş satış, kod değil.** Mustafa'nın 20 e-posta yazıp görüşmeye girmesi şart; Claude bunu
   yapamaz. Bu adım atlanırsa plan çalışmaz.
2. **"Risk yok" yanlış.** Aylık ücret aylık sorumluluk demek: müşterinin otomasyonu bozulursa
   Mustafa'nın problemi. Nöbetçi/alarm bu yüzden satışın parçası, süsü değil.
3. **Kapsam kayması.** "Bir de şunu ekle" ile aylık 1 495 kr'lık iş 10 saatlik işe dönüşür. Teklifte
   ne dahil / ne değil yazılı olmalı.
4. **Müşteri kaybı.** 1 495 kr/ay kolay iptal edilir. Değerin her ay görünür olması lazım — haftalık
   rapor tam bu yüzden pakette.
5. **Vergi tahmini.** Tablodaki egenavgifter/skatt hesabı tahmin; muhasebeciye teyit ettirilecek.

## 9. Medya hattı ne olacak

Kapatılmıyor, **yeni yatırım da almıyor.** İki bot ayda ~8 € ile çalışmaya devam eder ve karne
biriktirir. Görevi değişti: ürün değil, **satış vitrini** — "halka açık, tarihli karne tutan iki
canlı sistem kurdum ve işletiyorum" demek, teklifin en güçlü kanıtı.

Kaynaklar: [AI Kollegorna fiyat karşılaştırması](https://www.aikollegorna.se/insikter/ai-byraer-sverige-2026) ·
[AI danışman saat ücreti (Satori)](https://www.satoriml.se/blog/ai-konsult-priser-2026-vad-kostar-det) ·
[AI danışman fiyatı (Swivrr)](https://www.swivrr.se/priser/vad-kostar-ai-konsult) ·
[AI projesi fiyatı (Swivrr)](https://www.swivrr.se/priser/vad-kostar-ai-projekt) ·
[İsveç AI ajansları karşılaştırması (Wicflow)](https://wicflow.com/blog/basta-ai-byraerna-sverige-2026/) ·
[Synligwebb AI hizmetleri](https://synligwebb.se/ai-tjanster/) ·
[Web aylık paket (Groundwork)](https://groundwork.se/hemsida-pris) ·
[Web aylık paket (UmvioTech)](https://www.umviotech.com/vad-kostar-en-hemsida) ·
[Webbyrå fiyat aralıkları (Siteflow)](https://siteflow.se/webbyra-sverige)
