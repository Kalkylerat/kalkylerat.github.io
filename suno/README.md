# Suno şarkı üretici (Claude Code + Chrome)

Siz ne istediğinizi yazarsınız; Claude kendi bilgisayarınızdaki Chrome'da Suno hesabınızı açar, ayarları yapar, şarkıyı üretir, indirir ve klasörlere düzenler.

```
Siz:    "Suno'da 2 tane hüzünlü Türkçe akustik şarkı yap, konu: memleket özlemi, proje: Gurbet"
Claude: sözleri yazar → suno.com/create → Custom mod → söz, stil, başlık → Create
        → biter → MP3'leri indirir → ~/Music/Suno/Gurbet/2026-09-30_Memleket/
```

Her şarkı klasöründe: MP3 dosyaları (Suno'nun iki varyasyonu), `sozler.txt`, `bilgi.json` (stil, link, tarih). Ana klasörde tüm şarkıların listesi: `katalog.csv` (Excel'de açılır).

## Gerekenler

- Bilgisayarınızda **Claude Code** (terminal)
- Chrome'da **Claude in Chrome** eklentisi, Claude Code'a bağlı
- **Python 3** (python.org; Windows'ta kurarken "Add to PATH" kutusunu işaretleyin)
- Chrome'da Suno hesabınızla **giriş yapmış** olmanız

## Kurulum (bir kerelik, 5 dk)

1. Bu klasörü bilgisayarınıza indirin (GitHub'da bu branch → **Code → Download ZIP**, açın).
2. Terminalde açtığınız klasöre girip çalıştırın:
   ```
   python suno/kur.py
   ```
   (Windows'ta `python` çalışmazsa `py suno/kur.py`.) Bu, skill'i `~/.claude/skills/suno-muzik` altına kopyalar; artık Claude Code'u hangi klasörde açarsanız açın çalışır.
3. Claude Code'u Chrome bağlantısıyla başlatın: `claude --chrome` (veya açıkken `/chrome` yazıp bağlantıyı açın).
4. Chrome'da suno.com'a kendiniz giriş yapın. Şifrenizi Claude'a vermeyin; gerek de yok.

## Kullanım

Tek şarkı:
```
Suno'da enerjik bir Türkçe rock şarkısı üret, konu: sabah koşusu, erkek vokal, proje: Spor
```

Kendi sözlerinizle:
```
Şu sözlerle Suno'da şarkı yap, stil: slow R&B, female vocals, 75 bpm, başlık "Son Mektup": ...
```

Toplu (vaktiniz yoksa en pratiği): `suno/suno-muzik/istekler-ornek.toml` dosyasını kopyalayın, istediğiniz kadar şarkı yazın, sonra:
```
Masaüstündeki istekler.toml dosyasındaki şarkıları Suno'da üret
```

Liste:
```
Suno şarkılarımı listele
```

Kendi klasör yapınızla:
```
Suno'da 3 lofi şarkı üret, klasör yapısı: Tür/Yıl-Ay/Şarkı adı
```
Yapı söylemezseniz varsayılan: `Proje/Tarih_Başlık`.

Ayarlar:
- Farklı kayıt klasörü: "şarkıları D:\Muzik\Suno klasörüne kaydet" deyin ya da `SUNO_KLASOR` ortam değişkenini ayarlayın.
- Chrome başka bir klasöre indiriyorsa: `SUNO_INDIRILENLER` ortam değişkeni.
- WAV, model sürümü, persona, "şunlar olmasın" (exclude styles): isteğinizde söylemeniz yeterli.

## Bilmeniz gerekenler

- **Kredi:** Her üretim Suno kredinizden düşer (genelde 10 kredi, 2 varyasyon). Claude toplu işten önce toplam krediyi söyler; yeniden üretimi size sormadan yapmaz.
- **Arayüz değişirse:** Claude sayfayı okuyarak çalışır, sabit düğme konumlarına bağlı değildir; yine de Suno büyük bir değişiklik yaparsa takılabilir. Takılırsa ne gördüğünü söyler.
- **Hesap riski:** Suno'nun kullanım şartları otomatik araçlarla erişimi kısıtlıyor olabilir. Claude insan hızında, tek tek üretir, ama yine de günde yüzlerce üretim gibi yoğun kullanımdan kaçının.
- **Bilgisayar açık olmalı:** Claude sizin Chrome'unuzu kullandığı için üretim sırasında bilgisayar ve Chrome açık kalmalı. Başlatıp başka işe geçebilirsiniz.
- Claude giriş, captcha, ödeme ve "Publish/Public" işlemlerini yapmaz; bunlar sizde kalır.

## Elle deneme (Claude olmadan)

```
python suno/suno-muzik/duzenle.py isaret
# Suno'dan bir şarkı indirin
python suno/suno-muzik/duzenle.py tasi --proje Deneme --baslik "İlk Şarkı" --stil "acoustic pop"
python suno/suno-muzik/duzenle.py liste
```
