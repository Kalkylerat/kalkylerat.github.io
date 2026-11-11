---
name: gorsel-dili
description: Deep Space Log görsel dili. Sahne görseli (gorsel/NN.png), görsel istemi, kapak, arayüz (HUD), kayıt kartı, banner ya da profil tasarlanırken, istemi yazılırken, yeniden üretilirken veya denetlenirken (G13) önce bunu oku.
---

# Deep Space Log: görsel dili

Görsel departmanının tek kural kitabı. Kaynakları toplar, yenisini icat etmez: `SOZLESME.md` G1, G5, G6, G7, G13, G14,
G16; `deepspace/marka.toml`; `deepspace/gorsel_denetim.py`; `deepspace/kapak.py`; `deepspace/defter.py`.
Çelişki olursa sözleşme geçerlidir (G16); çelişkiyi şefe bildir, kendin çözme.
Onaylı tek örnek sahne: `deepspace/gorevler/001-trappist/gorsel/17.png`. Kararsız kaldığında ona bak.

## 1. Tek cümle

Her görsel, PROBE-7'nin kamerasının gerçek bir durakta gördüğüdür: karanlık, durgun bir yabancı ufuk ya da yörüngeden
bir görünüm ve tek büyük gerçek gök cismi. Sahnede insan, araç, sonda, iniş aracı, uzay aracı, bina, makine, iz yok
(sahibi: "araç Dünya'ya benziyor"). PROBE-7 yalnız arayüzde ve marka işaretinde görünür. Görsel durağandır; yalnız
arayüz hareket eder (G14). 16:9, genişlik ≥2560 px. Referanslar histir, kopyalanmaz. Sanatçı, film, oyun, stüdyo adı
hiçbir istemde ve metinde geçmez (G5).

## 2. Sahne grameri

Üç kadraj vardır. Her parça birini seçer.

| Kadraj | Ne zaman | Yerleşim |
|---|---|---|
| **Ufuk** | Yüzeyine inilebilen dünya (`kayalik`, `buz`, sıvısı gözlenmiş `okyanus`) | Ufuk çizgisi düz, üstten %58–70'te (zemin karenin alt %30–42'si). Karenin ortasından geçmez. Yıldız ufka yakın bir yanda, büyük komşu cisim karşı yanda yukarıda. |
| **Yörünge** | Gezegen ve uydular, `gaz` devleri | Ana cisim merkezden kaymış. Disk çapı kare yüksekliğinin %45–110'u: ya nefes payıyla tam disk ya da kareyi kesen büyük bir kenar yayı. Gündüz-gece sınırı görünür. |
| **Derin uzay** | `yildiz`, toz diski, küçük cisim | Yıldız üçte bir çizgisinde, disk kare yüksekliğinin en çok %25'i. Gerisi yıldız alanı. |

- **Tek özne.** Karede bir ana cisim vardır; ikinci cisim en çok bir tane ve belirgin küçük. Sıra hâlinde gezegenler
  gibi çoklu öğe yalnız gerçek sistem bunu gerektiriyorsa (ör. yedi gezegenli sistemin dış kenarı).
- **Boşluk.** Karenin en az yarısı sakin karanlıktır. Boşluk başlık için değil, his içindir; doldurma.
- **Parlak odak.** Her karede tek parlak odak olur (yıldız, hilalin aydınlık kenarı, buz parıltısı). Odaksız, tamamen
  siyah kare açık temalı akışta kaybolur ve teknik kapıdan kalır.
- **Sakin bölgeler** (arayüz buraya gelir; parlak odak ve ince yüksek kontrastlı ayrıntı girmez, koyu doku olur):

| Bölge | Kare içindeki yeri | Üstüne gelen |
|---|---|---|
| Alt şerit | bütün genişlik, alt %16 | YouTube oynatma çubuğu (G14-4) |
| Sol üst | x %0–30, y %0–20 | kanal adı, görev ve cisim adı, ARTIST'S IMPRESSION |
| Sağ üst | x %80–100, y %0–15 | görev saati |
| Sol alt | x %0–37, y %64–84 | kayıt kartı (yalnız parça başında) |
| Sağ alt | x %65–100, y %70–84 | sinyal çizgisi |

  Ana cisim ve odak orta bantta yaşar: x %20–85, y %15–65. 17.png bunu sağlar (yıldız x %17, y %58; hilal x %72–84,
  y %17–40).
