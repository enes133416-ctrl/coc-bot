"""
================================================================================
 tests/test_planner.py - Savas Plani (AttackPlanner) Testleri
================================================================================
 AttackPlanner sinifinin kayit, listeleme, oynatma ve silme davranislarini test
 eder. Gercek ADB baglantisi gerekmez; sahte (fake) bir ADB nesnesi kullanilir.

   test_record_and_playback -> kayit yap, oku, dogru aksiyon sayisi donsun
   test_list_plans           -> plan listesi bos baslar
   test_delete_plan          -> silme sonrasinda plan yoktur
================================================================================
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Proje kokunu yola ekle
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.attack_planner import AttackPlanner  # noqa: E402


class FakeADB:
    """Testler icin ADBController taklidi - cagrilari kaydeder."""

    def __init__(self) -> None:
        """FakeADB nesnesini olusturur."""
        self.calls: List[Tuple[str, int, int]] = []
        self.swipes: List[Tuple[int, int, int, int, int]] = []
        self.long_presses: List[Tuple[int, int, int]] = []
        self.keys: List[int] = []
        self.screen_size: Tuple[int, int] = (1600, 900)

    def tap(self, x: int, y: int, delay: float = 0.0) -> bool:
        """
        Sahte tiklama kaydi.

        Args:
            x (int): X koordinati.
            y (int): Y koordinati.
            delay (float): Bekleme (kullanilmaz).

        Returns:
            bool: Her zaman True.
        """
        self.calls.append(("tap", int(x), int(y)))
        return True

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """
        Sahte kaydirma kaydi.

        Args:
            x1 (int): Baslangic X.
            y1 (int): Baslangic Y.
            x2 (int): Bitis X.
            y2 (int): Bitis Y.
            duration (int): Sure (ms).

        Returns:
            bool: Her zaman True.
        """
        self.swipes.append((int(x1), int(y1), int(x2), int(y2), int(duration)))
        return True

    def long_press(self, x: int, y: int, duration: int = 1000) -> bool:
        """
        Sahte uzun basma kaydi.

        Args:
            x (int): X koordinati.
            y (int): Y koordinati.
            duration (int): Sure (ms).

        Returns:
            bool: Her zaman True.
        """
        self.long_presses.append((int(x), int(y), int(duration)))
        return True

    def key_event(self, keycode: int) -> bool:
        """
        Sahte tus olayi kaydi.

        Args:
            keycode (int): Tus kodu.

        Returns:
            bool: Her zaman True.
        """
        self.keys.append(int(keycode))
        return True

    def get_screen_size(self) -> Tuple[int, int]:
        """
        Sahte ekran boyutu.

        Returns:
            Tuple[int, int]: (1600, 900)
        """
        return self.screen_size


class TestAttackPlanner(unittest.TestCase):
    """AttackPlanner sinifi icin birim testleri."""

    def setUp(self) -> None:
        """Her test icin temiz bir gecici plan dosyasi olusturur."""
        self.temp_dir = tempfile.TemporaryDirectory(prefix="coc_test_planner_")
        self.plans_path = Path(self.temp_dir.name) / "battle_plans.json"
        self.planner = AttackPlanner(plans_path=str(self.plans_path))

    def tearDown(self) -> None:
        """Gecici klasoru temizler."""
        self.temp_dir.cleanup()

    def test_list_plans(self) -> None:
        """Plan listesinin bos baslamasini test eder."""
        planlar = self.planner.list_plans()
        self.assertIsInstance(planlar, dict, "list_plans sozluk dondurmeli.")
        self.assertEqual(len(planlar), 0, "Yeni planda liste bos olmali.")
        self.assertEqual(self.planner.list_names(), [], "Plan adi listesi bos olmali.")
        self.assertTrue(self.plans_path.exists(), "Plan dosyasi olusturulmali.")

    def test_record_and_playback(self) -> None:
        """Kayit yapip oynatildiginda dogru aksiyon sayisinin tekrarlanmasini test eder."""
        name = self.planner.start_recording("test_plani")
        self.assertEqual(name, "test_plani")

        self.assertTrue(self.planner.record_action(100, 200, "tap", "birinci"))
        self.assertTrue(self.planner.record_action(300, 400, "tap", "ikinci"))
        self.assertTrue(
            self.planner.record_action(
                500, 600, "swipe", "kaydir", metadata={"x2": 700, "y2": 800, "duration": 250}
            )
        )

        saved_name = self.planner.stop_recording()
        self.assertEqual(saved_name, "test_plani", "Plan kaydedilmeli.")

        # Dosyadan tekrar oku
        self.assertTrue(self.plans_path.exists(), "Plan dosyasi yazilmali.")
        with open(self.plans_path, "r", encoding="utf-8") as handle:
            payload: Dict[str, Any] = json.load(handle)
        self.assertIn("test_plani", payload, "Plan dosyada bulunmali.")
        self.assertEqual(
            len(payload["test_plani"]["actions"]), 3, "3 aksiyon kaydedilmis olmali."
        )

        # Yeni bir planner ile dosyadan yukle ve oynat
        reloaded = AttackPlanner(plans_path=str(self.plans_path))
        plan = reloaded.get_plan("test_plani")
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan["actions"]), 3, "Yuklenen plan 3 aksiyon icermeli.")

        fake_adb = FakeADB()
        ok = reloaded.execute("test_plani", fake_adb, speed=10.0)
        self.assertTrue(ok, "Plan oynatilmali.")
        self.assertEqual(len(fake_adb.calls), 2, "2 tap uygulanmis olmali.")
        self.assertEqual(fake_adb.calls[0], ("tap", 100, 200))
        self.assertEqual(fake_adb.calls[1], ("tap", 300, 400))
        self.assertEqual(len(fake_adb.swipes), 1, "1 swipe uygulanmis olmali.")
        self.assertEqual(fake_adb.swipes[0], (500, 600, 700, 800, 250))

    def test_record_without_start(self) -> None:
        """Kayit baslatilmadan record_action cagrilirsa False donmesini test eder."""
        self.assertFalse(
            self.planner.record_action(10, 10, "tap", "gecersiz"),
            "Kayit baslatilmadan aksiyon eklenememeli.",
        )

    def test_stop_recording_empty(self) -> None:
        """Bos kayit durduruldugunda plan olusmamasini test eder."""
        self.planner.start_recording("bos_plan")
        result = self.planner.stop_recording()
        self.assertIsNone(result, "Hareketsiz kayit plan olusturmamali.")
        self.assertEqual(len(self.planner.plans), 0)

    def test_delete_plan(self) -> None:
        """Silme sonrasinda planin kalmadigini test eder."""
        self.planner.start_recording("silinecek")
        self.planner.record_action(10, 20, "tap", "tek")
        self.planner.stop_recording()
        self.assertIn("silinecek", self.planner.plans, "Plan once eklenmis olmali.")

        sonuc = self.planner.delete_plan("silinecek")
        self.assertTrue(sonuc, "Silme basarili olmali.")
        self.assertNotIn("silinecek", self.planner.plans, "Plan silinmis olmali.")
        self.assertEqual(len(self.planner.plans), 0)

        # Silme islemi dosyaya da yansimali
        reloaded = AttackPlanner(plans_path=str(self.plans_path))
        self.assertNotIn("silinecek", reloaded.plans)

    def test_delete_missing_plan(self) -> None:
        """Olmayan plan silinmeye calisildiginda False donmesini test eder."""
        self.assertFalse(self.planner.delete_plan("yok_boyle_plan"))

    def test_execute_missing_plan(self) -> None:
        """Olmayan plan oynatilmaya calisildiginda False donmesini test eder."""
        self.assertFalse(self.planner.execute("olmayan", FakeADB(), speed=1.0))

    def test_execute_without_adb(self) -> None:
        """ADB verilmediginde oynatmanin basarisiz olmasini test eder."""
        self.planner.start_recording("plan_a")
        self.planner.record_action(1, 2, "tap", "a")
        self.planner.stop_recording()
        self.assertFalse(self.planner.execute("plan_a", None))

    def test_export_and_import(self) -> None:
        """Plan disa/ice aktarma dongusunu test eder."""
        self.planner.start_recording("tasinan")
        self.planner.record_action(11, 22, "tap", "a")
        self.planner.record_action(33, 44, "long_press", "b", metadata={"duration": 800})
        self.planner.stop_recording()

        export_path = Path(self.temp_dir.name) / "exported.json"
        self.assertIsNotNone(self.planner.export_plan("tasinan", str(export_path)))
        self.assertTrue(export_path.exists(), "Disa aktarilan dosya olusmali.")

        new_name = self.planner.import_plan(str(export_path), new_name="kopya_plan")
        self.assertEqual(new_name, "kopya_plan", "Ice aktarma yeni adla yapilmali.")
        self.assertIn("kopya_plan", self.planner.plans)

    def test_action_types_and_metadata(self) -> None:
        """Farkli eylem tiplerinin dogru sekilde kaydedildigini test eder."""
        self.planner.start_recording("tipler")
        self.planner.record_action(1, 1, "tap", "tap")
        self.planner.record_action(2, 2, "long_press", "uzun", metadata={"duration": 1200})
        self.planner.record_action(3, 3, "swipe", "kaydir", metadata={"x2": 9, "y2": 9})
        self.planner.record_action(4, 0, "key", "geri", metadata={"keycode": 4})
        self.planner.stop_recording()

        plan = self.planner.get_plan("tipler")
        self.assertIsNotNone(plan)
        types = [action["action_type"] for action in plan["actions"]]
        self.assertEqual(types, ["tap", "long_press", "swipe", "key"])

        fake_adb = FakeADB()
        self.assertTrue(self.planner.execute("tipler", fake_adb, speed=20.0))
        self.assertEqual(len(fake_adb.calls), 1)
        self.assertEqual(len(fake_adb.long_presses), 1)
        self.assertEqual(len(fake_adb.swipes), 1)
        self.assertEqual(fake_adb.keys, [4])


if __name__ == "__main__":  # pragma: no cover - elle calistirma
    unittest.main(verbosity=2)
