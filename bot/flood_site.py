"""Tiny Fixes sitesi (GitHub Pages, `docs/tinyfixes/`; SOZLESME F11).

X ve Instagram profil bağlantısı buraya gelir. Ana sayfa aynı zamanda "link in bio" sayfasıdır: ücretsiz paket için
e-posta formu (Kit), ücretli paket düğmesi (Lemon Squeezy), son denenmiş çözümler. Her yayınlanmış çözüm kendi
sayfasını alır (arama motorundan da gelen trafik: "how to ... with AI"). Yalnızca kütüphanedeki (yayınlanmış,
denenmiş) girdiler kullanılır; dosya yalnızca içeriği değiştiyse yazılır (gereksiz commit yok). Ücretsiz."""

import html
import shutil
from datetime import datetime
from email.utils import format_datetime

from . import config, flood_denetci
from .flood_gelir import GelirAyar, sayfa_url

KLASOR = config.ROOT / "docs" / "tinyfixes"
KAPAK = config.ROOT / "marka" / "tiny_fixes_x_kapak.png"
LOGO = config.ROOT / "marka" / "tiny_fixes_logo.png"


def _e(t) -> str:
    return html.escape(str(t or ""), quote=True)


_CSS = """:root{--bg:#FFF6EA;--card:#fff;--ink:#22223B;--muted:#63667F;--line:#EADFCF;--mint:#5ED3A8;--mint2:#DDF5EC;--coral:#FF7A6B;--coral2:#FFE3DE}
@media (prefers-color-scheme:dark){:root{--bg:#1A1B2E;--card:#23253C;--ink:#F4EEE4;--muted:#A9ABC2;--line:#34364F;--mint2:#1F3B37;--coral2:#43293A;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 "Bricolage Grotesque",system-ui,-apple-system,"Segoe UI",sans-serif;overflow-wrap:anywhere}
main{max-width:720px;margin:0 auto;padding:28px max(16px,env(safe-area-inset-right)) 64px max(16px,env(safe-area-inset-left))}
a{color:var(--ink);text-decoration-color:var(--coral);text-underline-offset:3px}
.marka{display:flex;align-items:center;gap:12px;text-decoration:none;font-weight:800;font-size:20px}.marka img{width:44px;height:44px;border-radius:50%}
h1{font-size:clamp(30px,7vw,46px);line-height:1.05;margin:22px 0 8px;text-wrap:balance}h2{font-size:24px;margin:34px 0 10px;text-wrap:balance}
.alt{color:var(--muted);margin:0 0 18px}
.kutu{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:18px 20px;margin:18px 0}
.kutu.nane{background:var(--mint2);border-color:transparent}.kutu.mercan{background:var(--coral2);border-color:transparent}
form{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}input[type=email]{flex:1 1 220px;min-width:0;font:inherit;padding:12px 14px;border-radius:999px;border:2px solid var(--ink);background:var(--card);color:var(--ink)}
button,.dugme{font-family:inherit;font-weight:700;font-size:16px;line-height:1;border:0;border-radius:999px;padding:14px 20px;background:var(--ink);color:var(--bg);cursor:pointer;text-decoration:none;display:inline-block}
.dugme.mercan{background:var(--coral);color:#22223B}
.kucuk{font-size:13px;color:var(--muted);margin:8px 0 0}
pre{white-space:pre-wrap;background:var(--card);border:2px solid var(--ink);border-radius:16px;padding:16px;font:14px/1.6 ui-monospace,"SFMono-Regular",Menlo,monospace;margin:8px 0}
.liste{list-style:none;padding:0;margin:0;display:grid;gap:10px}.liste a{display:block;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 16px;text-decoration:none}
.liste .tur{font-size:12px;font-weight:700;color:var(--coral);text-transform:uppercase;letter-spacing:.06em}
.etiket{display:inline-block;font-size:13px;font-weight:700;background:var(--mint2);border-radius:999px;padding:2px 10px}
footer{margin-top:48px;color:var(--muted);font-size:14px}"""

_KOPYA_JS = """<script>document.querySelectorAll("[data-kopya]").forEach(b=>b.addEventListener("click",()=>{const t=document.getElementById(b.dataset.kopya).innerText;
const ok=()=>{b.textContent="Copied";setTimeout(()=>b.textContent="Copy prompt",1600)};
if(navigator.clipboard)navigator.clipboard.writeText(t).then(ok,()=>{});else ok()}))</script>"""


