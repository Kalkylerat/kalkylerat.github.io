# Kalkylerat — otomatik İsveççe futbol "değer" oyunları botu

Bot her gün maçları tarar, keskin piyasanın (Pinnacle) adil olasılığına göre **kazanma ihtimali en yüksek** 0–3 tekli (singel) oyunu seçer ve İsveç lisanslı bahisçideki oranla birlikte, Claude'un yazdığı İsveççe gerekçelerle X'te paylaşır. Maçlar bitince sonuçları yazar ve herkese açık rekor panelini günceller.

- Görseller ve profil metinleri: **[marka/](marka/)** (`PROFIL.md` içinde kopyala-yapıştır metinler)

## Günlük akış (siz uyurken çalışır)

```
10:00  dünkü sonuçlar → sonuç tweetleri → bugünün maçları → tüm bahisçilerin oranları
       → adil olasılık (Pinnacle) ≥ %65 ve oran adil fiyattan en fazla %5 kötü → Poisson gol modeli kontrolü
       → Claude en yüksek ihtimalli 0–3 oyunu seçer, İsveççe gerekçe yazar → taslak veya doğrudan X paylaşımı
23:30  akşam maçlarının sonuçları → sonuç tweeti → rekor paneli güncellenir
```

Yeterince yüksek ihtimalli oyun yoksa o gün paylaşım yapılmaz. Bu bilinçli bir tercih: az ama sağlam oyun.

## Kurulum (bir kerelik, ~45 dakika)

### 1. X hesabını açın (5 dk)
1. Yeni bir e-posta ile yeni bir X hesabı açın (kişisel hesabınızdan ayrı).
2. `marka/PROFIL.md` dosyasındaki isim, kullanıcı adı ve biyografiyi girin. `marka/logo.png` profil fotoğrafı, `marka/kapak.png` kapak görseli olacak.
3. Otomasyon etiketini açın (adımlar `PROFIL.md` içinde).
4. İsteğe bağlı ama önerilir: X Premium (erişimi ciddi artırır).

> **Şifrenizi kimseyle, bana da, paylaşmayın.** Bot hesabınıza şifreyle değil, sizin ürettiğiniz ve istediğiniz an iptal edebileceğiniz API anahtarlarıyla erişir. Anahtarları sohbete yapıştırmayın; doğrudan GitHub'a (2. adım) girin.

### 2. X geliştirici anahtarları (10 dk)
1. **Yeni hesapla** giriş yapmışken developer.x.com → Developer Portal'a girin ve kaydolun.
2. Bir **Project** ve içinde bir **App** oluşturun.
3. Billing / Credits bölümünden kredi yükleyin: 10$ aylarca yeter (gönderi başı ~0,015$).
4. App → **User authentication settings → Set up**:
   - App permissions: **Read and write**
   - Type of App: **Web App, Automated App or Bot**
   - Callback URI ve Website URL: `https://github.com` (zorunlu alan, kullanılmıyor)
5. App → **Keys and tokens**:
   - "API Key and Secret" → **Regenerate** → iki değeri kopyalayın.
   - "Access Token and Secret" → **Generate** → iki değeri kopyalayın. İzni değiştirdikten **sonra** üretilmiş olmalı; alt yazıda "Read and Write" görünmeli.

### 3. Diğer iki anahtar (10 dk)
| Servis | Nereden | Not |
|---|---|---|
| API-Football | dashboard.api-football.com → kayıt → API key | Ücretsiz planla başlayın |
| Anthropic | platform.claude.com → Billing: 10$ kredi → API Keys → Create | Aylık ~5–10$ harcar |

### 4. Anahtarları GitHub'a girin (5 dk)
Depo sayfası → **Settings → Secrets and variables → Actions → New repository secret**. Şu 6 ismi birebir kullanın:

| İsim | Değer |
|---|---|
| `X_API_KEY` | API Key |
| `X_API_SECRET` | API Key Secret |
| `X_ACCESS_TOKEN` | Access Token |
| `X_ACCESS_SECRET` | Access Token Secret |
| `API_FOOTBALL_KEY` | API-Football anahtarı |
| `ANTHROPIC_API_KEY` | Anthropic anahtarı |

