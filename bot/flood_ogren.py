"""Tiny Fixes öğrenme döngüsü ve haftalık rapor (SOZLESME F10).

24 saat sonraki ölçümler kalıcı bir geçmişe (`state["gecmis"]`, 365 gün) yazılır. Bot bu geçmişle YALNIZCA sıralama ve
öneri yapar: trend adaylarının sırası (Fix mi News mi), onay issue'sunda kanca önerisi, otomatik modda planlı evergreen'in
kancası ve sahibine haftalık rapor. Öğrenme hiçbir kuralı gevşetmez, onay isteyen içeriği onaysız yayınlamaz, günlük
sınırları artırmaz ve en az MIN_ORNEK ölçülmüş birim olmadan devreye girmez. Ek API çağrısı yoktur (maliyet sıfır)."""

from datetime import datetime, timedelta

MIN_ORNEK = 6          # bundan az ölçülmüş birimle öğrenme kapalı (gürültü)
ONCUL = 3              # küçük örneklerde ortalamayı genel ortalamaya çeken sanal gözlem sayısı
KANCA_FARK = 0.15      # kanca önerisi için en az %15 fark
KANCA_MIN = 4          # ve her kancada en az 4 ölçüm
GECMIS_GUN = 365
KANCALAR = {1: "A (sorun önce)", 2: "B (sonuç önce)"}

# Tahmini birim maliyetler (USD). Kaynak: marka/TINY_FIXES.md maliyet raporu; gerçek faturayla güncellenmeli.
MALIYET = {"x_post": 0.015, "x_okuma": 0.005, "arastirma": 0.08, "yazim": 0.04, "deneme": 0.02, "secim": 0.002,
           "yorum_taslagi": 0.002}


# ---------- Puan ----------

def x_skoru(m: dict | None) -> float | None:
    """X: 1000 görüntülenme başına ağırlıklı etkileşim. Kaydetme (bookmark) ve yanıt en değerli sinyaller."""
    if not m or not m.get("impression_count"):
        return None
    puan = (m.get("like_count", 0) + 2 * m.get("retweet_count", 0) + 2 * m.get("reply_count", 0)
            + 2 * m.get("quote_count", 0) + 3 * m.get("bookmark_count", 0))
    return round(1000 * puan / m["impression_count"], 2)


def ig_skoru(m: dict | None) -> float | None:
    """Instagram: 1000 erişim başına; kaydetme ve gönderme (Mosseri'nin sinyalleri) üç kat."""
    if not m or not m.get("reach"):
        return None
    puan = m.get("likes", 0) + 2 * m.get("comments", 0) + 3 * m.get("saved", 0) + 3 * m.get("shares", 0)
    return round(1000 * puan / m["reach"], 2)


def birim_skoru(o: dict) -> float | None:
    s = [v for v in (x_skoru(o.get("x")), ig_skoru(o.get("ig"))) if v is not None]
    return round(sum(s) / len(s), 2) if s else None


def gecmise_yaz(state: dict, b: dict) -> None:
    """Ölçümü alınmış birimi kalıcı geçmişe ekler (birimler 30 günde silinir, geçmiş kalır)."""
    o = b.get("olcum") or {}
    x, ig = o.get("x") or {}, o.get("ig") or {}
    state.setdefault("gecmis", []).append({
        "id": b["id"], "tur": b["tur"], "kanca": b.get("secim", 1), "yayin": b.get("yayin"),
        "saat": int(b["yayin"][11:13]) if b.get("yayin") else None, "konu": b["konu"][:80],
        "x_gosterim": x.get("impression_count"), "x_kaydetme": x.get("bookmark_count"), "x_skor": x_skoru(x),
        "ig_erisim": ig.get("reach"), "ig_kaydetme": ig.get("saved"), "ig_gonderme": ig.get("shares"), "ig_skor": ig_skoru(ig),
        "skor": birim_skoru(o)})


def gecmisi_temizle(state: dict, simdi: datetime) -> None:
    sinir = (simdi - timedelta(days=GECMIS_GUN)).isoformat()
    state["gecmis"] = [g for g in state.get("gecmis", []) if (g.get("yayin") or "") >= sinir][-500:]


# ---------- Öğrenilenler ----------

def _olculen(state: dict) -> list[dict]:
    return [g for g in state.get("gecmis", []) if g.get("skor") is not None]


def _ortalama(degerler: list[float], genel: float) -> float:
    """Küçük örnek genel ortalamaya çekilir (ONCUL sanal gözlem): 1 şanslı post sıralamayı çevirmesin."""
    return (sum(degerler) + ONCUL * genel) / (len(degerler) + ONCUL)


def agirliklar(state: dict, alan: str) -> dict:
    """{değer: (düzeltilmiş ortalama skor, n)}; öğrenme kapalıysa boş."""
    olculen = _olculen(state)
    if len(olculen) < MIN_ORNEK:
        return {}
    genel = sum(g["skor"] for g in olculen) / len(olculen)
    gruplar: dict = {}
    for g in olculen:
        gruplar.setdefault(g.get(alan), []).append(g["skor"])
    return {k: (round(_ortalama(v, genel), 2), len(v)) for k, v in gruplar.items() if k is not None}


def sirala_secimler(secimler: list[dict], state: dict) -> list[dict]:
    """Triage seçimleri: daha iyi ölçülen tür (fix/news) öne. Aynı tür içinde triage sırası korunur. Öğrenme kapalıysa
    sıra değişmez. Hiçbir aday eklenmez ya da çıkarılmaz (F10: yalnızca sıralama)."""
    w = agirliklar(state, "tur")
    if not w:
        return list(secimler)
    return sorted(secimler, key=lambda s: -w.get(s["tur"], (0, 0))[0])


