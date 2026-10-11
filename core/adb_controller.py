"""
================================================================================
 core/adb_controller.py - ADB (Android Debug Bridge) Kontrolcusu
================================================================================
 LDPlayer / BlueStacks gibi emulatorlere ADB uzerinden baglanir; dokunma,
 kaydirma, uzun basma, ekran goruntusu alma ve ekran boyutu sorgulama
 islemlerini yapar.

 Tum metodlar try/except ile korunur ve hata durumunda Turkce aciklama basar.
 Hicbir koordinat veya yol hardcode edilmez; degerler config.py'dan gelir.

 Ornek:
   adb = ADBController(serial="emulator-5554")
   if adb.is_connected():
       adb.tap(800, 450)
       path = adb.screenshot("data/screenshots/ekran.png")
================================================================================
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import List, Optional, Tuple

import config


class ADBController:
    """ADB komutlarini guvenli ve tek noktadan yoneten sinif."""

    def __init__(
        self,
        serial: Optional[str] = None,
        adb_path: Optional[str] = None,
        auto_connect: bool = True,
    ) -> None:
        """
        ADBController nesnesini olusturur ve baglantiyi dogrular.

        Args:
            serial (Optional[str]): Cihaz seriali. None ise config.ADB_SERIAL kullanilir.
            adb_path (Optional[str]): adb.exe yolu. None ise config.ADB_PATH kullanilir.
            auto_connect (bool): True ise baslangicta baglanti kontrolu/denemesi yapilir.

        Returns:
            None
        """
        self.serial: str = serial or config.ADB_SERIAL
        self.adb_path: Optional[str] = adb_path or config.ADB_PATH
        self.timeout: int = config.ADB_TIMEOUT
        self.tap_delay: float = config.ADB_DEFAULT_TAP_DELAY
        self.dry_run: bool = config.DRY_RUN
        self._screen_size: Optional[Tuple[int, int]] = None
        self._last_error: str = ""

        print(f"[ADB] Kontrolcu hazirlandi -> serial: {self.serial}")
        if self.adb_path:
            print(f"[ADB] adb yolu          -> {self.adb_path}")
        else:
            print("[!]   adb bulunamadi. scripts/setup_adb.ps1 calistirmayi deneyin.")

        if auto_connect and not self.is_connected():
            print("[!]   Cihaz bagli degil, otomatik baglanma deneniyor...")
            self.connect()

    # -------------------------------------------------------------------------
    # TEMEL KOMUT CALISTIRICI
    # -------------------------------------------------------------------------
    def _adb_base(self) -> List[str]:
        """
        Kullanilacak temel adb komut listesini uretir (-s serial dahil).

        Returns:
            List[str]: ["adb", "-s", "emulator-5554"] benzeri liste.
        """
        executable = self.adb_path or "adb"
        if self.serial:
            return [executable, "-s", self.serial]
        return [executable]

    def _run(
        self,
        args: List[str],
        timeout: Optional[int] = None,
        binary: bool = False,
    ) -> subprocess.CompletedProcess:
        """
        Verilen adb argumanlarini subprocess ile calistirir.

        Args:
            args (List[str]): adb'ye verilecek argumanlar (orn. ["shell", "wm", "size"]).
            timeout (Optional[int]): Komut zaman asimi (saniye).
            binary (bool): True ise cikti bytes olarak alinir (ekran goruntusu icin).

        Returns:
            subprocess.CompletedProcess: Komut sonucu (stdout, stderr, returncode).
        """
        command = self._adb_base() + args
        try:
            return subprocess.run(
                command,
                capture_output=True,
                timeout=timeout or self.timeout,
                check=False,
            )
        except FileNotFoundError:
            self._last_error = (
                "ADB calistirilabilir dosyasi bulunamadi. platform-tools kurulu mu?"
            )
            print(f"[!] {self._last_error}")
        except subprocess.TimeoutExpired:
            self._last_error = f"ADB komutu zaman asimina ugradi: {' '.join(command)}"
            print(f"[!] {self._last_error}")
        except Exception as error:
            self._last_error = f"ADB komutu calistirilamadi: {error}"
            print(f"[!] {self._last_error}")
        return subprocess.CompletedProcess(command, 1, b"", str(self._last_error).encode())

    def _text(self, result: subprocess.CompletedProcess) -> str:
        """
        Komut ciktisini guvenli sekilde metne cevirir.

        Args:
            result (subprocess.CompletedProcess): _run() ciktisi.

        Returns:
            str: stdout metni (hata varsa bos string).
        """
        try:
            output = result.stdout
            if isinstance(output, bytes):
                return output.decode("utf-8", errors="ignore").strip()
            return str(output).strip()
        except Exception as error:
            print(f"[!] ADB cikti okuma hatasi: {error}")
            return ""

    # -------------------------------------------------------------------------
    # BAGLANTI
    # -------------------------------------------------------------------------
    def list_devices(self) -> List[str]:
        """
        Bagli adb cihazlarinin seri numaralarini dondurur.

        Returns:
            List[str]: Cihaz seri listesi (orn. ["emulator-5554"]).
        """
        devices: List[str] = []
        try:
            result = self._run(["devices"])
            for line in self._text(result).splitlines():
                line = line.strip()
                if not line or line.lower().startswith("list of devices"):
                    continue
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    devices.append(parts[0])
        except Exception as error:
            print(f"[!] Cihaz listesi alinamadi: {error}")
        return devices

    def is_connected(self) -> bool:
        """
        Hedef cihazin bagli ve yetkili olup olmadigini kontrol eder.

        Returns:
            bool: True -> cihaz hazir, False -> bagli degil/yetkisiz/yok.
        """
        try:
            if self.dry_run:
                print("[ADB] DRY_RUN aktif: baglanti kontrolu atlandi (True kabul).")
                return True
            devices = self.list_devices()
            if self.serial in devices:
                print(f"[OK]  Cihaz bagli: {self.serial}")
                return True
            if devices:
                print(f"[!]   {self.serial} bulunamadi. Bagli cihazlar: {', '.join(devices)}")
            else:
                print("[!]   Hicbir ADB cihazi bagli degil.")
            return False
        except Exception as error:
            print(f"[!] Baglanti kontrolu hatasi: {error}")
            return False

    def connect(self, address: Optional[str] = None) -> bool:
        """
        Emulator/cihaza TCP uzerinden baglanmayi dener (orn. 127.0.0.1:5555).

        Args:
            address (Optional[str]): Baglanilacak adres. None ise config.ADB_CONNECT_ADDRESS.

        Returns:
            bool: True -> baglanti basarili, False -> basarisiz.
        """
        target = address or config.ADB_CONNECT_ADDRESS
        try:
            print(f"[ADB] Baglaniliyor -> {target}")
            result = self._run(["connect", target])
            output = self._text(result)
            if "connected" in output.lower():
                print(f"[OK]  Baglanti kuruldu: {output}")
                if not self.serial or self.serial == config.ADB_SERIAL:
                    self.serial = target
                return True
            print(f"[!]   Baglanti kurulamadi: {output or self._last_error}")
            return False
        except Exception as error:
            print(f"[!] Baglanti hatasi: {error}")
            return False

    def disconnect(self) -> bool:
        """
        Mevcut ADB baglantisini kapatir.

        Returns:
            bool: True -> islem basarili.
        """
        try:
            self._run(["disconnect", self.serial])
            print(f"[ADB] Baglanti kapatildi: {self.serial}")
            return True
        except Exception as error:
            print(f"[!] Baglanti kapatma hatasi: {error}")
            return False

    # -------------------------------------------------------------------------
    # DOKUNMA ISLEMLERI
    # -------------------------------------------------------------------------
    def tap(self, x: int, y: int, delay: Optional[float] = None) -> bool:
        """
        Ekranda verilen koordinata tek dokunus yapar.

        Args:
            x (int): X koordinati (piksel).
            y (int): Y koordinati (piksel).
            delay (Optional[float]): Tiklamadan sonra beklenecek saniye.

        Returns:
            bool: True -> tiklama gonderildi, False -> hata olustu.
        """
        try:
            if self.dry_run:
                print(f"[ADB] (DRY_RUN) tap -> x={x}, y={y}")
                return True
            result = self._run(["shell", "input", "tap", str(int(x)), str(int(y))])
            if result.returncode != 0:
                print(f"[!] Tiklama basarisiz ({x}, {y}): {self._last_error}")
                return False
            print(f"[ADB] TIKLA -> x={x}, y={y}")
            time.sleep(delay if delay is not None else self.tap_delay)
            return True
        except Exception as error:
            print(f"[!] Tiklama hatasi ({x}, {y}): {error}")
            return False

    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: int = 300,
    ) -> bool:
        """
        Ekranda iki nokta arasinda kaydirma (swipe) yapar.

        Args:
            x1 (int): Baslangic X.
            y1 (int): Baslangic Y.
            x2 (int): Bitis X.
            y2 (int): Bitis Y.
            duration (int): Kaydirma suresi (milisaniye).

        Returns:
            bool: True -> kaydirma gonderildi.
        """
        try:
            if self.dry_run:
                print(f"[ADB] (DRY_RUN) swipe -> ({x1},{y1}) -> ({x2},{y2}) {duration}ms")
                return True
            result = self._run(
                [
                    "shell",
                    "input",
                    "swipe",
                    str(int(x1)),
                    str(int(y1)),
                    str(int(x2)),
                    str(int(y2)),
                    str(int(duration)),
                ]
            )
            if result.returncode != 0:
                print(f"[!] Kaydirma basarisiz: {self._last_error}")
                return False
            print(f"[ADB] SWIPE -> ({x1},{y1}) -> ({x2},{y2}) / {duration}ms")
            time.sleep(self.tap_delay)
            return True
        except Exception as error:
            print(f"[!] Kaydirma hatasi: {error}")
            return False

    def long_press(self, x: int, y: int, duration: int = 1000) -> bool:
        """
        Verilen noktada uzun basma hareketi yapar (ayni noktaya swipe ile).

        Args:
            x (int): X koordinati.
            y (int): Y koordinati.
            duration (int): Basma suresi (milisaniye).

        Returns:
            bool: True -> islem gonderildi.
        """
        try:
            if self.dry_run:
                print(f"[ADB] (DRY_RUN) long_press -> x={x}, y={y}, {duration}ms")
                return True
            result = self._run(
                [
                    "shell",
                    "input",
                    "swipe",
                    str(int(x)),
                    str(int(y)),
                    str(int(x)),
                    str(int(y)),
                    str(int(duration)),
                ]
            )
            if result.returncode != 0:
                print(f"[!] Uzun basma basarisiz: {self._last_error}")
                return False
            print(f"[ADB] UZUN BAS -> x={x}, y={y} / {duration}ms")
            time.sleep(self.tap_delay)
            return True
        except Exception as error:
            print(f"[!] Uzun basma hatasi: {error}")
            return False

    def key_event(self, keycode: int) -> bool:
        """
        Cihaza tus olayi gonderir (orn. 4 = geri, 3 = home).

        Args:
            keycode (int): Android keycode numarasi.

        Returns:
            bool: True -> olay gonderildi.
        """
        try:
            self._run(["shell", "input", "keyevent", str(int(keycode))])
            time.sleep(self.tap_delay)
            print(f"[ADB] TUS -> keycode={keycode}")
            return True
        except Exception as error:
            print(f"[!] Tus olayi hatasi: {error}")
            return False

    # -------------------------------------------------------------------------
    # EKRAN GORUNTUSU
    # -------------------------------------------------------------------------
    def screenshot(self, save_path: str, use_exec_out: bool = True) -> Optional[str]:
        """
        Cihaz ekran goruntusunu alip bilgisayara kaydeder.

        Iki yontem dener:
          1) adb exec-out screencap -p  (hizli, dogrudan stdout)
          2) adb shell screencap -> /sdcard/... -> adb pull (yedek yontem)

        Args:
            save_path (str): Kaydedilecek dosya yolu (PNG).
            use_exec_out (bool): False ise dogrudan pull yontemi kullanilir.

        Returns:
            Optional[str]: Kaydedilen dosyanin yolu, hata olursa None.
        """
        target = Path(save_path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if self.dry_run:
                print(f"[ADB] (DRY_RUN) screenshot -> {target}")
                return str(target)

            if use_exec_out:
                result = self._run(["exec-out", "screencap", "-p"], binary=True)
                data = result.stdout if isinstance(result.stdout, bytes) else b""
                if result.returncode == 0 and data.startswith(b"\x89PNG"):
                    target.write_bytes(data)
                    print(f"[ADB] EKRAN GORUNTUSU -> {target}")
                    return str(target)
                print("[!] exec-out yontemi basarisiz, pull yontemi denenecek...")

            # Yedek yontem: cihazda kaydet, sonra cek
            self._run(["shell", "screencap", "-p", config.ADB_SCREENSHOT_PATH])
            pull_result = self._run(
                ["pull", config.ADB_SCREENSHOT_PATH, str(target)],
                timeout=max(self.timeout, 60),
            )
            if pull_result.returncode == 0 and target.exists():
                print(f"[ADB] EKRAN GORUNTUSU (pull) -> {target}")
                return str(target)
            print(f"[!] Ekran goruntusu alinamadi: {self._last_error}")
            return None
        except Exception as error:
            print(f"[!] Ekran goruntusu hatasi: {error}")
            return None

    def get_screen_size(self, refresh: bool = False) -> Tuple[int, int]:
        """
        Cihaz ekran cozunurlugunu 'wm size' komutu ile sorgular.

        Args:
            refresh (bool): True ise onbellek yok sayilip yeniden sorgulanir.

        Returns:
            Tuple[int, int]: (genislik, yukseklik). Hata olursa config varsayilani.
        """
        default_size = (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        try:
            if self._screen_size is not None and not refresh:
                return self._screen_size

            result = self._run(["shell", "wm", "size"])
            output = self._text(result)
            # Ornek ciktilar: "Physical size: 1600x900" / "Override size: 1280x720"
            for line in output.splitlines():
                if "size:" not in line.lower():
                    continue
                raw = line.split(":", 1)[1].strip()
                if "x" not in raw:
                    continue
                width_str, height_str = raw.split("x", 1)
                self._screen_size = (int(width_str), int(height_str))
                print(f"[ADB] EKRAN BOYUTU -> {self._screen_size[0]}x{self._screen_size[1]}")
                return self._screen_size

            print(f"[!] Ekran boyutu okunamadi, varsayilan kullaniliyor: {default_size}")
            return default_size
        except Exception as error:
            print(f"[!] Ekran boyutu sorgu hatasi: {error}")
            return default_size

    # -------------------------------------------------------------------------
    # YARDIMCILAR
    # -------------------------------------------------------------------------
    def get_last_error(self) -> str:
        """
        Son olusan ADB hatasinin aciklamasini dondurur.

        Returns:
            str: Son hata mesaji (hata yoksa bos string).
        """
        return self._last_error

    def check_app_running(self, package_name: str) -> bool:
        """
        Verilen paketin cihazda calisip calismadigini kontrol eder.

        Args:
            package_name (str): Android paket adi (orn. com.supercell.clashofclans).

        Returns:
            bool: True -> uygulama calisiyor.
        """
        try:
            result = self._run(["shell", "pidof", package_name])
            running = bool(self._text(result))
            status = "calisiyor" if running else "calismiyor"
            print(f"[ADB] {package_name} -> {status}")
            return running
        except Exception as error:
            print(f"[!] Uygulama kontrol hatasi: {error}")
            return False

    def start_app(self, package_name: str, activity: str = "") -> bool:
        """
        Paketi baslatir (monkey ile varsayilan aktivite).

        Args:
            package_name (str): Android paket adi.
            activity (str): Opsiyonel aktivite adi ("com.x/.MainActivity").

        Returns:
            bool: True -> baslatma komutu basarili.
        """
        try:
            if activity:
                result = self._run(["shell", "am", "start", "-n", activity])
            else:
                result = self._run(
                    ["shell", "monkey", "-p", package_name, "-c",
                     "android.intent.category.LAUNCHER", "1"]
                )
            ok = result.returncode == 0
            print(f"[ADB] Uygulama baslatma -> {package_name} ({'OK' if ok else 'HATA'})")
            return ok
        except Exception as error:
            print(f"[!] Uygulama baslatma hatasi: {error}")
            return False

    def wait(self, seconds: float) -> None:
        """
        Belirtilen sure kadar bekler (test/DRY_RUN modunda beklemez).

        Args:
            seconds (float): Beklenecek saniye.

        Returns:
            None
        """
        try:
            if config.TEST_SLEEP_BETWEEN_STATES > 0:
                time.sleep(seconds)
            elif not config.DRY_RUN:
                time.sleep(seconds)
        except Exception as error:
            print(f"[!] Bekleme hatasi: {error}")


if __name__ == "__main__":  # pragma: no cover - elle test
    controller = ADBController(auto_connect=False)
    print(f"Cihazlar    : {controller.list_devices()}")
    print(f"Bagli mi    : {controller.is_connected()}")
    print(f"Ekran boyutu: {controller.get_screen_size()}")
