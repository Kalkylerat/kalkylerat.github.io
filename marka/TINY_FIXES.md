# Tiny Fixes: marka ve hesap rehberi

Üçüncü hesap (X ve Instagram, İngilizce, yapay zekâ). Konsept: **trend olan küçük sorunlara denenmiş yapay zekâ çözümleri
("Fix") ve yapay zekâ haberleri kaynaklarıyla ("News")**; evergreen komut kartları ("Library") otomatik. Kurallar:
SOZLESME.md F bölümü. Kod: `bot/flood*.py`. Sahibin adımları: `TINY_FIXES_KURULUM.md`.
Mod: `ayarlar.toml` → `[flood] mod` (varsayılan `kapali`).

## Neden bu isim (15 Ekim 2026)

Sahibi "tatlı, sorun çözen, şirin" bir isim istedi, karakter olmadan. Önceki çalışma adı "Prompt Proof" doğru ama soğuk ve
teknikti. **Tiny Fixes** seçildi çünkü:

- İsim vaadi söyler: her post *küçük bir düzeltme*. Yeni gelen biri ilk saniyede ne alacağını anlar (büyümede en önemli şey).
- "Tiny" sevimli ve iddiasız; "fix" sorun çözer. Abartı dili kullanmayan, dürüst sesimizle (F2, F3) uyumlu.
- Seri kurmaya uygun: "Tiny Fix #12", "today's tiny fix". Kısa, yazımı kolay, Türkçe konuşan biri için de okunur.
- Araştırma (15 Ekim 2026): "Solvy" ve "Fixie" yapay zekâ ürünlerinde kullanılıyor (karışıklık riski). "TinyFix" adında küçük
  bir iPhone onarım programı var; biz çoğul ve iki kelime ("Tiny Fixes") ve içerik hesabıyız, karışma riski düşük.
  Kullanıcı adının boş olup olmadığını bu ortamdan kontrol edemedim: hesap açarken siz deneyeceksiniz (aşağıdaki sıra).

## Görsel kimlik

Karakter yok; işaret **küçük bir yara bandı ve bir pırıltı**. Görseller bu klasörde, yeniden üretmek için
`python -m bot.flood_gorsel`.

| Dosya | Nerede | Boyut |
|---|---|---|
| `tiny_fixes_logo.png` | X ve Instagram profil fotoğrafı (aynısı) | 1080×1080, daire kırpmada kesilmez |
| `tiny_fixes_x_kapak.png` | X başlık görseli (banner) | 1500×500 |
| `tiny_fixes_one_cikan_start/fixes/news/library.png` | Instagram öne çıkan hikâye kapakları | 1080×1920 |
| `tiny_fixes_tanitim_1..4.jpg` | İlk Instagram postu (carousel) ve X sabit postunun görseli | 1080×1350 |

Instagram'da banner yoktur: profil fotoğrafı + biyografi + öne çıkanlar + ilk 3 post profilin "vitrini"dir.

| Renk | Kod | Kullanım |
|---|---|---|
| Krem | `#FFF6EA` | zemin |
| Mürekkep | `#22223B` | yazı |
| Nane | `#5ED3A8` | ana vurgu, logo zemini |
| Mercan | `#FF7A6B` | çağrı düğmeleri, bant pedi |
| Güneş | `#FFC94D` | pırıltı |

Yazı tipi: Bricolage Grotesque (başlık ve metin), DejaVu Sans Mono (komut kartı).

## Hesap bilgileri (kopyala-yapıştır)

| Alan | Değer |
|---|---|
| İsim (Name) | `Tiny Fixes` |
| X kullanıcı adı | sırayla dene: `@tinyfixes`, `@tinyfixes_ai`, `@tinyfixesai`, `@gettinyfixes`, `@tinyfixesdaily` |
| Instagram kullanıcı adı | sırayla dene: `tinyfixes`, `tinyfixes.ai`, `tinyfixes_ai`, `tinyfixesdaily` (X ile aynısı tercih edilir) |
| Dil | English |
| Kategori (Instagram) | Creator → "Education" ya da "Science & Technology" (hangisi varsa) |

### X biyografisi (≤160) ve web sitesi alanı

```
Small AI fixes for real problems. Every prompt tested before we post it. Free pack of tested prompts below.
```

Web sitesi alanı: `kalkylerat.github.io/tinyfixes`

### Instagram biyografisi (≤150)

```
Small AI fixes for real problems 🩹
Every prompt tested before we post.
Free pack of 10 tested prompts ↓
```

Profil bağlantısı: `https://kalkylerat.github.io/tinyfixes` (Instagram'da caption'daki link tıklanmaz; tek tıklanabilir
adres budur).

### Sabitlenecek X postu (elle at, profilde sabitle; görsel: `tiny_fixes_tanitim_1.jpg`)

```
Hi, we're Tiny Fixes.

Each day we take a problem people are searching for and fix it with an AI prompt. We run the prompt first, name the model, and say where it fails.

AI news only runs when two independent sources confirm it.
```

### İlk Instagram postu (elle; 4 görsel `tiny_fixes_tanitim_1..4.jpg`, bu sırayla)

```
Small AI fixes for real problems.

Every prompt here is run on a real AI model before we post it. We name the model and tell you where it fails. News only runs with two independent sources.

Save the fixes you need, and send one to a friend who's stuck.
```

## Who is speaking (voice notes; the writer model reads this section)

Tiny Fixes is a kind, upbeat friend who tests things before recommending them. Warm, plain and specific. Never a guru, never
a hype account, and with no invented biography. The account speaks as "we".

