# Deep Space Log: bağımsız inceleme (11 Kasım 2026)

Yalnızca okudum; depoda hiçbir dosyayı değiştirmedim. Baktıklarım: SOZLESME.md G bölümü, `deepspace/` kodu ve ayarları, 001 görevi, marka kiti görselleri, iki skill, ajan dosyaları, testler (93 test yeşil), bu oturumun örnek kareleri. YouTube'un iki yardım sayfasını (yapay zekâ beyanı ve para kazanma politikası) bugün yeniden okudum; alıntılar oradan.

Not: inceleme sırasında başka bir oturum depoda çalışıyordu (G9, `metin.py`, `kanal.md` değişti). Aşağıdaki bulgular dosyaların son hâline göredir.

## 1. Özet

- Fikir doğru ve nişe göre ayırt edici: gerçek gök cisimleri, PROBE-7'nin kaydı, görev saati ve müziğe bağlı sinyal çizgisi. Rakiplerde bu yok. Örnek kare (HUD'lu TRAPPIST-1e) gerçekten şık duruyor.
- Ama proje şu an hedefe değil, kendi iç düzenine çalışıyor: 3 günde 11 ajan, 17 sözleşme maddesi, 93 test, kilit sistemi kuruldu; yayında video sayısı sıfır. Konsept 3 günde üç kez değişti ve depo son kararı yansıtmıyor.
- "Yarın düzgün başlatma" depodaki duruma göre mümkün değil: yeni konseptte 20 görselden 1'i, 20 şarkıdan 0'ı hazır. Gerçekçi ilk yayın 4–7 gün sonra.
- En büyük risk: YouTube'un para kazanma incelemesinde kanalın "şablonla seri üretilmiş yapay zekâ içeriği" ya da "anlatısız görsel slayt" sayılması. Bugünkü kapak şablonu (her videoda "DEEP FOCUS 2H") bu izlenimi kendi eliyle üretiyor.
- İkinci büyük risk: kararı yapay zekâ denetçinin verip videonun kendiliğinden yayına girmesi (G8). Bugüne kadar sahibinin baktığı her örnek geri döndü; denetçinin 8–9 puan verdiği 20 görselin tamamı çöpe gitti. Zevk kararı henüz sisteme devredilecek kadar oturmadı.
- En büyük fırsat: "LOG" fikrini kanalın her yüzeyine taşımak (kapak, banner, profil). Şu an kanal sayfası nişteki herkesin kullandığı "Samanyolu + gezegen kenarı" görüntüsü; ayırt edici olan HUD ise yalnız videonun içinde.
- Öneri: yarın kanal sayfasını ve 001'in üretimini başlat, ilk 3 videoda son sözü sahibi söylesin, Shorts'u ve ajan düzenini ilk 5 videoya kadar beklet.

## 2. Hatalar ve riskler (hedefe etkisine göre sıralı)

### 2.1 Para kazanma incelemesi: "seri üretim" izlenimi (en yüksek etki)

**Ne:** YouTube'un politikası para kazandırmayacağı içerikleri şöyle sayıyor: "Image slideshows ... with minimal or no narrative, commentary, or educational value" ve "AI-generated content made with generic or unoriginal templates giving the impression of mass production". İzin verilen: "Same intro and outro for your videos, but the bulk of your content is different".

**Neden önemli:** Kanal tam bu sınırda duruyor: durağan görsel + müzik + sabit bir çerçeve. İnceleyen kişi videoyu baştan sona izlemez; kanal sayfasına, kapaklara, başlıklara ve birkaç saniyeye bakar. İhlal kararı kanalın tamamına uygulanır.

**Kanıt:**
- `deepspace/kapak.py:26`: kapak yazısı her videoda seri adı + süre ("DEEP FOCUS" + "2H"). Aynı serinin bütün kapakları aynı iki kelimeyi taşıyacak. Kanal sayfasında yan yana dizilince tam "şablon" görüntüsü.
- `deepspace/kapak.py:38-43`: üç kapak varyantı aynı görselin hafif farklı yakınlaştırması. Test & Compare bundan bir şey öğrenemez.
- Kayıt kartı parça başına tek cümle ve ~20 saniye görünüyor (`defter.py:306-320`). 2 saatte toplam ~7 dakika "anlatı". Bu, skill'de "minimal narrative değildir" diye yazılmış ama dışarıdan bakan için zayıf bir savunma.

