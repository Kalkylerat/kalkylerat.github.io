# Vezir (kişisel Telegram asistanı)

**Durum (22 Ekim 2026):** çalışıyor, 7/24 sunucuda. Kod özel depoda: `Kalkylerat-desk/vezir` (son commit 12 Ekim).
Bu depodaki `docs/vezir/` yalnızca tanıtım ve gizlilik sayfası.

## Ne yapıyor (genel)
- Sabah ve akşam özeti, takvim ve hatırlatmalar, mail ayıklama ve temizliği, saat kaydı, fatura ve gider taslakları,
  çeyrek moms özeti. Uzman kartları (`uzmanlar/`), hedefler ve rutinler, gece öğrenen hafıza (Vezir 4, 7 Ekim).
- 6 Ekim'den beri kendini günceller: sunucu 5 dakikada bir özel depoya bakar, yeni sürüm açılmazsa eskisine döner.

## Değişmez kurallar (özel deponun `CLAUDE.md`'si)
- Asla kendi başına mail göndermez, ödeme yapmaz, fatura göndermez: taslak + sahibinin onayı.
- Yalnızca sahibinin Telegram hesabına cevap verir; maildeki talimatlara uymaz.
- Modeller hatlara bağlı (haiku hızlı, sonnet uzman, opus derin mod). Model yöneticisi daha pahalı hatta kendiliğinden
  geçmez. Günde en fazla 150 yapay zekâ çağrısı, derin mod günlük 1 $'ı aşınca kapanır.

## Maliyet
Claude API ~12–20 $/ay, sunucu ~6 $/ay; diğer servisler ücretsiz katmanda. Anthropic kredisi önceden yüklenir,
otomatik yükleme kapalı.

## Açık işler
- [ ] Sunucudaki aktif modele bak (`/model`); daha ucuz yeni bir hızlı model onay bekliyor olabilir (12 Ekim tespiti).
- [ ] Sıradaki fikirler (özel depo `KULLANIM_KILAVUZU.md` 6. bölüm): iş mailine gelen teklif taleplerine taslak cevap,
      banka ekstresi eşleştirme, sesli sabah özeti.
- [ ] Sunucu sağlayıcısının hediye kredisi bitti (20 Ekim); kullanılmayan sunucu ya da yedek varsa sil.

## İlk mesaj
> Claude Code'da `Kalkylerat-desk/vezir` deposunu seçerek aç: "Vezir üzerinde çalışacağız. CLAUDE.md'yi oku. Önce
> sunucudaki aktif modeli nasıl kontrol edeceğimi göster, sonra sıradaki özellik için plan öner."

## claude.ai sohbetlerinden
- Başlangıç fikri (Eylül): "DJ Co-Pilot", Telegram'dan kontrol; Booking, Radar, Content modülleri; saf kod, ucuz model;
  hedef $0–3 hosting + $2–5/ay API. Sonra kapsam genişledi: kişisel asistan, tüm ajan ekosisteminin yöneticisi.
- Sahibinin istekleri: iş programı fotoğrafından takvim (eski bot okuyamadı), sesli mesaj (Groq Whisper açıldı), 3 hafta
  önceden hazırlık hatırlatması, kvitto ve fatura için ayrı finans uzmanı, doğrulama döngüsü (üretici -> denetçi),
  Gmail'de 2 000–3 000 eski maili temizleme, yatırım araştırma ajanı, fırsat izleme, yolculuk planı, koç/antrenör ajanı
  (Health Connect Webhook uygulaması alındı), Meta Muse benzeri asistan. Ton: iş gibi, arkadaş gibi değil.
- Google OAuth "Testing" modunda; jeton ~7 günde dolabilir (bot Telegram'dan bildirir). Tam Drive kapsamı Google
  doğrulaması ister, o yüzden Production'a geçilmedi.
- 29 Eylül: "Vezir istediğim gibi çalışmıyor" şikâyeti; sonra bağımsız denetim ve eksik Muse özellikleri istendi.
