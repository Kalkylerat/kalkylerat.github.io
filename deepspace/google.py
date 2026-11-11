"""Google Drive ve YouTube Data API (SOZLESME.md G8): ses alma, paket teslimi, onaylı ve gizli yükleme.

Ücretsiz API'ler; kimlik bilgileri ortam değişkenlerinden okunur (sohbete ya da depoya asla yazılmaz):
    DSL_GOOGLE_CLIENT_ID, DSL_GOOGLE_CLIENT_SECRET, DSL_GOOGLE_REFRESH_TOKEN
Kurulum adımları: deepspace/KURULUM.md. Gereken hostlar: oauth2.googleapis.com, www.googleapis.com.

Yükleme kuralları (G8, 10 Kasım 2026): rapor.json yeşil olmalı; cikti/onay.json denetçinin kararıdır ve videonun
şimdiki haliyle eşleşmeli; yayın her zaman gizli + planlı (publishAt, karardan en az 24 saat sonra); sahibine o arada
bilgi gider; cikti/iptal.json varsa yükleme yok. "Altered or synthetic content" işaretli.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
YT_UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"
YT = "https://www.googleapis.com/youtube/v3"
PARCA = 64 * 1024 * 1024  # devam ettirilebilir yüklemede parça boyu (256 KiB'nin katı)


class GoogleHatasi(RuntimeError):
    pass


def erisim_belirteci(oturum=requests) -> str:
    eksik = [k for k in ("DSL_GOOGLE_CLIENT_ID", "DSL_GOOGLE_CLIENT_SECRET", "DSL_GOOGLE_REFRESH_TOKEN")
             if not os.environ.get(k)]
    if eksik:
        raise GoogleHatasi(f"ortam değişkeni eksik: {', '.join(eksik)} (deepspace/KURULUM.md)")
    r = oturum.post(TOKEN_URL, data={"client_id": os.environ["DSL_GOOGLE_CLIENT_ID"],
                                     "client_secret": os.environ["DSL_GOOGLE_CLIENT_SECRET"],
                                     "refresh_token": os.environ["DSL_GOOGLE_REFRESH_TOKEN"],
                                     "grant_type": "refresh_token"}, timeout=30)
    if r.status_code != 200:
        raise GoogleHatasi(f"belirteç alınamadı ({r.status_code}): {r.text[:300]}")
    return r.json()["access_token"]


def _baslik(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


# ---------- Drive ----------
def klasor_bul(ad: str, tok: str, ust: str | None = None, oturum=requests) -> str | None:
    q = f"mimeType='application/vnd.google-apps.folder' and name='{ad}' and trashed=false"
    if ust:
        q += f" and '{ust}' in parents"
    r = oturum.get(f"{DRIVE}/files", headers=_baslik(tok), params={"q": q, "fields": "files(id,name)"}, timeout=30)
    r.raise_for_status()
    dosyalar = r.json().get("files", [])
    return dosyalar[0]["id"] if dosyalar else None


def klasor_yolu(yol: str, tok: str, olustur: bool = False, oturum=requests) -> str:
    """'DeepSpaceLog/001' gibi bir yolu klasör kimliğine çevirir (gerekirse oluşturur)."""
    ust = None
    for ad in [p for p in yol.split("/") if p]:
        bulunan = klasor_bul(ad, tok, ust, oturum)
        if not bulunan:
            if not olustur:
                raise GoogleHatasi(f"Drive'da klasör yok: {yol}")
            govde = {"name": ad, "mimeType": "application/vnd.google-apps.folder"}
            if ust:
                govde["parents"] = [ust]
            r = oturum.post(f"{DRIVE}/files", headers=_baslik(tok), json=govde, params={"fields": "id"}, timeout=30)
            r.raise_for_status()
            bulunan = r.json()["id"]
        ust = bulunan
    return ust


def drive_listele(klasor_id: str, tok: str, oturum=requests) -> list[dict]:
    r = oturum.get(f"{DRIVE}/files", headers=_baslik(tok),
                   params={"q": f"'{klasor_id}' in parents and trashed=false", "fields": "files(id,name,size)",
                           "pageSize": 200}, timeout=30)
    r.raise_for_status()
    return r.json().get("files", [])


def drive_indir(dosya_id: str, hedef: Path, tok: str, oturum=requests) -> Path:
    with oturum.get(f"{DRIVE}/files/{dosya_id}", headers=_baslik(tok), params={"alt": "media"}, stream=True,
                    timeout=120) as r:
        r.raise_for_status()
        with open(hedef, "wb") as f:
            for blok in r.iter_content(8 * 1024 * 1024):
                f.write(blok)
    return hedef


def _devam_ettir(oturum_url: str, dosya: Path, mime: str, oturum=requests) -> dict:
    boyut = dosya.stat().st_size
    with open(dosya, "rb") as f:
        bas = 0
        while bas < boyut:
            veri = f.read(PARCA)
            son = bas + len(veri) - 1
            r = oturum.put(oturum_url, data=veri, timeout=600,
                           headers={"Content-Length": str(len(veri)), "Content-Type": mime,
                                    "Content-Range": f"bytes {bas}-{son}/{boyut}"})
            if r.status_code in (200, 201):
                return r.json()
            if r.status_code != 308:
                raise GoogleHatasi(f"yükleme kesildi ({r.status_code}): {r.text[:300]}")
            bas = son + 1
    raise GoogleHatasi("yükleme tamamlanmadı")


def drive_yukle(dosya: Path, klasor_id: str, tok: str, mime: str = "application/octet-stream",
                oturum=requests) -> str:
    r = oturum.post(DRIVE_UPLOAD, params={"uploadType": "resumable", "fields": "id"}, timeout=30,
                    headers={**_baslik(tok), "X-Upload-Content-Type": mime},
                    json={"name": dosya.name, "parents": [klasor_id]})
    if r.status_code != 200:
        raise GoogleHatasi(f"Drive yükleme başlatılamadı ({r.status_code}): {r.text[:300]}")
    return _devam_ettir(r.headers["Location"], dosya, mime, oturum)["id"]


# ---------- onay ----------
def video_imzasi(video: Path) -> dict:
    s = video.stat()
    return {"boyut": s.st_size, "degisme": int(s.st_mtime)}


BILDIRIM_SAATI = 24  # karar ile yayın arası; sahibi bu sürede bilgilendirilir ve isterse iptal eder


def _zaman_oku(metin: str) -> datetime:
    return datetime.fromisoformat(metin.replace("Z", "+00:00"))


# İlk görevlerde son söz sahibinindir (G8, 11 Kasım 2026, sahibinin onayıyla; bağımsız inceleme önerisi).
SAHIP_ONAYI_ILK_GOREV = 5


def _gorev_no(cikti: Path) -> int | None:
    import tomllib
    yol = Path(cikti).parent / "gorev.toml"
    try:
        return int(tomllib.loads(yol.read_text(encoding="utf-8"))["no"])
    except (OSError, ValueError, KeyError):
        return None


def onay_yaz(cikti: Path, kim: str, yayin_zamani: str, simdi: datetime | None = None) -> Path:
    """Karar (G8): rapor yeşil, yayın saati karardan en az BILDIRIM_SAATI saat sonra. İlk SAHIP_ONAYI_ILK_GOREV
    görevde kararı yalnız sahibi verir (`kim="sahip"`, sahibinin sohbette yazdığı `ok`tan sonra)."""
    simdi = simdi or datetime.now(timezone.utc)
    no = _gorev_no(cikti)
    if no is not None and no <= SAHIP_ONAYI_ILK_GOREV and kim != "sahip":
        raise GoogleHatasi(f"görev {no:03d}: ilk {SAHIP_ONAYI_ILK_GOREV} görevde sahibinin ok'u olmadan yayın yok (G8)")
    rapor = json.loads((cikti / "rapor.json").read_text(encoding="utf-8"))
    if not rapor.get("gecti"):
        raise GoogleHatasi("rapor.json kırmızı: video yayına planlanamaz (G8)")
    if (cikti / "iptal.json").exists():
        raise GoogleHatasi("sahibi iptal etmiş (iptal.json): yayın planlanmaz (G8)")
    if not yayin_zamani or _zaman_oku(yayin_zamani) < simdi + timedelta(hours=BILDIRIM_SAATI):
        raise GoogleHatasi(f"yayın saati karardan en az {BILDIRIM_SAATI} saat sonra olmalı (G8)")
    onay = {"karar_veren": kim, "zaman": simdi.isoformat(timespec="seconds"),
            "video": video_imzasi(cikti / "video.mp4"), "yayin_zamani": yayin_zamani,
            "not": "sahibi izleyicidir; bilgi gider, iptal.json her zaman önceliklidir"}
    yol = cikti / "onay.json"
    yol.write_text(json.dumps(onay, indent=2, ensure_ascii=False), encoding="utf-8")
    return yol


def iptal_yaz(cikti: Path, neden: str = "") -> Path:
    """Sahibinin acil freni (G8)."""
    yol = cikti / "iptal.json"
    yol.write_text(json.dumps({"zaman": datetime.now(timezone.utc).isoformat(timespec="seconds"), "neden": neden},
                              ensure_ascii=False), encoding="utf-8")
    return yol


def onay_kontrol(cikti: Path) -> dict:
    rapor_yol, onay_yol = cikti / "rapor.json", cikti / "onay.json"
    if (cikti / "iptal.json").exists():
        raise GoogleHatasi("sahibi iptal etmiş (iptal.json): yükleme yapılmaz (G8)")
    if not rapor_yol.exists() or not json.loads(rapor_yol.read_text(encoding="utf-8")).get("gecti"):
        raise GoogleHatasi("rapor.json yok ya da kırmızı (G8)")
    if not onay_yol.exists():
        raise GoogleHatasi("onay.json yok: denetçi kararı olmadan yükleme yapılmaz (G8)")
    onay = json.loads(onay_yol.read_text(encoding="utf-8"))
    if onay.get("video") != video_imzasi(cikti / "video.mp4"):
        raise GoogleHatasi("video karardan sonra değişmiş: yeniden karar gerekli (G8)")
    if not onay.get("yayin_zamani"):
        raise GoogleHatasi("planlı yayın saati yok (G8)")
    return onay


def youtube_planli_yayini_geri_al(video_id: str, oturum=requests) -> None:
    """iptal: videoyu gizli bırakır, planlı yayını kaldırır (G8)."""
    tok = erisim_belirteci(oturum)
    r = oturum.put(f"{YT}/videos", params={"part": "status"}, headers=_baslik(tok), timeout=30,
                   json={"id": video_id, "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False}})
    if r.status_code != 200:
        raise GoogleHatasi(f"planlı yayın geri alınamadı ({r.status_code}): {r.text[:300]}")


# ---------- YouTube ----------
def youtube_govdesi(yt: dict, yayin_zamani: str | None) -> dict:
    durum = {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True,
             "embeddable": True}
    if yayin_zamani:
        durum["publishAt"] = yayin_zamani  # gizli kalır, bu saatte kendiliğinden yayına girer
    return {"snippet": {"title": yt["baslik"], "description": yt["aciklama"], "tags": yt["etiketler"],
                        "categoryId": yt.get("kategori", "10"), "defaultLanguage": yt.get("dil", "en"),
                        "defaultAudioLanguage": "zxx"},
            "status": durum}


def youtube_yukle(cikti: Path, oturum=requests) -> dict:
    onay = onay_kontrol(cikti)
    yt = json.loads((cikti / "youtube.json").read_text(encoding="utf-8"))
    if not yt.get("sentetik_icerik"):
        raise GoogleHatasi("sentetik içerik etiketi kapalı (G9)")
    tok = erisim_belirteci(oturum)
    govde = youtube_govdesi(yt, onay.get("yayin_zamani"))
    video = cikti / "video.mp4"
    r = oturum.post(YT_UPLOAD, params={"uploadType": "resumable", "part": "snippet,status"}, json=govde,
                    timeout=30, headers={**_baslik(tok), "X-Upload-Content-Type": "video/mp4",
                                         "X-Upload-Content-Length": str(video.stat().st_size)})
    if r.status_code != 200:
        raise GoogleHatasi(f"YouTube yükleme başlatılamadı ({r.status_code}): {r.text[:300]}")
    sonuc = _devam_ettir(r.headers["Location"], video, "video/mp4", oturum)
    vid = sonuc["id"]
    kapak = cikti / "kapak_1.jpg"
    if kapak.exists():
        with open(kapak, "rb") as f:
            k = oturum.post("https://www.googleapis.com/upload/youtube/v3/thumbnails/set", params={"videoId": vid},
                            headers={**_baslik(tok), "Content-Type": "image/jpeg"}, data=f.read(), timeout=60)
        if k.status_code != 200:
            sonuc["kapak_hatasi"] = f"{k.status_code}: {k.text[:200]}"  # doğrulanmamış kanalda kapak yüklenemez
    (cikti / "yukleme.json").write_text(json.dumps({"video_id": vid, "durum": govde["status"]}, indent=2),
                                        encoding="utf-8")
    return sonuc


def shorts_yukle(cikti: Path, oturum=requests, gunler: list[int] | None = None) -> list[dict]:
    """G12: her Short gizli ve planlı; uzun videonun yayınından yayin_gunleri[k] gün sonra. Açıklamadaki {UZUN_VIDEO}
    uzun videonun bağlantısıyla değişir. Denetçi kararı (onay) ve yüklenmiş uzun video gerekir."""
    from .ortak import ayar_yukle
    onay = onay_kontrol(cikti)
    yuk = cikti / "yukleme.json"
    if not yuk.exists():
        raise GoogleHatasi("uzun video yüklenmemiş (yukleme.json yok): Shorts ona bağlanır (G12)")
    uzun = json.loads(yuk.read_text(encoding="utf-8"))["video_id"]
    metinler = json.loads((cikti / "shorts.json").read_text(encoding="utf-8"))
    gunler = gunler or ayar_yukle()["shorts"]["yayin_gunleri"]
    if len(gunler) < len(metinler):
        raise GoogleHatasi(f"yayin_gunleri {len(gunler)} gün, Short {len(metinler)}")
    yayin = _zaman_oku(onay["yayin_zamani"])
    iz = cikti / "shorts_yukleme.json"
    sonuc = json.loads(iz.read_text(encoding="utf-8")) if iz.exists() else []  # yarıda kaldıysa kaldığı yerden
    yuklu = {s["dosya"] for s in sonuc}
    if all(f"short_{k + 1}.mp4" in yuklu for k in range(len(metinler))):
        return sonuc
    tok = erisim_belirteci(oturum)
    for k, m in enumerate(metinler):
        if not m.get("sentetik_icerik"):
            raise GoogleHatasi("sentetik içerik etiketi kapalı (G9)")
        dosya = cikti / f"short_{k + 1}.mp4"
        if dosya.name in yuklu:
            continue
        zaman = (yayin + timedelta(days=gunler[k])).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        govde = youtube_govdesi(dict(m, aciklama=m["aciklama"].replace("{UZUN_VIDEO}", f"https://youtu.be/{uzun}")),
                                zaman)
        r = oturum.post(YT_UPLOAD, params={"uploadType": "resumable", "part": "snippet,status"}, json=govde,
                        timeout=30, headers={**_baslik(tok), "X-Upload-Content-Type": "video/mp4",
                                             "X-Upload-Content-Length": str(dosya.stat().st_size)})
        if r.status_code != 200:
            raise GoogleHatasi(f"Short yükleme başlatılamadı ({r.status_code}): {r.text[:300]}")
        sonuc.append({"id": _devam_ettir(r.headers["Location"], dosya, "video/mp4", oturum)["id"],
                      "publishAt": zaman, "dosya": dosya.name})
        iz.write_text(json.dumps(sonuc, indent=2), encoding="utf-8")  # yarıda kalırsa iz
    return sonuc
