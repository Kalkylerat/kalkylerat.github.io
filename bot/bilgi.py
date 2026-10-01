"""Günlük bilgi postu: oran, olasılık, kasa yönetimi ve modelleme üzerine kısa, doğru bilgiler.

Doğruluk kuralı: her konunun sayıları ya tanım gereği doğrudur (ör. 1/oran) ya da burada hesaplanır; tahmin ya da
istatistik iddiası (ör. "beraberlik oranı %25") yoktur. X Direktörü metni doğal bir dille yeniden yazar ama yalnızca
"olgular"daki sayıları kullanabilir (etkilesim.sayilar_dogru denetler); uymazsa buradaki şablon paylaşılır."""

import math
from datetime import date


def _yuzde(p: float, basamak: int = 1) -> str:
    metin = f"{100 * p:.{basamak}f}"
    return (metin.rstrip("0").rstrip(".") if "." in metin else metin) + "%"


def _poisson(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _en_az_bir_seri(n: int, uzunluk: int, p_kayip: float) -> float:
    """n bahiste en az bir kez art arda `uzunluk` kayıp görme olasılığı (dinamik programlama, kesin)."""
    durum = [1.0] + [0.0] * (uzunluk - 1)  # şu anki kayıp serisi uzunluğu (seri henüz görülmedi)
    for _ in range(n):
        yeni = [0.0] * uzunluk
        for s, p in enumerate(durum):
            yeni[0] += p * (1 - p_kayip)
            if s + 1 < uzunluk:
                yeni[s + 1] += p * p_kayip
        durum = yeni
    return 1 - sum(durum)


def _binom_en_fazla(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def _konular() -> list[dict]:
    seri = _en_az_bir_seri(100, 5, 0.4)
    az10 = _binom_en_fazla(4, 10, 0.55)
    ev, dep = 1.4, 1.1
    skorlar = sorted(((_poisson(i, ev) * _poisson(j, dep), f"{i}-{j}") for i in range(8) for j in range(8)), reverse=True)
    kg = (1 - math.exp(-ev)) * (1 - math.exp(-dep))
    return [
        {"id": "ima", "baslik": "Odds are just probabilities in disguise",
         "govde": f"Divide 1 by the odds: 2.00 means {_yuzde(1 / 2)}, 1.50 means {_yuzde(1 / 1.5)}, "
                  f"1.25 means {_yuzde(1 / 1.25)}. That's the chance the price is asking you to believe in.",
         "soru": "What's the shortest price you'd ever take? 👇"},
        {"id": "marj", "baslik": "Where the bookmaker's edge hides",
         "govde": f"A coin-flip game priced 1.91 / 1.91 adds up to {_yuzde(2 / 1.91)} instead of 100%. "
                  f"That extra {_yuzde(2 / 1.91 - 1)} is the margin, built into every price.",
         "soru": "Did you know the margin was baked in like that? 👇"},
        {"id": "deger", "baslik": "Value in one line",
         "govde": f"Chance × odds above 1 = value. A 55% shot at 2.00 gives {0.55 * 2:.2f}: about "
                  f"{_yuzde(0.55 * 2 - 1, 0)} back per unit over time. A 75% shot at 1.25 gives {0.75 * 1.25:.4f}: "
                  f"a loss over time, however likely it looks.",
         "soru": "Do you check the price, or just the pick? 👇"},
        {"id": "kombine", "baslik": "Why accumulators shrink so fast",
         "govde": f"Chances multiply. Three 70% legs together: {_yuzde(0.7 ** 3)}. Five 80% legs: "
                  f"{_yuzde(0.8 ** 5)}. Each extra leg looks safe on its own and still cuts the whole thing down.",
         "soru": "How many legs is too many for you? 👇"},
        {"id": "seri", "baslik": "Losing runs are normal",
         "govde": f"Even at a 60% hit rate, over 100 picks the chance of at least one run of 5 losses in a row is "
                  f"{_yuzde(seri, 0)}. Streaks aren't proof something's broken; that's maths.",
         "soru": "What's the longest losing run you've sat through? 👇"},
        {"id": "yuzde1", "baslik": "Why we only use 1% of the bank",
         "govde": f"Ten losses in a row at 1% of the current bank leaves {_yuzde(0.99 ** 10)} of it. "
                  f"At 10% per go, the same run leaves {_yuzde(0.9 ** 10)}. Small stakes keep you in the game.",
         "soru": "Flat stakes or a % of the bank: which do you use? 👇"},
        {"id": "kelly", "baslik": "The Kelly formula, simply",
         "govde": "Kelly says: stake (chance × odds − 1) ÷ (odds − 1) of the bank. A 55% shot at 2.00 → 10%. "
                  "Full Kelly swings hard, so many people use a half or a quarter of it.",
         "soru": "Ever tried Kelly, or does it feel too aggressive? 👇"},
        {"id": "formatlar", "baslik": "Same price, three ways to write it",
         "govde": "Decimal 2.50 = fractional 3/2 = American +150. Decimal 1.50 = 1/2 = −200. "
                  "Decimal odds include your stake, which makes them the easiest to compare.",
         "soru": "Which format did you grow up with? 👇"},
        {"id": "dnb", "baslik": "Draw no bet vs double chance",
         "govde": "Draw no bet: a draw gives your stake back. Double chance: you win on two of the three results. "
                  "Both cost you some price compared with the plain win.",
         "soru": "Which one do you reach for more? 👇"},
        {"id": "asya", "baslik": "Asian handicap, the quick version",
         "govde": "−0.5 means the team must win. 0.0 is draw no bet. −0.25 splits your stake: half on 0.0, "
                  "half on −0.5, so a draw returns half.",
         "soru": "Do Asian lines confuse you or are they your go-to? 👇"},
        {"id": "ust", "baslik": "Over 2.5 vs Over 2.0",
         "govde": "Over 2.5 has no middle ground: 2 goals loses, 3 wins. Over 2.0 gives your stake back on "
                  "exactly 2 goals. Safer, so the price is shorter.",
         "soru": "Would you trade price for that safety net? 👇"},
        {"id": "poisson", "baslik": "How a goal model thinks",
         "govde": f"Many models treat goals like a Poisson process. If a team is expected to score 1.5, "
                  f"the chance it scores none is {_yuzde(math.exp(-1.5))}, and the chance it scores 3+ is "
                  f"{_yuzde(1 - sum(_poisson(k, 1.5) for k in range(3)))}.",
         "soru": "Does a team expected to score 1.5 drawing a blank surprise you? 👇"},
        {"id": "skor", "baslik": "Why correct scores are so hard",
         "govde": f"With 1.4 v 1.1 expected goals, the most likely score is {skorlar[0][1]} at just "
                  f"{_yuzde(skorlar[0][0])}. The next one, {skorlar[1][1]}, is {_yuzde(skorlar[1][0])}. "
                  f"Even the favourite score misses most of the time.",
         "soru": "Do you ever play correct scores? 👇"},
        {"id": "kgvar", "baslik": "Both teams to score, by the numbers",
         "govde": f"If the home side expects 1.4 goals and the away side 1.1, and you treat them as independent, "
                  f"both scoring comes out at {_yuzde(kg)}: basically a coin flip.",
         "soru": "BTTS fan or not for you? 👇"},
        {"id": "xg", "baslik": "What xG really measures",
         "govde": "Expected goals adds up how likely each shot was to go in. A penalty is worth about 0.76 to 0.79 "
                  "depending on the model. It describes chances, not finishing luck.",
         "soru": "Do you trust xG or the eye test more? 👇"},
        {"id": "orneklem", "baslik": "Ten results prove very little",
         "govde": f"A tipster who truly hits 55% will still go 4 wins or fewer out of 10 about "
                  f"{_yuzde(az10, 0)} of the time. Judge a record on hundreds of picks, not a week.",
         "soru": "How many results do you need before you trust a record? 👇"},
        {"id": "basabas", "baslik": "The break-even number",
         "govde": f"To break even at 1.20 you must win {_yuzde(1 / 1.2)} of the time. At 1.50: {_yuzde(1 / 1.5)}. "
                  f"At 2.00: {_yuzde(1 / 2)}. Short odds leave almost no room for a bad day.",
         "soru": "Surprised how high that first number is? 👇"},
        {"id": "martingale", "baslik": "Why doubling up after a loss is dangerous",
         "govde": f"Double after every loss and seven misses in a row take your next stake to {2 ** 7}× the first one. "
                  f"One cold run and the bank's gone.",
         "soru": "Have you ever been tempted to chase a loss? 👇"},
        {"id": "kapanis", "baslik": "Closing line value",
         "govde": "If you take 2.10 and the price closes at 1.90, you got a better number than the market's final "
                  "view. Beating the closing price over time is a widely used sign of a real edge.",
         "soru": "Do you track the closing price of your picks? 👇"},
        {"id": "beraberlik", "baslik": "Reading a three-way price",
         "govde": f"Odds of 2.20, 3.40 and 3.40 imply {_yuzde(round(1 / 2.2, 3))}, {_yuzde(round(1 / 3.4, 3))} and "
                  f"{_yuzde(round(1 / 3.4, 3))}: {_yuzde(round(1 / 2.2, 3) + 2 * round(1 / 3.4, 3))} in total. "
                  f"Strip the margin and the home win is about {_yuzde((1 / 2.2) / (1 / 2.2 + 2 / 3.4))}.",
         "soru": "Do you ever work out the real chance behind a price? 👇"},
    ]


KONULAR = _konular()


def gunun_konusu(tarih: str) -> dict:
    """Her gün sırayla başka konu (20 günde bir döner)."""
    return KONULAR[date.fromisoformat(tarih).toordinal() % len(KONULAR)]
