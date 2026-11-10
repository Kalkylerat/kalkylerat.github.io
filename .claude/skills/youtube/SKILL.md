---
name: youtube
description: YouTube kanal uzmanı (Deep Space Log). Kanal kurulumu ve yeniden markalama (ad, handle, açıklama, banner, profil, fragman, oynatma listeleri), başlık/kapak/paket, büyüme ve izlenme süresi stratejisi, YPP para kazanma politikaları (inauthentic/reused content, yapay zekâ beyanı) ve Studio ayarları sorulduğunda ya da değiştirilirken kullan. "Kanalı kur", "başlık", "kapak", "neden izlenmiyor", "para kazanma", "kanal ayarları" gibi isteklerde.
---

# YouTube kanal uzmanı: Deep Space Log

Bu rehber Deep Space Log için yazıldı: uzun, enstrümantal, uzay temalı odak ve uyku müziği. Kurallar her zaman
`SOZLESME.md` G bölümüne bağlıdır. Marka kararları `deepspace/marka.toml` ve marka kitinde durur. Kanal metinleri
İngilizce yazılır; sahibiyle Türkçe konuşulur. Referans kanallar yalnız fikir verir, hiçbir şey kopyalanmaz.

## 1. Bu nişin gerçekleri
- **Büyüme izlenme seansıyla gelir, viral patlamayla gelmez.** Bu nişte YouTube'un önerdiği şey uzun dinleme
  seanslarıdır. İnsanlar bu videoları çalışırken arka planda açar ve tekrar döner. Uzun, zamansız (evergreen)
  videolar yıllarca izlenir.
- **Rekabet yoğun, giriş kolay.** Fark yaratan şey: tutarlı bir ruh hali ve marka, tanınan bir görsel imza (bizde
  sinyal çizgisi, görev saati, PROBE-7) ve her videoda gerçekten farklı bir konsept.
- **Değerli izleyici geri dönen izleyicidir.** Seri yapısı (MISSION 001, 002 …) geri dönüşü besler.
- Sektör blogları (vidIQ, OutlierKit, Metricool) yön verir ama rakamları satış amaçlıdır. Karar verirken kanalın
  kendi Studio verisine bak.

## 2. Para kazanma politikası (en büyük risk)
YouTube 15 Temmuz 2025'te "repetitious content" kuralının adını **inauthentic content** yaptı ve tanımını
netleştirdi. Kaynak: support.google.com/youtube/answer/1311392.
- **Yasak olanlar:**
  - "mass-produced, generic, repetitive" içerik;
  - "minimal variation across videos";
  - "image slideshows … with minimal or no narrative";
  - "AI-generated content made with generic or unoriginal templates giving the impression of mass production".
- **İzin verilen:** ortak giriş/çıkış ve "each video has a distinct storyline, focus, or concept" olan seriler.
- **Reused content** kuralı kanalın bütününe uygulanır: ihlal varsa kanalın tamamında para kazanma kapanabilir.

**Deep Space Log'u koruyan şeyler.** Hiçbiri gevşetilmez; denetçi her videoda arar:
1. Her video ayrı bir görevdir: kendi rotası, 20 gerçek gök cismi, yayı ve ses paleti olur (G4, konsept
   istasyonu).
2. Her parçanın kendi özgün görseli ve kendi katman tarifi vardır. Aynı görsel iki videoda kullanılmaz.
3. Anlatı vardır: seyir defteri kaydı gök cisminin doğrulanmış bilgisini anlatır, görev saati ve rota ilerler.
   Bu "minimal narrative" değildir.
4. İnsan emeği görünür: konsepti, müziğin seçimini ve kürasyonunu sahibi ve sistem yapar; açıklamada süreç notu
   bulunur (G9).
5. Şablon tek başına içerik değildir: HUD ortak bir çerçevedir; içerik (müzik, görsel, bilgi) her videoda yenidir.
6. Toplu yükleme yapılmaz. Kalite kapısından geçen video yayına çıkar; haftada en fazla 1–2 uzun video.

**Yapay zekâ beyanı.** Kaynak: support.google.com/youtube/answer/14328491.
- YouTube "AI generated music" için beyanı zorunlu sayıyor: müzik videonun ana konusuysa beyan gerekir.
- Her yüklemede Studio'da Attributes → **AI use: Yes** (G9).
- Beyan erişimi ya da para kazanmayı kısıtlamaz. Beyan etmemek ise ceza ve YPP'den çıkarılma nedenidir.

**Telif.**
- Yalnız ticari hakkı olan Suno planıyla üretilmiş müzik kullanılır.
- Başkasının müziği, görüntüsü ya da sesi kullanılmaz (G9).
- Content ID itirazı gelirse kanıt olarak Suno üretim kaydı saklanır.

## 3. Kanal kurulumu (Köz → Deep Space Log)
**Kurulum sırası.** Ad ve handle API ile değişmez; bunları sahibi Studio'dan yapar. Gerisini sistem hazırlar.
1. **Ad:** 14 gün içinde en fazla 2 değişiklik. Değişiklik doğrulama rozetini kaldırır.
   - 11 Kasım 2026 itibarıyla "Deep Space Log" adında başka bir küçük kanal var: `@deepspacelog`, 1 video, Mayıs
     2025'ten beri bırakılmış.
   - YouTube'da adlar benzersiz değildir, ama handle benzersizdir.
