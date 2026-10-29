import threading
import time
from typing import Callable, Optional, Dict, List
from pynput import keyboard


class GlobalHotkeyManager:
    """
    Global Hotkey Manager – Push-to-Talk / Toggle.

    Key fixes vs previous version:
    - Uses RLock (reentrant) to prevent deadlock when stop() is called from
      within start() while holding the same lock.
    - Callbacks are called OUTSIDE the lock to prevent callback-induced deadlocks.
    - start() guard: if already running, stop first then start fresh.
    - Strict debounce on all triggers (≥ 0.35 s between same trigger).
    """

    def __init__(
        self,
        mode: str = "push_to_talk",
        on_start_recording: Optional[Callable[[str], None]] = None,
        on_stop_recording: Optional[Callable[[str], None]] = None,
        on_toggle_recording: Optional[Callable[[str], None]] = None,
        on_clipboard_triggered: Optional[Callable[[], None]] = None,
    ):
        self.mode = mode
        self.on_start_recording = on_start_recording
        self.on_stop_recording = on_stop_recording
        self.on_toggle_recording = on_toggle_recording
        self.on_clipboard_triggered = on_clipboard_triggered

        self._hotkey_configs: Dict[str, str] = {
            "bn-BD":     "<ctrl>+<shift>+b",
            "en-US":     "<ctrl>+<shift>+e",
            "auto":      "<ctrl>+<shift>+space",
            "clipboard": "<ctrl>+b",
        }

        self._current_keys: set = set()
        self._parsed_hotkeys: Dict[str, List] = {}
        self._active_held_lang: Optional[str] = None
        self._last_trigger_times: Dict[str, float] = {}

        self._listener: Optional[keyboard.Listener] = None
        self._is_running = False
        # ─── RLock: reentrant – prevents deadlock when stop() is called
        #     from inside start() while the same thread already holds the lock.
        self._lock = threading.RLock()

        self._parse_all_hotkeys()

    # ─── Public API ─────────────────────────────────────────────────────────

    def set_hotkeys(
        self,
        bn_hk: str,
        en_hk: str,
        mixed_hk: str,
        clip_hk: str = "<ctrl>+b",
        mode: str = "push_to_talk",
    ):
        self.mode = mode
        self._hotkey_configs["bn-BD"] = bn_hk
        self._hotkey_configs["en-US"] = en_hk
        self._hotkey_configs["auto"] = mixed_hk
        self._hotkey_configs["clipboard"] = clip_hk
        self._parse_all_hotkeys()

    def start(self) -> bool:
        """Start the listener. Safe to call even if already running."""
        with self._lock:
            if self._is_running:
                # stop first (RLock lets us re-enter from the same thread)
                self._stop_locked()
            self._parse_all_hotkeys()
            try:
                self._listener = keyboard.Listener(
                    on_press=self._on_press,
                    on_release=self._on_release,
                )
                self._listener.daemon = True
                self._listener.start()
                self._is_running = True
                return True
            except Exception:
                self._is_running = False
                return False

    def stop(self):
        """Stop the listener. Safe to call even if not running."""
        with self._lock:
            self._stop_locked()

    def _stop_locked(self):
        """Internal stop — must be called with self._lock held."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        self._is_running = False
        self._current_keys.clear()
        self._active_held_lang = None

    # ─── Parsing ────────────────────────────────────────────────────────────

    def _parse_key_spec(self, key_str: str):
        """Return a tuple of pynput keys that any one of which satisfies this part."""
        k = key_str.strip().lower()
        if k in ("ctrl", "<ctrl>"):
            return (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r, keyboard.Key.ctrl)
        if k in ("shift", "<shift>"):
            return (keyboard.Key.shift_l, keyboard.Key.shift_r, keyboard.Key.shift)
        if k in ("alt", "<alt>"):
            return (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt, keyboard.Key.alt_gr)
        if k in ("cmd", "<cmd>", "win", "<win>", "super"):
            return (keyboard.Key.cmd_l, keyboard.Key.cmd_r, keyboard.Key.cmd)
        if k in ("space", "<space>"):
            return (keyboard.Key.space,)
        if k in ("enter", "<enter>"):
            return (keyboard.Key.enter,)
        if k in ("tab", "<tab>"):
            return (keyboard.Key.tab,)
        clean = k.replace("<", "").replace(">", "")
        return (keyboard.KeyCode.from_char(clean),)

    def _parse_all_hotkeys(self):
        self._parsed_hotkeys.clear()
        for action, hk_str in self._hotkey_configs.items():
            parts = [p.strip().lower() for p in hk_str.split("+") if p.strip()]
            groups = [self._parse_key_spec(p) for p in parts]
            self._parsed_hotkeys[action] = groups

    # ─── Matching ───────────────────────────────────────────────────────────

    def _canonical(self, key):
        try:
            if self._listener:
                return self._listener.canonical(key)
        except Exception:
            pass
        return key

    def _matches(self, groups: List) -> bool:
        if not groups:
            return False
        for key_options in groups:
            matched = False
            for opt in key_options:
                if opt in self._current_keys:
                    matched = True
                    break
                # Char comparison (case-insensitive)
                if hasattr(opt, "char") and opt.char:
                    for held in self._current_keys:
                        if hasattr(held, "char") and held.char and held.char.lower() == opt.char.lower():
                            matched = True
                            break
                # Name-based comparison (e.g. ctrl_l vs ctrl)
                elif hasattr(opt, "name") and opt.name:
                    for held in self._current_keys:
                        if hasattr(held, "name") and held.name:
                            if held.name == opt.name or held.name.startswith(opt.name):
                                matched = True
                                break
                if matched:
                    break
            if not matched:
                return False
        return True

    # ─── Listener callbacks ─────────────────────────────────────────────────

    def _on_press(self, key):
        # Build action outside the lock whenever possible; call callbacks
        # OUTSIDE the lock to avoid re-entrancy deadlocks.
        action_to_fire = None
        action_lang = None

        with self._lock:
            canon = self._canonical(key)
            self._current_keys.add(canon)
            self._current_keys.add(key)
            now = time.time()

            # Clipboard shortcut check first
            if "clipboard" in self._parsed_hotkeys and self._matches(self._parsed_hotkeys["clipboard"]):
                last = self._last_trigger_times.get("clipboard", 0.0)
                if now - last >= 0.35:
                    self._last_trigger_times["clipboard"] = now
                    action_to_fire = "clipboard"

            if action_to_fire is None:
                # Check language hotkeys — longer combos win (most-specific first)
                langs_sorted = sorted(
                    ["auto", "bn-BD", "en-US"],
                    key=lambda l: len(self._parsed_hotkeys.get(l, [])),
                    reverse=True,
                )
                for lang in langs_sorted:
                    if lang in self._parsed_hotkeys and self._matches(self._parsed_hotkeys[lang]):
                        if self.mode == "push_to_talk":
                            if self._active_held_lang is None:
                                self._active_held_lang = lang
                                action_to_fire = "start"
                                action_lang = lang
                        else:  # toggle
                            last = self._last_trigger_times.get(lang, 0.0)
                            if now - last >= 0.35:
                                self._last_trigger_times[lang] = now
                                action_to_fire = "toggle"
                                action_lang = lang
                        break

        # Fire callbacks OUTSIDE the lock
        if action_to_fire == "clipboard" and self.on_clipboard_triggered:
            try:
                self.on_clipboard_triggered()
            except Exception:
                pass
        elif action_to_fire == "start" and self.on_start_recording:
            try:
                self.on_start_recording(action_lang)
            except Exception:
                pass
        elif action_to_fire == "toggle" and self.on_toggle_recording:
            try:
                self.on_toggle_recording(action_lang)
            except Exception:
                pass

    def _on_release(self, key):
        action_lang = None

        with self._lock:
            canon = self._canonical(key)
            self._current_keys.discard(canon)
            self._current_keys.discard(key)

            if self.mode == "push_to_talk" and self._active_held_lang is not None:
                lang = self._active_held_lang
                groups = self._parsed_hotkeys.get(lang, [])
                if not self._matches(groups):
                    self._active_held_lang = None
                    action_lang = lang

        # Fire stop callback OUTSIDE the lock
        if action_lang is not None and self.on_stop_recording:
            try:
                self.on_stop_recording(action_lang)
            except Exception:
                pass
