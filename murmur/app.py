import ctypes
import logging
import os
import sys
import threading
import time

import pystray
from PIL import ImageDraw

from . import __version__, mascot, paths
from .controller import Controller
from .server import make_server
from .uiwindow import UiWindow


def _single_instance():
    # MURMUR_INSTANCE lets automated tests run a second copy next to a real one; normal use never sets it.
    h = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\MurmurDictationApp" + os.environ.get("MURMUR_INSTANCE", ""))
    return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


def main():
    logging.basicConfig(filename=paths.log_path(), level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.info("process %s starting", os.getpid())
    if not _single_instance():
        logging.info("another Murmur is already running; this copy (pid %s) will exit", os.getpid())
        from . import i18n
        msg = ("Murmur is already running. Look for the little bird in your system tray (bottom right).")
        ctypes.windll.user32.MessageBoxW(0, i18n.t(msg, i18n.system_lang()), "Murmur", 0x40)
        return
    background = "--background" in sys.argv
    ctl = Controller()
    srv, token = make_server(ctl)
    url = f"http://127.0.0.1:{srv.server_port}/"
    quitting = threading.Event()
    ui = UiWindow(url)

    def show_ui(*_):
        ui.open()

    ctl.show_ui = show_ui

    # ---- tray ----
    base = mascot.draw(64)

    def icon_for(state):
        im = base.copy()
        if state in ("listening", "paused"):
            d = ImageDraw.Draw(im)
            d.ellipse([44, 44, 62, 62], fill="#FF5C7A" if state == "listening" else "#999999",
                      outline="white", width=2)
        return im

    def toggle_pause(icon, item):
        ctl.paused = not ctl.paused

    def open_folder(*_):
        os.startfile(paths.sub("recordings"))

    def do_quit():
        if ctl.rec.active:       # never drop a live recording: stop + save it first
            try:
                ctl.stop_recording()
            except Exception:
                pass
        quitting.set()
        try:
            tray.stop()
        except Exception:
            pass

    def quit_app(icon, item):
        do_quit()

    def install_update(icon, item):
        try:
            ctl.install_update()
        except Exception as e:
            ctl.notify("Murmur", str(e))

    ctl.quit_app = do_quit
    ctl.notify = lambda title, msg: tray.notify(msg, title)

    tray = pystray.Icon("Murmur", icon_for("idle"), "Murmur", pystray.Menu(
        pystray.MenuItem(lambda i: ctl.T("Open Murmur"), show_ui, default=True),
        pystray.MenuItem(lambda i: ctl.T("Undo last dictation"), lambda i, m: ctl.undo_last()),
        pystray.MenuItem(lambda i: ctl.T("Install update {v}").replace(
            "{v}", (ctl.updates.available or {}).get("version", "")), install_update,
            visible=lambda i: bool(ctl.updates.available)),
        pystray.MenuItem(lambda i: ctl.T("Pause dictation"), toggle_pause, checked=lambda i: ctl.paused),
        pystray.MenuItem(lambda i: ctl.T("Open recordings folder"), open_folder),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(lambda i: ctl.T("Quit"), quit_app)))
    tray.run_detached()

    def tray_sync():
        last = None
        while not quitting.is_set():
            s = ctl.state
            if s != last:
                tray.icon = icon_for(s)
                tray.title = ctl.T({"idle": "Murmur: ready", "listening": "Murmur: listening…",
                                    "thinking": "Murmur: transcribing…", "paused": "Murmur: paused"}[s])
                last = s
            time.sleep(0.25)

    threading.Thread(target=tray_sync, daemon=True).start()

    # ---- window ----
    first = not ctl.cfg["first_run_done"]
    show_now = (first or "--show" in sys.argv) and not background
    if first:
        ctl.cfg.update({"first_run_done": True})
    logging.info("Murmur %s started (pid %s, window shown: %s)", __version__, os.getpid(), show_now)
    if show_now:
        ui.open()
    quitting.wait()                 # the tray and hotkey threads do the work; "Quit" ends this
    logging.info("Murmur exiting normally")
    ui.close()
    os._exit(0)
