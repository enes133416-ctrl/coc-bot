"""
================================================================================
 main.py - Clash of Clans Yerel AI Bot | Ana Giris Noktasi
================================================================================
 Botun tum modlarini tek bir interaktif menu uzerinden baslatir:

   [1] Bot'u baslat          -> bot_mode()      (StateMachine.run)
   [2] Savas plani kaydet    -> record_mode()   (AttackPlanner ile kayit)
   [3] OCR kalibre et        -> calibrate_mode()(calibrate.py cagrilir)
   [4] Test calistir         -> test_mode()     (pytest tests/)
   [5] Hatalari AI icin aktar-> export_mode()   (DataLogger + export_summary)
   [6] Cikis

 Kullanim:
   python main.py            -> interaktif menu
   python main.py --bot      -> dogrudan bot modu
   python main.py --test     -> dogrudan test modu
   python main.py --export   -> dogrudan disa aktarma
================================================================================
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import List

# Proje kokunu yola ekle (script farkli klasorden cagrilirsa)
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config  # noqa: E402

try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
    COLOR = True
except ImportError:  # pragma: no cover - colorama eksikse
    COLOR = False

    class _Dummy:  # pragma: no cover - yedek renk sinifi
        """colorama yoksa renk kodlarini bos metne cevirir."""

        def __getattr__(self, _name: str) -> str:
            return ""

    Fore = _Dummy()  # type: ignore[assignment]
    Style = _Dummy()  # type: ignore[assignment]


# ==============================================================================
# GORSEL YARDIMCILAR
# ==============================================================================
ASCII_TITLE: str = r"""
   ______      ______        ______         __
  / ____/___  / ____/       / __ )____     / /_
 / /   / __ \/ /           / __  / __ \   / __/
/ /___/ /_/ / /___        / /_/ / /_/ /  / /_
\____/\____/\____/        \____/\____/   \__/

   Clash of Clans  -  YEREL AI BOT  (API YOK, %100 Cevrimdisi)
   OpenCV + Tesseract + ADB + Ollama/LLaVA
