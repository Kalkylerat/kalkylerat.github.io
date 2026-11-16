# Görev 002 · Frost Line: araştırma (G17), 16 Kasım 2026

Bütçe: `vidiq_balance` (ücretsiz, 23 kredi görünüyor) + 2 ücretli çağrı = 10 kredi. Defter:
`deepspace/buyume/vidiq_harcama.jsonl` (14:23:03 ve 14:23:05 satırları). Kanal düzeyindeki kelime ve rakip verisi
yeniden çekilmedi; `deepspace/arastirma.md` (11 Kasım) kullanıldı. Rakamlar vidIQ tahminidir; son sözü Studio verisi
söyler. 001 yalnız bir gündür yayında; kendi kanal verisi henüz karar verecek kadar değil, ilk haftalık analize kalır.

Kaynak kısaltmaları:
- **[KR]** `vidiq_keyword_research`, research, tohum "solar system ambient music", 2026-11-16 14:23 UTC
- **[OUT]** `vidiq_outliers`, long, en, "solar system planets and icy moons ambient music for sleep and focus", 20 sonuç, 2026-11-16 14:23 UTC
- **[001]** `deepspace/arastirma.md`, 11 Kasım 2026 (vidIQ, 10 çağrı)

## 1. Kelimeler

| Kelime | Aylık arama | Rekabet | Büyüme | Kaynak | Karar |
|---|---|---|---|---|---|
| space ambient music | 123K | 39 | +33% | [001] | başlıkta zaten var ("Deep Space Ambient Music") |
| space ambient | 101.8K | 50 | +53% | [KR] | başlıktaki ifadenin içinde, büyüyor |
| space music | 117.4K | 30 | +52.6% (US %17, VN %12, BR %10) | [KR] | büyüyor, düşük rekabet; başlık ifadesinin içinde, etiket |
| ambient space music | 8.6K | 28 | (kayıt yok) | [KR] | etiket |
| deep focus music | 716K | 35 | | [001] | başlıkta ("Deep Focus") |
| ambient music for sleep | 32K | 35 | | [001] | başlıkta ("for Sleep") |
| space sleep music | 7K | 36 | | [001] | etiket |
| sci fi ambient music | 25.7K | 27 | +65% | [001] | etiket |
| solar system ambient music | <750 | 84 | (kayıt yok) | [KR] | **başlığa girmez**: arama yok, rekabet çok yüksek |
| solar system | 305K | 68 | (kayıt yok); pazar IN %20, PK %15, BD %7 | [KR] | **başlığa girmez**: eğitim/çocuk araması |
| solar system song | 17.1K | 60 | +96.1% | [KR] | çocuk şarkısı araması, bizim kitle değil |
| solar system for kids | 9.3K | 40 | (kayıt yok) | [KR] | aynı; "made for kids" sinyalinden uzak dur |

Not: [KR] çıktısında "büyüme yok" değerleri, vidIQ'nun notuna göre bilinmiyor değil, ±%30'dan az değişim demektir.
"relaxing and sleeping" -80.1% [KR] düşüşte, kullanılmaz.

