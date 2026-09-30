"""Kullanım: python -m beyin ["bu çalışmaya özel ek not"]"""

import os
import sys

from .firtina import BeyinHatasi, Toplanti, kaydet


def main(argv: list[str]) -> int:
    toplanti = Toplanti(ek_not=" ".join(argv))
    try:
        ozet, tutanak = toplanti.calistir()
    except BeyinHatasi as e:
        # Yarım kalan tartışma da kaybolmasın.
        kaydet(f"# Beyin fırtınası yarım kaldı\n\n{e}", f"# Yarım tutanak\n\n{toplanti.kayit.metin()}", toplanti.simdi)
        print(f"❌ {e}", file=sys.stderr)
        return 1
    karar, tutanak_yolu = kaydet(ozet, tutanak, toplanti.simdi)
    print(f"Karar: {karar}\nTutanak: {tutanak_yolu}")
    if ozet_dosyasi := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(ozet_dosyasi, "a", encoding="utf-8") as f:
            f.write(ozet + "\n")
    if cikti := os.environ.get("GITHUB_OUTPUT"):
        with open(cikti, "a", encoding="utf-8") as f:
            f.write(f"karar={karar}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
