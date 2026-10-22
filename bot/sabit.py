"""Profilin sabit tweeti (sahibinin isteği, 22 Ekim 2026): yeni konumu ("oynamadan önce hesap makinesi") anlatan
post, nabızla bir kez paylaşılır. X API'de sabitleme yok: sahibi profilde elle sabitler. Aynı metin ikinci kez
gitmez (kayıt: data/sabit_tweet.json); kurala uymayan metin hiç gitmez."""

import json

from .tweets import ANSVAR, LIMIT, uzunluk

METIN = f"""How likely is it, really?

Big games in plain numbers:
– chances from the odds, no margin
– a fair price for each result
– the bookmakers' cut
– at full time: what happened and its chance

Mondays: what we said vs what happened.

Chances, not picks.
{ANSVAR}"""


def kurala_uygun(metin: str, ayar) -> bool:
    from . import direktor
    return uzunluk(metin) <= LIMIT and direktor.kurala_uygun(metin, "analiz", ayar.oran_bahiscileri + [ayar.keskin_bahisci]) \
        and not direktor.yz_izi(metin) and "not picks" in metin.lower()


def gonder(x, ayar, dosya, simdi, yaz=print) -> str | None:
    """Metin daha önce gönderilmediyse bir kez paylaşır; tweet kimliğini döner (gönderilmediyse None)."""
    try:
        kayit = json.loads(dosya.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        kayit = {}
    if kayit.get("metin") == METIN:
        return None
    if not kurala_uygun(METIN, ayar):
        yaz("⚠️ Sabit tweet metni kurala uymuyor; gönderilmedi.")
        return None
    tid = x.gonder(METIN)
    dosya.write_text(json.dumps({"id": tid, "metin": METIN, "zaman": simdi.isoformat(timespec="seconds")},
                                ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    yaz(f"📌 Sabit tweet paylaşıldı: https://x.com/i/status/{tid} (profilde elle sabitleyin)")
    return tid