"""


def print_banner() -> None:
    """
    Program basligini (ASCII art) ve sistem durumunu yazdirir.

    Returns:
        None
    """
    try:
        print(Fore.CYAN + ASCII_TITLE)
        print(Fore.YELLOW + "-" * 78)
        print(f" {config.APP_NAME} v{config.APP_VERSION}")
        print(f" Tesseract : {config.TESSERACT_CMD or 'BULUNAMADI (!)'}")
        print(f" ADB       : {config.ADB_PATH or 'BULUNAMADI (!)'}")
        print(f" ADB cihaz : {config.ADB_SERIAL}")
        print(f" Yerel AI  : {'ACIK' if config.USE_LOCAL_AI else 'KAPALI'} "
              f"({config.OLLAMA_URL} / {config.OLLAMA_MODEL})")
        print(f" Loot esigi: {config.MIN_TOTAL_LOOT:,} (altin>={config.MIN_GOLD:,}, "
              f"iksir>={config.MIN_ELIXIR:,})")
        print(f" Aktif plan: {config.ACTIVE_PLAN}")
        print(Fore.YELLOW + "-" * 78)
    except Exception as error:
        print(f"[!] Baslik yazma hatasi: {error}")


def print_menu() -> None:
    """
    Ana menuyu yazdirir.

    Returns:
        None
    """
    try:
        print(Fore.GREEN + "\n ANA MENU")
        print(" " + "-" * 40)
        print("  [1] Bot'u baslat")
        print("  [2] Savas plani kaydet")
        print("  [3] OCR kalibre et / template test et")
        print("  [4] Testleri calistir (pytest)")
        print("  [5] Hatalari AI icin disa aktar")
        print("  [6] Cikis")
        print(" " + "-" * 40)
    except Exception as error:
        print(f"[!] Menu yazma hatasi: {error}")


def ask(prompt: str, default: str = "") -> str:
    """
    Kullanicidan girdi alir; hata durumunda varsayilani dondurur.

    Args:
        prompt (str): Sorulacak metin.
        default (str): Bos girdi halinde dondurulecek deger.

    Returns:
        str: Kullanici girdisi.
    """
    try:
        value = input(prompt).strip()
        return value if value else default
    except (EOFError, KeyboardInterrupt):
        print("\n[!] Girdi alinamadi, varsayilan kullaniliyor.")
        return default
    except Exception as error:
        print(f"[!] Girdi hatasi: {error}")
        return default


# ==============================================================================
# MOD 1: BOT
# ==============================================================================
def bot_mode() -> None:
    """
    Tum bilesenleri baslatir ve durum makinesini calistirir.

    Returns:
        None
    """
    try:
        print(Fore.CYAN + "\n[1] BOT MODU - bilesenler yukleniyor...")
        print("=" * 78)

        # Bagimliliklari burada import et: modul eksikse sadece bu mod etkilenir
        from core.adb_controller import ADBController
        from core.ocr_engine import OCREngine
        from core.screen_capture import ScreenCapture
        from core.state_machine import StateMachine
        from core.vision_engine import VisionEngine
        from data_collector.logger import DataLogger
        from modules.attack_planner import AttackPlanner
        from modules.error_handler import ErrorHandler
        from modules.scout_filter import ScoutFilter

        # 1) Veri toplayici (her sey loglanir)
        logger = DataLogger()

        # 2) ADB baglantisi
        adb = ADBController(serial=config.ADB_SERIAL)
        if not adb.is_connected():
            print(Fore.RED + "[!] Cihaz bagli degil!")
            print(
                "    Cozum: LDPlayer'i acin ve "
                f"'adb connect {config.ADB_CONNECT_ADDRESS}' calistirin."
            )
            logger.log_error(
                "ADB_NOT_CONNECTED",
                "Bot baslatilamadi: ADB cihazi bulunamadi.",
                context={"serial": config.ADB_SERIAL},
            )
            return

        screen = adb.get_screen_size()
        print(f"[MAIN] Ekran cozunurlugu -> {screen[0]}x{screen[1]}")

        # 3) Cekirdek bilesenler
        capture = ScreenCapture(adb=adb)
        vision = VisionEngine()
        ocr = OCREngine()

        # 4) Moduller
        scout = ScoutFilter(
            min_total=config.MIN_TOTAL_LOOT,
            min_gold=config.MIN_GOLD,
            min_elixir=config.MIN_ELIXIR,
            min_dark=config.MIN_DARK,
        )
        planner = AttackPlanner()
        error_handler = ErrorHandler(logger=logger)

        # 5) Yerel AI (opsiyonel)
        ai = None
        if config.USE_LOCAL_AI:
            try:
                from ai.local_vision import LocalVisionAI

                ai = LocalVisionAI()
                if not ai.available:
                    print("[!] Yerel AI kullanilamaz durumda, AI adimlari atlanacak.")
                    ai = None
            except Exception as error:
                print(f"[!] Yerel AI yuklenemedi: {error}")

        # 6) Aktif plan kontrolu
        if config.ACTIVE_PLAN not in planner.plans:
            print(Fore.YELLOW + f"[!] '{config.ACTIVE_PLAN}' plani yok!")
            print("    Once 'python main.py' -> [2] ile savas plani kaydedin.")
            if planner.plans:
                print(f"    Mevcut planlar: {', '.join(planner.list_names())}")
            devam = ask("    Yine de devam edilsin mi? (e/h): ", "h").lower()
            if devam not in ("e", "evet", "y", "yes"):
                return

        # 7) Durum makinesi
        machine = StateMachine(
            adb=adb,
            vision=vision,
            ocr=ocr,
            capture=capture,
            scout_filter=scout,
            planner=planner,
            logger=logger,
            ai=ai,
            error_handler=error_handler,
        )
        logger.log_action(
            "BOT_START",
            {
                "serial": config.ADB_SERIAL,
                "screen": {"width": screen[0], "height": screen[1]},
                "plan": config.ACTIVE_PLAN,
                "ai": ai is not None,
            },
        )

        machine.run()

        # 8) Kapanis: ozet ve disa aktarma
        logger.log_action("BOT_STOP", machine.get_stats())
        logger.finish()
        error_handler.print_summary()
        print(Fore.GREEN + "\n[MAIN] Bot durduruldu. Veriler data/sessions/ klasorunde.")
    except KeyboardInterrupt:
        print("\n[MAIN] Bot kullanici tarafindan durduruldu (Ctrl+C).")
    except Exception as error:
        print(Fore.RED + f"[!] Bot modu hatasi: {error}")


# ==============================================================================
# MOD 2: KAYIT
# ==============================================================================
def record_mode() -> None:
    """
    Kullanicidan koordinat alarak savas plani kaydeder.

    Kullanim: sirayla coord gir (orn. 800,450), eylem tipini ve etiketi yaz.
    Bitirmek icin 'bitti' yaz. 'swipe' icin x2,y2 de sorulur.

    Returns:
        None
    """
    try:
        print(Fore.CYAN + "\n[2] SAVAS PLANI KAYIT MODU")
        print("=" * 78)
        from modules.attack_planner import AttackPlanner

        planner = AttackPlanner()
        planner.list_plans()

        name = ask("\n Plan adi (orn. koy_saldirisi): ", config.ACTIVE_PLAN)
        planner.start_recording(name)

        print("\n Koordinat girin: 'x,y' (orn. 800,450)")
        print(" Eylem tipi : tap / swipe / long_press / key / wait")
        print(" Bitirmek   : 'bitti' yazin")
        print(" Ikinci nokta (swipe icin): 'x2,y2'")
        print("-" * 78)

        # Canli kayit icin (opsiyonel) ADB
        canli = ask(" Hareketleri emulatora da gondersin mi? (e/h): ", "h").lower()
        adb = None
        if canli in ("e", "evet", "y", "yes"):
            try:
                from core.adb_controller import ADBController

                adb = ADBController(auto_connect=True)
            except Exception as error:
                print(f"[!] ADB baslatilamadi, sadece kayit yapilacak: {error}")

        action_count = 0
        while True:
            raw = ask(f"\n [{action_count + 1}] x,y (veya 'bitti'): ")
            if raw.lower() in ("bitti", "bitir", "q", "quit", "exit"):
                break

            try:
                parts = [int(item.strip()) for item in raw.replace(";", ",").split(",")]
                if len(parts) < 2:
                    raise ValueError("En az iki deger gerekli")
                x, y = parts[0], parts[1]
            except Exception:
                print(Fore.RED + "[!] Gecersiz koordinat! Ornek: 800,450")
                continue

            action_type = ask(" Eylem tipi (tap/swipe/long_press/key/wait) [tap]: ", "tap").lower()
            label = ask(" Etiket (orn. ejder birak): ", f"adim_{action_count + 1}")
            metadata = None

            if action_type == "swipe":
                raw2 = ask(" Bitis x2,y2: ", f"{x},{y}")
                try:
                    parts2 = [int(item.strip()) for item in raw2.replace(";", ",").split(",")]
                    metadata = {
                        "x2": parts2[0],
                        "y2": parts2[1],
                        "duration": int(ask(" Sure ms [300]: ", "300") or 300),
                    }
                except Exception:
                    print("[!] Bitis koordinati gecersiz, ayni noktaya kaydirma kaydedildi.")
                    metadata = {"x2": x, "y2": y, "duration": 300}
            elif action_type == "long_press":
                metadata = {"duration": int(ask(" Basma suresi ms [1000]: ", "1000") or 1000)}
            elif action_type == "key":
                metadata = {"keycode": int(x)}
            elif action_type == "wait":
                metadata = {"seconds": float(ask(" Kac saniye [1.0]: ", "1.0") or 1.0)}

            if planner.record_action(x, y, action_type, label, metadata):
                action_count += 1
                # Canli modda hareketi emulatora uygula
                if adb is not None:
                    try:
                        if action_type == "swipe" and metadata:
                            adb.swipe(x, y, int(metadata["x2"]), int(metadata["y2"]),
                                      int(metadata.get("duration", 300)))
                        elif action_type == "long_press":
                            adb.long_press(x, y, int((metadata or {}).get("duration", 1000)))
                        elif action_type == "key":
                            adb.key_event(int((metadata or {}).get("keycode", 4)))
                        elif action_type == "tap":
                            adb.tap(x, y)
                    except Exception as error:
                        print(f"[!] Canli uygulama hatasi: {error}")
                time.sleep(0.4)

        if action_count == 0:
            planner.cancel_recording()
            print(Fore.YELLOW + "[MAIN] Kayit yapilmadi.")
            return

        saved = planner.stop_recording()
        if saved:
            print(Fore.GREEN + f"\n[MAIN] '{saved}' plani kaydedildi ({action_count} hareket).")
            print(f"       config.py icinde ACTIVE_PLAN = \"{saved}\" yapabilirsiniz.")
            planner.list_plans()
        else:
            print(Fore.RED + "[MAIN] Plan kaydedilemedi!")
    except KeyboardInterrupt:
        print("\n[MAIN] Kayit iptal edildi.")
    except Exception as error:
        print(Fore.RED + f"[!] Kayit modu hatasi: {error}")


# ==============================================================================
# MOD 3: KALIBRASYON
# ==============================================================================
def calibrate_mode() -> None:
    """
    calibrate.py aracini baslatir (OCR bolgeleri ve template testleri).

    Returns:
        None
    """
    try:
        print(Fore.CYAN + "\n[3] KALIBRASYON MODU")
        script = BASE_DIR / "calibrate.py"
        if not script.exists():
            print(Fore.RED + f"[!] calibrate.py bulunamadi: {script}")
            return
        code = subprocess.run([sys.executable, str(script)], check=False).returncode
        if code != 0:
            print(f"[!] Kalibrasyon araci {code} kodu ile kapandi.")
    except KeyboardInterrupt:
        print("\n[MAIN] Kalibrasyon iptal edildi.")
    except Exception as error:
        print(Fore.RED + f"[!] Kalibrasyon hatasi: {error}")


# ==============================================================================
# MOD 4: TEST
# ==============================================================================
def test_mode() -> None:
    """
    pytest ile tests/ klasorundeki testleri calistirir ve sonucu gosterir.

    Returns:
        None
    """
    try:
        print(Fore.CYAN + "\n[4] TEST MODU")
        print("=" * 78)
        command: List[str] = [
            sys.executable,
            "-m",
            "pytest",
            str(BASE_DIR / "tests"),
            "-v",
            "--tb=short",
        ]
        print(f"[TEST] Komut: {' '.join(command)}")
        result = subprocess.run(command, check=False)
        print("=" * 78)
        if result.returncode == 0:
            print(Fore.GREEN + "[MAIN] Tum testler basarili! [OK]")
        else:
            print(Fore.RED + f"[MAIN] Testler basarisiz (cikis kodu: {result.returncode})")
    except FileNotFoundError:
        print(Fore.RED + "[!] pytest bulunamadi! Kurmak icin: pip install pytest")
    except Exception as error:
        print(Fore.RED + f"[!] Test calistirma hatasi: {error}")


# ==============================================================================
# MOD 5: DISA AKTARMA
# ==============================================================================
def export_mode() -> str:
    """
    Tum oturum verilerini ve hatalari AI icin tek JSON'da toplar.

    Returns:
        str: Olusturulan dosyanin yolu (bos string -> hata).
    """
    try:
        print(Fore.CYAN + "\n[5] AI ICIN DISA AKTARMA")
        print("=" * 78)
        from data_collector.export_for_ai import export_summary
        from data_collector.logger import DataLogger

        logger = DataLogger()
        session_export = logger.export_for_ai()
        print(f"[MAIN] Oturum verisi     -> {session_export}")

        outcome = export_summary()
        summary_path = str(outcome.get("output_path", ""))
        if outcome.get("success"):
            print(Fore.GREEN + f"[MAIN] AI ozet dosyasi    -> {summary_path}")
            prompt = str(outcome.get("prompt", ""))
            if prompt:
                preview = prompt[:600]
                print("-" * 78)
                print(" AI PROMPT ONIZLEME:")
                print(preview)
                if len(prompt) > len(preview):
                    print(" ... (devami dosyada)")
                print("-" * 78)
        else:
            print(Fore.RED + "[MAIN] Disa aktarma basarisiz oldu.")
        return summary_path
    except Exception as error:
        print(Fore.RED + f"[!] Disa aktarma hatasi: {error}")
        return ""


# ==============================================================================
# ANA MENU DONGUSU
# ==============================================================================
def main_menu() -> None:
    """
    Interaktif ana menuyu calistirir.

    Returns:
        None
    """
    try:
        while True:
            print_menu()
            choice = ask(" Seciminiz [1-6]: ", "6")

            if choice == "1":
                bot_mode()
            elif choice == "2":
                record_mode()
            elif choice == "3":
                calibrate_mode()
            elif choice == "4":
                test_mode()
            elif choice == "5":
                export_mode()
            elif choice in ("6", "q", "quit", "exit", "cikis"):
                print(Fore.CYAN + "\n[MAIN] Gorusuruz! Iyi savaslar! [KILIC]")
                break
            else:
                print(Fore.RED + "[!] Gecersiz secim! 1-6 arasinda bir deger girin.")
    except KeyboardInterrupt:
        print(Fore.CYAN + "\n\n[MAIN] Cikis yapiliyor...")
    except Exception as error:
        print(Fore.RED + f"[!] Menu hatasi: {error}")


def main() -> int:
    """
    Program giris noktasi; komut satiri argumanlarini isler.

    Returns:
        int: 0 -> normal cikis.
    """
    try:
        print_banner()

        arguments = sys.argv[1:]
        if "--bot" in arguments:
            bot_mode()
        elif "--record" in arguments:
            record_mode()
        elif "--calibrate" in arguments:
            calibrate_mode()
        elif "--test" in arguments:
            test_mode()
        elif "--export" in arguments:
            export_mode()
        elif "--help" in arguments or "-h" in arguments:
            print(" Kullanim:")
            print("   python main.py             -> interaktif menu")
            print("   python main.py --bot       -> botu baslat")
            print("   python main.py --record    -> savas plani kaydet")
            print("   python main.py --calibrate -> kalibrasyon araci")
            print("   python main.py --test      -> testleri calistir")
            print("   python main.py --export    -> AI icin disa aktar")
        else:
            main_menu()
        return 0
    except KeyboardInterrupt:
        print("\n[MAIN] Program kullanici tarafindan kapatildi.")
        return 0
    except Exception as error:
        print(Fore.RED + f"[!] Kritik hata: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
