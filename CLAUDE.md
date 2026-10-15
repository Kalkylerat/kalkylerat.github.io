# Kalkylerat botu: çalışma kuralları

- **Değişiklikten önce `SOZLESME.md`'yi oku.** Oradaki kurallar sahibiyle anlaşılmış, değişmez davranıştır. Bir
  değişiklik bir maddeyi bozacaksa önce sahibine sor; onay gelirse sırayla SOZLESME.md, `tests/test_sozlesme.py`, kod.
- Her değişiklikten sonra `python -m pytest -q` (sözleşme testleri dahil) yeşil olmalı; kırmızıysa gönderme.
- Sahibiyle Türkçe konuş; postlar İngilizce.
- **Maliyet kuralı (sahibinin isteği):** performansı ve doğruluğu düşürmeden en ucuz yöntem. Ücretli her çağrıyı (X okuma/
  yazma, Claude, API-Football) eklemeden önce günlük maliyetini hesapla; aynı veriyi iki kez okuma (önbellek, ortak
  arama), boş dönen sorguları tercih et, Claude sistem metnini önbellekte tut. Ucuzlatmak için kaliteden ödün verme.
- X kuralları (SOZLESME.md D bölümü) her öneride önce kontrol edilir: otomatik takip/beğeni/başkalarına yanıt yok.
- Büyüme ve içerik soruları için `.claude/skills/sosyal-medya/SKILL.md`.
- Saatlik sağlık kontrolü, alarmlar, workflow'lar ve paylaşım zamanlaması için `.claude/skills/nobet/SKILL.md`
  (hızlı durum: `python -m bot.durum`).
- **Mr. Likely** (ikinci hesap, otomatik mod): `bot/likely.py`, görsel `bot/likely_gorsel.py`, kurallar SOZLESME.md
  E bölümü, karakter ve kurulum `marka/MR_LIKELY.md`. Kuponu sabit kurallar seçer (E6); kuralları gevşetmeden önce sahibine sor.
- **Prompt Proof** (üçüncü hesap, X + Instagram, yapay zekâ; varsayılan `kapali`): `bot/flood*.py`, kurallar SOZLESME.md
  F bölümü, karakter ve kurulum `marka/PROMPT_PROOF.md`, işletme `.claude/skills/prompt-proof/SKILL.md`, Instagram
  `.claude/skills/instagram/SKILL.md`. Trend içerik yalnızca sahibinin `ok` cevabıyla çıkar (F6); kuralları gevşetmeden önce sahibine sor.
