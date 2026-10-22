# Tiny Fixes (yapay zekâ, X + Instagram)

**Durum (22 Ekim 2026):** kod ana dalda (PR #71), bot kapalı (`[flood] mod = "kapali"`). Kurulum listesinde 22 adımın
1'i tamam. Eski çalışma adı "Prompt Proof" (14–15 Ekim).

## Özet
- İngilizce; Fix (trend sorun + gerçekten denenmiş prompt), News (kaynaklı haber), Library (evergreen kart).
- "Tested with <model>" + sınır cümlesi, iki bağımsız kaynak, sahte deneyim yok (SOZLESME F1–F3). Trend içerik
  yalnızca sahibinin `ok` cevabıyla (F6).
- Gelir: kendi site (`docs/tinyfixes/`) + Kit e-posta listesi (ücretsiz 10 prompt) + Lemon Squeezy $9 paket (F11–F14).
  `[flood_gelir]` içinde form ve ürün adresi henüz boş.
- Tahmini maliyet ~$35–45/ay (sıkı mod ~$25). Ayrıntı: `docs/superpowers/specs/2026-10-15-tiny-fixes-design.md`.

## Açık işler (sahibinin adımları, `marka/TINY_FIXES_KURULUM.md`)
- [ ] Anthropic aylık harcama sınırı (öneri $40).
- [ ] X hesabı (Automated etiketi, Premium) → `flood_yetki`.
- [ ] Instagram Creator hesabı + Meta uygulaması → `flood_ig`.
- [ ] Kit formu ve Lemon Squeezy ürün adresi → `ayarlar.toml [flood_gelir]`.
- [ ] `mod = "onay"`, birkaç gün taslak kalitesi, sonra `"otomatik"`.
- [ ] Sahibine sorulacak: "Tiny Fix #12" seri numarası eklensin mi? (öneri: evet, ek maliyet yok)
- Not: RSS/Trends kaynakları ve gerçek X/Instagram çağrıları canlı denenmedi; ilk çalışmada `flood_tani` ile bak.

## İlk mesaj
> Tiny Fixes kurulumuna devam edeceğiz. CLAUDE.md, SOZLESME.md F bölümü, marka/TINY_FIXES_KURULUM.md ve
> projeler/tiny-fixes.md dosyalarını oku. Sıradaki kurulum adımını söyle ve beni adım adım yönlendir. Kuralları bana
> sormadan gevşetme.
