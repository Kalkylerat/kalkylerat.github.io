---
name: suno-muzik
description: Kullanıcının Suno hesabında, Claude in Chrome ile şarkı üretir, indirir ve bilgisayarda proje/tarih/başlık klasörlerine düzenler. "Şarkı yap", "Suno'da üret", "şu tarzda 3 şarkı", "istekler dosyasındaki şarkıları üret", "şarkılarımı listele" gibi isteklerde kullan.
---

# Suno şarkı üretici

Kullanıcının kendi Suno aboneliğiyle, kendi Chrome'unda (Claude in Chrome, `mcp__claude-in-chrome__*` araçları) şarkı üretirsin, indirirsin ve `duzenle.py` ile klasörlere yerleştirirsin. Kullanıcıyla Türkçe konuş.

Bu skill'in klasöründe `duzenle.py` ve `istekler-ornek.toml` var. Betiği her zaman bu klasördeki tam yoluyla çağır (`python <skill-klasoru>/duzenle.py ...`; Windows'ta `python` yoksa `py`).

## 0. Hazırlık

1. Chrome'u kullanmadan önce `chrome-browser` skill'ini oku ve araçları yükle.
2. İsteği netleştir. Her şarkı için gerekenler:
   - **baslik** (yoksa sen öner)
   - **stil**: tür, tempo, enstrümanlar, vokal tipi, duygu (ör. `dark synthwave, 100 bpm, female breathy vocals, melancholic`). Suno'nun stil alanı İngilizce anahtar kelimelerle daha iyi çalışır; kullanıcı Türkçe tarif ederse sen İngilizceye çevir.
   - **sozler** veya **tarif**: kullanıcı söz verirse aynen kullan. Söz yerine konu verirse sözleri sen yaz, `[Verse]`, `[Chorus]`, `[Bridge]`, `[Outro]` gibi bölüm etiketleriyle. Kullanıcı dil belirtmediyse Türkçe yaz ve bunu özetinde söyle.
   - **enstrumantal**: evet/hayır
   - **proje**: klasör adı (yoksa `Genel`)
   - **adet**: kaç kez üretilecek (her üretim Suno'da 2 varyasyon verir)
3. Kullanıcı "istekler dosyası" derse, verdiği `.toml` dosyasını oku (biçim: `istekler-ornek.toml`). Dosyadaki her `[[sarki]]` bir istektir.
4. Birden fazla üretim varsa başlamadan önce kısa bir liste göster: kaç üretim, tahmini kredi (Suno'da genelde üretim başına 10 kredi; sayfadaki güncel bilgiyi esas al). Kullanıcı isteğinde sayıyı zaten açıkça verdiyse ayrıca onay bekleme.

## 1. Suno'yu aç ve girişi kontrol et

1. Yeni sekmede `https://suno.com/create` aç. Kullanıcının açık sekmelerine dokunma.
2. Sayfayı oku. Giriş yapılmamışsa **dur**: kullanıcıdan Chrome'da kendisinin giriş yapmasını iste. Şifre, e-posta kodu veya Google girişi yazma/tıklama; bunlar kullanıcının işi. Giriş yapınca devam et.
3. Kalan krediyi oku (kenar çubuğunda veya profil menüsünde görünür). Planlanan üretimler için yetmiyorsa kullanıcıya söyle, yeteni üret.

## 2. Her şarkı için üret

Suno'nun arayüzü sık değişir. Aşağıdaki adımlar yol haritasıdır; düğme adlarını sayfayı okuyarak bul, tahmin ederek tıklama.

1. **Custom** (Özel) modunu aç. Simple/açıklama modunu yalnızca kullanıcı "sen karar ver, sadece tarif" derse kullan.
2. **Lyrics** alanına sözleri yaz (enstrümantalse **Instrumental** anahtarını aç ve söz alanını boş bırak).
3. **Styles / Style of Music** alanına stili yaz. Kullanıcı "şunlar olmasın" dediyse varsa **Exclude styles** alanına yaz.
4. **Title** alanına başlığı yaz.
5. Kullanıcı model sürümü, persona veya gelişmiş ayar (weirdness, style influence vb.) belirttiyse onları ayarla; belirtmediyse varsayılanlara dokunma.
6. Alanların doğru dolduğunu sayfayı okuyarak doğrula, sonra **Create**'e bir kez tıkla.
7. Üretim 1–3 dakika sürer. Birkaç saniyede bir sayfayı yeniden okuyarak iki yeni parçanın süresinin göründüğünü / "generating" durumunun bittiğini bekle. Aynı anda birden fazla Create'e basma; bir üretim bitmeden sonrakine geçme.
8. Hata, "moderation", "credits" veya captcha çıkarsa dur ve kullanıcıya olduğu gibi bildir. Captcha'yı sen çözme.

## 3. İndir ve düzenle

1. İndirmeden **hemen önce**: `python <skill-klasoru>/duzenle.py isaret`
2. Yeni üretilen iki parçanın her biri için `...` (More) menüsü → **Download** → **MP3 Audio** (kullanıcı WAV istediyse ve planı destekliyorsa **WAV Audio**). Chrome bir onay penceresi açarsa kullanıcıya söyle.
3. Şarkının sayfa linkini al (parçaya tıklayınca açılan `suno.com/song/...` adresi); iki varyasyon varsa ikisini de not al.
4. Sözleri geçici bir dosyaya yaz (ör. skill klasörü dışında bir temp dosyası) ve taşı:

   ```
   python <skill-klasoru>/duzenle.py tasi --proje "<proje>" --baslik "<baslik>" --stil "<stil>" --mod "<vokal|enstrümantal>" --link "<link1> <link2>" --sozler-dosyasi "<sozler.txt>"
   ```

   Betik İndirilenler klasöründe işaretten sonra inen ses dosyalarını `<kok>/<proje>/<YYYY-MM-DD>_<baslik>/` klasörüne taşır, yanına `bilgi.json` ve `sozler.txt` koyar, `<kok>/katalog.csv`'ye bir satır ekler ve işareti yeniler.
5. Betik "yeni ses dosyası bulunamadı" derse: indirmenin gerçekten başladığını kontrol et; kullanıcının Chrome indirme klasörü farklıysa `--indirilenler "<klasör>"` ekle.

Varsayılan ana klasör `~/Music/Suno`. Kullanıcı başka yer isterse her çağrıya `--kok "<klasör>"` ekle (veya kullanıcıya `SUNO_KLASOR` ortam değişkenini ayarlamasını öner). `--kok` ve `--indirilenler` alt komuttan **önce** yazılır: `duzenle.py --kok "D:\Muzik" tasi ...`

## 4. Bitiş

Kısa bir özet ver: hangi şarkılar üretildi, klasör yolları, harcanan/kalan kredi, sorun çıkanlar. "Şarkılarımı listele" denirse `python <skill-klasoru>/duzenle.py liste` çalıştır.

## Kurallar

- Yalnızca kullanıcının istediği kadar üret; krediyi boşa harcama. Beğenmediği bir sonucu yeniden üretmek için kullanıcının onayını al.
- Hesap ayarlarına, abonelik/ödeme sayfalarına, yayınlama/paylaşma (Publish, public yapma) düğmelerine dokunma; kullanıcı açıkça isterse yap.
- Şarkıyı "public" yapma, başkasıyla paylaşma; varsayılan gizlilik ayarını değiştirme.
- Başka sanatçıların telifli sözlerini birebir yazma; "X tarzında" isteğini stil kelimelerine çevir (sanatçı adı Suno'da genelde reddedilir).
- Seri üretimde insan hızında çalış: üretimler arasında sonucu bekle, arka arkaya düğmeye basma.
