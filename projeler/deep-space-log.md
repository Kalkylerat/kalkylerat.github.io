# Deep Space Log (YouTube, eski Köz)

**Durum (9 Kasım 2026):** hat kuruldu (`claude/deep-space-log` dalı), uçtan uca denendi (34/34 kapı yeşil). İlk görev
001 TRAPPIST-1e: 20 parça, ~124 dk; sahibi Suno'da üretiyor (`SUNO.md`). Görsel yön: bütün görsellere kırmızı →
turuncu marka filtresi (`renk.py`, 5 seçenek sahibine gönderildi, seçim bekleniyor); 4K canlı tablo motoru hazır,
görsel kaynağı henüz kararlaştırılmadı. Film tonu seçildi: bal_kehribar (hafif). Onaylı görsel referansı: FLUX 3 "gözlem güvertesi".

- Kurallar: SOZLESME.md G. Kod `deepspace/`, rehber `.claude/skills/deep-space-log/SKILL.md`.
- Kanal: `@kozruh` (UCtJHvFs1UuIKwTUhcWVyWIg), 7 abone, video yok. Ad "Deep Space Log", maskot PROBE-7.
- Seriler: Deep Focus 2 saat (20 parça), Deep Sleep 3 saat (20), Sci-Fi Drift 2 saat (20).
- Ortam: görüntü sunucularına izinli kişisel ortam `kalkylerat.github.io` oluşturuldu; üretim oturumları orada açılmalı.

## Açık işler
- [ ] Filtre seçimi (marka.toml [filtre]) ve görsel kaynağı kararı (yapay zekâ görseli mi, JWST/Hubble mı).
- [ ] Sahibi: kanal adı/handle değişikliği, Suno'da 001'in 20 parçası, Google kurulumu (`deepspace/KURULUM.md`).
- [ ] YouTube Data API yüklemesi (OAuth kurulumu sahibinde), Drive'dan ses alma.
- [ ] İlk yayın sonrası `kaydet` ve haftalık analiz.

## İlk mesaj
Ayrıntılı devir notu: `deepspace/DEVIR.md` (yerel terminal kurulumu dahil).
> Deep Space Log'a devam ediyoruz. deepspace/DEVIR.md, SOZLESME.md G bölümü ve deep-space-log skill'ini oku,
> `py -m pytest -q tests/test_deepspace.py` çalıştır, sonra durumu 5 satırda özetle ve görsel kaynağı kararını sor.
