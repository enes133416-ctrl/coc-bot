"""
================================================================================
 tests/__init__.py - Test Paketi
================================================================================
 Botun tum birim testlerini barindirir. Testler harici bagimlilik (ADB, Tesseract,
Ollama) olmadan da calisacak sekilde yazilmistir; ilgili arac yoksa testler
"skip" edilir.

 Testleri calistirma:
   pytest tests/ -v --tb=short
   python main.py  ->  [4] Test calistir

 Test dosyalari:
   - test_ocr.py     : OCR okuma ve on isleme testleri
   - test_vision.py  : Template matching ve renk tespiti testleri
   - test_planner.py : Savas plani kayit/oynatma/silme testleri
================================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

# Proje kokunu sys.path'e ekle (pytest farkli klasorden calistirilabilir)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

__all__: List[str] = [
    "test_ocr",
    "test_vision",
    "test_planner",
]
