"""GitHub issue yardımcıları (sahibine bildirim, rapor ve taslak issue'ları) ve sahibinin "ok" / "iptal" cevabını okuma.
Kalkylerat'ın eski kupon onay akışı (önizleme, otomatik paylaşım) 22 Ekim 2026'da kaldırıldı."""

import os

import requests

ESKIYI_KAPAT = ("alarm", "yanit-kiti", "rapor", "mr-likely", "yorum-kiti", "yorum-kiti-likely", "yorum-firsatlari", "yorum-firsatlari-likely", "yorum-kiti-flood", "yorum-kiti-flood-ig", "flood-rapor", "flood-tani")  # yenisi açılınca eskisi kapanan günlük/haftalık issue'lar
OK = {"ok", "okay", "onay", "onayla", "onaylıyorum", "evet", "tamam", "paylas", "paylaş", "yes"}
# "iptal" her zaman önceliklidir: yanlışlıkla paylaşmaktansa paylaşmamak.
IPTAL = {"iptal", "hayir", "hayır", "cancel", "dur", "durdur", "bekle"}


def karar(metin: str) -> str | None:
    """Mesajdaki kelimelere bakar; "iptal" her zaman önceliklidir (yanlışlıkla paylaşmaktansa paylaşmamak)."""
    kelimeler = [k.strip(".!,?:;") for k in metin.lower().split()]
    if set(kelimeler) & IPTAL:
        return "iptal"
    # Onay yalnızca mesaj "ok" ile başlıyorsa: "not ok", "ok değil" onay sayılmaz.
    if kelimeler and kelimeler[0] in OK and not {"değil", "degil", "not", "no"} & set(kelimeler):
        return "ok"
    return None


class GitHub:
    def __init__(self, token: str | None = None, repo: str | None = None):
        self.repo = repo or os.environ.get("GITHUB_REPOSITORY", "")
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token or os.environ.get('GH_TOKEN', '')}",
                               "Accept": "application/vnd.github+json"})

    def _url(self, yol: str) -> str:
        return f"https://api.github.com/repos/{self.repo}/{yol}"

    def yorumlar(self, no: int) -> list[dict]:
        r = self.s.get(self._url(f"issues/{no}/comments"), params={"per_page": 100}, timeout=30)
        r.raise_for_status()
        return r.json()

    def yetkili(self, kullanici: str) -> bool:
        try:
            r = self.s.get(self._url(f"collaborators/{kullanici}/permission"), timeout=30)
            return r.ok and r.json().get("permission") in ("admin", "maintain", "write")
        except requests.RequestException:
            return False

    def yorum(self, no: int, mesaj: str) -> None:
        self.s.post(self._url(f"issues/{no}/comments"), json={"body": mesaj}, timeout=30).raise_for_status()

    def issue_ac(self, baslik: str, govde: str, etiket: str) -> int:
        r = self.s.post(self._url("issues"), json={"title": baslik, "body": govde, "labels": [etiket]}, timeout=30)
        r.raise_for_status()
        no = r.json()["number"]
        if etiket in ESKIYI_KAPAT:
            self._eskileri_kapat(etiket, no)
        return no

    def _eskileri_kapat(self, etiket: str, yeni: int) -> None:
        """Aynı etiketli eski issue'ları kapatır: sahibinin listesinde yalnızca güncel olan açık kalsın (12 Ekim).
        Başarısız olursa yeni issue yine açılmıştır; kapatma bir sonraki sefere kalır."""
        try:
            r = self.s.get(self._url("issues"), params={"labels": etiket, "state": "open", "per_page": 50}, timeout=30)
            r.raise_for_status()
            for i in r.json():
                if i["number"] != yeni and "pull_request" not in i:
                    self.s.patch(self._url(f"issues/{i['number']}"), json={"state": "closed", "state_reason": "completed"},
                                 timeout=30).raise_for_status()
        except requests.RequestException as e:
            print(f"Eski {etiket} issue'ları kapatılamadı: {e}")

    def kapat(self, no: int, mesaj: str) -> None:
        self.yorum(no, mesaj)
        self.s.patch(self._url(f"issues/{no}"), json={"state": "closed"}, timeout=30).raise_for_status()
