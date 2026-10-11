# 📸 Template Görselleri Klasörü

Bu klasör, botun ekrandaki butonları **OpenCV template matching** ile bulması için gereken PNG görsellerini barındırır.

## ⚠️ ÖNEMLİ: Bu klasör boş bırakılamaz!

Bot çalışmaya başladığında aşağıdaki butonları arar. Bu görseller yoksa bot hiçbir şey yapamaz.

---

## ⚡ HIZLI YOL: Otomatik Kesme Aracı

Elle Paint ile kesmek yerine, ekran görüntülerinizden **tek komutla** buton kesin:

```bash
# 1. Durum: hangi template eksik?
python scripts/crop_templates.py --list

# 2. Otomatik kesme (ekran görüntülerinizin olduğu klasörü verin)
python scripts/crop_templates.py --auto --shots "C:\Users\Sen\Pictures"

# 3. Eksik kalanları fare ile kendiniz kesin (örn. savaş sonu "Ana Köye Dön")
python scripts/crop_templates.py --interactive "C:\resimler\savas_sonu.jpg"

# 4. Doğrula
python scripts/crop_templates.py --verify "C:\resimler\ana_ekran.jpg"
```

Araç ne yapar:
- Buton konumlarını **ekranın yüzdesi** olarak bildiği için her çözünürlükte çalışır
- Kestiği her template'i **başka bir ekran görüntüsünde** test edip güven puanı verir
- `assets/debug/template_preview.png` dosyasına yan yana önizleme montajı üretir

İnteraktif modda: fare ile kutuyu çiz → ENTER → otomatik PNG olarak kaydedilir.

---

## 📖 Elle Kesme (Alternatif)

---

## 📋 Gerekli Template Dosyaları

| Dosya Adı | Ne İşe Yarar | Nereden Alınır |
|---|---|---|
| `attack_button.png` | Ana ekrandaki "Saldır" / "Attack" butonu | Ana köy ekranı (sol alt/alt orta) |
| `find_match.png` | "Eşleşme Bul" / "Find a Match" butonu | Saldırı menüsü |
| `next_button.png` | Rakibi atlarken basılan "Sonraki" butonu | Rakip önizleme ekranı |
| `return_home.png` | Savaş sonu "Ana köye dön" butonu | Savaş sonucu ekranı |
| `surrender.png` | "Teslim ol" butonu (opsiyonel) | Savaş içi menü |
| `end_battle_ok.png` | Savaş bitirme onay butonu (opsiyonel) | Savaş sonucu ekranı |
| `collect_resources.png` | Kaynak toplama butonu (opsiyonel) | Ana köy ekranı |
| `hero_king.png` | Barbar Kral ikonu (opsiyonel) | Savaş alt barı |
| `hero_queen.png` | Okçu Kraliçe ikonu (opsiyonel) | Savaş alt barı |
| `spell_factory.png` | Büyü fabrikası (opsiyonel) | Savaş alt barı |

> **Not:** Sadece ilk 4 tanesi zorunludur. Diğerleri isteğe bağlıdır.

---

## ✂️ Template Nasıl Kesilir? (Adım Adım)

### Yöntem 1: Windows Ekran Alıntısı Aracı (En Kolay)

1. **LDPlayer'ı aç** ve Clash of Clans'ı başlat
2. Ana köy ekranına gel
3. `Win + Shift + S` tuşlarına bas (Ekran Alıntısı Aracı açılır)
4. **"Dikdörtgen"** seçeneğini seç
5. **Sadece butonu** seç — butonun tamamı + her kenardan 2-3 piksel boşluk
   - ❌ Çok küçük seçme (butonun yarısı olmaz)
   - ❌ Çok büyük seçme (arka planı da alırsan eşleşmez)
   - ✅ Butonun tamamı + azıcık kenar boşluk
6. Kesilen resim panoya kopyalanır → `Paint`'e yapıştır (`Ctrl+V`)
7. **PNG olarak kaydet** → dosya adını **tam olarak** `attack_button.png` yap
8. Bu klasöre (`assets/templates/`) kopyala

### Yöntem 2: Bot'un Aldığı Ekran Görüntüsünü Kullanma (Önerilen)

Bot zaten sizin için ekran görüntüsü alabilir:

```bash
# 1. ADB bağlantısını doğrula
python calibrate.py    # -> [4] ADB bağlantısını test et

# 2. Kalibrasyon aracını çalıştır
python calibrate.py    # -> [2] Template matching test et

# 3. Kalibrasyon aracı ekran görüntüsünü şuraya kaydeder:
#    data/screenshots/kalibrasyon_XXXXXX.png
```

Sonra bu PNG'yi Paint veya herhangi bir görsel editörde açıp butonu kes.

### Yöntem 3: Python ile Otomatik Kesme (İleri Seviye)

```python
import cv2
import config

# Ekran görüntüsünü aç
gorsel = cv2.imread("data/screenshots/kalibrasyon_120000.png")

# Keseceğin bölgeyi x, y, w, h olarak ver (piksel)
bolge = gorsel[800:860, 700:900]   # örnek: y1:y2, x1:x2

# Kaydet
cv2.imwrite(str(config.TEMPLATES_DIR / "attack_button.png"), bolge)
print("Template kaydedildi!")
```