- Short sentences. Everyday words. Contractions are fine. A little warmth is good ("small fix, big relief"), no jargon.
- Say what was actually done: "we ran it", "tested with Claude Sonnet 5.5", "it put the maps app first". Never "I've been
  using this for months", never clients, followers' results or years of experience.
- Every piece admits one limit in one plain line: "It only knows what you paste."
- A weak result is shown as weak. If a prompt failed, that is the post.
- Quote at most two short lines of a real output. Never invent a number, version, date or price.
- No hype: no "game-changer", "insane", "mind-blowing", "changes everything", "you won't believe".
- No bait ("RT if", "reply YES"). One calm ask at the end: save it, or follow for the next tiny fix.
- News: what happened, what it means for a normal person, what to do now. Two independent sources or it does not run.
- Stay away from health, law, money advice, politics, tragedies and claims about named people.
- On X: no emojis, no exclamation marks. On Instagram: at most one emoji in the caption, never on slides.

Example lines in this voice:

- "Battery draining after the update? We ran a prompt that ranks the likely causes from your own stats."
- "Tested with Claude Sonnet 5.5 on made-up stats. It put the maps app first and said what to check."
- "The limit: it only knows what you paste. It can't read your phone."
- "Tiny fix, saved for the next update."
- "Two sources confirm the release. Only one confirms the price, so we left the price out."

## Değişmez kurallar (SOZLESME.md F bölümü)

- Her olgu en az 2 bağımsız alan adından kaynaklı, yazar rakam uyduramaz (F1). Fix komutu gerçekten çalıştırılır ve
  postta hangi modelle denendiği yazar (F2). Sahte kişisel deneyim yok (F3). Link ana postta yok, affiliate yalnızca
  yanıtta/profilde ve etiketli (F4). Sağlık, hukuk, para tavsiyesi, trajedi, siyaset ve kişi iddiaları yok (F5).
- Trend içerik sahibin `ok` cevabıyla çıkar (F6). Başkalarına otomatik yanıt, etiket, DM, takip, beğeni yok (F7).
- Günde en fazla 4 birim (flood bir birim), Instagram en fazla 3 (F8). Varsayılan mod `kapali` (F9).
- Ölçümden öğrenme yalnızca sıralama ve öneri yapar, hiçbir kuralı gevşetmez (F10).
- X'te "Automated" etiketi açık olmalı (X ayarı, sahibi yapar).

## İş planı ve gelir modeli (sahibinin kararı, 15 Ekim 2026: "önce para")

X ve Instagram **trafik getirir**; para **kendi sitemizden** gelir. Takipçi eşiği beklemeden ilk günden çalışır.

```
X flood / Instagram carousel ──► profil bağlantısı ──► kalkylerat.github.io/tinyfixes
   (son post: "Free pack: link in our profile")          │
                                                          ├─ e-posta formu (Kit) ──► ücretsiz paket (10 komut) ──► haftalık bülten
                                                          ├─ ücretli paket (Lemon Squeezy, $9, ~60 denenmiş komut)
                                                          └─ her çözümün kendi sayfası (aramadan gelen trafik) + etiketli affiliate
```

| Parça | Araç | Maliyet | Kim yapar |
|---|---|---|---|
| Site | GitHub Pages (`docs/tinyfixes/`) | 0 | bot, her yayından sonra (`flood_site`) |
| E-posta listesi | Kit (10.000 aboneye kadar ücretsiz) | 0 | form ve hoş geldin e-postası bir kez sahibi kurar |
| Ücretsiz paket | PDF, 10 denenmiş komut | ~$0.40 tek sefer | bot (`flood_paket`), sahibi Kit'e yükler |
| Ücretli paket | Lemon Squeezy (aylık ücret yok, satış başına %5 + 50¢, KDV'yi kendisi öder) | satıştan | bot üretir, sahibi yükler |
| Bülten | Kit broadcast | 0 | bot taslağı Pazartesi raporunda, sahibi gönderir (2 dk) |
| Gelir takibi | Kit ve Lemon Squeezy API (yalnızca okuma) | 0 | bot, Pazartesi raporu |

Neden bu yapı:
- **Liste bizim malımız.** X ya da Instagram erişimi düşse de abonelere ulaşırız. Gelirin çoğu listeden gelir.
- **Ürün içerikten çıkar.** Zaten denediğimiz komutlar pakete girer; ek iş yok, tema başına ~$0.04.
- **Güven = satış.** "Tested with <model>" ve açık sınır cümlesi (F2) paketin satış argümanıdır; sahte aciliyet, sahte
  yorum yok (F11). Para kuralı ile içerik kuralı aynı.
- **Maliyet sabit kalır.** Postlarda link yok (X'te linkli post ~$0.20); çağrı "link in our profile".

Hedefler (söz değil, ölçüt; Pazartesi raporu karar verir):

| Dönem | İçerik | Liste | Satış |
|---|---|---|---|
| 1. ay | günde 1–2 onaylı birim | ilk 100 abone | ilk satışlar |
| 3. ay | `otomatik` mod, en çok kaydedilen biçim çoğaltılır | 500 abone | haftada birkaç satış |
| 6. ay | paket v2 (en iyi postlar eklenir) | 1.500 abone | ikinci ürün kararı (ör. Notion şablonu) |

Sonra: X Original Content Rewards (Premium + 500 doğrulanmış takipçi + 90 günde 500 bin doğrulanmış görüntülenme;
otomatik hesaplara açık mı önce teyit), Instagram programları (yüksek eşikler), kendi alan adı (yılda ~$10–15; site
adresinde "kalkylerat" adı görünmesin diye, satışlar başlayınca önerilir).