def _sayfa(g: GelirAyar, baslik: str, aciklama: str, govde: str, yol: str = "") -> str:
    url = g.site_url.rstrip("/") + "/" + yol
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{_e(baslik)}</title><meta name="description" content="{_e(aciklama)}"><link rel="canonical" href="{_e(url)}">
<meta property="og:title" content="{_e(baslik)}"><meta property="og:description" content="{_e(aciklama)}">
<meta property="og:image" content="{_e(g.site_url.rstrip('/'))}/og.png"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{_e(g.site_url.rstrip('/'))}/logo.png"><link rel="alternate" type="application/rss+xml" href="{_e(g.site_url.rstrip('/'))}/feed.xml">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,700;12..96,800&display=swap">
<style>{_CSS}</style></head><body><main>
<a class="marka" href="{_e(g.site_url.rstrip('/'))}/"><img src="{_e(g.site_url.rstrip('/'))}/logo.png" alt="">Tiny Fixes</a>
{govde}
<footer>Tiny Fixes: small AI fixes for real problems. Every prompt is run on a real AI model before we post it, and we say where it fails.
Sample inputs are made up. Not medical, legal or financial advice.</footer>
</main>{_KOPYA_JS}</body></html>
"""


def _form(g: GelirAyar) -> str:
    """Ücretsiz paket formu (Kit). Ayar yoksa boş: sayfada vaat olmaz (F12)."""
    if not g.form_var:
        return ""
    return f"""<section class="kutu nane"><h2 style="margin-top:0">Get the free pack</h2>
<p style="margin:0">{_e(g.ucretsiz_paket_adi)}. Every prompt tested, each with its limit. Plus one tiny fix a week by email.</p>
<form action="{_e(g.bulten_form_action)}" method="post"><input type="email" name="{_e(g.bulten_email_alani)}" required
placeholder="you@example.com" aria-label="Email address"><button type="submit">Send me the pack</button></form>
<p class="kucuk">Free. Unsubscribe any time. We never sell or share your email.</p></section>"""


def _urun(g: GelirAyar, ozet: dict | None) -> str:
    """Ücretli paket kutusu. Paket henüz üretilmediyse ya da bağlantı yoksa görünmez; içerik özeti paketin kendisinden (F13)."""
    if not g.urun_var or not ozet or not ozet.get("sayi"):
        return ""
    kategoriler = ", ".join(k.lower() for k in ozet.get("kategoriler") or []) or "everyday problems"
    modeller = " and ".join(ozet.get("modeller") or []) or "a real AI model"
    return f"""<section class="kutu mercan"><h2 style="margin-top:0">{_e(g.urun_adi)}</h2>
