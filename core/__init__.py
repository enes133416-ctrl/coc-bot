"""
================================================================================
 core/__init__.py - Cekirdek (Core) Paketi
================================================================================
 ADB baglantisi, ekran yakalama, goruntu isleme (OpenCV), OCR (Tesseract) ve
 bot durum makinesi bilesenlerini tek cati altinda toplar.

 Disa acilan siniflar:
   - ADBController   : core.adb_controller
   - ScreenCapture   : core.screen_capture
   - VisionEngine    : core.vision_engine
   - OCREngine       : core.ocr_engine
   - StateMachine    : core.state_machine
   - BotState        : core.state_machine
================================================================================
"""

from __future__ import annotations

from typing import List

__all__: List[str] = [
    "adb_controller",
    "screen_capture",
    "vision_engine",
    "ocr_engine",
    "state_machine",
]

__version__: str = "1.0.0"
