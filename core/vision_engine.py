"""
================================================================================
 core/vision_engine.py - OpenCV Goruntu Isleme Motoru
================================================================================
 Template matching (sablon eslestirme) ile ekrandaki butonlari/ikonlari bulur.
 13 farkli olcekte (0.7 - 1.3) arama yapar, basarili olan olcegi onbellege alir
ve sonraki aramalarda once onu dener (buyuk hiz kazanci).

 Yetenekler:
   - find_template()      : tek template ara (cok olcekli + onbellek)
   - wait_for_template()  : ekranda gorunene kadar bekle
   - detect_color_region(): HSV renk araligina gore bolge bul (loot kutulari vb.)
   - draw_debug()         : bulunan bolgeyi kirmizi dikdortgenle isaretle/kaydet

 Donen sozluk formati:
   {"found": bool, "x": int, "y": int, "confidence": float, ...}
================================================================================
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import config

try:
    import cv2
    import numpy as np

    CV2_AVAILABLE = True
except ImportError:  # pragma: no cover - bagimlilik eksikse
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    CV2_AVAILABLE = False


# Bulunamayan sonuclar icin ortak sablon
NOT_FOUND: Dict[str, Any] = {"found": False, "x": 0, "y": 0, "confidence": 0.0}


class VisionEngine:
    """OpenCV tabanli sablon eslestirme motoru."""

    def __init__(
        self,
        threshold: Optional[float] = None,
        use_multi_scale: Optional[bool] = None,
        debug: Optional[bool] = None,
    ) -> None:
        """
        VisionEngine nesnesini olusturur.

        Args:
            threshold (Optional[float]): Eslesme esigi. None ise config.TEMPLATE_THRESHOLD.
            use_multi_scale (Optional[bool]): Cok olcekli arama acik mi.
            debug (Optional[bool]): True ise tespit goruntuleri kaydedilir.

        Returns:
            None
        """
        self.threshold: float = threshold if threshold is not None else config.TEMPLATE_THRESHOLD
        self.use_multi_scale: bool = (
            config.MULTI_SCALE_ENABLED if use_multi_scale is None else use_multi_scale
        )
        self.debug: bool = config.DEBUG_DRAW_ENABLED if debug is None else debug
        self.scale_min: float = config.SCALE_MIN
        self.scale_max: float = config.SCALE_MAX
        self.scale_steps: int = max(1, config.SCALE_STEPS)

        # Basarili olan olcekleri template adi bazinda hatirla (onbellek)
        self._scale_cache: Dict[str, float] = {}
        # Istatistik
        self.stats: Dict[str, int] = {"search": 0, "found": 0, "cache_hit": 0}

        if not CV2_AVAILABLE:
            print("[!] OpenCV (cv2) veya numpy yuklu degil! VisionEngine sinirli calisir.")
        print(
            f"[VISION] Motor hazir -> esik={self.threshold}, "
            f"cok_olcek={self.use_multi_scale}, adim={self.scale_steps}"
        )

    # -------------------------------------------------------------------------
    # YARDIMCI: OLCEK LISTESI
    # -------------------------------------------------------------------------
    def _scale_list(self) -> List[float]:
        """
        Denenecek olcek degerlerini uretir (0.7 ile 1.3 arasi, 13 adim).

        Returns:
            List[float]: Olcek listesi.
        """
        try:
            if self.scale_steps == 1:
                return [1.0]
            return [
                round(float(value), 3)
                for value in np.linspace(self.scale_min, self.scale_max, self.scale_steps)
            ]
        except Exception as error:
            print(f"[!] Olcek listesi olusturulamadi: {error}")
            return [1.0]

    def _ordered_scales(self, template_key: str) -> List[float]:
        """
        Olcekleri, onbellekteki basarili olcek one gelecek sekilde siralar.

        Args:
            template_key (str): Template dosya adi (onbellek anahtari).

        Returns:
            List[float]: Sirali olcek listesi.
        """
        try:
            scales = self._scale_list()
            cached = self._scale_cache.get(template_key)
            if cached is None:
                return scales
            self.stats["cache_hit"] += 1
            ordered = [cached] + [item for item in scales if abs(item - cached) > 1e-6]
            return ordered
        except Exception as error:
            print(f"[!] Olcek siralama hatasi: {error}")
            return [1.0]

    @staticmethod
    def _template_key(template_path: str) -> str:
        """
        Template yolu icin kisa ve benzersiz bir onbellek anahtari uretir.

        Args:
            template_path (str): Template dosya yolu.

        Returns:
            str: Anahtar (genelde dosya adi).
        """
        try:
            return Path(template_path).name
        except Exception:
            return str(template_path)

    # -------------------------------------------------------------------------
    # TEMPLATE ARAMA
    # -------------------------------------------------------------------------
    def find_template(
        self,
        screenshot_path: str,
        template_path: str,
        region: Optional[Dict[str, int]] = None,
        multi_scale: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Bir template'i ekran goruntusunde arar.

        Args:
            screenshot_path (str): Ekran goruntusu dosya yolu.
            template_path (str): Aranacak template (PNG) dosya yolu.
            region (Optional[Dict[str, int]]): Sadece bu bolgede ara {"x","y","w","h"}.
            multi_scale (Optional[bool]): True ise 13 farkli olcekte dener.

        Returns:
            Dict[str, Any]: {"found", "x", "y", "confidence", "scale", "template"}
                            Bulunamazsa veya hata olursa found=False.
        """
        result: Dict[str, Any] = dict(NOT_FOUND)
        result["scale"] = 1.0
        result["template"] = self._template_key(template_path)

        try:
            if not CV2_AVAILABLE:
                print("[!] OpenCV yuklu degil, template aramasi yapilamaz.")
                return result

            screen_file = Path(screenshot_path)
            template_file = Path(template_path)
            if not screen_file.exists():
                print(f"[!] Ekran goruntusu bulunamadi: {screenshot_path}")
                return result
            if not template_file.exists():
                print(f"[!] Template dosyasi bulunamadi: {template_path}")
                return result

            screen = cv2.imread(str(screen_file))
            template = cv2.imread(str(template_file))
            if screen is None or template is None:
                print("[!] Goruntu okunamadi (bozuk dosya olabilir).")
                return result

            offset_x, offset_y = 0, 0
            if region:
                cropped = self._crop(screen, region)
                if cropped is None:
                    print(f"[!] Arama bolgesi gecersiz: {region}")
                    return result
                screen = cropped
                offset_x = int(region.get("x", 0))
                offset_y = int(region.get("y", 0))

            scaled_list = self._ordered_scales(result["template"])
            use_scales = scaled_list if (
                self.use_multi_scale if multi_scale is None else multi_scale
            ) else [1.0]

            best: Dict[str, Any] = dict(NOT_FOUND)
            self.stats["search"] += 1

            for scale in use_scales:
                match = self._match_single_scale(screen, template, float(scale))
                if match["confidence"] > best["confidence"]:
                    best = match
                    best["scale"] = float(scale)
                if best["confidence"] >= self.threshold:
                    break  # yeterince iyi eslesme bulundu, erken cik

            if best["confidence"] >= self.threshold:
                result = {
                    "found": True,
                    "x": int(best["x"] + offset_x),
                    "y": int(best["y"] + offset_y),
                    "width": int(best.get("width", 0)),
                    "height": int(best.get("height", 0)),
                    "confidence": round(float(best["confidence"]), 4),
                    "scale": float(best.get("scale", 1.0)),
                    "template": result["template"],
                }
                self._scale_cache[result["template"]] = float(best.get("scale", 1.0))
                self.stats["found"] += 1
                print(
                    f"[VISION] BULUNDU -> {result['template']} "
                    f"({result['x']},{result['y']}) guven={result['confidence']} "
                    f"olcek={result['scale']}"
                )
            else:
                result["confidence"] = round(float(best["confidence"]), 4)
                result["scale"] = float(best.get("scale", 1.0))
                print(
                    f"[VISION] Bulunamadi -> {result['template']} "
                    f"(en iyi guven={result['confidence']} < {self.threshold})"
                )
            return result
        except Exception as error:
            print(f"[!] Template arama hatasi ({template_path}): {error}")
            return result

    def _match_single_scale(
        self,
        screen: "np.ndarray",
        template: "np.ndarray",
        scale: float,
    ) -> Dict[str, Any]:
        """
        Tek bir olcekte sablon eslestirme yapar (ic kullanim).

        Args:
            screen (np.ndarray): Aranacak goruntu.
            template (np.ndarray): Sablon goruntu.
            scale (float): Sablonun olcek katsayisi.

        Returns:
            Dict[str, Any]: {"confidence", "x", "y", "width", "height"}
        """
        best: Dict[str, Any] = {"confidence": 0.0, "x": 0, "y": 0, "width": 0, "height": 0}
        try:
            scaled = template
            if abs(scale - 1.0) > 1e-6:
                new_w = max(1, int(template.shape[1] * scale))
                new_h = max(1, int(template.shape[0] * scale))
                interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
                scaled = cv2.resize(template, (new_w, new_h), interpolation=interpolation)

            screen_h, screen_w = screen.shape[:2]
            temp_h, temp_w = scaled.shape[:2]
            if temp_h > screen_h or temp_w > screen_w:
                return best  # sablon ekrandan buyuk, bu olcekte atla

            outcome = cv2.matchTemplate(screen, scaled, cv2.TM_CCOEFF_NORMED)
            _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(outcome)
            best = {
                "confidence": float(max_val),
                "x": int(max_loc[0]),
                "y": int(max_loc[1]),
                "width": int(temp_w),
                "height": int(temp_h),
            }
        except Exception as error:
            print(f"[!] Olcekli eslestirme hatasi (scale={scale}): {error}")
        return best

    @staticmethod
    def _crop(image: "np.ndarray", region: Dict[str, int]) -> Optional["np.ndarray"]:
        """
        Goruntuden bolge kirpar (sinir kontrollu).

        Args:
            image (np.ndarray): Kaynak goruntu.
            region (Dict[str, int]): {"x", "y", "w", "h"}

        Returns:
            Optional[np.ndarray]: Kirpilmis goruntu veya None.
        """
        try:
            height, width = image.shape[:2]
            x = max(0, int(region.get("x", 0)))
            y = max(0, int(region.get("y", 0)))
            w = max(1, int(region.get("w", 1)))
            h = max(1, int(region.get("h", 1)))
            x2 = min(width, x + w)
            y2 = min(height, y + h)
            if x >= width or y >= height or x2 <= x or y2 <= y:
                return None
            return image[y:y2, x:x2]
        except Exception as error:
            print(f"[!] Kirpma hatasi: {error}")
            return None

    # -------------------------------------------------------------------------
    # BEKLEME
    # -------------------------------------------------------------------------
    def wait_for_template(
        self,
        adb: "object",
        template_path: str,
        timeout: Optional[int] = None,
        interval: Optional[float] = None,
        region: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """
        Template ekranda gorunene kadar belirli araliklarla kontrol eder.

        Args:
            adb (object): ADBController benzeri nesne (ekran goruntusu icin).
            template_path (str): Aranacak template dosyasi.
            timeout (Optional[int]): Maksimum bekleme suresi (saniye).
            interval (Optional[float]): Kontroller arasi bekleme (saniye).
            region (Optional[Dict[str, int]]): Sadece bu bolgede ara.

        Returns:
            Dict[str, Any]: Bulunca {"found": True, "x", "y", "confidence", "attempts"}
                            Bulunamazsa {"found": False, "x": 0, "y": 0, ...}
        """
        result: Dict[str, Any] = dict(NOT_FOUND)
        result["attempts"] = 0
        total_timeout = timeout if timeout is not None else config.TEMPLATE_WAIT_TIMEOUT
        wait_interval = interval if interval is not None else config.TEMPLATE_WAIT_INTERVAL
        temp_dir = Path(config.SCREENSHOT_DIR) / "wait"
        start = time.time()

        try:
            temp_dir.mkdir(parents=True, exist_ok=True)
            print(f"[VISION] Bekleniyor -> {Path(template_path).name} (maks {total_timeout} sn)")
            while (time.time() - start) < total_timeout:
                result["attempts"] = int(result.get("attempts", 0)) + 1
                screen_path = temp_dir / f"wait_{result['attempts']:04d}.png"
                saved = adb.screenshot(str(screen_path))
                if saved:
                    found = self.find_template(saved, template_path, region=region)
                    if found.get("found"):
                        found["attempts"] = result["attempts"]
                        found["elapsed"] = round(time.time() - start, 2)
                        print(
                            f"[VISION] Bekleme basarili ({found['elapsed']} sn, "
                            f"{found['attempts']} deneme)"
                        )
                        return found
                time.sleep(wait_interval)

            print(f"[VISION] Zaman asimi! {Path(template_path).name} bulunamadi.")
            return result
        except Exception as error:
            print(f"[!] Template bekleme hatasi: {error}")
            return result

    # -------------------------------------------------------------------------
    # RENK TESPITI
    # -------------------------------------------------------------------------
    def detect_color_region(
        self,
        screenshot_path: str,
        lower_hsv: Sequence[int],
        upper_hsv: Sequence[int],
        min_area: int = 150,
        max_regions: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        HSV renk araligina giren bolgeleri bulur.

        Args:
            screenshot_path (str): Ekran goruntusu yolu.
            lower_hsv (Sequence[int]): Alt HSV siniri (orn. [0, 120, 120]).
            upper_hsv (Sequence[int]): Ust HSV siniri (orn. [10, 255, 255]).
            min_area (int): Kabul edilecek minimum piksel alani.
            max_regions (int): Dondurulecek maksimum bolge sayisi.

        Returns:
            List[Dict[str, Any]]: Her biri {"x","y","w","h","area","center","mean_hsv"}
                                  Bulunamazsa bos liste.
        """
        regions: List[Dict[str, Any]] = []
        try:
            if not CV2_AVAILABLE:
                print("[!] OpenCV yuklu degil, renk tespiti yapilamaz.")
                return regions
            if not Path(screenshot_path).exists():
                print(f"[!] Goruntu bulunamadi: {screenshot_path}")
                return regions

            image = cv2.imread(screenshot_path)
            if image is None:
                print("[!] Goruntu okunamadi.")
                return regions

            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            lower = np.array(lower_hsv, dtype=np.uint8)
            upper = np.array(upper_hsv, dtype=np.uint8)
            mask = cv2.inRange(hsv, lower, upper)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

            contours, _hierarchy = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            for contour in contours:
                area = int(cv2.contourArea(contour))
                if area < min_area:
                    continue
                x, y, w, h = cv2.boundingRect(contour)
                regions.append(
                    {
                        "x": int(x),
                        "y": int(y),
                        "w": int(w),
                        "h": int(h),
                        "area": area,
                        "center": (int(x + w / 2), int(y + h / 2)),
                    }
                )

            regions.sort(key=lambda item: item["area"], reverse=True)
            regions = regions[:max_regions]
            print(f"[VISION] Renk tespiti -> {len(regions)} bolge bulundu.")
            return regions
        except Exception as error:
            print(f"[!] Renk tespiti hatasi: {error}")
            return regions

    # -------------------------------------------------------------------------
    # DEBUG GORSELLESTIRME
    # -------------------------------------------------------------------------
    def draw_debug(
        self,
        screenshot_path: str,
        result: Dict[str, Any],
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Tespit edilen bolgeyi kirmizi dikdortgen ile isaretleyip kaydeder.

        Args:
            screenshot_path (str): Kaynak ekran goruntusu.
            result (Dict[str, Any]): find_template sonucu (x, y, width, height).
            output_path (Optional[str]): Cikti yolu. None ise otomatik isim verilir.

        Returns:
            Optional[str]: Kaydedilen debug goruntusunun yolu veya None.
        """
        try:
            if not CV2_AVAILABLE:
                print("[!] OpenCV yuklu degil, debug gorseli cizilemez.")
                return None
            if not Path(screenshot_path).exists():
                print(f"[!] Goruntu bulunamadi: {screenshot_path}")
                return None

            image = cv2.imread(screenshot_path)
            if image is None:
                print("[!] Goruntu okunamadi.")
                return None

            found = bool(result.get("found"))
            color = (0, 0, 255) if found else (0, 165, 255)
            label = (
                f"{result.get('template', 'template')} "
                f"{float(result.get('confidence', 0.0)):.2f}"
            )

            if found:
                x = int(result.get("x", 0))
                y = int(result.get("y", 0))
                w = int(result.get("width", 0)) or 80
                h = int(result.get("height", 0)) or 40
                cv2.rectangle(image, (x, y), (x + w, y + h), color, 3)
                cv2.circle(image, (x + w // 2, y + h // 2), 6, (0, 255, 0), -1)
                text_y = max(20, y - 10)
            else:
                cv2.putText(
                    image,
                    "BULUNAMADI",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    color,
                    2,
                )
                text_y = 80

            cv2.putText(
                image,
                label,
                (20, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
            )

            if not output_path:
                stem = Path(screenshot_path).stem
                target = Path(config.DEBUG_DIR) / f"debug_{stem}.png"
            else:
                target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(target), image)
            print(f"[VISION] Debug gorseli kaydedildi -> {target}")
            return str(target)
        except Exception as error:
            print(f"[!] Debug cizim hatasi: {error}")
            return None

    def draw_color_debug(
        self,
        screenshot_path: str,
        regions: List[Dict[str, Any]],
        output_path: Optional[str] = None,
        color: Tuple[int, int, int] = (255, 0, 0),
    ) -> Optional[str]:
        """
        Renk tespitinde bulunan tum bolgeleri cizip kaydeder.

        Args:
            screenshot_path (str): Kaynak goruntu.
            regions (List[Dict[str, Any]]): detect_color_region ciktisi.
            output_path (Optional[str]): Cikti yolu.
            color (Tuple[int, int, int]): BGR cizim rengi.

        Returns:
            Optional[str]: Kaydedilen dosya yolu veya None.
        """
        try:
            if not CV2_AVAILABLE:
                return None
            image = cv2.imread(screenshot_path)
            if image is None:
                print("[!] Goruntu okunamadi.")
                return None
            for item in regions:
                x = int(item.get("x", 0))
                y = int(item.get("y", 0))
                w = int(item.get("w", 0))
                h = int(item.get("h", 0))
                cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
            target = Path(output_path) if output_path else (
                Path(config.DEBUG_DIR) / f"renk_{Path(screenshot_path).stem}.png"
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(target), image)
            print(f"[VISION] Renk debug gorseli -> {target}")
            return str(target)
        except Exception as error:
            print(f"[!] Renk debug hatasi: {error}")
            return None

    # -------------------------------------------------------------------------
    # YARDIMCILAR
    # -------------------------------------------------------------------------
    def clear_cache(self) -> None:
        """
        Olcek onbellegini temizler.

        Returns:
            None
        """
        self._scale_cache.clear()
        print("[VISION] Olcek onbellegi temizlendi.")

    def get_cache(self) -> Dict[str, float]:
        """
        Mevcut olcek onbellegini dondurur.

        Returns:
            Dict[str, float]: {template_adi: olcek}
        """
        return dict(self._scale_cache)

    def get_stats(self) -> Dict[str, int]:
        """
        Vision istatistiklerini dondurur.

        Returns:
            Dict[str, int]: {"search", "found", "cache_hit"}
        """
        return dict(self.stats)


if __name__ == "__main__":  # pragma: no cover - elle test
    engine = VisionEngine()
    print(f"Olcek listesi: {engine._scale_list()}")
    print(f"Onbellek     : {engine.get_cache()}")
