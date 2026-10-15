# Tiny Fixes kurulumu: sahibinin adımları

Bot hazır ve **kapalı** (`[flood] mod = "kapali"`): siz bu adımları bitirip modu açana dek hiçbir şey paylaşılmaz ve
hiçbir anahtar okunmaz. Arayüz adları zamanla değişebilir; takılırsanız ekran görüntüsünü Claude'a gönderin.
Aynı liste, işaretleyerek ilerleyebileceğiniz bir sayfa olarak da var (Claude oturumunda paylaşılan bağlantı).

Tahmini maliyet (USD/ay): X Premium ~8, X API ~8–12, Claude API ~15–25, Instagram API 0 → **~35–45** (sıkı mod ~25).
Pazartesi raporu sayaçlardan tahmini maliyeti yazar; ilk ayın sonunda gerçek faturalarla karşılaştırın.

## A. Başlamadan (5 dk)

1. **Adı onaylayın: Tiny Fixes.** Beğenmezseniz söyleyin; ad tek yerden değişir (`marka/TINY_FIXES.md`, görseller yeniden üretilir).
2. **Dalı ana dala alın.** Zamanlanmış işler yalnızca ana daldan çalışır. Claude'a "PR aç" deyin, o açar; siz GitHub'da
   **Merge**'e basarsınız. (Ana dala gelse de bot kapalı kalır.)
3. **Harcama sınırı koyun:** console.anthropic.com → Settings → Limits → aylık sınır (öneri $40). X Developer Console'da
   kredi/limit ekranına bakın. Böylece bir hata faturayı büyütemez.

## B. X hesabı (20 dk)

4. Kullanıcı adını deneyin (sırayla): `@tinyfixes`, `@tinyfixes_ai`, `@tinyfixesai`, `@gettinyfixes`, `@tinyfixesdaily`.
   Yeni hesap için ayrı e-posta gerekir; Gmail kullanıyorsanız adresinize `+tinyfixes` ekleyerek yeni adres gibi kullanabilirsiniz.
5. Profil: isim `Tiny Fixes`, fotoğraf `marka/tiny_fixes_logo.png`, başlık `marka/tiny_fixes_x_kapak.png`, biyografi
   `marka/TINY_FIXES.md` içinde. Web sitesi ve konum boş.
6. **Otomatik hesap etiketi:** Ayarlar → Hesabınız → Hesap bilgileri → **Otomasyon** → yöneten hesap olarak kendi kişisel
   hesabınızı seçin (X kuralı; etiket yoksa hesap kısıtlanabilir).
7. **Premium** (aylık ~$8): yanıtlarınız üstte görünür, uzun post ve ileride Original Content Rewards başvurusu için gerekli.
8. **Sabit post:** `marka/TINY_FIXES.md` içindeki metni `tiny_fixes_tanitim_1.jpg` görseliyle elle atın, profilde sabitleyin.
9. **Bota izin:** GitHub → Actions → **Kalkylerat Botu** → Run workflow → komut **`flood_yetki`**. Açılan issue'daki bağlantıyı
   **Tiny Fixes hesabıyla giriş yapılmış** tarayıcıda açın → **Authorize app** → dönülen adresin tamamını kopyalayın →
   aynı komutu yeniden çalıştırırken adresi **`ek`** alanına yapıştırın. "✅ ... izni tamam" issue'su gelmeli.

## C. Instagram hesabı (30–40 dk)

10. Yeni hesap açın (X ile aynı kullanıcı adı tercih edilir: `tinyfixes`, `tinyfixes.ai`, `tinyfixes_ai`).
11. Ayarlar → Hesap türü → **Profesyonel hesaba geç → Creator** (kişisel hesaba API ile paylaşılamaz). Kategori:
    "Education" ya da "Science & Technology". Facebook Sayfası bağlamanız gerekmez.
