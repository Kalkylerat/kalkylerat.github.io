"""Herkese açık doğruluk paneli (İngilizce): docs/index.html (GitHub Pages)."""

from datetime import datetime
from html import escape
from pathlib import Path

from .kayit import kar, kombi_durumu, kombi_olasilik, kombi_oran, ozet

DURUM = {"kazandi": "Won", "kaybetti": "Lost", "iptal": "Void", "bekliyor": "Pending"}

SABLON = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kalkylerat – Record</title>
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
.kazandi,.tuttu {{ color:var(--win); }} .kaybetti,.yatti {{ color:var(--loss); }} .bekliyor {{ color:var(--pend); }}
.yorum {{ color:var(--muted); font-size:13px; }}
footer {{ color:var(--muted); font-size:13px; margin-top:32px; }}
</style>
</head>
<body><main>
<h1>Kalkyl<span>erat</span> – record</h1>
<p class="alt">Every pick is posted on X before kick-off and logged here automatically. Nothing is deleted. Stake: 1 unit per pick. Updated {guncelleme}.</p>
<div class="tiles">
<div class="tile"><b>{traff}%</b><span>Picks won ({vunna}–{forlorade})</span></div>
<div class="tile"><b>{kombi_tuttu}/{kombi}</b><span>Combos won</span></div>
<div class="tile"><b>{enheter}</b><span>Units (singles)</span></div>
<div class="tile"><b>{snittodds}</b><span>Average odds</span></div>
<div class="tile"><b>{vantande}</b><span>Pending</span></div>
</div>
{gunler}
<footer>18+ | For information only, not an invitation to gamble. Gambling can be addictive – never bet money you cannot afford to lose. Sweden: Stödlinjen 020-81 91 00. Chances are fair probabilities from a sharp betting market with the bookmaker margin removed. Odds are taken at posting time and may have changed.</footer>
</main></body></html>
"""


def _isaretli(x: float) -> str:
    return f"{x:+.2f}"


def _gun_html(g: dict) -> str:
    satirlar = "".join(
        f'<tr><td>{escape(s["ev"])} v {escape(s["dep"])}<div class="yorum">{escape(s["yorum"])}</div></td>'
        f'<td>{escape(s["kisa"])}<div class="yorum">{100 * s["adil_olasilik"]:.0f}% chance</div></td>'
        f'<td class="num">{s["oran"]:.2f}</td><td class="num">{escape((s.get("skor") or "").replace("-", "–"))}</td>'
        f'<td class="num {s["durum"]}">{DURUM[s["durum"]]}</td></tr>'
        for s in g["secimler"]
    )
    kombi = ""
    if len(g["secimler"]) >= 2:
        durum = kombi_durumu(g)
        etiket = {"tuttu": "won", "yatti": "lost", None: "pending"}[durum]
        kombi = (f'<tr><td colspan="5" class="{durum or "bekliyor"}">Combo @{kombi_oran(g):.2f} · '
                 f'chance all win {100 * kombi_olasilik(g):.0f}% · {etiket}</td></tr>')
    gunluk = f"{_isaretli(sum(kar(s) for s in g['secimler']))} units" if g["sonuc"] else "In play"
    return (f'<section class="dag"><header><span>{escape(g["tarih"])}</span><span>{gunluk}</span></header>'
            f'<table>{satirlar}{kombi}</table></section>')


def olustur(gunler: list[dict], path: Path) -> None:
    yayinlanan = sorted((g for g in gunler if g.get("tweet_id")), key=lambda g: g["tarih"], reverse=True)
    o = ozet(gunler)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SABLON.format(
        guncelleme=datetime.now().strftime("%Y-%m-%d %H:%M"),
        gunler="".join(_gun_html(g) for g in yayinlanan) or "<p>No published picks yet.</p>",
        vunna=o["vunna"], forlorade=o["forlorade"], traff=f'{o["traff"]:.0f}',
        kombi=o["kombi"], kombi_tuttu=o["kombi_tuttu"],
        enheter=_isaretli(o["enheter"]), snittodds=f'{o["snittodds"]:.2f}', vantande=o["vantande"],
    ), encoding="utf-8")