<p style="margin:0 0 12px">{ozet["sayi"]} tested prompts in one PDF ({_e(kategoriler)}). Every prompt was run on {_e(modeller)},
with a short real output and its honest limit. {_e(g.urun_fiyat)}, one-time.</p>
<a class="dugme mercan" href="{_e(g.urun_url)}" rel="noopener">Get the library · {_e(g.urun_fiyat)}</a></section>"""


def _affiliate(g: GelirAyar, girdi: dict) -> str:
    """F4/F11: yalnızca kayıttaki denenmiş araç ve ayarlarda bağlantısı olan araç; 'affiliate' ibaresiyle."""
    arac = (girdi.get("arac") or {}).get("ad") if isinstance(girdi.get("arac"), dict) else None
    url = dict(g.affiliate).get(arac or "")
    if not (arac and url and girdi.get("komut") and girdi.get("cikti")):
        return ""
    return f'<p class="kucuk">Tool we tested: <a href="{_e(url)}" rel="sponsored noopener">{_e(arac)}</a> (affiliate link)</p>'


def _liste(g: GelirAyar, girdiler: list[dict]) -> str:
    satirlar = [f'<li><a href="{_e(sayfa_url(g, x["slug"]))}"><span class="tur">{_e({"news": "News"}.get(x["tur"], "Fix"))}'
                f'</span><br>{_e(x["baslik"])}</a></li>' for x in girdiler]
    return '<ul class="liste">' + "".join(satirlar) + "</ul>"


def fix_sayfasi(g: GelirAyar, x: dict, ozet: dict | None) -> str:
    p = [f'<h1>{_e(x["baslik"])}</h1>']
    if x.get("komut"):
        p.append(f'<p class="alt"><span class="etiket">Tested with {_e(x["model"])}</span> · {_e(x["tarih"])}</p>')
        p.append('<h2>The prompt</h2><pre id="komut">' + _e(x["komut"]) + '</pre><button type="button" data-kopya="komut">Copy prompt</button>')
        p.append('<p class="kucuk">Replace the part in &lt;angle brackets&gt; with your own material, then paste it into any AI assistant.</p>')
        p.append(f'<h2>What it did in our test</h2><p class="kucuk">Sample input (made up): {_e(x["ornek_girdi"][:300])}</p>'
                 f'<pre>{_e(x["cikti"][:900])}{"…" if len(x["cikti"]) > 900 else ""}</pre>')
        p.append(f'<h2>The limit</h2><p>{_e(x["sinir"])}</p>')
    if x.get("olgular"):
        p.append("<h2>Sources</h2><ul>" + "".join(
            f'<li>{_e(o["metin"])} ' + " ".join(f'<a href="{_e(u)}" rel="noopener nofollow">[{i}]</a>'
                                                 for i, u in enumerate(o["kaynaklar"], 1)) + "</li>" for o in x["olgular"]) + "</ul>")
    p += [_affiliate(g, x), _form(g), _urun(g, ozet)]
    aciklama = f"A tested AI prompt: {x['baslik']}. Tested with {x['model']}, with its limit." if x.get("komut") else x["baslik"]
    return _sayfa(g, f"{x['baslik']} | Tiny Fixes", aciklama, "\n".join(p), f"fix/{x['slug']}.html")


def ana_sayfa(g: GelirAyar, girdiler: list[dict], ozet: dict | None) -> str:
    son = list(reversed(girdiler))[:8]
    govde = ["<h1>Small AI fixes for real problems.</h1>",
             '<p class="alt">Each fix is one prompt we ran on a real AI model before posting it, with the model named and the limit said out loud.</p>',
             _form(g), _urun(g, ozet)]
    if son:
        govde += ["<h2>Latest fixes</h2>", _liste(g, son)]
        if len(girdiler) > len(son):
            govde.append(f'<p><a href="{_e(g.site_url.rstrip("/"))}/library.html">All {len(girdiler)} fixes</a></p>')
    else:
        govde.append('<p class="kucuk">The first fixes are on their way.</p>')
    return _sayfa(g, "Tiny Fixes: small AI fixes for real problems", "Tested AI prompts for everyday problems. Every prompt is run "
                  "before we post it, with the model named and its limit.", "\n".join(govde))


def kutuphane_sayfasi(g: GelirAyar, girdiler: list[dict], ozet: dict | None) -> str:
    govde = ["<h1>All tiny fixes</h1>", f'<p class="alt">{len(girdiler)} tested fixes, newest first.</p>',
             _liste(g, list(reversed(girdiler))), _form(g), _urun(g, ozet)]
    return _sayfa(g, "All fixes | Tiny Fixes", "Every tested AI prompt Tiny Fixes has posted.", "\n".join(govde), "library.html")


def rss(g: GelirAyar, girdiler: list[dict]) -> str:
    """RSS: bülten aracının "RSS'ten e-posta" özelliği (ücretli planlarda) ve okuyucular için."""
    ogeler = []
    for x in list(reversed(girdiler))[:30]:
        tarih = format_datetime(datetime.fromisoformat(x["tarih"] + "T12:00:00+00:00"))
        ozet = f"Tested with {x['model']}. The limit: {x['sinir']}" if x.get("komut") else x["baslik"]
        ogeler.append(f"<item><title>{_e(x['baslik'])}</title><link>{_e(sayfa_url(g, x['slug']))}</link>"
                      f"<guid>{_e(sayfa_url(g, x['slug']))}</guid><pubDate>{tarih}</pubDate><description>{_e(ozet)}</description></item>")
    return (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Tiny Fixes</title>'
            f'<link>{_e(g.site_url)}</link><description>Small AI fixes for real problems. Every prompt tested.</description>'
            + "".join(ogeler) + "</channel></rss>\n")


def site_metni(x: dict) -> str:
    return " ".join([x.get("baslik", ""), x.get("komut", ""), x.get("cikti", ""), x.get("sinir", "")]
                    + [o["metin"] for o in x.get("olgular") or []])


def uret(g: GelirAyar, girdiler: list[dict], paket_ozeti: dict | None = None, klasor=None) -> list[str]:
    """Siteyi yazar; yalnızca içeriği değişen dosyalar. Değişen yolların listesi. F5'e takılan girdi sayfa almaz (F11)."""
    klasor = klasor or KLASOR
    guvenli = [x for x in girdiler if not flood_denetci.guvensiz_alan(site_metni(x))]
    dosyalar = {"index.html": ana_sayfa(g, guvenli, paket_ozeti), "library.html": kutuphane_sayfasi(g, guvenli, paket_ozeti),
                "feed.xml": rss(g, guvenli)}
    for x in guvenli:
        dosyalar[f"fix/{x['slug']}.html"] = fix_sayfasi(g, x, paket_ozeti)
    degisen = []
    for yol, icerik in dosyalar.items():
        hedef = klasor / yol
        if hedef.exists() and hedef.read_text(encoding="utf-8") == icerik:
            continue
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_text(icerik, encoding="utf-8")
        degisen.append(yol)
    for ad, kaynak in (("og.png", KAPAK), ("logo.png", LOGO)):
        if not (klasor / ad).exists() and kaynak.exists():
            klasor.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(kaynak, klasor / ad)
            degisen.append(ad)
    return degisen
