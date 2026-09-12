

import logging
import os
from datetime import datetime


class AppLogger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_logger()
        return cls._instance
    
    def _init_logger(self):
        log_dir = os.path.join(os.path.expanduser("~"), ".vpn_client", "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"vpn_{datetime.now().strftime('%Y%m%d')}.log")
        
        self.logger = logging.getLogger("VPNClient")
        self.logger.setLevel(logging.DEBUG)
        
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.INFO)
        
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
        self.log_buffer = []
        self.max_buffer = 1000
        self.callbacks = []
    
    def add_callback(self, callback):
        self.callbacks.append(callback)
    
    def remove_callback(self, callback):
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _notify(self, message: str, level: str):
        entry = {
            'time': datetime.now().strftime('%H:%M:%S'),
            'level': level,
            'message': message
        }
        self.log_buffer.append(entry)
        if len(self.log_buffer) > self.max_buffer:
            self.log_buffer = self.log_buffer[-self.max_buffer:]

        if level == "DEBUG":
            return

        for cb in self.callbacks:
            try:
                cb(entry)
            except Exception:
                pass
    
    def info(self, msg):
        self.logger.info(msg)
        self._notify(msg, "INFO")
    
    def warning(self, msg):
        self.logger.warning(msg)
        self._notify(msg, "WARNING")
    
    def error(self, msg):
        self.logger.error(msg)
        self._notify(msg, "ERROR")
    
    def debug(self, msg):
        self.logger.debug(msg)
        self._notify(msg, "DEBUG")

    def get_log_dir(self) -> str:
        return os.path.join(os.path.expanduser("~"), ".vpn_client", "logs")

    def get_log_files(self) -> list:
        log_dir = self.get_log_dir()
        files = []
        if os.path.isdir(log_dir):
            for f in sorted(os.listdir(log_dir)):
                if f.endswith(".log"):
                    path = os.path.join(log_dir, f)
                    size = os.path.getsize(path)
                    files.append({"name": f, "path": path, "size": size})
        return files

    def clear_all_logs(self):
        for f in self.get_log_files():
            try:
                os.remove(f["path"])
            except Exception:
                pass
        self.log_buffer.clear()


def get_logger() -> AppLogger:
    return AppLogger()