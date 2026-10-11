# 🎬 Savaş Planı Kayıt Rehberi (Detaylı)

Bu belge, botun saldırı sırasında ne yapacağını **adım adım nasıl kaydedeceğinizi** anlatır.

---

## 🤔 Savaş Planı Nedir?

Bot, oyundaki üsleri analiz edip **kendi başına saldırı planı üretmez**. Onun yerine:

1. **Siz bir saldırı yaparsınız** ("ben şuraya ejder bırakıyorum, şuraya büyü atıyorum...")
2. Bot **her tıklamanızı ve zamanlamasını** kaydeder → `data/battle_plans.json`
3. Bot sonraki rakiplerde **aynı hareketleri aynı zamanlamayla** tekrarlar

Yani: **siz bir kez oynarsınız, bot binlerce kez tekrarlar.**

```
SİZ:    [Ejder bırak 2. saniyede] → [Kraliçe 5. saniyede] → [Öfke 8. saniyede]
BOT:    [Ejder bırak 2. saniyede] → [Kraliçe 5. saniyede] → [Öfke 8. saniyede]
                     ▲                        ▲                       ▲
                aynı koordinat          aynı koordinat          aynı koordinat
                aynı zamanlama          aynı zamanlama          aynı zamanlama
```

---

## 📍 Adım 0: Koordinatları Öğrenmek

Bot **piksel koordinatları** kullanır (ekranın sol üst köşesi = 0,0).

### Yöntem A: Bot'un kendi aracı (En kolay)

```bash
python scripts/crop_templates.py --verify "ana_ekran.png"
```

veya kalibrasyon aracındaki `[2]` seçeneği, tıkladığınız noktayı size yazdırır:
```bash
python calibrate.py     # -> [2] Template matching test et
```

### Yöntem B: Koordinat bulma scripti

```python
# koordinat_bul.py  olarak kaydedip çalıştırın
import cv2

goruntu = cv2.imread("ekran_goruntusu.png")
print(f"Ekran boyutu: {goruntu.shape[1]} x {goruntu.shape[0]}")

def tiklandi(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"  -> TIKLADINIZ: x={x}, y={y}")

cv2.namedWindow("Koordinat Bul", cv2.WINDOW_NORMAL)
cv2.setMouseCallback("Koordinat Bul", tiklandi)
cv2.imshow("Koordinat Bul", goruntu)
print("Ekranda bir yere tıklayın, koordinat konsola yazılır. Çıkmak için Q.")
cv2.waitKey(0)
```

### Yöntem C: LDPlayer penceresinden ölçüm

LDPlayer'ı **1600x900** ve **pencere modunda** çalıştırın. Ekran görüntüsünü Paint'te açın,
fare imlecinin konumu Paint'in sol alt köşesinde `x, y` olarak görünür.

> ⚠️ **Çok önemli:** Bot koordinatları **pencerenin iç kısmına** göre hesaplar
> (başlık çubuğu ve kenarlıklar hariç). LDPlayer'ı tam ekran (F11) yaparsanız
> koordinatlar tam olarak ekran görüntüsüyle eşleşir.

---

## 📝 Adım 1: Kayıt Modunu Başlatın

```bash
python main.py
```

```
 ANA MENU
 ----------------------------------------
  [1] Bot'u baslat
  [2] Savas plani kaydet      ◀── BUNU SEÇ
  [3] OCR kalibre et / template test et
  ...
```

`2` yazıp Enter'a basın.

---

## 🎯 Adım 2: Plan Adını Verin

```
 KAYITLI SAVAS PLANLARI
 ==============================================================================
  (Henuz plan yok. Kaydetmek icin: python main.py -> [2])
 ==============================================================================

 Plan adi (orn. koy_saldirisi): ejder_saldirisi
```

**İsim önerileri:** `ejder_saldirisi`, `koy_farm`, `kupa_kas`, `koy_v2` ...
(Boş bırakırsanız `varsayilan` kullanılır.)

---

## 🔴 Adım 3: Canlı Kayıt Modu (ÖNERİLEN)

```
 Hareketleri emulatora da gondersin mi? (e/h): e
```

**`e` seçin!** Bu modda:
- Sizin girdiğiniz her koordinat **anında emülatörde tıklanır**
- Siz oyunun gerçekten nasıl tepki verdiğini görürsünüz
- Yanlış koordinat girdiyseniz hemen fark edersiniz

> Not: Bu modda oyun gerçekten oynanır (birlikler bırakılır). Yedek bir hesap/köy ile denemek daha güvenlidir.

---

## ⌨️ Adım 4: Hareketleri Kaydedin

Bot her adımda şunları sorar:

```
 [1] x,y (veya 'bitti'): 800,450
 Eylem tipi (tap/swipe/long_press/key/wait) [tap]: tap
 Etiket (orn. ejder birak): sol_kanat_ejder
[PLAN] + Kayit #1 | t=0.00s | tap (800,450) sol_kanat_ejder
```

