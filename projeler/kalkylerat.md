# Kalkylerat (analiz hesabı, X)

**Durum (22 Ekim 2026):** çalışıyor. `python -m bot.durum` → `SORUN YOK`; günde en fazla 10 kart (22 Ekim'den beri).

## Ne yapıyor
- @kalkylerat, İngilizce. Sabah 05:17 UTC analizi; sabah tablosu, analiz kartları (oran ve takım istatistiği yan yana),
  maç sonu postu, tablo altına sonuçlar, anket ve bilgi postları. Kupon, kasa ya da bahis tavsiyesi yok.
- GitHub Actions: nabız ~7 dakikada bir, nöbetçi nabız durursa yeniden başlatır. Saatlik Claude nöbeti Haiku 5.5 ile
  yalnızca kontrol eder (`.claude/skills/nobet/SKILL.md`).
- Yorum fırsatları: 10, 13, 16, 18 UTC; yalnızca kartı paylaşılmış maçlardan söz eden büyük hesap postları, günde en
  fazla 10 (SOZLESME D6). Cevabı sahibi elle atar.
- API-Football Pro (190 kr/ay) Mr. Likely ile ortak; Mr. Likely ek istek atmaz.

## Kararlar
- Kurallar `SOZLESME.md` A–D, her madde `tests/test_sozlesme.py` ile bağlı.
- Jev (TypeSafe) eklenmedi (12 Ekim): metin yazamıyor, Haiku 5.5 karşısında kazanç küçük.
- Türkçe hesap avukat görüşüne kadar beklemede: `marka/TURKCE_HESAP_PLANI.md`.
- Yeni analiz kartı ve post açılışı (22 Ekim, sahibinin "sen karar ver"i): kart ve postun ilk satırı maçın hikâyesi
  (`analiz.hikaye`: oranla istatistik ayrışıyor / güçlü favori / açık maç / gollü maç / en olası skor). Kartta oran ve
  istatistik çubukları alt alta, kaç gol sütunları, en olası skorlar; renk tek anlam (ev mavi, deplasman turuncu, yeşil
  yalnızca "en olası"). Çifte şans ve takım golleri karttan çıktı. Direktör postu hikâyeyle açmazsa şablon gider.
- Günde en fazla 10 kart (22 Ekim, sahibinin kararı; önceden yoğun günde 30): benzer postlar benzerlik cezası
  alıyordu. Büyük maç fazlaysa önce oranla istatistiğin ayrıştığı maçlar; kartsız büyük maçlar tabloda (SOZLESME B4, B6).
  Kart ve maç sonu postu azaldığı için günde ~40 post ve direktör çağrısı daha az.

## Açık işler
- [ ] Yeni kartın etkisini ölç (22 Ekim'den): bir hafta sonra `metrik` (tek seferde ~100 post okuma, ~$0,50) ve
      eski haftayla görüntülenme/yanıt karşılaştırması. Son ölçüm 3 Ekim'den.
- [x] Bildirim düzeltmesi canlıda (22 Ekim): X 5xx ya da "aynı metin" dönerse hesabın son postlarına bakılır, aynı
      hata için tek bildirim, tablo sonuçları nabız başına 5 (SOZLESME B2, C2).
- [ ] Profildeki sabit tweet hâlâ "€10,000 challenge" ise `marka/PROFIL.md`'deki yeni metinle elle değiştir.
- [ ] `MALIYET.md` (`ccr-53dc4a08-tzpiit`) ana dala alınsın mı?
- [ ] Sahibine sorulacak (16 Ekim'den açık): kartı paylaşılmış ama başlamış maçların postları da yorum fırsatı olsun mu?
      Ek okuma maliyeti yok.
- [ ] Alarm #73 (15 Ekim, tek seferlik) kapatılabilir.

## Geçmiş (commit geçmişinden)
- 27 Eylül: İsveççe "value single" botu olarak başladı. 28 Eylül: €10.000 sanal kasa.
- 1 Ekim: analiz konseptine geçildi; kupon ve kasa durdu, eski postlar silindi. 2 Ekim: Türkçe hesap rafa kalktı.
- 3 Ekim: `SOZLESME.md` doğdu. 5–6 Ekim: Mr. Likely doğdu (önce elle, sonra otomatik).
- 9 Ekim: CEST/UTC hatası, 6–7 kart kaçtı ve düzeltildi. 11 Ekim: "hesap 10 saattir post atmamış" → nöbet ve alarm.
- 12 Ekim: nöbet rehberi + `python -m bot.durum`; 4 eski sohbet arşivlendi, 18 issue kapandı, README yenilendi.
- 22 Ekim: eski kupon/kasa düzeni koddan tamamen söküldü (~2 000 satır: kupon postu, sanal kasa, onay isteği, kasa
  grafiği, eski komutlar, `[kasa]` ve `[yayin]` ayarları). Ana sayfa (kalkylerat.github.io) artık analiz hesabını anlatıyor.
- Öneri: nöbet saatlerini maç saatlerine daralt.

## İlk mesaj
> Kalkylerat üzerinde çalışacağız. Önce CLAUDE.md, SOZLESME.md ve projeler/kalkylerat.md dosyalarını oku, sonra
> `python -m bot.durum` çalıştır. Bana durumu ve açık işler listesini 5 satırda özetle, ilk işe geçmeden onayımı bekle.

## Bulut kanalı ve rutin kayıtlarından
- 29 Eylül'den beri 463 rutin koşusu, hepsi "succeeded": saatlik sağlık kontrolü (3 Ekim, kapalı, 207 koşu), saatlik nöbet
  (12 Ekim, etkin, 242 koşu), 14 tek seferlik kontrol. Nöbet SADECE KONTROL modundadır: kod, commit, PR, issue ve elle X
  paylaşımı yok; tek izin, hiç `in_progress` nöbetçi yoksa onu workflow_dispatch ile başlatmak. Yanlış alarm sayılanlar:
  nöbetçinin 5,5 saate kadar `in_progress` kalması (330 dk döngü), kuyrukta `pending`/`cancelled` koşular, `gh auth status`
  "token invalid" ama `gh api` çalışıyor. B7: 08–21 UTC arasında 3 saatten uzun sessizlik her zaman sorun.
- Yedek kaynak: The Odds API (`bot/oddsapi.py`), API-Football çalışmazsa oran ve sonuç. Ücretsiz plan ayda 500 kredi; lig ve
  maç listesi kredi harcamaz, oran isteği pazar × bölge başına 1 kredi. 29 Eylül'de ilk kez bu kaynakla sonuç kapandı.
- Maliyet notu: Mr. Likely 18 Ekim'den beri sabah verisi zayıfsa 11:00'de ~55 API-Football isteği daha atar (PR #102),
  yani "Mr. Likely ek istek atmaz" artık geçerli değil. `max_oran_sayfasi = 30`.
