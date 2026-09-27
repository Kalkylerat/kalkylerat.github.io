"""Herkese açık doğruluk paneli (İsveççe): docs/index.html (GitHub Pages)."""

from datetime import datetime
from html import escape
from pathlib import Path

from .kayit import kar, ozet
from .tweets import isaretli, sayi

DURUM = {"kazandi": "Vann", "kaybetti": "Förlust", "iptal": "Inställd", "bekliyor": "Väntar"}

SABLON = """<!doctype html>
<html lang="sv">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kalkylerat – Rekord</title>
<style>
:root {{ --bg:#f5f6f8; --card:#fff; --text:#0f1b2d; --muted:#5d6878; --line:#e1e4ea; --win:#12805a; --loss:#b3261e; --pend:#8a6d00; --accent:#19c37d; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0f1b2d; --card:#16243a; --text:#eef2f7; --muted:#9aa7b8; --line:#253652; --win:#3fd394; --loss:#ff6b61; --pend:#e0b84a; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }}
main {{ max-width:960px; margin:0 auto; padding:24px 16px 48px; }}
h1 {{ font-size:26px; margin:0 0 4px; }} h1 span {{ color:var(--accent); }}
p.alt {{ color:var(--muted); margin:0 0 20px; }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:12px; margin-bottom:24px; }}
.tile {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; }}
.tile b {{ display:block; font-size:24px; font-variant-numeric:tabular-nums; }}
.tile span {{ color:var(--muted); font-size:13px; }}
.dag {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; margin-bottom:12px; }}
.dag header {{ display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px; font-weight:600; }}
table {{ width:100%; border-collapse:collapse; margin-top:8px; font-size:14px; }}
td {{ overflow-wrap:anywhere; padding:6px 4px; border-top:1px solid var(--line); vertical-align:top; }}
td.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
.kazandi {{ color:var(--win); }} .kaybetti {{ color:var(--loss); }} .bekliyor {{ color:var(--pend); }}
.yorum {{ color:var(--muted); font-size:13px; }}
footer {{ color:var(--muted); font-size:13px; margin-top:32px; }}
</style>
</head>
<body><main>
<h1>Kalkyl<span>erat</span> – rekord</h1>
<p class="alt">Alla spel publiceras på X före avspark och förs in här automatiskt. Inget raderas. Insats: 1 enhet per spel. Uppdaterad {guncelleme}.</p>
<div class="tiles">
<div class="tile"><b>{vunna}–{forlorade}</b><span>Vunna–förlorade ({traff} %)</span></div>
<div class="tile"><b>{enheter}</b><span>Enheter</span></div>
<div class="tile"><b>{roi} %</b><span>ROI</span></div>
<div class="tile"><b>{snittodds}</b><span>Snittodds</span></div>
<div class="tile"><b>{vantande}</b><span>Väntar på resultat</span></div>
</div>
{gunler}
<footer>18+ | Informationssida, inte en uppmaning att spela. Spel kan vara beroendeframkallande – spela aldrig för pengar du inte har råd att förlora. Stödlinjen: 020-81 91 00 (stodlinjen.se). Odds hämtas från svensklicensierade spelbolag vid publiceringstillfället och kan ha ändrats.</footer>
</main></body></html>
"""


def _gun_html(g: dict) -> str:
    satirlar = "".join(
        f'<tr><td>{escape(s["ev"])} – {escape(s["dep"])}<div class="yorum">{escape(s["yorum"])}</div></td>'
        f'<td>{escape(s["etiket"])}<div class="yorum">{escape(s["bolag"])}</div></td>'
        f'<td class="num">{sayi(s["oran"])}</td><td class="num">{escape((s.get("skor") or "").replace("-", "–"))}</td>'
        f'<td class="num {s["durum"]}">{DURUM[s["durum"]]}<br>{isaretli(kar(s), 2) if s["durum"] != "bekliyor" else ""}</td></tr>'
        for s in g["secimler"]
    )
    dag = sum(kar(s) for s in g["secimler"])
    durum = f"{isaretli(dag, 2)} e" if g["sonuc"] else "Pågår"
    return (f'<section class="dag"><header><span>{escape(g["tarih"])}</span><span>{durum}</span></header>'
            f'<table>{satirlar}</table></section>')


def olustur(gunler: list[dict], path: Path) -> None:
    yayinlanan = sorted((g for g in gunler if g.get("tweet_id")), key=lambda g: g["tarih"], reverse=True)
    o = ozet(gunler)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SABLON.format(
        guncelleme=datetime.now().strftime("%Y-%m-%d %H:%M"),
        gunler="".join(_gun_html(g) for g in yayinlanan) or "<p>Inga publicerade spel ännu.</p>",
        vunna=o["vunna"], forlorade=o["forlorade"], traff=sayi(o["traff"], 0),
        enheter=isaretli(o["enheter"], 2), roi=isaretli(o["roi"]), snittodds=sayi(o["snittodds"]),
        vantande=o["vantande"],
    ), encoding="utf-8")