### Eylem Tipleri Tablosu

| Tip | Ne Zaman Kullanılır? | İstenen Bilgiler | Örnek |
|---|---|---|---|
| `tap` | Birlik/büyü bırakma, butona basma | `x,y` | `800,450` |
| `swipe` | Ekranı kaydırma, birlikleri sürükleme | `x,y` + `x2,y2` + süre(ms) | `800,450` → `1200,600`, 500ms |
| `long_press` | Uzun basma (nadiren gerekir) | `x,y` + süre(ms) | `800,450`, 1200ms |
| `key` | Geri tuşu (keycode 4), Home (3) | keycode | `4` |
| `wait` | Sadece bekleme (hiç tıklama yok) | saniye | `2.5` |

### Gerçek Bir Saldırı Örneği (15 adım)

Aşağıda tipik bir ejder saldırısının kaydı var. Siz de benzer şekilde girin:

```
 [1] x,y (veya 'bitti'): 500,300        ← Sol kanada ejder
 Eylem tipi [tap]: tap
 Etiket: sol_kanat_ejder

 [2] x,y (veya 'bitti'): 520,320        ← Aynı bölgeye ikinci ejder
 Etiket: sol_kanat_ejder_2

 [3] x,y (veya 'bitti'): 1100,300       ← Sağ kanada ejder
 Etiket: sag_kanat_ejder

 [4] x,y (veya 'bitti'): 800,400        ← Merkeze ejder (Town Hall üstüne)
 Etiket: merkez_ejder
 Eylem tipi [tap]: tap

 [5] x,y (veya 'bitti'): 300,700        ← Barbar Kral
 Etiket: kral

 [6] x,y (veya 'bitti'): 1300,700       ← Okçu Kraliçe
 Etiket: kralice

 [7] x,y (veya 'bitti'): 700,450
 Eylem tipi [tap]: swipe
 Etiket: ofke_buyusu
 Bitis x2,y2: 900,500
 Sure ms [300]: 400

 [8] x,y (veya 'bitti'): 800,600
 Etiket: sifa_buyusu

 ... (devam edin, her birlik/büyü için)

 [15] x,y (veya 'bitti'): bitti         ← KAYDI BİTİR
```

### ⏱️ Zamanlama Otomatik Ölçülür

Her kayıtta **`t=` değerine bakın**: bu o anki kayıt zamanıdır.

```
[PLAN] + Kayit #1 | t=0.00s   ← kayıt başlangıcı
[PLAN] + Kayit #2 | t=3.21s   ← 1. hareketten 3.21 saniye sonra
[PLAN] + Kayit #3 | t=5.40s   ← 2. hareketten 2.19 saniye sonra
```

Bot oynatırken bu farkları bekler. **Bu yüzden kayıt yaparken acele etmeyin** —
gerçek saldırıdaki temponuzla girin (birlikler yavaş bırakılır, büyüler 5-8 saniye sonra atılır vb.).

**Hızlandırmak isterseniz:** `config.py` → `PLAYBACK_SPEED = 1.5` (plan %50 hızlı oynatılır).

---

## ✅ Adım 5: Kaydı Bitirin

```
 [15] x,y (veya 'bitti'): bitti

[OK]  [PLAN] 'ejder_saldirisi' kaydedildi -> 14 hareket, 42.7 saniye

 KAYITLI SAVAS PLANLARI
 ==============================================================================
  PLAN ADI                 HAREKET       SURE            OLUSTURMA
 ------------------------------------------------------------------------------
  ejder_saldirisi               14      42.70s     2026-10-11 14:23:07
 ==============================================================================

[MAIN] 'ejder_saldirisi' plani kaydedildi (14 hareket).
       config.py icinde ACTIVE_PLAN = "ejder_saldirisi" yapabilirsiniz.
```

---

## ⚙️ Adım 6: Planı Aktif Edin

`config.py` dosyasını açın ve şu satırı bulun:

```python
ACTIVE_PLAN: str = "varsayilan"
```

Şuna çevirin:

```python
ACTIVE_PLAN: str = "ejder_saldirisi"
```

İsteğe bağlı ayarlar:

```python
PLAYBACK_SPEED: float = 1.0      # 1.0 = orijinal hız, 1.5 = %50 hızlı
BATTLE_TIMEOUT: int = 180        # savaş bitişini bekleme süresi (saniye)
```

---

## 🚀 Adım 7: Bot'u Çalıştırın

```bash
python main.py     # -> [1] Bot'u baslat
```

Bot artık şu döngüyü işletir:

1. **HOME** → "Saldır!" butonunu bulur, tıklar
2. **FINDING_MATCH** → "Eşleşme Bul" butonunu bulur, tıklar (1400 kupa harcanır)
3. **SCOUTING** → Rakibin loot'unu OCR ile okur
   - Loot ≥ 1.6M ise → **ATTACKING**
   - Loot az ise → "İleri" butonuna basar, yeni rakip arar
