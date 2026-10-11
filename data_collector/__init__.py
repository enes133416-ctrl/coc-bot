"""
================================================================================
 data_collector/__init__.py - Veri Toplama Paketi
================================================================================
 Botun tum eylemlerini, loot kontrollerini, savas sonuclarini ve hatalarini
 kaydeden; bu veriyi yapay zeka egitimi/analizi icin disa aktaran moduller.

 Disa acilan siniflar:
   - DataLogger : data_collector.logger

 Disa acilan fonksiyonlar:
   - export_summary : data_collector.export_for_ai
================================================================================
"""

from __future__ import annotations

from typing import List

__all__: List[str] = [
    "logger",
    "export_for_ai",
]

__version__: str = "1.0.0"
