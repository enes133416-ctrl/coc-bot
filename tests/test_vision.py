"""
================================================================================
 tests/test_vision.py - Goruntu Isleme (Vision) Testleri
================================================================================
 VisionEngine sinifinin template arama, hatali yol davranisi ve renk tespiti
 fonksiyonlarini test eder. Sentetik goruntuler kullanilir; ADB gerekmez.

   test_find_template_not_found  -> olmayan template icin found=False
   test_find_template_invalid_path -> hatali yol icin hata firlatilmaz
   test_detect_color_region      -> siyah goruntude renk bulunamaz
================================================================================
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

# Proje kokunu yola ekle
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.vision_engine import VisionEngine  # noqa: E402

try:
    import cv2
    import numpy as np

    CV2_AVAILABLE = True
except ImportError:  # pragma: no cover - bagimlilik eksikse
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    CV2_AVAILABLE = False


class TestVisionEngine(unittest.TestCase):
    """VisionEngine sinifi icin birim testleri."""

    @classmethod
    def setUpClass(cls) -> None:
        """Gecici klasor ve test motorunu hazirlar."""
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="coc_test_vision_")
        cls.temp_path = Path(cls.temp_dir.name)
        cls.engine = VisionEngine(threshold=0.90, use_multi_scale=True)

    @classmethod
    def tearDownClass(cls) -> None:
        """Gecici klasoru temizler."""
        cls.temp_dir.cleanup()

    def _save(self, image: "np.ndarray", name: str) -> str:
        """
        Goruntuyu gecici klasore kaydeder.

        Args:
            image (np.ndarray): Kaydedilecek goruntu.
            name (str): Dosya adi.

        Returns:
            str: Dosya yolu.
        """
        target = self.temp_path / name
        cv2.imwrite(str(target), image)
        return str(target)

    def _noise_image(self, width: int, height: int, seed: int) -> "np.ndarray":
        """
        Tekrarlanabilir rastgele gurultu goruntusu uretir.

        Args:
            width (int): Genislik.
            height (int): Yukseklik.
            seed (int): Rastgelelik tohumu.

        Returns:
            np.ndarray: BGR gurultu goruntusu.
        """
        generator = np.random.default_rng(seed)
        return generator.integers(0, 256, (height, width, 3), dtype=np.uint8)

    def test_find_template_not_found(self) -> None:
        """Ekranda bulunmayan bir template icin found=False donmesini test eder."""
        if not CV2_AVAILABLE:
            self.skipTest("OpenCV yuklu degil.")

        screenshot = self._noise_image(320, 240, seed=1)
        template = self._noise_image(40, 30, seed=99)

        screenshot_path = self._save(screenshot, "ekran.png")
        template_path = self._save(template, "olmayan_template.png")

        result = self.engine.find_template(screenshot_path, template_path)
        self.assertIsInstance(result, dict, "Sonuc sozluk olmali.")
        self.assertIn("found", result)
        self.assertIn("x", result)
        self.assertIn("y", result)
        self.assertIn("confidence", result)
        self.assertFalse(result["found"], "Olmayan template bulunmamali.")
        self.assertEqual(result["x"], 0)
        self.assertEqual(result["y"], 0)
        self.assertLess(result["confidence"], 0.90, "Guven esigin altinda olmali.")
        self.assertIsInstance(result["confidence"], float)

    def test_find_template_found(self) -> None:
        """Ekranda bulunan bir template'in dogru tespit edildigini test eder."""
        if not CV2_AVAILABLE:
            self.skipTest("OpenCV yuklu degil.")

        screenshot = self._noise_image(400, 300, seed=7)
        template = screenshot[100:140, 150:200].copy()  # ekrandan alinan parca

        screenshot_path = self._save(screenshot, "ekran2.png")
        template_path = self._save(template, "buton.png")

        result = self.engine.find_template(screenshot_path, template_path)
        self.assertTrue(result["found"], "Ekrandan alinan parca bulunmali.")
        self.assertGreaterEqual(result["confidence"], 0.90)
        self.assertAlmostEqual(result["x"], 150, delta=6, msg="X koordinati yakin olmali.")
        self.assertAlmostEqual(result["y"], 100, delta=6, msg="Y koordinati yakin olmali.")

    def test_find_template_invalid_path(self) -> None:
        """Hatali dosya yollarinda hata firlatilmadigini test eder."""
        if not CV2_AVAILABLE:
            self.skipTest("OpenCV yuklu degil.")

        result = self.engine.find_template(
            str(self.temp_path / "yok.png"),
            str(self.temp_path / "o_da_yok.png"),
        )
        self.assertIsInstance(result, dict)
        self.assertFalse(result["found"], "Gecersiz yolda found=False olmali.")
        self.assertEqual(result["confidence"], 0.0)

    def test_find_template_with_region(self) -> None:
        """Bolge verildiginde koordinatin ekran koordinatina cevrilmesini test eder."""
        if not CV2_AVAILABLE:
            self.skipTest("OpenCV yuklu degil.")

        screenshot = self._noise_image(500, 400, seed=3)
        template = screenshot[200:240, 300:360].copy()
        screenshot_path = self._save(screenshot, "ekran3.png")
        template_path = self._save(template, "buton2.png")

        result = self.engine.find_template(
            screenshot_path,
            template_path,
            region={"x": 250, "y": 150, "w": 200, "h": 150},
        )
        self.assertTrue(result["found"], "Bolge icinde template bulunmali.")
        self.assertAlmostEqual(result["x"], 300, delta=8)
        self.assertAlmostEqual(result["y"], 200, delta=8)

    def test_scale_cache_used(self) -> None:
        """Basarili eslesmeden sonra olcek onbelleginin doldugunu test eder."""
        if not CV2_AVAILABLE:
            self.skipTest("OpenCV yuklu degil.")

        screenshot = self._noise_image(300, 200, seed=11)
        template = screenshot[50:90, 80:130].copy()
        screenshot_path = self._save(screenshot, "ekran4.png")
        template_path = self._save(template, "buton3.png")

        self.engine.clear_cache()
        self.assertEqual(self.engine.get_cache(), {})
        result = self.engine.find_template(screenshot_path, template_path)
        self.assertTrue(result["found"])
        self.assertIn("buton3.png", self.engine.get_cache(), "Olcek onbellege alinmali.")

    def test_detect_color_region(self) -> None:
        """Siyah goruntude renk bulunamayacagini test eder."""
        if not CV2_AVAILABLE:
            self.skipTest("OpenCV yuklu degil.")

        black = np.zeros((240, 320, 3), dtype=np.uint8)
        path = self._save(black, "siyah.png")

        regions = self.engine.detect_color_region(
            path, lower_hsv=[0, 120, 120], upper_hsv=[10, 255, 255]
        )
        self.assertIsInstance(regions, list, "Sonuc liste olmali.")
        self.assertEqual(len(regions), 0, "Siyah goruntude kirmizi bolge olmamali.")

    def test_detect_color_region_found(self) -> None:
        """Kirmizi bir dikdortgenin tespit edildigini test eder."""
        if not CV2_AVAILABLE:
            self.skipTest("OpenCV yuklu degil.")

        image = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.rectangle(image, (50, 60), (150, 140), (0, 0, 255), -1)  # BGR kirmizi
        path = self._save(image, "kirmizi.png")

        regions = self.engine.detect_color_region(
            path, lower_hsv=[0, 120, 120], upper_hsv=[10, 255, 255], min_area=100
        )
        self.assertGreaterEqual(len(regions), 1, "Kirmizi dikdortgen bulunmali.")
        first = regions[0]
        self.assertGreaterEqual(int(first["w"]), 50)
        self.assertGreaterEqual(int(first["h"]), 40)

    def test_draw_debug(self) -> None:
        """Debug goruntusunun olusturuldugunu test eder."""
        if not CV2_AVAILABLE:
            self.skipTest("OpenCV yuklu degil.")

        screenshot = self._noise_image(200, 150, seed=5)
        path = self._save(screenshot, "debug_kaynak.png")
        output = self.temp_path / "debug_cikti.png"

        result = self.engine.draw_debug(
            path,
            {"found": True, "x": 20, "y": 30, "width": 40, "height": 20, "confidence": 0.95},
            str(output),
        )
        self.assertIsNotNone(result, "Debug cikti yolu donmeli.")
        self.assertTrue(output.exists(), "Debug goruntusu olusmali.")

    def test_scale_list_length(self) -> None:
        """Olcek listesinin 13 adim icerdigini test eder."""
        scales = self.engine._scale_list()
        self.assertEqual(len(scales), 13, "13 farkli olcek denenmeli.")
        self.assertAlmostEqual(min(scales), 0.7, places=2)
        self.assertAlmostEqual(max(scales), 1.3, places=2)


if __name__ == "__main__":  # pragma: no cover - elle calistirma
    unittest.main(verbosity=2)
