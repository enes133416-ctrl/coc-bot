# ==============================================================================
# scripts/install_ollama.ps1
# ------------------------------------------------------------------------------
# Windows uzerinde Ollama (yerel yapay zeka) kurulum scripti.
#
# Yaptigi isler:
#   1. Ollama zaten kurulu mu kontrol eder
#   2. OllamaSetup.exe dosyasini indirir (https://ollama.com/download/windows)
#   3. Sessiz kurulum yapar (/S parametresi)
#   4. PATH'i gunceller
#   5. Ollama servisini baslatir (ollama serve)
#   6. LLaVA 7B modelini indirir (ollama pull llava:7b)
#   7. Kurulumu dogrular (ollama list)
#
# Kullanim (PowerShell'i Yonetici olarak acin):
#   powershell -ExecutionPolicy Bypass -File scripts/install_ollama.ps1
#
# Not: Model indirme islemi ~4.7 GB yer kaplar ve internet gerektirir.
#      Internet olmadan bot calisir ancak yerel AI ozellikleri kullanilamaz.
# ==============================================================================

$ErrorActionPreference = "Stop"

function Write-Step($mesaj)  { Write-Host ""; Write-Host "=== $mesaj ===" -ForegroundColor Cyan }
function Write-Ok($mesaj)    { Write-Host "[OK]  $mesaj" -ForegroundColor Green }
function Write-Uyari($mesaj) { Write-Host "[!]   $mesaj" -ForegroundColor Yellow }
function Write-Hata($mesaj)  { Write-Host "[X]   $mesaj" -ForegroundColor Red }

$ModelAdi = "llava:7b"
$IndirmeUrl = "https://ollama.com/download/OllamaSetup.exe"
$GeciciDosya = Join-Path $env:TEMP "OllamaSetup.exe"

Write-Host "==============================================================" -ForegroundColor Magenta
Write-Host " OLLAMA + LLaVA KURULUMU (Windows)" -ForegroundColor Magenta
Write-Host "==============================================================" -ForegroundColor Magenta

# ------------------------------------------------------------------------------
# 1) Zaten kurulu mu?
# ------------------------------------------------------------------------------
Write-Step "1/6 - Mevcut kurulum kontrol ediliyor"

$ollamaYolu = $null
$adaylar = @(
    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
    "$env:ProgramFiles\Ollama\ollama.exe"
)
foreach ($aday in $adaylar) {
    if (Test-Path $aday) { $ollamaYolu = $aday; break }
}
if (-not $ollamaYolu) {
    $pathte = Get-Command ollama -ErrorAction SilentlyContinue
    if ($pathte) { $ollamaYolu = $pathte.Source }
}

if ($ollamaYolu) {
    Write-Ok "Ollama zaten kurulu: $ollamaYolu"
    & $ollamaYolu --version
}
else {
    # --------------------------------------------------------------------------
    # 2) Indirme
    # --------------------------------------------------------------------------
    Write-Step "2/6 - Ollama indiriliyor"
    Write-Host " Kaynak: $IndirmeUrl"

    try {
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $IndirmeUrl -OutFile $GeciciDosya -UseBasicParsing
        Write-Ok "Indirme tamamlandi: $GeciciDosya"
    }
    catch {
        Write-Hata "Indirme basarisiz: $_"
        Write-Host " Manuel indirme: https://ollama.com/download/windows" -ForegroundColor Yellow
        exit 1
    }

    # --------------------------------------------------------------------------
    # 3) Sessiz kurulum
    # --------------------------------------------------------------------------
    Write-Step "3/6 - Ollama kuruluyor (sessiz kurulum)"
    try {
        Start-Process -FilePath $GeciciDosya -ArgumentList "/S" -Wait
        Write-Ok "Kurulum tamamlandi."
        Start-Sleep -Seconds 5
    }
    catch {
        Write-Hata "Kurulum basarisiz: $_"
        exit 1
    }

    Remove-Item $GeciciDosya -ErrorAction SilentlyContinue

    foreach ($aday in $adaylar) {
        if (Test-Path $aday) { $ollamaYolu = $aday; break }
    }
}

if (-not $ollamaYolu) {
    Write-Hata "Ollama kurulum yolu bulunamadi!"
    exit 1
}

# ------------------------------------------------------------------------------
# 4) PATH guncelleme
# ------------------------------------------------------------------------------
Write-Step "4/6 - PATH guncelleniyor"

$klasor = Split-Path $ollamaYolu -Parent
$kullaniciPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($kullaniciPath -notlike "*$klasor*") {
    [Environment]::SetEnvironmentVariable("Path", "$kullaniciPath;$klasor", "User")
    Write-Ok "PATH'e eklendi: $klasor"
}
else {
    Write-Ok "Klasor zaten PATH'te: $klasor"
}
$env:Path = "$env:Path;$klasor"

# ------------------------------------------------------------------------------
# 5) Servisi baslat + modeli indir
# ------------------------------------------------------------------------------
Write-Step "5/6 - Ollama servisi baslatiliyor"

$servisCalisiyor = $false
try {
    $yanit = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 5
    if ($yanit.StatusCode -eq 200) {
        $servisCalisiyor = $true
        Write-Ok "Ollama servisi zaten calisiyor (port 11434)."
    }
}
catch {
    Write-Uyari "Servis yanit vermiyor, arka planda baslatiliyor..."
}

if (-not $servisCalisiyor) {
    Start-Process -FilePath $ollamaYolu -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 8
    try {
        $yanit = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 10
        $servisCalisiyor = ($yanit.StatusCode -eq 200)
    }
    catch {
        $servisCalisiyor = $false
    }
}

if ($servisCalisiyor) {
    Write-Ok "Ollama servisi calisiyor: http://localhost:11434"
}
else {
    Write-Uyari "Servis dogrulanamadi. 'ollama serve' komutunu elle calistirin."
}

Write-Host ""
Write-Host " $ModelAdi modeli indiriliyor (yaklasik 4.7 GB, birkac dakika surebilir)..." -ForegroundColor Yellow
try {
    & $ollamaYolu pull $ModelAdi
    Write-Ok "$ModelAdi modeli indirildi."
}
catch {
    Write-Uyari "Model indirilemedi: $_"
    Write-Host " Sonra elle deneyin: ollama pull $ModelAdi" -ForegroundColor Yellow
}

# ------------------------------------------------------------------------------
# 6) Dogrulama
# ------------------------------------------------------------------------------
Write-Step "6/6 - Kurulum dogrulaniyor"

try {
    & $ollamaYolu --version
    Write-Host ""
    Write-Host " Kurulu modeller:" -ForegroundColor White
    & $ollamaYolu list

    Write-Host ""
    Write-Host "==============================================================" -ForegroundColor Green
    Write-Host " OLLAMA KURULUMU TAMAMLANDI!" -ForegroundColor Green
    Write-Host "==============================================================" -ForegroundColor Green
    Write-Host " Test icin: ollama run $ModelAdi 'merhaba'" -ForegroundColor White
    Write-Host " Sonraki adim: python setup.py" -ForegroundColor White
}
catch {
    Write-Hata "Dogrulama basarisiz: $_"
    exit 1
}
