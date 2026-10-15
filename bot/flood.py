"""Tiny Fixes (üçüncü hesap, X + Instagram; SOZLESME F): konu bul, doğrula, yaz, onayla, paylaş, ölç.

Mod (ayarlar.toml [flood] mod):
  "kapali"   : hiçbir şey yapılmaz, hiçbir anahtar okunmaz (varsayılan, F9).
  "onay"     : taslaklar GitHub issue olarak sahibine gelir; `ok`/`ok 2`/`iptal` ile paylaşılır.
  "otomatik" : evergreen (Library) kendiliğinden, trend içerik (Fix, News) yine onayla (F6).
Anahtarlar yoksa bot yalnızca taslak hazırlar. Bot başkalarına yanıt, etiket, DM, takip, beğeni yapmaz (F7)."""

import json
import os
import subprocess
import tempfile
import time
import tomllib
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import requests

from . import (config, flood_denetci, flood_dogrula, flood_gorsel, flood_ig, flood_kaynak, flood_puan, flood_yazar,
               flood_yetki, onay)

DOSYA = config.ROOT / "data" / "flood.json"
ETIKET = "flood-onay"
YETKILI = {"OWNER", "MEMBER", "COLLABORATOR"}
MEDYA_DAL = "flood-medya"
SAKLA_GUN = 30


@dataclass(frozen=True)
class FloodAyar:
    mod: str = "kapali"
    model: str = "claude-sonnet-5-5"        # yazar ve web araştırması
    hafif_model: str = "claude-haiku-5-5"   # konu seçimi ve çıktı değerlendirmesi
    test_model: str = "claude-sonnet-5-5"   # Fix komutunu çalıştıran model (postta adı yazar, F2)
    effort: str = "medium"
    geo: str = "US"
    hacker_news: bool = True
    rss: tuple = ()
    trend_saatleri: tuple = (6, 14)         # UTC: bu saatlerden sonra günde bir trend taslağı
    evergreen_saati: int = 10               # UTC: günlük evergreen taslağı
    evergreen_yayin_saati: int = 17         # UTC: otomatik modda evergreen'in çıkış saati
    onay_suresi_dk: int = 180               # F6: bu sürede cevap yoksa taslak düşer
    birim_araligi_dk: int = 90              # iki birim arası en az
    gunluk_birim: int = 4                   # F8
    x_aktif: bool = True
    ig_aktif: bool = True
    ig_surum: str = "v23.0"
    alarm_kime: str = ""


def ayar_yukle(path=config.ROOT / "ayarlar.toml") -> FloodAyar:
    with open(path, "rb") as f:
        t = tomllib.load(f).get("flood", {})
    alanlar = FloodAyar.__dataclass_fields__
    kw = {}
    for k, v in t.items():
        if k not in alanlar:
            continue
        if k == "rss":
            kw[k] = tuple((str(a), str(u)) for a, u in v)
        elif k == "trend_saatleri":
            kw[k] = tuple(int(h) for h in v)
        else:
            kw[k] = type(alanlar[k].default)(v)
    return FloodAyar(**kw)


