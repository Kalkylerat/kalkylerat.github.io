# Kalkylerat botu: çalışma kuralları

- **Değişiklikten önce `SOZLESME.md`'yi oku.** Oradaki kurallar sahibiyle anlaşılmış, değişmez davranıştır. Bir
  değişiklik bir maddeyi bozacaksa önce sahibine sor; onay gelirse sırayla SOZLESME.md, `tests/test_sozlesme.py`, kod.
- Her değişiklikten sonra `python -m pytest -q` (sözleşme testleri dahil) yeşil olmalı; kırmızıysa gönderme.
- Sahibiyle Türkçe konuş; postlar İngilizce.
- X kuralları (SOZLESME.md D bölümü) her öneride önce kontrol edilir: otomatik takip/beğeni/başkalarına yanıt yok.
- Büyüme ve içerik soruları için `.claude/skills/sosyal-medya/SKILL.md`.
- **Mr. Likely** (ikinci hesap, elle paylaşılır): `bot/likely.py`, kurallar SOZLESME.md E bölümü, karakter ve
  kullanım `marka/MR_LIKELY.md`. Bot bu hesap adına X'e hiçbir şey paylaşmaz; yalnızca GitHub'da taslak hazırlar.