- **Kapak okunurluğu.** Kapak aynı karenin 1280x720'ye küçültülmüş hâlidir (kırpma yok). Başlık bloğu üç yerden birine
  oturur ve arkası koyulur: sol üst (x %7–55, y %12–43), sol alt (x %7–55, y %58–90), üst orta. `kapak_parcalari` için
  seçilen üç sahnede odak bu bloğun dışında kalmalı ve üçü ayrı kadraj, ayrı renk olmalı. Deneme: kareyi 168x94'e
  küçült; özne tek bakışta seçiliyorsa kapaklıktır.

## 3. Işık ve fizik (kontrol listesi)

İstemi yazarken ve denetlerken sırayla bak:

1. Tek ışık kaynağı: adı geçen yıldız. İkinci güneş, kaynağı olmayan dolgu ışığı, kendinden parlayan zemin yok.
2. Aydınlık yüz ve hilalin dış kenarı yıldıza bakar; hilalin uçları yıldızdan uzağı gösterir.
3. Evre açıyla tutarlı: gökte yıldıza yakın duran cisim ince hilal, yıldızın karşısındaki cisim dolun.
4. Gölgeler yıldızdan uzağa düşer; yıldız ufka yakınsa gölgeler uzundur. Bütün gölgeler aynı yönde.
5. Işığın rengi yıldızın rengidir: kırmızı cüce soluk turuncu-kırmızı, Güneş benzeri sarı-beyaz, sıcak yıldız
   mavi-beyaz, uzaydan bakılan Güneş beyaz.
6. Güneş Sistemi'nde Güneş'in boyutu uzaklıkla küçülür: Ay'da küçük beyaz disk, Mars'ta daha küçük, Jüpiter ve
   Satürn'de minik parlak disk, Uranüs ve ötesinde yalnız en parlak nokta. Uzakta ışık soluk ama gölge yine serttir.
7. Havasız cisimde gök ufka kadar siyah, gölge sert, ufukta parıltı yok. Ufuk parıltısı ve yumuşak ışık yalnız gerçek
   atmosferi olan cisimde (ince pus: Mars, Plüton; kalın pus: Titan, orada yıldız da görünmez).
8. Yıldızlar keskin, kıpırtısız noktalardır: ışın haçı, çizgi, kayan yıldız, göktaşı izi yok (G14-1).
9. Bir cismin karanlık yüzünün içinden yıldız görünmez; disk arkasındaki yıldızları örter.
10. Yıldız diski tam yuvarlaktır; ufukta basık ya da oval olmaz.
11. Sıvı yalnız gözlenmiş yerde: Titan'ın metan denizi. Başka hiçbir yüzeyde deniz, göl, akarsu, ıslak yansıma yok.
    Yüzeyi bilinmeyen `okyanus` türü ötegezegen yalnız yörüngeden gösterilir.
12. Dünya çağrışımı yok: bitki, kar örtülü sıradağ, hava bulutu, mavi gök, sis, akarsu vadisi, kumsal.
13. Gerçek cismin ayırt edici özelliği doğru: Satürn'ün halkası, Io'nun sarısı, Iapetus'un iki rengi. Ekrana ya da
    isteme giren olgu `bilgi_kaynak.json` ile uyuşur; emin değilsen bilgi doğrulayıcıya sor, uydurma.

## 4. İstem şablonları (İngilizce)

**Birleştirme.** `gorev.toml` içindeki `gorsel_istem` yalnız sahneyi anlatır. `py -m deepspace.gorev gorseller <klasör>`
her isteme `marka.toml [gorsel] stil_eki` metnini kendisi ekler (`GORSEL.md`). Bu yüzden `gorsel_istem` içine stil
kelimesi (photorealistic, cinematic, 16:9, ultra detailed) ve genel yasak listesi (no people, no text) yazma; iki kez
yazılan yasak, yasaklanan şeyi çağırır. `gorsel_istem` 35–60 kelime, şu sırayla: kadraj, özne, yıldızın yeri/boyu/rengi,
aydınlık yan ve gölge yönü, gök, varsa tek ikincil cisim. Renkler kelimeyle yazılır, onaltılık kod yazılmaz.