**Çözüm:**
1. Kapakta görevin kendi adı olsun ("SEVEN WORLDS"), seri adı küçük etiket olsun. Her kapak farklı bir dünya göstersin.
2. Açıklamadaki "Mission notes" bölümü zaten iyi bir eğitim katmanı; her videoda en üste 3–4 cümlelik, o göreve özel bir giriş yazısı ekleyin (şablon cümle değil).
3. Yükleme hızını düşük tutun (haftada en çok 1). Toplu yükleme yapmayın.
4. Açık söyleyeyim: bu önlemler riski azaltır, sıfırlamaz. Aynı formatta para kazanan çok kanal var, reddedilen de var. Kesin sonucu ancak başvuru gösterir.

### 2.2 Yapay zekâ beyanı: ne zorunlu, ne değil

YouTube'un sayfasından bugün okuduğum (kısa özetleyen bir araçla okudum; kelimesi kelimesine emin olmak için sayfayı bir kez kendiniz açın: support.google.com/youtube/answer/14328491):

- **Zorunlu:** Studio'daki "altered or synthetic content / AI use" işareti. Sayfa, müzik videonun ana konusuysa yapay zekâyla üretilmiş müziğin beyan edilmesi gerektiğini söylüyor. Tekrar tekrar beyan etmeyene YouTube etiketi kendisi koyabilir ve ceza verebilir: "removal of content or suspension from the YouTube Partner Program".
- **Zorunlu değil:** açıklamaya ya da kanal metnine "AI ile yapıldı" yazmak. Bu yalnızca sizin eski G9 kuralınızdı. Bugün yapılan değişiklik (metinlerden çıkarmak, işareti tutmak, "hand-made / no AI" gibi yalanları yasaklamak) YouTube kurallarına uygun ve bence doğru.
- **Beyan erişimi kısmaz:** "Disclosing AI content alone won't limit a video's audience or impact its eligibility to earn money."
- **Bilmeniz gereken:** sayfa, yapay zekâ müziğinde etiketin oynatıcının üstünde de görünebileceğini söylüyor ("a label in the video player may also appear"). Yani metinden silmek etiketi izleyiciden saklamaz. Strateji "gizlemek" olamaz; "emeği görünür kılmak" olmalı.
- **Emin olmadığım:** AB Yapay Zekâ Yasası'nın şeffaflık maddeleri sizi (İsveç'te bir yayıncı olarak) ayrıca bağlar mı. Bence platform etiketi pratikte yeterli, ama hukukçu değilim.

**Yeni metinde iki zayıf cümle var (`deepspace/metin.py:14-20`):**
- "Every fact in the mission log is checked against published sources." 001 için kaynak dosyası (`bilgi_kaynak.json`) yok; bilgi istasyonu 002'den başlıyor. Ayrıca iki uzaklık eski: Kepler-452b için "1,400 light-years" (Gaia ölçümüyle yaklaşık 1.800), Kepler-186f için "500 light-years" (yaklaşık 580). Bu rakamlardan %100 emin değilim; yayından önce NASA Exoplanet Archive'dan doğrulatın. Uzay meraklısı izleyici bunu yorumda yazar.
- "Visuals are artistic impressions based on real scientific data." Görseller bir görsel modelinin hayali; "veriye dayalı" demek fazla iddialı. Önerim: "Visuals are artist's impressions. The worlds are real."

### 2.3 Depo, kilitlenen konsepti yansıtmıyor

Konsept (karanlık yabancı ufuk, insan/araç yok, elektronik palet, durağan görsel, başlık "Seven Worlds | ...") yalnızca asistanın hafıza notunda duruyor. Depoda:

