---
name: tiny-fixes
description: Tiny Fixes (üçüncü hesap: X ve Instagram, yapay zekâ) işletme rehberi — taslak/onay akışı, mod, alarm, kurulum, kural değişikliği ve "neden paylaşılmadı / taslak düştü / Instagram hata verdi" sorularında kullan.
---

# Tiny Fixes işletme rehberi

Kurallar: `SOZLESME.md` F bölümü (değişmez), çalışma kuralları: `CLAUDE.md`. Sahibiyle Türkçe konuş, postlar İngilizce.
Karakter ve hesap bilgileri: `marka/TINY_FIXES.md`; kurulum: `marka/TINY_FIXES_KURULUM.md`. X için `sosyal-medya`,
Instagram için `instagram` skill'i. Mr. Likely ve Kalkylerat hesaplarına bu modül dokunmaz.

## Akış (`bot/flood.py`)
`kaynak` (Google Trends, Hacker News, RSS; X'ten okuma yok) → `puan` (kaynak sayısı, tazelik, hız, nişe uygunluk; F5 güvensiz
konular ve işlenmiş konular elenir) → `yazar.triage` (Fix/News/atla) → `dogrula` (web araması + her olgu 2 bağımsız alan adı;
Fix komutu gerçekten çalıştırılır, zayıf çıktı elenir) → `yazar.yaz` (X flood + Instagram carousel, en fazla 3 deneme) →
`denetci` (tüm kurallar kodla) → onay issue'su (`flood-onay`) → yayın (X zinciri, sonra Instagram) → 24 saat sonra ölçüm →
kalıcı geçmiş (`state.gecmis`) → `flood_ogren` (F10: yalnızca sıralama ve öneri) → Pazartesi `flood-rapor` issue'su.
Trend adayları tembel doğrulanır: ilk uygun konu yazılınca kalanlar araştırılmaz (maliyet).
Yorum kitleri: X (`yorum.kontrol`, hesap "flood", ayrı `FLOOD_SISTEM`) ve Instagram (`flood.ig_yorumlari`, 30 dk'da bir,
yalnızca okuma + 2 taslak, `yorum-kiti-flood-ig` issue'su). Bot hiçbir zaman cevap atmaz (F7).
Her nabızda çalışır (`nabiz`/`onay_kontrol`); slotlar: trend 06 ve 14 UTC, evergreen 10 UTC; nabız başına en fazla bir birim.

## Mod (`ayarlar.toml → [flood] mod`)
`kapali` (varsayılan: hiçbir şey okunmaz/yapılmaz), `onay` (hepsi sahibin `ok` cevabıyla), `otomatik` (yalnızca evergreen
kendiliğinden, trend yine onayla: F6). Anahtarlar yoksa yalnızca taslak (F9).

## Gelir katmanı (F11–F14; sahibinin kararı: "önce para")
Trafik X/Instagram'dan, para kendi sitemizden: `flood_site` (docs/tinyfixes/, yalnızca yayınlanmış çözümler),
`flood_kutuphane` (herkese açık `data/flood_kutuphane.json` + şifreli paket `data/flood_paket.enc`), `flood_pdf`
(kopyalanabilir metinli PDF), `flood_gelir` (ayarlar `[flood_gelir]`, son çağrı seçenekleri, bülten taslağı, Kit ve Lemon
Squeezy yalnızca okuma). Form/ürün bağlantısı yoksa site o kutuyu ve postlar "free pack" çağrısını göstermez.
Paket PDF'leri depoya girmez (`urun/` gitignore; iş akışı 1 günlük artifact).

## Komutlar
`flood_paket` (paket temalarını gerçekten dener, PDF'leri üretir; `ek` = en fazla kaç yeni tema), `flood_site` (siteyi yeniden yazar),
`flood_tani` (salt okunur: kaynaklar, puanlama, depo erişimi; Claude/X/Instagram'a dokunmaz; mod kapalıyken de çalışır),
`flood_yetki` (X izni), `flood_ig` (Instagram anahtarı), `flood` (nabzın yalnızca Tiny Fixes kısmı).

## Sorun giderme
- **Taslak gelmedi:** `data/flood.json → gun[<tarih>].slotlar` o slotun denendiğini gösterir (başarısız olsa da yeniden
  denenmez, para harcar). Nöbet özetinde "uygun konu çıkmadı / doğrulanamadı / çıktı zayıf" satırları nedeni yazar.
- **Taslak düştü:** 3 saat cevap gelmedi (F6); yeni taslak sonraki slotta gelir.
- **Paylaşım denetimden geçmedi (durum `hata`):** son kapı kayıttan sonra bozulan metni yakaladı; `birim.hata` nedeni yazar.
- **Instagram hata:** 3 denemeden sonra yalnızca X yayınlanmış sayılır ve nedeni `birim.ig.hata`'da. Sık nedenler: depo
  herkese açık değil (görsel adresi 404), anahtar süresi dolmuş, hesap Business/Creator değil, 24 saatlik hak.
- **X hata:** yarım kalan flood sonraki nabızda kaldığı yerden sürer (çift paylaşım yok).
- **Konu kaynağı yanıt vermiyor:** RSS adresleri `[flood] rss` içinde; çökeni bot atlar. Hepsi çökerse üretim durur.

## Kural değiştirmek
Önce SOZLESME.md F bölümü, sonra `tests/test_flood.py`, en son kod (CLAUDE.md sırası). `python -m pytest -q` yeşil olmalı.

## Maliyet (tahmin, USD/ay; ilk ay sonunda gerçek faturayla doğrula)
X Premium ~8, X API ~8–12 (post başına ~0,015; linkli post ~0,20), Claude ~15–25 (Sonnet 5.5 yazar/araştırma, Haiku 5.5
seçim/değerlendirme), Instagram API 0. Sıkı mod ~25: günde 1 trend birimi, link yanıtı yok.
