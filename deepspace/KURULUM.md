# Deep Space Log: Google kurulumu (bir kez, ~20 dk)

Amaç: sistem Drive'daki ses ve görsel dosyalarını kendisi alsın, bitmiş videoyu Drive'a koysun, ileride YouTube'a
kendisi (gizli/planlı) yüklesin. Hepsi ücretsiz. Anahtarları **sohbete asla yapıştırma**; yalnızca 6. adımdaki
ortam ayarına girilir.

## 1. Google Cloud projesi
1. https://console.cloud.google.com → üstte proje seçici → **New project** → ad: `Deep Space Log` → Create.
2. Sol menü **APIs & Services → Library**: `YouTube Data API v3` → Enable; `Google Drive API` → Enable.

## 2. İzin ekranı
1. **Google Auth Platform → Branding**: uygulama adı `Deep Space Log`, destek e-postası kendi adresin → Save.
2. **Audience**: User type **External**. Ardından **Publish app** ile durumu **In production** yap.
   (Testing'de kalırsa anahtar 7 günde bir geçersiz olur.) "Doğrulanmamış uygulama" uyarısı normaldir, uygulamayı
   yalnızca sen kullanacaksın.

## 3. İstemci (client)
1. **Clients → Create client** → Application type **Web application**, ad `dsl`.
2. **Authorized redirect URIs** → `https://developers.google.com/oauthplayground` ekle → Create.
3. Çıkan **Client ID** ve **Client secret**'ı bir kenara not et (sohbete değil).

## 4. Yenileme anahtarı (refresh token)
1. https://developers.google.com/oauthplayground → sağ üstte dişli → **Use your own OAuth credentials** işaretle →
   Client ID ve secret'ı yapıştır.
2. Soldaki kutuya şu üç kapsamı boşlukla yaz → **Authorize APIs**:
   `https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/drive`
3. Köz/Deep Space Log kanalının bağlı olduğu Google hesabıyla gir (kanal bir marka hesabıysa listeden **kanalı** seç).
   Uyarıda **Advanced → Go to Deep Space Log** → izin ver.
4. **Exchange authorization code for tokens** → çıkan **Refresh token**'ı not et.

## 5. YouTube yükleme denetimi (beklerken manuel yükleme)
YouTube, 2020'den sonra açılmış ve denetimden geçmemiş projelerden API ile yüklenen videoları **gizli kalmaya
kilitler**. Bu yüzden:
- Şimdilik: sistem videoyu Drive'a koyar (`teslim`), sen YouTube Studio'dan yüklersin; başlık, açıklama, etiket,
  reklam araları ve kapaklar hazır gelir.
- Paralelde: "YouTube API Services Audit and Quota Extension Form" ile denetim başvurusu (kullanım: kendi kanalına
  kendi videolarını yüklemek). Onay gelince `yukle` komutu tam otomatik çalışır.

## 6. Ortama girme
claude.ai'de oturum başlığındaki ortam menüsü → **kalkylerat.github.io** ortamı → **Edit**:
- **Allowed hosts**'a ekle: `oauth2.googleapis.com`, `www.googleapis.com`
- **Environment variables**'a ekle: `DSL_GOOGLE_CLIENT_ID`, `DSL_GOOGLE_CLIENT_SECRET`, `DSL_GOOGLE_REFRESH_TOKEN`
  (değerler 3. ve 4. adımdan).
Sonraki oturumu bu ortamda başlat. Bana yalnızca "Google kurulumu tamam" yaz.

## Drive klasör düzeni
```
DeepSpaceLog/
  001/
    01-proxima-b.mp3 ... 16-3c-273.mp3   (SUNO.md'deki adlarla)
    gorsel/01.png ... 16.png             (varsa; NN_on.png = şeffaf ön plan)
    cikti/                               (sistem doldurur: video, 3 kapak, 3 Shorts, açıklama)
```
