"""vidIQ bütçe kancası (G17). Claude Code `PreToolUse` kancası olarak her vidIQ çağrısından önce çalışır.

- Yalnız okuma ve araştırma araçlarına izin verir; üretim yapan, kanala yazan ya da yorum yanıtlayan araçlar reddedilir.
- Aylık tavan `ayar.toml [vidiq] aylik_kredi`; dönem vidIQ'nun kredi yenileme gününde başlar.
- İzin verilen her çağrı `deepspace/buyume/vidiq_harcama.jsonl` defterine yazılır.

Kanca girdisi stdin'den JSON'dur (`tool_name`). Red: stderr'e neden, çıkış 2 (Claude Code çağrıyı engeller).
Kapalı başarısızlık: kancanın içindeki her beklenmedik hata da çıkış 2'dir (Claude Code çıkış 1'de çağrıyı geçirir).
Elle yazılmış negatif kredi satırı sıfır sayılır (bütçeyi yeniden açamaz).
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from .ortak import KOK, ayar_yukle

DEFTER = KOK / "buyume" / "vidiq_harcama.jsonl"

# Araç kısa adı -> çağrı başı kredi (vidIQ'nun ilan ettiği maliyet; 0 = ücretsiz). Listede olmayan her araç reddedilir.
IZINLI: dict[str, int] = {
    "vidiq_balance": 0,
    "vidiq_keyword_research": 5,
    "vidiq_outliers": 5,
    "vidiq_similar_channels": 5,
    "vidiq_youtube_search": 5,
    "vidiq_channel_stats": 5,
    "vidiq_video_stats": 5,
    "vidiq_trending_videos": 5,
    "vidiq_channel_analytics": 5,
    "vidiq_channel_videos": 5,
    "vidiq_get_videos_by_ids": 5,
}


def kisa_ad(arac: str) -> str:
    """`mcp__<sunucu>__vidiq_x` -> `vidiq_x` (her iki vidIQ sunucusu öneki için)."""
    return arac.rsplit("__", 1)[-1]


def donem_basi(simdi: datetime, yenileme_gunu: int) -> date:
    gun = simdi.date()
    if gun.day >= yenileme_gunu:
        return gun.replace(day=yenileme_gunu)
    yil, ay = (gun.year - 1, 12) if gun.month == 1 else (gun.year, gun.month - 1)
    return date(yil, ay, yenileme_gunu)


def harcanan(defter: Path, bas: date) -> int:
    if not defter.exists():
        return 0
    toplam = 0
    for satir in defter.read_text(encoding="utf-8").splitlines():  # bozuk kodlama: hata -> main çıkış 2
        try:
            k = json.loads(satir)
            if datetime.fromisoformat(k["zaman"]).date() >= bas:
                toplam += max(0, int(k["kredi"]))
        except (ValueError, KeyError, TypeError):
            continue
    return toplam


def karar(arac: str, defter: Path, ayar: dict, simdi: datetime) -> tuple[bool, str]:
    ad = kisa_ad(arac)
    if ad not in IZINLI:
        return False, f"{ad}: izin listesinde yok (G17: yalnız okuma ve araştırma araçları)"
    v = ayar["vidiq"]
    kredi = IZINLI[ad] and v.get("cagri_kredi", IZINLI[ad])
    bas = donem_basi(simdi, v["yenileme_gunu"])
    once = harcanan(defter, bas)
    if once + kredi > v["aylik_kredi"]:
        return False, (f"aylık vidIQ tavanı: {once}/{v['aylik_kredi']} kredi harcandı (dönem {bas.isoformat()}); "
                       "artış için sahibine sor (G17)")
    defter.parent.mkdir(parents=True, exist_ok=True)
    with open(defter, "a", encoding="utf-8") as f:
        f.write(json.dumps({"zaman": simdi.isoformat(timespec="seconds"), "arac": ad, "kredi": kredi},
                           ensure_ascii=False) + "\n")
    return True, ""


def main() -> int:
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    try:
        girdi = json.loads(sys.stdin.read())
        arac = girdi["tool_name"]
    except (ValueError, KeyError, TypeError):
        print("vidIQ kancası: girdi okunamadı, çağrı reddedildi (G17)", file=sys.stderr)
        return 2
    try:
        ok, neden = karar(arac, DEFTER, ayar_yukle(), datetime.now(timezone.utc))
    except Exception as e:  # kapalı başarısızlık: defter ya da ayar okunamazsa çağrı geçmez
        print(f"vidIQ kancası hata verdi, çağrı reddedildi (G17): {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    if not ok:
        print(neden, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
