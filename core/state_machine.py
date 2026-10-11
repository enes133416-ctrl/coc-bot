"""
================================================================================
 core/state_machine.py - Bot Durum Makinesi
================================================================================
 Botun tum karar akisini yoneten sonlu durum makinesi (FSM).

 Durumlar:
   HOME          -> Ana koy ekrani; saldiri butonunu ara ve tikla
   FINDING_MATCH -> Rakip arama ekrani; "Eslesme Bul" butonuna bas
   SCOUTING      -> Rakibi incele; loot oku, filtrele, gerekirse atla
   ATTACKING     -> Kayitli savas planini oynat
   WAITING_END   -> Savasin bitmesini bekle (savas sonu ekrani)
   RETURNING     -> Ana ekrana don
   ERROR         -> Hata durumu; kurtarma (recovery) dene

 Her durum icin ayri bir handler metodu vardir ve her handler bir sonraki
 durumu dondurur. Bagimliliklar constructor uzerinden enjekte edilir
 (dependency injection) - boylece siniflar arasi bagimlilik minimumdur.

 Ornek:
   bot = StateMachine(adb=adb, vision=vision, ocr=ocr, planner=planner)
   bot.run()
================================================================================
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, Optional

import config


class BotState(Enum):
    """Botun bulunabilecegi durumlar."""

    HOME = "HOME"
    FINDING_MATCH = "FINDING_MATCH"
    SCOUTING = "SCOUTING"
    ATTACKING = "ATTACKING"
    WAITING_END = "WAITING_END"
    RETURNING = "RETURNING"
    ERROR = "ERROR"


class StateMachine:
    """Clash of Clans botunun durum makinesi."""

    def __init__(
        self,
        adb: Any,
        vision: Any = None,
        ocr: Any = None,
        capture: Any = None,
        scout_filter: Any = None,
        planner: Any = None,
        logger: Any = None,
        ai: Any = None,
        error_handler: Any = None,
    ) -> None:
        """
        StateMachine nesnesini olusturur.

        Args:
            adb (Any): ADBController nesnesi (zorunlu).
            vision (Any): VisionEngine nesnesi.
            ocr (Any): OCREngine nesnesi.
            capture (Any): ScreenCapture nesnesi (None ise otomatik olusturulur).
            scout_filter (Any): ScoutFilter nesnesi (None ise otomatik olusturulur).
            planner (Any): AttackPlanner nesnesi (None ise otomatik olusturulur).
            logger (Any): DataLogger nesnesi (opsiyonel).
            ai (Any): LocalVisionAI nesnesi (opsiyonel, None ise AI atlanir).
            error_handler (Any): ErrorHandler nesnesi (opsiyonel).

        Returns:
            None
        """
        self.adb = adb
        self.vision = vision
        self.ocr = ocr
        self.logger = logger
        self.ai = ai
        self.error_handler = error_handler

        # Opsiyonel bagimliliklari gec (lazy) olustur - import dongusunu onler
        self.capture = capture if capture is not None else self._make_capture()
        self.scout_filter = (
            scout_filter if scout_filter is not None else self._make_scout_filter()
        )
        self.planner = planner if planner is not None else self._make_planner()

        self.state: BotState = BotState.HOME
        self.previous_state: BotState = BotState.HOME
        self.running: bool = True
        self.active_plan: str = config.ACTIVE_PLAN
        self.playback_speed: float = config.PLAYBACK_SPEED

        self.skip_count: int = 0
        self.total_skips: int = 0
        self.accepted_count: int = 0
        self.battles_done: int = 0
        self.error_count: int = 0
        self.cycle_count: int = 0
        self._last_loot: Dict[str, int] = {"gold": 0, "elixir": 0, "dark": 0, "total": 0}

        print("=" * 78)
        print(" [STATE] Durum makinesi hazir")
        print(f" [STATE] Aktif plan     : {self.active_plan}")
        print(f" [STATE] Savas timeout  : {config.BATTLE_TIMEOUT} sn")
        ai_durumu = "ACIK" if (config.USE_LOCAL_AI and self.ai) else "KAPALI"
        print(f" [STATE] Yerel AI       : {ai_durumu}")
        print("=" * 78)

    # -------------------------------------------------------------------------
    # TEMBEL (LAZY) BAGIMLILIK OLUSTURUCULARI
    # -------------------------------------------------------------------------
    def _make_capture(self) -> Any:
        """
        Varsayilan ScreenCapture nesnesini olusturur.

        Returns:
            Any: ScreenCapture nesnesi veya None.
        """
        try:
            from core.screen_capture import ScreenCapture

            return ScreenCapture(adb=self.adb)
        except Exception as error:
            print(f"[!] ScreenCapture olusturulamadi: {error}")
            return None

    def _make_scout_filter(self) -> Any:
        """
        Varsayilan ScoutFilter nesnesini olusturur.

        Returns:
            Any: ScoutFilter nesnesi veya None.
        """
        try:
            from modules.scout_filter import ScoutFilter

            return ScoutFilter(
                min_total=config.MIN_TOTAL_LOOT,
                min_gold=config.MIN_GOLD,
                min_elixir=config.MIN_ELIXIR,
                min_dark=config.MIN_DARK,
            )
        except Exception as error:
            print(f"[!] ScoutFilter olusturulamadi: {error}")
            return None

    def _make_planner(self) -> Any:
        """
        Varsayilan AttackPlanner nesnesini olusturur.

        Returns:
            Any: AttackPlanner nesnesi veya None.
        """
        try:
            from modules.attack_planner import AttackPlanner

            return AttackPlanner()
        except Exception as error:
            print(f"[!] AttackPlanner olusturulamadi: {error}")
            return None

    # -------------------------------------------------------------------------
    # YARDIMCI METODLAR
    # -------------------------------------------------------------------------
    def _screenshot(self, name: Optional[str] = None) -> Optional[str]:
        """
        Ekran goruntusu alir (ScreenCapture varsa onu, yoksa ADB'yi kullanir).

        Args:
            name (Optional[str]): Ozel dosya adi.

        Returns:
            Optional[str]: Goruntu yolu veya None.
        """
        try:
            if self.capture is not None:
                return self.capture.capture(name=name, force=True)
            stamp = time.strftime("%Y%m%d_%H%M%S")
            target = config.SCREENSHOT_DIR / f"{name or 'state'}_{stamp}.png"
            return self.adb.screenshot(str(target))
        except Exception as error:
            print(f"[!] Ekran goruntusu hatasi: {error}")
            return None

    def _find(self, template_key: str, screenshot_path: Optional[str]) -> Dict[str, Any]:
        """
        Verilen template'i son ekran goruntusunde arar.

        Args:
            template_key (str): config.TEMPLATES anahtari.
            screenshot_path (Optional[str]): Aranacak goruntu.

        Returns:
            Dict[str, Any]: Bulma sonucu sozlugu.
        """
        empty: Dict[str, Any] = {"found": False, "x": 0, "y": 0, "confidence": 0.0}
        try:
            if self.vision is None or not screenshot_path:
                print("[!] Vision motoru veya goruntu yok, arama atlandi.")
                return empty
            template_path = str(config.get_template_path(template_key))
            return self.vision.find_template(screenshot_path, template_path)
        except Exception as error:
            print(f"[!] Template arama hatasi ({template_key}): {error}")
            return empty

    def _tap_found(self, result: Dict[str, Any], label: str) -> bool:
        """
        Bulunan template'in merkezine tiklar.

        Args:
            result (Dict[str, Any]): find_template sonucu.
            label (str): Log icin aciklama.

        Returns:
            bool: True -> tiklama gonderildi.
        """
        try:
            if not result.get("found"):
                print(f"[!] '{label}' bulunamadi, tiklama yapilmadi.")
                return False
            x = int(result.get("x", 0)) + max(0, int(result.get("width", 0))) // 2
            y = int(result.get("y", 0)) + max(0, int(result.get("height", 0))) // 2
            print(f"[STATE] '{label}' tiklaniyor -> ({x}, {y})")
            return bool(self.adb.tap(x, y))
        except Exception as error:
            print(f"[!] Tiklama hatasi ({label}): {error}")
            return False

    def _log(self, method_name: str, *args: Any, **kwargs: Any) -> None:
        """
        Logger varsa ilgili metodu guvenle cagirir.

        Args:
            method_name (str): DataLogger metodunun adi (orn. "log_action").
            *args (Any): Pozisyonel argumanlar.
            **kwargs (Any): Anahtar kelime argumanlari.

        Returns:
            None
        """
        try:
            if self.logger is None:
                return
            method = getattr(self.logger, method_name, None)
            if callable(method):
                method(*args, **kwargs)
        except Exception as error:
            print(f"[!] Loglama hatasi ({method_name}): {error}")

    def _handle_error(
        self,
        error_type: str,
        description: str,
        screenshot: Optional[str] = None,
    ) -> None:
        """
        Hatayi logger ve error_handler uzerinden kaydeder.

        Args:
            error_type (str): Hata kategorisi (orn. "STATE_ERROR").
            description (str): Turkce aciklama.
            screenshot (Optional[str]): Ilgili ekran goruntusu.

        Returns:
            None
        """
        try:
            self.error_count += 1
            print(f"[ERROR] {error_type}: {description}")
            self._log(
                "log_error",
                error_type=error_type,
                description=description,
                screenshot_path=screenshot,
                context={"state": self.state.value, "cycle": self.cycle_count},
            )
            if self.error_handler is not None and hasattr(self.error_handler, "handle"):
                self.error_handler.handle(error_type, description, screenshot)
        except Exception as error:
            print(f"[!] Hata kaydi sirasinda sorun: {error}")

    def set_state(self, new_state: BotState) -> None:
        """
        Durumu degistirir ve loglar.

        Args:
            new_state (BotState): Yeni durum.

        Returns:
            None
        """
        try:
            self.previous_state = self.state
            self.state = new_state
            print(f"[STATE] {self.previous_state.value} --> {new_state.value}")
            if config.LOG_ALL_ACTIONS:
                self._log(
                    "log_action",
                    action_type="STATE_CHANGE",
                    details={
                        "from": self.previous_state.value,
                        "to": new_state.value,
                        "cycle": self.cycle_count,
                    },
                )
        except Exception as error:
            print(f"[!] Durum degistirme hatasi: {error}")

    # -------------------------------------------------------------------------
    # DURUM ISLEYICILERI (HANDLERS)
    # -------------------------------------------------------------------------
    def _home(self) -> BotState:
        """
        HOME durumu: ana ekranda saldiri butonunu bulur ve tiklar.

        Returns:
            BotState: FINDING_MATCH (basarili) veya ERROR (basarisiz).
        """
        try:
            print("[STATE] HOME -> Saldiri butonu araniyor...")
            deadline = time.time() + config.HOME_WAIT_TIMEOUT
            while time.time() < deadline:
                screenshot = self._screenshot("home")
                result = self._find("attack_button", screenshot)
                if result.get("found"):
                    self._log(
                        "log_action",
                        action_type="FIND_ATTACK_BUTTON",
                        details=result,
                        screenshot_path=screenshot,
                    )
                    if self._tap_found(result, "attack_button"):
                        time.sleep(config.STATE_LOOP_DELAY)
                        return BotState.FINDING_MATCH
                time.sleep(1.5)

            self._handle_error(
                "HOME_ATTACK_BUTTON",
                "Ana ekranda saldiri butonu bulunamadi! Ekran goruntusu "
                "assets/templates/attack_button.png ile uyusmuyor olabilir.",
            )
            return BotState.ERROR
        except Exception as error:
            self._handle_error("HOME_EXCEPTION", f"HOME durumu hatasi: {error}")
            return BotState.ERROR

    def _find_match(self) -> BotState:
        """
        FINDING_MATCH durumu: rakip arama butonuna basar.

        Returns:
            BotState: SCOUTING (basarili) veya ERROR (basarisiz).
        """
        try:
            print("[STATE] FINDING_MATCH -> Rakip araniyor...")
            result = self.vision.wait_for_template(
                self.adb,
                str(config.get_template_path("find_match")),
                timeout=config.FIND_MATCH_TIMEOUT,
                interval=config.TEMPLATE_WAIT_INTERVAL,
            )
            if result.get("found"):
                self._tap_found(result, "find_match")
                self._log(
                    "log_action",
                    action_type="FIND_MATCH_TAP",
                    details=result,
                    screenshot_path=self.capture.get_last_path() if self.capture else None,
                )
                time.sleep(config.SCOUT_READ_DELAY)
                return BotState.SCOUTING

            self._handle_error(
                "FIND_MATCH_BUTTON",
                "Eslesme bulma butonu zaman asimi ile bulunamadi.",
            )
            return BotState.ERROR
        except Exception as error:
            self._handle_error("FIND_MATCH_EXCEPTION", f"Eslesme arama hatasi: {error}")
            return BotState.ERROR

    def _scout(self) -> BotState:
        """
        SCOUTING durumu: rakibin loot degerlerini okur ve filtre uygular.

        Returns:
            BotState: ATTACKING (loot yeterli) veya SCOUTING/ERROR (atla).
        """
        try:
            print("[STATE] SCOUTING -> Rakip inceleniyor...")
            time.sleep(config.SCOUT_READ_DELAY)
            screenshot = self._screenshot("scout")
            if not screenshot:
                self._handle_error("SCOUT_SCREENSHOT", "Rakip ekran goruntusu alinamadi.")
                return BotState.ERROR

            if self.ocr is None:
                self._handle_error("SCOUT_OCR_MISSING", "OCR motoru yok, loot okunamadi.")
                return BotState.ERROR

            loot = self.ocr.read_loot(screenshot)
            self._last_loot = loot

            accepted = True
            if self.scout_filter is not None:
                accepted = bool(self.scout_filter.is_worth_attacking(loot))
            else:
                accepted = loot.get("total", 0) >= config.MIN_TOTAL_LOOT

            self._log(
                "log_loot_check",
                loot=loot,
                accepted=accepted,
                screenshot_path=screenshot,
            )

            if accepted:
                self.accepted_count += 1
                print(f"[STATE] Rakip KABUL edildi -> toplam loot {loot.get('total', 0):,}")
                return BotState.ATTACKING

            self.skip_count += 1
            self.total_skips += 1
            print(f"[STATE] Rakip ATLANDI (toplam atlanan: {self.total_skips})")

            if self.skip_count >= config.MAX_SKIPS_PER_CYCLE:
                self._handle_error(
                    "SCOUT_MAX_SKIP",
                    f"{self.skip_count} rakip ust uste atlandi! Loot esikleri cok "
                    "yuksek olabilir veya OCR hatali okuyor olabilir.",
                    screenshot,
                )
                self.skip_count = 0
                return BotState.ERROR

            next_result = self._find("next_button", screenshot)
            if not self._tap_found(next_result, "next_button"):
                print("[STATE] Sonraki butonu bulunamadi, ekran goruntusu yenileniyor...")
                time.sleep(2.0)
            time.sleep(config.STATE_LOOP_DELAY)
            return BotState.SCOUTING
        except Exception as error:
            self._handle_error("SCOUT_EXCEPTION", f"Tarama hatasi: {error}")
            return BotState.ERROR

    def _attack(self) -> BotState:
        """
        ATTACKING durumu: aktif savas planini oynatir.

        Returns:
            BotState: WAITING_END (plan calistirildi) veya ERROR.
        """
        try:
            if self.planner is None:
                self._handle_error("ATTACK_NO_PLANNER", "Savas planlayici yuklu degil.")
                return BotState.ERROR

            plans = getattr(self.planner, "plans", {})
            if self.active_plan not in plans:
                self._handle_error(
                    "ATTACK_PLAN_MISSING",
                    f"'{self.active_plan}' plani bulunamadi! once kayit yapin: "
                    "python main.py -> [2] Savas plani kaydet",
                )
                return BotState.ERROR

            print(f"[STATE] ATTACKING -> '{self.active_plan}' plani oynatiliyor...")
            self._log(
                "log_action",
                action_type="ATTACK_START",
                details={"plan": self.active_plan, "loot": self._last_loot},
                screenshot_path=self.capture.get_last_path() if self.capture else None,
            )

            success = bool(
                self.planner.execute(self.active_plan, self.adb, speed=self.playback_speed)
            )
            self.battles_done += 1
            self._log(
                "log_battle_result",
                plan_name=self.active_plan,
                success=success,
                stars=None,
                loot_gained=self._last_loot,
            )
            if not success:
                print("[!] Plan tamamlanmadi ancak savas sonu beklenecek.")
            time.sleep(config.STATE_LOOP_DELAY)
            return BotState.WAITING_END
        except Exception as error:
            self._handle_error("ATTACK_EXCEPTION", f"Saldiri hatasi: {error}")
            return BotState.ERROR

    def _wait_end(self) -> BotState:
        """
        WAITING_END durumu: savas sonu (ana ekrana don) butonunu bekler.

        Returns:
            BotState: RETURNING (bulundu) veya ERROR (zaman asimi).
        """
        try:
            print(
                f"[STATE] WAITING_END -> Savas bitisi bekleniyor "
                f"(maks {config.BATTLE_TIMEOUT} sn)"
            )
            result = self.vision.wait_for_template(
                self.adb,
                str(config.get_template_path("return_home")),
                timeout=config.BATTLE_TIMEOUT,
                interval=config.TEMPLATE_WAIT_INTERVAL,
            )
            if result.get("found"):
                self._log(
                    "log_action",
                    action_type="BATTLE_END_DETECTED",
                    details=result,
                    screenshot_path=self.capture.get_last_path() if self.capture else None,
                )
                time.sleep(config.STATE_LOOP_DELAY)
                return BotState.RETURNING

            self._handle_error(
                "BATTLE_TIMEOUT",
                f"Savas {config.BATTLE_TIMEOUT} saniyede bitmedi, donus butonu bulunamadi.",
            )
            return BotState.ERROR
        except Exception as error:
            self._handle_error("WAIT_END_EXCEPTION", f"Savas sonu bekleme hatasi: {error}")
            return BotState.ERROR

    def _return(self) -> BotState:
        """
        RETURNING durumu: ana ekrana donus butonuna basar.

        Returns:
            BotState: HOME (donus yapildi) veya ERROR.
        """
        try:
            print("[STATE] RETURNING -> Ana ekrana donuluyor...")
            screenshot = self._screenshot("return")
            result = self._find("return_home", screenshot)
            if result.get("found"):
                self._tap_found(result, "return_home")
            else:
                print("[!] Donus butonu bulunamadi, merkeze dokunuluyor.")
                screen = self.adb.get_screen_size()
                self.adb.tap(int(screen[0] / 2), int(screen[1] / 2))

            time.sleep(config.RETURN_HOME_WAIT)
            self.skip_count = 0
            self._log(
                "log_action",
                action_type="RETURN_HOME",
                details={"found": result.get("found", False)},
                screenshot_path=screenshot,
            )
            return BotState.HOME
        except Exception as error:
            self._handle_error("RETURN_EXCEPTION", f"Donus hatasi: {error}")
            return BotState.ERROR

    def _recover(self) -> BotState:
        """
        ERROR durumu: bekler, ekran goruntusu alir ve yerel AI ile durumu kontrol eder.

        Returns:
            BotState: HOME (kurtarma basarili) veya FINDING_MATCH/HOME (varsayilan).
        """
        try:
            print("[STATE] ERROR -> Kurtarma modu baslatildi (5 saniye bekleniyor)...")
            time.sleep(5.0)
            screenshot = self._screenshot("recover")

            if config.USE_LOCAL_AI and self.ai is not None and screenshot:
                try:
                    at_home = self.ai.is_home_screen(screenshot)
                    print(f"[STATE] AI kontrolu -> ana ekran mi: {at_home}")
                    if at_home:
                        self._log(
                            "log_action",
                            action_type="RECOVER_HOME",
                            details={"ai": "home_screen"},
                            screenshot_path=screenshot,
                        )
                        return BotState.HOME
                except Exception as error:
                    print(f"[!] AI kurtarma kontrolu hatasi: {error}")

            self._log(
                "log_action",
                action_type="RECOVER_RESET",
                details={"action": "state reset to HOME"},
                screenshot_path=screenshot,
            )
            print("[STATE] Durum HOME olarak sifirlandi.")
            return BotState.HOME
        except Exception as error:
            print(f"[!] Kurtarma hatasi: {error}")
            return BotState.HOME

    # -------------------------------------------------------------------------
    # ANA DONGU
    # -------------------------------------------------------------------------
    def step(self) -> BotState:
        """
        Tek bir durum adimi calistirir.

        Returns:
            BotState: Bir sonraki durum.
        """
        handlers = {
            BotState.HOME: self._home,
            BotState.FINDING_MATCH: self._find_match,
            BotState.SCOUTING: self._scout,
            BotState.ATTACKING: self._attack,
            BotState.WAITING_END: self._wait_end,
            BotState.RETURNING: self._return,
            BotState.ERROR: self._recover,
        }
        handler = handlers.get(self.state, self._recover)
        next_state = handler()
        self.set_state(next_state)
        return next_state

    def run(self, max_cycles: int = 0) -> None:
        """
        Ana dongu: durumlari sirayla isler.

        KeyboardInterrupt (Ctrl+C) alindiginda tum oturum verisi AI icin
        disa aktarilir ve bot guvenli sekilde kapatilir.

        Args:
            max_cycles (int): 0 ise sonsuz dongu; >0 ise bu kadar dongu sonra durur.

        Returns:
            None
        """
        print("=" * 78)
        print(" [STATE] BOT BASLATILDI - Durdurmak icin Ctrl+C")
        print("=" * 78)
        try:
            while self.running:
                if max_cycles and self.cycle_count >= max_cycles:
                    print(f"[STATE] Maksimum dongu sayisina ulasildi ({max_cycles}).")
                    break
                self.cycle_count += 1
                print(f"\n--- Dongu #{self.cycle_count} | Durum: {self.state.value} ---")
                self.step()
                if config.STATE_LOOP_DELAY > 0:
                    time.sleep(config.STATE_LOOP_DELAY)
        except KeyboardInterrupt:
            print("\n[STATE] Ctrl+C algilandi, bot durduruluyor...")
            self.stop()
        except Exception as error:
            self._handle_error("RUN_EXCEPTION", f"Ana dongu hatasi: {error}")
        finally:
            try:
                if self.logger is not None and hasattr(self.logger, "export_for_ai"):
                    path = self.logger.export_for_ai()
                    print(f"[STATE] Oturum verisi AI icin disa aktarildi -> {path}")
            except Exception as error:
                print(f"[!] Disa aktarma hatasi: {error}")
            self.print_summary()

    def stop(self) -> None:
        """
        Botu guvenli sekilde durdurur.

        Returns:
            None
        """
        self.running = False
        print("[STATE] Durdurma istegi alindi.")

    def print_summary(self) -> None:
        """
        Oturum ozetini konsola yazar.

        Returns:
            None
        """
        try:
            print("\n" + "=" * 78)
            print(" OTURUM OZETI")
            print("=" * 78)
            print(f" Toplam dongu        : {self.cycle_count}")
            print(f" Kabul edilen rakip  : {self.accepted_count}")
            print(f" Atlanan rakip       : {self.total_skips}")
            print(f" Tamamlanan savas    : {self.battles_done}")
            print(f" Hata sayisi         : {self.error_count}")
            print(f" Son loot            : {self._last_loot}")
            if self.scout_filter is not None and hasattr(self.scout_filter, "get_stats"):
                print(f" Filtre istatistigi  : {self.scout_filter.get_stats()}")
            if self.ocr is not None and hasattr(self.ocr, "get_stats"):
                print(f" OCR istatistigi     : {self.ocr.get_stats()}")
            print("=" * 78)
        except Exception as error:
            print(f"[!] Ozet yazma hatasi: {error}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Bot istatistiklerini sozluk olarak dondurur.

        Returns:
            Dict[str, Any]: Istatistik sozlugu.
        """
        return {
            "cycles": self.cycle_count,
            "accepted": self.accepted_count,
            "skipped": self.total_skips,
            "battles": self.battles_done,
            "errors": self.error_count,
            "state": self.state.value,
            "last_loot": dict(self._last_loot),
        }


if __name__ == "__main__":  # pragma: no cover - elle test
    print("StateMachine tek basina calistirilmaz.")
    print("Kullanim: python main.py -> [1] Botu baslat")