Sonuç: "Solar System" kelimesi hacimli ama arayan kitle çocuk/eğitim; başlığa koymak yanlış izleyiciyi çeker ve
düşük izlenme süresi getirir. Güneş Sistemi bilgisi açıklamanın ilk satırlarında (`ozet` zaten "crosses the Solar
System" diyor), bölüm adlarında (Saturn, Europa, Pluto... aramada key moments) ve etiketlerde kalır. "icy moons" ve
"frost line" ölçülmedi (bütçe); yalnız açıklama/etiket için, başlık için değil.

## 2. Başlık

- **Seçilen (0):** `Frost Line | Deep Space Ambient Music for Sleep & Deep Focus (2 Hours) · Mission 002` (84 karakter).
  G1 kalıbının aynısı; 001 ile karşılaştırılabilir kalsın diye başlıkta değişiklik yok (bir kerede tek değişiklik,
  youtube skill §6). Kelimeleri [001] ve [KR]'deki büyüyen "space ambient" ve "space music" ile örtüşüyor. Sanatçı ya da
  film adı yok (G5).
- **Aday (1), şimdi kullanılmaz:** `Frost Line: Icy Worlds | Deep Space Ambient Music for Sleep & Deep Focus (2 Hours) · Mission 002`
  (96 karakter). Görev adı yuvasını uzatır, kapaktaki `002 FROST LINE` ile ayrışır ve "icy worlds" ölçülmedi. 001 ve 002
  Studio verisi geldikten sonra ilk başlık testi adayı olarak saklanır.
- [OUT]'ta öne çıkan bir Saturn videosu başlığında "real images" diyor; bizim görsellerimiz sanatçı yorumudur
  (G14 "ARTIST'S IMPRESSION"), böyle bir ifade kullanılmaz (G9).

## 3. Kapak: hangi 3 parça

Öneri: taslaktaki üçlü kalır, sıra değişir → `kapak_parcalari = [10, 7, 18]`.

1. **kapak_1 = Saturn (10, yörünge kadrajı).** [OUT]'taki 20 videonun 3'ü halkalı dev gezegen kapağıyla öne çıkıyor:
   Saturn konulu 4 saatlik video 12.3K izlenme, kanal ortalamasının 2.9 katı, 4.3 izlenme/saat; halkalı dev
   gezegenli 1 saatlik video 7.9K, 1.6x; halkalı dev gezegenli 1.5 saatlik video 1.3K, 2.4x. Telefonda en tanınır siluet.
2. **kapak_2 = Europa (7, buz ufku).** Sahibinin seçtiği "karanlık ufuk + gökyüzünde tek dev gök cismi" hissine
   ([001] §5–6) en yakın durak: buz ufkunun üstünde dev Jüpiter. Okyanus teması [OUT]'ta da var (2 saatlik okyanus
   temalı uzay videosu 4.1K, 1.6x). Sahne isteminde Jüpiter göğe hâkim olursa en güçlü varyant olabilir.
3. **kapak_3 = Pluto (18, buz ufku).** Görevin hedefi (`hedef = "Pluto"`), kapaktaki veri satırıyla uyumlu
   (hedef, uzaklık 5.5 light-hours); tanınır ad.

Titan (12) düşünüldü ama okyanus türü `ufuk_pus` (G6) puslu ve düşük kontrastlı olur; kapakta zayıf. Kapakta seri adı
ya da süre yazılmaz (G7): yalnız `002 FROST LINE`, alt veri satırı ve imza. Test & Compare kazananı belirler; bu
sıra yalnız ilk görünen kapağı seçer.

## 4. Yayın günü ve saati

- **Gün: pazar.** 001 pazar (15 Kasım) yayına girdi. Haftalık ritim için aynı gün; ilk ölçümler gelmeden gün
  değiştirmek ikinci bir değişken olur.
- **Saat: 17:00 UTC** (12:00 ET, 09:00 PT, 18:00 CET, 14:00 BRT, 20:00 TR). Sahibinin 001 için onayladığı plan saatiyle
  aynı (`DEVIR.md`, onay 2026-11-17T17:00:00Z). En büyük bilinen pazar ABD ("space music" US %17, "space ambient" US %13
  ve FR %13 [KR]): video ABD öğleden sonrası ve Avrupa akşamından önce işlenmiş ve dizinlenmiş olur, başlıktaki uyku
  dinleyicisinin akşamı ile pazartesi sabahı odak oturumu aynı ilk 24 saate girer.
- **Hedef tarih:** 2026-11-22 pazar. Suno indirme hakkı 18 Kasım'da yenilenince 6–20. parçalar, ardından görsel,
  video, Fable ve sahibinin `ok`u gerekiyor (G8: karar en az 24 saat önce). Yetişmezse ara gün değil, 2026-11-29 pazar
  17:00 UTC.
- Saat testi ancak 2–3 videonun Studio verisinden (izleyicinin etkin olduğu saatler) sonra yapılır.

## 5. Açık noktalar

- "icy moons", "frost line", "planets ambient music" ölçülmedi (2 çağrı sınırı); ilk haftalık analizde, gerekirse
  27 Kasım dönem yenilemesinden sonra.
- [OUT] sonuçlarının çoğu 8–12 saatlik uyku videosu (ör. 4.7K aboneli kanalda 11:54:55, 30.5K izlenme, 9.8x): bu,
  askıdaki Deep Sleep serisinin talebini gösteriyor; yeni seri sahibinin kararıdır, burada öneri yok.
