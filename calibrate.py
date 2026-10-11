"""
================================================================================
 calibrate.py - OCR / Vision Kalibrasyon Araci
================================================================================
 Botu kurduktan sonra ekrani botun anlayacagi sekilde ayarlamak icin kullanilan
 interaktif arac.

 Menu:
   [1] OCR bolgelerini kalibre et   -> OpenCV penceresinde trackbar ile
   [2] Template matching test et    -> bir template sec, ekranda ara
   [3] Ekran boyutunu goster        -> ADB wm size ciktisi
   [4] ADB baglantisini test et     -> bagli cihazlar + baglanti denemesi
   [5] Tum template'leri test et    -> assets/templates/ klasorundekileri dene
   [6] Cikis

 Kullanim:
   python calibrate.py
   python calibrate.py --no-adb     -> ADB olmadan mevcut goruntuyu kullan
================================================================================
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Optional

# Proje kokunu yola ekle
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config  # noqa: E402


# ==============================================================================
# YARDIMCILAR
# ==============================================================================
def ask(prompt: str, default: str = "") -> str:
    """
    Kullanicidan guvenli sekilde girdi alir.

    Args:
        prompt (str): Soru metni.
        default (str): Bos girdide kullanilacak deger.

    Returns:
        str: Kullanici girdisi.
    """
    try:
        value = input(prompt).strip()
        return value if value else default
    except (EOFError, KeyboardInterrupt):
        print("\n[!] Girdi alinamadi.")
        return default
    except Exception as error:
        print(f"[!] Girdi hatasi: {error}")
        return default


def print_header(title: str) -> None:
    """
    Baslik yazdirir.

    Args:
        title (str): Baslik metni.

    Returns:
        None
    """
    print("\n" + "=" * 78)
    print(f" {title}")
    print("=" * 78)


def take_screenshot(adb: Any = None, name: str = "kalibrasyon") -> Optional[str]:
    """
    Ekran goruntusu alir (ADB varsa cihazdan, yoksa kullanicidan dosya ister).

    Args:
        adb (Any): ADBController nesnesi veya None.
        name (str): Dosya adi oneki.

    Returns:
        Optional[str]: Goruntu dosyasinin yolu veya None.
    """
    try:
        if adb is not None:
            from core.screen_capture import ScreenCapture

            capture = ScreenCapture(adb=adb)
            path = capture.capture(name=name)
            if path:
                print(f"[CALIBRATE] Ekran goruntusu alindi -> {path}")
                return path
            print("[!] Ekran goruntusu alinamadi, mevcut dosya sorulacak.")

        manual = ask(" Ekran goruntusu dosya yolu (bos birak = iptal): ")
        if manual and Path(manual).exists():
            return manual
        if manual:
            print(f"[!] Dosya bulunamadi: {manual}")
        return None
    except Exception as error:
        print(f"[!] Ekran goruntusu hatasi: {error}")
        return None


def build_adb(auto_connect: bool = True) -> Any:
    """
    ADBController nesnesi olusturur; basarisiz olursa None dondurur.

    Args:
        auto_connect (bool): Otomatik baglanma denesin mi.

    Returns:
        Any: ADBController nesnesi veya None.
    """
    try:
        from core.adb_controller import ADBController

        adb = ADBController(auto_connect=auto_connect)
        if not adb.is_connected():
            print("[!] Cihaz bagli degil. LDPlayer'in acik oldugundan emin olun.")
            return None
        return adb
    except Exception as error:
        print(f"[!] ADB olusturma hatasi: {error}")
        return None


# ==============================================================================
# [1] OCR BOLGE KALIBRASYONU
# ==============================================================================
def option_calibrate_ocr(adb: Any) -> None:
    """
    OCR bolgelerini interaktif olarak kalibre eder.

    Args:
        adb (Any): ADBController nesnesi veya None.

    Returns:
        None
    """
    try:
        print_header("[1] OCR BOLGE KALIBRASYONU")
        screenshot = take_screenshot(adb, "ocr_kalibrasyon")
        if not screenshot:
            print("[!] Goruntu olmadan kalibrasyon yapilamaz.")
            return
        from core.ocr_engine import OCREngine

        ocr = OCREngine()
        regions = ocr.calibrate_regions(screenshot)
        print(f"[CALIBRATE] Guncel bolgeler: {regions}")
    except Exception as error:
        print(f"[!] OCR kalibrasyon hatasi: {error}")


# ==============================================================================
# [2] TEMPLATE MATCHING TESTI
# ==============================================================================
def option_test_template(adb: Any) -> None:
    """
    Secilen tek bir template'i ekranda arar ve sonucu gosterir.

    Args:
        adb (Any): ADBController nesnesi veya None.

    Returns:
        None
    """
    try:
        print_header("[2] TEMPLATE MATCHING TESTI")
        full_screenshot = take_screenshot(adb, "template_test")
        if not full_screenshot:
            print("[!] Goruntu olmadan test yapilamaz.")
            return

        templates = sorted(Path(config.TEMPLATES_DIR).glob("*.png"))
        if not templates:
            print(f"[!] Hic template yok: {config.TEMPLATES_DIR}")
            print("    assets/templates/README.md dosyasindaki rehberi izleyin.")
            return

        print(" Mevcut template'ler:")
        for index, item in enumerate(templates, start=1):
            print(f"   [{index}] {item.name}")

        choice = ask(f" Template secin [1-{len(templates)}] (varsayilan 1): ", "1")
        try:
            selected = templates[max(0, min(len(templates) - 1, int(choice) - 1))]
        except Exception:
            print("[!] Gecersiz secim, ilk template kullaniliyor.")
            selected = templates[0]

        from core.vision_engine import VisionEngine

        vision = VisionEngine()
        print(f"[CALIBRATE] '{selected.name}' araniyor...")
        result = vision.find_template(full_screenshot, str(selected))
        print("-" * 78)
        print(f" Bulundu mu : {result.get('found')}")
        print(f" Konum      : x={result.get('x')}, y={result.get('y')}")
        print(f" Guven      : {result.get('confidence')} (esik: {vision.threshold})")
        print(f" Olcek      : {result.get('scale')}")
        print("-" * 78)

        # Debug gorseli ciz
        debug_path = Path(config.DEBUG_DIR) / f"kalibrasyon_{selected.stem}.png"
        vision.draw_debug(full_screenshot, result, str(debug_path))

        # OpenCV penceresinde goster (varsa)
        try:
            import cv2

            image = cv2.imread(str(debug_path))
            if image is not None:
                window = f"Template Testi - {selected.name} (kapatmak icin bir tusa basin)"
                cv2.namedWindow(window, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(window, 1000, 620)
                cv2.imshow(window, image)
                print("[CALIBRATE] Pencere acildi. Kapatmak icin bir tusa basin.")
                cv2.waitKey(0)
                cv2.destroyAllWindows()
        except Exception as error:
            print(f"[!] Onizleme penceresi acilamadi: {error}")
    except Exception as error:
        print(f"[!] Template test hatasi: {error}")


# ==============================================================================
# [3] EKRAN BOYUTU
# ==============================================================================
def option_screen_size(adb: Any) -> None:
    """
    Ekran boyutunu ve OCR bolgelerinin bu boyuta gore olceklenmis halini gosterir.

    Args:
        adb (Any): ADBController nesnesi veya None.

    Returns:
        None
    """
    try:
        print_header("[3] EKRAN BOYUTU")
        if adb is None:
            print("[!] ADB baglantisi yok, config varsayilani gosteriliyor.")
            width, height = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
        else:
            width, height = adb.get_screen_size(refresh=True)

        print(f" Gercek ekran boyutu : {width} x {height}")
        print(f" Config varsayilani  : {config.SCREEN_WIDTH} x {config.SCREEN_HEIGHT}")
        if (width, height) != (config.SCREEN_WIDTH, config.SCREEN_HEIGHT):
            print("\n[!] Dikkat: Cozunurluk farkli! Bolgeler otomatik olceklenecek")
            print("    ancak en dogru sonuc icin config.py degerlerini guncelleyin.")
        print("\n Bu cozunurlukte kullanilacak bolgeler:")
        for key, region in config.OCR_REGIONS.items():
            scaled = config.scale_region(region, width, height)
            print(
                f"   {key:<10} x={scaled['x']:<5} y={scaled['y']:<5} "
                f"w={scaled['w']:<5} h={scaled['h']:<5}"
            )
    except Exception as error:
        print(f"[!] Ekran boyutu hatasi: {error}")


# ==============================================================================
# [4] ADB TESTI
# ==============================================================================
def option_test_adb(adb: Any) -> None:
    """
    ADB baglantisini test eder, gerekirse yeniden baglanmayi dener.

    Args:
        adb (Any): ADBController nesnesi veya None.

    Returns:
        None
    """
    try:
        print_header("[4] ADB BAGLANTI TESTI")
        print(f" adb yolu             : {config.ADB_PATH or 'BULUNAMADI'}")
        print(f" Hedef serial         : {config.ADB_SERIAL}")
        print(f" Baglanti adresi      : {config.ADB_CONNECT_ADDRESS}")

        if adb is None:
            adb = build_adb(auto_connect=False)
            if adb is None:
                print("[!] ADBController olusturulamadi.")
                return

        devices = adb.list_devices()
        print(f" Bagli cihazlar       : {devices if devices else '(yok)'}")

        if config.ADB_SERIAL in devices:
            print(f"[OK]  Hedef cihaz bagli -> {config.ADB_SERIAL}")
        else:
            print(f"[!] {config.ADB_SERIAL} bagli cihazlar arasinda yok.")
            baglan = ask(f" {config.ADB_CONNECT_ADDRESS} adresine baglanilsin mi? (e/h): ", "e")
            if baglan.lower() in ("e", "evet", "y", "yes"):
                adb.connect()

        if adb.is_connected():
            width, height = adb.get_screen_size(refresh=True)
            print(f"[OK]  Baglanti saglikli. Ekran: {width}x{height}")
            test_path = Path(config.DEBUG_DIR) / "adb_test.png"
            saved = adb.screenshot(str(test_path))
            if saved:
                print(f"[OK]  Test ekran goruntusu -> {saved}")
            else:
                print("[!] Ekran goruntusu alinamadi!")
        else:
            print("[!] ADB baglantisi kurulamadi.")
            print("     Kontrol listesi:")
            print("       1. LDPlayer acik mi?")
            print("       2. LDPlayer ayarlarindan ADB Debug acik mi?")
            print(f"       3. 'adb connect {config.ADB_CONNECT_ADDRESS}' komutunu deneyin")
            print("       4. scripts/setup_adb.ps1 ile tekrar kurulum yapin")
    except Exception as error:
        print(f"[!] ADB test hatasi: {error}")


# ==============================================================================
# [5] TUM TEMPLATE'LERI TEST ET
# ==============================================================================
def option_test_all_templates(adb: Any) -> None:
    """
    assets/templates/ klasorundeki tum template'leri tek ekran goruntusunde test eder.

    Args:
        adb (Any): ADBController nesnesi veya None.

    Returns:
        None
    """
    try:
        print_header("[5] TUM TEMPLATE'LERI TEST ET")
        screenshot = take_screenshot(adb, "tum_template_test")
        if not screenshot:
            print("[!] Goruntu olmadan test yapilamaz.")
            return

        templates = sorted(Path(config.TEMPLATES_DIR).glob("*.png"))
        if not templates:
            print(f"[!] Hic template yok: {config.TEMPLATES_DIR}")
            print("    assets/templates/README.md rehberine bakin.")
            return

        from core.vision_engine import VisionEngine

        vision = VisionEngine()
        print(f" {len(templates)} template test edilecek (esik={vision.threshold})...\n")
        print(f" {'TEMPLATE':<28} {'SONUC':<10} {'KONUM':<16} {'GUVEN':>8} {'OLCEK':>7}")
        print("-" * 78)

        bulunan = 0
        for item in templates:
            start = time.time()
            result = vision.find_template(screenshot, str(item))
            sure = time.time() - start
            durum = "BULUNDU" if result.get("found") else "YOK"
            if result.get("found"):
                bulunan += 1
            konum = f"({result.get('x')},{result.get('y')})"
            print(
                f" {item.name:<28} {durum:<10} {konum:<16} "
                f"{float(result.get('confidence', 0.0)):>8.3f} "
                f"{float(result.get('scale', 1.0)):>7.2f}  ({sure:.2f}s)"
            )

        print("-" * 78)
        print(f" Ozet: {bulunan}/{len(templates)} template bulundu.")
        if bulunan < len(templates):
            print("\n Bulunamayan template'ler icin:")
            print("   - Oyun ekraninda ilgili buton gorunuyor mu?")
            print("   - Buton goruntusunu tekrar kesip kaydedin (buton + biraz kenar bosluk)")
            print("   - config.TEMPLATE_THRESHOLD degerini dusurun (orn. 0.75)")
            print("   - Gorseli gri tonlamali (grayscale) kaydetmeyi deneyin")
    except Exception as error:
        print(f"[!] Toplu template test hatasi: {error}")


# ==============================================================================
# MENU
# ==============================================================================
def print_menu() -> None:
    """
    Kalibrasyon menusunu yazdirir.

    Returns:
        None
    """
    print("\n" + "-" * 78)
    print(" KALIBRASYON MENUSU")
    print("-" * 78)
    print("   [1] OCR bolgelerini kalibre et (OpenCV penceresi)")
    print("   [2] Template matching test et (tek template)")
    print("   [3] Ekran boyutunu goster")
    print("   [4] ADB baglantisini test et")
    print("   [5] Tum template'leri test et")
    print("   [6] Cikis")
    print("-" * 78)


def main() -> int:
    """
    Kalibrasyon aracinin ana dongusu.

    Returns:
        int: 0 -> normal cikis.
    """
    adb = None
    try:
        print("=" * 78)
        print(f" {config.APP_NAME} - KALIBRASYON ARACI v{config.APP_VERSION}")
        print("=" * 78)
        print(f" Template klasoru : {config.TEMPLATES_DIR}")
        print(f" Debug klasoru    : {config.DEBUG_DIR}")
        print(f" Egik cozunurluk  : {config.SCREEN_WIDTH}x{config.SCREEN_HEIGHT}")

        if "--no-adb" not in sys.argv:
            print("\n[CALIBRATE] ADB baglantisi deneniyor...")
            adb = build_adb(auto_connect=True)
            if adb is None:
                print("[!] ADB yok: ekran goruntusu dosyadan alinacak.")
        else:
            print("[CALIBRATE] --no-adb: ADB kullanilmayacak.")

        while True:
            print_menu()
            choice = ask(" Seciminiz [1-6]: ", "6")

            if choice == "1":
                option_calibrate_ocr(adb)
            elif choice == "2":
                option_test_template(adb)
            elif choice == "3":
                option_screen_size(adb)
            elif choice == "4":
                option_test_adb(adb)
            elif choice == "5":
                option_test_all_templates(adb)
            elif choice in ("6", "q", "quit", "exit", "cikis"):
                print("\n[CALIBRATE] Cikiliyor. Iyi savaslar!")
                break
            else:
                print("[!] Gecersiz secim! 1-6 arasinda bir deger girin.")
        return 0
    except KeyboardInterrupt:
        print("\n[CALIBRATE] Kullanici tarafindan kapatildi.")
        return 0
    except Exception as error:
        print(f"[!] Kalibrasyon araci hatasi: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
