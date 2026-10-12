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
2. `python -m bot.durum` → bugünün postları (UTC), sözleşme sapmaları, günün kalanının simülasyonu.
   Son satır `SORUN YOK` ya da `SORUN: ...`.
3. Workflow'lar:
   - `gh api "repos/Kalkylerat/kalkylerat.github.io/actions/workflows/kalkylerat.yml/runs?per_page=4" --jq '.workflow_runs[]|"\(.created_at) \(.status) \(.conclusion)"'`
     → son çalışma 15 dakikadan eski ya da üst üste `failure` ise sorun.
   - `gh api "repos/Kalkylerat/kalkylerat.github.io/actions/runs?status=in_progress" --jq '.workflow_runs[]|"\(.name) \(.created_at)"'`
     → "Kalkylerat Nöbetçi" yoksa: `gh api -X POST repos/Kalkylerat/kalkylerat.github.io/actions/workflows/nobet.yml/dispatches -f ref=claude/twitter-football-predictions-ywwfxw`
4. Alarmlar: `gh api "repos/Kalkylerat/kalkylerat.github.io/issues?labels=alarm&state=open" --jq '.[]|"#\(.number) \(.updated_at)"'`
   Yeni (daha önce görülmemiş) issue/yorum varsa gövdesini oku.
   Eskiler, açıklandı: #8 #11 #16 #38 #41 (3–8 Ekim), #49 #50 (11 Ekim 14:47, Mr. Likely'de tek seferlik bağlantı kopması).
5. Sorun yoksa sahibine tek satır "sorun yok" yeter. Sorun varsa kök nedeni bul, Türkçe kısa özet yaz.
   B7: 08–21 UTC arasında 3 saatten uzun post/yanıt yoksa bu HER ZAMAN sorundur ("sakin gün" deme).

## Tuzaklar (yaşandı)
- **Saat dilimi:** `baslama` ve `_plan` saatleri +02:00 (CEST). Yorumlamadan önce `.astimezone(timezone.utc)`.
  9 Ekim'de CEST saatleri UTC sanıldı, yanlış rapor verildi.
- Büyük maç dışı kaçan kart alarm üretmez (bilinçli, `saglik._buyuk_kart`), ama sahibine bildirilmeli;
  `bot.durum` bunu "atlanan postlar" olarak yazar.
- Yerelde test için gerekirse: `pip install --ignore-installed cryptography`. Testler: `python -m pytest -q` (hepsi yeşil olmalı).
- `git checkout <dosya>` yerel değişikliği siler; eski davranışı denemek için `git stash push <dosya>`.
- Tek seferlik ağ hatası (RemoteDisconnected vb.) sonraki nabızlar başarılıysa müdahale gerektirmez.

## Paylaşım zamanlaması (bot/etkilesim.py) — neden böyle
- `_plan`: her post için (tür, en erken, en geç). Kart: maçtan 8 saat önce açılır, 35 dk önce kapanır, taban 08:00 UTC;
  aynı saate yığılan kartlar sığmayacaksa taban sabah analizine kadar öne çekilir (`KART_ADIM` 20 dk; 11 Ekim fix).
- `_oncelik`: büyük maç kartı önce (B6); büyük olmayan kart, son saatine 1 saatten çok varsa 3 saat geride sayılır
  (9 Ekim: bilgi postu kartı kaçırttı).
- `_paylasim_sirasi`: öncelikli post ancak kalan herkes son saatine yetişiyorsa öne geçer (10 Ekim).
- `aralik_dk`: yoğun günde en az 13 dk (ayarlar.toml), kalanlara yayılır ama her post kendi son saatine yetişecek sıklıkta.
- Geçmiş: 9 Ekim 7 kart kaçtı → yayılım düzeltmesi; 10 Ekim 30/30 kart; 11 Ekim 29/30 → kart penceresi düzeltmesi
  (e9cee15); 12 Ekim simülasyonu temiz.

## Rutin
- Saatlik rutin: "Kalkylerat saatlik sağlık kontrolü", cron `3 * * * *` (UTC).
- Her çalışmada yeni oturum açan rutin için istem: "Kalkylerat saatlik nöbet: .claude/skills/nobet/SKILL.md'deki
  saatlik kontrolü uygula. Sorun varsa kök nedeni bul, güvenle düzeltilebiliyorsa testlerle düzelt ve push et,
  sahibine Türkçe kısa özet yaz."
