"""
Configuration module for the Audio Transcription App.
Centralizes all settings and environment variables.
"""
import os
from dataclasses import dataclass
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class TranscriptionConfig:
    """Configuration for transcription settings."""
    max_duration_seconds: int = 600  # 10 minutes
    chunk_overlap_seconds: int = 5   # Overlap between chunks
    silence_padding_ms: int = 100    # Silence added at the beginning
    max_file_size_mb: int = 25       # OpenAI API limit

@dataclass
class UIConfig:
    """Configuration for UI elements."""
    page_title: str = "Audio Transcription App"
    layout: str = "wide"
    default_language: str = "it"
    default_model: str = "gpt-4o-transcribe"
    default_description: str = "A conversation about ..."

@dataclass
class SupportedFormats:
    """Supported audio formats and their configurations."""
    upload_types: List[str] = None
    
    def __post_init__(self):
        if self.upload_types is None:
            self.upload_types = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]

@dataclass
class LanguageConfig:
    """Language configuration and mappings."""
    supported_languages: Dict[str, str] = None
    
    def __post_init__(self):
        if self.supported_languages is None:
            self.supported_languages = {
                "it": "Italian",
                "en": "English", 
                "es": "Spanish",
                "fr": "French",
                "de": "German",
                "auto": "Auto-detect"
            }

class AppConfig:
    """Main application configuration."""
    
    def __init__(self):
        self.transcription = TranscriptionConfig()
        self.ui = UIConfig()
        self.formats = SupportedFormats()
        self.languages = LanguageConfig()
        
        # API Configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.summary_model = os.getenv("SUMMARY_MODEL", "gpt-4o-mini")
        
        # Debug settings
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Validate required settings
        self._validate_config()
    
    def _validate_config(self):
        """Validate required configuration values."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
    
    @property
    def language_options(self) -> List[str]:
        """Get list of supported language codes."""
        return list(self.languages.supported_languages.keys())
    
    @property
    def language_display_map(self) -> Dict[str, str]:
        """Get mapping of language codes to display names."""
        return self.languages.supported_languages
    
    def get_language_display_name(self, code: str) -> str:
        """Get display name for a language code."""
        return self.languages.supported_languages.get(code, code)

# Global configuration instance
config = AppConfig() 