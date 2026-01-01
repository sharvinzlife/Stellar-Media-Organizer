"""
Tests for custom exceptions
"""
from core.exceptions import (
    AudioFilterError,
    DirectoryNotFoundError,
    FFmpegNotFoundError,
    IMDBLookupError,
    MediaOrganizerError,
    MKVToolNixNotFoundError,
    VideoConversionError,
)


def test_base_exception():
    """Test base MediaOrganizerError"""
    error = MediaOrganizerError("Test error", "Test details")

    assert str(error) == "Test error"
    assert error.message == "Test error"
    assert error.details == "Test details"

    error_dict = error.to_dict()
    assert error_dict["error"] == "MediaOrganizerError"
    assert error_dict["message"] == "Test error"
    assert error_dict["details"] == "Test details"


def test_directory_not_found_error():
    """Test DirectoryNotFoundError"""
    error = DirectoryNotFoundError("/nonexistent/path")

    assert "/nonexistent/path" in str(error)
    assert error.path == "/nonexistent/path"
    assert "permission" in error.details.lower()


def test_ffmpeg_not_found_error():
    """Test FFmpegNotFoundError"""
    error = FFmpegNotFoundError()

    assert "FFmpeg" in str(error)
    assert "brew install" in error.details or "apt install" in error.details


def test_mkvtoolnix_not_found_error():
    """Test MKVToolNixNotFoundError"""
    error = MKVToolNixNotFoundError()

    assert "MKVToolNix" in str(error)
    assert "mkvmerge" in str(error)


def test_video_conversion_error():
    """Test VideoConversionError"""
    error = VideoConversionError("/path/to/video.mkv", "Invalid codec")

    assert "/path/to/video.mkv" in str(error)
    assert error.file_path == "/path/to/video.mkv"
    assert error.reason == "Invalid codec"


def test_audio_filter_error():
    """Test AudioFilterError"""
    error = AudioFilterError("/path/to/video.mkv", "No matching tracks")

    assert "/path/to/video.mkv" in str(error)
    assert error.file_path == "/path/to/video.mkv"
    assert error.reason == "No matching tracks"


def test_imdb_lookup_error():
    """Test IMDBLookupError"""
    error = IMDBLookupError("Unknown Series", "API rate limit")

    assert "Unknown Series" in str(error)
    assert error.series_name == "Unknown Series"
    assert "API" in error.details


def test_exception_inheritance():
    """Test that all exceptions inherit from MediaOrganizerError"""
    exceptions = [
        DirectoryNotFoundError("/test"),
        FFmpegNotFoundError(),
        MKVToolNixNotFoundError(),
        VideoConversionError("/test.mkv"),
        AudioFilterError("/test.mkv"),
        IMDBLookupError("Test Series"),
    ]

    for exc in exceptions:
        assert isinstance(exc, MediaOrganizerError)
        assert isinstance(exc, Exception)

