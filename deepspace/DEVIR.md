# Deep Space Log: devir notu (10 Kasım 2026, bulut oturumundan yerel terminale)

Bu dosya yeni bir Claude Code oturumunun (yerel terminal) kaldığımız yerden devam etmesi için. Önce bunu, sonra
`SOZLESME.md` G bölümünü ve `.claude/skills/deep-space-log/SKILL.md`'yi oku. Sahibiyle Türkçe konuş.

## Güncel durum (11 Kasım 2026): iş bölümü, Shorts departmanı, YouTube uzmanı
Bu bölüm aşağıdaki eski notların üstündedir; çelişirse bu geçerlidir.
- **İş bölümü (G15):** 002'den itibaren her istasyonu bir ajan yapar (`.claude/agents/`, 11 ajan), kararı sıfır
  bağlamlı `denetci` verir (`gorev denetim`), komutlar kilitlidir (`gorev durum`, `gorev kilit`). `hepsi` yalnız 001.
  Akış ve şefin döngüsü: deep-space-log skill'i. Tasarım `docs/superpowers/specs/2026-11-11-is-bolumu-design.md`,
  plan `docs/superpowers/plans/2026-11-11-is-bolumu.md`.
- **Marka kiti (G16):** sahibi 11 Kasım'da onayladı. Renk A (film tonu yok, `[filtre] secim = ""`; eski bal_kehribar
  notu geçersiz), yazı Space Mono, kaynak `deepspace/marka/kaynak/A2.png`, kit `deepspace/marka/` (`gorev kanal`).
  Görsel dili: karanlık ufuk + tek dev gök cismi (`stil_eki`); 001 eski Dünya benzeri dilde kalır (`stil_eki_001`).
- **Hareket:** varsayılan Seyir Defteri (`[video] mod = "defter"`): görüntü bükülmez, yalnız fiziksel ışık katmanları
  (işaret lambası, pencereler, kutup ışığı, halka pırıltısı, bulutsu tülü, uydu ...), en az 3 katman, biri müzikle.
  4K 2 saatlik video ≈ 5 saat kare (3 süreç).
- **Shorts (G12):** `shorts-analiz` → shorts-kurgucusu `shorts_plan.json` → `shorts` (dikey Seyir Defteri);
  uzun videodan +1/+3/+5 gün sonra planlı.
- **YouTube uzmanı (G17):** araştırma istasyonu ve haftalık analiz, vidIQ aylık 100 kredi tavanı (kanca
  `deepspace/vidiq_butce.py`). Araştırmanın başlığı G5'ten geçerse pakete girer (`baslik_kaynagi`).
- **Açık:** marka istasyonunun denetçi kararı ve sahibin onay kaydı (`gorev marka --onay --kim sahip`); 001 kapağı
  için sahibinin seçtiği B3 (`marka/taslak/kapak_001.jpg`) ile `kapaklar`ın ürettiği arasında fark; Suno dosyaları
  (şu an yalnız `Small Signal.wav`); kanal adı/handle (`@deepspacelogmusic`) ve Google OAuth sahibinde.

## Kurulum (Windows, bir kez): masaüstü klasörü
Sahibine `DeepSpaceLog_kur.ps1` gönderildi (10 Kasım). Ne yapar: `Masaüstü\DeepSpaceLog\` açar, depoyu
`depo\` altına klonlar (`claude/deep-space-log` dalı), paketleri kurar, görev klasörlerine kısayol (junction)
koyar ve 20 görseli indirir. Düzen:
```
Masaüstü\DeepSpaceLog\
  depo\                         # kod (git)
  001-trappist\  -> depo\deepspace\gorevler\001-trappist
      gorsel\   NN.png         # 20 görsel (depoya girmez)
      ses\      NN-ad.wav/mp3  # Suno dosyaları buraya (SUNO.md'deki adlarla)
      cikti\    video, kapak, shorts, rapor
      denetim\  NN.json        # G13 kararları (depoda)
```
Elle: `winget install Git.Git Python.Python.3.12 Gyan.FFmpeg`, sonra
`git clone -b claude/deep-space-log https://github.com/kalkylerat/kalkylerat.github.io.git depo`,
`py -m pip install -r requirements.txt -r deepspace/requirements.txt`, `py -m pytest -q`.

