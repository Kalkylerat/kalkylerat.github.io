# Beyin fırtınası: yeni X hesabı

Üç yapay zekâ uzmanı "nasıl bir X hesabı açalım?" sorusunu tartışır ve **sahibin isteklerine en uygun fikirde
ortak karar** verir. Seçilen fikir sonra Kalkylerat gibi tam otomatik bir bota dönüştürülecek.

| Uzman | Bakış açısı |
|---|---|
| **A – Büyüme Uzmanı** | X algoritması, niş, viral formatlar, ilk 1.000 takipçi |
| **B – Gelir Uzmanı** | Hangi kanallardan, kaçıncı ayda, ne kadar para |
| **C – Otomasyon ve Risk Uzmanı** | Tam otomatik çalışır mı, veri kaynağı, X kuralları, yasal risk |

Her uzmanın uzmanlık alanları, çalışma yöntemi, sınırları ve kontrol soruları [uzmanlar/](uzmanlar/)
klasöründedir (düzenlenebilir). Yetenekleri: **web araması** (güncel fiyat, kural, rakip hesaplar) ve **sayfa
okuma** (X kuralları, API şartları gibi resmi sayfaları baştan sona okur). İddialarının yanına kaynak linki koyarlar.

## Turlar

1. **Öneri:** Her uzman, rakamları web'de doğrulayarak 2 fikir yazar (A1, A2, B1, B2, C1, C2).
2. **Denetim:** Her uzman diğer iki uzmanın 4 fikrini eleştirir.
3. **Düzeltme:** Her uzman eleştirilere göre kendi fikirlerini düzeltir ya da geri çeker.
4. **Gizli oylama:** Her uzman diğerlerinin fikirlerini 5 kritere göre puanlar. Kimse kendi fikrine puan veremez.
   Kriterler: gelir %25, otomasyon %25, büyüme %20, risk %20, maliyet %10.
5. **Ortak karar:** En yüksek puanlı 2 fikir finale kalır. Uzmanlar pozisyonlarını yazar, tarafsız yazman ortak
   kararı yazar. Üç uzman onaylar ya da itiraz eder. İtiraz varsa karar en fazla 2 kez düzeltilir.

## Çalıştırma

- **Otomatik çalışma kapalı.** İlk tam deneme ~9$ tuttuğu için istekler ya da tetik dosyası değişince artık çalışmaz.
  Beyin fırtınası bundan sonra Claude Code sohbetinde (API faturası olmadan) yapılır; bu kod arşiv olarak duruyor.
- **Elle:** Actions → **Beyin Fırtınası** → Run workflow (isterseniz bir ek not yazın).
- **Yarıda kalan tartışma:** Tartışma yarıda kesildiyse (ör. API harcama sınırı) biten turlar `kararlar/devam.json` içinde durur ve
  yeni çalışma kaldığı yerden devam eder. İstekler değiştiyse tartışma baştan başlar.
- **Sonuç:** [kararlar/](kararlar/) klasörüne yazılır: kısa karar (`…-karar.md`) ve bütün tartışma
  (`…-tutanak.md`). Karar ayrıca 🧠 etiketli bir issue olarak açılır.
- **Maliyet:** Pahalı kısım web araştırmalı ilk iki turdur (ilk tam denemede ~9$). Sonraki turlar web kullanmaz,
  ~3$ tutar. Bir çalışma en fazla 7$ harcayabilir (`firtina.py` → `BUTCE_USD`); sınır aşılırsa biten turlar
  kaydedilip durulur ve sonraki çalışma kaldığı yerden devam eder. Süre 30–45 dakika.