2. **Handle:** 14 günde en fazla 2 değişiklik. `@deepspacelog` dolu. Boş adaylar (11 Kasım 2026'da 404 döndü):
   `@deepspacelogmusic`, `@thedeepspacelog`. Seçmeden önce Studio'da yeniden kontrol et.
3. **Profil resmi:** 800×800 px, daire içinde 98 px'te bile okunur. Yazı yok, PROBE-7 işareti.
4. **Banner:** 2560×1440 px (en az 2048×1152), ≤6 MB.
   - Yazı ve logo yalnızca ortadaki güvenli alana girer: 2560 genişlikte 1546×423 px; 2048 genişlikte 1235×338.
   - Kenarlar TV'de görünür, telefonda kırpılır.
5. **Filigran:** 150×150 px, şeffaf PNG. Abone ol düğmesi işlevi görür; videonun sonunda göster.
6. **Açıklama (About):** ilk 2 cümle aramada görünür. Ne (space ambient for focus and sleep), kim (PROBE-7'nin
   seyir defteri), ne sıklıkla. Anahtar kelimeler doğal cümle içinde geçer, liste halinde dizilmez.
7. **Bağlantılar ve iletişim:** yalnız sahibinin onayladığı bağlantılar eklenir.
8. **Varsayılan yükleme ayarları:**
   - kategori Music, dil English;
   - "Altered or synthetic content": Yes;
   - yorumlar açık, ama "potentially inappropriate" tutulur;
   - lisans Standard;
   - açıklama şablonu `metin.py`'den gelir.
9. **Kanal ana sayfası düzeni:**
   - fragman: abone olmayanlara 60–90 sn'lik "Mission briefing";
   - öne çıkan video: abonelere son görev;
   - bölümler: "Missions" (uzun videolar, yeni → eski), "Deep Focus", "Deep Sleep", "Sci-Fi Drift" oynatma
     listeleri, Shorts.
10. **Oynatma listeleri:** her seri bir liste, ayrıca "All Missions". Liste açıklaması da İngilizce ve
    anahtar kelimeli.

## 4. Paket: başlık, kapak, ilk 30 saniye
- **Başlık** (≤100 karakter, G5): önce fayda, sonra marka.
  - Örnek: `Deep Focus Music for Studying · 2 Hours of Space Ambient · Mission 001: TRAPPIST-1`.
  - Sanatçı ya da film adı yok (G5), yanıltıcı vaat yok. Yıl eklemek ("2026") arama trafiği getirebilir, ama
    zamansızlığı azaltır: önce test et.
- **Kapak** (G7):
  - 3 varyant Test & Compare'de, en fazla 3 kelime, PROBE-7 görünür, marka kitinin renkleri;
  - telefonda 168×94 px'te bile okunmalı;
  - tek bir odak (dev gök cismi), yüksek kontrast;
  - seri etiketi `MISSION 00N` her kapakta aynı yerde.
- **İlk 30 saniye:**
  - siyah ekran yok (G6);
  - müzik 3 sn'de açılır;
  - HUD hemen görünür (görev adı, saat);
  - izleyici ne dinleyeceğini ilk karede anlar.
- **Bölümler:** her parça bir bölüm (G5); bölüm adları gök cisimleri. Bu, aramada "key moments" olarak çıkar.
- **Sabit yorum:** görev rotası, bir sonraki görev, izleyiciye soru ("Where should PROBE-7 go next?"). Cevaplar
  sonraki konseptin aday havuzudur.

## 5. Yayın ritmi ve büyüme
- Düzenli takvim, toplu yükleme değil. Başlangıçta haftada 1 uzun video. Yayın saati hedef kitlenin
  sabahından 2–3 saat önce, gizli ve planlı (G8).
- **Shorts:** her videodan 3 dikey parça (G12), keşif için. Shorts'tan uzun videoya bağlantı ver ("related video").
- **Uzun yayınlar:** 3 saat (Deep Sleep). 24/7 canlı yayın, kanal 10+ video ve geri dönen izleyici olunca
  düşünülür; tekrar eden döngü canlı yayını inauthentic riski taşır.
- **Topluluk:** sonraki görev oylaması, yeni bir gök cismi bilgisi.
- **Yasak** (G9): sahte izlenme ya da abone, sub4sub, başka kanallara spam yorum.

## 6. Ölçüm ve karar
- İlk 48 saat: gösterim tıklama oranı (CTR). Bu nişte %4–8 iyi sayılır; %2'nin altındaysa kapak ya da başlık
  testi yap.
- Ortalama izlenme süresi (dakika) ve oran: uzun videoda dakika, oran değerinden daha önemlidir.
- Geri dönen izleyici, abonelik kaynağı, trafik kaynağı (arama, önerilen, dış kaynak).
- Karar kuralı: bir değişiklik bir kerede bir şeyi değiştirir. Test & Compare sonucu gelmeden ikinci değişiklik
  yapılmaz.
- vidIQ ve benzeri ücretli araçlar çağrı başına kredi harcar: sahibine sormadan kullanma (G11).

## 7. Denetçiye kontrol listesi (YouTube paketi)
- [ ] Başlık ≤100 karakter, fayda önce, sanatçı/film adı yok, yanıltıcı değil.
- [ ] 3 kapak; telefonda okunur; ≤3 kelime; PROBE-7; marka renkleri; seri etiketi.
- [ ] Açıklama: ilk 2 satır özet; bölümler 0:00'dan; her gök cismi için doğrulanmış bilgi; süreç ve yapay zekâ
      notu.
- [ ] AI use = Yes; kategori Music; gizli ve planlı yükleme (≥24 sa).
- [ ] Bu video öncekilerden konsept, görseller, müzik ve anlatı bakımından açıkça farklı (inauthentic kalkanı).
- [ ] Sabit yorum ve bitiş ekranı (son 20 sn: sonraki görev + abone ol).