Kaçınılacak tetikleyici kelimeler (araç, insan ya da arayüz üretir): `standing on`, `landing site`, `probe`, `camera`,
`mission`, `station`, `window`, `cockpit`, `explorer`, `outpost`, `telescope view`. Dünya üreten kelimeler: `shore`,
`beach`, `valley`, `meadow`, `lake`, `snow`, `clouds`, `sunset`, `dusk`. Yerlerine `plain`, `ridge`, `limb`,
`terminator`, `twilight line` kullan.

Yer tutucular: `{STAR}` aşağıdaki ölçek tablosundan, `{SIDE}` left ya da right, `{OPP}` karşı yan,
`{SURFACE}`, `{BODY}`, `{COMPANION}` gerçek cismin tarifi.

`{STAR}` ölçeğe göre:

| Ölçek | `{STAR}` |
|---|---|
| Güneş Sistemi, Ay–Mars | `the small white Sun` |
| Güneş Sistemi, Jüpiter–Satürn | `the distant Sun, a tiny brilliant white disc` |
| Güneş Sistemi, Uranüs ve ötesi | `the Sun, only the brightest star-like point in the sky` |
| Yıldız sistemi, kırmızı cüce | `a dim orange-red dwarf star` (iç gezegende `large in the sky`, dıştakinde `small`) |
| Yıldız sistemi, Güneş benzeri | `a yellow-white star` |
| Yıldız sistemi, sıcak yıldız | `a brilliant blue-white star` |

```text
kayalik · ufuk
A vast dark {SURFACE} plain, bare rock and dust, completely empty to the horizon. {STAR} sits low on the {SIDE}
horizon; rocks are rim-lit on their {SIDE} sides, long hard shadows stretch to the {OPP}. High on the {OPP},
{COMPANION} hangs as a crescent lit on its {SIDE} edge. Airless black sky down to the horizon.

kayalik · yörünge
Orbital view of {BODY}, {SURFACE}, placed off-centre on the {OPP} of the frame, lit from the {SIDE} by {STAR};
the lit side faces {SIDE}, a clear terminator, the night side pure black and hiding the stars behind it.
Deep black starfield.

buz · ufuk
A vast frozen plain of {SURFACE} ice crossed by low ridges and fractures, bone-dry, nothing liquid.
{STAR} rests low on the {SIDE} horizon; ridge crests catch its light on their {SIDE} sides, long shadows to the
{OPP}. {COMPANION} hangs large on the {OPP} as a thin crescent lit on its {SIDE} edge. Black sky.

buz · yörünge
Orbital view of {BODY}, smooth pale ice with {SURFACE}, off-centre, lit from the {SIDE} by {STAR}; the lit
crescent faces {SIDE} and is tinted by the star's colour, the rest in black shadow. Deep black starfield.

okyanus · yörünge (yüzeyi bilinmeyen ötegezegen)
Orbital view of {BODY}, a dark ocean world under thin cloud bands, off-centre, lit from the {SIDE} by {STAR};
one small glint of starlight on the ocean near the lit limb, a thin atmosphere line on the edge, the night
side black. Deep black starfield.

okyanus · ufuk (yalnız sıvısı gözlenmiş cisim, ör. Titan)
A dark, perfectly still {SURFACE} sea meets a low shoreline of rounded pebbles under a thick uniform haze.
The sky is a dim even {SURFACE} glow with no stars; {STAR} is only a faint pale disc behind the haze on the
{SIDE}. Soft diffuse light, no hard shadows, no waves, no surf.

gaz · yörünge
Seen from close orbit, {BODY} fills the {OPP} two thirds of the frame: {SURFACE} cloud bands, lit from the
{SIDE} by {STAR}; the bands fade across a soft terminator into black night. {COMPANION}. Deep black sky.

yildiz · derin uzay
View from deep space: {BODY}, a perfectly round disc with a soft even glow, placed at one third from the
{SIDE}, small in a vast frame. {COMPANION}. Everything else is deep black space with countless pin-sharp stars.
```

