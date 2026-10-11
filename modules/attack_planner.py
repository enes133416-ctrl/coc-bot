"""
================================================================================
 modules/attack_planner.py - Savas Plani Kayit / Oynatma Modulu
================================================================================
 Kullanicinin elle yaptigi saldiriyi adim adim kaydeder, data/battle_plans.json
dosyasinda saklar ve ayni zamanlamayla (hiz carpani ile) tekrar oynatir.

 Kayit formati (ornek):
   {
     "varsayilan": {
       "name": "varsayilan",
       "created_at": "2026-01-01 12:00:00",
       "duration": 42.5,
       "speed": 1.0,
       "actions": [
         {"time": 0.0, "x": 800, "y": 450, "action_type": "tap",
          "label": "ordu birak", "metadata": {}},
         {"time": 1.2, "x": 900, "y": 460, "action_type": "swipe",
          "label": "kaydir", "metadata": {"duration_ms": 300}}
       ]
     }
   }

 Oynatma, orijinal zamanlama farklarini (delta) kullanarak birebir tekrarlar;
 speed parametresi ile tum bekleme sureleri olceklenir.

 Ornek:
   planner = AttackPlanner()
   planner.start_recording("koy_saldirisi")
   planner.record_action(800, 450, "tap", "barbar birak")
   planner.stop_recording()
   planner.execute("koy_saldirisi", adb, speed=1.0)
================================================================================
"""

from __future__ import annotations

import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import config


