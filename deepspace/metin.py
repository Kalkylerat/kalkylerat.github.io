"""YouTube metinleri: başlık, açıklama (bölümler + gerçek gök cismi bilgisi + süreç notu), etiketler, sabit yorum.

Şablonla üretilir; yapay zekâ çağrısı yok (maliyet kuralı). Bilgiler görevin gorev.toml dosyasından gelir.
"""
from __future__ import annotations

import json

from .ortak import cikti, seri, zaman

SUREC_NOTU = (
    "How this music is made\n"
    "Every mission is composed around one destination. Each piece has its own melodic motif, key and sound "
    "palette, written as composition prompts and generated with AI music tools (Suno), then hand-selected, "
    "sequenced and mastered for long, distraction-free focus. The visuals are generated with code: real "
    "planets and stars, imagined surfaces."
)


def bolum_satirlari(bolumler: dict) -> list[str]:
    return [f"{zaman(p['basla'])} {p['ad']}" for p in bolumler["parcalar"]]


def uret(gorev: dict, ayar: dict) -> dict:
    out = cikti(gorev)
    bolumler = json.loads((out / "bolumler.json").read_text(encoding="utf-8"))
    sr = seri(gorev, ayar)
    kanal = ayar["kanal"]["ad"]
    saat = round(bolumler["toplam_sn"] / 3600)
    baslik = sr["baslik"].format(hedef=gorev["hedef"], saat=saat)

    notlar = [f"{p['ad']}: {p['bilgi']}" for p in gorev["parca"] if p.get("bilgi")]
    aciklama = "\n".join([
        f"{kanal} · Mission {gorev['no']:03d} · {gorev['hedef']} ({gorev['uzaklik']})",
        "",
        gorev["ozet"].strip(),
        "",
        f"{saat} hours of {sr['ad'].lower()} space ambient music for studying, coding, reading and deep work. "
        "No vocals, no drums, no sudden changes. Ad breaks only fall between pieces.",
        "",
        "Chapters",
        *bolum_satirlari(bolumler),
        "",
        "Mission notes",
        *notlar,
        "",
        SUREC_NOTU,
        "",
        f"A new mission every week. Where should {ayar['kanal']['maskot']} go next? Tell us in the comments.",
        "",
        " ".join(sr["hashtagler"]),
    ])

    etiketler, toplam = [], 0
    for e in sr["etiketler"] + [gorev["hedef"], kanal]:
        if toplam + len(e) + 1 > ayar["metin"]["etiket_max_karakter"]:
            break
        etiketler.append(e)
        toplam += len(e) + 1

    sonraki = gorev.get("sonraki_adaylar") or []
    yorum = (f"Next mission: where should {ayar['kanal']['maskot']} go? "
             + (" · ".join(sonraki) + ". Most-liked reply wins." if sonraki else "Reply with a planet, moon or star."))

    sonuc = {
        "baslik": baslik,
        "aciklama": aciklama,
        "etiketler": etiketler,
        "sabit_yorum": yorum,
        "kategori": "10",  # Music
        "dil": ayar["kanal"]["dil"],
        "sentetik_icerik": True,  # "Altered or synthetic content" etiketi her yüklemede işaretlenir (G9)
        "reklam_noktalari": [zaman(p["basla"]) for p in bolumler["parcalar"][1:]],
    }
    (out / "youtube.json").write_text(json.dumps(sonuc, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "aciklama.txt").write_text(aciklama, encoding="utf-8")
    return sonuc
