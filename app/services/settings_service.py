"""
Settings Service for managing user preferences.
"""
import os
import json
from typing import Optional
from PySide6.QtCore import QStandardPaths
from app.models.entities import Settings

class SettingsService:
    """Handles loading and saving application settings to a JSON file."""
    
    def __init__(self):
        self.settings_file = self._get_settings_path()
        self._settings: Optional[Settings] = None
        self.load_settings()

    def _get_settings_path(self) -> str:
        data_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        return os.path.join(data_dir, "settings.json")

    def load_settings(self) -> Settings:
        """Loads settings from disk, or creates defaults if missing."""
        if self._settings is not None:
            return self._settings
            
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._settings = Settings(**data)
            except Exception:
                self._settings = Settings() # Fallback to defaults on corruption
        else:
            self._settings = Settings()
            self.save_settings(self._settings)
            
        return self._settings

    def save_settings(self, settings: Settings) -> None:
        """Persists settings to disk."""
        self._settings = settings
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings.__dict__, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")