class AttackPlanner:
    """Savas planlarini kaydeden, listeleyen ve oynatan sinif."""

    def __init__(self, plans_path: Optional[str] = None) -> None:
        """
        AttackPlanner nesnesini olusturur ve plan dosyasini yukler.

        Args:
            plans_path (Optional[str]): Plan dosyasi yolu.
                                        None ise config.BATTLE_PLANS_PATH.

        Returns:
            None
        """
        self.plans_path: Path = Path(plans_path) if plans_path else Path(config.BATTLE_PLANS_PATH)
        self.plans: Dict[str, Dict[str, Any]] = {}
        self.recording: bool = False
        self.current_name: Optional[str] = None
        self.current_actions: List[Dict[str, Any]] = []
        self.record_start_time: float = 0.0
        self.last_record_time: float = 0.0

        self.load_plans()

    # -------------------------------------------------------------------------
    # DOSYA ISLEMLERI
    # -------------------------------------------------------------------------
    def load_plans(self) -> Dict[str, Dict[str, Any]]:
        """
        Planlari JSON dosyasindan yukler; dosya yoksa bos yapi olusturur.

        Returns:
            Dict[str, Dict[str, Any]]: Yuklenen planlar sozlugu.
        """
        try:
            self.plans_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.plans_path.exists():
                self.plans = {}
                self._write_json(self.plans)
                print(f"[PLAN] Plan dosyasi olusturuldu (bos) -> {self.plans_path}")
                return self.plans

            with open(self.plans_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                print("[!] Plan dosyasi formati hatali, sifirlaniyor.")
                data = {}
            self.plans = data
            print(f"[PLAN] {len(self.plans)} plan yuklendi -> {self.plans_path}")
            return self.plans
        except json.JSONDecodeError as error:
            print(f"[!] Plan dosyasi bozuk JSON iceriyor: {error}")
            self.plans = {}
            return self.plans
        except Exception as error:
            print(f"[!] Plan yukleme hatasi: {error}")
            self.plans = {}
            return self.plans

    def _write_json(self, data: Dict[str, Any]) -> bool:
        """
        Veriyi plan dosyasina yazar.

        Args:
            data (Dict[str, Any]): Yazilacak veri.

        Returns:
            bool: True -> kayit basarili.
        """
        try:
            self.plans_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.plans_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=4, ensure_ascii=False)
            return True
        except Exception as error:
            print(f"[!] Plan kaydetme hatasi: {error}")
            return False

    def save_plans(self) -> bool:
        """
        Bellekteki planlari dosyaya yazar.

        Returns:
            bool: True -> kayit basarili.
        """
        return self._write_json(self.plans)

    # -------------------------------------------------------------------------
    # KAYIT
    # -------------------------------------------------------------------------
    def start_recording(self, name: Optional[str] = None) -> str:
        """
        Yeni bir savas plani kaydini baslatir.

        Args:
            name (Optional[str]): Plan adi. None ise zaman damgali isim uretilir.

        Returns:
            str: Baslatilan planin adi.
        """
        try:
            self.current_name = (
                name.strip() if name and name.strip() else f"plan_{datetime.now():%Y%m%d_%H%M%S}"
            )
            self.current_actions = []
            self.recording = True
            self.record_start_time = time.time()
            self.last_record_time = self.record_start_time
            print("=" * 78)
            print(f" [PLAN] KAYIT BASLADI -> '{self.current_name}'")
            print(" [PLAN] Her hareket icin record_action() cagrilir.")
            print(" [PLAN] Bitirmek icin stop_recording() kullanin.")
            print("=" * 78)
            return self.current_name
        except Exception as error:
            print(f"[!] Kayit baslatma hatasi: {error}")
            self.recording = False
            return ""

    def record_action(
        self,
        x: int,
        y: int,
        action_type: str = "tap",
        label: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Tek bir hareketi kayit listesine ekler.

        Args:
            x (int): X koordinati.
            y (int): Y koordinati.
            action_type (str): "tap", "swipe", "long_press", "key" gibi eylem tipi.
            label (str): Kullanici dostu etiket (orn. "ejder birak").
            metadata (Optional[Dict[str, Any]]): Ek bilgiler (bitis koordinati, sure...).

        Returns:
            bool: True -> kayit eklendi.
        """
        try:
            if not self.recording:
                print("[!] Kayit aktif degil! Once start_recording() cagirin.")
                return False

            now = time.time()
            elapsed = now - self.record_start_time
            delay = max(0.0, now - self.last_record_time)
            self.last_record_time = now

            entry: Dict[str, Any] = {
                "time": round(elapsed, 3),
                "delay": round(delay, 3),
                "x": int(x),
                "y": int(y),
                "action_type": str(action_type),
                "label": str(label),
                "metadata": dict(metadata) if metadata else {},
            }
            self.current_actions.append(entry)
            print(
                f"[PLAN] + Kayit #{len(self.current_actions)} | t={entry['time']:.2f}s | "
                f"{entry['action_type']} ({entry['x']},{entry['y']}) {entry['label']}"
            )
            return True
        except Exception as error:
            print(f"[!] Kayit ekleme hatasi: {error}")
            return False

    def stop_recording(self) -> Optional[str]:
        """
        Kaydi durdurur ve plani JSON dosyasina kaydeder.

        Returns:
            Optional[str]: Kaydedilen planin adi veya hata halinde None.
        """
        try:
            if not self.recording:
                print("[!] Aktif kayit yok.")
                return None

            self.recording = False
            if not self.current_actions:
                print("[!] Hic hareket kaydedilmedi, plan olusturulmadi.")
                self.current_name = None
                return None

            duration = round(time.time() - self.record_start_time, 3)
            name = self.current_name or f"plan_{datetime.now():%Y%m%d_%H%M%S}"
            self.plans[name] = {
                "name": name,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "duration": duration,
                "speed": 1.0,
                "action_count": len(self.current_actions),
                "actions": list(self.current_actions),
            }
            if self._write_json(self.plans):
                print(
                    f"[OK]  [PLAN] '{name}' kaydedildi -> "
                    f"{len(self.current_actions)} hareket, {duration} saniye"
                )
                self.current_name = None
                self.current_actions = []
                return name
            return None
        except Exception as error:
            print(f"[!] Kayit durdurma hatasi: {error}")
            self.recording = False
            return None

    def cancel_recording(self) -> None:
        """
        Aktif kaydi iptal eder (kaydetmez).

        Returns:
            None
        """
        try:
            self.recording = False
            self.current_actions = []
            self.current_name = None
            print("[PLAN] Kayit iptal edildi.")
        except Exception as error:
            print(f"[!] Iptal hatasi: {error}")

    # -------------------------------------------------------------------------
    # OYNATMA
    # -------------------------------------------------------------------------
    def execute(
        self,
        plan_name: Optional[str] = None,
        adb: Any = None,
        speed: float = 1.0,
    ) -> bool:
        """
        Kayitli bir savas planini orijinal zamanlamayla oynatir.

        Args:
            plan_name (Optional[str]): Oynatilacak plan adi. None ise config.ACTIVE_PLAN.
            adb (Any): ADBController nesnesi (tap/swipe/long_press icermeli).
            speed (float): Hiz carpani. 1.0 = orijinal, 0.5 = iki kat yavas,
                           2.0 = iki kat hizli.

        Returns:
            bool: True -> plan tamamen oynatildi.
        """
        try:
            name = plan_name or config.ACTIVE_PLAN
            if adb is None:
                print("[!] ADB nesnesi verilmedi, plan oynatilamaz.")
                return False
            if name not in self.plans:
                print(f"[!] '{name}' plani bulunamadi! Mevcut planlar: {self.list_names()}")
                return False

            speed_value = float(speed) if speed and speed > 0 else 1.0
            plan = self.plans[name]
            actions: List[Dict[str, Any]] = list(plan.get("actions", []))
            if not actions:
                print(f"[!] '{name}' planinda hareket yok.")
                return False

            print("=" * 78)
            print(f" [PLAN] OYNATILIYOR -> '{name}' ({len(actions)} hareket, hiz={speed_value}x)")
            print("=" * 78)

            start = time.time()
            for index, action in enumerate(actions, start=1):
                expected_time = float(action.get("time", 0.0))
                elapsed = time.time() - start
                wait = (expected_time - elapsed) / speed_value
                if wait > 0:
                    time.sleep(wait)

                ok = self._execute_single(action, adb)
                print(
                    f" [PLAN] {index}/{len(actions)} | t={expected_time:.2f}s | "
                    f"{action.get('action_type')} ({action.get('x')},{action.get('y')}) "
                    f"{action.get('label', '')} -> {'OK' if ok else 'HATA'}"
                )
                if not ok:
                    print("[!] Adim basarisiz oldu ancak plan devam ediyor.")

            total = round(time.time() - start, 2)
            print(f"[OK]  [PLAN] '{name}' tamamlandi ({total} saniye).")
            return True
        except Exception as error:
            print(f"[!] Plan oynatma hatasi: {error}")
            return False

    def _execute_single(self, action: Dict[str, Any], adb: Any) -> bool:
        """
        Tek bir plan adimini uygular.

        Args:
            action (Dict[str, Any]): Kayitli hareket.
            adb (Any): ADBController nesnesi.

        Returns:
            bool: True -> adim basariyla uygulandi.
        """
        try:
            action_type = str(action.get("action_type", "tap")).lower()
            x = int(action.get("x", 0))
            y = int(action.get("y", 0))
            metadata = action.get("metadata", {}) or {}

            if action_type == "tap":
                return bool(adb.tap(x, y))
            if action_type == "long_press":
                duration = int(metadata.get("duration", metadata.get("duration_ms", 1000)))
                return bool(adb.long_press(x, y, duration))
            if action_type == "swipe":
                x2 = int(metadata.get("x2", x))
                y2 = int(metadata.get("y2", y))
                duration = int(metadata.get("duration", metadata.get("duration_ms", 300)))
                return bool(adb.swipe(x, y, x2, y2, duration))
            if action_type == "key":
                keycode = int(metadata.get("keycode", x))
                return bool(adb.key_event(keycode))
            if action_type == "wait":
                time.sleep(float(metadata.get("seconds", 1.0)))
                return True

            print(f"[!] Bilinmeyen eylem tipi: {action_type}, 'tap' olarak uygulaniyor.")
            return bool(adb.tap(x, y))
        except Exception as error:
            print(f"[!] Adim uygulama hatasi: {error}")
            return False

    # -------------------------------------------------------------------------
    # PLAN YONETIMI
    # -------------------------------------------------------------------------
    def list_plans(self) -> Dict[str, Dict[str, Any]]:
        """
        Mevcut planlari tablo halinde konsola basar.

        Returns:
            Dict[str, Dict[str, Any]]: Planlar sozlugu.
        """
        try:
            self.load_plans()
            print("=" * 78)
            print(" KAYITLI SAVAS PLANLARI")
            print("=" * 78)
            if not self.plans:
                print(" (Henuz plan yok. Kaydetmek icin: python main.py -> [2])")
                print("=" * 78)
                return self.plans

            print(f" {'PLAN ADI':<24} {'HAREKET':>8} {'SURE':>10} {'OLUSTURMA':>20}")
            print("-" * 78)
            for name, plan in self.plans.items():
                count = plan.get("action_count", len(plan.get("actions", [])))
                duration = plan.get("duration", 0.0)
                created = plan.get("created_at", "-")
                print(f" {name:<24} {count:>8} {duration:>8.2f}s {created:>20}")
            print("=" * 78)
            return self.plans
        except Exception as error:
            print(f"[!] Plan listeleme hatasi: {error}")
            return self.plans

    def list_names(self) -> List[str]:
        """
        Kayitli plan adlarini dondurur.

        Returns:
            List[str]: Plan adlari listesi.
        """
        try:
            return list(self.plans.keys())
        except Exception as error:
            print(f"[!] Plan adlari okunamadi: {error}")
            return []

    def get_plan(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Tek bir plani dondurur.

        Args:
            name (str): Plan adi.

        Returns:
            Optional[Dict[str, Any]]: Plan sozlugu veya None.
        """
        try:
            return self.plans.get(name)
        except Exception as error:
            print(f"[!] Plan okuma hatasi: {error}")
            return None

    def delete_plan(self, name: str) -> bool:
        """
        Kayitli bir plani siler.

        Args:
            name (str): Silinecek plan adi.

        Returns:
            bool: True -> plan silindi.
        """
        try:
            if name not in self.plans:
                print(f"[!] '{name}' plani bulunamadi, silme yapilmadi.")
                return False
            del self.plans[name]
            ok = self._write_json(self.plans)
            if ok:
                print(f"[OK]  [PLAN] '{name}' plani silindi.")
            return ok
        except Exception as error:
            print(f"[!] Plan silme hatasi: {error}")
            return False

    def rename_plan(self, old_name: str, new_name: str) -> bool:
        """
        Bir planin adini degistirir.

        Args:
            old_name (str): Mevcut plan adi.
            new_name (str): Yeni plan adi.

        Returns:
            bool: True -> isim degistirildi.
        """
        try:
            if old_name not in self.plans:
                print(f"[!] '{old_name}' plani bulunamadi.")
                return False
            if new_name in self.plans:
                print(f"[!] '{new_name}' adinda bir plan zaten var.")
                return False
            plan = self.plans.pop(old_name)
            plan["name"] = new_name
            self.plans[new_name] = plan
            return self._write_json(self.plans)
        except Exception as error:
            print(f"[!] Plan yeniden adlandirma hatasi: {error}")
            return False

    # -------------------------------------------------------------------------
    # ICE / DISA AKTARMA
    # -------------------------------------------------------------------------
    def export_plan(self, name: str, path: Optional[str] = None) -> Optional[str]:
        """
        Tek bir plani ayri bir JSON dosyasina aktarir.

        Args:
            name (str): Aktarilacak plan adi.
            path (Optional[str]): Hedef dosya. None ise data/exports/<ad>.json.

        Returns:
            Optional[str]: Aktarilan dosya yolu veya None.
        """
        try:
            plan = self.plans.get(name)
            if plan is None:
                print(f"[!] '{name}' plani bulunamadi.")
                return None
            target = (
                Path(path)
                if path
                else (Path(config.DATA_DIR) / "exports" / f"{name}.json")
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as handle:
                json.dump(plan, handle, indent=4, ensure_ascii=False)
            print(f"[OK]  [PLAN] '{name}' disa aktarildi -> {target}")
            return str(target)
        except Exception as error:
            print(f"[!] Plan disa aktarma hatasi: {error}")
            return None

    def import_plan(self, path: str, new_name: Optional[str] = None) -> Optional[str]:
        """
        Disaridan bir plan JSON dosyasi yukler.

        Args:
            path (str): Yuklenecek dosya yolu.
            new_name (Optional[str]): Yeni plan adi (cakismayi onlemek icin).

        Returns:
            Optional[str]: Eklenen planin adi veya None.
        """
        try:
            source = Path(path)
            if not source.exists():
                print(f"[!] Plan dosyasi bulunamadi: {path}")
                return None
            with open(source, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict) or "actions" not in data:
                print("[!] Gecersiz plan formati (actions alani yok).")
                return None

            name = new_name or str(data.get("name") or source.stem)
            if name in self.plans:
                name = f"{name}_{datetime.now():%Y%m%d_%H%M%S}"
            data["name"] = name
            data.setdefault("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            data.setdefault("duration", 0.0)
            data.setdefault("speed", 1.0)
            data["action_count"] = len(data.get("actions", []))
            self.plans[name] = data
            self._write_json(self.plans)
            print(f"[OK]  [PLAN] '{name}' ice aktarildi ({data['action_count']} hareket).")
            return name
        except json.JSONDecodeError as error:
            print(f"[!] Plan dosyasi bozuk JSON: {error}")
            return None
        except Exception as error:
            print(f"[!] Plan ice aktarma hatasi: {error}")
            return None

    def backup_plans(self) -> Optional[str]:
        """
        Plan dosyasinin zaman damgali yedegini olusturur.

        Returns:
            Optional[str]: Yedek dosya yolu veya None.
        """
        try:
            if not self.plans_path.exists():
                print("[!] Yedeklenecek plan dosyasi yok.")
                return None
            target = Path(config.DATA_DIR) / "backups" / (
                f"battle_plans_{datetime.now():%Y%m%d_%H%M%S}.json"
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.plans_path, target)
            print(f"[OK]  [PLAN] Yedek olusturuldu -> {target}")
            return str(target)
        except Exception as error:
            print(f"[!] Yedekleme hatasi: {error}")
            return None

    def is_recording(self) -> bool:
        """
        Kayit durumunu dondurur.

        Returns:
            bool: True -> kayit aktif.
        """
        return self.recording


if __name__ == "__main__":  # pragma: no cover - elle test
    planner = AttackPlanner()
    planner.list_plans()