12. Profil: fotoğraf `tiny_fixes_logo.png`, isim `Tiny Fixes`, biyografi `TINY_FIXES.md` içinde. Bağlantı boş.
13. **İlk post (elle):** `tiny_fixes_tanitim_1..4.jpg` dört görseli tek carousel olarak, `TINY_FIXES.md` içindeki caption ile.
14. (İsteğe bağlı) Öne çıkanlar: bir hikâye paylaşın → "Öne çıkanlara ekle" → kapak olarak `tiny_fixes_one_cikan_*.png`.
15. **Meta uygulaması:** developers.facebook.com → My Apps → **Create app** → kullanım durumu "Instagram API" (Instagram
    ile içerik ve mesaj yönetimi) → **API setup with Instagram login** → Instagram hesabını ekleyin (kendi hesabınız olduğu
    ve uygulamada rolünüz olduğu için App Review gerekmez). İzinler:
    - `instagram_business_basic` (hesap bilgisi)
    - `instagram_business_content_publish` (carousel yayını)
    - `instagram_business_manage_comments` (yorum kiti: yorumları **okumak** için; bot cevap yazmaz)
    - `instagram_business_manage_insights` (24 saat sonraki erişim/kaydetme/gönderme ölçümü)
16. Aynı ekrandan **access token** üretin (uzun ömürlü) ve **Instagram hesap kimliğini** (Instagram user ID) kopyalayın.
17. GitHub → depo **Settings → Secrets and variables → Actions → New repository secret**: `IG_FLOOD_TOKEN` (anahtar) ve
    `IG_FLOOD_ID` (kimlik).
18. Actions → komut **`flood_ig`**: bot hesabı doğrular ve anahtarı şifreli kaydeder ("✅ Instagram bağlantısı tamam" issue'su).
    Bundan sonra anahtarı bot 30 günde bir yeniler; gizli anahtarlara bir daha dokunmazsınız.

## D. Açılış (10 dk + ilk hafta)

19. Actions → komut **`flood_tani`**: kaynaklar ve puanlama gerçek veriyle denenir (Claude/X/Instagram'a dokunmaz, ücretsiz).
    Gelen "🩹 Tiny Fixes tanı" issue'sunu Claude'a gösterin; ❌ olan kaynağı birlikte düzeltiriz. (Depo herkese açık:
    15 Ekim'de doğrulandı, Instagram görselleri bu yüzden çalışır.)
20. `ayarlar.toml` → `[flood]` → `mod = "onay"` (ya da Claude'a "Tiny Fixes'i onay modunda aç" deyin).
21. **İlk hafta:** taslaklar `flood-onay` etiketli issue olarak telefona gelir (günde en fazla 2 trend + 1 evergreen).
    Cevap: `ok` (kanca A), `ok 2` (kanca B), `iptal`. 3 saat içinde cevap yoksa taslak düşer. Beğenmediğiniz bir şeyi
    Claude'a yazın, kuralı birlikte düzeltelim.
22. Bir hafta sonra kalite iyiyse `mod = "otomatik"`: yalnızca evergreen kendiliğinden çıkar, trend yine sizin `ok`'unuzla (F6).

## E. Günlük rutin (20–30 dk)

- Taslak onayları (`flood-onay`), 1–2 dk.
- **İlk saatte gelen yorumlar:** "💬 Yorumlar" (X) ve "💬 Instagram yorumları" issue'larında her yoruma 2 hazır cevap var;
  📋 ile kopyalayıp elle gönderin. Bot hiçbir zaman kendisi cevap atmaz.
- Büyük yapay zekâ hesaplarının postlarına günde 10–15 **anlamlı, bilgi veren** yanıt (elle). İlk ayın en etkili büyüme işi.
- Pazartesi: "🩹 Tiny Fixes haftalık rapor" issue'su (yayınlar, görüntülenme, kaydetme, tahmini maliyet, öğrenilenler).

## F. Takvim

- **1. ayın sonu:** Anthropic ve X faturalarını rapordaki tahminle karşılaştırın; Claude'a söyleyin, sabitleri güncelleriz.
- **~500 takipçi:** ücretsiz bülten (profil bağlantısı) ve yalnızca denenmiş araçlar için "affiliate" ibareli bağlantı (F4).
- **Original Content Rewards:** Premium + 500 doğrulanmış takipçi + 90 günde 500 bin doğrulanmış görüntülenme. Başvurmadan
  önce X'in Creator Monetization Standards sayfasından otomatik hesapların uygun olup olmadığını teyit edin.

## Neyi izleyeceksiniz

- `alarm` etiketli issue'lar: paylaşım durdu, denetimden geçmedi, 30 saat sessizlik, bir adım hata verdi.
- `data/flood.json`: taslaklar, durumlar, ölçümler ve kalıcı `gecmis` (öğrenme verisi).
