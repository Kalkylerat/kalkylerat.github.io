# Niş kararı — AI nişine geçiş önerisi

Tarih: 3 Ekim 2026. Durum: **karar bekliyor** (sahibinde).

## 0. Neden şimdi

Hesap 4 günlük. `data/direktor.json`: en iyi post 65–87 gösterim, yabancıdan sıfır beğeni/yorum.
Yani **pivotun maliyeti sıfır** — kaybedilecek takipçi, bozulacak itibar, silinecek rekor yok.
Bir ay sonra aynı karar pahalı olur.

Bahis nişinin çözülmeyen üç sorunu:
- **Türkiye 7258.** `marka/TURKCE_HESAP_PLANI.md` iki aydır "ceza avukatı onayı" şartına kilitli.
- **İsveç.** Spelinspektionen lisansı olmayan içerik/affiliate pazarlaması riskli; affiliate 3. aya ertelenmiş,
  yani bugüne kadar gelir kalemi fiilen yok.
- **X.** Kumar içeriği reklam payı ve sponsorluk tarafında sürekli daraltılan bir kategori.

Üçü de nişin kendisinden geliyor; daha iyi kod yazmak çözmüyor.

## 1. Öneri: aynı motor, yeni konu — AI'nın fiyat/performans karnesi

**Kalkylerat = İsveççe "hesaplanmış".** Markanın tezi hiçbir zaman futbol değildi: *fiyat doğru mu?*
Futbol oranı yerine **token fiyatı** koyduğumuzda marka, ses tonu ve kodun %80'i aynı kalıyor.

Her gün aynı **gerçek işler** bütün sınır modellere (Claude, GPT, Gemini, Llama…) veriliyor;
hesap şunu yayınlıyor:

```
GÖREV #212 — 40 sayfalık PDF sözleşmeden 9 alan çıkar
  model A  9/9 doğru   $0.011   7.2 sn
  model B  8/9 doğru   $0.004   3.1 sn   ← işi 2.7x ucuza yapıyor
  model C  9/9 doğru   $0.098   19.4 sn  ← 9x pahalı, aynı sonuç
30 günlük ortalama: başarılı iş başına en ucuz = model B ($0.0051)
```

Ertesi gün aynı görev, aynı yöntem, aynı tabloya bir satır daha. Hiçbir satır silinmiyor.

### Neden "değişik bir yaklaşım"
AI Twitter'ın %95'i hype ve "şu 10 prompt'u kullan". Ölçüm yapan azınlık ise ya
tercih oylaması (LMArena) ya ham hız/fiyat (Artificial Analysis) ölçüyor.
**Hiç kimse günlük olarak "başarılı iş başına kaç kuruş" yayınlamıyor.**
Boşluk tam burada: sıkıcı, gerçek, ticari işler + kuruş maliyeti + kamuya açık karne.

### Neden kopyalanamaz
Bugün başlayan biri bizim 12 aylık zaman serimizi üretemez — geçmişe dönük ölçüm yapılamaz.
Tek varlığımız **tarih damgalı, değiştirilemez ölçüm arşivi**. Bu, bahis botunun "şeffaf rekor"
kozunun birebir aynısı; sadece artık satılabilir bir veri kümesi.

### Etkileşim neden gelir
Model karşılaştırması AI alanının en çok yanıt alan konusu. Yanıtlar beğeniden ~15x ağır
(`.claude/skills/sosyal-medya/SKILL.md`). "Pahalı model aynı işi 9x fiyata yaptı" tipi tek satır,
taraftarı olan her modelin kullanıcısını yoruma çeker — hem de kavga etmeden, çünkü elimizde sayı var.

## 2. Gelir / gider

### Aylık gider
| Kalem | Tutar | Not |
|---|---|---|
| X API — paylaşım | $2.70 | 6 post/gün × 30, post başı $0.015. **Linkli post $0.20 (13x) — posta link konmaz** |
| X API — okuma | ~$5 | kendi metriklerimiz, ~1000 okuma × $0.005 |
| X Premium | $8 | reklam payının ön şartı + erişim |
| Anthropic (direktör, denetçi, puanlayıcı) | ~$25 | Sonnet 5.5 $2/$10, haftalık strateji Opus 5.5 $4/$20 per MTok |
| Test edilen modeller (OpenAI + Google + diğer) | ~$20 | günde 1 görev × 4 model küçük başlar |
| GitHub Actions + Pages | $0 | public repo |
| **Toplam** | **~$61 / ay** | ≈ €56 ≈ 620 SEK |

**İptal edilen:** API-Football Pro ($19) + Odds API. Yani **pivot aylık faturayı artırmıyor, hatta düşürüyor.**

