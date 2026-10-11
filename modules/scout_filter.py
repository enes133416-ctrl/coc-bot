"""
================================================================================
 modules/scout_filter.py - Rakip Loot Filtresi (1.6M Kurali)
================================================================================
 Tarama (scout) ekraninda okunan loot degerlerini filtreler. Toplam loot,
 altin ve iksir esiklerinin uzerindeyse saldiriyi onerir; aksi halde rakibin
 atlanmasini saglar.

 Varsayilan kural (config.py'dan degistirilebilir):
   - Toplam loot >= 1.600.000
   - Altin       >=   600.000
   - Iksir       >=   600.000
   - Kara iksir  >=         0  (sart yok)

 Kara iksir, toplam hesabina DARK_ELIXIR_MULTIPLIER ile dahil edilir.

 Ornek:
   filtre = ScoutFilter(min_total=1_600_000, min_gold=600_000, min_elixir=600_000)
   if filtre.is_worth_attacking({"gold": 900_000, "elixir": 800_000, "dark": 2_000}):
       print("Saldir!")
================================================================================
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import config


class ScoutFilter:
    """Loot degerlerine gore saldiri karari veren filtre sinifi."""

    def __init__(
        self,
        min_total: Optional[int] = None,
        min_gold: Optional[int] = None,
        min_elixir: Optional[int] = None,
        min_dark: Optional[int] = None,
        dark_multiplier: Optional[float] = None,
    ) -> None:
        """
        ScoutFilter nesnesini olusturur.

        Args:
            min_total (Optional[int]): Minimum toplam loot. None ise config.MIN_TOTAL_LOOT.
            min_gold (Optional[int]): Minimum altin. None ise config.MIN_GOLD.
            min_elixir (Optional[int]): Minimum iksir. None ise config.MIN_ELIXIR.
            min_dark (Optional[int]): Minimum kara iksir. None ise config.MIN_DARK.
            dark_multiplier (Optional[float]): Kara iksir katsayisi.

        Returns:
            None
        """
        self.min_total: int = int(config.MIN_TOTAL_LOOT if min_total is None else min_total)
        self.min_gold: int = int(config.MIN_GOLD if min_gold is None else min_gold)
        self.min_elixir: int = int(config.MIN_ELIXIR if min_elixir is None else min_elixir)
        self.min_dark: int = int(config.MIN_DARK if min_dark is None else min_dark)
        self.dark_multiplier: float = float(
            config.DARK_ELIXIR_MULTIPLIER if dark_multiplier is None else dark_multiplier
        )

        # Istatistikler
        self.stats: Dict[str, int] = {
            "checked": 0,
            "accepted": 0,
            "rejected": 0,
            "rejected_total": 0,
            "rejected_gold": 0,
            "rejected_elixir": 0,
            "rejected_dark": 0,
        }
        self.history: List[Dict[str, Any]] = []
        self.reject_log_enabled: bool = True

        print(
            f"[FILTER] Aktif kural -> toplam>={self.min_total:,} | "
            f"altin>={self.min_gold:,} | iksir>={self.min_elixir:,} | "
            f"kara>={self.min_dark:,}"
        )

    # -------------------------------------------------------------------------
    # ANA KARAR FONKSIYONU
    # -------------------------------------------------------------------------
    def is_worth_attacking(self, loot_dict: Dict[str, Any]) -> bool:
        """
        Verilen loot degerlerinin saldiriya deger olup olmadigini kontrol eder.

        Args:
            loot_dict (Dict[str, Any]): {"gold": int, "elixir": int, "dark": int, ...}
                                        "total" yoksa otomatik hesaplanir.

        Returns:
            bool: True -> saldir, False -> atla.
        """
        try:
            gold = self._safe_int(loot_dict.get("gold", 0))
            elixir = self._safe_int(loot_dict.get("elixir", 0))
            dark = self._safe_int(loot_dict.get("dark", 0))
            total = self._safe_int(loot_dict.get("total", 0))
            if total <= 0:
                total = gold + elixir + int(dark * self.dark_multiplier)

            self.stats["checked"] += 1
            reasons: List[str] = []

            if total < self.min_total:
                reasons.append(
                    f"TOPLAM yetersiz ({total:,} < {self.min_total:,})"
                )
                self.stats["rejected_total"] += 1
            if gold < self.min_gold:
                reasons.append(f"ALTIN yetersiz ({gold:,} < {self.min_gold:,})")
                self.stats["rejected_gold"] += 1
            if elixir < self.min_elixir:
                reasons.append(f"IKSIR yetersiz ({elixir:,} < {self.min_elixir:,})")
                self.stats["rejected_elixir"] += 1
            if dark < self.min_dark:
                reasons.append(f"KARA IKSIR yetersiz ({dark:,} < {self.min_dark:,})")
                self.stats["rejected_dark"] += 1

            accepted = len(reasons) == 0
            if accepted:
                self.stats["accepted"] += 1
                print(
                    f"[FILTER] [+] SALDIR -> toplam={total:,} "
                    f"(altin={gold:,}, iksir={elixir:,}, kara={dark:,})"
                )
            else:
                self.stats["rejected"] += 1
                if self.reject_log_enabled:
                    print(f"[FILTER] [-] ATLA (rakip #{self.stats['checked']})")
                    for reason in reasons:
                        print(f"          - {reason}")

            self._record_history(gold, elixir, dark, total, accepted, reasons)
            return accepted
        except Exception as error:
            print(f"[!] Filtre hatasi, guvenli tarafta kaliniyor (ATLA): {error}")
            return False

    def _record_history(
        self,
        gold: int,
        elixir: int,
        dark: int,
        total: int,
        accepted: bool,
        reasons: List[str],
    ) -> None:
        """
        Karar kaydini gecmise ekler (en fazla 200 kayit tutulur).

        Args:
            gold (int): Altin miktari.
            elixir (int): Iksir miktari.
            dark (int): Kara iksir miktari.
            total (int): Toplam deger.
            accepted (bool): Karar.
            reasons (List[str]): Red nedenleri.

        Returns:
            None
        """
        try:
            self.history.append(
                {
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "gold": gold,
                    "elixir": elixir,
                    "dark": dark,
                    "total": total,
                    "accepted": accepted,
                    "reasons": reasons,
                }
            )
            if len(self.history) > 200:
                self.history = self.history[-200:]
        except Exception as error:
            print(f"[!] Gecmis kaydi hatasi: {error}")

    # -------------------------------------------------------------------------
    # YARDIMCILAR
    # -------------------------------------------------------------------------
    @staticmethod
    def _safe_int(value: Any) -> int:
        """
        Gelen degeri guvenli sekilde tam sayiya cevirir.

        Args:
            value (Any): Cevrilecek deger (int, float, str).

        Returns:
            int: Cevrilmis sayi; hata halinde 0.
        """
        try:
            if value is None:
                return 0
            if isinstance(value, str):
                cleaned = value.replace(",", "").replace(".", "").strip()
                if not cleaned:
                    return 0
                return int(float(cleaned))
            return int(value)
        except Exception:
            return 0

    def get_stats(self) -> Dict[str, int]:
        """
        Filtre istatistiklerini dondurur.

        Returns:
            Dict[str, int]: {"checked", "accepted", "rejected", ...}
        """
        return dict(self.stats)

    def get_stats_text(self) -> str:
        """
        Istatistikleri tek satir Turkce metin olarak dondurur.

        Returns:
            str: Okunabilir istatistik ozeti.
        """
        try:
            return (
                f"Kontrol: {self.stats['checked']} | "
                f"Kabul: {self.stats['accepted']} | "
                f"Red: {self.stats['rejected']} "
                f"(toplam reddi: {self.stats['rejected_total']}, "
                f"altin: {self.stats['rejected_gold']}, "
                f"iksir: {self.stats['rejected_elixir']}, "
                f"kara: {self.stats['rejected_dark']})"
            )
        except Exception as error:
            return f"Istatistik hatasi: {error}"

    def reset_stats(self) -> None:
        """
        Istatistikleri sifirlar.

        Returns:
            None
        """
        try:
            for key in self.stats:
                self.stats[key] = 0
            self.history.clear()
            print("[FILTER] Istatistikler sifirlandi.")
        except Exception as error:
            print(f"[!] Sifirlama hatasi: {error}")

    def update_thresholds(
        self,
        min_total: Optional[int] = None,
        min_gold: Optional[int] = None,
        min_elixir: Optional[int] = None,
        min_dark: Optional[int] = None,
    ) -> None:
        """
        Esik degerleri calisma aninda gunceller.

        Args:
            min_total (Optional[int]): Yeni toplam esigi.
            min_gold (Optional[int]): Yeni altin esigi.
            min_elixir (Optional[int]): Yeni iksir esigi.
            min_dark (Optional[int]): Yeni kara iksir esigi.

        Returns:
            None
        """
        try:
            if min_total is not None:
                self.min_total = int(min_total)
            if min_gold is not None:
                self.min_gold = int(min_gold)
            if min_elixir is not None:
                self.min_elixir = int(min_elixir)
            if min_dark is not None:
                self.min_dark = int(min_dark)
            print(
                f"[FILTER] Esikler guncellendi -> toplam>={self.min_total:,}, "
                f"altin>={self.min_gold:,}, iksir>={self.min_elixir:,}, "
                f"kara>={self.min_dark:,}"
            )
        except Exception as error:
            print(f"[!] Esik guncelleme hatasi: {error}")

    def export_history(self, path: Optional[str] = None) -> Optional[str]:
        """
        Karar gecmisini JSON dosyasina kaydeder.

        Args:
            path (Optional[str]): Hedef dosya yolu. None ise data/scout_history.json.

        Returns:
            Optional[str]: Kaydedilen dosya yolu veya None.
        """
        try:
            target = Path(path) if path else (Path(config.DATA_DIR) / "scout_history.json")
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "rules": {
                    "min_total": self.min_total,
                    "min_gold": self.min_gold,
                    "min_elixir": self.min_elixir,
                    "min_dark": self.min_dark,
                    "dark_multiplier": self.dark_multiplier,
                },
                "stats": self.get_stats(),
                "history": self.history,
            }
            with open(target, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=4, ensure_ascii=False)
            print(f"[FILTER] Gecmis disa aktarildi -> {target}")
            return str(target)
        except Exception as error:
            print(f"[!] Disa aktarma hatasi: {error}")
            return None


if __name__ == "__main__":  # pragma: no cover - elle test
    demo = ScoutFilter()
    demolar = [
        {"gold": 900_000, "elixir": 800_000, "dark": 2_500},
        {"gold": 120_000, "elixir": 150_000, "dark": 0},
        {"gold": 1_200_000, "elixir": 100_000, "dark": 500},
    ]
    for index, loot in enumerate(demolar, start=1):
        print(f"\n--- Demo #{index}: {loot}")
        print(f"Karar: {'SALDIR' if demo.is_worth_attacking(loot) else 'ATLA'}")
    print(f"\n{demo.get_stats_text()}")
