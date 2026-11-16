# Görev 002 · görsel denetimi (G13), G11 denemesi

16 Kasım 2026, denetçi: Claude (kontrol listesi sürüm 1). gpt-image-2, 2K taslak (2048x1152), istem = `GORSEL.md` bölüm 10, 07, 18
(sahne + `marka.toml` stil ve kadraj eki). Kararlar `denetim/NN.json` (`--taslak`); geçen taslak Lanczos + `pozla` ile son dosyaya taşınır.

Teknik ölçüm (taslak): 3/3 yalnız çözünürlük (2048 < 2560, Lanczos büyütmeyle kalkar). Parlaklık 0.11 / 0.16 / 0.24, yanık ≤ %0.6,
simsiyah %63 / %56 / %27, netlik 16 / 84 / 68. İkiz yok (parmak izi farkı 50–59).

| # | Parça | Puan | Karar | Not |
|---|---|---|---|---|
| 10 | Saturn | 8 | GEÇTİ | Soldan aydınlık, gece yüzü siyah ve arkasındaki yıldızları örtüyor; halka geometrisi tutarlı (ön yüz diskin önünde, arka yüz sağ kenarda yeniden çıkıyor). Yazı, araç, ışın haçı yok. Küçük: sağdaki halkalar keskin gezegen gölgesi yerine yumuşak geçişle kararıyor; alt %16'da diskin orta tonlu alt kenarı. |
| 07 | Europa | 4 | KALDI | `istem`: çokgen çamur çatlağı deseni + güneşten inen ıslak parlak yansıma şeridi + sıcak gün batımı tonu = tuz gölü (Dünya). `olcek`: Jüpiter ~%55 aydınlık; Güneş'e ~55–60° uzakta, hilal olmalı (aydınlık yan sola, yön doğru). `marka`: Güneş büyük ve turuncu haleli; Jüpiter'in gece yarısı siyah değil. |
| 18 | Pluto | 3 | KALDI | `istem`: Dünya'nın yörüngeden fotoğrafı gibi (eğri gezegen kenarı, parlak mavi atmosfer bandı, buz tabakası + kıyı şeridi gibi dağlar, ıslak parlak yansıma); ufuk kadrajı değil, havadan bakış. `marka`: Güneş 8 kollu ışın haçı ve hale ile. `olcek`: ufuk eğri ve y %51'de; Güneş yüksekte ve büyük. Charon yok (doğru). |

Yönetmene öneri (rehber bölüm 9 cümleleri; son metin yönetmenindir):

- 07: `The surface is bone-dry solid rock and ice: no sea, no lake, no liquid, no wet reflections, no shoreline.` + yüzeyi Europa'ya
  özgü tarif et (ör. matte frost-dulled ice crossed by long straight double ridges and dark reddish-brown bands), "cracked" kelimesini
  çıkar. `Jupiter hangs as a crescent lit on its left edge; its night side is pure black.` (istemdeki "nearly full" fiziğe aykırı.)
  `The Sun is tiny, a small sharp white disc with no glow, yet it casts hard shadows.`
- 18: "heart-shaped" havadan harita bakışı çağırıyor; çıkar. Düz, alçak ufuk iste (`a straight flat horizon, the ground fills the
  bottom third`), `a thin blue haze line hugs the horizon; the sky above is black`. `The Sun is tiny, only the brightest star-like
  point, yet it casts hard shadows.` + `Stars are tiny pin-sharp points with no spikes, no glints, no streaks; no shooting stars,
  no comets.` + 07'deki kuru yüzey cümlesi.
- Şefe: iki buz karesinde de ıslak parlak yansıma çıktı; `ufuk_buz` ekindeki "the ice reflects far more light than rock, clean and
  bright" ifadesi parlak cam/su yüzeyini çağırıyor olabilir (marka kiti, G16; denetçi değiştirmez).

## Tur 2 (16 Kasım 2026, 1. yeniden üretim: 07, 18)

Aynı denetçi, bağımsız göz denetimi; tur 1 dosyaları `gorsel/taslak/tur1/`. Teknik (taslak): yalnız çözünürlük (2048 < 2560,
Lanczos büyütmeyle kalkar). Parlaklık 0.18 / 0.25, yanık %0, simsiyah %63 / %61.

