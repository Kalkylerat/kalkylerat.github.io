# Kalkylerat (analiz hesabı, X)

**Durum (22 Ekim 2026):** çalışıyor. `python -m bot.durum` → `SORUN YOK`; günde ~30 kart, hepsi zamanında.

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

## Açık işler
- [ ] `claude/email-notification-cleanup-314g6n` dalını ana dala al (16 Ekim): X 5xx ya da "aynı metin" dönerse hesabın
      son postlarına bakılır; bot alarmı yazdıysa çalışma başarısız sayılmaz; nöbetçi hata dizisi başına tek alarm açar;
      tablo sonuçları nabız başına 5. SOZLESME C2'ye "tek kanal" eklenir.
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
- Temizlik işi (acil değil): kodda ~400 satır eski kupon/kasa kodu duruyor. Öneri: nöbet saatlerini maç saatlerine daralt.

## İlk mesaj
> Kalkylerat üzerinde çalışacağız. Önce CLAUDE.md, SOZLESME.md ve projeler/kalkylerat.md dosyalarını oku, sonra
> `python -m bot.durum` çalıştır. Bana durumu ve açık işler listesini 5 satırda özetle, ilk işe geçmeden onayımı bekle.
