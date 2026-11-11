---
name: deep-space-log
description: Deep Space Log YouTube kanalı (eski Köz) işletme rehberi: yeni görev (video) konsepti, Suno istemleri, ses klasöründen videoya hat, kapı raporu, denetçi, sahibin onayı ve kayıt. "Yeni video", "görev", "Suno istemleri", "videoyu hazırla", "rapor kırmızı" gibi isteklerde kullan.
---

# Deep Space Log: işletme rehberi

Kurallar: `SOZLESME.md` G bölümü (değişmez; değiştirmeden önce sahibine sor). Kod: `deepspace/`. Ayarlar:
`deepspace/ayar.toml`. Görevler: `deepspace/gorevler/NNN-ad/gorev.toml`. Sahibiyle Türkçe konuş; kanal metinleri İngilizce.

## İş bölümü (G15, 002'den itibaren; tasarım `docs/superpowers/specs/2026-11-11-is-bolumu-design.md`)
Sen şefsin: atama yaparsın, kararı okursun, sahibine özet verirsin. İşi ajanlar yapar (`.claude/agents/`), işi yapan
kendi işini denetlemez. Alt ajan başka ajan çağıramaz.

| # | İstasyon | İşçi ajan | Çıktı (denetim özeti bunlardan) |
|---|---|---|---|
| 1 | `marka` (kanal başına bir kez) | marka-tasarimcisi | `deepspace/marka/`, `marka.toml` + **sahibin onayı** |
| 2 | `arastirma` | youtube-uzmani (vidIQ, G17 bütçesi) | `buyume/oneriler.json`, `buyume/arastirma.md` |
| 3 | `konsept` | konsept-yazari | `gorev.toml`, `SUNO.md` |
| 4 | `bilgi` | bilgi-dogrulayici | `bilgi_kaynak.json` |
| – | müzik | **sahibi** (Suno, tek insan adımı) | `ses/` |
| 5 | `ses` | operator (`gorev ses`) | `cikti/bolumler.json`, `cikti/ses.m4a` |
| 6 | `gorsel` | gorsel-yonetmeni → gorsel-denetcisi (G13) | `gorsel/NN.png`, `denetim/NN.json` |
| 7 | `hareket` | hareket-tarifcisi | `gorsel/NN_hareket.json` (≥3 katman, biri müzikle) |
| 8 | `video` | operator (`gorev video`, Seyir Defteri modu) | `cikti/video.mp4` |
| 9 | `shorts` | shorts-kurgucusu (`shorts-analiz` → plan) → operator (`gorev shorts`) | `shorts_plan.json`, `short_?.mp4`, `shorts.json` |
| 10 | `paket` | operator (`gorev kapak`, `gorev metin`) | `kapak_?.jpg`, `youtube.json`, `aciklama.txt` |
| 11 | `karar` | şef + denetci | `cikti/onay.json` |

**Şefin döngüsü:**
1. `py -m deepspace.gorev durum <klasör>` → `sıradaki` istasyon.
2. O istasyonun işçi ajanını çağır (girdi dosyaları ve sözleşme maddesiyle).
3. Kod kapıları işçinin çıktısında çalışır; kırmızıysa işçiye geri ver.
4. `denetci` ajanını sıfır bağlamla çağır: yalnız çıktı, sözleşme, marka kiti ve kanıt dosyaları. Kararı o yazar:
   `py -m deepspace.gorev denetim <klasör> --istasyon X --karar GECTI|KALDI --bulgu "kod:not" [--kanit yol]`.
   Kırmızı kod kapısı varken GEÇTİ yazılamaz (komut çıkış 3).
