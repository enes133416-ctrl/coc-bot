"""
================================================================================
 core/screen_capture.py - Ekran Yakalama Modulu
================================================================================
 ADBController'i kullanarak ekran goruntusu alir, onbellege alir ve OpenCV
 (numpy) formatinda bolge/parca cikarma islemlerini saglar.

 Ozellikler:
   - Tekrarli cagrilarda gereksiz adb komutu gondermez (onbellek + TTL)
   - Bolge (region) bazli kirpma ve numpy dizisi dondurme
   - Ekran goruntusu gecmisi (debug icin)
   - Oturum klasorune otomatik kayit

 Ornek:
   capture = ScreenCapture(adb=ADBController())
   path = capture.capture()
   crop = capture.capture_region({"x": 10, "y": 10, "w": 200, "h": 50})
================================================================================
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional

import config

try:
    import cv2
    import numpy as np

    CV2_AVAILABLE = True
except ImportError:  # pragma: no cover - bagimlilik eksikse
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    CV2_AVAILABLE = False


class ScreenCapture:
    """ADB uzerinden ekran goruntusu alan ve isleyen sinif."""

    def __init__(
        self,
        adb: "object",
        output_dir: Optional[str] = None,
        cache_ttl: float = 0.4,
    ) -> None:
        """
        ScreenCapture nesnesini olusturur.

        Args:
            adb (object): ADBController benzeri nesne (screenshot/get_screen_size icermeli).
            output_dir (Optional[str]): Goruntulerin kaydedilecegi klasor.
            cache_ttl (float): Onbellek gecerlilik suresi (saniye).

        Returns:
            None
        """
        self.adb = adb
        self.output_dir: Path = Path(output_dir) if output_dir else config.SCREENSHOT_DIR
        self.cache_ttl: float = cache_ttl
        self.cache_enabled: bool = True
        self._last_path: Optional[str] = None
        self._last_time: float = 0.0
        self._history: List[str] = []
        self._counter: int = 0

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as error:
            print(f"[!] Ekran goruntusu klasoru olusturulamadi: {error}")
        print(f"[CAPTURE] Ekran yakalayici hazir -> {self.output_dir}")

    # -------------------------------------------------------------------------
    # YAKALAMA
    # -------------------------------------------------------------------------
    def capture(self, name: Optional[str] = None, force: bool = False) -> Optional[str]:
        """
        Ekran goruntusu alir ve dosya yolunu dondurur.

        Args:
            name (Optional[str]): Ozel dosya adi (uzantisiz). None ise zaman damgali ad.
            force (bool): True ise onbellek yok sayilir ve yeni goruntu alinir.

        Returns:
            Optional[str]: Kaydedilen PNG dosyasinin yolu, hata olursa onbellekten
                           veya None.
        """
        try:
            now = time.time()
            if (
                not force
                and self.cache_enabled
                and self._last_path
                and (now - self._last_time) < self.cache_ttl
                and Path(self._last_path).exists()
            ):
                return self._last_path

            self._counter += 1
            if name:
                file_name = name if name.lower().endswith(".png") else f"{name}.png"
            else:
                stamp = time.strftime("%Y%m%d_%H%M%S")
                file_name = f"screen_{stamp}_{self._counter:04d}.png"

            target = self.output_dir / file_name
            path = self.adb.screenshot(str(target))
            if path and Path(path).exists():
                self._last_path = path
                self._last_time = time.time()
                self._history.append(path)
                return path

            print("[!] Ekran goruntusu alinamadi.")
            return self._last_path
        except Exception as error:
            print(f"[!] Ekran yakalama hatasi: {error}")
            return self._last_path

    def capture_to(self, full_path: str, force: bool = True) -> Optional[str]:
        """
        Ekran goruntusunu belirtilen tam yola kaydeder.

        Args:
            full_path (str): Hedef dosya yolu.
            force (bool): True ise onbellek kullanilmaz.

        Returns:
            Optional[str]: Kaydedilen dosya yolu veya None.
        """
        try:
            target = Path(full_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            path = self.adb.screenshot(str(target))
            if path and Path(path).exists():
                self._last_path = path
                self._last_time = time.time()
                self._history.append(path)
                return path
            return None
        except Exception as error:
            print(f"[!] Ekran goruntusu kaydetme hatasi: {error}")
            return None

    def capture_array(self, force: bool = True) -> Optional["np.ndarray"]:
        """
        Ekrani numpy dizisi (BGR) olarak dondurur.

        Args:
            force (bool): True ise yeni goruntu alinir.

        Returns:
            Optional[np.ndarray]: Goruntu dizisi, hata/eksik bagimlilik halinde None.
        """
        try:
            if not CV2_AVAILABLE:
                print("[!] OpenCV/numpy yuklu degil, dizi donusturulemiyor.")
                return None
            path = self.capture(force=force)
            if not path:
                return None
            return cv2.imread(path)
        except Exception as error:
            print(f"[!] Goruntu dizisi hatasi: {error}")
            return None

    def capture_region(
        self,
        region: Dict[str, int],
        force: bool = True,
    ) -> Optional["np.ndarray"]:
        """
        Ekranin belirli bir bolgesini kirpip numpy dizisi dondurur.

        Args:
            region (Dict[str, int]): {"x", "y", "w", "h"} sozlugu.
            force (bool): True ise yeni ekran goruntusu alinir.

        Returns:
            Optional[np.ndarray]: Kirpilmis goruntu, hata halinde None.
        """
        try:
            if not CV2_AVAILABLE:
                print("[!] OpenCV/numpy yuklu degil, bolge kirpma yapilamaz.")
                return None
            image = self.capture_array(force=force)
            if image is None:
                return None
            return self.crop_region(image, region)
        except Exception as error:
            print(f"[!] Bolge yakalama hatasi: {error}")
            return None

    # -------------------------------------------------------------------------
    # GORUNTU ISLEME YARDIMCILARI
    # -------------------------------------------------------------------------
    @staticmethod
    def crop_region(image: "np.ndarray", region: Dict[str, int]) -> Optional["np.ndarray"]:
        """
        Verilen goruntuden bolgeyi guvenli sekilde kirpar.

        Args:
            image (np.ndarray): Kaynak goruntu (BGR).
            region (Dict[str, int]): {"x", "y", "w", "h"}.

        Returns:
            Optional[np.ndarray]: Kirpilmis goruntu, gecersiz bolgede None.
        """
        try:
            if image is None or not hasattr(image, "shape"):
                print("[!] Gecersiz goruntu nesnesi.")
                return None
            height, width = image.shape[:2]
            x = max(0, int(region.get("x", 0)))
            y = max(0, int(region.get("y", 0)))
            w = max(1, int(region.get("w", 1)))
            h = max(1, int(region.get("h", 1)))
            x2 = min(width, x + w)
            y2 = min(height, y + h)
            if x >= width or y >= height:
                print(f"[!] Bolge ekran disinda: {region}")
                return None
            return image[y:y2, x:x2].copy()
        except Exception as error:
            print(f"[!] Bolge kirpma hatasi: {error}")
            return None

    @staticmethod
    def open_image(path: str) -> Optional["np.ndarray"]:
        """
        Dosyadan goruntu okur.

        Args:
            path (str): Goruntu dosyasi yolu.

        Returns:
            Optional[np.ndarray]: Okunan goruntu veya None.
        """
        try:
            if not CV2_AVAILABLE:
                print("[!] OpenCV yuklu degil, goruntu okunamaz.")
                return None
            if not Path(path).exists():
                print(f"[!] Goruntu dosyasi yok: {path}")
                return None
            image = cv2.imread(path)
            if image is None:
                print(f"[!] Goruntu okunamadi (bozuk olabilir): {path}")
            return image
        except Exception as error:
            print(f"[!] Goruntu okuma hatasi: {error}")
            return None

    @staticmethod
    def save_image(image: "np.ndarray", path: str) -> bool:
        """
        Goruntuyu dosyaya kaydeder.

        Args:
            image (np.ndarray): Kaydedilecek goruntu.
            path (str): Hedef dosya yolu.

        Returns:
            bool: True -> kayit basarili.
        """
        try:
            if not CV2_AVAILABLE or image is None:
                return False
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            ok = bool(cv2.imwrite(str(target), image))
            if ok:
                print(f"[CAPTURE] Goruntu kaydedildi -> {target}")
            else:
                print(f"[!] Goruntu kaydedilemedi -> {target}")
            return ok
        except Exception as error:
            print(f"[!] Goruntu kaydetme hatasi: {error}")
            return False

    # -------------------------------------------------------------------------
    # YARDIMCILAR
    # -------------------------------------------------------------------------
    def get_screen_size(self) -> Dict[str, int]:
        """
        Ekran cozunurlugunu sozluk olarak dondurur.

        Returns:
            Dict[str, int]: {"width": int, "height": int}
        """
        try:
            size = self.adb.get_screen_size()
            if isinstance(size, (tuple, list)) and len(size) >= 2:
                return {"width": int(size[0]), "height": int(size[1])}
            print("[!] Beklenmeyen ekran boyutu formati, config varsayilani kullaniliyor.")
            return {"width": config.SCREEN_WIDTH, "height": config.SCREEN_HEIGHT}
        except Exception as error:
            print(f"[!] Ekran boyutu hatasi: {error}")
            return {"width": config.SCREEN_WIDTH, "height": config.SCREEN_HEIGHT}

    def get_last_path(self) -> Optional[str]:
        """
        Son alinan ekran goruntusunun yolunu dondurur.

        Returns:
            Optional[str]: Son goruntu yolu veya None.
        """
        return self._last_path

    def get_history(self, limit: int = 10) -> List[str]:
        """
        Alinan son ekran goruntulerinin yollarini dondurur.

        Args:
            limit (int): Dondurulecek maksimum dosya sayisi.

        Returns:
            List[str]: Dosya yolu listesi (en yeni en sonda).
        """
        try:
            if limit <= 0:
                return []
            return list(self._history[-limit:])
        except Exception as error:
            print(f"[!] Gecmis listesi hatasi: {error}")
            return []

    def cleanup(self, keep_last: int = 200) -> int:
        """
        Eski ekran goruntulerini silerek klasoru temizler.

        Args:
            keep_last (int): Korunacak en yeni dosya sayisi.

        Returns:
            int: Silinen dosya sayisi.
        """
        deleted = 0
        try:
            files = sorted(
                self.output_dir.glob("*.png"),
                key=lambda item: item.stat().st_mtime,
            )
            for old_file in files[:-keep_last] if keep_last > 0 else files:
                old_file.unlink()
                deleted += 1
            if deleted:
                print(f"[CAPTURE] {deleted} eski ekran goruntusu silindi.")
        except Exception as error:
            print(f"[!] Temizlik hatasi: {error}")
        return deleted

    def __repr__(self) -> str:
        """
        Sinifin okunabilir temsili.

        Returns:
            str: Temsil metni.
        """
        return f"ScreenCapture(dir={self.output_dir}, cache_ttl={self.cache_ttl}s)"


if __name__ == "__main__":  # pragma: no cover - elle test
    from core.adb_controller import ADBController

    controller = ADBController()
    capture = ScreenCapture(adb=controller)
    saved = capture.capture(name="test_ekran")
    print(f"Kaydedilen dosya: {saved}")
    print(f"Ekran boyutu    : {capture.get_screen_size()}")
