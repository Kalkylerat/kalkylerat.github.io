# Kaynak

`SKILL.md` ve `LICENSE`: https://github.com/blader/humanizer (v3.1.0, MIT, Siqi Chen), 15 Ekim 2026'da değiştirilmeden
indirildi. Wikipedia'nın "Signs of AI writing" listesine dayanır.

Botta kullanımı: Mr. Likely'nin cevap taslaklarını yazan modele bu dosyanın tamamı gönderilmez (her çağrıda ~8 bin
token, maliyet kuralı). Kısa tweet'e uyan maddeleri `bot/yorum.py` → `LIKELY_INSAN` içinde özetlendi; uzun tire ve
kıvrık tırnak `bot/yorum.py` → `temizle` ile koddan düzeltilir. Bu skill'i elle metin düzeltirken (post, rehber)
doğrudan kullanabilirsin.
