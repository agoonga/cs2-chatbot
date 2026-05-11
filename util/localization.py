"""
Localization module for multi-language support.
Manages loading, retrieving, and formatting translated strings.
"""

import json
import os
from typing import Optional, Dict, Any
import logging


class LocalizationManager:
    """Manages translations for the bot across multiple languages."""
    
    def __init__(self, strings_dir: str = "strings", default_language: str = "en_US"):
        """
        Initialize the localization manager.
        
        Args:
            strings_dir: Directory containing translation JSON files
            default_language: Default language code (e.g., "en_US")
        """
        self.strings_dir = strings_dir
        self.default_language = default_language
        self.current_language = default_language
        self.translations: Dict[str, Dict] = {}
        self.logger = logging.getLogger(__name__)
        
        # Load default language and current language
        self._load_language(default_language)
        if default_language != self.current_language:
            self._load_language(self.current_language)
    
    def _load_language(self, language_code: str) -> bool:
        """
        Load a language's translation file.
        
        Args:
            language_code: Language code (e.g., "en_US", "pt_BR")
            
        Returns:
            True if loaded successfully, False otherwise
        """
        if language_code in self.translations:
            return True  # Already loaded
        
        file_path = os.path.join(self.strings_dir, f"{language_code}.json")
        
        if not os.path.exists(file_path):
            self.logger.warning(f"Translation file not found: {file_path}")
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.translations[language_code] = json.load(f)
            self.logger.info(f"Loaded translations for {language_code}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load translations for {language_code}: {e}")
            return False
    
    def set_language(self, language_code: str) -> bool:
        """
        Set the current language.
        
        Args:
            language_code: Language code (e.g., "pt_BR")
            
        Returns:
            True if set successfully, False if language not available
        """
        if not self._load_language(language_code):
            self.logger.warning(f"Could not set language to {language_code}, keeping {self.current_language}")
            return False
        
        self.current_language = language_code
        self.logger.info(f"Language changed to {language_code}")
        return True
    
    def get_string(self, key: str, language: Optional[str] = None, **kwargs) -> str:
        """
        Get a translated string by key.
        
        Args:
            key: Dot-separated key path (e.g., "commands.fishing.cast_success_fish")
            language: Optional language override. If not provided, uses current language.
            **kwargs: Format arguments for string interpolation
            
        Returns:
            Translated string, or the key itself if not found (with fallback to default language)
        """
        lang = language or self.current_language

        # Load requested language lazily if it hasn't been loaded yet.
        if lang not in self.translations:
            self._load_language(lang)
        
        # Try to get string from requested language
        string = self._get_nested_value(lang, key)
        
        # Fallback to default language if not found
        if string is None and lang != self.default_language:
            if self.default_language not in self.translations:
                self._load_language(self.default_language)
            self.logger.debug(f"Key '{key}' not found in {lang}, falling back to {self.default_language}")
            string = self._get_nested_value(self.default_language, key)
        
        # If still not found, return the key
        if string is None:
            self.logger.warning(f"Translation key not found: {key}")
            return key
        
        # Format string with provided arguments
        if kwargs:
            try:
                string = string.format(**kwargs)
            except KeyError as e:
                self.logger.error(f"Missing format argument for key '{key}': {e}")
        
        return string

    def get_value(self, key: str, language: Optional[str] = None, default=None):
        """Get any translated value (string, list, dict) by key with fallback."""
        lang = language or self.current_language

        if lang not in self.translations:
            self._load_language(lang)

        value = self._get_nested_any(lang, key)
        if value is None and lang != self.default_language:
            if self.default_language not in self.translations:
                self._load_language(self.default_language)
            value = self._get_nested_any(self.default_language, key)

        return default if value is None else value
    
    def _get_nested_value(self, language: str, key: str) -> Optional[str]:
        """
        Get a value from nested dictionary using dot notation.
        
        Args:
            language: Language code
            key: Dot-separated key path
            
        Returns:
            The value if found, None otherwise
        """
        if language not in self.translations:
            return None
        
        keys = key.split('.')
        value = self.translations[language]
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value if isinstance(value, str) else None

    def _get_nested_any(self, language: str, key: str):
        """Get a value from nested dictionary using dot notation, preserving original type."""
        if language not in self.translations:
            return None

        keys = key.split('.')
        value = self.translations[language]

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None

        return value
    
    def get_available_languages(self) -> list:
        """Get list of available language codes in the strings directory."""
        languages = []
        if os.path.exists(self.strings_dir):
            for file in os.listdir(self.strings_dir):
                if file.endswith('.json'):
                    lang_code = file.replace('.json', '')
                    languages.append(lang_code)
        return sorted(languages)


# Global localization manager instance
_localization_manager: Optional[LocalizationManager] = None


def initialize_localization(strings_dir: str = "strings", default_language: str = "en_US") -> LocalizationManager:
    """
    Initialize the global localization manager.
    
    Args:
        strings_dir: Directory containing translation JSON files
        default_language: Default language code
        
    Returns:
        The initialized LocalizationManager instance
    """
    global _localization_manager
    _localization_manager = LocalizationManager(strings_dir, default_language)
    return _localization_manager


def get_localization_manager() -> LocalizationManager:
    """Get the global localization manager instance."""
    global _localization_manager
    if _localization_manager is None:
        _localization_manager = LocalizationManager()
    return _localization_manager
