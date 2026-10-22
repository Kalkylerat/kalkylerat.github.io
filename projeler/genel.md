# Genel: Claude kullanımı ve maliyet

**Durum (22 Ekim 2026):** çalışma düzeni notları. Projelere ait olmayan kararlar burada.

## Model ve oturum
- **Model kuralı (9 Ekim, geçerli):** varsayılan Sonnet; Opus yalnızca zor tasarım ve hata ayıklamada. 27 Eylül'deki
  "direkt Opus + effort low" tavsiyesi geçersiz.
- Uzun tek oturum pahalı: kalıcı Kalkylerat oturumu ~466,89 $ tuttu. İş başına yeni oturum aç, başta ilgili
  `projeler/<proje>.md` dosyasını okut (her dosyanın sonunda "İlk mesaj" var).
- Beyin fırtınası API'de değil sohbette (abonelikle): üç ajanlı API turu ~9 $, X para kazanma oturumu ~25 $ tuttu.
- Claude Code bulut oturumları bilgisayar kapalıyken telefondan çalışır.
- Bulut oturumları claude.ai'deki normal sohbetleri, Projects'i ve Cowork'ü göremez: onlar için
  [claude-ai-aktarim.md](claude-ai-aktarim.md).

## Skill ve araçlar
- morluto/rea "reverse-engineer-anything" skill'i `ccr-a04ad725-brbtyt` dalında; MCP kurulamadı, CLI ile denenebilir.
- Kayıtlı skill'ler: `e-ticaret-uzmani`, `flow-event-finans`, bu depodaki `nobet`, `sosyal-medya`, `tiny-fixes`,
  `instagram`.

## Çalışma kuralları (sahibinin sözleri)
- "Benden çıkan her fikri mantıklıymış gibi düşünme."
- "Bir sorun olduğunda hemen bize haber gelmesi lazım." (nöbet ve alarm sistemi buradan)
- Her düzeltme bir testle gelir; verilen karar aynı gün koda döner (C4–C6).

## claude.ai sohbetlerinden
- 13 Ekim: claude.ai sohbeti evdeki PC'ye yalnızca masaüstü uygulama köprüsüyle ulaşır; terminaldeki Claude Code ayrı
  oturumdur. Erişim klasör bazlı (Downloads, Desktop, Documents, Pictures) ve o oturum için; PC uykuya geçmemeli.
- Çalışma tarzı: araştırıp somut, öncelikli seçeneklerle dön; sahibi tepki vererek ilerler; önce ucuz pilot, sonra yatırım.
- Dışa aktarma notu (22 Ekim): 112 sohbetin yalnızca 3'ünün metni geldi; kalan 109 sohbet yalnızca claude.ai hafızası ve
  artifact'lar üzerinden özetlenebildi. Eksik içerik için dışa aktarma yeniden istenebilir.