4. **ATTACKING** → `ejder_saldirisi` planını oynatır
5. **WAITING_END** → Savaş bitişini bekler (maks 180 sn)
6. **RETURNING** → "Ana Köye Dön" butonuna basar, 4 sn bekler
7. → **HOME** (döngü baştan)

---

## 🛠️ Sorun Giderme

| Sorun | Sebep | Çözüm |
|---|---|---|
| "Savas plani bulunamadi" | Plan kaydedilmemiş veya `ACTIVE_PLAN` yanlış | Plan adını `config.py`'daki `ACTIVE_PLAN` ile birebir eşleştirin |
| Birlikler **yanlış yere** bırakılıyor | Koordinatlar farklı çözünürlükte alınmış | Botu ve kaydı aynı çözünürlükte yapın (1600x900) |
| Birlikler **çok erken/geç** bırakılıyor | Kayıt sırasında tempo farklıydı | `PLAYBACK_SPEED` ile ayarlayın veya planı yeniden kaydedin |
| Plan **hiç oynanmıyor** | `execute()` başarısız | Konsol çıktısına bakın: `[PLAN] OYNATILIYOR -> ...` satırı görünüyor mu? |
| Tıklamalar **kaydırılıyor** | LDPlayer penceresi kaydırılmış | LDPlayer'ı F11 ile tam ekran yapın veya pencereyi sabitleyin |

### Planı Test Etme (Bot Olmadan)

```python
# plan_test.py olarak kaydedip çalıştırın
import time
from core.adb_controller import ADBController
from modules.attack_planner import AttackPlanner

adb = ADBController()
planner = AttackPlanner()
planner.list_plans()

# Sadece "İleri" butonuna bas ve koordinatı doğrula:
adb.tap(1400, 720)
time.sleep(1)

# Planı savaş başlamadan görmek için (dry): sadece zamanlamayı yazdır
plan = planner.get_plan("ejder_saldirisi")
for adim in plan["actions"]:
    print(f"  t={adim['time']:6.2f}s -> {adim['action_type']:<10} "
          f"({adim['x']},{adim['y']})  {adim['label']}")
```

### Kopya Plan Oluşturma (Küçük Değişiklikler İçin)

```python
from modules.attack_planner import AttackPlanner

planner = AttackPlanner()
planner.export_plan("ejder_saldirisi", "data/exports/ejder_v2.json")

# JSON'u düzenleyip (koordinat/süre değiştirip) geri yükleyin:
planner.import_plan("data/exports/ejder_v2.json", new_name="ejder_saldirisi_v2")
```

---

## 💡 İpuçları ve Püf Noktaları

1. **İlk planı "test köyü"nde yapın** — bir alt hesap veya dostluk savaşında deneyin.
2. **Az hareketle başlayın:** Önce sadece 3-4 adımlık basit bir plan kaydedip çalıştığını görün.
3. **Aynı üs tipini hedefleyin:** Plan, belirli bir üs düzenine göre kaydedilir. Rastgele üslerde
   etkili olmayabilir — bu yüzden loot filtresi önemli (yüksek loot = genelde max edilmiş üs).
4. **Büyüler için `swipe` kullanın:** Büyüyü tam merkeze değil, tıklayıp sürükleyerek bırakmak
   daha tutarlı sonuç verebilir.
5. **Birden fazla plan kaydedin:** Farklı üs tipleri için (`ejder_saldirisi`, `koy_farm`)
   ve `config.py`'dan hangisini isterseniz seçin.
6. **Yedek alın:** `data/battle_plans.json`'u arada bir kopyalayın
   (veya `planner.backup_plans()` çağırın).

---

## 📊 Kaydedilen Verinin Yapısı

`data/battle_plans.json` örneği:

```json
{
  "ejder_saldirisi": {
    "name": "ejder_saldirisi",
    "created_at": "2026-10-11 14:23:07",
    "duration": 42.7,
    "speed": 1.0,
    "action_count": 14,
    "actions": [
      {
        "time": 0.0,
        "delay": 0.0,
        "x": 500,
        "y": 300,
        "action_type": "tap",
        "label": "sol_kanat_ejder",
        "metadata": {}
      },
      {
        "time": 2.19,
        "delay": 2.19,
        "x": 1100,
        "y": 300,
        "action_type": "tap",
        "label": "sag_kanat_ejder",
        "metadata": {}
      }
    ]
  }
}
```

- `time` → kaydın başlangıcından itibaren geçen süre (oynatmada kullanılır)
- `delay` → bir önceki harekete göre bekleme
- `metadata` → swipe için `x2, y2, duration`; long_press için `duration`; key için `keycode`

---

**Sonraki adım:** [README.md → 5. İlk Çalıştırma](../README.md#-5-ilk-çalıştırma)
