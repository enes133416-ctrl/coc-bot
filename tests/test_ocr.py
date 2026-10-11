"""
================================================================================
 tests/test_ocr.py - OCR Motoru Testleri
================================================================================
 OCREngine sinifinin on isleme, sayi okuma ve loot okuma davranislarini test eder.

 Testler sentetik (kod ile uretilen) goruntuler kullanir; oyun ekrani veya ADB
 baglantisi gerekmez. Tesseract kurulu degilse OCR testleri otomatik atlanir.

   test_read_number_valid    -> gecerli goruntude sayi okur
   test_read_number_empty    -> bos goruntude 0 doner
   test_preprocess           -> on isleme ciktisi 3x boyutta olur
   test_read_loot_structure  -> loot sozlugu dogru anahtarlari icerir
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

import config  # noqa: E402
from core.ocr_engine import OCREngine  # noqa: E402

try:
    import cv2
    import numpy as np

    CV2_AVAILABLE = True
except ImportError:  # pragma: no cover - bagimlilik eksikse
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    CV2_AVAILABLE = False


def create_text_image(
    text: str = "1234567",
    width: int = 400,
    height: int = 120,
    background: int = 255,
    text_color: int = 0,
) -> "np.ndarray":
    """
    Uzerinde okunabilir sayi bulunan sentetik bir goruntu uretir.

    Args:
        text (str): Goruntuye yazilacak metin.
        width (int): Goruntu genisligi.
        height (int): Goruntu yuksekligi.
        background (int): Arka plan gri ton degeri (0-255).
        text_color (int): Metin rengi gri ton degeri (0-255).

    Returns:
        np.ndarray: Uretilen BGR goruntusu.
    """
    image = np.full((height, width, 3), background, dtype=np.uint8)
    cv2.putText(
        image,
        text,
        (20, int(height * 0.68)),
        cv2.FONT_HERSHEY_SIMPLEX,
        2.0,
        (text_color, text_color, text_color),
        4,
        cv2.LINE_AA,
    )
    return image


class TestOCREngine(unittest.TestCase):
    """OCREngine sinifi icin birim testleri."""

    @classmethod
    def setUpClass(cls) -> None:
        """Test sinifi baslarken motoru ve gecici klasoru hazirlar."""
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="coc_test_ocr_")
        cls.temp_path = Path(cls.temp_dir.name)
        cls.engine = OCREngine()

    @classmethod
    def tearDownClass(cls) -> None:
        """Gecici klasoru temizler."""
        cls.temp_dir.cleanup()

    def _write_image(self, image: "np.ndarray", name: str) -> str:
        """
        Goruntuyu gecici klasore kaydeder.

        Args:
            image (np.ndarray): Kaydedilecek goruntu.
            name (str): Dosya adi.

        Returns:
            str: Kaydedilen dosyanin yolu.
        """
        target = self.temp_path / name
        cv2.imwrite(str(target), image)
        return str(target)

    def test_read_number_valid(self) -> None:
        """Gecerli bir goruntuden sayi okunmasini test eder."""
        if not CV2_AVAILABLE:
            self.skipTest("OpenCV yuklu degil.")
        if not self.engine.available:
            self.skipTest("Tesseract kurulu degil, OCR testi atlandi.")

        image = create_text_image("1234567", width=600, height=160)
        path = self._write_image(image, "valid_number.png")

        value = self.engine.read_number(path)
        self.assertIsInstance(value, int, "read_number tam sayi dondurmeli.")
        self.assertGreater(value, 0, "Gecerli goruntude sayi okunmali (0'dan buyuk).")
        self.assertAlmostEqual(
            value, 1234567, delta=1234567 * 0.35,
            msg=f"Okunan deger beklenene yakin olmali, okunan: {value}",
        )

    def test_read_number_empty(self) -> None:
        """Bos (yazisiz) goruntude 0 donmesini test eder."""
        if not CV2_AVAILABLE:
            self.skipTest("OpenCV yuklu degil.")

        image = np.full((120, 400, 3), 255, dtype=np.uint8)
        path = self._write_image(image, "empty.png")

        value = self.engine.read_number(path)
        self.assertEqual(value, 0, "Bos goruntude 0 donmeli.")

    def test_read_number_invalid_path(self) -> None:
        """Olmayan bir dosya icin hata vermeden 0 donmesini test eder."""
        value = self.engine.read_number(str(self.temp_path / "yok_boyle_dosya.png"))
        self.assertEqual(value, 0, "Gecersiz yol icin 0 donmeli ve hata firlatilmamali.")

    def test_preprocess(self) -> None:
        """On isleme ciktisinin 3x boyutta ve tek kanalli oldugunu test eder."""
        if not CV2_AVAILABLE:
            self.skipTest("OpenCV yuklu degil.")

        source = np.full((40, 100, 3), 200, dtype=np.uint8)
        processed = self.engine.preprocess_for_ocr(source, scale=3.0)
        self.assertIsNotNone(processed, "On isleme ciktisi None olmamali.")
        self.assertEqual(
            processed.shape[0], 120, "Yukseklik 3 katina cikmali (40 -> 120)."
        )
        self.assertEqual(
            processed.shape[1], 300, "Genislik 3 katina cikmali (100 -> 300)."
        )
        self.assertEqual(len(processed.shape), 2, "Cikti tek kanalli (gri) olmali.")
        self.assertEqual(processed.dtype, np.uint8, "Cikti uint8 tipinde olmali.")

    def test_preprocess_invalid_input(self) -> None:
        """None girdi icin on islemenin None donmesini test eder."""
        if not CV2_AVAILABLE:
            self.skipTest("OpenCV yuklu degil.")
        self.assertIsNone(self.engine.preprocess_for_ocr(None))  # type: ignore[arg-type]

    def test_read_loot_structure(self) -> None:
        """read_loot ciktisinin dogru anahtarlari icerdigini test eder."""
        if not CV2_AVAILABLE:
            self.skipTest("OpenCV yuklu degil.")

        image = create_text_image("750000", width=config.SCREEN_WIDTH, height=120)
        path = self._write_image(image, "loot.png")

        loot = self.engine.read_loot(path)
        self.assertIsInstance(loot, dict, "read_loot sozluk dondurmeli.")
        for key in ("gold", "elixir", "dark", "total"):
            self.assertIn(key, loot, f"'{key}' anahtari sonucta bulunmali.")
            self.assertIsInstance(loot[key], int, f"'{key}' tam sayi olmali.")

        expected_total = loot["gold"] + loot["elixir"] + int(
            loot["dark"] * config.DARK_ELIXIR_MULTIPLIER
        )
        self.assertEqual(
            loot["total"], expected_total, "Toplam = altin + iksir + kara*carpan olmali."
        )

    def test_parse_number_formats(self) -> None:
        """Farkli sayi formatlarinin dogru ayristirildigini test eder (Tesseract gerekmez)."""
        cases = {
            "1,234,567": 1_234_567,
            "1234567": 1_234_567,
            "1.6M": 1_600_000,
            "850K": 850_000,
            "": 0,
            "abc": 0,
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                parsed = self.engine._parse_number(raw)
                if expected == 0:
                    self.assertEqual(parsed, 0, f"'{raw}' icin 0 bekleniyordu.")
                else:
                    self.assertEqual(
                        parsed, expected, f"'{raw}' icin {expected} bekleniyordu, {parsed} geldi."
                    )


if __name__ == "__main__":  # pragma: no cover - elle calistirma
    unittest.main(verbosity=2)