### 5. GitHub ayarları: isminiz görünmeyecek şekilde (10 dk)
Panel adresinde kişisel kullanıcı adınız görünmesin diye depo ücretsiz bir **organizasyona** taşınır:
1. github.com/organizations/plan → **Free** → organizasyon adı: `kalkylerat` (alınmışsa `kalkylerat-se`) → e-posta: X için açtığınız e-posta.
2. Organizasyon → **People** → kendi satırınızda **Public → Private**. Böylece organizasyon sayfasında görünmezsiniz.
3. Bu depo → **Settings → General** → en altta **Transfer ownership** → `kalkylerat`.
4. Taşınan depoda **Settings → General → Repository name** → `kalkylerat.github.io` → Rename. (Organizasyon adı farklıysa: `<organizasyon-adı>.github.io`.)
5. **Settings → Actions → General → Workflow permissions → Read and write permissions** → Save.
6. **Settings → Pages → Source: Deploy from a branch → Branch: `claude/twitter-football-predictions-ywwfxw`, klasör: `/docs`** → Save. Birkaç dakika sonra panel `https://kalkylerat.github.io/` adresinde açılır; X profilindeki "Web sitesi" alanına ve sabit tweete bu adresi koyun.
7. 4. adımdaki 6 anahtarı taşıma **sonrasında** bu depoya ekleyin (daha önce eklediyseniz Settings → Secrets altında durduklarını kontrol edin).
8. **Actions** sekmesi → "Kalkylerat Botu" → **Run workflow → komut: `tahmin`** ile ilk denemeyi yapın. Özet sayfasında bugünün taslağını görmelisiniz.

## Günlük kullanım (telefondan 1 dakika)

İlk 1–2 hafta **taslak modu** açık; bot hazırlar ama siz onaylamadan paylaşmaz:

1. 10:00'dan sonra GitHub uygulaması → Actions → Kalkylerat Botu → son çalışma → özet sayfasında taslağı okuyun.
2. Beğendiyseniz: **Run workflow → `yayinla`**. Beğenmediyseniz hiçbir şey yapmayın; yayınlanmayan taslak rekora girmez.
3. Sonuç tweetleri ve panel otomatik güncellenir.

Kaliteden emin olunca `ayarlar.toml` dosyasında `otomatik_paylas = true` yapın (GitHub'da dosya → kalem ikonu → değiştir → Commit). Bundan sonra size iş kalmaz.

**Değişmez kurallar:** ilk maç başladıktan sonra oyun yayınlanmaz, yayınlanan hiçbir oyun silinmez. Bu şeffaflık hesabın en değerli varlığı.

## Sizin yapmanız gerekenler (büyüme için, günde 10–15 dk)
Bot içeriği üretir; takipçiyi etkileşim getirir:
- İsveççe futbol sohbetlerinde (Allsvenskan, Premier League) değerli yanıtlar yazın. Spam yapmayın, link atmayın.
- Hafta sonları gelen yorumlara cevap verin.
- Bahis sitesi linki/reklamı **yok**: ne İsveç ne Türkiye için. Affiliate konusu ancak 3. aydan sonra, yalnızca İsveç lisanslı şirketlerle ve kurallara uygun şekilde.

## Ayarlar (`ayarlar.toml`)

| Ayar | Anlamı |
|---|---|
| `izinli` | Taranacak ligler (Allsvenskan önde) |
| `max_spel` | Günlük en fazla oyun sayısı (3) |
| `min_olasilik` | En düşük kazanma ihtimali (0,65 = %65) |
| `oran_min` / `oran_max` | Oran aralığı (1,20–1,75) |
| `min_deger` | Oranın adil fiyattan en fazla ne kadar kötü olabileceği (-0,05 = %5) |
| `isvec_lisansli` | Oranı önerilecek bahisçiler. spelinspektionen.se'den lisansları kontrol edin |
| `otomatik_paylas` | `true` ise onay beklemeden paylaşır |

## Anahtarsız deneme
```bash
pip install -r requirements.txt
python -m bot demo      # örnek veriyle: oyunlar, tweetler, sonuç, panel
python -m pytest -q
```

## Sorun giderme
- **Özet: "Anahtarlar henüz eklenmemiş"** → 4. adım eksik.
- **"API-Football hatası … plan/season"** → Ücretsiz plan güncel sezonu vermiyorsa Pro'ya (19$) geçin.
- **"X API hatası 401/403"** → App izni "Read and write" değil ya da Access Token izin değişikliğinden önce üretilmiş. Tokeni yeniden üretip secret'ı güncelleyin.
- **"X API hatası 402"** → X geliştirici kredisi bitmiş olabilir.
- **"Bugün oyun yok"** → O gün yeterince yüksek ihtimalli oyun bulunamadı; bilinçli bir davranış.
