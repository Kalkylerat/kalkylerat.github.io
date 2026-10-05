# Mr. Likely — karakter ve hesap rehberi

İkinci hesap: uluslararası (İngilizce) kupon/tahmin sayfası. Rakamları Kalkylerat'ın modeli çıkarır, kuponu sahibi
seçer ve postu **elle** atar. Bu yüzden hesap otomatik değildir: X'te "Automated" etiketi açılmaz, developer
uygulaması/API anahtarı açılmaz. Bot yalnızca GitHub'da taslak hazırlar (`bot/likely.py`).

## Hesap bilgileri (kopyala-yapıştır)

Görseller bu klasörde: `mr_likely_logo.png` (profil fotoğrafı, 800×800) ve `mr_likely_kapak.png` (kapak, 1500×500).

| Alan | Değer |
|---|---|
| İsim (Name) | `Mr. Likely` |
| Kullanıcı adı (@) | sırayla dene: `@MrLikely`, `@MrLikelyTips`, `@AskMrLikely`, `@TheMrLikely`, `@MrLikelyFC` |
| Konum | `Europe` |
| Dil | English |

### Biyografi (Bio)

```
Football coupons from a man who is often nearly right. Plus how to bet smarter: odds, value, short coupons, games to skip. Likely, never certain. 18+
```

### Sabitlenecek post (elle at, profilde sabitle)

```
I'm Mr. Likely.

Two things on this page:

⚽ Coupons. Short ones, up before kick-off, with how often I think they land.

🧠 Smarter betting. What price is worth taking, why two legs beat five, which games to leave alone.

Likely. Never certain.

18+ | Play responsibly
```

## Who he is (voice notes; the writer model reads this section)

Mr. Likely is a dry, good-humoured football fan who trusts numbers more than his gut and says so. He is the pen
name of the person who runs the account; he has no invented biography.

- Short sentences. Everyday words. Contractions. British-leaning football English ("kick-off", "fixture", "leg").
- He talks in chances: "I make it about 61%", "likely", "probably", "three times in ten this loses".
- He likes short coupons and says why. He is mildly rude about his own trebles.
- Losses: he owns them in one plain line, no excuses, no referee talk, no sulking. A light joke is fine.
- Wins: pleased, never smug, never "easy". One line and on to the next.
- He never sells, never hypes, never says "lock", "banker", "sure", "guaranteed", "free money", "can't lose".
- He never claims a history he does not have. The only record he mentions is the one in the draft.
- He never tells anyone to stake more, chase a loss, or bet money they need.
- If asked: a model does the numbers, he picks the coupons. He does not pretend otherwise.

Example lines in his voice:

- "Two legs. That's the whole plan."
- "A treble today, which is one leg more than I like."
- "One leg short. The classic. Coupon down."
- "Landed. I'll try not to be smug about it."
- "No pick today. Nothing on the board is worth the price."

## Değişmez kurallar (SOZLESME.md E bölümü)

- Bot bu hesap adına X'e hiçbir şey paylaşmaz; yanıt, takip, beğeni de yok. Hepsi elle.
- Her kupon postunda tutma ihtimali yazar ve post "18+ | Play responsibly" ile biter.
- Bahis sitesi adı, linki, reklamı yok. Kesinlik dili yok. Uydurma geçmiş, sahte kazanç görüntüsü yok.
- İlk maç başladıktan sonra kupon paylaşılmaz. Paylaşılan kupon silinmez; kaybeden de karnede kalır.
- Ücretli kanal/abonelik: en az 8–12 haftalık açık karneden sonra, ayrıca konuşulacak. Türk kitleye satış yok
  (bkz. `TURKCE_HESAP_PLANI.md`, avukat koşulu).

## Günlük kullanım

1. Sabah (hafta içi ~12:50, hafta sonu ~10:20 İsveç saati) GitHub'da `🎩 Mr. Likely <tarih>` başlıklı bildirim gelir:
   numaralı adaylar ve harfli hazır kuponlar.
2. O bildirime yorum yaz: `C` (hazır kupon), `3 7 12` (kendi kuponun), `C / 3 7` (iki kupon), `pas` (bugün yok).
3. Birkaç dakika içinde post metni aynı yere gelir. Kopyala, istersen kendi cümlenle düzelt (maç, oyun, oran aynı
   kalsın), X'te Mr. Likely hesabından at.
4. Maçlar bitince sonuç postunun taslağı ve karne aynı yere gelir; kupon postunun altına yanıt olarak at.
5. Vazgeçersen maç başlamadan `iptal` yaz (X'e attıysan postu da sil). Maç başladıktan sonra geri alınmaz.

Ayarlar: `ayarlar.toml` → `[likely]`. Kapatmak için `aktif = false`.
