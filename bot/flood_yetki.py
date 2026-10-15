"""Prompt Proof hesabının X izni ve Instagram anahtarı (şifreli, depoda).

X: Mr. Likely'deki akışın aynısı (likely_yetki): ayrı geliştirici hesabı gerekmez, yeni hesap mevcut uygulamaya
"Authorize app" ile izin verir. Anahtar `data/flood_x.enc` içinde şifreli durur.
Instagram: uzun ömürlü (60 gün) Instagram Login anahtarı `data/flood_ig.enc` içinde şifreli durur; bot süresi
dolmadan yeniler (GitHub gizli anahtarı elle güncellenemeyeceği için yenilenen anahtar buraya yazılır).
Şifre, X uygulamasının gizli anahtarından türetilir; yalnızca GitHub'daki gizli anahtarı bilen çalışma açabilir."""

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken
from requests_oauthlib import OAuth1Session

from . import config, likely_yetki

X_DOSYA = config.ROOT / "data" / "flood_x.enc"
IG_DOSYA = config.ROOT / "data" / "flood_ig.enc"
YASAK_HESAPLAR = {"kalkylerat", "kalkyleratkonto"}  # yanlış hesapla izin verilirse kaydedilmez
IG_YENILE_GUN = 30  # anahtar 60 gün geçerli; 30 günde bir yenilenir


def _kasa(api_secret: str) -> Fernet:
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(("prompt-proof|" + api_secret).encode()).digest()))


def _yasak(api_secret: str) -> set[str]:
    """Kalkylerat hesapları ve Mr. Likely hesabı: yeni hesabın yerine yanlışlıkla bunlar yetkilendirilmesin."""
    yasak = set(YASAK_HESAPLAR)
    mr = likely_yetki.anahtarlar(api_secret)
    if mr and mr.get("hesap"):
        yasak.add(mr["hesap"].lower())
    return yasak


baslat = likely_yetki.baslat
coz = likely_yetki.coz


def tamamla(api_key: str, api_secret: str, token: str, dogrulama: str, yasak: set[str] | None = None) -> str:
    """X erişim anahtarını alır ve şifreli kaydeder. İzin veren hesabın kullanıcı adını döndürür."""
    oturum = OAuth1Session(api_key, client_secret=api_secret, resource_owner_key=token, verifier=dogrulama)
    cevap = oturum.fetch_access_token(likely_yetki.ERISIM)
    hesap = cevap.get("screen_name", "")
    if hesap.lower() in (yasak if yasak is not None else _yasak(api_secret)):
        raise RuntimeError(f"İzin @{hesap} hesabıyla verildi; Prompt Proof hesabıyla giriş yapıp yeniden deneyin. Kaydedilmedi.")
    kaydet_x(api_secret, cevap["oauth_token"], cevap["oauth_token_secret"], hesap)
    return hesap


def kaydet_x(api_secret: str, token: str, gizli: str, hesap: str) -> None:
    X_DOSYA.write_bytes(_kasa(api_secret).encrypt(json.dumps({"token": token, "secret": gizli, "hesap": hesap}).encode()) + b"\n")


def x_anahtarlar(api_secret: str) -> dict | None:
    try:
        return json.loads(_kasa(api_secret).decrypt(X_DOSYA.read_bytes().strip()))
    except (FileNotFoundError, InvalidToken, ValueError):
        return None


def kaydet_ig(api_secret: str, token: str, ig_id: str, simdi: datetime) -> None:
    veri = {"token": token, "ig_id": str(ig_id), "yenilenme": simdi.astimezone(timezone.utc).isoformat(timespec="seconds")}
    IG_DOSYA.write_bytes(_kasa(api_secret).encrypt(json.dumps(veri).encode()) + b"\n")


def ig_anahtar(api_secret: str) -> dict | None:
    """{"token", "ig_id", "yenilenme"}; yoksa None."""
    try:
        return json.loads(_kasa(api_secret).decrypt(IG_DOSYA.read_bytes().strip()))
    except (FileNotFoundError, InvalidToken, ValueError):
        return None


def yenileme_gerekli(kayit: dict, simdi: datetime) -> bool:
    return simdi - datetime.fromisoformat(kayit["yenilenme"]) >= timedelta(days=IG_YENILE_GUN)
