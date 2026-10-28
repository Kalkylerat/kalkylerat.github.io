---
name: nobet
description: Kalkylerat saatlik sağlık kontrolü (nöbet) ve işletme rehberi — saatlik rutin çalıştığında, "bot çalışıyor mu / post kaçtı mı / alarm geldi" sorularında, nabız veya nöbetçi workflow'u, alarm issue'ları ya da paylaşım zamanlaması (kart penceresi, aralık) incelenirken kullan.
---

# Kalkylerat nöbet rehberi

Bu dosya, sistemi kuran uzun sohbetin işletme bilgisidir; yeni oturumda hiçbir şey kaybolmasın diye burada.
Kurallar: `SOZLESME.md` (değişmez), çalışma kuralları: `CLAUDE.md`. Sahibiyle Türkçe konuş.

## Sistem
- Repo: `Kalkylerat/kalkylerat.github.io` (eski adı aticimustafa/videosil; "repository moved" uyarısı normal).
  Çalışma dalı = varsayılan dal: `claude/twitter-football-predictions-ywwfxw`. PR açma.
- `.github/workflows/kalkylerat.yml`: nabız ~7 dakikada bir; sabah analizi cron `17 5 * * *` (05:17 UTC).
- `.github/workflows/nobet.yml`: nöbetçi, bir çalışma ~5,5 saat sürer, nabzı tetikler. Kuyrukta `pending` ve
  `cancelled` çalışmalar NORMAL (concurrency). Sorun yalnızca hiç `in_progress` nöbetçi yoksa.
- Veri: `data/spel.json` gün kayıtları listesi, sonuncusu bugün. `etkilesim[tur]` = {durum, zaman, takip, sonuclar}.
- Alarm: `bot/saglik.py` GitHub'da `alarm` etiketli issue açar, @Kalkylerat-desk etiketlenir.

## Saatlik kontrol (rutinin yaptığı)
1. `git pull -q --rebase`
2. `python -m bot.durum` → bugünün postları (UTC), sözleşme sapmaları, günün kalanının simülasyonu ve Mr. Likely
   (ikinci hesap, aynı nabızla çalışır, SOZLESME E): kupon planlanan saatte çıktı mı, sonuç postu geldi mi.
   Son satır `SORUN YOK` ya da `SORUN: ...`.
   Ayrıca yorum fırsatları (SOZLESME D6: arama saatleri geçti mi, bugün kaç fırsat) ve Mr. Likely kupon planı
   (E7: plan ilk maçtan sonraya düştüyse "kaçacak").
3. Workflow'lar:
   - `gh api "repos/Kalkylerat/kalkylerat.github.io/actions/workflows/kalkylerat.yml/runs?per_page=4" --jq '.workflow_runs[]|"\(.created_at) \(.status) \(.conclusion)"'`
     → son çalışma 15 dakikadan eski ya da üst üste `failure` ise sorun.
   - `gh api "repos/Kalkylerat/kalkylerat.github.io/actions/runs?status=in_progress" --jq '.workflow_runs[]|"\(.name) \(.created_at)"'`
     → "Kalkylerat Nöbetçi" yoksa: `gh api -X POST repos/Kalkylerat/kalkylerat.github.io/actions/workflows/nobet.yml/dispatches -f ref=claude/twitter-football-predictions-ywwfxw`
4. Alarmlar: `gh api "repos/Kalkylerat/kalkylerat.github.io/issues?labels=alarm&state=open" --jq '.[]|"#\(.number) \(.updated_at)"'`
   Yeni (daha önce görülmemiş) issue/yorum varsa gövdesini oku.
   Eskiler, açıklandı: #8 #11 #16 #38 #41 (3–8 Ekim), #49 #50 (11 Ekim 14:47, Mr. Likely'de tek seferlik bağlantı kopması),
   #56–#59 (13 Ekim 10:10–11:48, X API kredisi bitti: 402 "credits depleted"; kaçan 14 post aynı gün geri sıraya kondu).
   #73–#91 (15 Ekim 19:05–20:58): Mr. Likely bilgi postu 503 aldı ama X'te paylaşılmıştı; her nabız 403 "duplicate
   content" aldı, nöbetçi her başarısız çalışmaya ayrı issue açtı. 16 Ekim'de düzeltildi (SOZLESME C2 "tek kanal").
