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
| 8 | Onay ve yükleme | **sahibi** (`ok`) | G8 |

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
   Görev dosyasında `ses_paleti = [...]` olarak yazılır. (001 bu kuraldan önce yazıldı: parça başına ayrı palet.)
4. `python -m deepspace.gorev istemler <klasör>` → `SUNO.md`. Kapı kırmızıysa dosya üretilmez.
5. Konsepti sahibine kısa özetle sun (hedef, 16 durak, yay). `ok` gelmeden müzik istenmez.

4b. Görseller: `python -m deepspace.gorev gorseller <klasör>` → `GORSEL.md` (sahne + marka stil eki). Konsept:
   Dünya'ya benzeyen sakin manzara + gökyüzünü kaplayan gerçek gök cismi + küçük hikâye unsuru (`marka.toml`).
   Her görsele bir sinemagraf tarifi (`gorsel/NN_hareket.json`): yalnız gerçekte hareket eden şey, ince; katı
   nesneler "haric" ile korunur (`deepspace/ornek_hareket/`).

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

## Google (kurulum `deepspace/KURULUM.md`)
- `al --drive DeepSpaceLog/NNN`: ses ve görselleri Drive'dan çeker. `teslim`: paketi Drive'da `cikti/`'ya koyar.
- `onay --kim sahip [--yayin <RFC3339>]`: **yalnızca sahibi sohbette açıkça "ok" dediğinde**. `yukle`: gizli/planlı.
- YouTube API denetimi geçene kadar API yüklemeleri gizliye kilitlenir: o zamana kadar `teslim` + sahibin Studio'dan
  manuel yüklemesi.

## 4. Onay, yükleme, kayıt
- Sahibine: başlık, 3 kapak, rapor özeti, önizleme. `ok` olmadan public yok (G8). Yükleme gizli ya da planlı.
- Yüklemede: "altered or synthetic content" işaretli, kategori Music, reklam araları `youtube.json`
  → `reklam_noktalari`, Test & Compare'e 3 kapak, sabit yorum `sabit_yorum`.
- Yayından sonra `python -m deepspace.gorev kaydet <klasör> --youtube-id ...` ve kayit.json'u commit et.
- Sahibi bir şeyi beğenmezse tarihiyle `deepspace/begenmeme.md`'ye yaz; tekrar eden madde kurala ya da koda dönüşür.

## Maliyet (G11)
Ücretli tek kalem Suno. vidIQ (5 kredi/çağrı), görsel/video üretim kredisi gibi şeyleri sahibine sormadan kullanma.
