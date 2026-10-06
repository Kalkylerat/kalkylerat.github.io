# Kalkylerat botu: çalışma kuralları

- **Değişiklikten önce `SOZLESME.md`'yi oku.** Oradaki kurallar sahibiyle anlaşılmış, değişmez davranıştır. Bir
  değişiklik bir maddeyi bozacaksa önce sahibine sor; onay gelirse sırayla SOZLESME.md, `tests/test_sozlesme.py`, kod.
- Her değişiklikten sonra `python -m pytest -q` (sözleşme testleri dahil) yeşil olmalı; kırmızıysa gönderme.
- Sahibiyle Türkçe konuş; postlar İngilizce.
- X kuralları (SOZLESME.md D bölümü) her öneride önce kontrol edilir: otomatik takip/beğeni/başkalarına yanıt yok.
- Büyüme ve içerik soruları için `.claude/skills/sosyal-medya/SKILL.md`.
- **Mr. Likely** (ikinci hesap, otomatik mod): `bot/likely.py`, görsel `bot/likely_gorsel.py`, kurallar SOZLESME.md
  E bölümü, karakter ve kurulum `marka/MR_LIKELY.md`. Kuponu sabit kurallar seçer (E6); kuralları gevşetmeden önce sahibine sor.
