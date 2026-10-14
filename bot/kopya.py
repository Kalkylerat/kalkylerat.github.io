"""Kopyalama sayfası: cevap taslakları için tek dokunuşla "kopyala ve postu aç" düğmeli sayfa (GitHub Pages,
docs/kit/<tarih>/). Telefonda GitHub'daki metni seçip kopyalamak zahmetli; X'in cevap bağlantısı (web intent)
Android uygulamasında cevabı ayrı post olarak atıyordu (14 Ekim, Mr. Likely). Sayfa yalnızca panoya kopyalar ve
postu açar: cevabı sahibi X'te yapıştırıp kendisi gönderir (SÖZLEŞME D3).

Her bildirim kendi dosyasını alır (önbellekte eski sürüm görünmesin). 7 günden eski klasörler silinir."""

import html
import json
from datetime import datetime, timedelta

from . import config

KLASOR = config.ROOT / "docs" / "kit"
SITE = "https://kalkylerat.github.io/kit"

_SAYFA = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>{baslik}</title>
<style>
:root{{color-scheme:dark}}*{{box-sizing:border-box}}body{{overflow-wrap:anywhere;margin:0;background:#000;color:#e7e9ea;font:16px/1.45 -apple-system,system-ui,Roboto,sans-serif}}
main{{max-width:640px;margin:0 auto;padding:16px}}h1{{font-size:18px;margin:4px 0 4px}}.not{{color:#ffd166;margin:0 0 12px}}
.oge{{border:1px solid #2f3336;border-radius:14px;padding:14px;margin:0 0 18px}}.kim{{color:#71767b;font-size:14px}}
.post{{color:#c4c9cc;font-size:14px;margin:6px 0 10px;white-space:pre-wrap}}.ac{{color:#1d9bf0;font-size:14px}}
.taslak{{background:#16181c;border-radius:12px;padding:12px;margin:10px 0 0}}.metin{{white-space:pre-wrap;margin:0 0 10px}}
button{{width:100%;border:0;border-radius:999px;padding:13px;font-size:16px;font-weight:700;background:#1d9bf0;color:#fff}}
button.ikinci{{background:#2f3336;margin-top:8px;font-weight:600}}
</style></head><body><main>
<h1>{baslik}</h1>{uyari}
<p class="kim">Düğme metni panoya kopyalar ve postu X'te açar. X'te <b>Yanıtla</b>'ya dokun, kutuya uzun basıp
<b>Yapıştır</b>, sonra gönder.</p>
{ogeler}
</main><script>
const V = {veri};
function kopyala(i, ac, btn) {{
  const t = V[i].metin, git = () => {{ if (ac) setTimeout(() => location.href = V[i].url, 350); }};
  const tamam = () => {{ btn.textContent = "✅ Kopyalandı" + (ac ? ", post açılıyor…" : ""); git(); }};
  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(t).then(tamam, () => yedek(t, tamam));
  }} else {{ yedek(t, tamam); }}
}}
function yedek(t, tamam) {{
  const a = document.createElement("textarea"); a.value = t; document.body.appendChild(a); a.select();
  try {{ document.execCommand("copy"); }} catch (e) {{}} a.remove(); tamam();
}}
</script></body></html>
"""


def _e(t: str) -> str:
    return html.escape(t or "", quote=True)


def sayfa_yaz(dosya_adi: str, baslik: str, ogeler: list[dict], simdi: datetime, uyari: str = "") -> str:
    """ogeler: {kim, post, url, not, taslaklar: [(etiket, metin)]}. Sayfayı yazar, herkese açık adresini döner."""
    klasor = KLASOR / simdi.date().isoformat()
    klasor.mkdir(parents=True, exist_ok=True)
    veri, bloklar = [], []
    for o in ogeler:
        taslak_html = []
        for etiket, metin in o["taslaklar"]:
            i = len(veri)
            veri.append({"metin": metin, "url": o["url"]})
            taslak_html.append(
                f'<div class="taslak"><div class="kim">{_e(etiket)}</div><p class="metin">{_e(metin)}</p>'
                f'<button onclick="kopyala({i},true,this)">📋 Kopyala ve postu aç</button>'
                f'<button class="ikinci" onclick="kopyala({i},false,this)">Sadece kopyala</button></div>')
        bloklar.append(f'<section class="oge"><div class="kim">{_e(o["kim"])}</div>'
                       + (f'<p class="not">📝 {_e(o["not"])}</p>' if o.get("not") else "")
                       + f'<p class="post">{_e((o.get("post") or "")[:400])}</p>'
                       f'<a class="ac" href="{_e(o["url"])}">Postu X\'te gör</a>' + "".join(taslak_html) + "</section>")
    (klasor / dosya_adi).write_text(_SAYFA.format(
        baslik=_e(baslik), uyari=f'<p class="not">{_e(uyari)}</p>' if uyari else "", ogeler="\n".join(bloklar),
        veri=json.dumps(veri, ensure_ascii=False).replace("</", "<\\/")), encoding="utf-8")
    _eskileri_sil(simdi)
    return f"{SITE}/{simdi.date().isoformat()}/{dosya_adi}"


def _eskileri_sil(simdi: datetime) -> None:
    sinir = (simdi - timedelta(days=7)).date().isoformat()
    for eski in KLASOR.iterdir() if KLASOR.exists() else []:
        if eski.is_dir() and eski.name < sinir:
            for f in eski.iterdir():
                f.unlink()
            eski.rmdir()