def yukle() -> dict:
    try:
        return json.loads(DOSYA.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {"birimler": [], "konular": [], "gun": {}, "kutuphane": []}


def kaydet(state: dict, simdi: datetime | None = None) -> None:
    if simdi:  # eski kayıtlar atılır: dosya büyümesin
        sinir = (simdi - timedelta(days=SAKLA_GUN)).isoformat()
        state["birimler"] = [b for b in state["birimler"] if b["olusturma"] >= sinir]
        state["konular"] = [k for k in state["konular"] if k["tarih"] >= sinir[:10]][-300:]
        state["gun"] = {g: v for g, v in state["gun"].items() if g >= sinir[:10]}
    DOSYA.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _iso(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _gun(state: dict, simdi: datetime) -> dict:
    return state["gun"].setdefault(simdi.date().isoformat(), {"slotlar": [], "birim": 0, "ig": 0, "metinler": []})


# ---------- Onay (F6) ----------

def karar(metin: str) -> tuple[str, int] | None:
    """('ok', 1|2) ya da ('iptal', 1). 'iptal' her zaman önceliklidir; 'ok 2' alternatif kancayı seçer."""
    k = onay.karar(metin)
    if k == "iptal":
        return ("iptal", 1)
    if k == "ok":
        kelimeler = [w.strip(".!,?:;") for w in metin.lower().split()]
        return ("ok", 2 if {"2", "b"} & set(kelimeler[1:3]) else 1)
    return None


def sahibin_karari(gh, no: int) -> tuple[str, int] | None:
    sonuc = None
    for y in gh.yorumlar(no):
        k = karar(y.get("body") or "")
        if k and (y.get("author_association") in YETKILI or gh.yetkili(y["user"]["login"])):
            sonuc = k
    return sonuc


def onay_govdesi(b: dict, ayar: FloodAyar) -> str:
    k, f = b["kayit"], b["flood"]
    s = [f"@{ayar.alarm_kime} " if ayar.alarm_kime else "",
         f"**{k['tur'].upper()}**: {k['konu']}", "",
         "Cevap: `ok` (kanca A), `ok 2` (kanca B), `iptal`. "
         f"{ayar.onay_suresi_dk // 60} saat içinde cevap gelmezse taslak düşer, paylaşılmaz (F6).", "", "### X flood"]
    for i, p in enumerate(f["x"]["postlar"], 1):
        s.append(f"{i}. {p}")
    if f["x"].get("alternatif_hook"):
        s += ["", f"**Kanca B** (yerine 1. post): {f['x']['alternatif_hook']}"]
    d = k.get("denendi")
    if d:
        s += ["", f"### Denendi ({flood_denetci.model_adi(d['model'])}, {d['sure']})", f"Komut: `{d['komut']}`",
              f"Sınır: {d['sinir']}"]
    s += ["", "### Instagram carousel"] + [f"{i}. **{x['baslik']}**: {x['metin']}" for i, x in enumerate(f["ig"]["slaytlar"], 1)]
    s += ["", f"Caption: {f['ig']['caption']}", " ".join(f["ig"]["etiketler"])]
    if k.get("olgular"):
        s += ["", "### Kaynaklı olgular (F1)"] + [f"- {o['metin']} ({', '.join(o['kaynaklar'])})" for o in k["olgular"]]
    return "\n".join(s)


def onay_isle(ayar: FloodAyar, state: dict, simdi: datetime, gh, yaz=print) -> None:
    for b in state["birimler"]:
        if b["durum"] != "onay_bekliyor":
            continue
        k = sahibin_karari(gh, b["issue"]) if b.get("issue") else None
        if k and k[0] == "iptal":
            b["durum"] = "iptal"
            gh.kapat(b["issue"], "🛑 İptal edildi, paylaşılmayacak.")
        elif k:
            b["durum"], b["secim"] = "onaylandi", k[1]
            gh.yorum(b["issue"], f"✅ Onaylandı (kanca {'AB'[k[1] - 1]}). Sıradaki nabızda paylaşılır.")
        elif simdi >= _iso(b["son"]):
            b["durum"] = "dustu"
            gh.kapat(b["issue"], "⌛ Süre doldu, cevap gelmedi: taslak düştü, paylaşılmadı (F6).")
            yaz(f"Tiny Fixes taslağı düştü (onay yok): {b['konu']}")


# ---------- Üretim ----------

def _siradaki_slot(ayar: FloodAyar, gun: dict, simdi: datetime) -> str | None:
    for h in sorted(ayar.trend_saatleri):
        if simdi.hour >= h and f"t{h}" not in gun["slotlar"]:
            return f"t{h}"
    if simdi.hour >= ayar.evergreen_saati and "e" not in gun["slotlar"]:
        return "e"
    return None


def _birim(kayit: dict, flood: dict, simdi: datetime, ayar: FloodAyar, durum: str) -> dict:
    b = {"id": simdi.strftime("%Y%m%d-%H%M") + "-" + kayit["tur"], "tur": kayit["tur"], "konu": kayit["konu"],
         "kayit": kayit, "flood": flood, "durum": durum, "olusturma": simdi.isoformat(timespec="seconds"),
         "son": (simdi + timedelta(minutes=ayar.onay_suresi_dk)).isoformat(timespec="seconds"), "secim": 1,
         "yayin_zamani": None, "x": {"idler": []}, "ig": {}}
    if durum == "planli":
        t = simdi.replace(hour=ayar.evergreen_yayin_saati, minute=0, second=0, microsecond=0)
        b["yayin_zamani"] = max(simdi, t).isoformat(timespec="seconds")
    return b


def _taslak_ekle(ayar, state, b, gh, simdi, yaz) -> None:
    if b["durum"] == "onay_bekliyor":
        b["issue"] = gh.issue_ac(f"🧪 Tiny Fixes taslağı: {b['konu'][:70]}", onay_govdesi(b, ayar), ETIKET)
    state["birimler"].append(b)
    state["konular"].append({"baslik": b["konu"], "tarih": simdi.date().isoformat()})
    yaz(f"Tiny Fixes taslağı hazır ({b['tur']}, {b['durum']}): {b['konu']}")


def uret(ayar: FloodAyar, state: dict, simdi: datetime, client, gh, get=flood_kaynak.http_al, yaz=print) -> None:
    gun = _gun(state, simdi)
    slot = _siradaki_slot(ayar, gun, simdi)
    if not slot:
        return
    gun["slotlar"].append(slot)  # başarısız olsa da bu slot yeniden denenmez: her deneme para harcar
    kaydet(state)
    if client is None:
        yaz("Tiny Fixes: Claude anahtarı yok, taslak üretilmedi.")
        return
    if slot == "e":
        tema = flood_yazar.kutuphane_temasi(state["kutuphane"])
        kayit = flood_dogrula.kutuphane_kaydi(client, ayar, tema, yaz)
        durum = "planli" if ayar.mod == "otomatik" else "onay_bekliyor"  # F6: yalnızca evergreen otomatik
        adaylar = [(kayit, tema)] if kayit else []
    else:
        adaylar = _trend_adaylari(ayar, state, simdi, client, get, yaz)
        durum = "onay_bekliyor"
    for kayit, konu in adaylar:
        sorun = flood_denetci.kayit_kontrol(kayit)
        if sorun:
            yaz(f"Kayıt reddedildi ({konu}): {sorun[0]}")
            continue
        flood, sorunlar = flood_yazar.yaz(client, ayar, kayit, gun["metinler"], 0, yaz)
        if not flood:
            yaz(f"Yazılamadı ({konu}): {sorunlar[0] if sorunlar else '?'}")
            continue
        if slot == "e":
            state["kutuphane"] = (state["kutuphane"] + [konu])[-60:]
        _taslak_ekle(ayar, state, _birim(kayit, flood, simdi, ayar, durum), gh, simdi, yaz)
        return
    yaz(f"Tiny Fixes: bu slotta uygun konu çıkmadı ({slot}).")


def _trend_adaylari(ayar, state, simdi, client, get, yaz):
    """[(kayıt, konu)]: puanlanmış konulardan seçilen ve doğrulanan adaylar (en fazla 3)."""
    adaylar = flood_kaynak.topla(ayar, get, yaz)
    gecmis = [k["baslik"] for k in state["konular"]]
    sirali = flood_puan.sirala(adaylar, simdi, gecmis)
    sonuc = []
    for s in flood_yazar.triage(client, ayar, sirali):
        try:
            if s["tur"] == "news":
                kayit = flood_dogrula.haber_kaydi(client, ayar, s["aday"], yaz)
            else:
                kayit = flood_dogrula.fix_kaydi(client, ayar, s["aday"], s["problem"], s["fikir"], yaz)
        except Exception as e:  # tek konunun hatası diğerlerini engellemez
            yaz(f"Konu işlenemedi ({s['aday']['baslik']}): {e}")
            continue
        if kayit:
            sonuc.append((kayit, kayit["konu"]))
    return sonuc


# ---------- Yayın ----------

def gorselleri_yayinla(birim_id: str, jpegler: list[bytes], run=subprocess.run, head=requests.head, bekle=time.sleep) -> list[str]:
    """Slaytlar herkese açık bir dalda (`flood-medya`, her seferinde sıfırdan, geçmiş birikmez) yayınlanır; Meta
    görseli oradan çeker. Adresler erişilebilir olana dek beklenir; olmazsa hata (Instagram'a hiçbir şey gitmez)."""
    repo, token = os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GH_TOKEN", "")
    if not repo or not token:
        raise RuntimeError("GITHUB_REPOSITORY / GH_TOKEN yok: Instagram görselleri yayınlanamaz")
    with tempfile.TemporaryDirectory() as tmp:
        klasor = Path(tmp) / birim_id
        klasor.mkdir()
        for i, j in enumerate(jpegler, 1):
            (klasor / f"slayt{i}.jpg").write_bytes(j)
        kimlik = ["-c", "user.name=tiny-fixes-botu", "-c", "user.email=tiny-fixes-botu@users.noreply.github.com"]
        try:
            for komut in (["git", "init", "-q", "-b", MEDYA_DAL], ["git", *kimlik, "add", "-A"],
                          ["git", *kimlik, "commit", "-q", "-m", f"medya {birim_id}"],
                          ["git", "push", "-q", "--force", f"https://x-access-token:{token}@github.com/{repo}.git",
                           f"HEAD:refs/heads/{MEDYA_DAL}"]):
                run(komut, cwd=tmp, check=True, capture_output=True)
        except subprocess.CalledProcessError:  # komut satırı anahtar içerir: hata metnine yazılmaz
            raise RuntimeError("görsel dalı gönderilemedi (git)") from None
    urller = [f"https://raw.githubusercontent.com/{repo}/{MEDYA_DAL}/{birim_id}/slayt{i}.jpg" for i in range(1, len(jpegler) + 1)]
    for u in urller:
        for deneme in range(6):
            try:
                if head(u, timeout=20).status_code == 200:
                    break
            except requests.RequestException:
                pass
            if deneme == 5:
                raise RuntimeError(f"görsel adresi erişilebilir değil (depo herkese açık mı?): {u}")
            bekle(5)
    return urller


def _x_metinleri(b: dict) -> list[str]:
    p = list(b["flood"]["x"]["postlar"])
    alt = b["flood"]["x"].get("alternatif_hook")
    if b.get("secim") == 2 and alt:
        p[0] = alt
    return p


def _yayinla(ayar: FloodAyar, state: dict, b: dict, x, ig, simdi: datetime, yaz) -> None:
    gun = _gun(state, simdi)
    postlar = _x_metinleri(b)
    flood = {**b["flood"], "x": {**b["flood"]["x"], "postlar": postlar}}
    sorun = flood_denetci.denetle(flood, b["kayit"], [m for m in gun["metinler"] if m not in postlar], 0)
    if sorun:  # son kapı: kayıttan sonra bir şey değişmiş olabilir
        b["durum"] = "hata"
        b["hata"] = sorun[:5]
        yaz(f"Tiny Fixes paylaşımı denetimden geçmedi, durduruldu: {sorun[0]}")
        return
    d = b["kayit"].get("denendi")
    ig_izinli = gun["ig"] < flood_denetci.GUNLUK_IG  # F8: günde en fazla 3 Instagram postu (aşılırsa yalnızca atlanır)
    if x is not None and ayar.x_aktif and len(b["x"]["idler"]) < len(postlar):
        ids = b["x"]["idler"]
        medya = None
        if not ids:
            medya = [x.medya_yukle(flood_gorsel.x_karti(flood["ig"]["slaytlar"][0]["baslik"], "", None))]
        for i in range(len(ids), len(postlar)):
            ids.append(x.gonder(postlar[i], yanit=ids[-1] if ids else None, medya=medya if i == 0 else None))
            kaydet(state)  # yarıda kesilirse sonraki nabız kaldığı yerden sürdürür
        gun["metinler"] += postlar
    if ig is not None and ayar.ig_aktif and ig_izinli and not b["ig"].get("medya_id") and b["ig"].get("deneme", 0) < 3:
        try:
            if ig.kalan_hak()[0] >= 90:
                raise flood_ig.IgHata("24 saatlik Instagram yayın hakkı dolmak üzere")
            jpegler = flood_gorsel.carousel(flood["ig"]["slaytlar"], d["komut"] if d else None)
            urller = gorselleri_yayinla(b["id"], jpegler)
            caption = (flood["ig"]["caption"] + "\n\n" + " ".join(flood["ig"]["etiketler"])).strip()
            b["ig"]["medya_id"] = ig.carousel(urller, caption)
            gun["ig"] += 1
        except Exception as e:
            b["ig"]["deneme"] = b["ig"].get("deneme", 0) + 1
            b["ig"]["hata"] = str(e)[:200]
            yaz(f"Instagram paylaşımı başarısız ({b['ig']['deneme']}/3): {e}")
    x_bitti = x is None or not ayar.x_aktif or len(b["x"]["idler"]) >= len(postlar)
    ig_bitti = ig is None or not ayar.ig_aktif or not ig_izinli or b["ig"].get("medya_id") or b["ig"].get("deneme", 0) >= 3
    if x_bitti and ig_bitti:
        b["durum"], b["yayin"] = "yayinlandi", simdi.isoformat(timespec="seconds")
        gun["birim"] += 1
        state["son_yayin"] = b["yayin"]
        yaz(f"Tiny Fixes paylaşıldı: {b['konu']}")


def yayinla_sirali(ayar: FloodAyar, state: dict, simdi: datetime, x, ig, yaz=print) -> None:
    """Nabız başına en fazla bir birim. Onaylı içerik hemen çıkar (sahibi karar verdi); planlı evergreen saatini bekler."""
    if x is None and ig is None:
        return  # F9: anahtarlar yoksa yalnızca taslak
    gun = _gun(state, simdi)
    if gun["birim"] >= min(ayar.gunluk_birim, flood_denetci.GUNLUK_BIRIM):
        return
    son = state.get("son_yayin")
    for b in state["birimler"]:
        yarim = b["durum"] in ("onaylandi", "planli") and (b["x"]["idler"] or b["ig"])  # yarım kalan işi önce bitir
        if b["durum"] not in ("onaylandi", "planli"):
            continue
        if b["durum"] == "planli" and simdi < _iso(b["yayin_zamani"]):
            continue
        if not yarim and son and simdi - _iso(son) < timedelta(minutes=ayar.birim_araligi_dk):
            return
        _yayinla(ayar, state, b, x, ig, simdi, yaz)
        return


# ---------- Ölçüm ve sağlık ----------

def olcum_guncelle(state: dict, x, ig, simdi: datetime, yaz=print) -> None:
    """Yayından 24 saat sonra her birimin rakamları (günde bir kez). X: yalnızca ilk postların kimliği sorulur."""
    gun = simdi.date().isoformat()
    if state.get("son_olcum") == gun or simdi.hour < 12:
        return
    bekleyen = [b for b in state["birimler"] if b["durum"] == "yayinlandi" and not b.get("olcum")
                and simdi - _iso(b["yayin"]) >= timedelta(hours=24)]
    if not bekleyen:
        return
    state["son_olcum"] = gun
    xm = {}
    if x is not None:
        try:
            xm = {t["id"]: t.get("public_metrics") for t in x.metrikler_idle([b["x"]["idler"][0] for b in bekleyen if b["x"]["idler"]])}
        except Exception as e:
            yaz(f"Tiny Fixes X ölçümü alınamadı: {e}")
    for b in bekleyen:
        o = {"x": xm.get(b["x"]["idler"][0]) if b["x"]["idler"] else None, "ig": None}
        if ig is not None and b["ig"].get("medya_id"):
            try:
                o["ig"] = ig.olcum(b["ig"]["medya_id"])
            except Exception as e:
                yaz(f"Tiny Fixes Instagram ölçümü alınamadı: {e}")
        b["olcum"] = o


def sorunlar(ayar: FloodAyar, state: dict, simdi: datetime) -> list[tuple[str, str]]:
    """Alarm adayları. Kapalıyken hiçbir şey. Aynı sorun günde bir kez bildirilir (kod günü içerir)."""
    if ayar.mod == "kapali":
        return []
    gun = simdi.date().isoformat()
    sonuc = [(f"flood-hata-{b['id']}", f"Tiny Fixes paylaşımı durduruldu: {b['konu'][:60]}: {', '.join(b.get('hata', []))[:160]}")
             for b in state["birimler"] if b["durum"] == "hata"]
    bekleyen = [b for b in state["birimler"] if b["durum"] in ("onay_bekliyor", "onaylandi", "planli")]
    referans = state.get("son_yayin") or state.get("baslangic")
    if not bekleyen and referans and 7 <= simdi.hour < 21 and simdi - _iso(referans) > timedelta(hours=30):
        sonuc.append((f"flood-sessiz-{gun}", "Tiny Fixes 30 saattir hiçbir şey paylaşmadı ve bekleyen taslak yok."))
    return sonuc


# ---------- Giriş noktası ----------

def istemciler(simdi: datetime, yaz=print):
    """(x, ig, claude): anahtar yoksa ilgili istemci None. Kapalı modda çağrılmaz."""
    secret = os.environ.get("X_API_SECRET", "")
    x = ig = claude = None
    if secret and os.environ.get("X_API_KEY"):
        k = flood_yetki.x_anahtarlar(secret)
        if k:
            from . import tweets
            x = tweets.XClient(os.environ["X_API_KEY"], secret, k["token"], k["secret"])
    kayit = flood_yetki.ig_anahtar(secret) if secret else None
    token, ig_id = (kayit["token"], kayit["ig_id"]) if kayit else (os.environ.get("IG_FLOOD_TOKEN", ""), os.environ.get("IG_FLOOD_ID", ""))
    if token and ig_id:
        ig = flood_ig.InstagramClient(token, ig_id, surum=ayar_yukle().ig_surum)
        try:
            if kayit and flood_yetki.yenileme_gerekli(kayit, simdi):
                flood_yetki.kaydet_ig(secret, ig.anahtar_yenile(), ig_id, simdi)
                yaz("Instagram anahtarı yenilendi.")
            elif not kayit and secret:
                flood_yetki.kaydet_ig(secret, token, ig_id, simdi)  # ilk kez: şifreli kaydedilir, sonra bot yeniler
        except Exception as e:
            yaz(f"Instagram anahtarı yenilenemedi: {e}")
    if os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic
        claude = anthropic.Anthropic()
    return x, ig, claude


def nabiz(ana_ayar, simdi: datetime, yaz=print, gh=None, get=flood_kaynak.http_al, ayar: FloodAyar | None = None,
          istemci_fabrikasi=istemciler) -> None:
    """Her nabızda: onay kontrolü, yayın, (zamanı gelince) üretim, ölçüm, yorum kiti, alarm."""
    ayar = ayar or ayar_yukle()
    if ayar.mod == "kapali":
        return  # F9: hiçbir şey okunmaz, hiçbir anahtar kullanılmaz
    gh = gh or onay.GitHub()
    state = yukle()
    state.setdefault("baslangic", simdi.isoformat(timespec="seconds"))
    x, ig, claude = istemci_fabrikasi(simdi, yaz)
    adimlar = (("onay", lambda: onay_isle(ayar, state, simdi, gh, yaz)),
               ("yayın", lambda: yayinla_sirali(ayar, state, simdi, x, ig, yaz)),
               ("üretim", lambda: uret(ayar, state, simdi, claude, gh, get, yaz)),
               ("ölçüm", lambda: olcum_guncelle(state, x, ig, simdi, yaz)))
    hatalar = []
    for ad, adim in adimlar:
        try:
            adim()
        except Exception as e:  # bir adımın hatası diğerlerini engellemez
            hatalar.append(f"Tiny Fixes {ad}: {e}")
            yaz(f"⚠️ Tiny Fixes {ad} adımı başarısız: {e}")
    kaydet(state, simdi)
    if x is not None:
        try:
            from . import yorum
            yorum.kontrol(x, gh, ana_ayar, simdi, hesap="flood", client=claude, yaz=yaz)
        except Exception as e:
            yaz(f"⚠️ Tiny Fixes yorum kiti bu turda çalışmadı: {e}")
    from . import saglik
    saglik.bildir(sorunlar(ayar, state, simdi) + [(f"flood-adim-{simdi.date()}-{i}", h) for i, h in enumerate(hatalar)],
                  gh, ayar.alarm_kime or getattr(ana_ayar, "alarm_kime", ""), simdi, yaz)
