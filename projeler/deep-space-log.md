# Deep Space Log (YouTube, eski Köz)

**Durum (11 Kasım 2026):** hat kuruldu (`claude/deep-space-log` dalı). İş bölümü (G15: 11 ajan, istasyon başına
denetçi kararı, kilitli komutlar), Shorts departmanı (G12), YouTube uzmanı ve vidIQ bütçesi (G17) eklendi. Marka kiti
onaylı (G16: renk A, film tonu yok, Space Mono, karanlık ufuk + tek dev gök cismi). Varsayılan hareket Seyir Defteri
(görüntü bükülmez, fiziksel ışık katmanları). 001 TRAPPIST-1e: 20 görsel hazır ve denetlendi, sahibi Suno'da üretiyor
(şu an 1 parça). Ayrıntı `deepspace/DEVIR.md`.

- Kurallar: SOZLESME.md G. Kod `deepspace/`, rehber `.claude/skills/deep-space-log/SKILL.md`.
- Kanal: `@kozruh` (UCtJHvFs1UuIKwTUhcWVyWIg), 7 abone, video yok. Ad "Deep Space Log", maskot PROBE-7.
- Seriler: Deep Focus 2 saat (20 parça), Deep Sleep 3 saat (20), Sci-Fi Drift 2 saat (20).
- Ortam: görüntü sunucularına izinli kişisel ortam `kalkylerat.github.io` oluşturuldu; üretim oturumları orada açılmalı.

## Açık işler
- [x] Filtre ve görsel kaynağı kararı (11 Kasım: renk A, yapay zekâ görseli, marka kiti onaylı).
- [ ] Marka istasyonu: denetçi kararı ve sahibin onay kaydı (`gorev marka --onay --kim sahip`).
- [ ] 001 kapağı: sahibinin seçtiği B3 (`marka/taslak/kapak_001.jpg`) ile `kapaklar` çıktısını eşle.
- [ ] Sahibi: kanal adı/handle (`@deepspacelogmusic`), Suno'da 001'in 20 parçası, Google kurulumu (`deepspace/KURULUM.md`).
- [ ] YouTube Data API yüklemesi (OAuth kurulumu sahibinde), Drive'dan ses alma.
- [ ] İlk yayın sonrası `kaydet` ve haftalık analiz.

## İlk mesaj
Ayrıntılı devir notu: `deepspace/DEVIR.md` (yerel terminal kurulumu dahil).
> Deep Space Log'a devam ediyoruz. deepspace/DEVIR.md, SOZLESME.md G bölümü ve deep-space-log skill'ini oku,
> `py -m pytest -q` ve `py -m deepspace.gorev durum <görev klasörü>` çalıştır, sonra durumu 5 satırda özetle.
