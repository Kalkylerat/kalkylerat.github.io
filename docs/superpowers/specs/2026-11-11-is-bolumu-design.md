# Deep Space Log: iş bölümü, denetim kilidi ve marka istasyonu (tasarım)

Tarih: 11 Kasım 2026 · Durum: sahibi onayladı (11 Kasım 2026); §12 Shorts departmanı ve §13 YouTube uzmanı aynı gün
sahibinin isteğiyle eklendi

## 1. Amaç
Bir görevin (2 saatlik video) bütün işleri ajanlara bölünür. Her işi, o işe yetecek en ucuz model yapar. Her iş
bağımsız bir denetçiden geçer; kalan iş düzeltilmeden bir sonraki istasyona **geçemez**. Bunu talimat değil kod
sağlar. Üstte tek bir şef bulunur: Opus 5.5, yüksek efor. Şef planlar, işi atar, denetimleri okur ve son kararı
verir. Her şey tek bir marka kitine uyar.

Sahibinin kararları (11 Kasım 2026):
- Sistem bu bilgisayarda çalışır. Şef, terminaldeki Claude Code oturumudur; render burada alınır.
- Şef sahibine yalnız sonda döner (G8): sonuç özeti ve 3 turda çözülemeyen işler.
- 001 görselleri kalır. Yeni görsel kuralları (ortam odaklı) 002'den başlar.
- Marka kiti bir kez sahibinin onayına gelir. Bu, G8'in tek istisnasıdır.
- Referanslar (ör. jazzy cafe kanalları) yalnızca histir; hiçbir şey kopyalanmaz, her şey markaya göre üretilir.

## 2. Roller ve modeller
Ajan tanımları `.claude/agents/<ad>.md` dosyalarında durur; model ve efor dosyanın başındaki ayarlarda yazılıdır.
Alt ajan başka ajan çağıramaz: bütün atamaları şef yapar.

| Ajan | İş | Model / efor | Araçlar |
|---|---|---|---|
| **şef** (ana oturum) | plan, atama, denetim sonucunu okuma, son karar, sahibine özet | Opus 5.5 / high | hepsi |
| marka-tasarimcisi | marka kiti (logo, renk, yazı, şablonlar, marka kitabı) | Opus / medium | dosya, görsel üretim |
| konsept-yazari | `gorev.toml` (20 gök cismi, yay, motif), ses paleti, Suno istemleri | Sonnet / medium | dosya |
| bilgi-dogrulayici | ekrana ya da metne giren her olguyu kaynakla doğrular | Sonnet / medium | web araması, okuma |
| gorsel-yonetmeni | ortam odaklı görsel istemleri, üretim, indirme | Sonnet / medium | dosya, ElevenLabs |
| gorsel-denetcisi | G13 saçmalık denetimi, tam çözünürlükte paftalar | Opus / high | okuma |
| hareket-tarifcisi | `NN_hareket.json` katmanları ve kendi kare kontrolü | Sonnet / medium | dosya, python |
| operator | ses, render, kapak, Shorts, yükleme komutları | Haiku / low | kabuk |
| **youtube-uzmani** | vidIQ araştırması, görev önerileri, haftalık büyüme analizi ve kararları (§13) | Opus 5.5 / high | okuma, vidIQ (yalnız araştırma), yazma yalnız `buyume/` |
| shorts-kurgucusu | uzun videodan 3 Shorts anı seçer, `shorts_plan.json` yazar (§12) | Sonnet / medium | dosya, python |
| kod-ustasi | hat değişiklikleri ve testler | Sonnet / medium (zor işte Opus) | hepsi |
| **denetci** | her istasyon çıktısının sözleşme ve marka kitine uygunluğu | Opus / high | yalnız okuma ve `gorev denetim` komutu |

İlkeler:
- İşi yapan ajan kendi işini denetleyemez.
- Denetçi, işçinin konuşmasını görmez. Yalnız çıktıyı, sözleşmeyi, marka kitini ve kanıt dosyalarını görür.
- Mekanik işler Haiku'da yapılır; yargı isteyen işler (görsel saçmalığı, son denetim, marka) Opus'ta kalır.