| Yer | Durum |
|---|---|
| `gorevler/001-trappist/gorev.toml` | 20 parçanın tamamı eski: org flüt/rüzgâr/gök gürültüsü paleti; görsel istemlerinde kulübe, balıkçı, astronom |
| `gorev.toml:10` (`ozet`) | "a two-hour route through **sixteen** real worlds" yazıyor; 20 parça var. Bu metin doğrudan YouTube açıklamasına giriyor (`metin.py`) |
| `deepspace/gorev.py:76` | 001 için eski "Dünya manzarası" stil ekini zorla kullanıyor (`stil_eki_001`). `gorseller` komutu çalışırsa yeni istemlere terk edilen stili ekler |
| `gorsel/` | 20 görselden 19'u eski konsept. 16 numara yeni |
| `ses/` | Yalnız `Small Signal.wav` |
| Başlık | `buyume/oneriler.json` yok; hat şablona düşer: "Deep Focus Space Ambient for Studying \| TRAPPIST-1e \| 2 Hours". Kararlaştırılan "Seven Worlds \| ..." başlığı hiçbir dosyada yok |
| Açıklama (`metin.py:60`) | "music for studying, coding, reading and deep work" diyor; başlık "Sleep & Deep Focus" diyecek. Uyku geçmiyor |
| `DEVIR.md` "Güncel durum" | Hâlâ "Yalnız Gezegen" paletini ve katmanlı hareketi anlatıyor |

**Neden önemli:** yeni bir oturum (ya da ajan) DEVIR.md'yi okuyup eski konseptle üretim yapar; para ve Suno indirme hakkı gider.
**Çözüm:** üretimden önce tek seferde: gorev.toml, SUNO.md, GORSEL.md, DEVIR.md, `oneriler.json`, `gorev.py:76`.

### 2.4 Sözleşme kendi konseptiyle çelişiyor

- **G13 teknik kapısı yeni görseli reddediyor.** `deepspace/gorsel_denetim.py:79`: karenin %40'ından fazlası simsiyahsa görsel kalır. Yeni konseptin tek görseli (16) bugün çalıştırdığımda: "KALDI: simsiyah alan fazla (%47)". "Karanlık, sade, derin siyah" konsepti bu kapıdan geçemez; rapor kırmızı kalır, video çıkmaz. Eşik konsepte göre yeniden ayarlanmalı (örneğin %65) ya da ölçü "yıldızsız düz siyah" olarak değişmeli.
- **Hareket kapısı durağan görseli yasaklıyor.** `deepspace/kapilar.py:218-243`: her görsele en az 3 hareket katmanı, biri müzikle. Karar "tamamen durağan görsel + yalnız HUD". 002'den itibaren bu istasyon geçilemez; ya da geçmek için anlamsız katman eklenir. G14'ün başlığı hâlâ "Sinemagraf hareketi".
- **G6** hâlâ "canlı tablo, kusursuz döngü" diyor; **G1** üç ayrı seri diyor, yeni başlık uyku ve odağı tek videoda birleştiriyor; **G7** "PROBE-7 kapakta görünür" diyor, kapaktaki uydu çizimi ise en zayıf marka öğesi (bkz. 3.2).
- **G11** "ücretli tek kalem Suno" diyor. Gerçekte ElevenLabs Creator (~22 $/ay) ve vidIQ da var.
- **G4** aynı sesin iki videoda kullanılmasını yasaklıyor. Bu, nişin en ucuz büyüme aracını (kendi parçalarınızdan 8–10 saatlik uyku derlemesi) kapatıyor. Kendi araştırmanız (arastirma.md §4) uykuda 8–10 saatin iyi gittiğini söylüyor.

**Çözüm:** sahibinin tek onayıyla G1, G4, G6, G7, G11, G13, G14'ü yeni konsepte göre sadeleştirin. Sıra: sözleşme, test, kod.

### 2.5 Kararı denetçinin vermesi (G8)