| # | Parça | Puan | Karar | Not |
|---|---|---|---|---|
| 07 | Europa | 6 | KALDI | Konsept ve fizik temiz: tuz gölü ve ıslak şerit kalktı, ufuk düz (y %64), Güneş küçük beyaz (x %9, y %58; küçük yumuşak hale, ışın yok); ince hilal Güneş'e yakınlıkla tutarlı, aydınlık kenar sola-sol alta Güneş'e bakıyor, uçlar sağa, gece yüzü siyah, içinden yıldız görünmüyor. `marka`: hilal sol üst sakin bölgeye giriyor (aydınlık kenar x %14–20, y %5–20); 1080p arayüz benzetiminde üç satırın üçü de hilalin parlak kenarının üstüne biniyor. Hilalin tamamı x ≥ %30 ya da y ≥ %20'de olmalı, Güneş'e yakın ve solda kalarak. Küçük: çift sırtlar çökük hendek gibi. |
| 18 | Pluto | 5 | KALDI | Düzelenler: göz hizası, düz ufuk (y %70), ince mavi pus çizgisi, yıldızlar keskin, Charon yok, ıslak yansıma yok. `istem`: Dünya tuz düzlüğü çağrışımı; ova özelliksiz beyaz-krem kabuk (Sputnik'in çokgen hücreleri ve çukurları yok), sağdaki dağlar sudan aşınmış çöl sıradağı gibi ağaçsı oluklu ve oluklarında kar gibi beyaz şeritler var. `olcek`: Güneş alçakta ama ovada uzun gölge yok. `marka`: Güneş'te belirgin hale. |

Şefe: 18 isteminde tetikleyici `Standing on` duruyor (bölüm 4; bu turda figür üretmedi). Kare başına 1 yeniden üretim hakkı kaldı.

## Tur 3 (16 Kasım 2026, 2. ve son yeniden üretim: 07, 18)

Aynı denetçi, bağımsız göz denetimi; tur 2 dosyaları `gorsel/taslak/tur2/`. Teknik (taslak): yalnız çözünürlük (2048 < 2560,
Lanczos büyütmeyle kalkar). Parlaklık 0.19 / 0.21, yanık %0, simsiyah %60 / %53, netlik 232 / 150. İkiz yok (parmak izi farkı 47–69).

| # | Parça | Puan | Karar | Not |
|---|---|---|---|---|
| 07 | Europa | 5 | KALDI | Düzelenler: hilal yazı bölgesinden çıktı (x %21–31, y %26–36); ince hilal Güneş'e ~20° yakınlıkla tutarlı, aydınlık dış kenar sol alta Güneş'e (x %10, y %58) bakıyor, uçlar sağa-yukarı, gece yüzü siyah; ufuk düz (y %62); sırt gölgeleri sağa-öne. `istem`: sol öndeki iki çift sırt (x %20–60, y %65–100) ufka koşan dar, eşit aralıklı, tırtıllı paralel şeritler; tam ekranda ve 168x94'te kardaki araç/lastik izi gibi okunuyor (km ölçekli kabarık sırt yerine metre ölçekli iz). Güneş'in altında dalgacıklı dikey parlak yansıma sütunu (x %0–25, y %62–75) ıslak buz/su parlaması gibi; kuru, mat buz değil. `marka`: bu sütun sol alt kayıt kartı bölgesine giriyor; Güneş'te küçük hale. Küçük: zeminde ızgara dokusu. |
| 18 | Pluto | 5 | KALDI | Düzelenler: çokgen hücre ve çukur var, sağdaki dağlar köşeli eğik bloklar (oluk ve kar şeridi yok), ince mavi pus çizgisi, yıldızlar keskin, ıslak yansıma ve Charon yok. `istem`: tuz kabuğu gitti, yerine Dünya'nın kurumuş göl yatağı geldi: birkaç metrelik, kenarları kalkık koyu çatlaklarla ayrılmış çokgen levhalar (çamur çatlağı). Sputnik hücreleri onlarca km; göz hizasından ufka kadar en çok bir iki oluk görünmeli. `olcek`: Güneş ufukta (x %5, y %52) ama ovada uzun ince gölge yok, zemin önden ufka eşit aydınlık; ufuk y %57 (alt sınır %58). Küçük: zeminde ızgara dokusu, Güneş'te küçük hale. |

Şefe: iki kare de 2 yeniden üretimden sonra kalıyor (G13, bölüm 9): dur, video çıkmaz, sahibine sorulur. Ortak kök: göz hizası
ufuk kadrajında model gerçek yüzey yapısını (çift sırt, Sputnik hücresi) metre ölçeğinde çiziyor ve Dünya izi/çamur çatlağı
çıkıyor. 10 (Saturn) GEÇTİ olarak duruyor.
