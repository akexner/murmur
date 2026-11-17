import threading
import time

import keyboard


def norm(name: str) -> str:
    n = (name or "").lower()
    for p in ("left ", "right "):
        if n.startswith(p):
            n = n[len(p):]
    return {"win": "windows", "control": "ctrl"}.get(n, n)


def combo_of(s: str) -> set:
    return {norm(p.strip()) for p in s.split("+") if p.strip()}


class HotkeyManager:
    def __init__(self, on_press, on_release):
        self.on_press, self.on_release = on_press, on_release
        self.combo = {"ctrl", "windows"}
        self.down = set()
        self.active = False
        self._capture = None
        self._hook = keyboard.hook(self._event, suppress=False)

    def set_combo(self, s: str):
        c = combo_of(s)
        if c:
            self.combo = c

    def _event(self, e):
        k = norm(e.name)
        if e.event_type == "down":
            self.down.add(k)
        else:
            self.down.discard(k)
        cap = self._capture
        if cap is not None:
            if e.event_type == "down":
                cap["keys"] |= {k}
            elif not self.down:
                cap["done"].set()
            return
        if e.event_type == "down":
            if not self.active and self.combo <= self.down:
                self.active = True
                threading.Thread(target=self.on_press, daemon=True).start()
        else:
            if self.active and not self.combo <= self.down:
                self.active = False
                threading.Thread(target=self.on_release, daemon=True).start()

    def capture(self, timeout=10.0):
        """Wait for the user to press and release a combo; return e.g. 'ctrl+windows'."""
        cap = {"keys": set(), "done": threading.Event()}
        self.down.clear()
        self._capture = cap
        cap["done"].wait(timeout)
        self._capture = None
        order = ["ctrl", "alt", "shift", "windows"]
        keys = sorted(cap["keys"], key=lambda k: (order.index(k) if k in order else 9, k))
        return "+".join(keys)

    def wait_modifiers_released(self, timeout=1.0):
        t = time.time()
        while time.time() - t < timeout and any(
                keyboard.is_pressed(m) for m in ("windows", "alt", "shift")):
            time.sleep(0.02)
