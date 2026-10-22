# claude.ai sohbetlerini projelere aktarma (bilgisayardan, bir kez)

Claude Code bulut oturumları claude.ai'deki normal sohbetleri, Projects'i ve Cowork oturumlarını göremez. Onları
özetlemenin yolu claude.ai'nin dışa aktarma dosyası ve bilgisayardaki Claude Code.

## Sahibinin adımları

1. **Dışa aktar:** claude.ai → Ayarlar (Settings) → Gizlilik (Privacy) → **Verileri dışa aktar (Export data)**.
   E-postayla bir indirme bağlantısı gelir (bağlantı kısa süre geçerlidir). Zip dosyasını indir.
2. **Zip'i depo DIŞINDA bir klasöre aç.** Örnek: `~/claude-export/`. Bu depo herkese açık; ham sohbetler asla
   deponun içine konmaz.
3. **Depoyu al** (bilgisayarda yoksa):
   ```
   git clone https://github.com/Kalkylerat/kalkylerat.github.io.git
   cd kalkylerat.github.io
   git checkout claude/organize-conversations-projects-j4pcxk
   ```
4. **Claude Code'u ucuz modelle aç** (özetleme için Sonnet yeter): `claude --model sonnet`
5. Şu mesajı yapıştır:
   > projeler/claude-ai-aktarim.md dosyasındaki "Claude'a talimat" bölümünü uygula. Dışa aktarma klasörü: ~/claude-export

## Claude'a talimat

Amaç: sahibinin claude.ai'deki bütün sohbetlerini ve Project'lerini, hiçbir önemli bilgiyi kaybetmeden, projelere göre
özetlemek. Sahibiyle Türkçe konuş.

1. Dışa aktarma klasöründeki dosyaları bul (`conversations.json`, `projects.json`, varsa diğerleri). Dosyalar büyük
   olabilir: okumak için Python betiği yaz, tamamını tek seferde bağlama yükleme. Betiği depo dışında çalıştır.
2. Her sohbet için şunları çıkar: başlık, tarih aralığı, sahibinin sorduğu **her ayrı konu** (bir sohbette birden çok
   konu olabilir; sahibi bazen konuları karıştırdı), verilen kararlar, rakamlar ve fiyatlar, yapılan işler, açık kalan
   sorular, bağlantılar. Project'ler için talimat metni ve dosya adları.
3. Her konuyu şu projelerden birine ata; uymayanlar için yeni proje aç:
   Kalkylerat, Mr. Likely, Tiny Fixes, YouTube kanalı, Vezir, Flow Event, E-ticaret, Suno müzik, Fikir rafı, Genel
   (Claude kullanımı, maliyet, hesap ayarları, kişisel sorular).
4. **Tam özet yalnızca yerelde:** `~/claude-export/OZET.md` dosyasına proje başlıkları altında, sohbet sohbet, her konu
   ayrı madde olarak yaz. Bu dosya depoya girmez.
5. **Depoya giden kısım:** `projeler/<proje>.md` dosyalarına (yoksa aynı biçimde yeni dosya aç) "claude.ai
   sohbetlerinden" bölümü ekle: kararlar, açık işler, rakamlar. Şunları depoya **yazma**: sağlık, aile ve çocuklar,
   adres, kimlik ve hesap numaraları, kişisel para durumu, şifre ve anahtarlar, üçüncü kişilerin adları. Emin değilsen
   yazma, yalnızca OZET.md'ye koy.
6. `python -m pytest -q` yeşil olsun, sonra commit et ve `claude/organize-conversations-projects-j4pcxk` dalına push et.
7. Sahibine sohbet sayısını, proje başına konu sayısını ve atadığın yeni projeleri bildir. OZET.md'nin yerini söyle.
