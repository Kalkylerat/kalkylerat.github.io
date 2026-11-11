# Büyüme dosyaları (YouTube uzmanı, G17)

Yazan: YouTube uzmanı ajanı (`.claude/agents/youtube-uzmani.md`). Kurallar: `.claude/skills/youtube/SKILL.md` §8.

## Görev başına: `<görev>/buyume/`

`oneriler.json` (araştırma istasyonunun çıktısı; denetçi kararına girer):

```json
{
  "kelimeler": ["sci fi ambient music", "space ambient music"],
  "basliklar": ["<aday 1, en çok 100 karakter>", "<aday 2>"],
  "secilen": 0,
  "seri": "focus",
  "yayin_saati_utc": "14:00",
  "kaynaklar": [{"arac": "vidiq_keyword_research", "zaman": "2026-11-12T10:00:00Z", "not": "25.7K/ay, +65%"}]
}
```

- `metin.uret` `basliklar[secilen]` başlığını G5'ten (≤100 karakter, yasak kelime yok) geçerse kullanır; geçmezse
  seri şablonu kullanılır ve `youtube.json`'a `"baslik_kaynagi": "sablon"` yazılır.
- `arastirma.md`: gerekçe. Her rakamın yanında hangi çağrıdan geldiği yazar.

## Kanal düzeyi: `deepspace/buyume/`

- `hafta_<yıl>-<hafta>.md`: haftalık analiz (kendi kanal verisi, rakiplerin öne çıkanları, yükselen kelimeler).
- `kararlar.json`: verilen kararlar, sonuçları gelene kadar izlenir:

```json
[{"tarih": "2026-11-18", "tur": "baslik_testi", "karar": "Başlıkta önce mekân adı", "veri": "hafta_2026-47.md",
  "durum": "sonuc_bekleniyor"}]
```

  `tur`: `baslik_testi | yayin_saati | seri_sirasi | konsept_adayi | kapak_sirasi | liste`.
  `durum`: `uygulanacak | uygulandi | sonuc_bekleniyor`.

- `vidiq_harcama.jsonl`: bütçe kancasının defteri (`deepspace/vidiq_butce.py`). Elle düzenlenmez; elle yapılan
  araştırma bir satır olarak eklenir (`"arac": "elle: ..."`).
