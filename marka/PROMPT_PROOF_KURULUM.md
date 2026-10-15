# Prompt Proof kurulumu (sizin yapacaklarınız)

Bot hazır ve **kapalı** (`[flood] mod = "kapali"`): siz bu adımları bitirip modu açana dek hiçbir şey paylaşılmaz.
Aşağıdaki arayüz adları zamanla değişebilir; takılırsanız ekran görüntüsünü gönderin.

Tahmini maliyet (USD/ay): X Premium ~$8, X API ~$8–12, Claude API ~$15–25, Instagram API $0. Toplam ~$35–45.
Rakamlar üçüncü taraf kaynaklara ve token tahminine dayanır; ilk ayın sonunda gerçek faturalarla karşılaştırın.

## 1. X hesabı

1. Yeni bir X hesabı açın (kullanıcı adı denemeleri için `PROMPT_PROOF.md`). Profil fotoğrafı: `marka/prompt_proof_logo.png`,
   başlık: `marka/prompt_proof_kapak.png`, biyografi ve sabit post: `PROMPT_PROOF.md`.
2. **Ayarlar → Hesabınız → Otomatik hesap (Automated)** ile hesabı kendi insan hesabınıza bağlayın (X kuralı).
3. **Premium** aboneliği alın (erişim artışı ve ileride Original Content Rewards başvurusu için).
4. GitHub → Actions → **Kalkylerat Botu → Run workflow → komut `flood_yetki`**. Bot bir issue açar: bağlantıyı
   **Prompt Proof hesabıyla giriş yapmış** tarayıcıda açın, **Authorize app**'e basın, dönülen adresin tamamını
   kopyalayın. Aynı komutu yeniden çalıştırırken adresi `ek` alanına yapıştırın. Anahtar depoda şifreli saklanır.
   (Yanlışlıkla Kalkylerat ya da Mr. Likely hesabıyla yetki verirseniz bot kaydetmez.)

## 2. Instagram hesabı

1. Yeni bir Instagram hesabı açın, **Profesyonel hesaba** geçin (**Creator** ya da **Business**; kişisel hesaba API ile
   paylaşılamaz). Fotoğraf ve biyografi: `PROMPT_PROOF.md`. Profil bağlantısını başlangıçta boş bırakın.
2. developers.facebook.com'da bir uygulama oluşturun, **Instagram** ürününü ekleyin, **"API setup with Instagram login"**
   yolunu seçin (Facebook Sayfası gerekmez). Instagram hesabını uygulamaya ekleyin ve **içerik yayınlama** iznini verin
   (izin adı Meta'nın iki sayfasında farklı yazılmış: `instagram_business_content_publish` / `..._publishing`; arayüzde
   hangisi görünüyorsa onu seçin). Yalnızca kendi hesabınıza paylaşacağımız için App Review gerekmez.
3. Uzun ömürlü erişim anahtarını (access token) ve Instagram hesap kimliğini üretin.
4. GitHub → Settings → Secrets and variables → Actions: `IG_FLOOD_TOKEN` ve `IG_FLOOD_ID` ekleyin.
5. Actions → **komut `flood_ig`**: bot hesabı doğrular (adı ve türü issue'ya yazar) ve anahtarı şifreli kaydeder.
   Bundan sonra anahtarı bot 30 günde bir yeniler; gizli anahtarlara bir daha dokunmanız gerekmez.

## 3. Depo herkese açık mı?

Instagram, görselleri `raw.githubusercontent.com/<depo>/flood-medya/...` adresinden çeker. Bu yalnızca **herkese açık
depoda** çalışır. Bot adres erişilebilir değilse Instagram'a hiçbir şey göndermez ve nöbet özetine yazar. Depo özelse
bana söyleyin, görselleri ayrı bir herkese açık depoda barındıracak biçimde değiştiririm.

## 4. Açmak

1. `ayarlar.toml` → `[flood]` → `mod = "onay"`. İlk gün birkaç taslak, `flood-onay` etiketli issue olarak gelir
   (telefona bildirim). Cevap: `ok` (kanca A), `ok 2` (kanca B), `iptal`. 3 saat içinde cevap gelmezse taslak düşer.
2. İlk hafta yalnızca onay modunda çalıştırın, taslakların kalitesine bakın. Beğenirseniz `mod = "otomatik"`:
   o zaman yalnızca evergreen (Library) kendiliğinden çıkar, trend içerik yine sizin onayınızla (F6).
3. İlk 8 hafta gelir hedefi yok: tek hedef takipçi ve doğrulanmış kitle. Günde 20–30 dakika: onaylar, ilk saatte
   gelen yorumlara elle cevap (bot 3 taslak hazırlar, **"💬 Yorumlar" issue'sunda**), büyük yapay zekâ hesaplarının
   postlarına günde 10–15 anlamlı yanıt (elle; otomatikleştirilemez).

## 5. Neyi izleyeceksiniz

- Alarm issue'ları (`alarm` etiketi): paylaşım durdu, denetimden geçmedi, 30 saat sessizlik.
- X Developer Console ve Anthropic konsolu: ilk ayın gerçek maliyeti.
- `data/flood.json`: taslaklar, durumlar, 24 saat sonra ölçümler (görüntülenme, kaydetme, gönderme).
- Konu kaynağı RSS adresleri `ayarlar.toml → [flood] rss` içinde; çökeni bot atlar ve özete yazar. Bu ortamdan
  doğrulayamadım, ilk çalışmada hangilerinin yanıt verdiğine birlikte bakarız.
