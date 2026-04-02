import sys
import ctypes
import os

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if getattr(sys, 'frozen', False):
    exe_path = sys.executable
else:
    exe_path = sys.executable

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", exe_path, " ".join(sys.argv), None, 1
    )
    sys.exit()

from ui.app import run

if __name__ == "__main__":
    run()
