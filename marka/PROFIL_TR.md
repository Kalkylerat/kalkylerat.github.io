# Kalkylerat Türkiye — X hesabı kurulumu

Görseller bu klasörde: `logo_tr.png` (profil fotoğrafı), `kapak_tr.png` (kapak, 1500×500). Palet: antrasit + altın.

| Alan | Değer |
|---|---|
| İsim | `Kalkylerat \| Maç Analizi` |
| Kullanıcı adı | `@kalkyleratTR` — alınmışsa: `@kalkylerat_tr`, `@KalkyleratTurkiye` |
| Konum | `Avrupa` |
| Dil | Türkçe |

## Biyografi

```
Veriyle futbol analizi: her maç için tüm pazarların olasılıkları ve en olası skorlar, her gün. Her tahminin karnesi maç sonunda. Bahis tavsiyesi değildir. 18+
```

## Zorunlu ayarlar
1. Ayarlar → Hesabınız → Hesap bilgileri → **Otomasyon** → yönetici hesap olarak **@kalkylerat**'ı seçin
   ("Automated by @kalkylerat" etiketi; X kuralı).
2. Bu hesapla developer.x.com'a girip bir uygulama (app) açın; **Keys and tokens** bölümünden dört anahtarı alın
   (uygulama izni: Read and write). GitHub → Settings → Secrets → Actions altına şu adlarla ekleyin:
   `X_TR_API_KEY`, `X_TR_API_SECRET`, `X_TR_ACCESS_TOKEN`, `X_TR_ACCESS_SECRET`.
   (Anahtarlar sadece GitHub'a girilir; hiçbir yere yapıştırılmaz.)
