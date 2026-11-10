# Deep Space Log: iş bölümü, denetim kilidi ve marka istasyonu (tasarım)

Tarih: 11 Kasım 2026 · Durum: sahibinin onayı bekleniyor (yazılı not) · Sahibinin tasarım onayı: 11 Kasım 2026

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
| kod-ustasi | hat değişiklikleri ve testler | Sonnet / medium (zor işte Opus) | hepsi |
| **denetci** | her istasyon çıktısının sözleşme ve marka kitine uygunluğu | Opus / high | yalnız okuma ve `gorev denetim` komutu |

İlkeler:
- İşi yapan ajan kendi işini denetleyemez.
- Denetçi, işçinin konuşmasını görmez. Yalnız çıktıyı, sözleşmeyi, marka kitini ve kanıt dosyalarını görür.
- Mekanik işler Haiku'da yapılır; yargı isteyen işler (görsel saçmalığı, son denetim, marka) Opus'ta kalır.

## 3. İş kaydı ve kilit (`deepspace/is_kaydi.py`)
- **İstasyon listesi** (sırayla): `marka` (bir kez, kanal düzeyinde), `konsept`, `bilgi`, `ses`, `gorsel`,
  `hareket`, `video`, `paket` (kapak, metin, Shorts), `karar`.
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
2. **konsept:** `gorev.toml` ve `SUNO.md`, ardından **bilgi** (her olgunun kaynağı `bilgi_kaynak` alanına),
   ardından denetçi.
3. **Sahibi:** Suno'da şarkıları üretir ve `ses/` klasörüne koyar (tek insan adımı).
4. **ses:** operatör ses kapısını çalıştırır (G3), ardından denetçi.
5. **gorsel:** istemler (marka kitinin görsel dili), üretim, G13 görsel denetimi.
6. **hareket:** katman tarifleri; denetçi tarifçinin aldığı kırpıntılara bakar.
7. **video:** 4K render (Seyir Defteri modu), video kapıları (süre, ses duyuluyor, siyah ekran), denetçi örnek
   karelere bakar.
8. **paket:** kapak ×3, metin, Shorts ×3, ardından denetçi.
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
- Ajan dosyaları: her `.claude/agents/*.md` dosyasında model ve araç tanımlı; denetçide yazma aracı yok (testle).

## 10. Kapsam dışı
- Bulutta zamanlanmış çalışma.
- Shorts dışındaki sosyal medya.
- Suno otomasyonu (resmî API yok).
- 001 görsellerinin yeniden üretimi.

## 11. Riskler
- **Kullanım limiti:** çok ajan, çok kullanım demektir. Haiku/Sonnet ağırlıklı dağılım ve kısa ajan talimatlarıyla
  azaltılır.
- **Denetçinin aşırı sertliği ya da gevşekliği:** kontrol listeleri yazılıdır (G13 düzeni). Şef, denetçi
  bulgularını örnekleyerek kontrol eder.
- **Görsel kredisi:** görsel başına yaklaşık 1.454, görev başına yaklaşık 29.000 kredi (plan içinde). Yeniden
  üretim görsel başına en çok 2 (G13).