def kanca_onerisi(state: dict, tur: str | None = None) -> tuple[int, str] | None:
    """(önerilen kanca 1|2, Türkçe gerekçe) ya da None (yeterli veri ya da fark yok)."""
    olculen = [g for g in _olculen(state) if tur is None or g["tur"] == tur]
    if len(_olculen(state)) < MIN_ORNEK:
        return None
    a = [g["skor"] for g in olculen if g.get("kanca") == 1]
    b = [g["skor"] for g in olculen if g.get("kanca") == 2]
    if len(a) < KANCA_MIN or len(b) < KANCA_MIN:
        return None
    genel = sum(a + b) / len(a + b)
    oa, ob = _ortalama(a, genel), _ortalama(b, genel)
    iyi, kotu, k = (oa, ob, 1) if oa >= ob else (ob, oa, 2)
    if kotu <= 0 or (iyi - kotu) / kotu < KANCA_FARK:
        return None
    return k, f"Kanca {KANCALAR[k]} şimdiye dek %{round(100 * (iyi - kotu) / kotu)} daha iyi (A: {len(a)}, B: {len(b)} post)."


# ---------- Sayaç ve rapor ----------

def say(state: dict, simdi: datetime, ad: str, n: int = 1) -> None:
    """Günlük işlem sayacı (tahmini maliyet için). Ek çağrı yapmaz."""
    g = state.setdefault("sayac", {}).setdefault(simdi.date().isoformat(), {})
    g[ad] = g.get(ad, 0) + n


def tahmini_maliyet(state: dict, baslangic: datetime, bitis: datetime) -> float:
    toplam = 0.0
    for gun, sayaclar in (state.get("sayac") or {}).items():
        if baslangic.date().isoformat() <= gun < bitis.date().isoformat():
            toplam += sum(MALIYET.get(k, 0) * v for k, v in sayaclar.items())
    return round(toplam, 2)


def rapor_zamani(state: dict, simdi: datetime) -> bool:
    """Pazartesi 08 UTC'den sonra, haftada bir."""
    hafta = simdi.strftime("%G-%V")
    return simdi.weekday() == 0 and simdi.hour >= 8 and state.get("son_rapor") != hafta


def rapor(state: dict, simdi: datetime) -> str:
    """Sahibine Türkçe haftalık rapor (son 7 gün). Yalnızca kayıttaki rakamlar."""
    bas = simdi - timedelta(days=7)
    son7 = [g for g in state.get("gecmis", []) if (g.get("yayin") or "") >= bas.isoformat()]
    birimler = [b for b in state.get("birimler", []) if b["olusturma"] >= bas.isoformat()]
    durum: dict = {}
    for b in birimler:
        durum[b["durum"]] = durum.get(b["durum"], 0) + 1
    s = [f"## 🩹 Tiny Fixes haftalık rapor ({bas.date()} – {simdi.date()})", ""]
    s.append(f"- Taslak: {len(birimler)} · yayınlanan: {durum.get('yayinlandi', 0)} · iptal: {durum.get('iptal', 0)} · "
             f"cevapsız düşen: {durum.get('dustu', 0)} · denetimde duran: {durum.get('hata', 0)}")
    xg = sum(g.get("x_gosterim") or 0 for g in son7)
    xk = sum(g.get("x_kaydetme") or 0 for g in son7)
    ie = sum(g.get("ig_erisim") or 0 for g in son7)
    ik = sum(g.get("ig_kaydetme") or 0 for g in son7)
    ig_ = sum(g.get("ig_gonderme") or 0 for g in son7)
    s.append(f"- X: {xg} görüntülenme, {xk} kaydetme · Instagram: {ie} erişim, {ik} kaydetme, {ig_} gönderme (ölçülen {len(son7)} post)")
    s.append(f"- Tahmini API maliyeti (bu hafta): ~${tahmini_maliyet(state, bas, simdi + timedelta(days=1))} "
             "(sayaç tahmini; gerçek fatura: Anthropic ve X konsolları)")
    puanli = [g for g in son7 if g.get("skor") is not None]
    if puanli:
        en = max(puanli, key=lambda g: g["skor"])
        s.append(f"- Haftanın en iyisi: **{en['konu']}** ({en['tur']}, kanca {'AB'[en['kanca'] - 1]}, skor {en['skor']})")
    s += ["", "### Öğrenilenler (F10: yalnızca sıralama ve öneri)"]
    w = agirliklar(state, "tur")
    if not w:
        s.append(f"- Henüz yeterli veri yok ({len(_olculen(state))}/{MIN_ORNEK} ölçülmüş post). Öğrenme kapalı, sıra değişmiyor.")
    else:
        s.append("- Tür: " + ", ".join(f"{k} {v[0]} (n={v[1]})" for k, v in sorted(w.items(), key=lambda x: -x[1][0])))
        k = kanca_onerisi(state)
        s.append("- Kanca: " + (k[1] if k else "A ve B arasında belirgin fark yok."))
        saatler = agirliklar(state, "saat")
        if len(saatler) >= 2:
            en_saat = max(saatler.items(), key=lambda x: x[1][0])
            s.append(f"- Saat: en iyi sonuç {en_saat[0]:02d}:00 UTC civarı paylaşılanlarda (n={en_saat[1][1]}). "
                     "Saatleri değiştirmek sahibinin kararı (`ayarlar.toml → [flood]`).")
    s += ["", "Bu issue bilgi içindir, cevap gerekmez. Yeni rapor gelince bu kapanır."]
    return "\n".join(s)