- Uydudan görülen gaz devi, uydunun türüyle yazılır (`buz · ufuk` ya da `kayalik · ufuk`), dev `{COMPANION}` olur.
- `gorev.toml` içindeki `tur` yanlış sahne çağırıyorsa (ör. `okyanus` yazıp kuru bir ova istemek) şablonu sahneye göre
  seç ve farkı şefe yaz; `tur` alanını kendin değiştirme.
- Derin uzay karelerinde teknik kapıya dikkat (bölüm 8): yoğun yıldız alanı ve hafif toz ışığı simsiyah alanı %75'in
  altında tutar; küçük disk yanık alanı %8'in altında tutar.

## 5. Renk ve ton

- **Parça paleti** (`palet`, dört renk, koyudan açığa): 1 gök siyahı, 2 gölge, 3 yüzeyin ya da cismin orta tonu,
  4 en parlak ışık (yıldız, hilal kenarı). Kod bu alanı kullanmaz; istem yazarının renk pusulasıdır. 3. ve 4. rengi
  kelimeye çevir (`rust-red`, `pale salmon`, `cold white`), 1. ve 2. zaten stil ekindeki derin siyahtır.
- Karede tek renk ailesi artı siyah olur. İkinci aile yalnız ikincil cismin kendi rengiyse girer (soluk mavi gezegen).
- 4. renk yıldızın rengiyle uyuşmalı; uyuşmuyorsa palet değil fizik kazanır ve şefe yazılır.
- **Marka renkleri sahneye girmez.** Mürekkep `#05070f` zemin, kehribar `#e8c48a` yalnız grafik katmanda vurgu.
  Sahneye kehribar ton atılmaz; film tonu kapalıdır (`[filtre] secim = ""`).
- Yasak: neon pembe, mor geçiş, gökkuşağı bulutsu, aşırı mercek parlaması, çizgi film doygunluğu (`marka.toml yasaklar`).

## 6. Görev tutarlılığı: 20 kare, tek seri

İstemleri yazmadan önce 20 parçalık bir **kadraj çizelgesi** çıkar (parça, kadraj, öznenin yeri, evre, renk ailesi).