### Gelir — dürüst takvim
| Dönem | Beklenti | Gerekçe |
|---|---|---|
| Ay 1–3 | **€0** | X reklam payı şartı: 500 takipçi + 3 ayda 5M gösterim. Yeni hesap için ulaşılmaz. |
| Ay 4–6 | €0–150 | ilk affiliate / ilk sponsorlu post |
| Ay 7–12 | €200–900 | ücretli veri katmanı 30–80 abone × €9 + ara sıra sponsor |
| Her an | €1500–3000 (tek seferlik) | **asıl kırılma:** "bizim iş yükümüz için de yapar mısın" danışmanlığı, Flow Event üzerinden faturalanır |

**X reklam payı bu nişte para değildir, rozettir.** Oran milyon *doğrulanmış* gösterim başına $8–12,
ve yalnızca Premium kullanıcıların ana akışındaki görüntülemeler sayılıyor. 10.000 takipçili bir niş hesap
ayda ~€10–40 görür. Buna gelir diye bakmayacağız.

### Başabaş noktası
Giderler ~€56/ay. **Ücretli katmanda 7 abone × €9 = €63.** Hedef bu; 5M gösterim değil.

### Ücretli katman ne satıyor
- **Bedava:** günün kartı, aylık lider tablosu, yöntem dokümanı. (Erişim motoru bu.)
- **€9/ay:** görev bazında tam sonuçlar (CSV/JSON), geçmiş zaman serisi, haftalık derin rapor ve
  **"senin iş yükün için en ucuz model" hesaplayıcısı**. Alıcı: her ay model faturası ödeyen geliştirici/CTO.
- Tahsilat: Stripe + kendi sayfamız (X Subscriptions değil — platform kesintisi ve kontrol kaybı).
  *Açık konu:* AB içi dijital hizmet satışında moms/OSS yükümlülüğü — `flow-event-finans` becerisiyle ayrıca bakılacak.

## 3. Hukuki durum

Bahis nişiyle kıyas: **7258 yok, Spelinspektionen yok, 18+ yok, avukat kilidi yok.**
Yerine gelen dört sıradan yükümlülük:

1. **Sponsorlu/affiliate içerik etiketlenir.** Marknadsföringslagen açık reklam işaretlemesi istiyor; X'in
   paid-partnership bildirimi de kullanılır. Link posta değil, bio/sabit tweet/siteye konur (hem ücret hem erişim).
