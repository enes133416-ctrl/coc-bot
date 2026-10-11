"""
================================================================================
 ai/__init__.py - Yerel Yapay Zeka Paketi
================================================================================
 Ollama uzerinde calisan LLaVA 7B modeli ile tamamen yerel (internet
 gerektirmeyen) gorsel analiz saglar.

 Not: Bu paket OPSIYONELDIR. Ollama kurulu degilse bot normal calismaya devam
 eder; sadece AI destekli analizler atlanir.

 Disa acilan siniflar:
   - LocalVisionAI : ai.local_vision
================================================================================
"""

from __future__ import annotations

from typing import List

__all__: List[str] = [
    "local_vision",
]

__version__: str = "1.0.0"
