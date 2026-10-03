# Kanıtlanmış AI hesapları — ne yapıyorlar, nasıl para kazanıyorlar

Araştırma: 3 Ekim 2026. Kaynaklar web araması; **takipçi sayıları ikincil kaynaklardan, eski olabilir.**
Kesin sayı gerekirse `bot/__main__.py:1106` zaten `public_metrics` okuyor — 10 hesap = 10 okuma = **$0.05**.

## Kanıtlanmış 10 + 1

| # | Hesap / sayfa | Ölçek | Model | Para nereden |
|---|---|---|---|---|
| 1 | **The Rundown** (@rowancheung) | 567K X, 1M bülten abonesi | Günlük AI haber küratörlüğü → bülten → topluluk | **7 haneli yıllık.** Premium "University" $99/ay, 5.000+ üye + sponsorluk |
| 2 | **Ben's Bites** (@bentossell) | 120K günlük abone | Küratörlük + derin analiz | Sponsorluk + premium **$150/yıl**. "120K odaklı, 1.75M genelden iyi" vakası |
| 3 | **Matt Wolfe** (@mreflow) | ~1M YouTube | Araç tanıtımı + Future Tools dizini | YouTube reklamı + affiliate + dizin |
| 4 | **LMArena** | 5M aylık kullanıcı, 60M konuşma/ay | Kamuya açık model sıralaması (bedava) → laboratuvarlara özel değerlendirme (ücretli) | **$30M+ yıllık koşu hızı.** $150M yatırım, $1.7 milyar değerleme |
| 5 | **Artificial Analysis** | sektör referansı | Bağımsız fiyat/performans endeksi | Kurumsal veri/analiz — **bizim en yakın rakibimiz** |
| 6 | **AK** (@_akhaliq) | büyük, teknik | Günlük makale küratörlüğü, yorum yok | Nakit değil: HuggingFace'e geçiş. Otonomiye en uygun format |
| 7 | **Simon Willison** (@simonw) | orta, çok yüksek itibar | "Denedim, gerçekte şu oldu" + blog | Danışmanlık, konuşmacılık. **Tezimize en yakın ses** |
| 8 | **Ethan Mollick** (@emollick) | ~1M+ | Akademik otorite | Kitap, konuşmacılık. Kopyalanamaz (unvan temelli) |
| 9 | **Görsel demo hesapları** (Min Choi tipi) | yüksek viral | "Şuna bak ne yapıyor" video/thread | Affiliate + kurs. Viral ama savunulamaz |
| 10 | **Prompt/dijital ürün satıcıları** (God of Prompt tipi) | küçük kitle yeter | Prompt paketi / şablon satışı | **Küçük kitleyle $2.000–10.000/ay.** Paket $15–49, pazar yeri %20–40 kesiyor |
| +1 | **İsimsiz otomatik bot** (derewah.dev vakası) | **80.000 takipçi** | Reddit içeriğini toplu çekip otomatik paylaşım + otomatik yanıt | Twitter Blue reklam payı. Niş değiştirip hesap çoğaltmış |

## Bu listeden çıkan 5 gerçek

### 1. Para X reklam payından gelmiyor — üç yerden geliyor
(a) **Sponsorluk** (hacim ister), (b) **ücretli katman / dijital ürün** ($99/ay, $150/yıl, $15–49 paket),
(c) **B2B değerlendirme & danışmanlık** (LMArena $30M). Listedeki 11 vakanın hiçbirinin ana geliri
reklam payı değil. Önceki hesabımız doğruydu: reklam payı rozet, gelir değil.

### 2. Küçük kitle yeterli — ama ürün gerekiyor
Ben's Bites 120K ile 1.75M'lik bülteni yeniyor. Prompt satıcıları **küçük kitleyle** ayda $2–10K yapıyor.
Yani 100.000 takipçi beklemek gereksiz; **satılacak bir şeyin olması** gerekiyor. Başabaş hedefimiz
(7 abone × €9) bu tabloda fazlasıyla gerçekçi.

