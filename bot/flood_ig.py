"""Instagram yayın istemcisi (Instagram API with Instagram Login, SOZLESME F).

Yalnızca kendi hesabımıza paylaşır (Standard Access: App Review gerekmez), Facebook Sayfası gerekmez. Hesap
Business ya da Creator olmalı. Meta görseli kendisi çeker: adres herkese açık olmalı ve JPEG olmalı. Carousel hazırlanırken
her slayt için bir "container" açılır, hepsi FINISHED olunca carousel container'ı ve yayın gelir.

Başkalarına yanıt, beğeni, takip, DM yok (F7): bu istemcide bunları yapan bir yöntem bilerek yoktur. Yorumlar
yalnızca okunur (yorum kiti taslağı için)."""

import time

import requests

HOST = "https://graph.instagram.com"
KUYRUK_SN = 3  # container durumunu bu aralıkla sorar
KUYRUK_DENEME = 20


class IgHata(RuntimeError):
    pass


class InstagramClient:
    def __init__(self, token: str, ig_id: str, surum: str = "v23.0", oturum: requests.Session | None = None, bekle=time.sleep):
        self.token, self.ig_id, self.surum = token, str(ig_id), surum
        self.s = oturum or requests.Session()
        self.bekle = bekle

    def _istek(self, yontem: str, yol: str, **params) -> dict:
        url = f"{HOST}/{self.surum}/{yol}" if self.surum else f"{HOST}/{yol}"
        params = {k: v for k, v in params.items() if v is not None}
        r = self.s.request(yontem, url, params=params if yontem == "GET" else None,
                           data=params if yontem == "POST" else None,
                           headers={"Authorization": f"Bearer {self.token}"}, timeout=60)
        try:
            veri = r.json()
        except ValueError:
            veri = {}
        if r.status_code >= 400 or "error" in veri:
            e = veri.get("error") or {}
            raise IgHata(f"Instagram API hatası {r.status_code}: {e.get('message') or r.text[:300]} (kod {e.get('code')})")
        return veri

    def ben(self) -> dict:
        """Hesabın kullanıcı adı ve kimliği (kurulum doğrulaması)."""
        return self._istek("GET", "me", fields="user_id,username,account_type")

    def kalan_hak(self) -> tuple[int, int]:
        """(kullanılan, toplam) 24 saatlik API yayın hakkı. Meta uygulamanın bunu kendisinin denetlemesini önerir."""
        d = self._istek("GET", f"{self.ig_id}/content_publishing_limit", fields="quota_usage,config")
        satir = (d.get("data") or [{}])[0]
        return int(satir.get("quota_usage", 0)), int((satir.get("config") or {}).get("quota_total", 100))

    def _hazir_bekle(self, kap_id: str) -> None:
        for _ in range(KUYRUK_DENEME):
            durum = self._istek("GET", kap_id, fields="status_code").get("status_code")
            if durum == "FINISHED":
                return
            if durum in ("ERROR", "EXPIRED"):
                raise IgHata(f"Instagram container {durum}: {kap_id}")
            self.bekle(KUYRUK_SN)
        raise IgHata(f"Instagram container zamanında hazır olmadı: {kap_id}")

    def carousel(self, gorsel_urlleri: list[str], caption: str) -> str:
        """2-10 JPEG adresi -> yayınlanmış carousel'in kimliği. Hata olursa hiçbir şey yayınlanmaz."""
        if not 2 <= len(gorsel_urlleri) <= 10:
            raise IgHata(f"carousel 2-10 görsel olmalı, {len(gorsel_urlleri)} var")
        cocuklar = []
        for u in gorsel_urlleri:
            cocuklar.append(self._istek("POST", f"{self.ig_id}/media", image_url=u, is_carousel_item="true")["id"])
        for c in cocuklar:
            self._hazir_bekle(c)
        kap = self._istek("POST", f"{self.ig_id}/media", media_type="CAROUSEL", children=",".join(cocuklar),
                          caption=caption)["id"]
        self._hazir_bekle(kap)
        return self._istek("POST", f"{self.ig_id}/media_publish", creation_id=kap)["id"]

    def tek_gorsel(self, gorsel_url: str, caption: str) -> str:
        kap = self._istek("POST", f"{self.ig_id}/media", image_url=gorsel_url, caption=caption)["id"]
        self._hazir_bekle(kap)
        return self._istek("POST", f"{self.ig_id}/media_publish", creation_id=kap)["id"]

    def yorumlar(self, medya_id: str, adet: int = 25) -> list[dict]:
        """Postun yorumları (yalnızca okuma): id, text, username, timestamp."""
        return self._istek("GET", f"{medya_id}/comments", fields="id,text,username,timestamp", limit=adet).get("data", [])

    def olcum(self, medya_id: str) -> dict:
        """Postun rakamları (erişim, kaydetme, gönderme, beğeni, yorum); alınamayan metrik atlanır."""
        sonuc = {}
        for metrik in ("reach", "saved", "shares", "likes", "comments"):
            try:
                d = self._istek("GET", f"{medya_id}/insights", metric=metrik).get("data") or []
                if d:
                    sonuc[metrik] = (d[0].get("values") or [{}])[0].get("value")
            except IgHata:
                continue
        return sonuc

    def anahtar_yenile(self) -> str:
        """Uzun ömürlü anahtarı yeniler (24 saat geçmiş ve süresi dolmamış anahtar); yeni anahtarı döndürür."""
        r = self.s.get(f"{HOST}/refresh_access_token", params={"grant_type": "ig_refresh_token", "access_token": self.token}, timeout=30)
        veri = r.json() if r.content else {}
        if r.status_code >= 400 or "access_token" not in veri:
            raise IgHata(f"Instagram anahtarı yenilenemedi: {r.text[:200]}")
        self.token = veri["access_token"]
        return self.token
