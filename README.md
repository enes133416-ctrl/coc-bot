<div align="center">

# 🤖 Clash of Clans Yerel AI Bot

**%100 Yerel Çalışan, API Gerektirmeyen CoC Botu**

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.9-green.svg)](https://opencv.org/)
[![Tesseract](https://img.shields.io/badge/Tesseract-OCR-orange.svg)](https://github.com/tesseract-ocr/tesseract)
[![Ollama](https://img.shields.io/badge/Ollama-LLaVA%207B-purple.svg)](https://ollama.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

OpenCV • Tesseract OCR • ADB • Ollama + LLaVA 7B

</div>

---

## 📖 1. Proje Açıklaması

Bu proje, **Clash of Clans** oyununu LDPlayer (veya benzeri bir Android emülatörü) üzerinde oynayan; tamamen **yerel** çalışan, **hiçbir bulut API'si kullanmayan** bir bottur.

### ✨ Özellikler

| Özellik | Teknoloji | Açıklama |
|---|---|---|
| 🖱️ Buton Tespiti | OpenCV Template Matching | 13 farklı ölçekte (0.7-1.3) arama + ölçek önbelleği |
| 🔢 Loot Okuma | Tesseract OCR | Altın/iksir/kara iksir sayılarını okur (CLAHE + Otsu ön işleme) |
| 📱 Emülatör Kontrolü | ADB | Dokunma, kaydırma, uzun basma, ekran görüntüsü |
| 🧠 Yerel AI | Ollama + LLaVA 7B | Üs analizi, ekran doğrulama, strateji önerisi |
| 🎯 Loot Filtresi | Python | 1.6M toplam loot kuralı (altın ≥ 600K, iksir ≥ 600K) |
| 🎬 Savaş Planı | JSON | Saldırıyı kaydet, aynı zamanlamayla tekrar oynat |
| 📊 Veri Toplama | SQLite/JSON | Her eylem, loot kontrolü ve hata loglanır |
| 🤖 Hata Analizi | JSON Export | Hatalar AI'a hazır prompt olarak dışa aktarılır |

### 🔄 Çalışma Döngüsü

```
      ┌──────────────────────────────────────────────────┐
      │                                                  │
      ▼                                                  │
   ┌──────┐   saldır butonu   ┌───────────────┐          │
   │ HOME │─────────────────▶ │ FINDING_MATCH │          │
   └──────┘                   └───────┬───────┘          │
      ▲                               │ rakip bulundu    │
      │                               ▼                  │
      │                       ┌───────────────┐          │
      │        loot yetersiz  │   SCOUTING    │          │
      │        ◀──────────────┤  (OCR + filtre)│         │
      │        "Sonraki" tuşu └───────┬───────┘          │
      │                               │ loot yeterli ✅  │
      │                               ▼                  │
      │                       ┌───────────────┐          │
      │                       │   ATTACKING   │          │
      │                       │ (plan oynat)  │          │
      │                       └───────┬───────┘          │
      │                               ▼                  │
      │                       ┌───────────────┐          │
      │                       │  WAITING_END  │          │
      │                       └───────┬───────┘          │
      │                               ▼                  │
      │                       ┌───────────────┐          │
      └───────────────────────┤   RETURNING   │          │
            4 sn bekle        └───────────────┘          │
                                                         │
                    hata olursa → ERROR → _recover() ────┘
```

### 📁 Proje Yapısı

```
coc_bot/
├── .github/workflows/setup_and_run.yml   # GitHub Actions (otomatik kurulum + test)
├── core/
│   ├── adb_controller.py                 # ADB bağlantı ve tıklama
│   ├── screen_capture.py                 # Ekran yakalama (önbellekli)
│   ├── vision_engine.py                  # OpenCV template matching (13 ölçek)
│   ├── ocr_engine.py                     # Tesseract OCR + kalibrasyon
│   └── state_machine.py                  # Bot durum makinesi
├── modules/
│   ├── scout_filter.py                   # 1.6M loot filtresi
│   ├── attack_planner.py                 # Savaş planı kaydet/oynat
│   └── error_handler.py                  # Hata yönetimi + öneri motoru
├── ai/local_vision.py                    # Ollama + LLaVA yerel AI
├── data_collector/
│   ├── logger.py                         # Oturum bazlı loglama
│   └── export_for_ai.py                  # AI için veri dışa aktarma
├── assets/templates/                     # 👈 BURAYA template görselleri!
├── data/                                 # Oturumlar, hatalar, planlar
├── tests/                                # pytest birim testleri
├── scripts/                              # Kurulum scriptleri (ps1/sh)
├── main.py                               # Ana menü
├── config.py                             # ⚙️ TÜM AYARLAR
├── calibrate.py                          # OCR/Vision kalibrasyon aracı
├── setup.py                              # Kurulum scripti
└── requirements.txt
```

---

## 📋 2. Gereksinimler

### Zorunlu

| Yazılım | Sürüm | Ne İçin? | İndirme |
|---|---|---|---|
| **Python** | 3.11+ | Botun kendisi | https://www.python.org/downloads/ |
| **LDPlayer** | 9.x | Android emülatörü | https://www.ldplayer.net/ |
| **ADB** | Platform Tools | Emülatör kontrolü | https://developer.android.com/studio/releases/platform-tools |
| **Tesseract OCR** | 5.x | Loot sayılarını okuma | https://github.com/UB-Mannheim/tesseract/wiki |

### Opsiyonel (yerel AI için)

| Yazılım | Sürüm | Ne İçin? | İndirme |
|---|---|---|---|
| **Ollama** | 0.1.x+ | Yerel AI sunucusu | https://ollama.com/download |
| **LLaVA model** | llava:7b | Görsel analiz (~4.7 GB) | `ollama pull llava:7b` |

> 💡 **Ollama olmadan da bot çalışır!** Sadece AI destekli analizler atlanır.
> `config.py` → `USE_LOCAL_AI = False` yapmanız yeterli.

### Sistem Gereksinimleri

- **İşletim Sistemi:** Windows 10/11 (önerilen), Linux, macOS
- **RAM:** 8 GB (LLaVA 7B için 16 GB önerilir)
- **Disk:** 5 GB (Ollama modeli dahil)
- **Ekran:** 1600x900 çözünürlük önerilir (LDPlayer varsayılanı)

### LDPlayer Ayarları (ÖNEMLİ!)

1. LDPlayer'ı aç → **Ayarlar** (⚙️)
2. **Diğer Ayarlar** sekmesine gel
3. ✅ **"ADB Debug"** (yerel bağlantı) seçeneğini **AÇ**
4. LDPlayer'ı yeniden başlat
5. Çözünürlüğü **1600x900** yap (Ayarlar → Ekran)

---

## 🚀 3. GitHub Actions ile Kurulum (Önerilen)

Bu yöntemde **tek bir kod yazmanıza gerek yok** — sadece push edip Actions'ı çalıştırıyorsunuz.

### Adım 1: Kodu GitHub'a Push Edin

```bash
git add .
git commit -m "Clash of Clans yerel AI bot"
git push origin main
```

### Adım 2: Actions Sekmesine Gidin

GitHub deponuzda üst menüden **"Actions"** sekmesine tıklayın.

```
┌──────────────────────────────────────────────────────────┐
│  <> Code   ● Issues   ⑂ Pull requests   ▶ Actions   ...  │
└──────────────────────────────────────────────────────────┘
                                          ▲
                                     BURAYA TIKLA
```

### Adım 3: Workflow'u Seçin

Sol kenar çubuğunda **"🤖 CoC Bot Setup & Test"** workflow'una tıklayın.

```
Sol Menü:
  ├─ All workflows
  ├─ 🤖 CoC Bot Setup & Test     ◀── BUNU SEÇ
  └─ (diğerleri)
```

### Adım 4: Manuel Çalıştırın

Sağ üstteki **"Run workflow"** butonuna tıklayın:

```
┌─────────────────────────────────────────┐
│  Run workflow  ▼                        │
│  ┌───────────────────────────────────┐  │
│  │ Use workflow from: main    ▼      │  │
│  │ 🎯 mode:  [test          ▼]       │  │  ← test/setup/lint
│  │ 🐍 python_version: [3.11 ]        │  │  ← 3.11 önerilir
│  │                                   │  │
│  │        [ Run workflow ]           │  │  ← YEŞİL BUTON
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

**Mod seçenekleri:**

| Mod | Ne Yapar? |
|---|---|
| `test` (varsayılan) | Kurulum + tüm testler + kod stili kontrolü |
| `setup` | Sadece kurulum ve doğrulama |
| `lint` | Sadece flake8 kod stili kontrolü |

### Adım 5: Sonuçları İzleyin

Workflow çalışmaya başlar. Her adımın yanında ✅ veya ❌ görürsünüz:

```
🤖 CoC Bot Setup & Test  #12
├─ ✅ 🛠️ 1. Kurulum (Windows + Tesseract + Python)    2m 14s
├─ ✅ 🧪 2. Testler (pytest)                          1m 07s
└─ ✅ 🔍 3. Kod stili kontrolü (flake8)                 31s
```

### Adım 6: Test Sonuçlarını İndirin

Test job'u bittiğinde sayfanın altında **"Artifacts"** bölümü görünür:

```
Artifacts
  📦 pytest-results-windows         ⬇️ İndir
```

İndirdiğiniz klasörde:
- `results.xml` — detaylı test sonuçları
- `tests/` — test dosyalarının kopyası

### Adım 7 (Opsiyonel): Kendi Bilgisayarınızda Kurulum

Actions sadece **kodun doğruluğunu** test eder. Botu gerçekten oynatmak için kendi bilgisayarınıza kurmanız gerekir → **Bölüm 4'e geçin**.

---

## 💻 4. Manuel Kurulum Adımları

### Windows (Önerilen)

```powershell
# 1. PowerShell'i YÖNETİCİ olarak açın

# 2. Projeyi klonlayın
git clone https://github.com/enes133416-ctrl/coc-bot.git
cd coc-bot

# 3. Tesseract OCR kurun
powershell -ExecutionPolicy Bypass -File scripts/install_tesseract.ps1

# 4. ADB kurun ve LDPlayer'e bağlanın
powershell -ExecutionPolicy Bypass -File scripts/setup_adb.ps1

# 5. (Opsiyonel) Ollama + LLaVA kurun
powershell -ExecutionPolicy Bypass -File scripts/install_ollama.ps1

# 6. Python bağımlılıklarını kurun ve yapıyı hazırlayın
python setup.py
```

### Linux / macOS

```bash
# 1. Projeyi klonlayın
git clone https://github.com/enes133416-ctrl/coc-bot.git
cd coc-bot

# 2. Tesseract kurun
bash scripts/install_tesseract.sh

# 3. ADB kurun
sudo apt-get install -y android-tools-adb          # Ubuntu/Debian
# brew install android-platform-tools              # macOS

# 4. (Opsiyonel) Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llava:7b

# 5. Python bağımlılıkları
python3 -m pip install -r requirements.txt
python3 setup.py
```

### Beklenen `setup.py` Çıktısı

```
==============================================================
 Clash of Clans Yerel AI Bot v1.0.0 - KURULUM
==============================================================
 Python     : 3.11.9  (C:\python311\python.exe)
 Isletim S. : Windows 10

=== 1/7 - PYTHON BAGIMLILIKLARI KURULUYOR ===
[OK]  Bagimliliklar basariyla kuruldu.

=== 2/7 - TESSERACT OCR KONTROLU ===
[OK]  Tesseract bulundu -> C:\Program Files\Tesseract-OCR\tesseract.exe
      Surum: tesseract 5.3.3

=== 3/7 - OLLAMA (YEREL AI) KONTROLU ===
[OK]  Ollama bulundu -> C:\Users\...\Ollama\ollama.exe

=== 4/7 - ADB (ANDROID DEBUG BRIDGE) KONTROLU ===
[OK]  ADB bulundu -> C:\platform-tools\adb.exe

=== 5/7 - KLASOR YAPISI OLUSTURULUYOR ===
[OK]  .../data/sessions

=== 6/7 - SAVAS PLANI DOSYASI ===
[OK]  Bos plan dosyasi olusturuldu -> data/battle_plans.json

=== 7/7 - TEMPLATE DOSYALARI KONTROLU ===
[--]  attack_button      -> attack_button.png (EKSIK)
...

 KURULUM OZETI
 [OK]  Python bagimliliklari
 [OK]  Tesseract OCR
 [!!]  Template dosyalari   ->  assets/templates/ (0/10)

 SONRAKI ADIMLAR:
   1. LDPlayer'i acin ve Clash of Clans'i baslatin
   2. ADB baglantisi: adb connect 127.0.0.1:5555
   3. Buton template'lerini assets/templates/ klasorune ekleyin
   4. Kalibrasyon: python calibrate.py
   5. Botu baslatin: python main.py
```

> ⚠️ **Template uyarısı normaldir!** Botun çalışması için `assets/templates/` klasörüne buton görsellerini eklemeniz gerekir. Detaylar: [`assets/templates/README.md`](assets/templates/README.md)

---

## 🎮 5. İlk Çalıştırma

```bash
python main.py
```

Karşınıza çıkan menü:

```
   ______      ______        ______         __
  / ____/___  / ____/       / __ )____     / /_
 / /   / __ \/ /           / __  / __ \   / __/
/ /___/ /_/ / /___        / /_/ / /_/ /  / /_
\____/\____/\____/        \____/\____/   \__/

   Clash of Clans  -  YEREL AI BOT  (API YOK, %100 Cevrimdisi)

 ANA MENU
 ----------------------------------------
  [1] Bot'u baslat
  [2] Savas plani kaydet
  [3] OCR kalibre et / template test et
  [4] Testleri calistir (pytest)
  [5] Hatalari AI icin disa aktar
  [6] Cikis
 ----------------------------------------
```

### İlk Kez Çalıştırma Sırası

```
1. LDPlayer'ı aç + Clash of Clans'ı başlat
        ▼
2. python setup.py               (kurulum kontrolü)
        ▼
3. python calibrate.py           [4] ADB bağlantısını test et
        ▼
4. Template görsellerini ekle    assets/templates/README.md
        ▼
5. python calibrate.py           [5] Tüm template'leri test et
        ▼
6. python calibrate.py           [1] OCR bölgelerini kalibre et
        ▼
7. python main.py                [2] Savaş planı kaydet
        ▼
8. python main.py                [1] Bot'u başlat! 🚀
```

### Bot'u Durdurma

Bot çalışırken **`Ctrl + C`** tuşlarına basın. Bot:
1. Mevcut işlemi bitirir
2. Tüm oturum verisini `data/sessions/YYYYMMDD_HHMMSS/` klasörüne kaydeder
3. `ai_export.json` dosyasını oluşturur
4. Özet istatistikleri gösterir

---

## 🎬 6. Savaş Planı Kayıt Rehberi

Savaş planı, saldırıdaki **her dokunuşu ve zamanlamasını** kaydeder. Bot daha sonra bu planı birebir tekrarlar.

### Kayıt Adımları

```bash
python main.py
# [2] Savas plani kaydet seç
```

```
 Plan adi (orn. koy_saldirisi): ejder_saldirisi

 [PLAN] KAYIT BASLADI -> 'ejder_saldirisi'

 Koordinat girin: 'x,y' (orn. 800,450)
 Eylem tipi : tap / swipe / long_press / key / wait
 Bitirmek   : 'bitti' yazin

 [1] x,y (veya 'bitti'): 800,450
 Eylem tipi (tap/swipe/long_press/key/wait) [tap]: tap
 Etiket (orn. ejder birak): sol_kanat_ejder
 [PLAN] + Kayit #1 | t=0.00s | tap (800,450) sol_kanat_ejder

 [2] x,y (veya 'bitti'): 950,450
 Eylem tipi [tap]: tap
 Etiket: orta_ejder
 [PLAN] + Kayit #2 | t=3.21s | tap (950,450) orta_ejder

 [3] x,y (veya 'bitti'): bitti
[OK]  [PLAN] 'ejder_saldirisi' kaydedildi -> 2 hareket, 5.4 saniye
```

### Eylem Tipleri

| Tip | Açıklama | Ek Bilgi |
|---|---|---|
| `tap` | Tek dokunma | x, y |
| `swipe` | Kaydırma | x, y + x2, y2 + süre (ms) |
| `long_press` | Uzun basma | x, y + süre (ms) |
| `key` | Tuş olayı | keycode (4 = geri, 3 = home) |
| `wait` | Sadece bekleme | saniye |

### ⏱️ Zamanlama Nasıl Çalışır?

Kayıt sırasında her hareketin **kayıttan bu yana geçen süresi** (`t=3.21s`) saklanır. Oynatma sırasında bot bu süreleri bekleyerek aynı ritmi yakalar.

```
Kayıt:   [tap 800,450] --- 3.21s --- [tap 950,450] --- 2.19s --- [tap 1100,500]
Oynatma: [tap 800,450] --- 3.21s --- [tap 950,450] --- 2.19s --- [tap 1100,500]
                              ▲
                   speed=1.0 ise birebir aynı
                   speed=2.0 ise yarı sürede (1.6s / 1.1s)
```

### Piton Koordinatlarını Nasıl Bulurum?

**Yöntem 1 — Kalibrasyon aracı:**
```bash
python calibrate.py    # [2] Template matching test et → debug görselinde koordinatlar yazılı
```

**Yöntem 2 — Python ile:**
```python
import cv2
gorsel = cv2.imread("data/screenshots/ekran.png")
print("Ekran boyutu:", gorsel.shape[1], "x", gorsel.shape[0])

def tikla_koordinat(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"TIKLADINIZ: {x},{y}")

cv2.imshow("Koordinat Bul", gorsel)
cv2.setMouseCallback("Koordinat Bul", tikla_koordinat)
cv2.waitKey(0)
```

**Yöntem 3 — Canlı kayıt:** Kayıt modunda "emülatöre de göndersin mi? (e/h)" sorusuna **e** derseniz, girdiğiniz koordinatlar anında emülatörde uygulanır ve doğru yere tıklayıp tıklamadığınızı görürsünüz.

### Plan Yönetimi

```python
from modules.attack_planner import AttackPlanner

planner = AttackPlanner()
planner.list_plans()                        # Tüm planları tablo halinde göster
planner.delete_plan("eski_plan")            # Plan sil
planner.export_plan("ejder_saldirisi")      # Ayrı dosyaya aktar
planner.import_plan("baska_bot_plani.json") # Dışarıdan plan yükle
planner.backup_plans()                      # Yedek al
```

### Planı Aktif Etme

`config.py` dosyasında:
```python
ACTIVE_PLAN = "ejder_saldirisi"    # bot bu planı oynatacak
PLAYBACK_SPEED = 1.0               # 1.0 = orijinal hız
```

---

## 🔍 7. OCR Kalibrasyon Rehberi

Bot, loot değerlerini ekranda **belirli bölgelerden** okur. Bu bölgeler `config.py` içindeki `OCR_REGIONS` sözlüğünde tanımlıdır (1600x900 varsayılanıyla gelir).

### Varsayılan Bölgeler (1600x900)

```
┌────────────────────────────────────────────────────────────┐
│  ┌────────┐  ┌────────┐  ┌──────┐                          │
│  │ GOLD   │  │ ELIXIR │  │ DARK │   ← y=38, h=44           │
│  │ x=56   │  │ x=300  │  │x=544 │                          │
│  └────────┘  └────────┘  └──────┘                          │
│                                                            │
│                                                            │
│                     (oyun ekranı)                          │
│                                                            │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Kalibrasyon Adımları

```bash
python calibrate.py
# [1] OCR bolgelerini kalibre et
```

Açılan OpenCV penceresinde:

| Tuş | İşlev |
|---|---|
| `1` | Altın (gold) bölgesini seç |
| `2` | İksir (elixir) bölgesini seç |
| `3` | Kara iksir (dark) bölgesini seç |
| Trackbar: **X, Y, W, H** | Seçili bölgeyi kaydır/boyutlandır |
| `s` | Seçili bölgeyi kaydet (JSON'a yazar + config kodu basar) |
| `a` | Tüm bölgelerin koordinatlarını konsola yaz |
| `q` / `ESC` | Çıkış |

### Neye Dikkat Etmelisiniz?

✅ **Doğru:** Kutular sayıların **tam üzerine** oturuyor, rakamların kenarları kesilmiyor
❌ **Yanlış:** Kutu sayıların yarısını alıyor → OCR yanlış okur
❌ **Yanlış:** Kutu çok büyük, ikonlar/arka plan da içeride → OCR karışır

### Kalibrasyon Sonrası

Araç size `config.py`'ye yapıştıracağınız kodu gösterir:

```python
OCR_REGIONS: Dict[str, Dict[str, int]] = {
    "gold": {"x": 62, "y": 41, "w": 210, "h": 40},
    "elixir": {"x": 308, "y": 41, "w": 210, "h": 40},
    "dark": {"x": 550, "y": 41, "w": 190, "h": 40},
}
```

Bu bloğu kopyalayıp `config.py` içindeki aynı isimli sözlüğün üzerine yazın. Kalibrasyon verisi ayrıca `data/ocr_regions_calibrated.json` dosyasına da kaydedilir.

### OCR'ı Test Etme

```bash
python calibrate.py    # [1] sonra konsolda test
# veya doğrudan:
python -c "import sys; sys.path.insert(0,'.'); from core.ocr_engine import OCREngine; print(OCREngine().test_ocr('data/screenshots/ekran.png'))"
```

Beklenen çıktı:
```
======================================================================
 OCR TEST SONUCLARI
======================================================================
 [       OK] gold        =      874,320   bolge={'x': 62, 'y': 41, 'w': 210, 'h': 40}
 [       OK] elixir      =      912,105   bolge={'x': 308, 'y': 41, 'w': 210, 'h': 40}
 [       OK] dark        =        3,412   bolge={'x': 550, 'y': 41, 'w': 190, 'h': 40}
----------------------------------------------------------------------
 TOPLAM DEGER: 2,127,625
 Filtre esigi: 1,600,000
 Karar       : SALDIR
======================================================================
```

### Farklı Çözünürlükler

Bot, farklı çözünürlüklerde bölgeleri **otomatik ölçekler** (`AUTO_SCALE_REGIONS = True`). Yine de en doğru sonuç için:

```python
# config.py
SCREEN_WIDTH = 1600      # gerçek ekran genişliğiniz
SCREEN_HEIGHT = 900      # gerçek ekran yüksekliğiniz
```
ve ardından `calibrate.py` ile yeni koordinatları kalibre edin.

---

## ⚙️ 8. config.py Ayarları Tablosu

### Loot Filtresi

| Ayar | Varsayılan | Açıklama |
|---|---|---|
| `MIN_TOTAL_LOOT` | `1_600_000` | Minimum toplam loot (altın + iksir + kara×100) |
| `MIN_GOLD` | `600_000` | Minimum altın |
| `MIN_ELIXIR` | `600_000` | Minimum iksir |
| `MIN_DARK` | `0` | Minimum kara iksir (0 = şart yok) |
| `DARK_ELIXIR_MULTIPLIER` | `100.0` | 1 kara iksir kaç altın/iksir değerinde |

### Görüntü İşleme

| Ayar | Varsayılan | Açıklama |
|---|---|---|
| `TEMPLATE_THRESHOLD` | `0.82` | Minimum eşleşme skoru (düşür = daha esnek, yükselt = daha katı) |
| `MULTI_SCALE_ENABLED` | `True` | 13 farklı ölçekte arama yap |
| `SCALE_MIN` / `SCALE_MAX` | `0.7` / `1.3` | Ölçek aralığı |
| `SCALE_STEPS` | `13` | Denenecek ölçek sayısı |
| `TEMPLATE_WAIT_TIMEOUT` | `60` | Template bekleme zaman aşımı (sn) |
| `TEMPLATE_WAIT_INTERVAL` | `1.5` | Kontroller arası bekleme (sn) |
| `DEBUG_DRAW_ENABLED` | `True` | Debug görselleri kaydet |

### ADB

| Ayar | Varsayılan | Açıklama |
|---|---|---|
| `ADB_SERIAL` | `"emulator-5554"` | Hedef cihaz seri numarası |
| `ADB_CONNECT_ADDRESS` | `"127.0.0.1:5555"` | TCP bağlantı adresi (LDPlayer) |
| `ADB_TIMEOUT` | `20` | Komut zaman aşımı (sn) |
| `ADB_DEFAULT_TAP_DELAY` | `0.3` | Tıklama sonrası bekleme (sn) |

### Yerel AI

| Ayar | Varsayılan | Açıklama |
|---|---|---|
| `USE_LOCAL_AI` | `True` | `False` = AI tamamen devre dışı |
| `OLLAMA_URL` | `"http://localhost:11434"` | Ollama sunucu adresi |
| `OLLAMA_MODEL` | `"llava:7b"` | Kullanılacak model |
| `OLLAMA_TIMEOUT` | `60` | İstek zaman aşımı (sn) |

### Bot Davranışı

| Ayar | Varsayılan | Açıklama |
|---|---|---|
| `ACTIVE_PLAN` | `"varsayilan"` | Oynatılacak savaş planı |
| `BATTLE_TIMEOUT` | `180` | Savaş bitişi bekleme süresi (sn) |
| `PLAYBACK_SPEED` | `1.0` | Plan oynatma hızı |
| `STATE_LOOP_DELAY` | `1.0` | Durumlar arası bekleme (sn) |
| `HOME_WAIT_TIMEOUT` | `45` | Ana ekran bekleme (sn) |
| `FIND_MATCH_TIMEOUT` | `60` | Eşleşme bekleme (sn) |
| `MAX_SKIPS_PER_CYCLE` | `40` | Art arda maksimum atlama |
| `RETURN_HOME_WAIT` | `4.0` | Eve dönüş beklemesi (sn) |
| `DRY_RUN` | `False` | `True` = gerçekten tıklama (test için) |

### Ekran ve Log

| Ayar | Varsayılan | Açıklama |
|---|---|---|
| `SCREEN_WIDTH` / `SCREEN_HEIGHT` | `1600` / `900` | Referans çözünürlük |
| `AUTO_SCALE_REGIONS` | `True` | Bölgeleri otomatik ölçekle |
| `SAVE_SCREENSHOTS` | `True` | Eylemlerde ekran görüntüsü sakla |
| `LOG_ALL_ACTIONS` | `True` | Her eylemi JSON'a kaydet |
| `LOG_TO_FILE` | `True` | `bot.log` dosyasına yaz |
| `SESSION_PREFIX` | `"session"` | Oturum klasörü ön eki |

### Örnek: Daha Agresif Filtre

```python
# Sadece zengin köylere saldır
MIN_TOTAL_LOOT = 2_500_000
MIN_GOLD = 1_000_000
MIN_ELIXIR = 1_000_000
MIN_DARK = 5_000
MAX_SKIPS_PER_CYCLE = 80     # daha çok rakip atla
```

### Örnek: Hızlı ve Toleranslı Bot

```python
TEMPLATE_THRESHOLD = 0.75    # daha esnek eşleşme
TEMPLATE_WAIT_INTERVAL = 1.0 # daha sık kontrol
STATE_LOOP_DELAY = 0.5       # daha hızlı döngü
MAX_SKIPS_PER_CYCLE = 20     # daha az atla
```

---

## 🛠️ 9. Sık Karşılaşılan Sorunlar ve Çözümleri

### 🔌 Bağlantı Sorunları

<details>
<summary><b>❌ "Cihaz bagli degil" / adb devices boş dönüyor</b></summary>

**Çözüm 1:** LDPlayer ayarlarını kontrol edin
```
LDPlayer → Ayarlar (⚙️) → Diğer Ayarlar → ✅ "ADB Debug" açık olmalı
```

**Çözüm 2:** ADB sunucusunu yeniden başlatın
```bash
adb kill-server
adb start-server
adb connect 127.0.0.1:5555
adb devices
```

**Çözüm 3:** Farklı portlar deneyin (LDPlayer sürümüne göre değişir)
```bash
adb connect 127.0.0.1:5555   # LDPlayer 9
adb connect 127.0.0.1:5557   # LDPlayer 4 (bazı sürümler)
adb connect 127.0.0.1:62001  # Nox
```

**Çözüm 4:** LDPlayer'ı yeniden başlatın ve tekrar deneyin.

</details>

<details>
<summary><b>❌ "ADB calistirilabilir dosyasi bulunamadi"</b></summary>

```powershell
# Windows:
powershell -ExecutionPolicy Bypass -File scripts/setup_adb.ps1

# Manuel kontrol:
where adb
```

ADB yoksa: https://developer.android.com/studio/releases/platform-tools adresinden indirin,
`C:\platform-tools` klasörüne çıkarın ve PATH'e ekleyin.

</details>

### 🔤 Tesseract / OCR Sorunları

<details>
<summary><b>❌ "Tesseract calistirilamadi"</b></summary>

```powershell
# Kurulum:
powershell -ExecutionPolicy Bypass -File scripts/install_tesseract.ps1

# Doğrulama:
tesseract --version
```

Manuel çözüm — `config.py`'ye tam yolu yazın:
```python
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

veya ortam değişkeni:
```cmd
set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

</details>

<details>
<summary><b>❌ OCR yanlış sayı okuyor (ör. 874320 → 87432 veya 0)</b></summary>

1. **Kalibrasyon yapın:** `python calibrate.py` → `[1]` → kutuları sayıların tam üzerine getirin
2. **Kutu boyutunu kontrol edin:** Rakamların tamamı kutunun içinde olmalı, kenarlardan kesilmemeli
3. **Ekran ölçeğini kontrol edin:** LDPlayer çözünürlüğü 1600x900 olmalı
4. `config.py` → `SCREEN_WIDTH` / `SCREEN_HEIGHT` değerlerini gerçek çözünürlükle eşleştirin

</details>

### 👁️ Template Sorunları

<details>
<summary><b>❌ "Template dosyasi bulunamadi: attack_button.png"</b></summary>

`assets/templates/` klasöründe gerekli PNG dosyaları yok. Detaylı rehber:
[`assets/templates/README.md`](assets/templates/README.md)

Hızlı özet:
1. Oyunu aç, ana köy ekranına gel
2. `Win + Shift + S` ile butonu kes
3. Paint → `Ctrl+V` → **PNG** olarak kaydet
4. Dosya adı **tam olarak** `attack_button.png` olmalı
5. `assets/templates/` klasörüne kopyala

</details>

<details>
<summary><b>❌ "Saldiri butonu bulunamadi" (template var ama bulunmuyor)</b></summary>

1. **Test edin:** `python calibrate.py` → `[5]` tüm template'leri test et
2. **Güven değerine bakın:**
   - `0.70 - 0.82 arası` → Eşiği düşürün: `TEMPLATE_THRESHOLD = 0.75`
   - `0.50'nin altı` → Template yanlış kesilmiş, yeniden kesin
3. **Doğru anda mı?** Buton pasifken (gri) kesilmiş olabilir — aktif halini kesin
4. **Debug görseline bakın:** `assets/debug/debug_*.png` dosyalarını açın

</details>

### 🧠 Ollama / AI Sorunları

<details>
<summary><b>❌ "Ollama servisine baglanilamadi"</b></summary>

```bash
# Servis çalışıyor mu?
curl http://localhost:11434/api/tags

# Başlatma:
ollama serve

# Windows'ta arka planda:
start /B ollama serve
```

Bot, Ollama olmadan da çalışır. AI özelliklerini kapatmak için:
```python
# config.py
USE_LOCAL_AI = False
```

</details>

<details>
<summary><b>❌ "llava:7b modeli bulunamadi"</b></summary>

```bash
ollama pull llava:7b        # ~4.7 GB indirir
ollama list                 # kurulu modelleri göster
```

Alternatif (daha küçük, daha hızlı):
```bash
ollama pull llava:13b       # daha kaliteli ama daha yavaş
```

</details>

### 🤖 Bot Davranışı Sorunları

<details>
<summary><b>❌ Bot sürekli rakip atlıyor (hiç saldırmıyor)</b></summary>

Eşikler çok yüksek olabilir:
```python
# config.py
MIN_TOTAL_LOOT = 1_200_000     # düşür
MIN_GOLD = 400_000
MIN_ELIXIR = 400_000
```

Veya OCR yanlış okuyordur → Bölüm 7'deki kalibrasyonu yapın.

</details>

<details>
<summary><b>❌ Bot takılıp kalıyor (aynı ekranda dönüyor)</b></summary>

1. **Template eksik olabilir:** `next_button.png` veya `return_home.png` yoksa bot ilerleyemez
2. **Manuel müdahale:** Ekranı elle değiştirin, bot `_recover()` ile toparlanacaktır
3. **Timeout ayarları:**
```python
BATTLE_TIMEOUT = 240        # savaş bekleme süresini artır
FIND_MATCH_TIMEOUT = 90
```

</details>

<details>
<summary><b>❌ "Savas plani bulunamadi: varsayilan"</b></summary>

Henüz plan kaydetmemişsiniz:
```bash
python main.py
# [2] Savas plani kaydet → plan oluşturun
```
Sonra `config.py`:
```python
ACTIVE_PLAN = "kaydettiginiz_plan_adi"
```

</details>

### 🪟 Windows'a Özel Sorunlar

<details>
<summary><b>❌ "python: command not found"</b></summary>

```powershell
# Python'u PATH'e ekleyin veya şunu kullanın:
py -3.11 setup.py
py -3.11 main.py

# Kalıcı çözüm: Python kurulumunda "Add Python to PATH" işaretleyin
```

</details>

<details>
<summary><b>❌ PowerShell "execution of scripts is disabled"</b></summary>

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

veya her seferinde:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_tesseract.ps1
```

</details>

### 📊 Diğer

<details>
<summary><b>❌ Testler başarısız oluyor</b></summary>

```bash
python -m pytest tests/ -v --tb=long     # detaylı hata göster
```

Not: `test_read_number_valid` testi Tesseract yoksa otomatik **atlanır** (skip) — bu normaldir.

</details>

<details>
<summary><b>❌ GitHub Actions workflow başarısız</b></summary>

1. Actions sekmesinde başarısız adıma tıklayın
2. Hata mesajını okuyun
3. Yaygın nedenler:
   - `choco install tesseract` ağ hatası → workflow'u tekrar çalıştırın
   - `flake8` hataları → kodu düzeltin (`flake8 . --max-line-length=100 --exclude=.git`)
   - pytest hatası → `tests/` klasöründeki testi düzeltin

</details>

<details>
<summary><b>❌ "DRY_RUN modunda tıklamıyor"</b></summary>

`config.py` içinde:
```python
DRY_RUN = False    # True ise bot gerçekten tıklamaz (güvenli test modu)
```

</details>

---

## 🤝 10. Katkıda Bulunma Rehberi

### Geliştirme Ortamı Kurulumu

```bash
# 1. Fork'layın ve klonlayın
git clone https://github.com/KULLANICI_ADINIZ/coc-bot.git
cd coc-bot

# 2. Sanal ortam oluşturun
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/macOS

# 3. Bağımlılıkları kurun
pip install -r requirements.txt
pip install flake8            # kod stili için

# 4. Testleri çalıştırın
pytest tests/ -v
```

### Kod Standartları

| Kural | Açıklama |
|---|---|
| **Satır uzunluğu** | Maksimum 100 karakter |
| **Docstring** | Her sınıf ve fonksiyon için **Türkçe** docstring zorunlu |
| **Type hint** | `def tap(self, x: int, y: int) -> None:` |
| **Hata yönetimi** | Her fonksiyon `try/except` ile korunmalı |
| **Hardcode yasak** | Koordinat/yol değerleri `config.py`'dan gelmeli |
| **Dosya başlığı** | Her dosyanın en üstünde ne yaptığını açıklayan yorum bloğu |
| **Konsol çıktısı** | Türkçe + emoji (`[OK]`, `[!]`, `[VISION]`) |
| **Bağımlılık** | Sınıflar arası bağımlılık minimum (dependency injection) |

### Göndermeden Önce Kontrol Listesi

```bash
# 1. Kod stili (workflow ile aynı komut)
flake8 . --max-line-length=100 --exclude=.git

# 2. Tüm testler geçiyor mu?
pytest tests/ -v --tb=short

# 3. Kurulum hala çalışıyor mu?
python setup.py --skip-pip

# 4. Modüller import edilebiliyor mu?
python -c "import config, main, calibrate; print('OK')"
```

### Katkı Türleri

| Tür | Açıklama |
|---|---|
| 🐛 **Hata düzeltme** | Sorunu ve çözümü açıklayan bir issue açın |
| ✨ **Yeni özellik** | Önce issue açıp tartışın, sonra PR gönderin |
| 📚 **Dokümantasyon** | README veya docstring iyileştirmeleri |
| 🌍 **Çeviri** | Türkçe/İngilizce çeviri desteği |
| 📸 **Template paketi** | Farklı çözünürlükler için template setleri |

### Commit Mesajı Formatı

```
<tip>: <kısa açıklama>

<detaylı açıklama (opsiyonel)>

Örnek:
feat: kara iksir filtresi eklendi
fix: OCR binlik ayraç okuma hatası düzeltildi
docs: kurulum rehberine LDPlayer ayarları eklendi
test: scout_filter için birim testleri eklendi
```

### Pull Request Süreci

1. `main` branch'inden yeni bir branch oluşturun: `git checkout -b ozellik/yeni-filtre`
2. Değişikliklerinizi yapın
3. Kontrol listesini çalıştırın (yukarıda)
4. Commit ve push: `git push origin ozellik/yeni-filtre`
5. GitHub'da PR açın ve şablonu doldurun
6. CI (GitHub Actions) yeşil olana kadar bekleyin
7. İnceleme sonrası merge edilir 🎉

### Yol Haritası

- [ ] Klan savaşı modu desteği
- [ ] Duvar yükseltme otomasyonu
- [ ] Çoklu hesap desteği
- [ ] Web arayüzü (canlı bot durumu)
- [ ] YOLO tabanlı bina tespiti (Tesseract'a alternatif)
- [ ] LLaVA ile otomatik saldırı planı üretimi

---

## ⚠️ Yasal Uyarı

Bu proje **eğitim amaçlı** bir otomasyon örneğidir. Clash of Clans'ın Hizmet Şartları (ToS) otomatik oynatmayı yasaklar ve hesabınız **kalıcı olarak yasaklanabilir**. Kullanım sorumluluğu tamamen size aittir. Bu yazılımı yalnızca kendi hesabınızda, riskini bilerek ve yerel (offline) test ortamlarında kullanın.

---

<div align="center">

## 📄 Lisans

MIT License — Detaylar için [LICENSE](LICENSE) dosyasına bakın.

**🎉 Kolay gelsin, iyi savaşlar!** ⚔️

```
Yapıldı: Python 3.11 • OpenCV • Tesseract • ADB • Ollama
```

</div>