Görsel linkleri imzalı ve 10 Kasım ~14:00 (İsveç saati) sonra geçersiz. Sonra indirmek için: ElevenLabs bağlantısıyla
`creative_get_generations` (akış `wXHon9u5lPX0oECJcwqN`, kimlikler `gorev.toml`'da `gorsel_uretim`), dönen
`full_res_url`'yi `gorsel/NN.png`'ye indir. Aynı dosya inerse `denetim/NN.json` kararları geçerli kalır (özet eşleşir).

## Terminalde başlatma
```powershell
cd $env:USERPROFILE\Desktop\DeepSpaceLog\depo   # (OneDrive masaüstüyse betiğin yazdığı yol)
claude --teleport session_01SQC21TK4HUr2srKHyASQZw --model claude-opus-5-5 --effort high   # bulut konuşmasının devamı
claude --model claude-opus-5-5 --effort high                                               # ya da temiz oturum + bu dosya
claude -c --model claude-opus-5-5 --effort high                                            # sonraki günler: son yerel konuşma
```

## Nerede kaldık
- **Kanal**: Köz (`@kozruh`, UCtJHvFs1UuIKwTUhcWVyWIg, 7 abone, video yok) → "Deep Space Log". Sahibi adı/handle'ı
  Studio'da değiştirecek; metinler `deepspace/kanal.md`.
- **Hat** (`deepspace/`): ses → sahne/canlı tablo → 4K video → 3 kapak → metin → 3 Shorts → kapılar (`rapor.json`).
  Bulutta uçtan uca denendi (34/34 kapı yeşil). Komutlar: `py -m deepspace.gorev hepsi deepspace/gorevler/001-trappist`.
- **Görev 001 TRAPPIST-1e**: 20 parça, ~124 dk (sahibi: "20 şarkı, 2 saat"). İstemler `gorevler/001-trappist/SUNO.md`;
  **sahibi Suno'da üretiyor**, dosyaları SUNO.md'deki adlarla `ses/` klasörüne (ya da Drive `DeepSpaceLog/001/`) koyacak.
- **Film tonu (marka)**: `marka.toml [filtre]` = `bal_kehribar`, güç 0.55 ("2 ama biraz daha hafif"). Kırmızı-turuncu
  tonlar ve hafif tonlar reddedildi; sarımsı istendi. Ton `renk.py` ile tek LUT'tan video, kapak, Shorts, banner'a.
- **Görsel konsepti (9 Kasım, sahibinin YouTube referanslarıyla)**: tanıdık, Dünya'ya benzeyen sakin manzara
  (tarla, dağ, göl, yol, deniz feneri) + gökyüzünü kaplayan imkânsız büyüklükte gerçek gök cismi + ön planda küçük
  hikâye unsuru (astronot, tren, kulübe, araba). Stil cümlesi `marka.toml [gorsel] stil_eki`. Referanslar ElevenLabs
  akışı `G9Slu7mLp7MkDCxTUyPp` (FLUX 3). Rengi model değil LUT verir. Kodla çizilen gezegenler reddedildi.
- **ElevenLabs ücretsiz planı**: günlük görsel sınırı var (9 Kasım'da 5 görselde doldu). 20 görsel için ücretli
  plan ya da birkaç gün gerekir; sahibine sor.
- **Örnek kurgu**: Hubble Derin Alan (NASA, telifsiz) + canlı tablo + ton + kart/etiket; sahibine gönderildi.

## Hareket (9 Kasım)
Sahibi gerçek hareket istiyor ("direkt motion"). Hat hazır: `gorsel/NN.mp4` (yapay zekâ klibi, ~10 sn, başlangıç =
bitiş karesi) varsa `klip.py` dikişsiz döngüye çevirir, 4K'ya ölçekler, tonu uygular; yoksa görselden canlı tablo.
Klip üretimi: ElevenLabs'te video **ücretli plan ister** (ücretsiz planda kapalı); vidIQ'da 105 kredi var, video
saniyesi ≥20 kredi (yetmez). Seçenekler: ElevenLabs ücretli plan (Kling 4 / Seedance 2.5 / Veo 3.1 Fast, başlangıç ve
bitiş karesi aynı görsel), ya da sahibinin Kling/Runway sitesinden elle üretip `gorsel/` klasörüne koyması.
Hareket istemi: `marka.toml [hareket] istem_eki` + sahneye özel hareket (dalga, sis, buğday, fener ışığı).

## 3D fotoğraf efekti (9 Kasım, ücretsiz yol; sahibi "2'yi deneyelim")
`tablo.Tablo3D` + `derinlik.py`: Depth Anything V2 Small (ONNX, Apache-2.0, GitHub'dan ~100 MB, `deepspace/.model/`)
derinlik çıkarır; yakın/uzak katmanlar farklı hızda kayar, uzakta sis süzülür. Görsel varsa ve paketler kuruluysa
otomatik devreye girer (`py -m pip install -r deepspace/requirements.txt`). Derinlik `gorsel/NN_derinlik.png`'ye
önbelleklenir, elle düzeltilebilir. Örnek video sahibine gönderildi (referans ekran görüntüsündeki iki sahne).

## Sinemagraf (9 Kasım, sahibinin asıl istediği: "resim gibi, ama bazı yerler hareket etsin")
`canli.Sinemagraf`: kamera sabit; `gorsel/NN_hareket.json` tarifindeki bölgeler hareket eder (akis: bulut/sis/su,
salinim: ağaç/ot, dalga: buğday/çimen, parilti: ışıklar, kar, yildiz, donme: yalnız tam yüzey haritasıyla, G14).
Sahibinin geri bildirimleri: 1) "hareket görmedim" → belirgin olmalı; 2) "mantık yok, tren bulanıklaşıp geri geliyor"
→ yalnızca gerçekte hareket eden şey hareket eder, ince ve zarif; katı nesneler "haric" ile korunur, araçta yalnız ışık
titrer; 3) toz çok yoğundu → az; 4) gezegen biraz daha hızlı dönsün (~2.2–2.6°/sn). Taban değerler `ornek_hareket/` (3. sürüm). Bölge = normalize kutu + renk/parlaklık/
derinlik koşulu. Örnek tarifler `deepspace/ornek_hareket/`. Her görsel için tarifi ajan yazar: görseli ızgarayla
inceler (0.1'lik çizgiler), bölgeleri seçer, kısa bir deneme karesiyle kontrol eder (parlak gezegen kenarını
parilti kutusuna alma: dalgalı desen yapar). Örnek video sahibine gönderildi; ücretsiz.