**Ne:** video, sahibi bir şey yapmazsa 24 saat sonra kendiliğinden yayına girer.
**Kanıt:** 3 günde sahibinin bütün örnek izlemeleri düzeltmeyle bitti: hayalet gezegen, ses duyulmadı, kart player'a denk geldi, kart aynı şeyi tekrar etti, şarkılar "fantastik film müziği gibi", görseller "Dünya manzarası". Bunların hepsi otomatik kapılardan ve yapay zekâ denetiminden geçmişti.
**Çözüm:** ilk 3–5 videoda sahibi 5 dakikalık bir kontrol yapsın (başından 1 dk, iki geçiş, kapak telefonda) ve açık "ok" versin. Zevk oturunca G8'e dönülür.
**Ek gerçek:** otomatik yükleme zaten çalışmıyor. `google.py` gerçek hesapla hiç denenmedi; YouTube, denetlenmemiş API projelerinin yüklemelerini gizliye kilitler. İlk videolar Studio'dan elle yüklenecek. Test & Compare de yalnız Studio'dan yapılır (`google.py:216` yalnız tek kapak yükler).

### 2.6 İzleyiciyi tutma (retention)

- **Parça geçişinde görsel sert kesiliyor.** `deepspace/video.py:157-162`: görüntü, ses geçişinin ortasında bir kareden diğerine kesiliyor; yumuşak geçiş yok. Uyku videosunda karanlık bir sahneden daha aydınlık bir sahneye ani geçiş, ekrana bakan ya da ekranı açık uyuyan kişiyi rahatsız eder. 3–4 saniyelik çapraz geçiş eklenmeli. (Emin olmadığım: bu oturumdaki denemelerde geçiş ayrıca eklenmiş olabilir; depodaki kodda yok.)
- **İlk saniyeler sessiz.** 001'in mevcut 20 isteminin hepsi "Intro: wind only, near silence" ile 40 saniye başlıyor. Skill'in kendi kuralı "müzik 3 saniyede açılır". Yeni palette ilk parça ilk 3–5 saniyede duyulur bir pad ile açılmalı; sessiz giriş yalnız ara parçalarda olabilir.
- **Uyku + odak aynı videoda.** Uyku dinleyicisi parlak, kıpırdayan bir sinyal çizgisi ve "telemetry blips / radio static" istemez; odak dinleyicisi umursamaz. İlk 3 videoda birlikte deneyin, sonra veriye göre ayırın. Küçük bir iyileştirme: HUD ilk dakikadan sonra %40'a kadar sönükleşsin.
- **Rota tutarsız.** PROBE-7 4 ışık yılından 2.300 ışık yılına, oradan Jüpiter'in uydusu Europa'ya, sonra 64 ışık yılına gidiyor; son durak 2,4 milyar ışık yılı. "Seven Worlds" başlıklı görevde TRAPPIST-1 yalnızca 20 duraktan biri. Gerçek uzay meraklısı bunu fark eder. Görevi başlığa uydurun: ya uzaklığa göre sıralı bir rota, ya da gerçekten TRAPPIST-1 çevresinde bir görev (yıldız + 7 gezegen + yol üstü komşular).

### 2.7 Hattaki kırılgan yerler (kodda gördüğüm)

- `deepspace/video.py:199-204`: 20 bölüm ~5 saatte kodlanıyor; son birleştirme adımı hata verirse `finally` bloğu 20 bölümün hepsini siliyor. 5 saatlik iş baştan. Ayrıca yarıda kesilirse kaldığı yerden devam yok (hazır bölüm atlanmıyor).
- `deepspace/kapilar.py:185-189` siyah ekran kontrolü ve `kapilar.py:83` sessizlik kontrolü, "karanlık görsel + uzun sessizlikli ambient" içerikte yanlış alarm verebilir. İlk gerçek videoda eşiklere bakılmalı.
- `deepspace/video.py:173-175`: görseli kalan parça "kod sahnesi"ne düşüyor. Sahibi kodla çizilen gezegenleri reddetmişti; bu yedek yol sessizce yayına girebilir. Eksik görsel = video yok olmalı.
- `gorev.toml`'da 001 için `bilgi_kaynak.json` yok (bkz. 2.2).
- vidIQ kancası (`.claude/settings.json`) `py` komutuna bağlı; yalnız Windows'ta çalışır.

