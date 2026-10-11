# ==============================================================================
# scripts/setup_adb.ps1
# ------------------------------------------------------------------------------
# Windows uzerinde Android Platform Tools (ADB) kurulum scripti.
#
# Yaptigi isler:
#   1. ADB zaten kurulu mu kontrol eder
#   2. Android Platform Tools'u indirir (Google'in resmi adresi)
#   3. C:\platform-tools klasorune cikarir
#   4. PATH'e ekler
#   5. adb devices ile test eder
#   6. LDPlayer'e baglanir: adb connect 127.0.0.1:5555
#
# Kullanim (PowerShell'i Yonetici olarak acin):
#   powershell -ExecutionPolicy Bypass -File scripts/setup_adb.ps1
# ==============================================================================

$ErrorActionPreference = "Stop"

function Write-Step($mesaj)  { Write-Host ""; Write-Host "=== $mesaj ===" -ForegroundColor Cyan }
function Write-Ok($mesaj)    { Write-Host "[OK]  $mesaj" -ForegroundColor Green }
function Write-Uyari($mesaj) { Write-Host "[!]   $mesaj" -ForegroundColor Yellow }
function Write-Hata($mesaj)  { Write-Host "[X]   $mesaj" -ForegroundColor Red }

$IndirmeUrl = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
$HedefKlasor = "C:\platform-tools"
$ZipDosya = Join-Path $env:TEMP "platform-tools.zip"
$LDPlayerPort = "127.0.0.1:5555"

Write-Host "==============================================================" -ForegroundColor Magenta
Write-Host " ADB (ANDROID PLATFORM TOOLS) KURULUMU (Windows)" -ForegroundColor Magenta
Write-Host "==============================================================" -ForegroundColor Magenta

# ------------------------------------------------------------------------------
# 1) Zaten kurulu mu?
# ------------------------------------------------------------------------------
Write-Step "1/6 - Mevcut ADB kontrol ediliyor"

$adbYolu = $null
$adaylar = @(
    "$HedefKlasor\adb.exe",
    "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe",
    "C:\LDPlayer\LDPlayer9\adb.exe",
    "C:\LDPlayer\LDPlayer4.0\adb.exe",
    "C:\Program Files\LDPlayer\adb.exe"
)
foreach ($aday in $adaylar) {
    if (Test-Path $aday) { $adbYolu = $aday; break }
}
if (-not $adbYolu) {
    $pathte = Get-Command adb -ErrorAction SilentlyContinue
    if ($pathte) { $adbYolu = $pathte.Source }
}

if ($adbYolu) {
    Write-Ok "ADB bulundu: $adbYolu"
    $env:ADB_PATH = $adbYolu
    [Environment]::SetEnvironmentVariable("ADB_PATH", $adbYolu, "User")
}
else {
    # --------------------------------------------------------------------------
    # 2) Indirme
    # --------------------------------------------------------------------------
    Write-Step "2/6 - Platform Tools indiriliyor"
    Write-Host " Kaynak: $IndirmeUrl"
    try {
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $IndirmeUrl -OutFile $ZipDosya -UseBasicParsing
        Write-Ok "Indirme tamamlandi: $ZipDosya"
    }
    catch {
        Write-Hata "Indirme basarisiz: $_"
        Write-Host " Manuel indirme: https://developer.android.com/studio/releases/platform-tools" -ForegroundColor Yellow
        exit 1
    }

    # --------------------------------------------------------------------------
    # 3) Cikartma
    # --------------------------------------------------------------------------
    Write-Step "3/6 - Dosyalar cikartiliyor"
    try {
        $geciciKlasor = Join-Path $env:TEMP "platform-tools-extract"
        if (Test-Path $geciciKlasor) { Remove-Item $geciciKlasor -Recurse -Force }
        Expand-Archive -Path $ZipDosya -DestinationPath $geciciKlasor -Force

        if (Test-Path $HedefKlasor) {
            Write-Uyari "$HedefKlasor zaten var, guncelleniyor..."
            Remove-Item $HedefKlasor -Recurse -Force
        }
        Move-Item -Path (Join-Path $geciciKlasor "platform-tools") -Destination $HedefKlasor
        Remove-Item $geciciKlasor -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item $ZipDosya -ErrorAction SilentlyContinue
        Write-Ok "Cikartildi: $HedefKlasor"
    }
    catch {
        Write-Hata "Cikartma basarisiz: $_"
        exit 1
    }

    $adbYolu = Join-Path $HedefKlasor "adb.exe"
}

# ------------------------------------------------------------------------------
# 4) PATH'e ekle
# ------------------------------------------------------------------------------
Write-Step "4/6 - PATH guncelleniyor"

$klasor = Split-Path $adbYolu -Parent
$kullaniciPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($kullaniciPath -notlike "*$klasor*") {
    [Environment]::SetEnvironmentVariable("Path", "$kullaniciPath;$klasor", "User")
    Write-Ok "PATH'e eklendi: $klasor"
}
else {
    Write-Ok "Klasor zaten PATH'te: $klasor"
}
$env:Path = "$env:Path;$klasor"
$env:ADB_PATH = $adbYolu
[Environment]::SetEnvironmentVariable("ADB_PATH", $adbYolu, "User")

# ------------------------------------------------------------------------------
# 5) Test: adb devices
# ------------------------------------------------------------------------------
Write-Step "5/6 - Baglanti testi (adb devices)"
try {
    & $adbYolu start-server
    Write-Host ""
    Write-Host " Bagli cihazlar:" -ForegroundColor White
    & $adbYolu devices -l
    Write-Ok "ADB sunucusu calisiyor."
}
catch {
    Write-Hata "adb devices basarisiz: $_"
    exit 1
}

# ------------------------------------------------------------------------------
# 6) LDPlayer'e baglan
# ------------------------------------------------------------------------------
Write-Step "6/6 - LDPlayer baglantisi ($LDPlayerPort)"
try {
    & $adbYolu connect $LDPlayerPort
    Write-Host ""
    Write-Host " ADB baglanti listesi:" -ForegroundColor White
    & $adbYolu devices -l

    Write-Host ""
    Write-Host "==============================================================" -ForegroundColor Green
    Write-Host " ADB KURULUMU TAMAMLANDI!" -ForegroundColor Green
    Write-Host "==============================================================" -ForegroundColor Green
    Write-Host " Kontrol listesi:" -ForegroundColor White
    Write-Host "   1. LDPlayer acik mi?" -ForegroundColor White
    Write-Host "   2. LDPlayer Ayarlar -> 'ADB Debug' (yerel baglanti) acik mi?" -ForegroundColor White
    Write-Host "   3. Bagli cihaz olarak 'emulator-5554' veya '$LDPlayerPort' gorunmeli" -ForegroundColor White
    Write-Host ""
    Write-Host " Sorun olursa:" -ForegroundColor Yellow
    Write-Host "   $adbYolu kill-server" -ForegroundColor Yellow
    Write-Host "   $adbYolu connect $LDPlayerPort" -ForegroundColor Yellow
    Write-Host ""
    Write-Host " Sonraki adim: python setup.py" -ForegroundColor White
}
catch {
    Write-Uyari "LDPlayer'e baglanilamadi: $_"
    Write-Host " LDPlayer'i acin ve tekrar deneyin: adb connect $LDPlayerPort" -ForegroundColor Yellow
    exit 0
}