## Small Signal referans videosu ve G14 (10 Kasım, yerel Windows)
- Sahibinin tepkisi: "en büyük gezegen dönmüyor, üzerindeki katman çoğalıp birleşiyor; şarkı duymuyorum".
- **Gezegen sorunu:** eski `donme`, iki kaydırılmış kopyayı karıştırıyordu ve bu hayalet yapıyordu. Tek kopyalı
  dönme de denendi: arka yüz olmadığından kenar geriliyor ya da aynalı leke çıkıyor. Yeni kural (SOZLESME G14):
  gezegen yalnız tam yüzey haritasıyla (`doku`) ve diski kadrajdaysa döner; değilse sabit kalır. Kod bunu zorlar.
- **Ses sorunu:** ses `small_signal_1080p.mp4` içinde vardı (-16,7 dB ortalama). Aynı klasörde sessiz
  `dongu_1080p.mp4` de duruyordu; sahibi büyük olasılıkla onu açtı. Artık ara dosyalar `ornek/ara/` içinde, ses
  `kapilar.ses_duyuluyor` ile ölçülüyor. Uzun video ve Shorts kapısı da sesin duyulduğunu ölçüyor.
- Komut: `py -m deepspace.gorev ornek deepspace/gorevler/001-trappist --parca 16 --ses "deepspace/gorevler/001-trappist/ses/Small Signal.wav"`

## Bölüm ses paleti ve görsel istemleri (10 Kasım)
- Sahibinin fikri: her bölümün tutarlı bir enstrüman paleti, sonraki bölümde uzay teması korunarak değişen palet
  (skill'de "Bölüm ses paleti"). İlk deneme paleti "Yalnız Gezegen" (2 parça: PSO J318.5-22, Gale Crater), sahibi
  Suno'da üretti, "çok güzel" dedi. Uygun görürse 002 bu paletle kurulur.
- 001'in 20 görseli üretildi (10 Kasım, FLUX 3, **2K**, görsel başı 1.454 kredi, toplam ~29.080; 4K 4.654 kredi
  olduğu için seçilmedi). ElevenLabs akışı `wXHon9u5lPX0oECJcwqN`; her parçada `gorsel_oturum` + `gorsel_uretim`.
  İndirme (yerel): `creative_get_flow_run_status(akış, oturumlar)` → `content_url` → `gorsel/NN.png`.
  Sahibi Creator (~22 $/ay, 121.000 kredi) aldı.