5. Sorun yoksa sahibine tek satır "sorun yok" yeter. Sorun varsa kök nedeni bul, Türkçe kısa özet yaz.
   B7: 08–21 UTC arasında 3 saatten uzun post/yanıt yoksa bu HER ZAMAN sorundur ("sakin gün" deme).
   İstisna: az post modu (B8, `[az_post] aktif = true`, 28 Ekim 2026'dan beri): günde ~7 post, uzun boşluk normaldir;
   kart başına maç sonu ve tablo yanıtı yoktur, onların yerine gün sonu tek sonuç postu gelir.

## Tuzaklar (yaşandı)
- **Saat dilimi:** `baslama` ve `_plan` saatleri +02:00 (CEST). Yorumlamadan önce `.astimezone(timezone.utc)`.
  9 Ekim'de CEST saatleri UTC sanıldı, yanlış rapor verildi.
- Büyük maç dışı kaçan kart alarm üretmez (bilinçli, `saglik._buyuk_kart`), ama sahibine bildirilmeli;
  `bot.durum` bunu "atlanan postlar" olarak yazar.
- Yerelde test için gerekirse: `pip install --ignore-installed cryptography`. Testler: `python -m pytest -q` (hepsi yeşil olmalı).
- `git checkout <dosya>` yerel değişikliği siler; eski davranışı denemek için `git stash push <dosya>`.
- Tek seferlik ağ hatası (RemoteDisconnected vb.) sonraki nabızlar başarılıysa müdahale gerektirmez.
- **X kredisi biterse (402 "credits depleted"):** bot her nabızda sıradaki postu dener, düşen post o gün için
  `hata` olur ve bir daha denenmez (13 Ekim: 1,5 saatte 14 post düştü). Kredi yüklenince o günün 402 kayıtları
  `data/spel.json` → `etkilesim`'den silinirse bot onları normal düzende (aralık ≥13 dk) yeniden sıraya alır;
  önce `python -m bot.durum` simülasyonuyla son saatlere yetiştiğini doğrula. Mr. Likely kendi kendine yeniden dener.

## Paylaşım zamanlaması (bot/etkilesim.py) — neden böyle
- `_plan`: her post için (tür, en erken, en geç). Kart: maçtan 8 saat önce açılır, 35 dk önce kapanır, taban 08:00 UTC;
  aynı saate yığılan kartlar sığmayacaksa taban sabah analizine kadar öne çekilir (`KART_ADIM` 20 dk; 11 Ekim fix).
- `_oncelik`: büyük maç kartı önce (B6); büyük olmayan kart, son saatine 1 saatten çok varsa 3 saat geride sayılır
  (9 Ekim: bilgi postu kartı kaçırttı).
- `_paylasim_sirasi`: öncelikli post ancak kalan herkes son saatine yetişiyorsa öne geçer (10 Ekim).
- `aralik_dk`: yoğun günde en az 13 dk (ayarlar.toml), kalanlara yayılır ama her post kendi son saatine yetişecek sıklıkta.
- Geçmiş: 9 Ekim 7 kart kaçtı → yayılım düzeltmesi; 10 Ekim 30/30 kart; 11 Ekim 29/30 → kart penceresi düzeltmesi
  (e9cee15); 12 Ekim simülasyonu temiz.

## 14 Ekim dersleri (tekrar etmesin)
- Mr. Likely kupon aralığı seçim sırasıyla verilince kuponlar kendi maçlarının sonrasına itildi (E7, düzeltildi).
- "Double chance 12" kararı yalnızca gölge testte ölçülüyordu, koda geçmemişti (E6 artık yasaklar; C5).
- X'in cevap bağlantısı (web intent) Android'de cevabı ayrı post attı: taslaklar kopyalama sayfasıyla (D3, D6).
- Yorum fırsatları ve yorum kiti issue yorumu olarak gelir (#yorum-firsatlari, #yorum-kiti); sahibi göremiyorsa
  issue bağlantısını ver.

## Bildirim düzeni (16 Ekim, C2 "tek kanal")
- Bot yakaladığı hatayı günün `⚠️ Kalkylerat alarmı <tarih>` issue'suna yazar (aynı hata bir kez) ve çalışma YEŞİL biter.
- Kırmızı çalışma = bot alarm yazamadı ya da çöktü (test, kurulum, push). Nöbetçi bunun için dizi başına tek
  `(nöbetçi)` issue'su açar; bot düzelince sıfırlanır.
- Sahibine gelenler: alarm, 🚀 yorum fırsatları (iki hesap ayrı issue), 💬 yorumlar, 🎩 Mr. Likely günlük issue'su.

## Rutin
- Saatlik rutin "Kalkylerat saatlik nöbet", cron `3 * * * *` (UTC), Sonnet 5.5. Her çalışmada yeni, kısa bir oturum
  açar ve bu dosyayı izler; sonuç sahibine bildirim olarak gider. (12 Ekim'e kadar rutin, sistemi kuran uzun
  "Kalkylerat (Do Not Delete)" oturumuna bağlıydı; o oturum geçmiş olarak duruyor.)
- Rutin oturumu sorun yoksa tek satır yazar. Kod değişikliği gerekiyorsa küçük ve testli olanı yapar; büyük
  değişiklikleri (kural, mimari) yapmaz, sahibine önerir.
