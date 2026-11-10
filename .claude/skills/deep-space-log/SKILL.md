---
name: deep-space-log
description: Deep Space Log YouTube kanalı (eski Köz) işletme rehberi: yeni görev (video) konsepti, Suno istemleri, ses klasöründen videoya hat, kapı raporu, denetçi, sahibin onayı ve kayıt. "Yeni video", "görev", "Suno istemleri", "videoyu hazırla", "rapor kırmızı" gibi isteklerde kullan.
---

# Deep Space Log: işletme rehberi

Kurallar: `SOZLESME.md` G bölümü (değişmez; değiştirmeden önce sahibine sor). Kod: `deepspace/`. Ayarlar:
`deepspace/ayar.toml`. Görevler: `deepspace/gorevler/NNN-ad/gorev.toml`. Sahibiyle Türkçe konuş; kanal metinleri İngilizce.

## İstasyonlar (tek şef = sen; her istasyonun çıkışında kod kapısı var)

| # | İstasyon | Kim | Kapı |
|---|---|---|---|
| 1 | Konsept: `gorev.toml` (16 gerçek gök cismi, motif, palet, istem) | sen | `kapilar.gorev_dosyasi` + `ozgunluk` |
| 2 | Müzik: `SUNO.md` istemleriyle Suno'da üretim, seçim, `ses/` klasörüne yükleme | **sahibi** | dosya adları birebir |
| 3 | Ses: ölç, eşitle, çapraz geçiş, master | `python -m deepspace.gorev ses` | `kapilar.ses` |
| 4 | Sahneler (paralel) | `... sahneler` | döngü kusursuz (G6) |
| 5 | Uzun video (bölüm bölüm, paralel) | `... video` | süre, çözünürlük, siyah ekran |
| 6 | Kapak ×3, metin, Shorts ×3 | `... kapak / metin / shorts` | `kapilar.kapak / metin / shorts` |
| 7 | **Denetçi** | sıfır bağlamlı alt ajan | `rapor.json` yeşil + insan gözüyle bakış |
| 8 | Karar ve planlı yükleme | **denetçi** (sahibi izleyici, `iptal` hakkı) | G8 |

Hepsi tek komut: `python -m deepspace.gorev hepsi deepspace/gorevler/NNN-ad` (çıkış kodu 0 = bütün kapılar yeşil).

## 1. Yeni görev konsepti
1. `deepspace/kayit.json`'u oku: kullanılmış hedefler ve tohumlar tekrar edemez (G4). Önceki görevin
   `sonraki_adaylar` listesi ve sabit yorumdaki izleyici önerileri ilk aday havuzudur.
2. 16 parça (seriye göre), her biri **gerçek** bir gök cismi. `bilgi` alanı yalnızca doğrulanmış olgu (uzaklık,
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
   BAŞLASIN: `ambient soundscape, wind and distant thunder field recording,`. (001 bu kuraldan önce yazıldı: parça başına ayrı palet.)
4. `python -m deepspace.gorev istemler <klasör>` → `SUNO.md`. Kapı kırmızıysa dosya üretilmez.
5. Konsepti sahibine bilgi olarak bildir (hedef, duraklar, yay, ses paleti). Onay beklenmez (G8, 10 Kasım 2026):
   sahibi izleyicidir; yalnız Suno üretimi onda kalır (resmî API yok).

4b. Görseller: `python -m deepspace.gorev gorseller <klasör>` → `GORSEL.md` (sahne + marka stil eki). Konsept:
   Dünya'ya benzeyen sakin manzara + gökyüzünü kaplayan gerçek gök cismi + küçük hikâye unsuru (`marka.toml`).
   Her görsele bir sinemagraf tarifi (`gorsel/NN_hareket.json`): yalnız gerçekte hareket eden şey, ince; katı
   nesneler "haric" ile korunur (`deepspace/ornek_hareket/`). Kurallar ve dersler aşağıda "Sinemagraf hareketi".

## Sinemagraf hareketi (G14; 10 Kasım 2026 Small Signal örneğinden dersler)
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
- `hepsi` çalıştır. Kırmızı kapı varsa düzelt ya da sahibine hangi parçanın yeniden üretilmesi gerektiğini söyle
  (ör. "parça 05 ortasında 7 sn boşluk var").
- Aynı hata iki kez olursa not değil **kod kapısı** ekle (`kapilar.py` + test).

## 3. Denetçi
Rapor yeşil olunca bağlamsız bir alt ajana yalnızca `gorev.toml`, `cikti/rapor.json`, `cikti/youtube.json` ve
kapakları ver: "G kurallarına göre bu video yayına hazır mı? Kanıtla." Denetçi rapor.json'u okumadan ya da rapor
kırmızıyken "bitti" denmez. Sonra kapaklardan ve videodan birkaç kareyi kendin gör.

## Görseller ve marka
- Marka paleti ve stil eki `deepspace/marka.toml` (durum `taslak` iken sahibinin referansları bekleniyor). Tüm
  görseller bu paleti izler; paletten sapan görsel önerme.
- Parça görseli `gorsel/NN.png` (16:9, en az 3840 px genişlik) varsa canlı tablo (`tablo.py`) kullanılır; şeffaf ön
  plan `gorsel/NN_on.png` iki katmanlı derinlik verir. Görsel yoksa yedek kod sahnesi (`sahne.py`).
- 4K kodlama 2 saatlik videoda ~1,5–2 saat sürer: `hepsi`'yi arka planda çalıştır. Hızlı deneme için görevde
  `[ayar.video] genislik = 1920, yukseklik = 1080`.

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

## Maliyet (G11)
Ücretli tek kalem Suno. vidIQ (5 kredi/çağrı), görsel/video üretim kredisi gibi şeyleri sahibine sormadan kullanma.
