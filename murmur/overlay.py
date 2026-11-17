"""Floating status pill with an animated Murmi. Never takes focus, so pasting goes to your app."""
import ctypes
import math
import queue
import random
import threading
import time
import tkinter as tk

from . import mascot as M

W, H = 190, 64
KEY = "#010203"
PILL = "#2B2438"


class Overlay:
    def __init__(self, get_level):
        self.get_level = get_level
        self._q = queue.Queue()
        self.state = "hidden"
        self.msg = ""
        self._hide_at = 0
        threading.Thread(target=self._run, daemon=True, name="overlay").start()

    # thread-safe API
    def set(self, state, msg="", hold=0.0):
        self._q.put((state, msg, hold))

    # ---- tk thread ----
    def _run(self):
        try:
            self.root = tk.Tk()
        except Exception:
            return
        r = self.root
        r.overrideredirect(True)
        r.attributes("-topmost", True)
        r.attributes("-transparentcolor", KEY)
        r.configure(bg=KEY)
        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        r.geometry(f"{W}x{H}+{(sw - W) // 2}+{sh - H - 90}")
        self.cv = tk.Canvas(r, width=W, height=H, bg=KEY, highlightthickness=0)
        self.cv.pack()
        r.withdraw()
        self._shown = False
        self._blink_until = 0
        self._next_blink = time.time() + 2
        self._levels = [0.0] * 12
        r.after(30, self._tick)
        r.mainloop()

    def _no_activate(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            GWL_EXSTYLE = -20
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            # NOACTIVATE | TOOLWINDOW | TRANSPARENT (click-through) | LAYERED
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | 0x08000000 | 0x80 | 0x20 | 0x80000)
        except Exception:
            pass

    def _tick(self):
        now = time.time()
        try:
            while True:
                st, msg, hold = self._q.get_nowait()
                self.state, self.msg = st, msg
                self._hide_at = now + hold if hold else 0
        except queue.Empty:
            pass
        if self._hide_at and now > self._hide_at:
            self.state, self._hide_at = "hidden", 0
        if self.state == "hidden":
            if self._shown:
                self.root.withdraw()
                self._shown = False
        else:
            if not self._shown:
                self.root.deiconify()
                self.root.update_idletasks()
                self._no_activate()
                self.root.attributes("-topmost", True)
                self._shown = True
            self._draw(now)
        self.root.after(33, self._tick)

    def _draw(self, t):
        c = self.cv
        c.delete("all")
        st = self.state
        # pill
        r = H // 2 - 4
        c.create_oval(4, 4, 4 + 2 * r, 4 + 2 * r, fill=PILL, outline=PILL)
        c.create_oval(W - 4 - 2 * r, 4, W - 4, 4 + 2 * r, fill=PILL, outline=PILL)
        c.create_rectangle(4 + r, 4, W - 4 - r, 4 + 2 * r, fill=PILL, outline=PILL)
        # mascot
        bob = math.sin(t * (7 if st == "listening" else 3)) * (3 if st == "listening" else 1.5)
        if st == "done":
            bob = -abs(math.sin(t * 9)) * 5
        cx, cy = 36, 31 + bob
        s = 0.34
        o = lambda x, y: (cx + (x - 60) * s, cy + (y - 62) * s)

        def oval(x, y, rx, ry, fill):
            a, b = o(x - rx, y - ry), o(x + rx, y + ry)
            c.create_oval(*a, *b, fill=fill, outline=fill)

        tuft = [o(56, 26), o(52, 10 - (4 * math.sin(t * 12) if st == "listening" else 0)), o(59, 18),
                o(62, 6), o(66, 18), o(72, 11), o(66, 28)]
        c.create_polygon(*[v for p in tuft for v in p], fill=M.BODY_DARK, outline=M.BODY_DARK)
        oval(21, 70, 9, 14, M.BODY_DARK)
        oval(99, 70, 9, 14, M.BODY_DARK)
        oval(60, 64, 42, 40, M.BODY)
        oval(60, 76, 27, 22, M.BELLY)
        oval(37, 68, 6, 4.5, M.CHEEK)
        oval(83, 68, 6, 4.5, M.CHEEK)
        if t > self._next_blink:
            self._blink_until, self._next_blink = t + 0.12, t + random.uniform(2, 5)
        blinking = t < self._blink_until and st != "error"
        look = math.sin(t * 4) * 3 if st == "thinking" else 0
        for ex in (46, 74):
            if st == "error":
                a = o(ex - 4, 53); b = o(ex + 4, 61)
                c.create_line(*a, *b, fill=M.INK, width=2); c.create_line(a[0], b[1], b[0], a[1], fill=M.INK, width=2)
            elif blinking:
                a, b = o(ex - 5, 57), o(ex + 5, 57)
                c.create_line(*a, *b, fill=M.INK, width=2)
            else:
                ry = 6.4 if st == "listening" else 5.6
                oval(ex + look, 57, 4.8, ry, M.INK)
                x, y = o(ex + look + 1.6, 55)
                c.create_oval(x - 1.4, y - 1.4, x + 1.4, y + 1.4, fill="white", outline="white")
        beak = [o(53, 64), o(67, 64), o(60, 73 + (3 if st == "listening" and int(t * 6) % 2 else 0))]
        c.create_polygon(*[v for p in beak for v in p], fill=M.BEAK, outline=M.BEAK)
        # right side
        x0 = 70
        if st == "listening":
            lvl = min(1.0, self.get_level() * 9)
            self._levels = self._levels[1:] + [lvl]
            for i, v in enumerate(self._levels):
                h = 4 + v * 26 * (0.6 + 0.4 * math.sin(i + t * 8))
                x = x0 + 8 + i * 9
                c.create_line(x, H / 2 - h / 2, x, H / 2 + h / 2, fill="#CDBFFF", width=4, capstyle="round")
        elif st == "thinking":
            for i in range(3):
                y = H / 2 - abs(math.sin(t * 5 - i * 0.7)) * 8
                c.create_oval(x0 + 20 + i * 22, y - 5, x0 + 30 + i * 22, y + 5, fill="#CDBFFF", outline="#CDBFFF")
            c.create_text(x0 + 10, H - 9, text="", fill="#CDBFFF")
        else:
            txt = self.msg or ("Pasted!" if st == "done" else "")
            c.create_text(x0 + 52, H / 2, text=txt, fill="#F4EFFF", font=("Segoe UI", 10, "bold"),
                          width=110)