### 3. Büyüme motoru yanıt — ve onu otomatikleştiremeyiz
Küçük hesaplar için en etkili taktik, zamanın **%70–80'i** kendi postları değil başkalarının altına
yazılan nitelikli yanıtlar: günde 10–20 yanıt → 30 günde 500–2.000 takipçi; 50K'ya 8–12 ay.
**Ama X otomasyon kuralı otomatik yanıtı/etiketlemeyi yasaklıyor** (`.claude/skills/sosyal-medya/SKILL.md`:
"hesap kapanır"). Araştırmanın kendisi de aynı şeyi söylüyor: tam otonom yanıt itibar riski, insan onayı şart.

**Bu, "mümkün olduğunca otonom" hedefiyle doğrudan çatışan tek bulgu ve en önemlisi.**

### 4. 2023 arazi kapma penceresi kapandı
Rowan Cheung 1.000 → 500.000'e **2023'te** çıktı. Aynı küratörlük bugün aynı sonucu vermiyor;
listedeki büyük küratörler pencereyi yakalamış olanlar. Bugün işe yarayan: dar niş + tekrarlanabilir
format + ölçülebilir iddia. Genel "AI haberleri" hesabı açmak 2026'da ölü doğum.

### 5. Tek "yüzsüz" kazanan kategori: ölçüm
Listedeki her başarı ya bir **insan yüzüne** (1,2,3,7,8,9) ya **yatırımlı şirkete** (4,5) dayanıyor.
Tek istisna 6 (makale küratörlüğü — nakit üretmedi) ve +1 (telif açısından grinin içinde, kırılgan).
Ama 4 ve 5 şunu kanıtlıyor: **ölçüm/veri kategorisi yüz olmadan referans olabiliyor ve gerçekten para
kazanıyor** — insanlar sayıları alıntıladığı için dağıtım kendiliğinden oluyor.
Dezavantaj: tepede $1.7 milyar değerlemeli şirket var. O yüzden **onların ölçmediğini ölçmek şart.**

## Üç şeyden ikisi

Araştırmanın verdiği en net sonuç:

> **Tam otonom + hızlı büyüme + legal — üçü birden olmuyor.**

| Seçenek | Ne veriyor | Ne istiyor |
|---|---|---|
| **A. Otonom üretim + elle dağıtım** | Kanıtlanmış hızlı büyüme (30 günde 500–2.000 takipçi) | Günde **20–30 dk** elle yanıt, ilk 3–6 ay. Bot her şeyi üretir, yanıtları sen yazarsın |
| **B. Tam otonom "referans" modeli** | Sıfır günlük iş, linç riski yok, tamamen legal | **Yavaş**: dağıtım başkalarının bizi alıntılamasına bağlı. İlk 6 ay neredeyse sessiz. LMArena/Artificial Analysis yolu |
| **C. Tam otonom + hızlı** | — | Yalnızca kural ihlaliyle mümkün (otomatik yanıt/etiketleme) → **hesap kapanır.** Bu seçenek yok |

A ile B aynı kodu kullanıyor; fark yalnızca senin günde 20–30 dakika ayırıp ayırmaman.
Yani **sonradan A'dan B'ye ya da B'den A'ya geçmek serbest** — kod değişmiyor.

## Nişe etkisi

Araştırma 1. dosyadaki öneriyi (`marka/NIS_KARARI.md` — AI fiyat/performans karnesi) **değiştirmiyor,
iki yerde düzeltiyor:**

1. **Gelir sırası değişti.** Ücretli veri katmanı + danışmanlık öne geçti, sponsorluk arkaya düştü.
   Prompt satıcılarının "küçük kitleyle $2–10K" verisi, ücretli katmanı ay 9'dan **ay 5–6'ya** çekmeyi haklı kılıyor.
2. **Rakip netleşti.** Artificial Analysis ve LMArena aynı kategoride. Ayrışma noktamız artık tahmin değil
   zorunluluk: onlar *ham fiyat/hız* ve *tercih oylaması* ölçüyor; biz **"başarılı iş başına kuruş"**
   ölçeceğiz — gerçek, sıkıcı, makine-kontrol edilebilir ticari işlerde. Bu kutu boş.