## G8 değişti (10 Kasım 2026, sahibinin onayıyla): sahibi izleyici
Bütün seçimleri sistem yapar, kararı denetçi ajan verir. Yayın gizli + planlı, karardan en az 24 saat sonra; sahibine
bilgi gider, onay beklenmez; `iptal` her zaman önceliklidir (`py -m deepspace.gorev iptal <klasör>`). Sahibinde kalan
tek iş Suno üretimi (resmî API yok). Sahibi ElevenLabs Creator (~22 $) alıyor: görseller için ticari lisans.

## Görseller hazır ve denetlendi (10 Kasım)
Sahibi ElevenLabs Creator aldı; 20 görsel FLUX 3 2K (2736x1536) üretildi, bulut ağı açıldı, indirildi
(`deepspace/gorevler/001-trappist/gorsel/`, depoya girmez; yeniden indirmek için `gorev.toml`'daki
`gorsel_oturum/gorsel_uretim` kimlikleriyle `creative_get_generations`). G13 denetimi: 18 görsel ilk seferde geçti,
02 (ikiz balıkçı) ve 13 (8 tekerlekli gezici) istem düzeltilip birer kez yeniden üretildi, ikisi de geçti. Ayrıntı
`deepspace/gorevler/001-trappist/GORSEL_DENETIM.md`.

## Sıradaki işler (10 Kasım listesi; 001 için geçerli, 002'den itibaren skill'deki istasyon döngüsü)
1. Görseller tamam (yukarı bak). Her görsel için sinemagraf tarifi `gorsel/NN_hareket.json` (örnekler
   `deepspace/ornek_hareket/`); yeni görsel gelirse önce G13 denetimi (`py -m deepspace.gorev denetle`).
2. İsteğe bağlı ön plan: `NN_on.png` (şeffaf; ElevenLabs "Image Background Removal" ile pencere/oda ayrılırsa
   iki katmanlı derinlik).
3. Banner ve profil resmini yeni görsel diliyle yeniden üret (`py -m deepspace.gorev kanal`; şu anki kod sahnesinden).
4. Müzik gelince: `py -m deepspace.gorev hepsi <klasör>`. 4K, 2 saatte ~1,5–2 saat kodlama (dizüstünde daha uzun
   olabilir; hızlı deneme için görevde `[ayar.video] genislik = 1920, yukseklik = 1080`). Kırmızı kapı = video yok.
5. Denetçi alt ajan karar verir → `onay --yayin <en az 24 sa sonra>` → sahibine bilgi (önizleme, kapak, başlık).
6. Yükleme: Google kurulumu yapılmadıysa (`deepspace/KURULUM.md`) sahibi Studio'dan elle yükler; `youtube.json`'daki
   başlık/açıklama/etiket, reklam araları (`reklam_noktalari`), 3 kapak (Test & Compare), sentetik içerik işareti.
   Yayından sonra `py -m deepspace.gorev kaydet <klasör> --youtube-id ...` ve commit.

## Denenmemiş / bilinen eksikler
- `google.py` (Drive al/teslim, YouTube yükleme) sahte cevaplarla test edildi, gerçek hesapla hiç çalışmadı.
  YouTube API'si denetimsiz projelerin yüklemelerini gizliye kilitler; denetim başvurusu sahibinde.
- Kapak düzeni kod sahnesiyle denendi; gerçek görselle yeniden bakılmalı (yazı okunurluğu, PROBE-7 yeri).
- Suno Pro indirme sınırı ayda 20 (kaynaklardan, doğrulanmadı): 20 parça bir ayı doldurur.
- Bulutta oluşturulan `kalkylerat.github.io` ortamı (NASA/ESA/Solar System Scope hostları) yerelde gereksiz.

## Yeni oturuma ilk mesaj (teleport kullanılmazsa)
> Deep Space Log'a devam ediyoruz. deepspace/DEVIR.md, SOZLESME.md G bölümü ve deep-space-log skill'ini oku,
> `py -m pytest -q` ve `py -m deepspace.gorev denetle deepspace/gorevler/001-trappist` çalıştır, durumu 5 satırda
> özetle. Sonra: Suno WAV'ları `ses/` klasörüne geldiyse Small Signal ile örnek video, değilse sinemagraf tarifleri.
