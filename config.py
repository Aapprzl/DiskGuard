import os
import json
from pathlib import Path


class Config:
    DEFAULT_CONFIG = {
        "default_output_folder": "",
        "chunk_size_mb": 4,
        "auto_retry_count": 5,
        "theme": "dark",
        "color_accent": "blue"
    }
    
    def __init__(self):
        self.config_dir = Path.home() / ".diskguard"
        self.config_file = self.config_dir / "config.json"
        self.data = self._load()
    
    def _load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    for key, value in self.DEFAULT_CONFIG.items():
                        if key not in data:
                            data[key] = value
                    return data
            except Exception:
                return self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()
    
    def save(self):
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def set(self, key, value):
        self.data[key] = value
        self.save()


config = Config()