2. **AB AI Act madde 50.** Yapay zekâ üretimi metin için şeffaflık yükümlülükleri **2 Ağustos 2026'dan beri
   yürürlükte** (makine-okunur işaretleme için 2 Aralık 2026'ya kadar geçiş süresi var). Hesap İsveç'ten
   yönetildiği için kapsamda. Bizim için maliyet değil avantaj: "bu hesabı bir AI yazıyor, ölçümler burada"
   zaten markanın kendisi. Profilde + sabit tweette açık beyan, X otomasyon etiketi açık.
3. **Karşılaştırmalı iddia objektif ve doğrulanabilir olmalı** (AB yanıltıcı/karşılaştırmalı reklam rejimi).
   Panzehir: yöntem kamuya açık, ham çıktı arşivde, "en iyi" demiyoruz — ölçtüğümüz sayıyı söylüyoruz.
4. **Sağlayıcı sözleşmeleri.** Lansmandan önce OpenAI / Google / Anthropic kullanım şartları
   karşılaştırmalı sonuç yayınlama açısından tek tek okunacak. Araştırmada OpenAI tarafında yasak bir madde
   görünmedi, Google tarafında geçmişte "benchmark için izin" tipi ifadeler olmuştu — **bu, lansman öncesi
   kapatılacak tek açık hukuki iş.** Mitigasyon kolay: kendi ölçümümüzü yayınlıyoruz, model çıktısını
   toplu yeniden yayınlamıyoruz, sayı ve yöntem veriyoruz.

### Çıkar çatışması — ürünün kalbi
Ürün bağımsız ölçümse, ölçtüğümüz model şirketinden para alamayız. Kural:
**sınır model sağlayıcılarından sponsorluk/affiliate alınmaz.** Sponsor ancak nötr taraftan
(hosting, gözlemleme/observability, IDE, veri aracı) alınır. Bu kural kodda değil ama dosyada sabit durur.

## 4. Otonomi

Bot (günlük, insansız):
- görev havuzundan günün işini seçer → 4+ modele gönderir → cevapları **otomatik puanlar**
  (çıktı makine-kontrol edilebilir görevler seçilir: alan çıkarma, SQL, sınıflandırma, JSON şema uyumu —
  "hangi deneme daha güzel yazmış" gibi öznel iş yok)
- maliyet ve süreyi ölçer → kartı üretir → denetçiden geçirir → X'e atar
- panele satırı ekler → aylık lider tablosunu günceller
- Pazartesi etkileşim sayılarına bakıp haftanın stratejisini ve Türkçe raporu çıkarır

Sana kalan (günde 10–15 dk, ilk 2 ay):
- ilk saatte gelen yorumlara cevap (otomatik yanıt X kuralı gereği **yasak**, hesap kapatır)
- görev havuzuna ara sıra gerçek bir iş eklemek — en değerli katkın bu, çünkü "gerçek iş" iddiası
  havuzun gerçekliğine dayanıyor
- sponsor/danışmanlık DM'lerine cevap

## 5. Mevcut koddan ne kalır

Toplam 6.188 satır Python.

**Kalır (~5.000 satır, dokunulmaz):** `tweets.py` X istemcisi/uzunluk/etiket mantığı, `denetci.py` (kural
denetimi), `direktor.py` (metin + haftalık strateji), `gorsel.py` (kart üretimi, font, palet), `panel.py` +
`docs/` (kamuya açık panel), `onay.py` (paylaşım öncesi onay), `kayit.py` (değiştirilemez arşiv),
`editor.py`, `temizlik.py`, `etkilesim.py` iskeleti, `config.py`, `.github/workflows/kalkylerat.yml`
zamanlama ve komut yapısı.

**Atılır (~1.200 satır):** `football.py`, `oddsapi.py`, `model.py` (Poisson), `analiz.py`, `bilgi.py`.

**Yeni yazılır (~600–800 satır):** `gorev.py` (görev havuzu + çalıştırıcı), `puanla.py` (otomatik
değerlendirme), `fiyat.py` (token→kuruş maliyet tablosu), karşılaştırma kartı, yeni bilgi konuları.

Gerçekçi süre: **2–3 oturum.** Sıfırdan başlamak 3–4 hafta sürerdi.

**Tek hesap, İngilizce.** AI alıcı kitlesi ve ödeme gücü global; Türkçe AI kitlesi küçük ve €
ödemiyor. `marka/TURKCE_HESAP_PLANI.md` kapanır — avukat kilidi de onunla birlikte.

## 6. 90 gün

| Hafta | İş | Ölçüt |
|---|---|---|
| 1 | sağlayıcı şartları okunur, görev havuzu v1 (10 gerçek iş), puanlayıcı, fiyat tablosu | ilk kart demo'da çıkıyor |
| 2 | profil/marka güncellemesi, panel yeniden yazılır, AI Act beyanı, taslak modda yayın | her gün 1 kart, insan onaylı |
| 3–4 | otomatik yayına geçiş, günlük 3 post ritmi (kart + karşılaştırma + soru) | yabancıdan ilk yorum |
| 5–8 | haftalık derin rapor, görev havuzu 30 işe çıkar | 500 takipçi, ilk tekrar eden okuyucu |
| 9–12 | ücretli katman v1 (Stripe + CSV + hesaplayıcı) | **7 ödeyen abone = başabaş** |

İlk gerçek sinyal: hafta 4'te yabancıların yorumu. Gelmezse niş değil, biçim değişir (video/liste).
12 haftada 500 takipçi + 0 ödeyen abone gelirse niş yanlıştır; o noktada durur, yeniden bakarız.

## 7. Elenen alternatifler

| Niş | Neden hayır |
|---|---|
| **AI hype fact-check** — viral iddiayı test et, sonucu yayınla | En viral seçenek, ama sürekli belirli hesapları yanlışlamak üzerine kurulu: linç dinamiği, X otomasyon kuralları (@ ve otomatik yanıt yasak) ve iddia akışını beslemek için pahalı X okuma ($0.005/okuma). **Ana nişin içinde haftalık bir rubrik olarak kullanılabilir** — hesabın bütünü olarak hayır. |
| **Dikey B2B** — İsveç küçük işletmesi için AI | Para en net (Flow Event ile doğal uyum), rekabet en az; ama kitle küçük ve X'te büyümez — LinkedIn işi. Danışmanlık geliri ana nişten zaten geliyor. |
| **AI haber/özet akışı** | Otonomi mükemmel, ayırt edicilik sıfır: yüzlerce bot aynı şeyi yapıyor, ölçülebilir iddia yok, satılacak veri yok. |
| **Prompt/araç tavsiyesi** | Kanıtlanamaz iddia üzerine kurulu — markanın tezinin tam tersi. |

## 8. Karar noktaları (sahibinde)

1. **Pivot onayı:** AI fiyat/performans karnesi — evet/hayır.
2. **İsim:** `Kalkylerat` korunur mu? (Tez aynı kaldığı için koruma yönünde öneri; `marka/TURKCE_HESAP_PLANI.md`
   içindeki "Kalibre" önerisi futbol içindi ve artık geçersiz.) Hesap @Kalkylerat ise profil metni + kapak değişir.
3. **Ek API anahtarları:** OpenAI ve Google (Gemini) anahtarı gerekiyor — ölçülecek modeller onlar.
   10$ kredi her biri için aylarca yeter.
4. **Ücretli katman:** 9. haftada mı açılsın, yoksa önce 1000 takipçi mi beklenir?

> **Düzeltme (3 Ekim 2026):** bu dosyadaki X reklam payı eşikleri artık geçerli değil — program yeni hesaplara kapandı. Bkz. `marka/KEYIF_VE_YUK.md` bölüm 0.