## 3. İş kaydı ve kilit (`deepspace/is_kaydi.py`)
- **İstasyon listesi** (sırayla): `marka` (bir kez, kanal düzeyinde), `arastirma` (§13), `konsept`, `bilgi`, `ses`,
  `gorsel`, `hareket`, `video`, `shorts` (§12), `paket` (kapak, metin), `karar`.
- **Tanım:** her istasyonun girdi ve çıktı dosyaları ile kod kapıları (`kapilar.py`) tanımlıdır.
- **Denetim kaydı:** `<görev>/denetim/istasyon_<ad>.json`. İçinde:
  - `karar`: GEÇTİ ya da KALDI,
  - `tur`: kaçıncı deneme,
  - `denetci`: kararı veren,
  - `ozetler`: çıktı dosyalarının sha256 özetleri,
  - `bulgular`: kod, açıklama, kanıt yolu,
  - `zaman`.
  - Görevin marka kiti özeti de yazılır: marka değişirse eski kararlar geçersiz olur.
- **Kilit:** bir istasyonun komutu (`sahneler`, `video`, `kapak`, `yukle` …), önceki istasyon GEÇTİ değilse ya
  da çıktı dosyaları karardan sonra değiştiyse çalışmaz. Çıkış kodu 3 olur ve neden yazdırılır. G13'teki dosya
  özeti düzeninin genelleştirilmiş halidir.
- **Kırmızı kod kapısı:** denetçi kararından önce çalışır. Kapı kırmızıysa denetçi GEÇTİ yazamaz (komut reddeder).
- **Komutlar:**
  - `gorev durum <klasör>`: istasyonlar, kararlar, turlar, sıradaki iş.
  - `gorev denetim <klasör> --istasyon X --karar GECTI|KALDI --bulgu "kod:not" [--kanit yol]`: yalnız denetçi
    kullanır.
  - `gorev kilit <klasör> --istasyon X`: kilidi elle sorar; çıkış kodu 0 ya da 3.

## 4. Düzeltme döngüsü
```
işçi → kod kapıları → denetçi ─ GEÇTİ → sonraki istasyon
                         └ KALDI → bulgular işçiye → düzeltme → (tur+1) → denetçi …
3. turda da KALDI → şef inceler (farklı işçi/model, istem düzeltmesi)
şef de çözemezse → olay `GOREV_GUNLUGU.md`'ye, sahibine tek mesaj
```
Şef kırmızı bir kod kapısını aşamaz. Kuralı yalnız sahibi değiştirebilir (SOZLESME → test → kod).

## 5. Görev akışı (002'den itibaren)
1. **marka** (kanal başına bir kez): kit, ardından denetçi, ardından **sahibinin onayı**.
2. **arastirma:** YouTube uzmanı görev için kelime, başlık adayı ve rakip verisini çıkarır (§13), ardından denetçi.
   **konsept:** `gorev.toml` ve `SUNO.md` (araştırma önerileriyle), ardından **bilgi** (her olgunun kaynağı ayrı `bilgi_kaynak.json` dosyasına; `gorev.toml`'a dokunmaz,
   böylece konseptin onaylı özeti bozulmaz),
   ardından denetçi.
3. **Sahibi:** Suno'da şarkıları üretir ve `ses/` klasörüne koyar (tek insan adımı).
4. **ses:** operatör ses kapısını çalıştırır (G3), ardından denetçi.
5. **gorsel:** istemler (marka kitinin görsel dili), üretim, G13 görsel denetimi.
6. **hareket:** katman tarifleri; denetçi tarifçinin aldığı kırpıntılara bakar.
7. **video:** 4K render (Seyir Defteri modu), video kapıları (süre, ses duyuluyor, siyah ekran), denetçi örnek
   karelere bakar.
8. **shorts:** kurgucu anları seçer, operatör keser, Shorts kapıları, denetçi (§12).
   **paket:** kapak ×3, metin (başlık araştırma önerisinden), ardından denetçi.
