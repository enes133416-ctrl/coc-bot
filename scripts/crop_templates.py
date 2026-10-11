"""
================================================================================
 scripts/crop_templates.py - BUTON PNG KESME ARACI (Tek Komutla!)
================================================================================
 Oyun ekran goruntulerinden buton template'lerini (PNG) otomatik veya fare ile
 interaktif olarak keser, assets/templates/ klasorune kaydeder ve dogrular.

 KULLANIM:

   1) OTOMATIK MOD - klasordeki ekran goruntulerinden butonlari keser:
        python scripts/crop_templates.py --auto --shots "C:\\Users\\Sen\\Pictures"

   2) INTERAKTIF MOD - fare ile kutu cizerek kendi template'ini kes:
        python scripts/crop_templates.py --interactive "C:\\resimler\\savas_sonu.jpg"

   3) DOGRULAMA MOD - kesilen template'leri bir ekranda test et:
        python scripts/crop_templates.py --verify "C:\\resimler\\ana_ekran.jpg"

   4) EKSIK LISTESI - hangi template'ler eksik, ne kesilmeli:
        python scripts/crop_templates.py --list

 ORNEK (bu projeye ozel dosya adlariyla):
   python scripts/crop_templates.py --auto --shots uploads

 NASIL CALISIR?
   - OTOMATIK MOD: Buton konumlari ekran goruntusunun YUZDESI (oran) olarak
     tanimlidir (PRESETS). Bu sayede her cozunurlukte calisir.
   - Her kesilen template, BASKA bir ekran goruntusunde test edilir
     (kendisiyle eslesmesi zaten %100 olurdu, bu yuzden capraz dogrulama yapilir).
   - Sonuclar assets/debug/template_preview.png montajinda yan yana gosterilir.
   - Emin olamadiginiz butonlar icin --interactive modunu kullanin.

 NOT: return_home (savas sonu "Ana Koye Don") butonu icin ekran goruntusu
      gonderilmedigi icin otomatik kesilemez - --interactive ile kendiniz kesin.
================================================================================
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Proje kokunu yola ekle
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config  # noqa: E402

try:
    import cv2
    import numpy as np

    CV2_AVAILABLE = True
except ImportError:  # pragma: no cover - bagimlilik eksikse
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    CV2_AVAILABLE = False


# ==============================================================================
# OTOMATIK KESME AYARLARI (ekran goruntusunun yuzdesi olarak: x, y, w, h)
# ==============================================================================
# hints: dosya adinda gecen ipuclari (kullanicinin ekran goruntusu adlari)
# crop_from: hangi ipucundan kesilecek (ilk eslesen)
# verify_on: capraz dogrulama icin DIGER ipucu (varsa)
PRESETS: Dict[str, Dict[str, Any]] = {
    "attack_button": {
        "hints": ["130858", "133706"],
        "rect": (0.010, 0.825, 0.110, 0.155),
        "aciklama": "Ana koy ekrani 'Saldir!' butonu (sol alt)",
    },
    "find_match": {
        "hints": ["131421"],
        "rect": (0.048, 0.638, 0.220, 0.082),
        "aciklama": "Savas menusu 'Eslesme Bul 1400' butonu",
    },
    "next_button": {
        "hints": ["131225"],
        "rect": (0.818, 0.663, 0.180, 0.162),
        "aciklama": "Rakip onizleme 'Ileri 1400' butonu (sag alt)",
    },
    "attack_button_army": {
        "hints": ["131202", "133713"],
        "rect": (0.760, 0.750, 0.182, 0.075),
        "aciklama": "Ordu ekrani yesil 'Saldir!' butonu (sag alt)",
    },
    "surrender": {
        "hints": ["131225"],
        "rect": (0.008, 0.716, 0.120, 0.082),
        "aciklama": "Savas icindeki kirmizi 'Savasi Bitir' butonu",
    },
}

# Bu dosyalar icin otomatik preset yok - interaktif kesim gerekir
MANUEL_GEREKEN: Dict[str, str] = {
    "return_home": "Savas SONUCU ekranindaki 'Ana Koye Don' butonu (yesil/turuncu)",
    "end_battle_ok": "Savasi bitirme ONAY butonu (kirmizi yesil tik)",
    "collect_resources": "Ana ekrandaki kaynak toplama butonu (istege bagli)",
}


# ==============================================================================
# YARDIMCILAR
# ==============================================================================
def baslik(metin: str) -> None:
    """
    Baslik yazdirir.

    Args:
        metin (str): Baslik metni.

    Returns:
        None
    """
    print("\n" + "=" * 78)
    print(f" {metin}")
    print("=" * 78)


def goruntu_yolu_listesi(shots: str) -> List[Path]:
    """
    Verilen yol bir klasorse icindeki resim dosyalarini, degilse tek dosyayi dondurur.

    Args:
        shots (str): Klasor veya dosya yolu.

    Returns:
        List[Path]: Bulunan goruntu dosyalari (alfabetik).
    """
    sonuc: List[Path] = []
    try:
        yol = Path(shots)
        if yol.is_dir():
            for uzanti in ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"):
                sonuc.extend(yol.glob(uzanti))
        elif yol.is_file():
            sonuc.append(yol)
        else:
            print(f"[!] Yol bulunamadi: {shots}")
        benzersiz = sorted({item.resolve() for item in sonuc}, key=lambda p: p.name)
        return list(benzersiz)
    except Exception as error:
        print(f"[!] Goruntu listeleme hatasi: {error}")
        return []


def ipucuna_gore_bul(goruntuler: List[Path], ipuclari: List[str]) -> List[Path]:
    """
    Dosya adinda ipucu gecen goruntuleri dondurur (sirali).

    Args:
        goruntuler (List[Path]): Tum goruntuler.
        ipuclari (List[str]): Dosya adinda aranacak parcalar.

    Returns:
        List[Path]: Eslesen goruntuler (ipucu sirasina gore).
    """
    eslesen: List[Path] = []
    try:
        for ipucu in ipuclari:
            for goruntu in goruntuler:
                if ipucu in goruntu.name and goruntu not in eslesen:
                    eslesen.append(goruntu)
    except Exception as error:
        print(f"[!] Ipucu arama hatasi: {error}")
    return eslesen


def oran_ile_kes(goruntu: "np.ndarray", rect: Tuple[float, float, float, float]) -> "np.ndarray":
    """
    Goruntuyu yuzde oranlarina gore keser (her cozunurlukte calisir).

    Args:
        goruntu (np.ndarray): Kaynak goruntu.
        rect (Tuple[float, float, float, float]): (x, y, w, h) 0.0-1.0 arasi oranlar.

    Returns:
        np.ndarray: Kesilmis goruntu (bos olabilir).
    """
    height, width = goruntu.shape[:2]
    x = int(rect[0] * width)
    y = int(rect[1] * height)
    w = max(1, int(rect[2] * width))
    h = max(1, int(rect[3] * height))
    x2 = min(width, x + w)
    y2 = min(height, y + h)
    return goruntu[y:y2, x:x2].copy()


def padding_ekle(goruntu: "np.ndarray", oran: float = 0.04) -> "np.ndarray":
    """
    Kesilen goruntuye kenar bosluk (padding) ekler.

    Args:
        goruntu (np.ndarray): Kaynak goruntu.
        oran (float): Eklenecek bosluk orani (0.04 = %4).

    Returns:
        np.ndarray: Bosluklu goruntu.
    """
    try:
        height, width = goruntu.shape[:2]
        pad_y = max(2, int(height * oran))
        pad_x = max(2, int(width * oran))
        kenarlikli = cv2.copyMakeBorder(
            goruntu, pad_y, pad_y, pad_x, pad_x, cv2.BORDER_REPLICATE
        )
        return kenarlikli
    except Exception as error:
        print(f"[!] Padding hatasi: {error}")
        return goruntu


def template_dogrula(
    kaynak_goruntu: str,
    template_path: Path,
    threshold: Optional[float] = None,
) -> float:
    """
    Kesilen template'i bir ekran goruntusunde arar ve guven degerini dondurur.

    Args:
        kaynak_goruntu (str): Test edilecek ekran goruntusu.
        template_path (Path): Test edilecek template dosyasi.
        threshold (Optional[float]): Esik degeri (None ise config'den).

    Returns:
        float: Bulunan en yuksek guven degeri (0.0 - 1.0).
    """
    try:
        from core.vision_engine import VisionEngine

        motor = VisionEngine(threshold=threshold or config.TEMPLATE_THRESHOLD)
        sonuc = motor.find_template(kaynak_goruntu, str(template_path))
        return float(sonuc.get("confidence", 0.0))
    except Exception as error:
        print(f"[!] Dogrulama hatasi: {error}")
        return 0.0


def onizleme_montaji(
    parcalar: List[Tuple[str, "np.ndarray", float]],
    cikti: Optional[Path] = None,
) -> Optional[str]:
    """
    Kesilen tum template'leri tek bir onizleme goruntusunde yan yana birlestirir.

    Args:
        parcalar (List[Tuple[str, np.ndarray, float]]): (isim, goruntu, guven) listesi.
        cikti (Optional[Path]): Cikti dosyasi.

    Returns:
        Optional[str]: Kaydedilen dosyanin yolu veya None.
    """
    try:
        if not parcalar or not CV2_AVAILABLE:
            return None
        hedef_yukseklik = 90
        sutunlar: List["np.ndarray"] = []
        for isim, goruntu, guven in parcalar:
            oran = hedef_yukseklik / float(goruntu.shape[0])
            yeni_genislik = max(40, int(goruntu.shape[1] * oran))
            kucultulmus = cv2.resize(
                goruntu, (yeni_genislik, hedef_yukseklik), interpolation=cv2.INTER_AREA
            )
            etiket = f"{isim[:18]} {guven:.2f}"
            cv2.putText(
                kucultulmus,
                etiket,
                (4, hedef_yukseklik - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.38,
                (0, 255, 0),
                1,
                cv2.LINE_AA,
            )
            sutunlar.append(kucultulmus)
            sutunlar.append(np.full((hedef_yukseklik, 10, 3), 60, dtype=np.uint8))

        montaj = np.hstack(sutunlar[:-1])
        hedef = cikti or (Path(config.DEBUG_DIR) / "template_preview.png")
        hedef.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(hedef), montaj)
        print(f"[OK]  Onizleme montaji -> {hedef}")
        return str(hedef)
    except Exception as error:
        print(f"[!] Montaj hatasi: {error}")
        return None


def eksik_listesi() -> List[str]:
    """
    assets/templates/ klasorunde eksik olan template dosyalarini dondurur.

    Returns:
        List[str]: Eksik dosya adlari.
    """
    eksikler: List[str] = []
    try:
        for _anahtar, dosya_adi in config.TEMPLATES.items():
            if not (Path(config.TEMPLATES_DIR) / dosya_adi).exists():
                eksikler.append(dosya_adi)
    except Exception as error:
        print(f"[!] Eksik listesi hatasi: {error}")
    return eksikler


# ==============================================================================
# MOD 1: OTOMATIK KESME
# ==============================================================================
def mod_auto(shots: str, padding_orani: float = 0.0) -> int:
    """
    Klasordeki ekran goruntulerinden butonlari otomatik keser ve dogrular.

    Args:
        shots (str): Ekran goruntusu klasoru veya dosyasi.
        padding_orani (float): Kesime eklenecek bosluk orani (0 = yok).

    Returns:
        int: 0 -> islem tamamlandi.
    """
    try:
        baslik("OTOMATIK TEMPLATE KESME")
        if not CV2_AVAILABLE:
            print("[!] OpenCV yuklu degil! Kurmak icin: pip install opencv-python")
            return 1

        goruntuler = goruntu_yolu_listesi(shots)
        if not goruntuler:
            print(f"[!] Hic goruntu bulunamadi: {shots}")
            return 1
        print(f" [BILGI] {len(goruntuler)} goruntu bulundu:")
        for item in goruntuler:
            print(f"   - {item.name}")

        Path(config.TEMPLATES_DIR).mkdir(parents=True, exist_ok=True)
        basarili: List[Tuple[str, "np.ndarray", float]] = []
        eksik_eslesen: List[str] = []

        for isim, ayar in PRESETS.items():
            eslesenler = ipucuna_gore_bul(goruntuler, ayar["hints"])
            if not eslesenler:
                eksik_eslesen.append(isim)
                print(f"\n [ATLANDI] {isim} -> dosya adi ipucu bulunamadi "
                      f"({ayar['hints']})")
                continue

            kaynak = eslesenler[0]
            kaynak_img = cv2.imread(str(kaynak))
            if kaynak_img is None:
                print(f" [HATA] Goruntu okunamadi: {kaynak.name}")
                continue

            kesilmis = oran_ile_kes(kaynak_img, tuple(ayar["rect"]))
            if kesilmis.size == 0:
                print(f" [HATA] Kesim bos cikti: {isim}")
                continue
            if padding_orani > 0:
                kesilmis = padding_ekle(kesilmis, padding_orani)

            hedef = Path(config.TEMPLATES_DIR) / f"{isim}.png"
            cv2.imwrite(str(hedef), kesilmis)

            # Capraz dogrulama: baska bir goruntude ara
            test_goruntusu = eslesenler[1] if len(eslesenler) > 1 else kaynak
            kendisi_mi = test_goruntusu == kaynak
            guven = template_dogrula(str(test_goruntusu), hedef)
            durum = "OK" if guven >= config.TEMPLATE_THRESHOLD else "DUSUK"

            print(f"\n [+] {isim}.png kesildi")
            print(f"     Kaynak      : {kaynak.name}")
            print(f"     Aciklama    : {ayar['aciklama']}")
            print(f"     Boyut       : {kesilmis.shape[1]}x{kesilmis.shape[0]} piksel")
            print(f"     Dogrulama   : {guven:.3f} ({durum})"
                  f"{'  [uyari: ayni goruntude test edildi]' if kendisi_mi else ''}")

            basarili.append((isim, kesilmis, guven))

        # Ozet
        baslik("OTOMATIK KESME OZETI")
        bulunan = len(basarili)
        print(f" Basariyla kesilen : {bulunan}/{len(PRESETS)}")
        yuksek = sum(1 for _i, _g, guven in basarili if guven >= config.TEMPLATE_THRESHOLD)
        print(f" Dogrulanan        : {yuksek}/{bulunan}")

        if eksik_eslesen:
            print(f"\n [!] Bu butonlar icin ekran goruntusu eslesmedi: {eksik_eslesen}")
            print("     Dosya adlarinda ipucu arayin veya --interactive kullanin.")

        if basarili:
            onizleme = onizleme_montaji(basarili)
            if onizleme:
                print(f"\n [ADI] Onizlemeyi acip kontrol edin:\n       {onizleme}")
                print("       Butonlar duzgun kesilmemisse: --interactive modunu kullanin.")

        # Eksik template'ler
        eksikler = eksik_listesi()
        if eksikler:
            print(f"\n [BILGI] Hala eksik template'ler ({len(eksikler)}):")
            for ad in eksikler:
                ipucu = next(
                    (metin for anahtar, metin in MANUEL_GEREKEN.items()
                     if f"{anahtar}.png" == ad),
                    "assets/templates/README.md rehberine bakin",
                )
                print(f"   - {ad:<24} {ipucu}")
            print("\n     Interaktif kesim ornegi:")
            print(f"       python scripts/crop_templates.py --interactive \"{goruntuler[0]}\"")

        print("\n[OK]  Islem tamamlandi.")
        return 0
    except Exception as error:
        print(f"[!] Otomatik kesme hatasi: {error}")
        return 1


# ==============================================================================
# MOD 2: INTERAKTIF KESME (Fare ile)
# ==============================================================================
def mod_interaktif(goruntu_yolu: str) -> int:
    """
    Fare ile kutu cizerek template keser (eksik butonlar icin ideal).

    Kontroller (OpenCV penceresi):
      - Sol tik + surukle : kutuyu ciz
      - ENTER / SPACE     : kutuyu onayla
      - C                 : iptal
      - Q veya ESC        : cikis

    Args:
        goruntu_yolu (str): Kaynak ekran goruntusu.

    Returns:
        int: 0 -> islem tamamlandi.
    """
    try:
        baslik("INTERAKTIF TEMPLATE KESME (fare ile)")
        if not CV2_AVAILABLE:
            print("[!] OpenCV yuklu degil! Kurmak icin: pip install opencv-python")
            return 1

        kaynak = Path(goruntu_yolu)
        if not kaynak.exists():
            print(f"[!] Goruntu bulunamadi: {goruntu_yolu}")
            return 1
        img = cv2.imread(str(kaynak))
        if img is None:
            print(f"[!] Goruntu okunamadi: {goruntu_yolu}")
            return 1

        print(f" Kaynak goruntu : {kaynak.name}  ({img.shape[1]}x{img.shape[0]})")
        print("\n Kesilecek template adini yazin (uzantisiz). Ornekler:")
        mevcut_isimler = [anahtar for anahtar in config.TEMPLATES]
        print(f"   Hazir isimler: {', '.join(mevcut_isimler)}")
        print("   Veya kendi isminizi yazin (orn. return_home, end_battle_ok)")
        print("   Cikis icin bos birakip ENTER'a basin.\n")

        pencere = f"Kutu ciz: {kaynak.name}  (ENTER=onayla, C=iptal, Q=cikis)"
        cv2.namedWindow(pencere, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(pencere, 1100, 700)

        kesim_sayisi = 0
        while True:
            isim = input(" Template adi: ").strip()
            if not isim:
                break

            try:
                x, y, w, h = cv2.selectROI(
                    pencere, img, showCrosshair=True, fromCenter=False
                )
                cv2.destroyWindow("ROI selector")
            except Exception as error:
                print(f"[!] Kutu cizme hatasi: {error}")
                continue

            if w <= 0 or h <= 0:
                print("[!] Kutu cizilmedi, atlandi.")
                continue

            kesilmis = img[int(y):int(y + h), int(x):int(x + w)].copy()
            kesilmis = padding_ekle(kesilmis, 0.03)
            hedef = Path(config.TEMPLATES_DIR) / f"{isim}.png"
            hedef.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(hedef), kesilmis)
            kesim_sayisi += 1

            guven = template_dogrula(str(kaynak), hedef)
            print(f" [OK]  KESILDI -> {hedef}")
            print(f"       Bolge  : x={int(x)}, y={int(y)}, w={int(w)}, h={int(h)}")
            print(f"       Boyut  : {kesilmis.shape[1]}x{kesilmis.shape[0]}  "
                  f"| Kendi goruntusunde guven: {guven:.3f}")
            print("       (Not: ayni goruntude guven her zaman yuksek cikar;")
            print("        farkli bir ekran goruntusunde --verify ile test edin.)")

        cv2.destroyAllWindows()

        baslik("INTERAKTIF KESIM OZETI")
        print(f" Kesilen template sayisi : {kesim_sayisi}")
        eksikler = eksik_listesi()
        if eksikler:
            print(f" Hala eksik olanlar ({len(eksikler)}): {', '.join(eksikler)}")
        else:
            print(" [OK]  Tum template'ler tamamlandi!")
        print("\n Dogrulama icin:")
        print(f"   python scripts/crop_templates.py --verify \"{goruntu_yolu}\"")
        return 0
    except KeyboardInterrupt:
        print("\n[!] Interaktif kesim kullanici tarafindan durduruldu.")
        return 0
    except Exception as error:
        print(f"[!] Interaktif kesme hatasi: {error}")
        return 1


# ==============================================================================
# MOD 3: DOGRULAMA
# ==============================================================================
def mod_dogrula(goruntu_yolu: str) -> int:
    """
    assets/templates/ icindeki tum template'leri bir ekran goruntusunde test eder.

    Args:
        goruntu_yolu (str): Test edilecek ekran goruntusu.

    Returns:
        int: 0 -> islem tamamlandi.
    """
    try:
        baslik("TEMPLATE DOGRULAMA")
        if not CV2_AVAILABLE:
            print("[!] OpenCV yuklu degil! Kurmak icin: pip install opencv-python")
            return 1

        if not Path(goruntu_yolu).exists():
            print(f"[!] Goruntu bulunamadi: {goruntu_yolu}")
            return 1

        mevcut = sorted(Path(config.TEMPLATES_DIR).glob("*.png"))
        if not mevcut:
            print(f"[!] Hic template yok: {config.TEMPLATES_DIR}")
            print("     Once: python scripts/crop_templates.py --auto --shots <klasor>")
            return 1

        print(f" Goruntu   : {Path(goruntu_yolu).name}")
        print(f" Template  : {len(mevcut)} adet\n")
        print(f" {'TEMPLATE':<26} {'SONUC':<10} {'GUVEN':>7}  {'OLCEK':>6}")
        print("-" * 78)

        from core.vision_engine import VisionEngine

        motor = VisionEngine()
        bulunan = 0
        for item in mevcut:
            sonuc = motor.find_template(goruntu_yolu, str(item))
            durum = "BULUNDU" if sonuc.get("found") else "YOK"
            if sonuc.get("found"):
                bulunan += 1
            print(
                f" {item.name:<26} {durum:<10} "
                f"{float(sonuc.get('confidence', 0.0)):>7.3f}  "
                f"{float(sonuc.get('scale', 1.0)):>6.2f}"
            )

        print("-" * 78)
        print(f" Ozet: {bulunan}/{len(mevcut)} template bulundu "
              f"(esik: {config.TEMPLATE_THRESHOLD})")
        print("\n Not: Bu ekranda GORUNMEYEN butonlarin 'YOK' cikmasi normaldir!")
        print("      (orn. ana ekranda 'Ileri' butonu olmaz)")
        return 0
    except Exception as error:
        print(f"[!] Dogrulama hatasi: {error}")
        return 1


# ==============================================================================
# MOD 4: EKSIK LISTESI
# ==============================================================================
def mod_liste() -> int:
    """
    Hangi template'lerin eksik oldugunu ve nasil kesilecegini listeler.

    Returns:
        int: 0 -> islem tamamlandi.
    """
    try:
        baslik("TEMPLATE DURUMU")
        print(f" Klasor: {config.TEMPLATES_DIR}\n")
        print(f" {'DOSYA':<26} {'DURUM':<12} {'ACIKLAMA'}")
        print("-" * 78)

        mevcut_sayisi = 0
        for anahtar, dosya_adi in config.TEMPLATES.items():
            hedef = Path(config.TEMPLATES_DIR) / dosya_adi
            var = hedef.exists()
            if var:
                mevcut_sayisi += 1
            durum = "VAR" if var else "EKSIK"
            aciklama = MANUEL_GEREKEN.get(anahtar, "")
            if not aciklama:
                aciklama = next(
                    (ayar["aciklama"] for isim, ayar in PRESETS.items() if isim == anahtar),
                    "-",
                )
            print(f" {dosya_adi:<26} {durum:<12} {aciklama}")

        print("-" * 78)
        print(f" Toplam: {mevcut_sayisi}/{len(config.TEMPLATES)} template hazir")
        if mevcut_sayisi < len(config.TEMPLATES):
            print("\n Otomatik kesim icin (bu projeye ozel dosya adlariyla):")
            print("   python scripts/crop_templates.py --auto --shots <EKRAN_GORUNTUSU_KLASORU>")
            print("\n Tek tek interaktif kesim icin:")
            print("   python scripts/crop_templates.py --interactive <EKRAN_GORUNTUSU.jpg>")
        else:
            print("\n [OK]  Tum template'ler hazir! Test icin:")
            print("   python calibrate.py   ->  [5] Tum template'leri test et")
        return 0
    except Exception as error:
        print(f"[!] Liste hatasi: {error}")
        return 1


# ==============================================================================
# ANA GIRIS
# ==============================================================================
def main() -> int:
    """
    Komut satiri argumanlarini isler.

    Returns:
        int: 0 -> basarili.
    """
    try:
        parser = argparse.ArgumentParser(
            description="Clash of Clans botu icin buton PNG kesme araci",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=(
                "Ornekler:\n"
                "  python scripts/crop_templates.py --list\n"
                "  python scripts/crop_templates.py --auto --shots C:\\resimler\n"
                "  python scripts/crop_templates.py --interactive C:\\resimler\\savas_sonu.jpg\n"
                "  python scripts/crop_templates.py --verify C:\\resimler\\ana_ekran.jpg\n"
            ),
        )
        parser.add_argument("--auto", action="store_true", help="otomatik kesme modu")
        parser.add_argument(
            "--interactive", metavar="GORUNTU", help="fare ile kutu cizme modu"
        )
        parser.add_argument("--verify", metavar="GORUNTU", help="template dogrulama modu")
        parser.add_argument("--list", action="store_true", help="eksik template listesi")
        parser.add_argument("--shots", default=".", help="--auto icin klasor/dosya yolu")
        parser.add_argument(
            "--padding", type=float, default=0.0,
            help="otomatik kesime eklenecek kenar boslugu orani (orn. 0.03)",
        )
        args = parser.parse_args()

        print("=" * 78)
        print(" BUTON PNG KESME ARACI - Clash of Clans Yerel AI Bot")
        print("=" * 78)

        if args.interactive:
            return mod_interaktif(args.interactive)
        if args.auto:
            return mod_auto(args.shots, args.padding)
        if args.verify:
            return mod_dogrula(args.verify)

        # Varsayilan: durum listesi
        return mod_liste()
    except KeyboardInterrupt:
        print("\n[!] Islem kullanici tarafindan durduruldu.")
        return 0
    except Exception as error:
        print(f"[!] Kritik hata: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
