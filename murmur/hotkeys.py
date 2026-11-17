"""Global hotkey: any key, key combination, left/right-specific modifier or mouse side button."""
import threading
import time

import keyboard

try:
    import mouse as _mouse
except Exception:       # mouse buttons are optional
    _mouse = None

MODS = ("ctrl", "alt", "shift", "windows")
MOUSE_NAMES = {"x": "mouse4", "x2": "mouse5", "middle": "mouse_middle"}
NON_TYPING = set(MODS) | {"caps lock", "alt gr", "menu", "num lock", "scroll lock"}


def generic(name: str) -> str:
    n = (name or "").lower().strip()
    for p in ("left ", "right "):
        if n.startswith(p):
            n = n[len(p):]
    return {"win": "windows", "control": "ctrl"}.get(n, n)


def specific(name: str) -> str:
    n = (name or "").lower().strip()
    n = n.replace("win ", "windows ").replace("control", "ctrl")
    return {"win": "windows"}.get(n, n)


def combo_of(s: str) -> set:
    return {specific(p) for p in s.split("+") if p.strip()}


class HotkeyManager:
    def __init__(self, on_press, on_release):
        self.on_press, self.on_release = on_press, on_release
        self.combo = {"ctrl", "windows"}
        self._spec = set()          # exact keys currently down, e.g. {"left ctrl", "left windows"}
        self.active = False
        self.last_typed = 0.0       # time of the last real typing key (used to make Undo safe)
        self._capture = None
        self._lock = threading.RLock()
        keyboard.hook(self._kb, suppress=False)
        if _mouse is not None:
            try:
                _mouse.hook(self._ms)
            except Exception:
                pass

    # ---- state ----
    @property
    def down(self) -> set:
        with self._lock:
            return set(self._spec) | {generic(k) for k in self._spec}

    def set_combo(self, s: str):
        c = combo_of(s)
        if c:
            self.combo = c

    # ---- events ----
    def _kb(self, e):
        self._update(specific(e.name), e.event_type == "down", is_key=True)

    def _ms(self, e):
        btn = getattr(e, "button", None)
        if btn in MOUSE_NAMES and getattr(e, "event_type", "") in ("down", "up"):
            self._update(MOUSE_NAMES[btn], e.event_type == "down", is_key=False)

    def _update(self, name, is_down, is_key):
        with self._lock:
            if is_down:
                self._spec.add(name)
            else:
                self._spec.discard(name)
            down = set(self._spec) | {generic(k) for k in self._spec}
            cap = self._capture
        if cap is not None:
            if is_down:
                cap["keys"].add(name)
            elif not self._spec:
                cap["done"].set()
            return
        if is_down and is_key and generic(name) not in NON_TYPING and name not in self.combo \
                and generic(name) not in self.combo:
            self.last_typed = time.time()
        if is_down:
            if not self.active and self.combo <= down:
                self.active = True
                threading.Thread(target=self.on_press, daemon=True).start()
        elif self.active and not self.combo <= down:
            self.active = False
            threading.Thread(target=self.on_release, daemon=True).start()

    # ---- UI helpers ----
    def capture(self, timeout=10.0):
        """Wait for the user to press and release a key/combination; return e.g. 'ctrl+windows' or 'f9'."""
        cap = {"keys": set(), "done": threading.Event()}
        with self._lock:
            self._spec.clear()
        self._capture = cap
        cap["done"].wait(timeout)
        self._capture = None
        keys = cap["keys"]
        if len(keys) == 1:
            return next(iter(keys))              # single key: keep left/right exactness ("right ctrl")
        gens = {generic(k) for k in keys}
        order = list(MODS)
        return "+".join(sorted(gens, key=lambda k: (order.index(k) if k in order else 9, k)))

    def wait_modifiers_released(self, timeout=1.0):
        t = time.time()
        while time.time() - t < timeout and any(
                keyboard.is_pressed(m) for m in ("windows", "alt", "shift")):
            time.sleep(0.02)
