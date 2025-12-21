"""
Tests for configuration management
"""
import pytest
from pathlib import Path
from config import Settings, get_settings


def test_settings_defaults():
    """Test that settings have sensible defaults"""
    settings = Settings()
    
    assert settings.app_name == "Media Organizer Pro"
    assert settings.app_version == "6.1.0"
    assert settings.api_port == 8000
    assert settings.debug is False


def test_settings_path_expansion():
    """Test that paths are properly expanded"""
    settings = Settings()
    
    # All paths should be Path objects
    assert isinstance(settings.media_path, Path)
    assert isinstance(settings.upload_dir, Path)
    assert isinstance(settings.temp_dir, Path)
    assert isinstance(settings.output_dir, Path)
    
    # Paths should be absolute
    assert settings.upload_dir.is_absolute()


def test_settings_create_directories(tmp_path):
    """Test directory creation"""
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        temp_dir=tmp_path / "temp",
        output_dir=tmp_path / "output"
    )
    
    settings.create_directories()
    
    assert settings.upload_dir.exists()
    assert settings.temp_dir.exists()
    assert settings.output_dir.exists()


def test_settings_singleton():
    """Test that get_settings returns the same instance"""
    settings1 = get_settings()
    settings2 = get_settings()
    
    assert settings1 is settings2


def test_settings_to_dict():
    """Test conversion to dictionary"""
    settings = Settings()
    config_dict = settings.to_dict()
    
    assert isinstance(config_dict, dict)
    assert "app_name" in config_dict
    assert "api_port" in config_dict
    assert config_dict["app_name"] == "Media Organizer Pro"


def test_settings_validation():
    """Test settings validation"""
    # Test valid volume boost
    settings = Settings(default_volume_boost=1.5)
    assert settings.default_volume_boost == 1.5
    
    # Test that invalid values raise errors
    with pytest.raises(Exception):
        Settings(default_volume_boost=5.0)  # Too high

