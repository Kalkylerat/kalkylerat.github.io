"""Mr. Likely hesabının, mevcut X uygulamasına (Kalkylerat'ın uygulaması) paylaşım izni vermesi.

Ayrı bir geliştirici hesabı gerekmez: uygulama aynı kalır, Mr. Likely hesabı "Authorize app" ile izin verir ve o hesaba
ait erişim anahtarı üretilir (X'in standart OAuth 1.0a akışı). Anahtar depoda ŞİFRELİ durur (data/likely_x.enc);
şifre uygulamanın gizli anahtarından türetilir, yani yalnızca GitHub'daki gizli anahtarı bilen çalışma açabilir.

1) baslat(): izin bağlantısını üretir. Sahibi Mr. Likely hesabıyla açar, "Authorize app"e basar; tarayıcı
   https://github.com/?oauth_token=...&oauth_verifier=... adresine döner.
2) tamamla(): o adresteki iki değerle erişim anahtarını alır, hesabın adını doğrular ve şifreli kaydeder."""

import base64
import hashlib
import json
import re

from cryptography.fernet import Fernet, InvalidToken
from requests_oauthlib import OAuth1Session

from . import config

DOSYA = config.ROOT / "data" / "likely_x.enc"
GERI_DONUS = "https://github.com"
ISTEK, IZIN, ERISIM = ("https://api.x.com/oauth/request_token", "https://api.x.com/oauth/authorize",
                       "https://api.x.com/oauth/access_token")
YASAK_HESAPLAR = {"kalkylerat", "kalkyleratkonto"}  # yanlış hesapla izin verilirse kaydedilmez


def _kasa(api_secret: str) -> Fernet:
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(("mr-likely|" + api_secret).encode()).digest()))


def baslat(api_key: str, api_secret: str) -> str:
    """İzin bağlantısı (gizli bilgi içermez; birkaç dakika geçerlidir)."""
    oturum = OAuth1Session(api_key, client_secret=api_secret, callback_uri=GERI_DONUS)
    oturum.fetch_request_token(ISTEK)
    return oturum.authorization_url(IZIN)


def coz(metin: str) -> tuple[str, str] | None:
    """Dönülen adresten (ya da yapıştırılan parçadan) oauth_token ve oauth_verifier."""
    token = re.search(r"oauth_token=([\w-]+)", metin or "")
    dogrulama = re.search(r"oauth_verifier=([\w-]+)", metin or "")
    return (token.group(1), dogrulama.group(1)) if token and dogrulama else None


def tamamla(api_key: str, api_secret: str, token: str, dogrulama: str) -> str:
    """Erişim anahtarını alır ve şifreli kaydeder. İzin veren hesabın kullanıcı adını döndürür."""
    oturum = OAuth1Session(api_key, client_secret=api_secret, resource_owner_key=token, verifier=dogrulama)
    cevap = oturum.fetch_access_token(ERISIM)
    hesap = cevap.get("screen_name", "")
    if hesap.lower() in YASAK_HESAPLAR:
        raise RuntimeError(f"İzin @{hesap} hesabıyla verildi; Mr. Likely hesabıyla giriş yapıp yeniden deneyin. Kaydedilmedi.")
    kaydet(api_secret, cevap["oauth_token"], cevap["oauth_token_secret"], hesap)
    return hesap


def kaydet(api_secret: str, token: str, gizli: str, hesap: str) -> None:
    veri = json.dumps({"token": token, "secret": gizli, "hesap": hesap}).encode()
    DOSYA.write_bytes(_kasa(api_secret).encrypt(veri) + b"\n")


def anahtarlar(api_secret: str) -> dict | None:
    """Kayıtlı erişim anahtarı ({"token", "secret", "hesap"}); yoksa ya da açılamıyorsa None."""
    try:
        return json.loads(_kasa(api_secret).decrypt(DOSYA.read_bytes().strip()))
    except (FileNotFoundError, InvalidToken, ValueError):
        return None
