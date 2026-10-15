"""Tiny Fixes paketleri (PDF): ücretsiz başlangıç paketi ve ücretli kütüphane (SOZLESME F12, F13).

Metin gerçek metindir (kopyalanabilir): alıcı komutu PDF'ten kopyalayıp yapıştırır. Her komutun yanında hangi modelle
denendiği, örnek girdinin uydurma olduğu, gerçek çıktıdan kısa bir parça ve sınırı yazar. Yalnızca kütüphane
girdilerindeki metin kullanılır; yeni iddia üretilmez."""

from fpdf import FPDF

from . import config

FONT = config.ROOT / "marka" / "font"
LOGO = config.ROOT / "marka" / "tiny_fixes_logo.png"
MUREKKEP, NANE, MERCAN, SOLUK, KREM, NANE_ACIK = (34, 34, 59), (94, 211, 168), (255, 122, 107), (110, 113, 145), (255, 246, 234), (221, 245, 236)


class _Pdf(FPDF):
    def multi_cell(self, *a, align="L", **k):  # iki yana yaslı metin komutlarda boşluk açıyor: sola yaslı
        return super().multi_cell(*a, align=align, **k)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_font("sans", size=8)
        self.set_text_color(*SOLUK)
        self.cell(0, 8, f"Tiny Fixes · {self.page_no()}", align="R")


def _temiz(t: str) -> str:
    """DejaVu'da olmayan karakterler ve görünmez boşluklar PDF'i bozmasın."""
    return "".join(c for c in (t or "").replace(" ", " ").replace("​", "") if c >= " " or c == "\n")


def paket(girdiler: list[dict], baslik: str, alt_baslik: str) -> bytes:
    """Girdilerden PDF. Kategori sırasıyla; kapak, kullanım sayfası, içindekiler, komut başına bir bölüm."""
    pdf = _Pdf(format="A4")
    pdf.set_auto_page_break(True, margin=18)
    pdf.set_margins(18, 18, 18)
    pdf.add_font("sans", "", str(FONT / "DejaVuSans.ttf"))
    pdf.add_font("sans", "B", str(FONT / "DejaVuSans-Bold.ttf"))
    pdf.add_font("mono", "", str(FONT / "DejaVuSansMono.ttf"))
    sirali = sorted(girdiler, key=lambda g: (g.get("kategori") or "~", g["baslik"]))
    modeller = sorted({g["model"] for g in sirali if g.get("model")})

    # Kapak
    pdf.add_page()
    pdf.set_fill_color(*KREM)
    pdf.rect(0, 0, 210, 297, "F")
    if LOGO.exists():
        pdf.image(str(LOGO), x=80, y=48, w=50)
    pdf.set_y(112)
    pdf.set_text_color(*MUREKKEP)
    pdf.set_font("sans", "B", 30)
    pdf.multi_cell(0, 13, _temiz(baslik), align="C")
    pdf.ln(4)
    pdf.set_font("sans", size=13)
    pdf.set_text_color(*SOLUK)
    pdf.multi_cell(0, 7, _temiz(alt_baslik), align="C")
    pdf.ln(10)
    pdf.set_font("sans", size=11)
    pdf.set_text_color(*MUREKKEP)
    pdf.multi_cell(0, 6, _temiz(f"{len(sirali)} prompts. Every one was run on {', '.join(modeller) or 'a real AI model'} "
                                "before it went in, and each comes with its honest limit."), align="C")

    # Kullanım
    pdf.add_page()
    pdf.set_font("sans", "B", 18)
    pdf.cell(0, 10, "How to use this pack", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("sans", size=11)
    for satir in ("1. Find the problem you have in the contents.",
                  "2. Copy the prompt into any AI assistant (ChatGPT, Claude, Gemini...).",
                  "3. Replace the part in <angle brackets> with your own material.",
                  "4. Read the limit line: it says when the prompt is not the right tool.",
                  "",
                  "The sample inputs were made up for testing. The outputs shown are short, real excerpts from that test run. "
                  "Your result will differ with your own material and model."):
        pdf.multi_cell(0, 6.5, _temiz(satir), new_x="LMARGIN", new_y="NEXT")

    # İçindekiler
    pdf.ln(6)
    pdf.set_font("sans", "B", 14)
    pdf.cell(0, 9, "Contents", new_x="LMARGIN", new_y="NEXT")
    kategori = None
    for i, g in enumerate(sirali, 1):
        if g.get("kategori") != kategori:
            kategori = g.get("kategori")
            pdf.set_font("sans", "B", 11)
            pdf.set_text_color(*MERCAN)
            pdf.cell(0, 8, _temiz(kategori or "More"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*MUREKKEP)
        pdf.set_font("sans", size=10)
        pdf.multi_cell(0, 5.5, _temiz(f"{i}. {g['baslik']}"), new_x="LMARGIN", new_y="NEXT")

    # Komutlar
    for i, g in enumerate(sirali, 1):
        pdf.add_page()
        pdf.set_font("sans", size=9)
        pdf.set_text_color(*MERCAN)
        pdf.cell(0, 6, _temiz(f"{g.get('kategori') or 'Fix'} · #{i}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*MUREKKEP)
        pdf.set_font("sans", "B", 16)
        pdf.multi_cell(0, 8, _temiz(g["baslik"]), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        pdf.set_font("sans", "B", 10)
        pdf.cell(0, 6, "The prompt", new_x="LMARGIN", new_y="NEXT")
        pdf.set_fill_color(*NANE_ACIK)
        pdf.set_font("mono", size=9.5)
        pdf.multi_cell(0, 5.5, _temiz(g["komut"]), fill=True, padding=3, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        pdf.set_font("sans", size=9)
        pdf.set_text_color(*SOLUK)
        pdf.multi_cell(0, 5, _temiz(f"Tested with {g['model']} on a made-up sample input."), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*MUREKKEP)
        pdf.ln(2)
        pdf.set_font("sans", "B", 10)
        pdf.cell(0, 6, "Part of the real output", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("sans", size=9.5)
        parca = g["cikti"][:700] + ("..." if len(g["cikti"]) > 700 else "")
        pdf.multi_cell(0, 5.2, _temiz(parca), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        pdf.set_font("sans", "B", 10)
        pdf.set_text_color(*MERCAN)
        pdf.cell(0, 6, "The limit", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*MUREKKEP)
        pdf.set_font("sans", size=10)
        pdf.multi_cell(0, 5.5, _temiz(g["sinir"]), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
