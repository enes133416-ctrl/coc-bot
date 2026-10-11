"""
================================================================================
 setup.py - Kurulum Scripti
================================================================================
 Projeyi kurmak icin gereken her seyi tek komutla yapar:

   1. Python bagimliliklarini pip ile kurar (opencv, pytesseract, ...)
   2. Tesseract OCR kurulu mu kontrol eder (yoksa kurulum komutu onerir)
   3. Ollama (yerel AI) kurulu mu kontrol eder (yoksa kurulum komutu onerir)
   4. ADB (Android Debug Bridge) kurulu mu kontrol eder (yoksa onerir)
   5. data/ klasor yapisini olusturur
   6. assets/templates/ klasorunu olusturur
   7. data/battle_plans.json yoksa bos plan dosyasi olusturur
   8. Sonunda kurulum ozeti yazar

 Kullanim:
   python setup.py                 -> tam kurulum kontrolu
   python setup.py --skip-pip      -> pip kurulumunu atla
   python setup.py --quiet         -> daha az cikti
================================================================================
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

# Bu dosya ile ayni klasordeki config.py'yi kullan
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config  # noqa: E402

# ==============================================================================
# YARDIMCI FONKSIYONLAR
# ==============================================================================


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


def run_command(command: List[str], timeout: int = 600) -> int:
    """
    Bir komutu calistirir ve donus kodunu dondurur.

    Args:
        command (List[str]): Komut ve argumanlari.
        timeout (int): Zaman asimi (saniye).

    Returns:
        int: Komutun donus kodu (hata halinde -1).
    """
    try:
        print(f"[KOMUT] {' '.join(command)}")
        result = subprocess.run(command, timeout=timeout, check=False)
        return int(result.returncode)
    except FileNotFoundError:
        print(f"[!] Komut bulunamadi: {command[0]}")
        return -1
    except subprocess.TimeoutExpired:
        print(f"[!] Komut zaman asimina ugradi: {' '.join(command)}")
        return -1
    except Exception as error:
        print(f"[!] Komut hatasi: {error}")
        return -1


# ==============================================================================
# 1) PYTHON BAGIMLILIKLARI
# ==============================================================================
def install_requirements(skip: bool = False) -> bool:
    """
    requirements.txt icindeki bagimliliklari pip ile kurar.

    Args:
        skip (bool): True ise kurulum yapilmaz.

    Returns:
        bool: True -> bagimliliklar hazir.
    """
    try:
        if skip:
            print("[SETUP] pip kurulumu atlandi (--skip-pip).")
            return True

        requirements = BASE_DIR / "requirements.txt"
        if not requirements.exists():
            print(f"[!] requirements.txt bulunamadi: {requirements}")
            return False

        print_header("1/7 - PYTHON BAGIMLILIKLARI KURULUYOR")
        code = run_command(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements)]
        )
        if code == 0:
            print("[OK]  Bagimliliklar basariyla kuruldu.")
            return True

        # Bazi sistemlerde --break-system-packages gerekir (PEP 668)
        print("[!] Normal kurulum basarisiz, --break-system-packages deneniyor...")
        code = run_command(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--break-system-packages",
                "-r",
                str(requirements),
            ]
        )
        if code == 0:
            print("[OK]  Bagimliliklar kuruldu (break-system-packages ile).")
            return True

        # Son care: --user
        print("[!] Tekrar deneniyor: --user")
        code = run_command(
            [sys.executable, "-m", "pip", "install", "--user", "-r", str(requirements)]
        )
        print("[OK]  Bagimliliklar kuruldu." if code == 0 else "[!] pip kurulumu basarisiz!")
        return code == 0
    except Exception as error:
        print(f"[!] Bagimlilik kurulum hatasi: {error}")
        return False


# ==============================================================================
# 2) TESSERACT KONTROLU
# ==============================================================================
def check_tesseract() -> bool:
    """
    Tesseract OCR kurulu olup olmadigini kontrol eder.

    Returns:
        bool: True -> Tesseract hazir.
    """
    try:
        print_header("2/7 - TESSERACT OCR KONTROLU")
        path = config.find_tesseract()
        if path:
            result = subprocess.run(
                [path, "--version"], capture_output=True, text=True, timeout=20, check=False
            )
            first_line = (result.stdout or "").splitlines()[0] if result.stdout else "?"
            print(f"[OK]  Tesseract bulundu -> {path}")
            print(f"      Surum: {first_line}")
            return True

        print("[!] Tesseract BULUNAMADI!")
        if platform.system() == "Windows":
            print(
                "      Kurulum icin:  powershell -ExecutionPolicy Bypass -File "
                "scripts/install_tesseract.ps1"
            )
            print("      veya indir   :  https://github.com/UB-Mannheim/tesseract/wiki")
        elif platform.system() == "Darwin":
            print("      Kurulum icin:  brew install tesseract")
        else:
            print("      Kurulum icin:  bash scripts/install_tesseract.sh")
            print("      veya         :  sudo apt-get install -y tesseract-ocr")
        return False
    except Exception as error:
        print(f"[!] Tesseract kontrol hatasi: {error}")
        return False


# ==============================================================================
# 3) OLLAMA KONTROLU
# ==============================================================================
def check_ollama() -> bool:
    """
    Ollama (yerel AI) kurulu olup olmadigini kontrol eder.

    Returns:
        bool: True -> Ollama hazir.
    """
    try:
        print_header("3/7 - OLLAMA (YEREL AI) KONTROLU")
        ollama_path = shutil.which("ollama")
        if ollama_path:
            result = subprocess.run(
                [ollama_path, "--version"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            version = (result.stdout or "").strip() or (result.stderr or "").strip()
            print(f"[OK]  Ollama bulundu -> {ollama_path}")
            print(f"      Surum: {version}")
            print(f"      Model kurmak icin: ollama pull {config.OLLAMA_MODEL}")
            return True

        print("[!] Ollama BULUNAMADI (yerel AI devre disi kalacak)!")
        print("      Kurulum icin:  https://ollama.com/download")
        if platform.system() == "Windows":
            print(
                "      Otomatik     :  powershell -ExecutionPolicy Bypass -File "
                "scripts/install_ollama.ps1"
            )
        print(f"      Kurduktan sonra: ollama pull {config.OLLAMA_MODEL}")
        print("      Not: Ollama olmadan da bot calisir (USE_LOCAL_AI = False yapin).")
        return False
    except Exception as error:
        print(f"[!] Ollama kontrol hatasi: {error}")
        return False


# ==============================================================================
# 4) ADB KONTROLU
# ==============================================================================
def check_adb() -> bool:
    """
    ADB (Android Debug Bridge) kurulu olup olmadigini kontrol eder.

    Returns:
        bool: True -> ADB hazir.
    """
    try:
        print_header("4/7 - ADB (ANDROID DEBUG BRIDGE) KONTROLU")
        adb_path = config.find_adb()
        if adb_path:
            result = subprocess.run(
                [adb_path, "version"], capture_output=True, text=True, timeout=20, check=False
            )
            version = (result.stdout or "").strip().splitlines()
            print(f"[OK]  ADB bulundu -> {adb_path}")
            if version:
                print(f"      {version[0]}")
            print(f"      LDPlayer baglantisi: {adb_path} connect {config.ADB_CONNECT_ADDRESS}")
            return True

        print("[!] ADB BULUNAMADI!")
        if platform.system() == "Windows":
            print(
                "      Kurulum icin:  powershell -ExecutionPolicy Bypass -File "
                "scripts/setup_adb.ps1"
            )
            print("      LDPlayer ile birlikte gelen adb.exe de kullanilabilir.")
        else:
            print("      Kurulum icin:  sudo apt-get install -y android-tools-adb")
        return False
    except Exception as error:
        print(f"[!] ADB kontrol hatasi: {error}")
        return False


# ==============================================================================
# 5) KLASOR YAPISI
# ==============================================================================
def create_directories() -> bool:
    """
    Gerekli tum klasorleri olusturur.

    Returns:
        bool: True -> klasorler hazir.
    """
    try:
        print_header("5/7 - KLASOR YAPISI OLUSTURULUYOR")
        config.ensure_directories()
        folders = [
            config.ASSETS_DIR,
            config.TEMPLATES_DIR,
            config.DEBUG_DIR,
            config.DATA_DIR,
            config.SESSIONS_DIR,
            config.ERRORS_DIR,
            config.SCREENSHOT_DIR,
            config.DATA_DIR / "exports",
            config.DATA_DIR / "backups",
        ]
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)
            gitkeep = folder / ".gitkeep"
            if not any(folder.iterdir()):
                gitkeep.touch()
            print(f"[OK]  {folder}")
        return True
    except Exception as error:
        print(f"[!] Klasor olusturma hatasi: {error}")
        return False


# ==============================================================================
# 6) SAVAS PLANI DOSYASI
# ==============================================================================
def create_battle_plans() -> bool:
    """
    battle_plans.json yoksa bos plan dosyasi olusturur.

    Returns:
        bool: True -> plan dosyasi hazir.
    """
    try:
        print_header("6/7 - SAVAS PLANI DOSYASI")
        target = Path(config.BATTLE_PLANS_PATH)
        if target.exists():
            try:
                with open(target, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                print(f"[OK]  Plan dosyasi mevcut -> {target} ({len(data)} plan)")
            except json.JSONDecodeError:
                print("[!] Plan dosyasi bozuk, yeniden olusturuluyor...")
                with open(target, "w", encoding="utf-8") as handle:
                    json.dump({}, handle, indent=4, ensure_ascii=False)
            return True

        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            json.dump({}, handle, indent=4, ensure_ascii=False)
        print(f"[OK]  Bos plan dosyasi olusturuldu -> {target}")
        return True
    except Exception as error:
        print(f"[!] Plan dosyasi olusturma hatasi: {error}")
        return False


# ==============================================================================
# 7) TEMPLATE DOSYALARI
# ==============================================================================
def check_templates() -> Dict[str, Any]:
    """
    assets/templates/ klasorundeki template dosyalarini kontrol eder.

    Returns:
        Dict[str, Any]: {"found": List[str], "missing": List[str]}
    """
    result: Dict[str, Any] = {"found": [], "missing": []}
    try:
        print_header("7/7 - TEMPLATE DOSYALARI KONTROLU")
        config.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        for key, file_name in config.TEMPLATES.items():
            target = Path(config.TEMPLATES_DIR) / file_name
            if target.exists():
                result["found"].append(file_name)
                print(f"[OK]  {key:<18} -> {file_name}")
            else:
                result["missing"].append(file_name)
                print(f"[--]  {key:<18} -> {file_name} (EKSIK)")

        if result["missing"]:
            print("\n[!] Eksik template'ler var! Bot bu butonlari bulamaz.")
            print("    Cozum: oyun ekranindan butonun goruntusunu kesip")
            print(f"    su klasore PNG olarak kaydedin: {config.TEMPLATES_DIR}")
            print("    Ayrintili rehber: assets/templates/README.md")
        else:
            print("\n[OK]  Tum template'ler hazir.")
        return result
    except Exception as error:
        print(f"[!] Template kontrol hatasi: {error}")
        return result


# ==============================================================================
# ANA AKIS
# ==============================================================================
def main() -> int:
    """
    Kurulum surecini calistirir ve ozet yazar.

    Returns:
        int: 0 -> basarili, 1 -> kritik hata.
    """
    skip_pip = "--skip-pip" in sys.argv
    try:
        print("=" * 78)
        print(f" {config.APP_NAME} v{config.APP_VERSION} - KURULUM")
        print("=" * 78)
        print(f" Python     : {sys.version.split()[0]}  ({sys.executable})")
        print(f" Isletim S. : {platform.system()} {platform.release()}")
        print(f" Proje kok  : {BASE_DIR}")

        pip_ok = install_requirements(skip=skip_pip)
        tesseract_ok = check_tesseract()
        ollama_ok = check_ollama()
        adb_ok = check_adb()
        dirs_ok = create_directories()
        plans_ok = create_battle_plans()
        templates = check_templates()

        # ---------------- OZET ----------------
        print_header("KURULUM OZETI")
        rows = [
            ("Python bagimliliklari", pip_ok, "pip install -r requirements.txt"),
            ("Tesseract OCR", tesseract_ok, "scripts/install_tesseract.ps1 / .sh"),
            ("Ollama (yerel AI)", ollama_ok, "scripts/install_ollama.ps1"),
            ("ADB", adb_ok, "scripts/setup_adb.ps1"),
            ("Klasor yapisi", dirs_ok, "-"),
            ("Savas plani dosyasi", plans_ok, "data/battle_plans.json"),
            (
                "Template dosyalari",
                not templates["missing"],
                f"assets/templates/ ({len(templates['found'])}/"
                f"{len(templates['found']) + len(templates['missing'])})",
            ),
        ]
        for name, status, hint in rows:
            mark = "[OK] " if status else "[!!] "
            extra = "" if status else f"  ->  {hint}"
            print(f" {mark} {name:<24}{extra}")

        print("\n SONRAKI ADIMLAR:")
        print("   1. LDPlayer'i acin ve Clash of Clans'i baslatin")
        print(f"   2. ADB baglantisi: adb connect {config.ADB_CONNECT_ADDRESS}")
        print("   3. Buton template'lerini assets/templates/ klasorune ekleyin")
        print("   4. Kalibrasyon: python calibrate.py")
        print("   5. Botu baslatin: python main.py")
        print("=" * 78)

        critical_ok = dirs_ok and plans_ok
        if not critical_ok:
            print("\n[!] Kritik kurulum adimlari basarisiz oldu!")
            return 1
        if not pip_ok:
            print("\n[!] Python bagimliliklari kurulamadi, bot calismayabilir.")
            return 1
        if not tesseract_ok:
            print("\n[!] UYARI: Tesseract yok - OCR (loot okuma) calismayacak.")
        if not adb_ok:
            print("\n[!] UYARI: ADB yok - bot emulatora baglanamayacak.")
        if not ollama_ok:
            print("\n[!] UYARI: Ollama yok - yerel AI ozellikleri devre disi.")
        print("\n[OK]  Kurulum tamamlandi!")
        return 0
    except KeyboardInterrupt:
        print("\n[!] Kurulum kullanici tarafindan iptal edildi.")
        return 1
    except Exception as error:
        print(f"[!] Kurulum sirasinda kritik hata: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
