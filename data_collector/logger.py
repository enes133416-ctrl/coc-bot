"""
================================================================================
 data_collector/logger.py - Oturum Verisi Toplayici
================================================================================
 Botun her oturumu icin ayri bir klasor olusturur ve tum verileri kaydeder:

   data/sessions/20260101_120000/
       session.json      -> oturum ozeti (baslangic, bitis, istatistikler)
       actions.json      -> tum eylemler (tikla, swipe, durum degisimi...)
       loot_checks.json  -> her rakip icin loot kontrolu ve karar
       battles.json      -> savas sonuclari
       errors.json       -> bu oturumda olusan hatalar
       bot.log           -> konsol logu (metin)
       screenshots/      -> eylemlerle ilgili ekran goruntuleri
       errors/           -> hata anindaki ekran goruntuleri

 Ayrica export_for_ai() ile tum oturum verisi TEK bir JSON dosyasinda toplanir.

 Ornek:
   logger = DataLogger()
   logger.log_action("TAP", {"x": 100, "y": 200}, "data/screenshots/a.png")
   logger.log_loot_check({"gold": 900000, "elixir": 800000, "dark": 0}, True)
   logger.export_for_ai()
================================================================================
"""

from __future__ import annotations

import json
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import config


class DataLogger:
    """Oturum bazli veri kaydi tutan sinif."""

    def __init__(
        self,
        base_dir: Optional[str] = None,
        session_name: Optional[str] = None,
        save_screenshots: Optional[bool] = None,
    ) -> None:
        """
        DataLogger nesnesini olusturur ve oturum klasorunu hazirlar.

        Args:
            base_dir (Optional[str]): Oturumlarin kok klasoru. None ise config.SESSIONS_DIR.
            session_name (Optional[str]): Ozel oturum adi. None ise YYYYMMDD_HHMMSS.
            save_screenshots (Optional[bool]): Ekran goruntuleri kopyalansin mi.

        Returns:
            None
        """
        self.base_dir: Path = Path(base_dir) if base_dir else Path(config.SESSIONS_DIR)
        self.save_screenshots: bool = (
            config.SAVE_SCREENSHOTS if save_screenshots is None else bool(save_screenshots)
        )
        self.lock = threading.RLock()

        stamp = session_name or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_name: str = stamp
        self.session_dir: Path = self.base_dir / stamp
        self.screenshots_dir: Path = self.session_dir / "screenshots"
        self.errors_dir: Path = self.session_dir / "errors"

        # Veri listeleri
        self.actions: List[Dict[str, Any]] = []
        self.loot_checks: List[Dict[str, Any]] = []
        self.battles: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.notes: List[str] = []

        self.started_at: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.start_time: float = time.time()
        self.closed: bool = False

        self._prepare_directories()
        print(f"[LOG] Oturum basladi -> {self.session_dir}")

    # -------------------------------------------------------------------------
    # KLASOR / DOSYA HAZIRLIGI
    # -------------------------------------------------------------------------
    def _prepare_directories(self) -> None:
        """
        Oturum klasor yapisini olusturur.

        Returns:
            None
        """
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            self.session_dir.mkdir(parents=True, exist_ok=True)
            self.screenshots_dir.mkdir(parents=True, exist_ok=True)
            self.errors_dir.mkdir(parents=True, exist_ok=True)
        except Exception as error:
            print(f"[!] Oturum klasoru olusturma hatasi: {error}")

    def _write_json(self, file_name: str, data: Any) -> bool:
        """
        Veriyi oturum klasorundeki JSON dosyasina yazar.

        Args:
            file_name (str): Dosya adi (orn. "actions.json").
            data (Any): Yazilacak veri (JSON serilestirilebilir olmali).

        Returns:
            bool: True -> kayit basarili.
        """
        try:
            target = self.session_dir / file_name
            temp = target.with_suffix(target.suffix + ".tmp")
            with open(temp, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, ensure_ascii=False, default=str)
            temp.replace(target)
            return True
        except Exception as error:
            print(f"[!] JSON yazma hatasi ({file_name}): {error}")
            return False

    def _append_text_log(self, level: str, message: str) -> None:
        """
        Oturum klasorundeki bot.log dosyasina satir ekler.

        Args:
            level (str): Log seviyesi (INFO, WARN, ERROR).
            message (str): Log mesaji.

        Returns:
            None
        """
        try:
            if not config.LOG_TO_FILE:
                return
            line = (
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                f"[{level}] {message}\n"
            )
            with open(self.session_dir / "bot.log", "a", encoding="utf-8") as handle:
                handle.write(line)
        except Exception as error:
            print(f"[!] Metin log yazma hatasi: {error}")

    def _copy_screenshot(
        self,
        screenshot_path: Optional[str],
        target_dir: Path,
        prefix: str = "shot",
    ) -> Optional[str]:
        """
        Ekran goruntusunu oturum klasorune kopyalar.

        Args:
            screenshot_path (Optional[str]): Kaynak dosya.
            target_dir (Path): Hedef klasor.
            prefix (str): Dosya adi on eki.

        Returns:
            Optional[str]: Kopyalanan dosyanin yolu veya None.
        """
        try:
            if not self.save_screenshots or not screenshot_path:
                return None
            source = Path(screenshot_path)
            if not source.exists():
                return None
            target_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%H%M%S_%f")[:-3]
            target = target_dir / f"{prefix}_{stamp}_{source.name}"
            shutil.copy2(source, target)
            return str(target)
        except Exception as error:
            print(f"[!] Ekran goruntusu kopyalama hatasi: {error}")
            return None

    # -------------------------------------------------------------------------
    # KAYIT METODLARI
    # -------------------------------------------------------------------------
    def log_action(
        self,
        action_type: str,
        details: Optional[Dict[str, Any]] = None,
        screenshot_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Tek bir eylemi kaydeder ve ekran goruntusunu kopyalar.

        Args:
            action_type (str): Eylem tipi (orn. "TAP", "STATE_CHANGE").
            details (Optional[Dict[str, Any]]): Eylem detaylari.
            screenshot_path (Optional[str]): Ilgili ekran goruntusu.

        Returns:
            Dict[str, Any]: Kaydedilen kayit sozlugu.
        """
        record: Dict[str, Any] = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed": round(time.time() - self.start_time, 2),
            "type": str(action_type),
            "details": details or {},
            "screenshot": None,
        }
        try:
            if not config.LOG_ALL_ACTIONS:
                return record
            with self.lock:
                copied = self._copy_screenshot(screenshot_path, self.screenshots_dir, "action")
                record["screenshot"] = copied or screenshot_path
                self.actions.append(record)
                self._write_json("actions.json", self.actions)
                self._append_text_log("INFO", f"ACTION {action_type} -> {record['details']}")
            return record
        except Exception as error:
            print(f"[!] Eylem kaydi hatasi: {error}")
            return record

    def log_error(
        self,
        error_type: str,
        description: str,
        screenshot_path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Bir hatayi kaydeder; ekran goruntusunu errors/ klasorune kopyalar.

        Args:
            error_type (str): Hata tipi (orn. "ADB_ERROR").
            description (str): Turkce aciklama.
            screenshot_path (Optional[str]): Hata anindaki ekran goruntusu.
            context (Optional[Dict[str, Any]]): Ek baglam (state, dongu no...).

        Returns:
            Dict[str, Any]: Kaydedilen hata sozlugu.
        """
        record: Dict[str, Any] = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed": round(time.time() - self.start_time, 2),
            "error_type": str(error_type),
            "description": str(description),
            "context": context or {},
            "screenshot": None,
        }
        try:
            with self.lock:
                copied = self._copy_screenshot(screenshot_path, self.errors_dir, "error")
                record["screenshot"] = copied or screenshot_path
                self.errors.append(record)
                self._write_json("errors.json", self.errors)
                self._append_text_log("ERROR", f"{error_type}: {description}")
            print(f"[LOG] Hata kaydedildi -> {error_type}")
            return record
        except Exception as error:
            print(f"[!] Hata kaydi yazilamadi: {error}")
            return record

    def log_loot_check(
        self,
        loot: Dict[str, Any],
        accepted: bool,
        screenshot_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Loot kontrolunu (kabul/red karari ile) kaydeder.

        Args:
            loot (Dict[str, Any]): {"gold", "elixir", "dark", "total"}
            accepted (bool): True -> saldiri kabul edildi.
            screenshot_path (Optional[str]): Rakip ekran goruntusu.

        Returns:
            Dict[str, Any]: Kaydedilen kayit sozlugu.
        """
        record: Dict[str, Any] = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed": round(time.time() - self.start_time, 2),
            "loot": dict(loot or {}),
            "accepted": bool(accepted),
            "screenshot": None,
        }
        try:
            with self.lock:
                copied = self._copy_screenshot(screenshot_path, self.screenshots_dir, "loot")
                record["screenshot"] = copied or screenshot_path
                self.loot_checks.append(record)
                self._write_json("loot_checks.json", self.loot_checks)
                karar = "KABUL" if accepted else "RED"
                self._append_text_log("INFO", f"LOOT {karar} -> {record['loot']}")
            return record
        except Exception as error:
            print(f"[!] Loot kaydi hatasi: {error}")
            return record

    def log_battle_result(
        self,
        plan_name: str,
        success: bool,
        stars: Optional[int] = None,
        loot_gained: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Savas sonucunu kaydeder.

        Args:
            plan_name (str): Kullanilan savas plani adi.
            success (bool): Savas basarili mi (plan tamamlandi mi).
            stars (Optional[int]): Kazanilan yildiz sayisi (bilinmiyorsa None).
            loot_gained (Optional[Dict[str, Any]]): Elde edilen loot tahmini.

        Returns:
            Dict[str, Any]: Kaydedilen kayit sozlugu.
        """
        record: Dict[str, Any] = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed": round(time.time() - self.start_time, 2),
            "plan": str(plan_name),
            "success": bool(success),
            "stars": stars,
            "loot": dict(loot_gained or {}),
        }
        try:
            with self.lock:
                self.battles.append(record)
                self._write_json("battles.json", self.battles)
                self._append_text_log(
                    "INFO",
                    f"BATTLE {plan_name} -> {'BASARILI' if success else 'BASARISIZ'} "
                    f"yildiz={stars} loot={record['loot']}",
                )
            return record
        except Exception as error:
            print(f"[!] Savas kaydi hatasi: {error}")
            return record

    def log_note(self, note: str) -> None:
        """
        Oturuma serbest metin not ekler.

        Args:
            note (str): Not metni.

        Returns:
            None
        """
        try:
            with self.lock:
                self.notes.append(str(note))
                self._append_text_log("NOTE", str(note))
        except Exception as error:
            print(f"[!] Not kaydi hatasi: {error}")

    # -------------------------------------------------------------------------
    # ISTATISTIK
    # -------------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        """
        Oturum istatistiklerini dondurur.

        Returns:
            Dict[str, Any]: Toplam eylem, hata, savas ve loot istatistikleri.
        """
        try:
            with self.lock:
                accepted = sum(1 for item in self.loot_checks if item.get("accepted"))
                rejected = sum(1 for item in self.loot_checks if not item.get("accepted"))
                won = sum(1 for item in self.battles if item.get("success"))
                total_loot = sum(
                    int(item.get("loot", {}).get("total", 0)) for item in self.battles
                )
                return {
                    "session": self.session_name,
                    "session_dir": str(self.session_dir),
                    "started_at": self.started_at,
                    "duration_seconds": round(time.time() - self.start_time, 2),
                    "actions": len(self.actions),
                    "loot_checks": len(self.loot_checks),
                    "loot_accepted": accepted,
                    "loot_rejected": rejected,
                    "battles": len(self.battles),
                    "battles_success": won,
                    "battles_failed": len(self.battles) - won,
                    "total_loot": total_loot,
                    "errors": len(self.errors),
                    "notes": len(self.notes),
                }
        except Exception as error:
            print(f"[!] Istatistik hatasi: {error}")
            return {"session": self.session_name, "errors": len(self.errors)}

    def print_stats(self) -> None:
        """
        Oturum istatistiklerini Turkce olarak konsola yazar.

        Returns:
            None
        """
        try:
            stats = self.get_stats()
            print("=" * 78)
            print(f" OTURUM OZETI - {stats.get('session')}")
            print("=" * 78)
            print(f" Klasor         : {stats.get('session_dir')}")
            print(f" Baslangic      : {stats.get('started_at')}")
            print(f" Sure           : {stats.get('duration_seconds')} saniye")
            print(f" Eylem sayisi   : {stats.get('actions')}")
            print(f" Loot kontrolu  : {stats.get('loot_checks')} "
                  f"(kabul: {stats.get('loot_accepted')}, red: {stats.get('loot_rejected')})")
            print(f" Savas          : {stats.get('battles')} "
                  f"(basarili: {stats.get('battles_success')}, "
                  f"basarisiz: {stats.get('battles_failed')})")
            print(f" Toplam loot    : {stats.get('total_loot', 0):,}")
            print(f" Hata           : {stats.get('errors')}")
            print("=" * 78)
        except Exception as error:
            print(f"[!] Ozet yazma hatasi: {error}")

    # -------------------------------------------------------------------------
    # DISA AKTARMA
    # -------------------------------------------------------------------------
    def export_for_ai(self, output_path: Optional[str] = None) -> str:
        """
        Tum oturum verisini tek bir JSON dosyasinda toplar.

        Args:
            output_path (Optional[str]): Hedef dosya. None ise oturum klasorundeki
                                         ai_export.json dosyasidir.

        Returns:
            str: Olusturulan dosyanin yolu.
        """
        payload: Dict[str, Any] = {}
        try:
            with self.lock:
                payload = {
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "session": self.session_name,
                    "started_at": self.started_at,
                    "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "stats": self.get_stats(),
                    "actions": self.actions,
                    "loot_checks": self.loot_checks,
                    "battles": self.battles,
                    "errors": self.errors,
                    "notes": self.notes,
                }
            target = Path(output_path) if output_path else (self.session_dir / "ai_export.json")
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False, default=str)
            print(f"[OK]  [LOG] Oturum verisi disa aktarildi -> {target}")
            return str(target)
        except Exception as error:
            print(f"[!] Disa aktarma hatasi: {error}")
            fallback = str(self.session_dir / "ai_export.json")
            return fallback

    def finish(self) -> str:
        """
        Oturumu kapatir: ozet dosyasini yazar ve AI export'unu olusturur.

        Returns:
            str: Olusturulan ai_export.json dosyasinin yolu.
        """
        try:
            with self.lock:
                self.closed = True
                summary = self.get_stats()
                summary["notes"] = self.notes
                self._write_json("session.json", summary)
                self._append_text_log("INFO", f"Oturum kapatildi: {summary}")
            self.print_stats()
            return self.export_for_ai()
        except Exception as error:
            print(f"[!] Oturum kapatma hatasi: {error}")
            return str(self.session_dir / "ai_export.json")

    def __enter__(self) -> "DataLogger":
        """
        with blogu destegi.

        Returns:
            DataLogger: Kendisi.
        """
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """
        with blogu cikisinda oturumu kapatir.

        Args:
            exc_type (Any): Istisna tipi.
            exc_value (Any): Istisna degeri.
            traceback (Any): Iz yigini.

        Returns:
            None
        """
        try:
            self.finish()
        except Exception as error:
            print(f"[!] Cikis kapatma hatasi: {error}")


if __name__ == "__main__":  # pragma: no cover - elle test
    logger = DataLogger()
    logger.log_action("TEST", {"mesaj": "deneme"})
    logger.log_loot_check({"gold": 900_000, "elixir": 800_000, "dark": 0, "total": 1_700_000}, True)
    logger.log_battle_result("varsayilan", True, stars=2, loot_gained={"total": 1_700_000})
    logger.print_stats()
    print(f"Export: {logger.export_for_ai()}")
