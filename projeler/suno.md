# Suno müzik

**Durum (22 Ekim 2026):** skill hazır (30 Eylül–1 Ekim), kullanılıp kullanılmadığı belli değil. Kod
`claude/chrome-music-generation-9cyq2h` dalındaki `suno/` klasöründe (ana dalda yok).

## Nasıl çalışıyor
1. Bilgisayarda `claude --chrome` ile Claude Code'u aç.
2. Kurulum mesajını yapıştır: 3 dosya `~/.claude/skills/suno-muzik/` klasörüne iner (talimat, örnek istek listesi, ses
   dosyalarını taşıyan küçük betik).
3. `/exit`, sonra yeniden `claude --chrome`. Chrome'da Suno'ya kendin giriş yap.
4. Klasör yapısını istekte söyle (ör. "Tür/Yıl-Ay/Şarkı adı"); şarkılar `Music/Suno/...` altına gider.

Test isteği hazır: "Yağmurlu Sabah", Türkçe akustik pop, ~10 kredi; sözler önce onayına gelir.

## Daha büyük plan (9 Ekim, beklemede)
Her ay şarkı çıkarmak, DistroKid ile yayınlamak, manzarada canlı çekim.

## Açık işler
- [ ] Kurulumu yap ve test şarkısını üret.
- [ ] Aylık plan olacaksa tür, dil ve yayın takvimi kararı.

## İlk mesaj
> Suno müzik skill'ini kurmak istiyorum. Kalkylerat deposunun `claude/chrome-music-generation-9cyq2h` dalındaki `suno/`
> klasörüne bak ve beni adım adım kurulumdan ilk test şarkısına kadar götür.

## claude.ai sohbetlerinden
- Tercihler: minimal söz, güçlü ve kısa emirli nakarat, sokak dili ölçülü, özgüvenli ve eşit anlatıcı; "aura" teması;
  satır başına 8 hece, tam kafiye, günlük Türkçe, yapay zekâ klişesi yok; kendi kendini denetleyen döngü istemi.
- Çıktı biçimi: etiketli bölümler (verse, pre-chorus, chorus, bridge) ve şarkı başına ayrı kopyalanabilir stil istemi.
- Fikir: ayda ~20 Suno şarkısı, DistroKid'de sanatçı adıyla yayın, güzel manzarada çalıp YouTube'a çekim.
- Resmî olmayan Suno API sarmalayıcıları (hesap çerezi, kural ihlali riski) reddedildi; resmî API davetli ortaklara açık.
- Görev başına stil, söz ve kredi tavanını (örn. 250) sahibi belirler; sözleri kendisi denetler.