### 2.8 Maliyet israfı

- **4K, 2K görselden büyütülüyor.** Görseller 2736 piksel genişliğinde; çıktı 3840. Gerçek ayrıntı eklenmiyor, 5 saatlik kodlama ve dev dosya yükleniyor. 2560x1440 yeterli: YouTube yine yüksek kaliteli kodlamayı verir, süre kabaca yarıya iner. (G6 "4K sahibinin isteği" diyor; sahibine "aynı görüntü, yarı süre" diye sorulmalı.)
- **001'in ilk 20 görseli (~29.000 ElevenLabs kredisi) ve vidIQ'nun aylık 100 kredisinin 50'si ilk günde gitti.** Konsept oturmadan toplu üretim yapıldı. Kural önerisi: yeni konseptte önce 3 görsel + 2 şarkı + 1 dakikalık örnek, sahibinin oku, sonra kalan 17.
- **Suno indirme sınırı** (notlara göre 18 Kasım'a kadar ~25 indirme): 20 parçalık bir video hakkın tamamını yer, yeniden üretime yer kalmaz. Banner'daki "NEW MISSION WEEKLY" ve açıklamadaki "A new mission every week" (`metin.py:66`, `marka_kiti.py:20`) bu sınırla tutulamayabilir. Söz vermeyin; yazıyı kaldırın.
- **Kullanılmayan kod:** sinemagraf, 3D derinlik modeli, klip döngüsü, film tonu, kod sahneleri, 3 seri şablonu. Yeni konseptte hiçbiri kullanılmıyor ama testleri ve bakım yükü duruyor.

## 3. İyileştirmeler

### 3.1 Öncelik sırası

| # | Ne | Emek | Beklenen etki |
|---|---|---|---|
| 1 | Depoyu konsepte eşitle (2.3) ve çelişen sözleşme maddelerini düzelt (2.4) | orta | Üretimin önündeki engel kalkar; yanlış üretim riski biter |
| 2 | Kapak sistemi: görev adı + görev numarası + gerçek koordinat (3.2) | orta | Tıklanma ve "şablon" izlenimi; en yüksek getiri |
| 3 | Kanal sayfası: profil, banner, açıklama (3.2) | küçük | "AI slop" hissi gider |
| 4 | İlk 3–5 videoda sahibin oku | küçük | Kötü videonun yayına girmesi engellenir |
| 5 | Parça geçişinde yumuşak görsel geçiş; ilk 5 saniyede duyulur müzik | küçük | İlk dakika terk oranı, uyku deneyimi |
| 6 | 1440p çıktı, bölüm silme hatası (`video.py:199-204`), kaldığı yerden devam | küçük | Üretim süresi yarıya, 5 saatlik kayıp riski biter |
| 7 | Rota ve başlık uyumu; iki uzaklık rakamının doğrulanması | küçük | Güvenilirlik; "gerçek veri" iddiasının arkası dolar |
| 8 | Shorts'u ilk 5 uzun videoya kadar beklet | sıfır | Emek asıl işe gider (gerekçe 5. bölümde) |
| 9 | 4 görevden sonra 8 saatlik uyku derlemesi (G4 değişikliğiyle) | orta | İzlenme saati; nişte en iyi çalışan uzunluk |

### 3.2 Kanal sayfasını ayırt edici yapmak

Bugünkü hâli (dosyalar: `deepspace/marka/banner.jpg`, `profil.png`, `marka_kitabi.jpg`): fotoğraf gibi bir Samanyolu, altında kehribar ışıklı gezegen kenarı, üstünde ince aralıklı yazı. Bu, nişteki en çok izlenen kanalların (ve onları taklit eden yüzlerce kanalın) ortak görüntüsü. Üstüne konan PROBE-7 ise düz renkli bir "uydu simgesi": mavi paneller, sarı kutu. Foto-gerçekçi zeminde hazır ikon gibi duruyor. "AI slop" hissi bu ikisinin birleşiminden geliyor.

İlke: **güzel uzay resmi herkeste var; sizde olan "kayıt defteri".** Markayı resimden değil, defterin dilinden kurun: ince çizgiler, köşe işaretleri, görev numaraları, gerçek koordinatlar.

- **Profil resmi (küçük emek).** Fotoğraf zemini ve renkli uydu simgesini bırakın. Düz `#05070f` zemin üstünde tek renk (kehribar) ince çizgiyle bir işaret: örneğin bir yörünge halkası içinde "7", ya da PROBE-7'nin tek çizgiyle çizilmiş silueti. 98 pikselde net okunur, hiçbir yapay zekâ kanalına benzemez.
- **Banner (küçük emek).** Zeminin büyük kısmı siyah. Solda kanal adı, sağda bir "uçuş kaydı" tablosu gibi dizilmiş görev listesi: `001  SEVEN WORLDS  40 LY  2H`. İnce kehribar çizgiler, köşelerde nişan işaretleri. İsterseniz altta dar bir şerit hâlinde tek bir sahne görseli. "NEW MISSION WEEKLY" yazısını kaldırın.
- **Kapak sistemi (orta emek).** Her kapakta aynı çerçeve, farklı içerik:
  - sol üstte büyük görev numarası (`001`), yanında görev adı (`SEVEN WORLDS`);
  - altta küçük, gerçek veri satırı: `TRAPPIST-1 · RA 23h 06m · DEC −05° 02′ · 40 LY`;
  - dört köşede ince nişan işaretleri (videodaki HUD'un devamı);
  - görsel o görevin en güçlü tek sahnesi.
  Böylece kapaklar yan yana gelince "aynı kanal, farklı yolculuklar" okunur. Gerçek koordinat hem doğrulanabilir hem de hiçbir rakipte yok.
  Dikkat: marka kitabındaki küçük önizlemede (168x94) ince başlık okunmuyor. Başlığı kalınlaştırın ya da büyütün; kapağı telefonda küçük hâliyle kontrol edin. Tamamen siyah kapak açık temalı akışta kaybolur; sahnede tek bir parlak odak (yıldız, hilal) şart.
- **Videoda "ARTIST'S IMPRESSION" etiketi (küçük emek).** NASA ve ESA çizimlerinin altına bunu yazar. HUD'un bir köşesine küçük harflerle eklemek hem dürüst hem de bilim iletişimi geleneğinden gelen bir üslup; "yapay zekâ" demeden doğruyu söyler.
- **Başlıklar.** "Seven Worlds | Deep Space Ambient Music for Sleep & Deep Focus (2 Hours)" iyi; 71 karakter, ad önde. Öneri: sona görev numarasını ekleyin (`· Mission 001`). Seri hissi ve geri dönen izleyici için.
- **Kanal açıklaması.** Haftalık sözü ve genel cümleleri çıkarın, kısa tutun. Taslak:

  > Deep-space ambient music for sleep and deep focus.
  >
  > Each video is one mission of PROBE-7: a two-hour route through twenty real worlds, with one piece of music for every stop and a log entry about the place itself. No vocals, no drums, no sudden changes.
  >
  > Visuals are artist's impressions. The worlds are real.
  >
  > Where should PROBE-7 go next?

- **Sayfa düzeni.** Tek video varken boş raflar açmayın: yalnız öne çıkan video ve "Missions" listesi. Fragman olarak 60–90 saniyelik bir "mission briefing" kesiti (HUD'un en hareketli anı: kartın yazıldığı bölüm). 3. videodan sonra "Sleep" ve "Focus" listeleri.
- **Gerçek görüntü seçeneği (isteğe bağlı).** Güneş Sistemi cisimleri ve bulutsular için NASA görüntüleri genel olarak serbest kullanımlıdır (ESA/Webb görselleri kaynak gösterme ister; kullanmadan önce her görselin lisansına bakılmalı). Gerçek fotoğraf "yapay zekâ" izlenimini en hızlı kıran şeydir. Öte yandan videonun tamamı hazır görüntüden oluşursa "reused content" riski artar. Önerim: kapakta ve banner'da değil, ara sıra bir sahnede ve kaynak göstererek.

## 4. Yol haritası

### Yarın (başlangıç günü)

Yarın video yayınlamayın; hazır değil. Yarının işi:

1. Sahibi iki karar verir: (a) ilk 3 videoda son "ok" bende, (b) çıktı 1440p olabilir.
2. Asistan: depoyu konsepte eşitler, çelişen sözleşme maddelerini tek onayla düzeltir, kanal sayfasını (profil, banner, açıklama) yeniler, "weekly" sözünü kaldırır.
3. Üretim küçük başlar: yeni konseptte 3 görsel + 2 şarkı + 1 dakikalık örnek. Sahibi "ok" derse kalan 17 görsel ve 18 şarkı.

### İlk 2 hafta

- 001 yayında (gerçekçi tarih: 15–18 Kasım; Suno indirme hakkı 18 Kasım'da yenileniyorsa ikinci video ondan sonra).
- Studio'dan elle yükleme; "AI use" işareti açık; 3 gerçekten farklı kapakla Test & Compare.
- 002 üretimde; 001'den öğrenilen tek şey değiştirilir.
- Shorts yok. Google API başvurusu ve otomatik yükleme bekleyebilir.
- Ölçülecekler (Studio, video başına): gösterim, tıklanma oranı, ortalama izlenme süresi, ilk 30 saniyede kalanların oranı, trafik kaynağı.
- Beklenti: yeni kanalda ilk iki hafta rakamları çok küçük ve gürültülü olur. Bu dönemde konsepti değiştirmeyin.

### İlk 3 ay

- Hedef: 8–10 görev (haftada en çok 1), 3. aydan itibaren bir 8 saatlik uyku derlemesi.
- Para kazanma eşiği: 1.000 abone + son 12 ayda 4.000 saat herkese açık izlenme. (Shorts izlenmeleri bu saate sayılmaz.) Daha düşük bir ara kademe de var (500 abone, 3.000 saat, son 90 günde 3 video); o kademe reklam geliri değil, üyelik ve bağış özelliklerini açar. Rakamları başvurudan önce Studio'daki "Earn" sekmesinden teyit edin.
- Açık konuşayım: bu nişte bu eşiğe 3 ayda ulaşmak olağan değil. 6–18 ay gerçekçi; hiç ulaşamayan kanal da çok. Arka planda dinleyen izleyici saat getirir ama az abone olur; darboğaz büyük olasılıkla abone sayısı olacak.

### Karar eşikleri

| Ölçü | Eşik | Karar |
|---|---|---|
| Gösterim (yayından 14 gün sonra) | 1.000'in altında | Sorun kapak değil, keşif. Başlık kelimelerini gözden geçir, yayına devam et |
| Tıklanma oranı (en az 2.000 gösterimde) | %3'ün altında | Yeni kapak; başlığa dokunma (tek seferde tek değişiklik) |
| Tıklanma oranı | %5'in üstünde | Kapak sistemi doğru; sabitle |
| Ortalama izlenme süresi (2 saatlik video) | 8 dakikanın altında | İlk dakikaya bak: geç açılan müzik, sert geçiş, parlak HUD |
| Ortalama izlenme süresi | 20 dakikanın üstünde | Format doğru; uzun (8 saat) sürümü dene |
| 6 video / 8 hafta sonunda | Toplam 50 saatin altında ve hiçbir video 500 izlenmeyi geçmemiş | Paketi ve formatı yeniden düşün: uyku ve odağı ayır, 8–10 saatlik sürüm, başlık kalıbı |
| 3 ay sonunda | 100 abonenin altında | Konsepti değil, dağıtımı sorgula: derleme, topluluk gönderileri, ilgili forumlar (spam olmadan) |

Bu eşikler benim önerimdir, YouTube'un resmî ölçüsü değil. Kanalın kendi verisi biriktikçe düzeltilmeli.

## 5. Kör noktalar

1. **Süreç ürünü geçti.** Sıfır video için 11 ajan, istasyon kilitleri, özet imzaları, 93 test. Asıl belirsizlik "izleyici bunu ister mi" sorusu; buna yalnız yayınlanmış video cevap verir. İlk 5 videoyu tek asistan + sahibinin okuyla çıkarın; ajan düzenini iş tekrar etmeye başlayınca açın.
2. **Testler doğru şeyi ölçmüyor.** 93 test yeşilken: açıklama "sixteen worlds" diyor, kapak şablonu kararla çelişiyor, yeni konseptin görseli kapıdan geçemiyor, depo konsepti bilmiyor. Testler kuralların harfini koruyor, hedefi değil.
3. **Rakibi kopyalayıp "özgün" demek.** Görsel yön, en çok izlenen kanalın (karanlık ufuk, tek galaksi, ince aralıklı yazı) kapağından alındı. Veri bunun tıklandığını gösteriyor, ama aynı veriye bakan herkes aynı yere varıyor. Aynı tabloda tamamen farklı duran bir örnek de var (eski plak kapağı tarzı, 274 bin izlenme). Fark, resimde değil çerçevede yaratılmalı (3.2).
4. **Shorts yanlış araç.** Durağan görsel + sakin ambient, kaydırılan akışta en zayıf içerik türü. Shorts'tan gelen abone 2 saatlik video izlemez; Shorts izlenmeleri 4.000 saate sayılmaz. Bunun için ayrı kurgucu ajan, plan dosyası ve kapılar yazıldı.
5. **Denetçiye fazla güven.** Yapay zekâ denetçi teknik kusuru (fazla tekerlek, ikiz figür) yakalıyor ama "bu fantastik film müziği gibi" ya da "bu Dünya'ya benziyor" diyemiyor. Bunlar sahibinin iki cümlesiyle çöktü. Zevk kararı insanda kalmalı.
6. **"Gizlersek sorun çözülür" varsayımı.** İzleyicinin tepkisi kelimeye değil, özensiz görünen işe. YouTube etiketi oynatıcıda yine görünebilir. Çözüm emeği göstermek: doğru bilgi, tutarlı rota, elle tasarlanmış çerçeve, görev notları.
7. **Müzik kalitesinin tek ölçüsü sahibinin kulağı.** Hatta ses yüksekliği ve sessizlik ölçülüyor, ama "20 parça birbirinden ayırt edilebiliyor mu, 2 saat sıkmadan akıyor mu" sorusuna bakan yok. Bu nişte izleyiciyi tutan şey müzik. Suno'da ilk çıkanı değil, en az 2 varyasyondan iyisini seçmek ve sıralamayı bir kez baştan sona dinlemek en değerli emek. İndirme sınırı bunu zorlaştırıyor; gerekirse üst plana geçmek buradaki en mantıklı harcama.
8. **Telif ve sahiplik.** Tamamen yapay zekâyla üretilmiş müzikte telif korumanız zayıf olabilir (ülkeye göre değişir; emin değilim). Başkası parçalarınızı alıp yüklerse karşı koymak zor. Suno üretim kayıtlarını ve tarihlerini saklayın; ücretli planın ticari kullanım hakkını ve bu hakkın plan bitince sürüp sürmediğini Suno'nun güncel şartlarından bir kez okuyun.
9. **Gelir beklentisi yazılmamış.** Aylık gider (Suno, ElevenLabs, vidIQ, Claude) belli; bu nişte bin izlenme başına gelir düşüktür. Başa baş noktası hiçbir dosyada hesaplanmamış. Maliyet kuralınız var ama hedef rakamınız yok.
10. **Devir notu tek hakikat kaynağı değil.** Karar hafıza notunda, kurallar sözleşmede, durum DEVIR.md'de, plan skill'de ve hepsi farklı şey söylüyor. Her kararın yazıldığı tek bir yer olmalı ve oturum sonunda güncellenmeli.
