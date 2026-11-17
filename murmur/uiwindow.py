"""Murmur's window: an Edge (or Chrome) "app window" showing the local settings page.

An embedded web view proved unreliable (it can stay white until the window is resized), so we use the
browser that every Windows 10/11 PC has. It runs with its own profile, so it never touches your normal
browsing, and closing the window only closes the window: Murmur keeps running in the tray.
"""
import logging
import os
import subprocess
import webbrowser

from . import paths

log = logging.getLogger("murmur")
NO_WINDOW = 0x08000000


def find_browser():
    bases = [os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")]
    for rel in (r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"):
        for b in bases:
            if b and os.path.exists(os.path.join(b, rel)):
                return os.path.join(b, rel)
    return None


class UiWindow:
    def __init__(self, url):
        self.url = url
        self.profile = os.path.join(paths.data_dir(), "ui-profile")

    def open(self):
        exe = find_browser()
        if exe:
            try:
                subprocess.Popen(
                    [exe, f"--app={self.url}", "--window-size=1000,740", f"--user-data-dir={self.profile}",
                     "--no-first-run", "--no-default-browser-check"],
                    close_fds=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                log.exception("could not start %s, falling back to the default browser", exe)
        webbrowser.open(self.url)

    def close(self):
        """Close the app window (called when Murmur quits) by stopping browser processes using our profile."""
        script = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*Murmur\\ui-profile*' } "
                  "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }")
        try:
            subprocess.run(["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
                           creationflags=NO_WINDOW, timeout=15)
        except Exception:
            pass