9. **karar:** şef bütün kayıtların GEÇTİ olduğunu ve özetlerin tuttuğunu doğrular. Gizli ve planlı yükleme yapılır
   (≥24 sa, G8). Sahibine tek özet gider (önizleme, kapaklar, başlık, `iptal` hakkı).

## 6. Marka istasyonu
Çıktı `deepspace/marka/` klasörüne gider; `marka.toml` genişler:
- **Kimlik ve ton:** sakin, bilimsel, sıcak. PROBE-7 anlatıcıdır; her video onun seyir defterinden bir kayıttır.
- **Logo:** Space Mono tabanlı "DEEP SPACE LOG" yazısı, PROBE-7 işareti, profil simgesi, banner.
- **Renk:** palet ve bal_kehribar film tonu (0.55).
- **Yazı:** ekran yazısı Space Mono (OFL); küçük resim başlıkları için kalın bir açık lisanslı font. Telefon
  kuralı: en küçük yazı kare yüksekliğinin %2'si.
- **İmza öğeleri:** sinyal çizgisi (visualizer, sahibinin beğendiği), görev saati, `MISSION 00N` etiketi.
  Küçük resimde de görünür.
- **Görsel dili (sahibinin düzeltmesi, 11 Kasım 2026: "görseller uzay temalı olacak"):** her sahne uzaydadır.
  Dünya manzarası, akarsu, göl ya da buğday tarlası yoktur. Örnek sahneler:
  - yabancı gezegen yüzeyi (kraterler, buz ovaları, lav düzlükleri),
  - yörüngeden görünen dünya,
  - istasyon penceresi ve gözlem güvertesi,
  - gezegen halkaları içinden görünüm,
  - asteroit kuşağı,
  - bulutsu önünde PROBE-7.

  Sahnede doğal bir ışık kaynağı bulunur: istasyon ışıkları, PROBE-7'nin işaret lambası, yanardağ parıltısı,
  kutup ışığı ya da yıldız. Konu ortamdır; insan figürü yoktur ya da çok küçüktür. `marka.toml` stil eki bu dile
  göre yeniden yazılır (eski "Earth-like landscape" eki 001'de kalır).
- **Şablonlar:** küçük resim (G7: ≤3 kelime, PROBE-7 görünür, 3 varyant), Shorts, banner.
- **Marka kitabı:** tek sayfalık görsel sayfa, sahibine gösterilir.

## 7. Hareket (Seyir Defteri modu, G14 içinde)
- Görüntü bükülmez; hareket yalnız üstüne eklenen katmanlardır.
- Var olanlar: `isik`, `toz`, `goktasi`, `yildiz`.
- Eklenecekler (hepsi uzaya ait):
  - `isaret_lambasi`: PROBE-7 ya da istasyon lambası,
  - `pencereler`: istasyon pencerelerinde rastgele yanıp sönen küçük ışıklar,
  - `kutup_isigi`: yabancı gezegende aurora bölgesinde yavaş parlaklık nabzı,
  - `halka_piriltisi`: gezegen halkalarında parlayan buz taneleri,
  - `bulutsu_tulu`: bulutsunun desensiz alanında çok yavaş parlaklık akışı,
  - `uydu`: gökte yavaş geçen nokta.
- Sahibinin notu: hareket biraz daha fazla olsun. Her sahnede en az 3 katman bulunur, biri müzikle bağlıdır.
- HUD: telefon okunurluğu (testli). Kayıt **kartı** sol alt köşededir (genişliğin ~%34'ü, satır başına en çok 34
  karakter, 3 satır). Kartta koyu cam zemin, ince çerçeve, kehribar vurgu çizgisi ve `PROBE-7 · LOG` etiketi
  bulunur. Sahibinin isteği: "şık arka plan, köşede, videoya yayılmadan".

## 8. Sözleşme değişiklikleri
- **G15 İş bölümü ve denetim kilidi:** işi yapan denetleyemez; kalan iş düzeltilmeden geçemez (kod kilidi);
  3 tur sonra şef, sonra sahibi; kırmızı kod kapısı aşılamaz.
- **G16 Marka:** her görsel çıktı (video yazısı, kapak, Shorts, banner) marka kitine uyar. Marka kiti ve
  değişiklikleri sahibinin bir kerelik onayıyla yürürlüğe girer (G8 istisnası).
- **G1/G7:** marka kitine atıf eklenir.
- **G12 genişler (Shorts departmanı, §12):** Shorts uzun videonun kurallarına aynen uyar (G4, G5, G9, G14, G16) ve
  kendi kapılarından geçer.
- **G17 YouTube uzmanı ve vidIQ bütçesi (§13):** G11'in sahibi onaylı istisnası; aylık kredi tavanı ve yalnız
  araştırma araçları kodla (kanca) zorlanır.

## 9. Testler
- `test_G15_*`:
  - denetimsiz istasyondan sonraki komut 3 ile çıkar;
  - KALDI kaydı kilitler;
  - çıktı dosyası değişince kayıt geçersizleşir;
  - kırmızı kapıda GEÇTİ yazılamaz;
  - 3. turdan sonra durum "şefte" görünür.
- `test_G16_*`:
  - onaysız marka kitiyle `kapak` ve `video` çalışmaz;
  - kit değişince eski kararlar geçersizleşir;
  - şablon yazıları telefon kuralını sağlar.
- `test_G12_*`: plan dışı ya da kuralsız Short kesilmez; 3 Short 3 ayrı parçadan; ilk 2 sn ses duyuluyor; dikey
  Seyir Defteri karesinde görüntü bükülmez; önceki görevlerde kullanılan an tekrar etmez.
- `test_G17_*`: izin listesi dışındaki vidIQ aracı reddedilir; tavan aşılınca çağrı reddedilir; her çağrı deftere
  yazılır; ücretsiz araç bütçeden düşmez.
- Ajan dosyaları: her `.claude/agents/*.md` dosyasında model ve araç tanımlı; denetçide yazma aracı yok (testle).

## 10. Kapsam dışı
- Bulutta zamanlanmış çalışma.
- Shorts dışındaki sosyal medya.
- YouTube uzmanının yayınlanmış videoyu API ile değiştirmesi (OAuth kurulumu bitince ayrı iş).
- Suno otomasyonu (resmî API yok).
- 001 görsellerinin yeniden üretimi.

## 11. Riskler
- **Kullanım limiti:** çok ajan, çok kullanım demektir. Haiku/Sonnet ağırlıklı dağılım ve kısa ajan talimatlarıyla
  azaltılır.
- **Denetçinin aşırı sertliği ya da gevşekliği:** kontrol listeleri yazılıdır (G13 düzeni). Şef, denetçi
  bulgularını örnekleyerek kontrol eder.
- **Görsel kredisi:** görsel başına yaklaşık 1.454, görev başına yaklaşık 29.000 kredi (plan içinde). Yeniden
  üretim görsel başına en çok 2 (G13).

## 12. Shorts departmanı (sahibinin isteği, 11 Kasım 2026)
Amaç: her uzun videodan, aynı kurallarla, keşif için 3 dikey Short. Bugünkü `gorev shorts` parçaları eşit aralıkla
seçer ve parçanın ortasını keser. Yeni düzende anı bir ajan seçer, kod keser ve denetler.

- **shorts-kurgucusu (Sonnet):** girdi `bolumler.json`, ses ve görseller. Her parça için ses enerji eğrisi
  (`gorev shorts-analiz`: saniye başına RMS ve geçiş/fade bölgeleri) ile en canlı ve en temiz 20–58 sn'lik aralığı
  bulur, görselin dikey kesimi için yatay odak (`kirp_x`, 0–1) seçer. Çıktı `<görev>/shorts_plan.json`:
  `[{parca, basla_sn, sure_sn, kirp_x, kanca}]` ×3. `kanca`: ilk karedeki en çok 3 kelimelik yazı (G7 kuralı).
- **Kod (`gorev shorts`):** plan varsa ona göre keser, yoksa bugünkü seçimle. Dikey kare Seyir Defteri modunda
  üretilir: görüntü bükülmez, katmanlar dikey kesime taşınır, HUD dikey düzende (üstte marka + görev, ortada kanca,
  altta sinyal çizgisi ve "Full 2-hour mission on the channel"). Ses aynı kesimden, 1.5 sn içe, 2.5 sn dışa geçiş.
- **Kurallar (G12 genişlemesi):**
  - 1080×1920, ≤60 sn, yalnız o videonun kendi müziği ve görseli;
  - 3 Short 3 ayrı parçadan; kullanılan anlar `kayit.json`'a yazılır, başka görevde tekrar etmez (G4);
  - ilk 2 sn'de ses duyulur (sessiz giriş yok), video içinde siyah kare yok;
  - görüntü bükülmez (G14), yazılar telefon kuralını sağlar ve marka kitine uyar (G16);
  - başlık ve açıklama G5'e uyar, yapay zekâ beyanı G9'a uyar, açıklama uzun videoya bağlantı verir;
  - yükleme gizli ve planlı: uzun videodan sonra +1, +3, +5. gün (G8 düzeni).
- **Denetim:** kapılar yeşil olmadan denetçi GEÇTİ yazamaz. Denetçi her Short'tan 3 kare (0., orta, son saniye)
  ve plan dosyasına bakar: kanca okunuyor mu, kırpma konuyu kesiyor mu, marka doğru mu.

## 13. YouTube uzmanı (sahibinin isteği, 11 Kasım 2026)
Amaç: kanalın büyümesi için veriyle araştırma yapan ve kural içinde karar veren ajan. `youtube` skill'ini ve
`deepspace/arastirma.md` düzenini kullanır. Model Opus 5.5, efor yüksek (sahibinin seçimi).

- **Görev başına (`arastirma` istasyonu):** konseptten önce kelime ve rakip araştırması. Çıktı
  `<görev>/buyume/oneriler.json` (hedef kelimeler, iki biçimde başlık adayı, seri ve süre önerisi, yayın saati) ve
  kısa `arastirma.md` (her rakamın hangi çağrıdan geldiği). Denetçi: yasak adlar (G5), kaynak, bütçe.
- **Haftalık analiz (kanal düzeyinde, kilitsiz):** kendi kanal verisi (Studio/vidIQ), rakip öne çıkanları,
  yükselen kelimeler. Çıktı `deepspace/buyume/hafta_<yıl>-<hafta>.md` ve `deepspace/buyume/kararlar.json`.
- **Kendi verebileceği kararlar:** başlık kelimeleri ve biçim testi, yayın günü ve saati, seri sırası, sonraki konsept
  adayları, kapak varyant sırası, oynatma listesi düzeni. Bir kerede tek değişiklik; önceki testin sonucu gelmeden
  ikincisi yok (youtube skill §6). Studio verisi vidIQ tahmininden önce gelir.
- **Sahibine sorduğu kararlar:** yeni seri, bütçe artışı, herhangi bir kuralın gevşemesi, kanal adı/handle.
- **Yasak:** sahte etkileşim, başka kanallara yorum, kopya başlık/kapak, film ve sanatçı adları.
- **vidIQ bütçesi (kodla):** proje ayarındaki `PreToolUse` kancası (`deepspace/vidiq_butce.py`) her vidIQ
  çağrısından önce çalışır:
  - izin listesi: yalnız okuma ve araştırma araçları (keyword research, outliers, similar channels, youtube search,
    channel stats, video stats, trending, channel analytics, balance); üretim yapan, kanala yazan ya da yorum
    yanıtlayan vidIQ araçları reddedilir;
  - aylık tavan `ayar.toml [vidiq] aylik_kredi` (öneri: 100 kredi; vidIQ ayda 150 yeniler), çağrı başı 5 kredi
    (balance ücretsiz); tavan aşılırsa çağrı reddedilir;
  - her çağrı `deepspace/buyume/vidiq_harcama.jsonl`'a yazılır (zaman, araç, kredi).
- **Sahibine dönüş:** G8 düzeninde; haftalık tek özet (3 satır bulgu, verilen kararlar, sorulacak bir şey varsa o).
