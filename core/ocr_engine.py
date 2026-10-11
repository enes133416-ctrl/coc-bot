"""
================================================================================
 core/ocr_engine.py - Tesseract OCR Motoru
================================================================================
 Oyun ekranindaki altin / iksir / kara iksir sayilarini yerel Tesseract OCR ile
 okur. Harici API kullanmaz, tamamen cevrimdisi calisir.

 Yetenekler:
   - preprocess_for_ocr() : 3x buyutme, gri ton, CLAHE, Otsu, morph close
   - read_number()        : tek bir bolgeden sayi okur (int)
   - read_loot()          : gold, elixir, dark, total sozlugu dondurur
   - calibrate_regions()  : OpenCV penceresinde trackbar ile bolge duzeltme
   - test_ocr()           : tum bolgeleri test edip sonuc basar

 Sayi formatlari desteklenir: "1,234,567" / "1.6M" / "850K" / "1234567"
================================================================================
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import config

try:
    import cv2
    import numpy as np

    CV2_AVAILABLE = True
except ImportError:  # pragma: no cover - bagimlilik eksikse
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    CV2_AVAILABLE = False

try:
    import pytesseract

    TESSERACT_MODULE_AVAILABLE = True
except ImportError:  # pragma: no cover - bagimlilik eksikse
    pytesseract = None  # type: ignore[assignment]
    TESSERACT_MODULE_AVAILABLE = False


class OCREngine:
    """Tesseract tabanli sayi okuma motoru."""

    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        lang: Optional[str] = None,
        psm: Optional[int] = None,
    ) -> None:
        """
        OCREngine nesnesini olusturur ve Tesseract kurulumunu test eder.

        Args:
            tesseract_cmd (Optional[str]): tesseract.exe yolu. None ise config'den alinir.
            lang (Optional[str]): OCR dili. None ise config.OCR_LANG.
            psm (Optional[int]): Sayfa segmentasyon modu. None ise config.OCR_PSM.

        Returns:
            None
        """
        self.tesseract_cmd: Optional[str] = tesseract_cmd or config.TESSERACT_CMD
        self.lang: str = lang or config.OCR_LANG
        self.psm: int = psm if psm is not None else config.OCR_PSM
        self.whitelist: str = config.OCR_DIGIT_WHITELIST
        self.available: bool = False
        self.last_error: str = ""
        self.stats: Dict[str, int] = {"read": 0, "ok": 0, "fail": 0}

        self._configure_tesseract()
        self.test_installation()

    # -------------------------------------------------------------------------
    # KURULUM
    # -------------------------------------------------------------------------
    def _configure_tesseract(self) -> None:
        """
        pytesseract modulune tesseract yolunu tanitir.

        Returns:
            None
        """
        try:
            if pytesseract is None:
                self.last_error = "pytesseract modulu yuklu degil (pip install pytesseract)."
                print(f"[!] {self.last_error}")
                return
            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
                print(f"[OCR] Tesseract yolu -> {self.tesseract_cmd}")
            else:
                print("[!] Tesseract yolu bulunamadi, PATH uzerinden denenecek.")
        except Exception as error:
            self.last_error = f"Tesseract yapilandirma hatasi: {error}"
            print(f"[!] {self.last_error}")

    def test_installation(self) -> bool:
        """
        Tesseract'in calisip calismadigini test eder.

        Returns:
            bool: True -> Tesseract hazir.
        """
        try:
            if pytesseract is None:
                return False
            version = pytesseract.get_tesseract_version()
            self.available = True
            print(f"[OK]  Tesseract hazir -> surum {version}")
            return True
        except Exception as error:
            self.available = False
            self.last_error = (
                f"Tesseract calistirilamadi ({error}). "
                "scripts/install_tesseract.ps1 veya install_tesseract.sh calistirin."
            )
            print(f"[!] {self.last_error}")
            return False

    # -------------------------------------------------------------------------
    # ON ISLEME
    # -------------------------------------------------------------------------
    def preprocess_for_ocr(
        self,
        image: "np.ndarray",
        scale: float = 3.0,
    ) -> Optional["np.ndarray"]:
        """
        OCR basarimini artirmak icin goruntuyu isler.

        Adimlar:
          1) 3x buyutme (interpolasyon: cubic)
          2) Gri tona cevirme
          3) CLAHE ile kontrast artirma
          4) Otsu esikleme (binary)
          5) Morph close ile gurultu temizleme

        Args:
            image (np.ndarray): Kaynak goruntu (BGR veya gri).
            scale (float): Buyutme katsayisi (varsayilan 3.0).

        Returns:
            Optional[np.ndarray]: Islenmis tek kanalli goruntu; hata halinde None.
        """
        try:
            if not CV2_AVAILABLE or image is None:
                print("[!] On isleme yapilamadi (OpenCV eksik ya da goruntu None).")
                return None

            # 1) Buyutme
            resized = cv2.resize(
                image,
                None,
                fx=float(scale),
                fy=float(scale),
                interpolation=cv2.INTER_CUBIC,
            )

            # 2) Gri ton
            if len(resized.shape) == 3 and resized.shape[2] >= 3:
                gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            else:
                gray = resized

            # 3) CLAHE kontrast
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)

            # 4) Otsu esikleme (aydinlik durumuna gore ters cevrilir)
            _thr, binary = cv2.threshold(
                enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            if float(np.mean(binary)) < 127.0:
                binary = cv2.bitwise_not(binary)

            # 5) Morph close ile gurultu temizleme
            kernel = np.ones((3, 3), np.uint8)
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)

            return cleaned
        except Exception as error:
            print(f"[!] On isleme hatasi: {error}")
            return None

    # -------------------------------------------------------------------------
    # SAYI OKUMA
    # -------------------------------------------------------------------------
    def _parse_number(self, text: str) -> int:
        """
        OCR ciktisindaki metni tam sayiya cevirir (M/K gibi kisaltmalari cozer).

        Args:
            text (str): OCR sonucu (orn. "1,234,567", "1.6M", "850K").

        Returns:
            int: Okunan sayi; cozulemezse 0.
        """
        try:
            if not text:
                return 0
            raw = text.strip().upper().replace(" ", "").replace("\n", "")

            # 1) Son ek (M = milyon, K = bin, B = milyar) once ayristirilir
            multiplier = 1
            if raw.endswith("MN"):
                multiplier = 1_000_000
                raw = raw[:-2]
            elif raw.endswith("M"):
                multiplier = 1_000_000
                raw = raw[:-1]
            elif raw.endswith("K"):
                multiplier = 1_000
                raw = raw[:-1]
            elif raw.endswith("B") and len(raw) > 1:
                multiplier = 1_000_000_000
                raw = raw[:-1]

            # 2) Harf -> rakam duzeltmesi SADECE su durumlarda yapilir:
            #    a) Govde en az bir gercek rakam iceriyorsa (orn. "l.6" -> "1.6")
            #    b) Govdenin tamami karistirilabilir harflerden olusuyorsa (orn. "IOO" -> "100")
            # Bu sayede "abc" gibi anlamsiz metinler sayiya cevrilmez.
            has_digit = any(character.isdigit() for character in raw)
            all_confusable = len(raw) >= 2 and bool(re.fullmatch(r"[OQILSBZGT.,]+", raw))
            if not has_digit and not all_confusable:
                return 0

            cleaned = raw.replace("O", "0").replace("Q", "0")
            cleaned = cleaned.replace("I", "1").replace("L", "1").replace("|", "1")
            cleaned = cleaned.replace("S", "5").replace("B", "8").replace("Z", "2")
            cleaned = cleaned.replace("G", "6").replace("T", "7")

            # 3) Sadece rakam, virgul ve nokta birak
            cleaned = re.sub(r"[^0-9.,]", "", cleaned)
            if not cleaned:
                return 0

            # 4) Binlik ayraclari temizle: 1,234,567 -> 1234567
            if cleaned.count(",") >= 1 and cleaned.count(".") >= 1:
                if cleaned.rfind(",") > cleaned.rfind("."):
                    cleaned = cleaned.replace(".", "").replace(",", ".")
                else:
                    cleaned = cleaned.replace(",", "")
            elif cleaned.count(",") >= 1:
                parts = cleaned.split(",")
                if len(parts) > 1 and len(parts[-1]) == 3 and all(
                    len(part) == 3 for part in parts[1:]
                ):
                    cleaned = cleaned.replace(",", "")
                else:
                    cleaned = cleaned.replace(",", ".")
            elif cleaned.count(".") >= 1:
                parts = cleaned.split(".")
                if len(parts) > 1 and not all(len(part) == 3 for part in parts[1:]):
                    pass  # ondalik kullanim: 1.6 -> 1.6
                else:
                    cleaned = cleaned.replace(".", "")

            value = float(cleaned) * multiplier
            return int(round(value))
        except Exception as error:
            print(f"[!] Sayi ayristirma hatasi ('{text}'): {error}")
            return 0

    def read_number(
        self,
        screenshot_path: str,
        region: Optional[Dict[str, int]] = None,
    ) -> int:
        """
        Ekran goruntusunun belirtilen bolgesinden tek bir sayi okur.

        Args:
            screenshot_path (str): Ekran goruntusu yolu.
            region (Optional[Dict[str, int]]): {"x","y","w","h"}; None ise tum goruntu.

        Returns:
            int: Okunan sayi; okunamazsa 0.
        """
        try:
            if not self.available:
                print("[!] Tesseract hazir degil, sayi okunamadi.")
                return 0
            image = self._load_region(screenshot_path, region)
            if image is None:
                return 0

            processed = self.preprocess_for_ocr(image)
            if processed is None:
                return 0

            self.stats["read"] += 1
            text = self._image_to_text(processed)
            value = self._parse_number(text)
            if value > 0:
                self.stats["ok"] += 1
            else:
                self.stats["fail"] += 1
                print(f"[OCR] Sayi okunamadi (ham metin: '{text.strip()}')")
            return value
        except Exception as error:
            self.stats["fail"] += 1
            print(f"[!] Sayi okuma hatasi: {error}")
            return 0

    def _image_to_text(self, image: "np.ndarray") -> str:
        """
        Islenmis goruntuyu Tesseract ile metne cevirir.

        Args:
            image (np.ndarray): Islenmis goruntu.

        Returns:
            str: OCR sonucu metin.
        """
        try:
            if pytesseract is None:
                return ""
            custom_config = (
                f"--oem 3 --psm {self.psm} "
                f"-c tessedit_char_whitelist={self.whitelist}"
            )
            return str(
                pytesseract.image_to_string(
                    image,
                    lang=self.lang,
                    config=custom_config,
                    timeout=config.OCR_TIMEOUT,
                )
            ).strip()
        except Exception as error:
            print(f"[!] Tesseract okuma hatasi: {error}")
            return ""

    def _load_region(
        self,
        screenshot_path: str,
        region: Optional[Dict[str, int]],
    ) -> Optional["np.ndarray"]:
        """
        Ekran goruntusunu yukler ve istenen bolgeyi kirpar.

        Args:
            screenshot_path (str): Goruntu dosyasi.
            region (Optional[Dict[str, int]]): Kirpilacak bolge.

        Returns:
            Optional[np.ndarray]: Bolge goruntusu veya None.
        """
        try:
            if not CV2_AVAILABLE:
                print("[!] OpenCV yuklu degil, goruntu okunamaz.")
                return None
            if not Path(screenshot_path).exists():
                print(f"[!] Ekran goruntusu bulunamadi: {screenshot_path}")
                return None
            image = cv2.imread(str(screenshot_path))
            if image is None:
                print("[!] Goruntu okunamadi (bozuk dosya olabilir).")
                return None
            if not region:
                return image

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
            print(f"[!] Bolge yukleme hatasi: {error}")
            return None

    # -------------------------------------------------------------------------
    # LOOT OKUMA
    # -------------------------------------------------------------------------
    def read_loot(self, screenshot_path: str) -> Dict[str, int]:
        """
        Rakip ekranindaki tum loot degerlerini okur.

        Args:
            screenshot_path (str): Ekran goruntusu yolu.

        Returns:
            Dict[str, int]: {"gold", "elixir", "dark", "total"}
                            total = gold + elixir + (dark * DARK_ELIXIR_MULTIPLIER)
        """
        loot: Dict[str, int] = {"gold": 0, "elixir": 0, "dark": 0, "total": 0}
        try:
            loot["gold"] = self.read_number(screenshot_path, config.get_ocr_region("gold"))
            loot["elixir"] = self.read_number(
                screenshot_path, config.get_ocr_region("elixir")
            )
            loot["dark"] = self.read_number(screenshot_path, config.get_ocr_region("dark"))
            loot["total"] = loot["gold"] + loot["elixir"] + int(
                loot["dark"] * config.DARK_ELIXIR_MULTIPLIER
            )
            print(
                f"[OCR] Loot -> altin={loot['gold']:,} iksir={loot['elixir']:,} "
                f"kara={loot['dark']:,} TOPLAM={loot['total']:,}"
            )
            return loot
        except Exception as error:
            print(f"[!] Loot okuma hatasi: {error}")
            return loot

    def read_gold(self, screenshot_path: str) -> int:
        """
        Sadece altin degerini okur.

        Args:
            screenshot_path (str): Ekran goruntusu yolu.

        Returns:
            int: Altin miktari.
        """
        return self.read_number(screenshot_path, config.get_ocr_region("gold"))

    def read_elixir(self, screenshot_path: str) -> int:
        """
        Sadece iksir degerini okur.

        Args:
            screenshot_path (str): Ekran goruntusu yolu.

        Returns:
            int: Iksir miktari.
        """
        return self.read_number(screenshot_path, config.get_ocr_region("elixir"))

    def read_dark(self, screenshot_path: str) -> int:
        """
        Sadece kara iksir degerini okur.

        Args:
            screenshot_path (str): Ekran goruntusu yolu.

        Returns:
            int: Kara iksir miktari.
        """
        return self.read_number(screenshot_path, config.get_ocr_region("dark"))

    # -------------------------------------------------------------------------
    # KALIBRASYON
    # -------------------------------------------------------------------------
    def calibrate_regions(self, screenshot_path: str) -> Dict[str, Dict[str, int]]:
        """
        OCR bolgelerini interaktif OpenCV penceresi ile ayarlatir.

        Kontroller:
            1 / 2 / 3 / 4 : gold / elixir / dark / total bolgesini sec
            Trackbar'lar   : X, Y, Genislik, Yukseklik ayari
            S              : secili bolgeyi kaydet ve JSON'a yaz
            A              : tum bolgeleri ekrana ciz
            Q veya ESC     : cikis

        Args:
            screenshot_path (str): Kalibrasyon icin kullanilacak ekran goruntusu.

        Returns:
            Dict[str, Dict[str, int]]: Guncellenmis bolge sozlugu.
        """
        regions: Dict[str, Dict[str, int]] = {
            key: dict(value) for key, value in config.OCR_REGIONS.items()
        }
        if not CV2_AVAILABLE:
            print("[!] OpenCV yuklu degil, kalibrasyon penceresi acilamaz.")
            return regions

        try:
            base = cv2.imread(screenshot_path)
            if base is None:
                print(f"[!] Goruntu okunamadi: {screenshot_path}")
                return regions

            window = "OCR Kalibrasyon - bolge sec: 1=g 2=e 3=d 4=t | s=kaydet | a=ciz | q=cikis"
            cv2.namedWindow(window, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window, 1000, 620)

            keys: List[str] = ["gold", "elixir", "dark"]
            current = {"name": keys[0]}
            initial = regions.get("gold", {"x": 0, "y": 0, "w": 200, "h": 44})

            for label, value in (
                ("X", int(initial.get("x", 0))),
                ("Y", int(initial.get("y", 0))),
                ("W", int(initial.get("w", 200))),
                ("H", int(initial.get("h", 44))),
            ):
                cv2.createTrackbar(label, window, value, 2000, lambda value: None)

            def load_region_params(name: str) -> None:
                """Secili bolgenin degerlerini trackbar'lara yukler."""
                data = regions.get(name, {"x": 0, "y": 0, "w": 200, "h": 44})
                cv2.setTrackbarPos("X", window, int(data.get("x", 0)))
                cv2.setTrackbarPos("Y", window, int(data.get("y", 0)))
                cv2.setTrackbarPos("W", window, max(1, int(data.get("w", 200))))
                cv2.setTrackbarPos("H", window, max(1, int(data.get("h", 44))))

            print("[OCR] Kalibrasyon penceresi acildi. Kontroller:")
            print("      1=gold 2=elixir 3=dark | trackbar ile ayarla")
            print("      s=secili bolgeyi kaydet | a=tum bolgeleri ciz | q=cikis")

            while True:
                frame = base.copy()
                x = cv2.getTrackbarPos("X", window)
                y = cv2.getTrackbarPos("Y", window)
                w = max(1, cv2.getTrackbarPos("W", window))
                h = max(1, cv2.getTrackbarPos("H", window))
                name = current["name"]
                regions[name] = {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}

                for index, key in enumerate(keys):
                    item = regions[key]
                    color = (0, 0, 255) if key == name else (0, 200, 255)
                    cv2.rectangle(
                        frame,
                        (int(item["x"]), int(item["y"])),
                        (int(item["x"] + item["w"]), int(item["y"] + item["h"])),
                        color,
                        2,
                    )
                    cv2.putText(
                        frame,
                        f"{index + 1}:{key}",
                        (int(item["x"]), max(16, int(item["y"]) - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        color,
                        2,
                    )
                cv2.putText(
                    frame,
                    f"Secili: {name}  X={x} Y={y} W={w} H={h}",
                    (20, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )
                cv2.imshow(window, frame)

                pressed = cv2.waitKey(35) & 0xFF
                if pressed in (ord("q"), 27):
                    break
                if pressed == ord("1"):
                    current["name"] = "gold"
                    load_region_params("gold")
                elif pressed == ord("2"):
                    current["name"] = "elixir"
                    load_region_params("elixir")
                elif pressed == ord("3"):
                    current["name"] = "dark"
                    load_region_params("dark")
                elif pressed == ord("a"):
                    print("[OCR] Guncel bolgeler:")
                    for key in keys:
                        print(f"      {key}: {regions[key]}")
                elif pressed == ord("s"):
                    self._save_calibration(regions)
                    print(f"[OK]  '{name}' bolgesi kaydedildi: {regions[name]}")

            cv2.destroyAllWindows()
        except Exception as error:
            print(f"[!] Kalibrasyon hatasi: {error}")
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass
        return regions

    def _save_calibration(self, regions: Dict[str, Dict[str, int]]) -> Optional[str]:
        """
        Kalibrasyon sonuclarini JSON dosyasina ve konsola yazar.

        Args:
            regions (Dict[str, Dict[str, int]]): Kaydedilecek bolgeler.

        Returns:
            Optional[str]: JSON dosya yolu veya None.
        """
        try:
            target = Path(config.DATA_DIR) / "ocr_regions_calibrated.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as handle:
                json.dump(regions, handle, indent=4, ensure_ascii=False)

            print("\n" + "=" * 70)
            print(" config.py icindeki OCR_REGIONS blogunu su sekilde guncelleyin:")
            print("=" * 70)
            print("OCR_REGIONS: Dict[str, Dict[str, int]] = {")
            for key, value in regions.items():
                print(
                    f'    "{key}": {{"x": {value["x"]}, "y": {value["y"]}, '
                    f'"w": {value["w"]}, "h": {value["h"]}}},'
                )
            print("}")
            print("=" * 70)
            print(f"[OK]  Kalibrasyon dosyasi kaydedildi -> {target}")
            return str(target)
        except Exception as error:
            print(f"[!] Kalibrasyon kaydetme hatasi: {error}")
            return None

    # -------------------------------------------------------------------------
    # TEST
    # -------------------------------------------------------------------------
    def test_ocr(self, screenshot_path: str) -> Dict[str, Any]:
        """
        Tum OCR bolgelerini test eder ve sonuclari konsola basar.

        Args:
            screenshot_path (str): Test edilecek ekran goruntusu.

        Returns:
            Dict[str, Any]: {"gold", "elixir", "dark", "total", "regions", "success"}
        """
        report: Dict[str, Any] = {
            "gold": 0,
            "elixir": 0,
            "dark": 0,
            "total": 0,
            "regions": {},
            "success": False,
        }
        try:
            if not self.available:
                print("[!] Tesseract hazir degil, test yapilamaz.")
                return report

            print("=" * 70)
            print(" OCR TEST SONUCLARI")
            print("=" * 70)
            for key, region in config.OCR_REGIONS.items():
                value = self.read_number(screenshot_path, region)
                report["regions"][key] = value
                durum = "OK" if value > 0 else "OKUNAMADI"
                print(f" [{durum:>9}] {key:<11} = {value:>12,}   bolge={region}")

            loot = self.read_loot(screenshot_path)
            report["gold"] = loot["gold"]
            report["elixir"] = loot["elixir"]
            report["dark"] = loot["dark"]
            report["total"] = loot["total"]
            report["success"] = loot["total"] > 0
            print("-" * 70)
            print(f" TOPLAM DEGER: {loot['total']:,}")
            print(f" Filtre esigi: {config.MIN_TOTAL_LOOT:,}")
            karar = "SALDIR" if loot["total"] >= config.MIN_TOTAL_LOOT else "ATLA"
            print(f" Karar       : {karar}")
            print("=" * 70)
            return report
        except Exception as error:
            print(f"[!] OCR test hatasi: {error}")
            return report

    def get_stats(self) -> Dict[str, int]:
        """
        OCR istatistiklerini dondurur.

        Returns:
            Dict[str, int]: {"read", "ok", "fail"}
        """
        return dict(self.stats)


if __name__ == "__main__":  # pragma: no cover - elle test
    engine = OCREngine()
    print(f"Tesseract hazir mi : {engine.available}")
    print("Kullanim: python main.py -> [3] OCR kalibre et")
    time.sleep(0.1)
