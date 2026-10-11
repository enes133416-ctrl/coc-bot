"""
================================================================================
 config.py - Clash of Clans Yerel AI Bot | Merkezi Konfigurasyon Dosyasi
================================================================================
 Bu dosya botun TUM ayarlarini tek bir yerde toplar. Baska hicbir dosyada
 hardcode koordinat, yol veya esik degeri bulunmaz; her modul buradan okur.

 Icerik:
   1. Yol / klasor sabitleri
   2. Tesseract, ADB ve Ollama otomatik yol tespiti (Windows + Linux)
   3. Loot filtre esikleri (varsayilan: 1.6M toplam)
   4. Template matching ayarlari
   5. OCR bolge koordinatlari (varsayilan cozunurluk: 1600x900)
   6. Zamanlama / dongu ayarlari
   7. Yardimci fonksiyonlar (get_template_path, get_ocr_region, ...)

 Kullanim:
   import config
   print(config.MIN_TOTAL_LOOT)
   bolge = config.get_ocr_region("gold")
================================================================================
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ==============================================================================
# 1) GENEL UYGULAMA BILGILERI
# ==============================================================================
APP_NAME: str = "Clash of Clans Yerel AI Bot"
APP_VERSION: str = "1.0.0"
APP_DESCRIPTION: str = "OpenCV + Tesseract + Ollama/LLaVA tabanli tamamen yerel CoC botu"

# ==============================================================================
# 2) YOL / KLASOR SABITLERI
# ==============================================================================
BASE_DIR: Path = Path(__file__).resolve().parent
ASSETS_DIR: Path = BASE_DIR / "assets"
TEMPLATES_DIR: Path = ASSETS_DIR / "templates"
DEBUG_DIR: Path = ASSETS_DIR / "debug"
DATA_DIR: Path = BASE_DIR / "data"
SESSIONS_DIR: Path = DATA_DIR / "sessions"
ERRORS_DIR: Path = DATA_DIR / "errors"
BATTLE_PLANS_PATH: Path = DATA_DIR / "battle_plans.json"
REQUIREMENTS_PATH: Path = BASE_DIR / "requirements.txt"
SCREENSHOT_DIR: Path = DATA_DIR / "screenshots"

# ==============================================================================
# 3) TESSERACT OCR AYARLARI (Windows + Linux otomatik tespit)
# ==============================================================================
# Ortam degiskeni ile elle override edilebilir:  set TESSERACT_CMD=C:\...
TESSERACT_ENV_VAR: str = "TESSERACT_CMD"

# Windows'ta bilinen kurulum yollari (ilk bulunan kullanilir)
TESSERACT_WINDOWS_CANDIDATES: List[str] = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Tesseract-OCR\tesseract.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    os.path.expanduser(r"~\scoop\apps\tesseract\current\tesseract.exe"),
]

# Linux/Mac'te bilinen kurulum yollari
TESSERACT_LINUX_CANDIDATES: List[str] = [
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
    "/opt/homebrew/bin/tesseract",
    "/snap/bin/tesseract",
]

# OCR dili ve sayfa segmentasyon modu (PSM 7 = tek satir metin)
OCR_LANG: str = "eng"
OCR_PSM: int = 7
OCR_DIGIT_WHITELIST: str = "0123456789.,KMkmbBM"
OCR_TIMEOUT: int = 15

# ==============================================================================
# 4) ADB AYARLARI
# ==============================================================================
ADB_SERIAL: str = os.environ.get("COC_ADB_SERIAL", "emulator-5554")
ADB_HOST: str = "127.0.0.1"
ADB_PORT: int = 5555
ADB_CONNECT_ADDRESS: str = f"{ADB_HOST}:{ADB_PORT}"
ADB_TIMEOUT: int = 20              # saniye - her adb komutu icin maksimum sure
ADB_SCREENSHOT_PATH: str = "/sdcard/coc_bot_screen.png"
ADB_DEFAULT_TAP_DELAY: float = 0.3  # saniye - tiklamadan sonra bekleme

# ==============================================================================
# 5) LOOT FILTRE ESIKLERI  (1.6M kurali)
# ==============================================================================
MIN_TOTAL_LOOT: int = 1_600_000    # gold + elixir + dark*oran toplami
MIN_GOLD: int = 600_000
MIN_ELIXIR: int = 600_000
MIN_DARK: int = 0                  # kara iksir sarti (0 = sart yok)
DARK_ELIXIR_MULTIPLIER: float = 100.0  # 1 kara iksir ~ 100 altin/iksir degeri
MAX_SKIPS_BEFORE_RESET: int = 500   # bu kadar atlamadan sonra istatistik sifirlama

# ==============================================================================
# 6) VISION / TEMPLATE MATCHING AYARLARI
# ==============================================================================
TEMPLATE_THRESHOLD: float = 0.82   # min eslesme skoru (0.0 - 1.0)
MULTI_SCALE_ENABLED: bool = True
SCALE_MIN: float = 0.7
SCALE_MAX: float = 1.3
SCALE_STEPS: int = 13              # 0.70 ... 1.30 arasi 13 farkli olcek
TEMPLATE_WAIT_TIMEOUT: int = 60    # wait_for_template varsayilan timeout (saniye)
TEMPLATE_WAIT_INTERVAL: float = 1.5  # kontroller arasi bekleme (saniye)
DEBUG_DRAW_ENABLED: bool = True    # tespit kutularini ciz ve kaydet

# Ekranda aranacak buton template dosyalari (assets/templates/ icinde)
TEMPLATES: Dict[str, str] = {
    "attack_button": "attack_button.png",
    "find_match": "find_match.png",
    "next_button": "next_button.png",
    "return_home": "return_home.png",
    "surrender": "surrender.png",
    "end_battle_ok": "end_battle_ok.png",
    "collect_resources": "collect_resources.png",
    "hero_king": "hero_king.png",
    "hero_queen": "hero_queen.png",
    "spell_factory": "spell_factory.png",
}

# ==============================================================================
# 7) EKRAN COZUNURLUGU VE OCR BOLGELERI (varsayilan: 1600x900)
# ==============================================================================
SCREEN_WIDTH: int = 1600
SCREEN_HEIGHT: int = 900
AUTO_SCALE_REGIONS: bool = True    # farkli cozunurlukte bolgeleri otomatik olcekle

# Her bolge: {"x": sol, "y": ust, "w": genislik, "h": yukseklik}
#
# DIKKAT: Rakip onizleme (scout) ekraninda loot paneli EKRANIN SOL UST kosesinde
# D I K E Y   olarak dizilir:  altin / iksir / kara iksir (3 satir, ikonlar solda).
# Asagidaki degerler o duzene gore, 1600x900 referans cozunurlugu icin ayarlanmistir.
#
#   +--- sol ust kose ---
#   |  [icon] 493 564    <- gold    (y ~ 104)
#   |  [icon] 1 017 336  <- elixir  (y ~ 148)
#   |  [icon] 3 190      <- dark    (y ~ 192)
#
# Farkli cozunurluklerde AUTO_SCALE_REGIONS otomatik olceklendirir, ancak en
# dogru sonuc icin:   python calibrate.py  ->  [1] OCR bolgelerini kalibre et
OCR_REGIONS: Dict[str, Dict[str, int]] = {
    "gold": {"x": 58, "y": 104, "w": 200, "h": 40},
    "elixir": {"x": 58, "y": 148, "w": 200, "h": 40},
    "dark": {"x": 58, "y": 192, "w": 200, "h": 40},
    # Savas icinde okunan alanlar (istege bagli)
    "total": {"x": 58, "y": 236, "w": 240, "h": 40},
    "stars": {"x": 620, "y": 30, "w": 180, "h": 42},
    "percentage": {"x": 860, "y": 30, "w": 180, "h": 42},
    "timer": {"x": 1240, "y": 30, "w": 200, "h": 42},
}

# ==============================================================================
# 8) BOT DURUM MAKINESI AYARLARI
# ==============================================================================
ACTIVE_PLAN: str = "varsayilan"          # hangi savas plani oynatilacak
BATTLE_TIMEOUT: int = 180                # savas sonu beklerken maks sure (saniye)
PLAYBACK_SPEED: float = 1.0              # plan oynatma hizi (1.0 = orijinal)
STATE_LOOP_DELAY: float = 1.0            # her state sonrasi bekleme (saniye)
HOME_WAIT_TIMEOUT: int = 45              # ana ekranin yuklenmesini bekleme
FIND_MATCH_TIMEOUT: int = 60             # eslesme bulma ekrani timeout
SCOUT_READ_DELAY: float = 1.2            # rakibi gorunce loot okumadan once bekleme
RETURN_HOME_WAIT: float = 4.0            # eve donus sonrasi bekleme
MAX_SKIPS_PER_CYCLE: int = 40            # tek dongude atlanabilecek maks rakip
AUTO_SURRENDER_MINUTES: int = 3          # bu sureden sonra otomatik teslim (0 = kapali)

# ==============================================================================
# 9) YEREL AI (OLLAMA + LLaVA) AYARLARI
# ==============================================================================
USE_LOCAL_AI: bool = True                # False ise AI cagrilari tamamen atlanir
OLLAMA_URL: str = "http://localhost:11434"
OLLAMA_MODEL: str = "llava:7b"
OLLAMA_TIMEOUT: int = 60                 # saniye - tek istek icin maksimum sure
OLLAMA_HEALTH_TIMEOUT: int = 5           # baglanti testi timeout
AI_BASE_ANALYSIS_PROMPT: str = (
    "Bu Clash of Clans koy ekranini incele. Su JSON formatinda cevap ver: "
    '{"weak_side": "left|right|top|bottom", '
    '"town_hall_position": "x,y veya aciklama", '
    '"strategy": "kisa saldiri stratejisi", '
    '"notes": "dikkat edilmesi gerekenler"}'
)
AI_HOME_SCREEN_PROMPT: str = (
    "Bu goruntunun ekran goruntusu Clash of Clans ANA EKRANI (koy ekrani) mu? "
    "Sadece YES veya NO yaz."
)
AI_BATTLE_SCREEN_PROMPT: str = (
    "Bu goruntunun ekran goruntusu Clash of Clans SALDIRI ekrani mi? "
    "Sadece YES veya NO yaz."
)
AI_DESCRIBE_PROMPT: str = (
    "Bu Clash of Clans ekran goruntusunu Turkce olarak detayli acikla. "
    "Ekranda hangi butonlar, hangi degerler ve hangi durum var?"
)

# ==============================================================================
# 10) LOG / VERI TOPLAMA AYARLARI
# ==============================================================================
SAVE_SCREENSHOTS: bool = True      # her eylemde ekran goruntusu sakla
LOG_ALL_ACTIONS: bool = True       # her eylemi JSON'a kaydet
LOG_TO_CONSOLE: bool = True        # konsola da yaz
LOG_TO_FILE: bool = True           # data/sessions/<oturum>/bot.log dosyasina yaz
SESSION_PREFIX: str = "session"
EXPORT_MAX_SESSIONS: int = 50      # AI export'unda taranacak maks oturum sayisi
ERROR_SCREENSHOT_LIMIT: int = 200  # errors/ klasorunde tutulacak maks goruntu

# ==============================================================================
# 11) TEST / GELISTIRME AYARLARI
# ==============================================================================
TEST_IMAGE_SIZE: Tuple[int, int] = (400, 120)   # testler icin sentetik goruntu
TEST_SLEEP_BETWEEN_STATES: float = 0.0          # testlerde bekleme yapma
DRY_RUN: bool = False              # True ise hicbir tiklama gercekten yapilmaz
VERBOSE: bool = True               # ekstra konsol detayi

# ==============================================================================
# 12) OTOMATIK YOL TESPITI
# ==============================================================================


def find_tesseract() -> Optional[str]:
    """
    Tesseract OCR calistirilabilir dosyasinin yolunu otomatik bulur.

    Sirasiyla su kaynaklara bakar:
      1. TESSERACT_CMD ortam degiskeni
      2. TESSERACT_WINDOWS_CANDIDATES (sadece Windows'ta)
      3. TESSERACT_LINUX_CANDIDATES (Linux/Mac)
      4. PATH uzerindeki "tesseract" komutu

    Returns:
        Optional[str]: Bulunan tesseract yolu, bulunamazsa None.
    """
    try:
        # 1) Ortam degiskeni
        env_value = os.environ.get(TESSERACT_ENV_VAR, "").strip()
        if env_value and Path(env_value).exists():
            return env_value

        # 2) Isletim sistemine gore bilinen yollar
        candidates: List[str] = []
        if sys.platform.startswith("win"):
            candidates.extend(TESSERACT_WINDOWS_CANDIDATES)
        else:
            candidates.extend(TESSERACT_LINUX_CANDIDATES)
        candidates.extend(TESSERACT_WINDOWS_CANDIDATES)
        candidates.extend(TESSERACT_LINUX_CANDIDATES)
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate

        # 3) PATH uzerinde ara
        found = shutil.which("tesseract")
        if found:
            return found
    except Exception as error:  # pragma: no cover - ortam hatasi
        print(f"[!] Tesseract yolu tespit edilirken hata olustu: {error}")
    return None


def find_adb() -> Optional[str]:
    """
    ADB (Android Debug Bridge) calistirilabilir dosyasinin yolunu bulur.

    Returns:
        Optional[str]: Bulunan adb yolu, bulunamazsa None.
    """
    try:
        env_value = os.environ.get("ADB_PATH", "").strip()
        if env_value and Path(env_value).exists():
            return env_value

        candidates: List[str] = [
            os.path.expanduser(r"~\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
            r"C:\platform-tools\adb.exe",
            r"C:\LDPlayer\LDPlayer9\adb.exe",
            r"C:\LDPlayer\LDPlayer4.0\adb.exe",
            "/usr/bin/adb",
            "/usr/local/bin/adb",
            "/opt/android-sdk/platform-tools/adb",
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate

        found = shutil.which("adb")
        if found:
            return found
    except Exception as error:  # pragma: no cover - ortam hatasi
        print(f"[!] ADB yolu tespit edilirken hata olustu: {error}")
    return None


# Calisma aninda tespit edilen yollar (import sirasinda hesaplanir)
TESSERACT_CMD: Optional[str] = find_tesseract()
ADB_PATH: Optional[str] = find_adb()

# ==============================================================================
# 13) YARDIMCI FONKSIYONLAR
# ==============================================================================


def get_template_path(name: str) -> Path:
    """
    Template adini tam dosya yoluna cevirir.

    Args:
        name (str): TEMPLATES sozlugundeki anahtar (orn. "attack_button")
                    veya dogrudan dosya adi (orn. "next_button.png").

    Returns:
        Path: Template dosyasinin tam yolu (dosya var mi diye kontrol edilmez).
    """
    try:
        if name in TEMPLATES:
            return TEMPLATES_DIR / TEMPLATES[name]
        if not name.lower().endswith(".png"):
            return TEMPLATES_DIR / f"{name}.png"
        return TEMPLATES_DIR / name
    except Exception as error:  # pragma: no cover - beklenmeyen hata
        print(f"[!] Template yolu olusturulamadi ({name}): {error}")
        return TEMPLATES_DIR / f"{name}.png"


def get_ocr_region(name: str) -> Dict[str, int]:
    """
    OCR bolge sozlugunu dondurur; yoksa guvenli varsayilan uretir.

    Args:
        name (str): OCR_REGIONS anahtari ("gold", "elixir", "dark", ...).

    Returns:
        Dict[str, int]: {"x", "y", "w", "h"} sozlugu.
    """
    try:
        return dict(OCR_REGIONS.get(name, {"x": 0, "y": 0, "w": 200, "h": 44}))
    except Exception as error:  # pragma: no cover - beklenmeyen hata
        print(f"[!] OCR bolgesi okunamadi ({name}): {error}")
        return {"x": 0, "y": 0, "w": 200, "h": 44}


def scale_region(region: Dict[str, int], width: int, height: int) -> Dict[str, int]:
    """
    Bolge koordinatlarini gercek ekran cozunurlugune gore olcekler.

    1600x900 icin hazirlanmis degerleri farkli cozunurluklere uyarlar.

    Args:
        region (Dict[str, int]): {"x", "y", "w", "h"}
        width (int): Gercek ekran genisligi.
        height (int): Gercek ekran yuksekligi.

    Returns:
        Dict[str, int]: Olceklenmis bolge.
    """
    try:
        if not AUTO_SCALE_REGIONS or width <= 0 or height <= 0:
            return dict(region)
        ratio_x = width / float(SCREEN_WIDTH)
        ratio_y = height / float(SCREEN_HEIGHT)
        return {
            "x": int(region.get("x", 0) * ratio_x),
            "y": int(region.get("y", 0) * ratio_y),
            "w": max(1, int(region.get("w", 1) * ratio_x)),
            "h": max(1, int(region.get("h", 1) * ratio_y)),
        }
    except Exception as error:  # pragma: no cover - beklenmeyen hata
        print(f"[!] Bolge olcekleme hatasi: {error}")
        return dict(region)


def ensure_directories() -> None:
    """
    Botun ihtiyac ettigi tum klasorleri (yoksa) olusturur.

    Returns:
        None
    """
    try:
        for folder in (
            ASSETS_DIR,
            TEMPLATES_DIR,
            DEBUG_DIR,
            DATA_DIR,
            SESSIONS_DIR,
            ERRORS_DIR,
            SCREENSHOT_DIR,
        ):
            folder.mkdir(parents=True, exist_ok=True)
    except Exception as error:
        print(f"[!] Klasor olusturma hatasi: {error}")


def validate_config() -> List[str]:
    """
    Kritik ayarlari kontrol eder ve uyarilar listesi dondurur.

    Returns:
        List[str]: Bulunan sorunlarin Turkce aciklamalari (bos liste = her sey yolunda).
    """
    warnings: List[str] = []
    try:
        if TESSERACT_CMD is None:
            warnings.append(
                "Tesseract bulunamadi! scripts/install_tesseract.ps1 (Windows) veya "
                "scripts/install_tesseract.sh (Linux) calistirin."
            )
        if ADB_PATH is None:
            warnings.append(
                "ADB bulunamadi! scripts/setup_adb.ps1 calistirin veya platform-tools "
                "klasorunu PATH'e ekleyin."
            )
        if MIN_TOTAL_LOOT < (MIN_GOLD + MIN_ELIXIR):
            warnings.append(
                "MIN_TOTAL_LOOT, MIN_GOLD + MIN_ELIXIR toplamindan kucuk! "
                "Filtre beklendigi gibi calismayabilir."
            )
        if not (0.0 < TEMPLATE_THRESHOLD <= 1.0):
            warnings.append("TEMPLATE_THRESHOLD 0.0 ile 1.0 arasinda olmali.")
        if not TEMPLATES_DIR.exists():
            warnings.append(f"Template klasoru yok: {TEMPLATES_DIR}")
    except Exception as error:  # pragma: no cover - beklenmeyen hata
        warnings.append(f"Konfigurasyon dogrulama hatasi: {error}")
    return warnings


def print_config_summary() -> None:
    """
    Aktif konfigurasyonun ozetini konsola yazar.

    Returns:
        None
    """
    try:
        print("=" * 78)
        print(f" {APP_NAME} v{APP_VERSION} - KONFIGURASYON OZETI")
        print("=" * 78)
        print(f" [DIR]  Proje klasoru    : {BASE_DIR}")
        print(f" [DIR]  Template klasoru : {TEMPLATES_DIR}")
        print(f" [DIR]  Veri klasoru     : {DATA_DIR}")
        print(f" [OCR]  Tesseract        : {TESSERACT_CMD or 'BULUNAMADI (!)'}")
        print(f" [ADB]  ADB yolu         : {ADB_PATH or 'BULUNAMADI (!)'}")
        print(f" [ADB]  Cihaz serial     : {ADB_SERIAL}")
        print(f" [LOOT] Min toplam loot  : {MIN_TOTAL_LOOT:,}")
        print(f" [LOOT] Min altin        : {MIN_GOLD:,}")
        print(f" [LOOT] Min iksir        : {MIN_ELIXIR:,}")
        print(f" [LOOT] Min kara iksir   : {MIN_DARK:,}")
        print(f" [CV]   Eslesme esigi    : {TEMPLATE_THRESHOLD}")
        print(f" [CV]   Olcek sayisi     : {SCALE_STEPS} ({SCALE_MIN} - {SCALE_MAX})")
        print(f" [AI]   Yerel AI aktif   : {USE_LOCAL_AI}")
        print(f" [AI]   Ollama           : {OLLAMA_URL} ({OLLAMA_MODEL})")
        print(f" [PLAN] Aktif plan       : {ACTIVE_PLAN}")
        print(f" [TIME] Savas timeout    : {BATTLE_TIMEOUT} sn")
        print("=" * 78)
    except Exception as error:  # pragma: no cover - beklenmeyen hata
        print(f"[!] Konfigurasyon ozeti yazilamadi: {error}")


# ==============================================================================
# 14) MODUL IMPORT EDILDIGINDE KLASORLERI HAZIRLA
# ==============================================================================
ensure_directories()


if __name__ == "__main__":  # pragma: no cover - elle calistirma
    print_config_summary()
    problems = validate_config()
    if problems:
        print("\n[!] KONFIGURASYON UYARILARI:")
        for index, item in enumerate(problems, start=1):
            print(f"  {index}. {item}")
    else:
        print("\n[+] Konfigurasyon dogrulandi, sorun bulunamadi.")
