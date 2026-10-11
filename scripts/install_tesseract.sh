#!/usr/bin/env bash
# ==============================================================================
# scripts/install_tesseract.sh
# ------------------------------------------------------------------------------
# Linux (Ubuntu/Debian) uzerinde Tesseract OCR kurulum scripti.
#
# Yaptigi isler:
#   1. Root yetkisi kontrolu (gerekirse sudo ile yeniden calisir)
#   2. Paket yoneticisini tespit eder (apt / dnf / pacman / brew)
#   3. Tesseract + dil paketlerini kurar (eng, tur)
#   4. PATH ve kurulumu dogrular (tesseract --version)
#
# Kullanim:
#   bash scripts/install_tesseract.sh
# ==============================================================================

set -u

# -------- Renkli cikti yardimcilari --------
if [ -t 1 ]; then
    KIRMIZI='\033[0;31m'
    YESIL='\033[0;32m'
    SARI='\033[0;33m'
    MAVI='\033[0;36m'
    SIFIR='\033[0m'
else
    KIRMIZI=''; YESIL=''; SARI=''; MAVI=''; SIFIR=''
fi

adim()   { printf "\n${MAVI}=== %s ===${SIFIR}\n" "$1"; }
tamam()  { printf "${YESIL}[OK]  %s${SIFIR}\n" "$1"; }
uyari()  { printf "${SARI}[!]   %s${SIFIR}\n" "$1"; }
hata()   { printf "${KIRMIZI}[X]   %s${SIFIR}\n" "$1"; }

printf "${MAVI}==============================================================${SIFIR}\n"
printf "${MAVI} TESSERACT OCR KURULUMU (Linux / macOS)${SIFIR}\n"
printf "${MAVI}==============================================================${SIFIR}\n"

# -------- 1) Zaten kurulu mu? --------
adim "1/4 - Mevcut kurulum kontrol ediliyor"
if command -v tesseract >/dev/null 2>&1; then
    tamam "Tesseract zaten kurulu: $(command -v tesseract)"
    tesseract --version 2>&1 | head -n 1
    printf "${YESIL}Kurulum atlandi.${SIFIR}\n"
    exit 0
fi
uyari "Tesseract bulunamadi, kurulum baslatiliyor..."

# -------- 2) Root yetkisi --------
adim "2/4 - Yetki kontrolu"
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
        uyari "Root degilsiniz, 'sudo' kullanilacak."
    else
        hata "Root degilsiniz ve sudo yok! Scripti root olarak calistirin."
        exit 1
    fi
else
    tamam "Root yetkisi mevcut."
fi

# -------- 3) Paket yoneticisine gore kurulum --------
adim "3/4 - Tesseract kuruluyor"

if command -v apt-get >/dev/null 2>&1; then
    echo "[KURULUM] apt-get kullaniliyor (Ubuntu/Debian)..."
    $SUDO apt-get update -y
    $SUDO apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-tur \
        libtesseract-dev libleptonica-dev || {
        hata "apt-get kurulumu basarisiz!"
        exit 1
    }
elif command -v dnf >/dev/null 2>&1; then
    echo "[KURULUM] dnf kullaniliyor (Fedora)..."
    $SUDO dnf install -y tesseract tesseract-langpack-eng tesseract-langpack-tur || {
        hata "dnf kurulumu basarisiz!"
        exit 1
    }
elif command -v yum >/dev/null 2>&1; then
    echo "[KURULUM] yum kullaniliyor (RHEL/CentOS)..."
    $SUDO yum install -y epel-release || true
    $SUDO yum install -y tesseract tesseract-langpack-eng || {
        hata "yum kurulumu basarisiz!"
        exit 1
    }
elif command -v pacman >/dev/null 2>&1; then
    echo "[KURULUM] pacman kullaniliyor (Arch)..."
    $SUDO pacman -Sy --noconfirm tesseract tesseract-data-eng tesseract-data-tur || {
        hata "pacman kurulumu basarisiz!"
        exit 1
    }
elif command -v brew >/dev/null 2>&1; then
    echo "[KURULUM] brew kullaniliyor (macOS)..."
    brew install tesseract tesseract-lang || {
        hata "brew kurulumu basarisiz!"
        exit 1
    }
else
    hata "Desteklenen paket yoneticisi bulunamadi (apt/dnf/yum/pacman/brew)!"
    echo "Manuel kurulum: https://tesseract-ocr.github.io/tessdoc/Installation.html"
    exit 1
fi

tamam "Kurulum komutlari tamamlandi."

# -------- 4) Dogrulama --------
adim "4/4 - Kurulum dogrulaniyor"

if ! command -v tesseract >/dev/null 2>&1; then
    hata "tesseract hala PATH uzerinde bulunamadi!"
    echo "  Kontrol: which tesseract"
    echo "  PATH   : $PATH"
    exit 1
fi

TESSERACT_YOLU="$(command -v tesseract)"
tamam "Tesseract yolu: $TESSERACT_YOLU"
tesseract --version 2>&1 | head -n 1

echo ""
echo "[BILGI] Kurulu diller:"
tesseract --list-langs 2>&1 | tail -n +2 | while read -r dil; do
    echo "   - $dil"
done

# TESSERACT_CMD ortam degiskeni onerisi
echo ""
printf "${YESIL}==============================================================${SIFIR}\n"
printf "${YESIL} TESSERACT KURULUMU TAMAMLANDI!${SIFIR}\n"
printf "${YESIL}==============================================================${SIFIR}\n"
echo " Isterseniz ortam degiskeni tanimlayin:"
echo "   export TESSERACT_CMD=$TESSERACT_YOLU"
echo " Sonraki adim: python setup.py"
exit 0
