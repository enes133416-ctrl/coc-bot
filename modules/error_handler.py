"""
================================================================================
 modules/error_handler.py - Hata Yonetimi Modulu
================================================================================
 Botun calismasi sirasinda olusan hatalari yakalar, siniflandirir, kaydeder ve
 cozum onerileri sunar. Ayni hatanin tekrar tekrar loglanmasini engellemek icin
 basit bir "tekrar sayaci" ve soguma (cooldown) mekanizmasi icerir.

 Yetenekler:
   - handle()            : Hatayi kaydet, oneri uret, gerekirse tekrar deneme
   - retry()             : Bir fonksiyonu belirli sayida tekrar dene (backoff ile)
   - register_recovery() : Hata tipi icin ozel kurtarma fonksiyonu tanimla
   - get_error_summary() : Hata ozetini dondurur
   - print_summary()     : Ozeti konsola yazar

 Ornek:
   handler = ErrorHandler(logger=logger)
   ok = handler.retry(lambda: adb.tap(100, 200), error_type="TAP_HATASI")
================================================================================
"""

from __future__ import annotations

import json
import time
import traceback
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import config


class ErrorHandler:
    """Hatalari siniflandiran, kaydeden ve kurtarma stratejisi uygulayan sinif."""

    # Hata tiplerine gore Turkce cozum onerileri
    SUGGESTIONS: Dict[str, str] = {
        "ADB_ERROR": (
            "Emulator calisiyor mu kontrol edin. LDPlayer icin: adb connect 127.0.0.1:5555. "
            "scripts/setup_adb.ps1 tekrar calistirilabilir."
        ),
        "ADB_NOT_CONNECTED": (
            "ADB baglantisi yok. LDPlayer ayarlarindan 'ADB Debug' acin ve "
            "adb devices komutunu kontrol edin."
        ),
        "SCREENSHOT_ERROR": (
            "Ekran goruntusu alinamadi. Emulator penceresi kucultulmus veya "
            "cihaz mesgul olabilir."
        ),
        "TEMPLATE_NOT_FOUND": (
            "Template bulunamadi. assets/templates/ klasorundeki PNG dosyalarinin "
            "dogru oldugundan emin olun; calibrate.py -> [5] ile test edin."
        ),
        "HOME_ATTACK_BUTTON": (
            "Ana ekranda saldiri butonu yok. Oyunda farkli bir ekranda olabilirsiniz "
            "veya attack_button.png eski surum olabilir."
        ),
        "FIND_MATCH_BUTTON": (
            "Eslesme butonu bulunamadi. Klan savasi / etkinlik ekraninda olabilirsiniz; "
            "find_match.png template'ini guncelleyin."
        ),
        "BATTLE_TIMEOUT": (
            "Savas beklenenden uzun surdu. BATTLE_TIMEOUT degerini config.py'da artirin "
            "veya return_home.png template'ini kontrol edin."
        ),
        "OCR_ERROR": (
            "OCR sayilari okuyamiyor. calibrate.py -> [1] ile bolgeleri kalibre edin. "
            "Tesseract kurulu mu: tesseract --version."
        ),
        "OCR_NOT_INSTALLED": (
            "Tesseract bulunamadi! scripts/install_tesseract.ps1 (Windows) veya "
            "scripts/install_tesseract.sh (Linux) calistirin."
        ),
        "AI_ERROR": (
            "Yerel AI (Ollama) cevap vermiyor. 'ollama serve' calisiyor mu ve "
            "'ollama pull llava:7b' yapildi mi kontrol edin."
        ),
        "PLAN_ERROR": (
            "Savas plani hatasi. python main.py -> [2] ile yeni plan kaydedin; "
            "data/battle_plans.json dosyasinin bozuk olmadigindan emin olun."
        ),
        "CONFIG_ERROR": "config.py degerlerini kontrol edin (esikler, koordinatlar).",
        "UNKNOWN": "Bilinmeyen hata. data/errors/ klasorundeki detaylara bakin.",
    }

    def __init__(
        self,
        logger: Any = None,
        max_repeats: int = 3,
        cooldown: float = 20.0,
        retry_delay: float = 2.0,
    ) -> None:
        """
        ErrorHandler nesnesini olusturur.

        Args:
            logger (Any): DataLogger benzeri nesne (log_error metodu olmali).
            max_repeats (int): Ayni hata tipinin ust uste kaydedilme limiti.
            cooldown (float): Ayni hata icin minimum kayit araligi (saniye).
            retry_delay (float): retry() fonksiyonunda temel bekleme (saniye).

        Returns:
            None
        """
        self.logger = logger
        self.max_repeats: int = int(max_repeats)
        self.cooldown: float = float(cooldown)
        self.retry_delay: float = float(retry_delay)

        self.error_counts: Counter = Counter()
        self.last_seen: Dict[str, float] = {}
        self.suppressed: Counter = Counter()
        self.error_history: List[Dict[str, Any]] = []
        self.recovery_functions: Dict[str, Callable[[], bool]] = {}
        self.fatal_types: List[str] = ["ADB_NOT_CONNECTED", "OCR_NOT_INSTALLED"]

        print("[ERROR-HANDLER] Hata yoneticisi hazir.")

    # -------------------------------------------------------------------------
    # ANA HATA ISLEME
    # -------------------------------------------------------------------------
    def classify(self, error_type: str, description: str = "") -> str:
        """
        Verilen hata tipini/aciklamayi bilinen kategorilere esler.

        Args:
            error_type (str): Ham hata tipi.
            description (str): Hata aciklamasi.

        Returns:
            str: Kategori anahtari (SUGGESTIONS anahtarlarindan biri).
        """
        try:
            combined = f"{error_type} {description}".upper()
            for key in self.SUGGESTIONS:
                if key.upper() in combined:
                    return key
            if "TIMEOUT" in combined or "ZAMAN ASIMI" in combined:
                return "BATTLE_TIMEOUT"
            if "OCR" in combined or "TESSERACT" in combined:
                return "OCR_ERROR"
            if "TEMPLATE" in combined or "BULUNAMADI" in combined:
                return "TEMPLATE_NOT_FOUND"
            if "ADB" in combined or "CIHAZ" in combined:
                return "ADB_ERROR"
            if "PLAN" in combined:
                return "PLAN_ERROR"
            if "AI" in combined or "OLLAMA" in combined:
                return "AI_ERROR"
            return error_type if error_type in self.SUGGESTIONS else "UNKNOWN"
        except Exception:
            return "UNKNOWN"

    def handle(
        self,
        error_type: str,
        description: str,
        screenshot_path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[BaseException] = None,
    ) -> Dict[str, Any]:
        """
        Bir hatayi kaydeder, oneri uretir ve varsa kurtarma fonksiyonunu calistirir.

        Args:
            error_type (str): Hata tipi (orn. "ADB_ERROR").
            description (str): Turkce aciklama.
            screenshot_path (Optional[str]): Ilgili ekran goruntusu.
            context (Optional[Dict[str, Any]]): Ek baglam bilgileri.
            exception (Optional[BaseException]): Yakalanan istisna nesnesi.

        Returns:
            Dict[str, Any]: {"type", "category", "suggestion", "recovered", "count"}
        """
        category = "UNKNOWN"
        try:
            category = self.classify(error_type, description)
            now = time.time()
            self.error_counts[category] += 1

            # Soguma kontrolu: ayni hata cok sik loglanmasin
            last = self.last_seen.get(category, 0.0)
            if (now - last) < self.cooldown and self.error_counts[category] > self.max_repeats:
                self.suppressed[category] += 1
                return {
                    "type": error_type,
                    "category": category,
                    "suggestion": self.SUGGESTIONS.get(category, ""),
                    "recovered": False,
                    "count": self.error_counts[category],
                    "suppressed": True,
                }
            self.last_seen[category] = now

            suggestion = self.SUGGESTIONS.get(category, self.SUGGESTIONS["UNKNOWN"])
            record: Dict[str, Any] = {
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "type": error_type,
                "category": category,
                "description": description,
                "suggestion": suggestion,
                "screenshot": screenshot_path,
                "context": context or {},
                "traceback": self._format_traceback(exception),
            }
            self.error_history.append(record)
            if len(self.error_history) > 500:
                self.error_history = self.error_history[-500:]

            print("=" * 78)
            print(f" [HATA] {category} -> {error_type}")
            print(f" Aciklama : {description}")
            print(f" Oneri    : {suggestion}")
            print("=" * 78)

            # Logger'a kaydet
            if self.logger is not None and hasattr(self.logger, "log_error"):
                try:
                    self.logger.log_error(
                        error_type=error_type,
                        description=description,
                        screenshot_path=screenshot_path,
                        context=context,
                    )
                except Exception as log_error:
                    print(f"[!] Hatayi loglarken sorun olustu: {log_error}")

            # Ozel kurtarma fonksiyonu var mi?
            recovered = False
            recovery = self.recovery_functions.get(category)
            if callable(recovery):
                try:
                    recovered = bool(recovery())
                    durum = "BASARILI" if recovered else "BASARISIZ"
                    print(f"[ERROR-HANDLER] Kurtarma denemesi -> {durum}")
                except Exception as recovery_error:
                    print(f"[!] Kurtarma fonksiyonu hatasi: {recovery_error}")

            return {
                "type": error_type,
                "category": category,
                "suggestion": suggestion,
                "recovered": recovered,
                "count": self.error_counts[category],
            }
        except Exception as error:
            print(f"[!] Hata yonetimi sirasinda kritik hata: {error}")
            return {
                "type": error_type,
                "category": category,
                "suggestion": "",
                "recovered": False,
                "count": self.error_counts.get(category, 0),
            }

    # -------------------------------------------------------------------------
    # TEKRAR DENEME
    # -------------------------------------------------------------------------
    def retry(
        self,
        func: Callable[[], Any],
        attempts: int = 3,
        error_type: str = "GENEL_HATA",
        delay: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Bir fonksiyonu artan bekleme suresiyle birlikte tekrar dener.

        Args:
            func (Callable[[], Any]): Calistirilacak fonksiyon (basariliysa True dondurmeli).
            attempts (int): Maksimum deneme sayisi.
            error_type (str): Hata kaydinda kullanilacak tip.
            delay (Optional[float]): Temel bekleme suresi (None ise self.retry_delay).
            context (Optional[Dict[str, Any]]): Hata kaydi icin baglam.

        Returns:
            bool: True -> fonksiyon en az bir kez basarili oldu.
        """
        base_delay = self.retry_delay if delay is None else float(delay)
        for attempt in range(1, max(1, int(attempts)) + 1):
            try:
                result = func()
                if result is not False and result is not None:
                    if attempt > 1:
                        print(f"[ERROR-HANDLER] Deneme {attempt} basarili ({error_type}).")
                    return True
                print(f"[ERROR-HANDLER] Deneme {attempt}/{attempts} basarisiz ({error_type}).")
            except Exception as error:
                print(f"[!] Deneme {attempt}/{attempts} istisna ({error_type}): {error}")
                self.handle(
                    error_type,
                    f"Deneme {attempt}/{attempts} istisna ile sonuclandi: {error}",
                    context=context,
                    exception=error,
                )
            if attempt < attempts:
                wait = base_delay * attempt
                print(f"[ERROR-HANDLER] {wait:.1f} saniye sonra tekrar denenecek...")
                time.sleep(wait)

        self.handle(
            error_type,
            f"{attempts} denemede de basarisiz oldu.",
            context=context,
        )
        return False

    @staticmethod
    def _format_traceback(exception: Optional[BaseException]) -> str:
        """
        Istisna nesnesini okunabilir traceback metnine cevirir.

        Args:
            exception (Optional[BaseException]): Yakalanan istisna.

        Returns:
            str: Traceback metni (istisna yoksa bos string).
        """
        try:
            if exception is None:
                return ""
            return "".join(
                traceback.format_exception(
                    type(exception), exception, exception.__traceback__
                )
            )
        except Exception as error:
            return f"Traceback olusturulamadi: {error}"

    def register_recovery(self, category: str, func: Callable[[], bool]) -> None:
        """
        Belirli bir hata kategorisi icin kurtarma fonksiyonu tanimlar.

        Args:
            category (str): Hata kategorisi (SUGGESTIONS anahtari).
            func (Callable[[], bool]): Kurtarma fonksiyonu (True = basarili).

        Returns:
            None
        """
        try:
            self.recovery_functions[category] = func
            print(f"[ERROR-HANDLER] Kurtarma fonksiyonu tanimlandi -> {category}")
        except Exception as error:
            print(f"[!] Kurtarma fonksiyonu tanimlama hatasi: {error}")

    def is_fatal(self, category: str) -> bool:
        """
        Hatayi cozemediginizde botun durmasi gerekip gerekmedigini soyler.

        Args:
            category (str): Hata kategorisi.

        Returns:
            bool: True -> kritik hata (bot durmali).
        """
        try:
            return category in self.fatal_types
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # OZET / RAPORLAMA
    # -------------------------------------------------------------------------
    def get_error_summary(self) -> Dict[str, Any]:
        """
        Hata ozetini sozluk olarak dondurur.

        Returns:
            Dict[str, Any]: {"total", "by_category", "suppressed", "fatal_count", "last_errors"}
        """
        try:
            fatal_count = sum(
                count for key, count in self.error_counts.items() if key in self.fatal_types
            )
            return {
                "total": int(sum(self.error_counts.values())),
                "by_category": dict(self.error_counts),
                "suppressed": dict(self.suppressed),
                "fatal_count": int(fatal_count),
                "last_errors": self.error_history[-5:],
            }
        except Exception as error:
            print(f"[!] Ozet olusturma hatasi: {error}")
            return {
                "total": 0,
                "by_category": {},
                "suppressed": {},
                "fatal_count": 0,
                "last_errors": [],
            }

    def print_summary(self) -> None:
        """
        Hata ozetini Turkce olarak konsola yazar.

        Returns:
            None
        """
        try:
            summary = self.get_error_summary()
            print("=" * 78)
            print(" HATA OZETI")
            print("=" * 78)
            print(f" Toplam hata   : {summary['total']}")
            print(f" Kritik hata   : {summary['fatal_count']}")
            if summary["by_category"]:
                print(" Kategoriler   :")
                for key, value in sorted(
                    summary["by_category"].items(), key=lambda item: item[1], reverse=True
                ):
                    print(f"    - {key:<22} {value}")
            else:
                print(" Kategoriler   : (hata kaydi yok)")
            if summary["suppressed"]:
                print(f" Bastirilan    : {summary['suppressed']}")
            print("=" * 78)
        except Exception as error:
            print(f"[!] Ozet yazma hatasi: {error}")

    def export_summary(self, path: Optional[str] = None) -> Optional[str]:
        """
        Hata ozetini JSON dosyasina kaydeder.

        Args:
            path (Optional[str]): Hedef dosya. None ise data/errors/error_summary.json.

        Returns:
            Optional[str]: Kaydedilen dosya yolu veya None.
        """
        try:
            target = Path(path) if path else (Path(config.ERRORS_DIR) / "error_summary.json")
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as handle:
                json.dump(self.get_error_summary(), handle, indent=4, ensure_ascii=False)
            print(f"[ERROR-HANDLER] Ozet kaydedildi -> {target}")
            return str(target)
        except Exception as error:
            print(f"[!] Ozet disa aktarma hatasi: {error}")
            return None


if __name__ == "__main__":  # pragma: no cover - elle test
    handler = ErrorHandler()
    handler.handle("ADB_ERROR", "Cihaz baglantisi koptu (demo).")
    handler.print_summary()