5. KALDI ise bulgular işçiye, düzeltme, yeniden denetim. **3. turda da KALDI** (`durum`'da `ŞEFTE`): sen incele
   (farklı işçi ya da model, istem düzeltmesi). Çözülmezse `GOREV_GUNLUGU.md`'ye yaz, sahibine tek mesaj.
6. Sıradakine geç. Sahibine dönüş yalnız sonda (G8: önizleme, kapaklar, başlık, `iptal` hakkı) ve marka kiti
   onayında (G16).

**Kilit:** bir istasyonun komutu, önceki her istasyon GEÇTİ olmadan ya da çıktıları karardan sonra değiştiyse
çalışmaz (çıkış 3, neden yazılır). Marka kiti değişirse bütün eski kararlar geçersiz olur (G16). `hepsi` komutu
yalnız 001 içindir (002'den itibaren çıkış 3). Elle sorgu: `gorev kilit <klasör> --istasyon X`.

## 1. Yeni görev konsepti (konsept-yazari ve bilgi-dogrulayici bunu uygular)
1. `deepspace/kayit.json`'u oku: kullanılmış hedefler ve tohumlar tekrar edemez (G4). Önceki görevin
   `sonraki_adaylar` listesi ve sabit yorumdaki izleyici önerileri ilk aday havuzudur.
2. Parça sayısı seriye göre (`ayar.toml` `parca_sayisi`, şu an 20), her biri **gerçek** bir gök cismi. `bilgi` alanı yalnızca doğrulanmış olgu (uzaklık,
   keşif yılı); emin olmadığın rakamı yazma, yuvarla ya da çıkar.
3. Besteci kuralları: komşu tonlar (ör. Re minör, Fa majör, Do majör, La minör), 50–66 BPM; her parçanın kendi
   motifi (nota adlarıyla ve tarifle); saatin bir yayı olsun (tek doruk ~%60–70'te), son parça ilk parçanın
   motifini değiştirerek geri çağırsın. Sanatçı/film adı yok (G5).
   **Bölüm ses paleti (sahibinin fikri, 10 Kasım 2026):** her bölümün (görevin) tek, tutarlı bir enstrüman paleti
   olur; bölümün bütün parçaları bu paletten seçer, parçalar motif ve dokuyla ayrışır. Sonraki bölüm uzay temasını
   koruyarak paleti değiştirir (yeni enstrümanlar, yeni dokular). Örnek palet "Yalnız Gezegen": org flüt registerı,
   rüzgâr, uzak gök gürültüsü, gezegen uğultusu, uzun çello armoniği, cam tınılar; az eleman, uzun sessizlikler.
   Görev dosyasında `ses_paleti = [...]` olarak yazılır.
   Ders (10 Kasım, "Small Signal" ölçümü): Suno ortam seslerini zayıf verdi (enerjinin %90'ı 250 Hz altı ve
   orta bant, 2 kHz üstü ~0; rüzgâr/kum/cızırtı yok denecek kadar az). Ortam sesi istenen paletlerde Style şu ekle
   BAŞLASIN: `ambient soundscape, wind and distant thunder field recording,`. 001 de 11 Kasım'da sahibinin isteğiyle bu paletle (Yalnız Gezegen) yeniden yazıldı; 002 aynı tarzda, başka enstrümanlarla.
   İstem biçimi (sahibinin): her parça için ayrı **Style** (≤1000 karakter, tonu, BPM'i, motifi nota adlarıyla ve süreyi içerir), **Exclude** ve zaman damgalı bölümlerle ayrıntılı **Lyrics** (`[Bölüm | 0:00-0:40 | tarif]`).
4. `python -m deepspace.gorev istemler <klasör>` → `SUNO.md`. Kapı kırmızıysa dosya üretilmez.
5. Konsepti sahibine bilgi olarak bildir (hedef, duraklar, yay, ses paleti). Onay beklenmez (G8, 10 Kasım 2026):
   sahibi izleyicidir; yalnız Suno üretimi onda kalır (resmî API yok).
6. Görseller (gorsel-yonetmeni): `python -m deepspace.gorev gorseller <klasör>` → `GORSEL.md` (sahne + marka stil
   eki, aşağıda "Görseller ve marka"). Hareket tarifleri (hareket-tarifcisi): Seyir Defteri katmanları.

## Eski sinemagraf modu (yalnız 001 ve `ornek --mod sinemagraf`; G14, 10 Kasım 2026 dersleri)
002'den itibaren varsayılan Seyir Defteri'dir (görüntü bükülmez). Aşağıdakiler eski yolu kullanan iş içindir.

Sahibinin tepkisi: "en büyük gezegen dönmüyor, üzerindeki katman çoğalıp tekrar birleşiyor; motion grafik gibi değil".
- **Hayalet yasak.** `akis` iki kaydırılmış kopyayı karıştırır. Desensiz dokuda (sis, pus, ince bulut tülü, su
  yüzeyi) görünmez, ama belirgin şekli olan şeyde (gezegen yüzeyi, kasırga, kıta, belirgin bulut kümesi) çift görüntü
  olur. Gezegenin üstüne `akis` koyma; `ton` ya da `parlaklik` koşulu gezegeni yakalıyorsa onu `haric`e al.
- **Tek fotoğraftan gezegen döndürülmez.** Görselde arka yüz yoktur. Görünen yüzü döndürmek kenarı çizgi çizgi
  gerer ya da aynalı, simetrik leke yapar (denendi, ikisi de kötü). `donme` yalnız iki şart birlikteyse çalışır:
  tam yüzey haritası (`doku`: görselin yanında 2:1 eşdikdörtgen dosya) ve diski tamamen kadrajda olan gezegen. Kod
  ikisinden biri eksikse reddeder. Dev, kadraja sığmayan gezegen her zaman sabit kalır. Gerçekte de bu ölçekte
  dönme bir dakikada görünmez.
- Gezegeni döndürmenin ücretli yolları (G11: sahibine maliyetle sor): (1) gezegen başına bir tam yüzey haritası
  üretmek (görsel modeli, "seamless equirectangular texture map ...", 2K ≈ 1.454 kredi) ve `donme` + `doku`; (2)
  görselden hareketli klip `gorsel/NN.mp4` (görüntüden videoya model).
- Sahneyi canlı tutan şeyler: buğday/çimen `dalga`, ağaç `salinim`, ışıklar `parilti`, karanlık gökte `yildiz`,
  desensiz sis ya da su `akis`.
- **Tarifi göndermeden önce kendin bak.** Hareketli bölgeden döngünün 0, 1/8, 1/4, 3/8 ve 1/2 noktalarında kırpıntı
  al ve Read ile incele. Çift görüntü, gerilme çizgisi, simetrik leke ya da ileri-geri gidip gelme varsa tarifi düzelt.
- **Sesli teslim.** Örnek videoyu `python -m deepspace.gorev ornek <klasör> --parca N --ses <dosya>` ile üret. Sessiz
  döngü `cikti/ornek/ara/` içinde kalır, teslim klasöründe yalnız sesli video durur. Komut sesi ölçer
  (`kapilar.ses_duyuluyor`, ortalama > -45 dB); "hazır" demeden önce bu ölçüm geçmiş olmalı. Sahibine verilen
  yol tek dosya olsun.

## 2. Müzik geldikten sonra
- `ses/` klasöründe `SUNO.md`'deki dosya adları birebir olmalı. Ses dosyaları ve `cikti/` depoya girmez (.gitignore).
- 002'den itibaren istasyon istasyon ilerle (`ses` → `gorsel` → ... yukarıdaki döngü). `hepsi` yalnız 001 içindir.
  Kırmızı kapı varsa düzelt ya da sahibine hangi parçanın yeniden üretilmesi gerektiğini söyle
  (ör. "parça 05 ortasında 7 sn boşluk var").
- Aynı hata iki kez olursa not değil **kod kapısı** ekle (`kapilar.py` + test).

## 3. Denetçi (G15)
Her istasyonun kararını `denetci` ajanı verir (yukarıdaki döngü, `gorev denetim`). `karar` istasyonunda ona yalnızca
`gorev.toml`, `cikti/rapor.json`, `cikti/youtube.json`, kapaklar ve birkaç video karesi verilir: "G kurallarına göre
bu video yayına hazır mı? Kanıtla." Denetçi rapor.json'u okumadan ya da rapor kırmızıyken "bitti" denmez. Şef
kararı okur, kapaklardan ve videodan birkaç kareyi kendi de görür.

## Görseller ve marka (G16)
- Marka kiti onaylı (11 Kasım 2026): `deepspace/marka/` (banner, profil, filigran, marka kitabı, `kaynak/A2.png`) ve
  `marka.toml`. Renk A: film tonu yok, kehribar yalnız vurgu. Yazı Space Mono. Kit yeniden üretimi: `gorev kanal`.
- Görsel dili (`marka.toml [gorsel] stil_eki`): karanlık durgun ufuk, gökyüzünü kaplayan tek büyük gök cismi, bol
  boşluk, insan yok ya da çok küçük; ışık fiziği doğru (G13). 001 eski dilde kalır (`stil_eki_001`).
- Kapak şablonu: ince harf aralıklı başlık, kehribar çizgi ve etiket, gökte küçük PROBE-7; 3 düzen; en fazla 3
  kelime (G7: seri adı + süre, ör. `DEEP FOCUS` + `2H`).
- Parça görseli `gorsel/NN.png` (16:9). Defter modunda her parçanın görseli zorunludur.
- 4K Seyir Defteri render'ı 2 saatlik videoda yaklaşık 5 saat kare + kodlama (3 süreç): `video`'yu arka planda
  çalıştır. Hızlı deneme için görevde `[ayar.video] genislik = 1920, yukseklik = 1080`.

## Seyir Defteri modu (`deepspace/defter.py`; uzun video ve Shorts'un varsayılanı, `[video] mod = "defter"`)
- Görüntü hiç bükülmez (G14). Hareket yalnız üstüne eklenen ışık ve parlaklık katmanlarıdır
  (`gorsel/NN_hareket.json` → `"katmanlar"`; koordinatlar 16:9 karede, 0–1):
  `isik`, `isaret_lambasi` (kırmızı, 2 sn), `pencereler` (istasyon ışıkları, ~20 sn'de bir yanar/söner),
  `kutup_isigi` (resmin kendi parlaklığıyla), `halka_piriltisi` (parlak piksellerde), `bulutsu_tulu` (yavaş
  parlaklık dalgası), `uydu` (seyrek geçiş), `toz`, `goktasi`, `yildiz`. Her katman `"muzik": true` alabilir.
  Kutulu katman kutu dışındaki piksele dokunmaz. Hareket kapısı: en az 3 bilinen katman, biri müzikle bağlı.
- Marka kaydı (HUD), Space Mono: sol üst kanal ve görev; sağ üst görev saati (`T+` videonun gerçek saatini sayar) ve
  `NN/20 RECEIVING`; sol alt harf harf kayıt (gerçek bilgi `gorev.toml`'dan); sağ alt müziğin spektrumundan sinyal.
- Uzun video: parça başına bir bölüm (paralel süreçler, `cikti/ara/` altında sessiz), kesim çapraz geçişin
  ortasında; sonra birleştirme ve master ses. Sessiz dosya yalnız `ara/` içinde olabilir (G14).
- Tarifi göndermeden önce kendin bak: iki farklı anın karesini ve farkını al, hareket yalnız istenen yerde mi.
- Örnek: `python -m deepspace.gorev ornek <klasör> --parca N --ses <dosya>` (sesli, ölçülmüş).

## Shorts departmanı (G12)
1. `py -m deepspace.gorev shorts-analiz <klasör>` → `cikti/shorts_analiz.json` (saniyelik enerji, önerilen an).
2. shorts-kurgucusu analize ve görsellere bakıp `<görev>/shorts_plan.json` yazar:
   `[{"parca", "basla_sn" (mutlak), "sure_sn" (20–58), "kirp_x" (0–1, dikey kadraj odağı), "kanca" (≤3 kelime)}]`.
   3 Short 3 ayrı parçadan; aralık çapraz geçişin dışında; kullanılmış an (`kayit.json`) tekrar etmez.
3. `py -m deepspace.gorev shorts <klasör>`: plan kapısı yeşilse 1080x1920 dikey Seyir Defteri (üstte marka, y≈0.28H
   kanca, altta "Full N-hour mission" ve sinyal), master sesin aynı aralığı; `cikti/shorts.json` metinleri.
   Kapılar: dikey ve ≤60 sn, ses duyuluyor, ilk 2 sn ses, siyah kare yok, metin G5/G9.
4. Yükleme uzun videoyla: her Short gizli, uzun videonun yayınından +1, +3, +5 gün sonra planlı, açıklamada uzun
   videonun bağlantısı. `kaydet` kullanılan anları `kayit.json`'a yazar.

## Görsel denetimi (G13: saçmalık motoru)
Her yeni ya da değişen görsel videoya girmeden:
1. `python -m deepspace.gorev denetle <klasör>`: teknik durum (çözünürlük, 16:9, pozlama, netlik, kopya görsel).
2. `... denetle <klasör> --parca N`: kontrol listesi, istem ve 6 tam çözünürlüklü pafta yazdırır. Paftaların hepsine
   **Read ile bak** (küçük önizlemede fazla parmak, ikiz figür, fazla tekerlek görünmez). İnsan/araç varsa ayrıca
   yakın kırp. Gökteki dev cisim konseptin parçasıdır; istemde olmayan ikinci güneş/figür/nesne "tekrar"dır.
3. `... denetle <klasör> --parca N --puan P [--sorun "kod:not"]`. Kritik kod (anatomi, yazi, fizik, istem) ya da
   puan <7 = kaldı. Kalan görselde `gorev.toml`'daki `gorsel_istem`e kusurun tersini açıkça ekle ("a single
   fisherman, no other people", "exactly six wheels"), ElevenLabs düğümünün istemini güncelle, **tek varyasyonla**
   yeniden üret (`generations_count=1`, 2K ≈ 1.454 kredi), indir, yeniden denetle; `gorsel_oturum/gorsel_uretim`
   kimliklerini güncelle. Görsel başına en fazla 2 deneme; sonra kod sahnesi + `GORSEL_DENETIM.md`'ye kayıt.
`kontrol` raporu da bu kapıyı içerir: denetimsiz görsel = kırmızı rapor.

## Google (kurulum `deepspace/KURULUM.md`)
- `al --drive DeepSpaceLog/NNN`: ses ve görselleri Drive'dan çeker. `teslim`: paketi Drive'da `cikti/`'ya koyar.
- `onay --kim sahip [--yayin <RFC3339>]`: **yalnızca sahibi sohbette açıkça "ok" dediğinde**. `yukle`: gizli/planlı.
- YouTube API denetimi geçene kadar API yüklemeleri gizliye kilitlenir: o zamana kadar `teslim` + sahibin Studio'dan
  manuel yüklemesi.

## 4. Karar, yükleme, kayıt (G8: sahibi izleyici)
- Kararı denetçi verir: rapor yeşil + denetçinin gözle bakışı (kapaklar, birkaç kare, metin). Seçimleri (görsel,
  şarkı varyasyonu, kapak varyantı) sistem yapar.
- `onay --yayin <RFC3339>`: yayın saati karardan **en az 24 saat** sonra. Ardından sahibine **bilgi** gider
  (önizleme bağlantısı, kapak, başlık): onay istenmez. Sahibi "iptal" derse `iptal` komutu (planlı yayını da geri alır).
- Yükleme her zaman gizli + planlı; "altered or synthetic content" işaretli, kategori Music, reklam araları
  `reklam_noktalari`, Test & Compare'e 3 kapak, sabit yorum `sabit_yorum`.
- YouTube API denetimi geçene kadar yüklemeler gizliye kilitlenir: o zamana kadar `teslim` (Drive) ve sahibine
  "Studio'dan yükle" bilgisi.
- Yayından sonra `kaydet --youtube-id ...` ve kayit.json'u commit et.
- Sahibi bir şeyi beğenmezse tarihiyle `deepspace/begenmeme.md`'ye yaz; tekrar eden madde kurala ya da koda dönüşür.

## Maliyet (G11, G17)
Ücretli kalemler: Suno (sahibinde), ElevenLabs görsel kredisi (sahibine sormadan harcanmaz), vidIQ (yalnız
youtube-uzmani, aylık 100 kredi tavanı; proje kancası `deepspace/vidiq_butce.py` aşımı ve izin dışı aracı reddeder,
harcama `deepspace/buyume/vidiq_harcama.jsonl`'da).