---

## 🔍 Template'leri Test Etme

Görselleri kestikten sonra **mutlaka** test edin:

```bash
python calibrate.py
```

Menüden **[5] Tüm template'leri test et** seçeneğini seçin. Çıktı şöyle olmalı:

```
 TÜM TEMPLATE'LERİ TEST ET
 10 template test edilecek (eşik=0.82)...

 TEMPLATE                     SONUÇ      KONUM                GÜVEN   ÖLÇEK
 ------------------------------------------------------------------------------
 attack_button.png            BULUNDU    (812,794)            0.961    1.00
 find_match.png               BULUNDU    (798,652)            0.943    1.00
 next_button.png              YOK        (0,0)                0.612    0.90
 ------------------------------------------------------------------------------
 Özet: 7/10 template bulundu.
```

**GÜVEN değeri 0.82'den büyükse** ✅ template doğru çalışıyor.
**YOK çıkıyorsa** ❌ aşağıdaki adımları uygulayın.

---

## 🛠️ Sorun Giderme

### "YOK" çıkıyor ama buton ekranda görünüyor

| Sorun | Çözüm |
|---|---|
| Görsel çok küçük/büyük | Butonu daha düzgün kes; butonun tamamı görünsün |
| Yanlış anda alınmış | Butonun **aktif** olduğu andaki halini kes (pasif/gri halini değil) |
| Buton yarı saydam | Butonun altındaki arka planla birlikte kes |
| Eşik çok yüksek | `config.py` → `TEMPLATE_THRESHOLD = 0.75` yap |
| Farklı çözünürlük | Ekranı 1600x900 yap veya `config.SCREEN_WIDTH/HEIGHT` güncelle |
| Ölçek sorunu | Bot 13 farklı ölçek dener (0.7-1.3); yine olmazsa görseli yeniden kes |

### Görsel formatı gereksinimleri

- ✅ **PNG** formatı (JPG değil!)
- ✅ 24-bit veya 32-bit renk
- ✅ Buton çevresinde 2-3 piksel kenar boşluk
- ✅ Buton görünür ve net (bulanık değil)
- ❌ Şeffaflık (alpha) kullanmayın - siyah arka plan sorun yaratabilir

### Aynı buton farklı ekranlarda farklı görünüyor

Birden fazla template kullanabilirsiniz:
- `attack_button.png` (ana köy)
- `attack_button_clan_war.png` (klan savaşı)

Sonra `config.py`'deki `TEMPLATES` sözlüğüne ekleyin.

---

## 📐 Çözünürlük Notu

Bu template'ler **1600x900** çözünürlük için idealdir. Farklı çözünürlüklerde:
- Bot otomatik olarak **ölçekli arama** yapar (0.7x - 1.3x)
- Çok farklı çözünürlüklerde (örn. 2560x1440) yeni template kesmeniz gerekebilir

`config.py` içinde:
```python
SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900
```

---

## 💡 İpuçları

1. **Devlet emojisi ve animasyonlar:** Oyun içi animasyonlar template'i bozabilir. Mümkünse animasyonsuz/statik anları yakalayın.

2. **Buton aktif/pasif durumu:** Bazı butonlar (örn. savaş bitti butonu) pasifken gri görünür. **Aktif halini** kaydedin.

3. **Toplu kesme:** 10 buton için aynı anda ekran görüntüsü alıp hepsini Paint'te tek tek kesmek çok daha hızlıdır.

4. **Yedekleme:** Çalışan template'leri `assets/templates_backup/` gibi bir klasöre kopyalayın. Bozulursa geri dönebilirsiniz.

5. **Test döngüsü:** Kes → test et → olmuyorsa farklı kes → test et. Ortalama 2-3 denemede doğru template bulunur.

---

## 📊 Debug Görselleri

Bot bir template'i bulamadığında veya bulduğunda **kırmızı dikdörtgen** ile işaretlenmiş debug görüntüsü kaydeder:

```
assets/debug/debug_ekran_20260101_120000.png
```

Bu görseli açıp:
- ✅ **Yeşil nokta + kırmızı kutu** = doğru bulunmuş
- ❌ **Kutular yanlış yerde** = template'i yeniden kes
- ❌ **Hiç kutu yok** = template hiç bulunamamış

---

## 🎯 Hazır Template Paketi

Topluluk tarafından hazırlanmış template paketleri de kullanabilirsiniz ancak:
- ⚠️ Oyun güncellemelerinde template'ler değişebilir
- ⚠️ Her çözünürlük için ayrı paket gerekir
- ✅ En güvenilir yöntem **kendi template'inizi kesmektir**

---

**Sonraki adım:** Template'leri kestikten sonra `python calibrate.py` ile test edin,
ardından `python main.py` ile botu çalıştırın.

**Sorun mu yaşıyorsunuz?** README.md → "Sık Karşılaşılan Sorunlar" bölümüne bakın.
