"""
================================================================================
 ai/local_vision.py - Yerel Gorsel Yapay Zeka (Ollama + LLaVA 7B)
================================================================================
 Tamamen yerel calisan LLaVA 7B modelini Ollama sunucusu uzerinden kullanarak
 oyun ekranlarini analiz eder. Internet baglantisi veya bulut API'si GEREKMEZ.

 Yetenekler:
   - analyze_base()      : Ussu analiz eder -> weak_side, town_hall_position, strategy, notes
   - is_home_screen()    : Ekran ana ekran mi? (bool)
   - is_battle_screen()  : Ekran savas ekrani mi? (bool)
   - describe_screen()   : Serbest metin analizi (Turkce)
   - health_check()      : Ollama servisi ve model hazir mi?

 Ornek:
   ai = LocalVisionAI(base_url="http://localhost:11434", model="llava:7b")
   if ai.available:
       print(ai.analyze_base("data/screenshots/koy.png"))
================================================================================
"""

from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

import config

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:  # pragma: no cover - bagimlilik eksikse
    requests = None  # type: ignore[assignment]
    REQUESTS_AVAILABLE = False


class LocalVisionAI:
    """Ollama + LLaVA tabanli yerel gorsel analiz sinifi."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        auto_check: bool = True,
    ) -> None:
        """
        LocalVisionAI nesnesini olusturur ve Ollama baglantisini test eder.

        Args:
            base_url (Optional[str]): Ollama sunucu adresi. None ise config.OLLAMA_URL.
            model (Optional[str]): Model adi. None ise config.OLLAMA_MODEL.
            timeout (Optional[int]): Istek zaman asimi (saniye). None ise config.OLLAMA_TIMEOUT.
            auto_check (bool): True ise baslangicta baglanti/model kontrolu yapilir.

        Returns:
            None
        """
        self.base_url: str = (base_url or config.OLLAMA_URL).rstrip("/")
        self.model: str = model or config.OLLAMA_MODEL
        self.timeout: int = int(timeout or config.OLLAMA_TIMEOUT)
        self.available: bool = False
        self.last_error: str = ""
        self.model_ready: bool = False

        self.stats: Dict[str, int] = {"requests": 0, "success": 0, "fail": 0, "parse_fail": 0}

        if not REQUESTS_AVAILABLE:
            self.last_error = "requests modulu yuklu degil (pip install requests)."
            print(f"[!] {self.last_error}")
            return

        print(f"[AI] Yerel AI hazirlaniyor -> {self.base_url} | model: {self.model}")
        if auto_check:
            self.available = self.health_check()

    # -------------------------------------------------------------------------
    # SAGLIK KONTROLU
    # -------------------------------------------------------------------------
    def health_check(self) -> bool:
        """
        Ollama servisinin calisip calismadigini ve modelin yuklu oldugunu test eder.

        Returns:
            bool: True -> AI kullanilabilir.
        """
        try:
            if not REQUESTS_AVAILABLE:
                return False
            if not config.USE_LOCAL_AI:
                self.last_error = "USE_LOCAL_AI = False (config.py) - AI devre disi."
                print(f"[AI] {self.last_error}")
                return False

            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=config.OLLAMA_HEALTH_TIMEOUT,
            )
            if response.status_code != 200:
                self.last_error = (
                    f"Ollama yanit verdi ama beklenmeyen durum kodu: {response.status_code}"
                )
                print(f"[!] {self.last_error}")
                return False

            payload = response.json()
            models = [str(item.get("name", "")) for item in payload.get("models", [])]
            self.model_ready = any(self.model.split(":")[0] in name for name in models)
            if not self.model_ready:
                print(
                    f"[!] '{self.model}' modeli bulunamadi! Kurmak icin: "
                    f"ollama pull {self.model}"
                )
                print(f"    Mevcut modeller: {', '.join(models) if models else '(hic yok)'}")
            else:
                print(f"[OK]  Yerel AI hazir -> {self.model}")

            self.available = True
            return True
        except Exception as error:
            self.available = False
            self.last_error = (
                f"Ollama servisine baglanilamadi ({error}). "
                "Ollama calisiyor mu? scripts/install_ollama.ps1 ile kurun."
            )
            print(f"[!] {self.last_error}")
            return False

    # -------------------------------------------------------------------------
    # GORUNTU YARDIMCILARI
    # -------------------------------------------------------------------------
    @staticmethod
    def encode_image(image_path: str) -> Optional[str]:
        """
        Goruntuyu base64 metnine cevirir.

        Args:
            image_path (str): Goruntu dosyasi yolu.

        Returns:
            Optional[str]: base64 kodlanmis metin veya None.
        """
        try:
            file_path = Path(image_path)
            if not file_path.exists():
                print(f"[!] Goruntu bulunamadi: {image_path}")
                return None
            with open(file_path, "rb") as handle:
                return base64.b64encode(handle.read()).decode("utf-8")
        except Exception as error:
            print(f"[!] Goruntu kodlama hatasi: {error}")
            return None

    def _post_chat(self, prompt: str, image_b64: str) -> Optional[str]:
        """
        Ollama /api/generate ucuna gorsel + metin gonderir.

        Args:
            prompt (str): Modele verilecek metin.
            image_b64 (str): base64 kodlanmis goruntu.

        Returns:
            Optional[str]: Modelin metin cevabi veya None.
        """
        try:
            self.stats["requests"] += 1
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [image_b64],
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 400},
            }
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            if response.status_code != 200:
                self.stats["fail"] += 1
                print(f"[!] AI istegi basarisiz (HTTP {response.status_code})")
                return None

            data = response.json()
            text = str(data.get("response", "")).strip()
            self.stats["success"] += 1
            return text
        except Exception as error:
            self.stats["fail"] += 1
            print(f"[!] AI istek hatasi: {error}")
            return None

    # -------------------------------------------------------------------------
    # JSON AYRISTIRMA
    # -------------------------------------------------------------------------
    @staticmethod
    def extract_json(text: str) -> Optional[Dict[str, Any]]:
        """
        Model cevabindan JSON nesnesi cikarir (fazladan metin olsa bile).

        Args:
            text (str): Model cevabi.

        Returns:
            Optional[Dict[str, Any]]: Ayristirilmis JSON veya None.
        """
        try:
            if not text:
                return None
            # Once dogrudan dene
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

            # JSON blogunu regex ile bul
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return None
            candidate = match.group(0)
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                # Tek tirnaklari cift tirnaga cevirip tekrar dene
                candidate = candidate.replace("'", '"')
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            return None
        except Exception as error:
            print(f"[!] JSON ayristirma hatasi: {error}")
            return None

    # -------------------------------------------------------------------------
    # ANALIZ FONKSIYONLARI
    # -------------------------------------------------------------------------
    def analyze_base(self, screenshot_path: str) -> Dict[str, Any]:
        """
        Ussu (koy ekranini) analiz eder ve saldiri stratejisi onerir.

        Args:
            screenshot_path (str): Ekran goruntusu yolu.

        Returns:
            Dict[str, Any]: {"weak_side", "town_hall_position", "strategy", "notes"}
                            Hata olursa {"error": "..."}
        """
        try:
            if not self.available:
                return {"error": self.last_error or "Yerel AI kullanilabilir degil."}

            image_b64 = self.encode_image(screenshot_path)
            if image_b64 is None:
                return {"error": f"Goruntu okunamadi: {screenshot_path}"}

            print(f"[AI] Ussu analiz ediliyor -> {screenshot_path}")
            start = time.time()
            answer = self._post_chat(config.AI_BASE_ANALYSIS_PROMPT, image_b64)
            elapsed = round(time.time() - start, 2)

            if not answer:
                return {"error": "AI cevap vermedi (timeout veya servis hatasi)."}

            parsed = self.extract_json(answer)
            if parsed is None:
                self.stats["parse_fail"] += 1
                print("[!] AI cevabi JSON formatinda degil, ham metin donduruluyor.")
                return {"error": "JSON ayristirilamadi", "raw": answer}

            result: Dict[str, Any] = {
                "weak_side": parsed.get("weak_side", "bilinmiyor"),
                "town_hall_position": parsed.get("town_hall_position", "bilinmiyor"),
                "strategy": parsed.get("strategy", ""),
                "notes": parsed.get("notes", ""),
                "raw": answer,
                "elapsed": elapsed,
                "model": self.model,
            }
            print(f"[AI] Analiz tamamlandi ({elapsed} sn) -> zayif taraf: {result['weak_side']}")
            return result
        except Exception as error:
            print(f"[!] Ussu analiz hatasi: {error}")
            return {"error": str(error)}

    def is_home_screen(self, screenshot_path: str) -> bool:
        """
        Ekranin ana koy ekrani olup olmadigini sorar.

        Args:
            screenshot_path (str): Ekran goruntusu yolu.

        Returns:
            bool: True -> ana ekran.
        """
        try:
            if not self.available:
                print("[!] AI kullanilabilir degil, varsayilan False (ana ekran degil).")
                return False
            image_b64 = self.encode_image(screenshot_path)
            if image_b64 is None:
                return False
            answer = self._post_chat(config.AI_HOME_SCREEN_PROMPT, image_b64)
            if not answer:
                return False
            normalized = answer.strip().upper()
            result = "YES" in normalized and "NO" not in normalized.split("YES")[0]
            print(f"[AI] Ana ekran kontrolu -> {answer[:60]!r} => {result}")
            return bool(result)
        except Exception as error:
            print(f"[!] Ana ekran kontrol hatasi: {error}")
            return False

    def is_battle_screen(self, screenshot_path: str) -> bool:
        """
        Ekranin savas/saldiri ekrani olup olmadigini sorar.

        Args:
            screenshot_path (str): Ekran goruntusu yolu.

        Returns:
            bool: True -> savas ekrani.
        """
        try:
            if not self.available:
                return False
            image_b64 = self.encode_image(screenshot_path)
            if image_b64 is None:
                return False
            answer = self._post_chat(config.AI_BATTLE_SCREEN_PROMPT, image_b64)
            if not answer:
                return False
            normalized = answer.strip().upper()
            result = "YES" in normalized
            print(f"[AI] Savas ekrani kontrolu -> {answer[:60]!r} => {result}")
            return bool(result)
        except Exception as error:
            print(f"[!] Savas ekrani kontrol hatasi: {error}")
            return False

    def describe_screen(self, screenshot_path: str) -> str:
        """
        Ekrani serbest metin olarak (Turkce) aciklar.

        Args:
            screenshot_path (str): Ekran goruntusu yolu.

        Returns:
            str: Modelin aciklamasi; hata halinde hata metni.
        """
        try:
            if not self.available:
                return self.last_error or "Yerel AI kullanilabilir degil."
            image_b64 = self.encode_image(screenshot_path)
            if image_b64 is None:
                return f"Goruntu okunamadi: {screenshot_path}"
            answer = self._post_chat(config.AI_DESCRIBE_PROMPT, image_b64)
            if not answer:
                return "AI cevap vermedi."
            print(f"[AI] Ekran aciklamasi alindi ({len(answer)} karakter).")
            return answer
        except Exception as error:
            print(f"[!] Ekran aciklama hatasi: {error}")
            return f"Hata: {error}"

    def suggest_attack_strategy(self, loot: Dict[str, int]) -> str:
        """
        Loot degerlerine gore (gorsel olmadan) metin tabanli strateji onerir.

        Args:
            loot (Dict[str, int]): {"gold", "elixir", "dark", "total"}

        Returns:
            str: Strateji onerisi metni.
        """
        try:
            if not self.available:
                return "Yerel AI kullanilabilir degil."
            prompt = (
                "Clash of Clans oyuncusuyum. Rakip loot degerleri: "
                f"altin={loot.get('gold', 0)}, iksir={loot.get('elixir', 0)}, "
                f"kara iksir={loot.get('dark', 0)}, toplam={loot.get('total', 0)}. "
                "Hangi orduyu nasil kullanmami onerirsin? Turkce ve kisa yaz."
            )
            return self._post_chat(prompt, "") or "AI cevap vermedi."
        except Exception as error:
            print(f"[!] Strateji onerisi hatasi: {error}")
            return f"Hata: {error}"

    # -------------------------------------------------------------------------
    # YARDIMCILAR
    # -------------------------------------------------------------------------
    def get_stats(self) -> Dict[str, int]:
        """
        AI istatistiklerini dondurur.

        Returns:
            Dict[str, int]: {"requests", "success", "fail", "parse_fail"}
        """
        return dict(self.stats)

    def print_status(self) -> None:
        """
        AI durumunu konsola yazar.

        Returns:
            None
        """
        try:
            print("=" * 78)
            print(" YEREL AI DURUMU")
            print("=" * 78)
            print(f" Sunucu        : {self.base_url}")
            print(f" Model         : {self.model}")
            print(f" Kullanilabilir: {self.available}")
            print(f" Model hazir   : {self.model_ready}")
            print(f" Son hata      : {self.last_error or '-'}")
            print(f" Istatistik    : {self.get_stats()}")
            print("=" * 78)
        except Exception as error:
            print(f"[!] Durum yazma hatasi: {error}")


if __name__ == "__main__":  # pragma: no cover - elle test
    ai = LocalVisionAI()
    ai.print_status()
