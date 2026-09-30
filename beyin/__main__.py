"""Kullanım: python -m beyin ["bu çalışmaya özel ek not"]"""

import os
import sys

import anthropic

from .firtina import BeyinHatasi, Toplanti, kaydet


def main(argv: list[str]) -> int:
    toplanti = Toplanti(ek_not=" ".join(argv))
    try:
        ozet, tutanak = toplanti.calistir()
    except (BeyinHatasi, anthropic.APIError) as e:
        # Biten turlar devam dosyasında duruyor; sonraki çalışma kaldığı yerden sürer.
        mesaj = (f"❌ Beyin fırtınası yarım kaldı: {e}\n\n{len(toplanti.kayit.bolumler)} bölüm kaydedildi; "
                 "bir sonraki çalışma kaldığı yerden devam eder.")
        print(mesaj, file=sys.stderr)
        if ozet_dosyasi := os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(ozet_dosyasi, "a", encoding="utf-8") as f:
                f.write(mesaj + "\n")
        return 1
    if toplanti.kayit.dosya:
        toplanti.kayit.dosya.unlink(missing_ok=True)
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
