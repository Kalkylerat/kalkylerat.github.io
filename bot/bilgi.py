"""Günlük bilgi postu: oran, olasılık ve gol modeli üzerine kısa, doğru bilgiler (bahis/kasa tavsiyesi yok).

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
    ms = [sum(_poisson(i, ev) * _poisson(j, dep) for i in range(12) for j in range(12) if f(i, j))
          for f in (lambda i, j: i > j, lambda i, j: i == j, lambda i, j: i < j)]
    ust25 = 1 - sum(_poisson(k, ev + dep) for k in range(3))
    return [
        {"id": "ima", "baslik": "Odds are just probabilities in disguise",
         "govde": f"Divide 1 by the odds: 2.00 means {_yuzde(1 / 2)}, 1.50 means {_yuzde(1 / 1.5)}, "
                  f"1.25 means {_yuzde(1 / 1.25)}. Every price is a chance written another way.",
         "soru": "Do you read odds as chances already? 👇"},
        {"id": "marj", "baslik": "Where the bookmaker's edge hides",
         "govde": f"A coin-flip game priced 1.91 / 1.91 adds up to {_yuzde(2 / 1.91)} instead of 100%. "
                  f"That extra {_yuzde(2 / 1.91 - 1)} is the margin, built into every price.",
         "soru": "Did you know the margin was baked in like that? 👇"},
        {"id": "deger", "baslik": "Prices move because chances move",
         "govde": f"When odds drop from 2.10 to 1.90, the chance they imply rises from {_yuzde(1 / 2.1)} to "
                  f"{_yuzde(1 / 1.9)}. A moving price is the market changing its mind.",
         "soru": "Do you watch the odds move before kick-off? 👇"},
        {"id": "kombine", "baslik": "Several likely things rarely all happen",
         "govde": f"Chances multiply. Three 70% events together: {_yuzde(0.7 ** 3)}. Five 80% events: "
                  f"{_yuzde(0.8 ** 5)}. Each looks safe alone; together they're closer to a coin flip.",
         "soru": "Did you expect it to drop that fast? 👇"},
        {"id": "seri", "baslik": "Streaks are normal",
         "govde": f"Something that happens 60% of the time will, over 100 tries, miss 5 in a row at least once "
                  f"with a {_yuzde(seri, 0)} chance. A run of misses isn't proof of anything; that's maths.",
         "soru": "Do streaks fool you too? 👇"},
        {"id": "yuzde1", "baslik": "The most likely number of goals",
         "govde": f"With 2.5 goals expected in a game, exactly 2 goals is the single most likely total at "
                  f"{_yuzde(_poisson(2, ev + dep))}, just ahead of 3 at {_yuzde(_poisson(3, ev + dep))}.",
         "soru": "Would you have guessed 2 or 3? 👇"},
        {"id": "kelly", "baslik": "Why 0-0 is rarer than it feels",
         "govde": f"If the home side expects 1.4 goals and the away side 1.1, a goalless draw comes out at just "
                  f"{_yuzde(_poisson(0, ev) * _poisson(0, dep))}. It feels common because we remember the dull ones.",
         "soru": "Higher or lower than you thought? 👇"},
        {"id": "formatlar", "baslik": "Same chance, three ways to write it",
         "govde": f"Decimal 2.50 = fractional 3/2 = American +150: all a {_yuzde(1 / 2.5)} chance. Decimal 1.50 = "
                  f"1/2 = −200: {_yuzde(1 / 1.5)}. Decimal odds are the easiest to turn into a %.",
         "soru": "Which format did you grow up with? 👇"},
        {"id": "dnb", "baslik": "Take the draw out",
         "govde": f"If a game is 45% home, 27% draw, 28% away, then in the games that do have a winner the home "
                  f"side wins {_yuzde(0.45 / 0.73)} of the time.",
         "soru": "Does the draw change how you see a favourite? 👇"},
        {"id": "asya", "baslik": "Clean sheets in numbers",
         "govde": f"A team expected to concede 1.1 goals keeps a clean sheet about {_yuzde(_poisson(0, dep))} of "
                  f"the time. Concede 1.5 on average and it drops to {_yuzde(_poisson(0, 1.5))}.",
         "soru": "Which keeper in your league beats those odds? 👇"},
        {"id": "ust", "baslik": "Over 2.5 goals, by the numbers",
         "govde": f"A game expecting 2.5 goals in total still ends with 3 or more only {_yuzde(ust25)} of the "
                  f"time. Expecting 2.5 doesn't make 3+ the likely side.",
         "soru": "Surprised it's under half? 👇"},
        {"id": "poisson", "baslik": "How a goal model thinks",
         "govde": f"Many models treat goals like a Poisson process. If a team is expected to score 1.5, the chance "
                  f"it scores none is {_yuzde(_poisson(0, 1.5))}, and the chance it scores 3+ is "
                  f"{_yuzde(1 - sum(_poisson(k, 1.5) for k in range(3)))}.",
         "soru": "Does a team expected to score 1.5 drawing a blank surprise you? 👇"},
        {"id": "skor", "baslik": "Why correct scores are so hard",
         "govde": f"With 1.4 v 1.1 expected goals, the most likely score is {skorlar[0][1]} at just "
                  f"{_yuzde(skorlar[0][0])}. The next one, {skorlar[1][1]}, is {_yuzde(skorlar[1][0])}. "
                  f"Even the likeliest score misses most of the time.",
         "soru": "Which score would you have guessed? 👇"},
        {"id": "kgvar", "baslik": "Both teams to score, by the numbers",
         "govde": f"If the home side expects 1.4 goals and the away side 1.1, and you treat them as independent, "
                  f"both scoring comes out at {_yuzde(kg)}: basically a coin flip.",
         "soru": "Both teams to score: more or less often than you'd think? 👇"},
        {"id": "xg", "baslik": "What expected goals really measures",
         "govde": "Expected goals adds up how likely each shot was to go in. A penalty goes in about 76% to 79% of the "
                  "time. It describes chances, not finishing luck.",
         "soru": "Expected goals or the eye test? 👇"},
        {"id": "orneklem", "baslik": "Ten results prove very little",
         "govde": f"A team that truly wins 55% of its games will still win 4 or fewer of 10 about "
                  f"{_yuzde(az10, 0)} of the time. Judge strength on a season, not a fortnight.",
         "soru": "How many games before you trust a team's form? 👇"},
        {"id": "basabas", "baslik": "What short odds really ask",
         "govde": f"Odds of 1.20 say {_yuzde(1 / 1.2)}: the favourite should win 5 of every 6 such games. "
                  f"At 1.50: {_yuzde(1 / 1.5)}. At 2.00: {_yuzde(1 / 2)}.",
         "soru": "Do favourites live up to that, in your experience? 👇"},
        {"id": "martingale", "baslik": "From expected goals to a result",
         "govde": f"Feed 1.4 v 1.1 expected goals into a Poisson model and you get home {_yuzde(ms[0], 0)}, draw "
                  f"{_yuzde(ms[1], 0)}, away {_yuzde(ms[2], 0)}. A small edge in goals is a small edge in results.",
         "soru": "Bigger home edge than you'd expect, or smaller? 👇"},
        {"id": "kapanis", "baslik": "The market's final word",
         "govde": "Odds right before kick-off carry the most information: team news, line-ups, weather. That is why "
                  "our cards compare them with what the team stats alone say.",
         "soru": "Do you check the line-ups before you judge a game? 👇"},
        {"id": "beraberlik", "baslik": "Reading a three-way price",
         "govde": f"Odds of 2.20, 3.40 and 3.40 imply {_yuzde(round(1 / 2.2, 3))}, {_yuzde(round(1 / 3.4, 3))} and "
                  f"{_yuzde(round(1 / 3.4, 3))}: {_yuzde(round(1 / 2.2, 3) + 2 * round(1 / 3.4, 3))} in total. "
                  f"Strip the margin and the home win is about {_yuzde((1 / 2.2) / (1 / 2.2 + 2 / 3.4))}.",
         "soru": "Do you ever work out the real chance behind a price? 👇"},
    ]


KONULAR = _konular()


def gunun_konusu(tarih: str, kayma: int = 0) -> dict:
    """Her gün sırayla başka konu (20 günde bir döner); kayma: aynı günün ikinci (akşam) konusu."""
    return KONULAR[(date.fromisoformat(tarih).toordinal() + kayma * (len(KONULAR) // 2)) % len(KONULAR)]