- **Sabit kalan (seri hissi):** derin siyah gök, tek ışık kaynağı, tek özne, bol boşluk, durgunluk, ışığın geldiği yan.
  Işık yanı görev boyunca varsayılan olarak aynıdır (001 ve 002'de sol); çapraz geçişte ışık zıplamaz. Karşı yan en
  çok 2–3 parçada ve gerçek bir nedenle kullanılır.
- **Değişen (her kare ayrı):** kadraj, ölçek (disk %45'ten %110'a), öznenin yeri (sol üçte bir, sağ üçte bir, alttan
  kenar yayı), evre (hilal, yarım, şişkin), ufuk yüksekliği, renk ailesi. Art arda iki parça bu altısından en az
  ikisinde ayrılır.
- Aynı kadraj art arda en çok 2 kez. Bir görevde ufuk kareleri en az 6, yörünge kareleri en çok 10 olsun.
- **Kopya riski (G13):** "soldan aydınlanan disk, siyah zemin" kalıbı tekrarlanırsa teknik kapı "neredeyse aynı" der.
  Yörünge karelerinde disk boyunu ve yerini parça parça değiştir.
- Her görevin bir renk imzası olur (001 kızıl cüce pası, 002 soğuk beyaz Güneş ve buz grisi). Yeni görev öncekinin
  imzasını tekrar etmez (G4).
- Üretim sırası (G11): önce 3 deneme (üç ayrı kadraj, tercihen `kapak_parcalari`), sahibinin `ok`u, sonra kalanlar.

## 7. Grafik katman: kayıt defteri dili

Marka güzel bir fotoğraftan değil defterin dilinden kurulur: mürekkep zemin, tek vurgu rengi, ince çizgi, gerçek veri.
Kod çizer; görsel modeliyle yazı ya da arayüz üretilmez.

| Öğe | Kural |
|---|---|
| Yazı | Space Mono; başlık Bold, veri Regular. Hep büyük harf, geniş harf aralığı. Başka font yok. |
| Renk | Zemin `#05070f`, başlık `#f0f0f5`, ikincil `#b8c0d0`, vurgu `#e8c48a`. İkinci vurgu rengi yok. |
| Kehribar çizgi | Başlığın altında tek ince çizgi (kapakta 2 px, 240 px). Yüzey başına bir tane; süs olarak çoğaltılmaz. |
| Köşe nişanları | Dört köşede ince L işareti (kapakta 30 px kol, kenardan 34 px). Çerçeve çizilmez. |
| Veri satırı | Yalnız gerçek, doğrulanmış veri: `TARGET · RA/DEC · DISTANCE`, ayırıcı orta nokta. Bilinmeyen alan çizgiyle boş bırakılır, uydurulmaz. |
| Telefon kuralı | En küçük yazı kare yüksekliğinin %2'si (G16): 720'de ≥15 px, 1080'de ≥22 px, 1440'ta ≥29 px. |

- **Kapak (G7, `kapak.py`):** kehribar görev numarası, altında görev adı (büyük yazı en çok 3 kelime), kehribar çizgi,
  küçük veri satırı, köşe nişanları, küçük `DEEP SPACE LOG · PROBE-7` imzası. Seri adı, süre, slogan yazılmaz. Üç
  varyant üç ayrı parçanın karesidir; aynı karenin yakınlaştırması varyant değildir.
- **Arayüz (G14, `defter.py`):** sol üstte kanal adı, `MISSION 00N · cisim adı`, `ARTIST'S IMPRESSION`; sağ üstte görev
  saati ve alım ışığı; sağ altta müziğe bağlı kehribar sinyal çizgisi. Hiçbiri alt %16'ya girmez (`ALT_GUVENLI`).
  İlk dakikadan sonra %60 opaklık.
- **Kayıt kartı:** sol altta dar koyu cam kart, ince çerçeve, solda kehribar çubuk, `PROBE-7 · ARRIVAL` etiketi; en çok
  3 satır, tam cümle, cisim adını tekrar etmez; yalnız parça başında görünür ve bütün olarak kaybolur (G14-5).
- **Banner ve profil (`deepspace/marka/taslak/defter_kiti.py`):** banner bir uçuş kaydı sayfasıdır (kanal adı,
  `PROBE-7 FLIGHT LOG`, görev tablosu, ölçekli yörünge şeması, uçuş hattı); her şey güvenli alanda (1546x423) okunur.
  Profil mürekkep zeminde kehribar yörünge halkası içinde "7"; 40 pikselde seçilir. Fotoğraf zemini, renkli simge yok.
- **Yap:** bol siyah, hizalı sütunlar, tek kalınlıkta çizgi, gerçek sayı.
  **Yapma:** parlama, gradyan, gölgeli kutu, yuvarlak balon, emoji, ikon seti, sahte veri, söz veren yazı
  ("weekly"), sahnenin üstüne çizilmiş sonda.
- Kit, `marka.toml` ya da şablon değişirse marka istasyonu yeniden denetlenir ve sahibinin onayı yenilenir (G16).
  Kod değişikliği kod ustasının işidir; görsel departmanı öneriyi şefe yazar.

## 8. Denetim listesi (G13)

Önce teknik kapı (`py -m deepspace.gorev denetle <klasör>`): genişlik ≥2560, 16:9, ortalama parlaklık 0.05–0.8, yanık
alan ≤%8, simsiyah alan ≤%75, netlik ≥1.0, aynı görevde ikiz kare yok. Sonra göz denetimi: altı paftanın hepsine ve
karenin bütününe bak. Kodlar `KONTROL_LISTESI` kodlarıdır; başka kod yazılamaz.

| Kod | Kritik | Bu kanalda ne demek |
|---|---|---|
| `istem` | evet | Adı geçen cisim yok ya da ayırt edici özelliği yanlış. Konsept ihlali: insan, araç, sonda, bina, makine, iz; Dünya manzarası (bölüm 3, madde 12); olmayan yerde sıvı (madde 11). |
| `fizik` | evet | Işık yanlış yandan; hilal yıldıza sırt dönmüş; gölge yıldıza doğru ya da iki yöne; ikinci ışık kaynağı; karanlık diskin içinden görünen yıldız; kayan yıldız ya da göktaşı izi; havada asılı kaya. |
| `yazi` | evet | Harf, rakam, logo, filigran, imza, üretilmiş arayüz ya da nişan çizgisi. |
| `anatomi` | evet | Herhangi bir canlı figürü (zaten `istem` ihlalidir; ikisini de yaz). |
| `tekrar` | hayır | İstenmemiş ikinci güneş ya da ikiz gezegen; kopyala-yapıştır doku; görevdeki başka bir kareyle aynı kompozisyon. |
| `olcek` | hayır | Eğik ufuk; uzaklığa göre fazla büyük Güneş (madde 6); evre açıyla tutarsız (madde 3); basık yıldız diski. |
| `bozulma` | hayır | Erimiş doku, siyah gökte bantlanma, plastik yüzey, aşırı keskinlik, leke gibi yıldızlar. |
| `marka` | hayır | Masalsı görünüm, neon ya da mor, mercek parlaması, yıldızlarda ışın haçı, paletten kopuk renk, sakin bölgede parlak odak (bölüm 2), boşluksuz kalabalık kare. |

**Puan (0–10).** Kritik kusur varsa puan ne olursa olsun kalır. Kritik değilse:

- 9–10: kusursuz ve kapaklık; 17.png düzeyinde ya da üstünde. 8: temiz, kusur yalnız paftada yakından görülüyor.
- 7: geçer; tek küçük kusur, tam ekranda dikkat çekmiyor.
- 5–6: kalır; kritik olmayan bir kusur tam ekranda görülüyor (bu durumda puan en çok 6). 0–4: kare seriye ait değil.

Soru sırası: (1) Sahibi buna "Dünya gibi" ya da "masal gibi" der mi? Derse kalır, gerisine bakma. (2) Işık fiziği.
(3) Yapay zekâ bozulmaları. (4) Sakin bölgeler ve kapak okunurluğu. (5) Görevin öbür kareleriyle yan yana: ikiz var mı?
Not: önceki görevde otomatik denetimin 8–9 verdiği 20 karenin hepsi sahibinden döndü; temiz piksel yetmez, önce konsept.

## 9. Bilinen hatalar ve yeniden üretim cümlesi

Kalan karenin `gorsel_istem`ine kusurun tersi açıkça yazılır, tek varyasyonla yeniden üretilir, kare başına en çok 2
kez (G13). 1. deneme: tersini istemin başına yakın ekle ve tetikleyici kelimeyi sil. 2. deneme: sahneyi sadeleştir
(ikincil cismi çıkar, tek özne bırak). Yine kalırsa dur ve şefe dön; video çıkmaz, sahibine sorulur.
Yalnız yasak eklemek yetmez: boşluğu olumlu cümleyle tarif et.

| Hata | İsteme eklenecek cümle (İngilizce) |
|---|---|
| Dünya manzarası | `An airless alien world: bare rock and dust only, no vegetation, no weather, no erosion by water; the sky is black down to the horizon.` |
| Araç, sonda, yapı | `The plain is completely empty and untouched to the horizon; nothing man-made anywhere in the frame.` (ve bölüm 4'teki tetikleyici kelimeleri sil) |
| Işık yanlış yandan | `The star is on the {SIDE}. Every lit edge, including the crescent in the sky, faces {SIDE}; every shadow points {OPP}.` |
| Hilal ters | `The crescent's bright outer edge faces the star on the {SIDE}; its horns point {OPP}; its dark side is pure black.` |
| Işın haçı, kayan yıldız | `Stars are tiny pin-sharp points with no spikes, no glints, no streaks; no shooting stars, no comets.` |
| Masalsı görünüm | `Restrained natural colour and documentary realism, like a raw spacecraft photograph; a single body in the sky, no nebula clouds, no glowing ground.` |
| Basık ya da oval yıldız | `The star is a perfectly round disc, small and sharp-edged, not squashed, not stretched along the horizon.` |
| Olmayan deniz | `The surface is bone-dry solid rock and ice: no sea, no lake, no liquid, no wet reflections, no shoreline.` |
| Güneş fazla büyük | `The Sun is tiny, only the brightest star-like point, yet it casts hard shadows.` |
| Karanlık yüzden yıldız görünüyor | `The planet's night side is a solid black disc that hides every star behind it.` |
| İkiz kare (G13) | Fiziği değil kadrajı değiştir: disk boyu, yeri, evresi (bölüm 6). |
| Fazla siyah, teknik kapı | `A dense field of faint sharp stars fills the black sky; a faint glow of starlight on the ground.` |
