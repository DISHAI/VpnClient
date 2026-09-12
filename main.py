

import sys
import os
import ctypes
import platform


def is_admin() -> bool:
    
    try:
        if platform.system() == "Windows":
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except Exception:
        return False


def request_admin():
    
    if platform.system() == "Windows":
        if getattr(sys, 'frozen', False):
            executable = sys.executable
            params = " ".join(sys.argv[1:])
        else:
            executable = sys.executable
            params = '"' + os.path.abspath(sys.argv[0]) + '"'
            if len(sys.argv) > 1:
                params += " " + " ".join(sys.argv[1:])

        try:
            ret = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                executable,
                params,
                None,
                0
            )
            if ret > 32:
                sys.exit(0)
            else:
                return False
        except Exception:
            return False

    elif platform.system() == "Linux":
        if os.path.isfile("/usr/bin/pkexec"):
            os.execvp("pkexec", ["pkexec", sys.executable] + sys.argv)
        else:
            os.execvp("sudo", ["sudo", sys.executable] + sys.argv)

    elif platform.system() == "Darwin":
        import shlex
        script = f'do shell script {shlex.quote(sys.executable + " " + " ".join(sys.argv))} with administrator privileges'
        os.system(f"osascript -e {shlex.quote(script)}")
        sys.exit(0)

    return False


def hide_console():
    
    if platform.system() == "Windows":
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
        except Exception:
            pass


def main():
    hide_console()

    autostart = "--autostart" in sys.argv

    if not is_admin():
        if not request_admin():
            pass
        else:
            return

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from gui.app import VPNApp
    app = VPNApp(start_minimized=autostart)
    app.run()


if __name__ == "__main__":
    main()