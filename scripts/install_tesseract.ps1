# ==============================================================================
# scripts/install_tesseract.ps1
# ------------------------------------------------------------------------------
# Windows uzerinde Tesseract OCR kurulum scripti.
#
# Yaptigi isler:
#   1. Tesseract zaten kurulu mu kontrol eder (varsa cikar)
#   2. winget ile kurmayi dener
#   3. winget yoksa/olmazsa chocolatey (choco) ile kurmayi dener
#   4. Kurulum yolunu PATH'e ekler
#   5. Kurulumu dogrular (tesseract --version, turkce/ingilizce dil paketi)
#
# Kullanim (PowerShell'i Yonetici olarak acin):
#   powershell -ExecutionPolicy Bypass -File scripts/install_tesseract.ps1
# ==============================================================================

$ErrorActionPreference = "Stop"

function Write-Step($mesaj) {
    Write-Host ""
    Write-Host "=== $mesaj ===" -ForegroundColor Cyan
}

function Write-Ok($mesaj) {
    Write-Host "[OK]  $mesaj" -ForegroundColor Green
}

function Write-Uyari($mesaj) {
    Write-Host "[!]   $mesaj" -ForegroundColor Yellow
}

function Write-Hata($mesaj) {
    Write-Host "[X]   $mesaj" -ForegroundColor Red
}

Write-Host "==============================================================" -ForegroundColor Magenta
Write-Host " TESSERACT OCR KURULUMU (Windows)" -ForegroundColor Magenta
Write-Host "==============================================================" -ForegroundColor Magenta

# ------------------------------------------------------------------------------
# 1) Zaten kurulu mu?
# ------------------------------------------------------------------------------
Write-Step "1/5 - Mevcut kurulum kontrol ediliyor"

$bulunanYol = $null
$adaylar = @(
    "C:\Program Files\Tesseract-OCR\tesseract.exe",
    "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "C:\Tesseract-OCR\tesseract.exe",
    "$env:LOCALAPPDATA\Programs\Tesseract-OCR\tesseract.exe",
    "$env:USERPROFILE\scoop\apps\tesseract\current\tesseract.exe"
)

foreach ($aday in $adaylar) {
    if (Test-Path $aday) {
        $bulunanYol = $aday
        break
    }
}

if (-not $bulunanYol) {
    $pathUzerinde = Get-Command tesseract -ErrorAction SilentlyContinue
    if ($pathUzerinde) {
        $bulunanYol = $pathUzerinde.Source
    }
}

if ($bulunanYol) {
    Write-Ok "Tesseract zaten kurulu: $bulunanYol"
    & $bulunanYol --version | Select-Object -First 1
    Write-Host "Kurulum atlandi." -ForegroundColor Green
    exit 0
}

Write-Uyari "Tesseract bulunamadi, kurulum baslatiliyor..."

# ------------------------------------------------------------------------------
# 2) winget ile kurulum
# ------------------------------------------------------------------------------
Write-Step "2/5 - winget ile kurulum deneniyor"

$wingetVar = Get-Command winget -ErrorAction SilentlyContinue
if ($wingetVar) {
    try {
        winget install --id UB-Mannheim.TesseractOCR -e --accept-source-agreements --accept-package-agreements --silent
        Write-Ok "winget kurulumu tamamlandi."
    }
    catch {
        Write-Uyari "winget kurulumu basarisiz: $_"
    }
}
else {
    Write-Uyari "winget bulunamadi (Windows 10 1809+ ve App Installer gerekir)."
}

# ------------------------------------------------------------------------------
# 3) Chocolatey ile kurulum (yedek yontem)
# ------------------------------------------------------------------------------
if (-not (Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe")) {
    Write-Step "3/5 - Chocolatey (choco) ile kurulum deneniyor"

    $chocoVar = Get-Command choco -ErrorAction SilentlyContinue
    if ($chocoVar) {
        try {
            choco install tesseract -y --no-progress
            Write-Ok "choco kurulumu tamamlandi."
        }
        catch {
            Write-Uyari "choco kurulumu basarisiz: $_"
        }
    }
    else {
        Write-Uyari "choco bulunamadi."
    }
}
else {
    Write-Ok "Tesseract kuruldu (winget)."
}

# ------------------------------------------------------------------------------
# 4) PATH'e ekle
# ------------------------------------------------------------------------------
Write-Step "4/5 - Kurulum yolu PATH'e ekleniyor"

$kurulumYolu = $null
foreach ($aday in $adaylar) {
    if (Test-Path $aday) {
        $kurulumYolu = $aday
        break
    }
}

if ($kurulumYolu) {
    $klasor = Split-Path $kurulumYolu -Parent
    $kullaniciPath = [Environment]::GetEnvironmentVariable("Path", "User")

    if ($kullaniciPath -notlike "*$klasor*") {
        [Environment]::SetEnvironmentVariable("Path", "$kullaniciPath;$klasor", "User")
        Write-Ok "PATH'e eklendi: $klasor"
    }
    else {
        Write-Ok "Klasor zaten PATH'te: $klasor"
    }

    $env:Path = "$env:Path;$klasor"
    $env:TESSERACT_CMD = $kurulumYolu
    [Environment]::SetEnvironmentVariable("TESSERACT_CMD", $kurulumYolu, "User")
    Write-Ok "TESSERACT_CMD ortam degiskeni ayarlandi: $kurulumYolu"
}
else {
    Write-Hata "Kurulum yolu bulunamadi! Kurulum basarisiz olmus olabilir."
    Write-Host "Manuel indirme: https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Yellow
    exit 1
}

# ------------------------------------------------------------------------------
# 5) Dogrulama
# ------------------------------------------------------------------------------
Write-Step "5/5 - Kurulum dogrulaniyor"

try {
    $surumCikti = & $kurulumYolu --version
    Write-Ok "Tesseract surumu: $($surumCikti[0])"

    $diller = & $kurulumYolu --list-langs 2>&1
    if ($diller -match "eng") {
        Write-Ok "Ingilizce (eng) dil paketi mevcut."
    }
    else {
        Write-Uyari "eng dil paketi bulunamadi! Dil paketlerini kurun."
    }
    if ($diller -match "tur") {
        Write-Ok "Turkce (tur) dil paketi mevcut."
    }

    Write-Host ""
    Write-Host "==============================================================" -ForegroundColor Green
    Write-Host " TESSERACT KURULUMU TAMAMLANDI!" -ForegroundColor Green
    Write-Host "==============================================================" -ForegroundColor Green
    Write-Host " Dogrulama icin yeni bir terminalde: tesseract --version" -ForegroundColor White
    Write-Host " Sonraki adim: python setup.py" -ForegroundColor White
}
catch {
    Write-Hata "Dogrulama basarisiz: $_"
    exit 1
}
