"""
Custom exception classes for Media Organizer Pro
Provides user-friendly error messages and proper error handling
"""


class MediaOrganizerError(Exception):
    """Base exception for all Media Organizer errors"""

    def __init__(self, message: str, details: str | None = None):
        self.message = message
        self.details = details
        super().__init__(self.message)

    def to_dict(self):
        """Convert exception to dictionary for API responses"""
        result = {"error": self.__class__.__name__, "message": self.message}
        if self.details:
            result["details"] = self.details
        return result


class DirectoryNotFoundError(MediaOrganizerError):
    """Raised when a specified directory does not exist"""

    def __init__(self, path: str):
        message = f"Directory not found: {path}"
        details = "Please check that the path exists and you have permission to access it."
        super().__init__(message, details)
        self.path = path


class FileNotFoundError(MediaOrganizerError):
    """Raised when a specified file does not exist"""

    def __init__(self, path: str):
        message = f"File not found: {path}"
        details = "Please check that the file exists and you have permission to access it."
        super().__init__(message, details)
        self.path = path


class FFmpegNotFoundError(MediaOrganizerError):
    """Raised when FFmpeg is not installed or not in PATH"""

    def __init__(self):
        message = "FFmpeg is not installed or not found in PATH"
        details = (
            "Please install FFmpeg:\n"
            "  • macOS: brew install ffmpeg\n"
            "  • Ubuntu/Debian: sudo apt install ffmpeg\n"
            "  • Windows: Download from https://ffmpeg.org/download.html"
        )
        super().__init__(message, details)


class MKVToolNixNotFoundError(MediaOrganizerError):
    """Raised when MKVToolNix (mkvmerge) is not installed or not in PATH"""

    def __init__(self):
        message = "MKVToolNix (mkvmerge) is not installed or not found in PATH"
        details = (
            "Please install MKVToolNix:\n"
            "  • macOS: brew install mkvtoolnix\n"
            "  • Ubuntu/Debian: sudo apt install mkvtoolnix\n"
            "  • Windows: Download from https://mkvtoolnix.download/"
        )
        super().__init__(message, details)


class VideoConversionError(MediaOrganizerError):
    """Raised when video conversion fails"""

    def __init__(self, file_path: str, reason: str | None = None):
        message = f"Video conversion failed: {file_path}"
        details = reason or "Check ffmpeg output for more details"
        super().__init__(message, details)
        self.file_path = file_path
        self.reason = reason


class AudioFilterError(MediaOrganizerError):
    """Raised when audio filtering fails"""

    def __init__(self, file_path: str, reason: str | None = None):
        message = f"Audio filtering failed: {file_path}"
        details = reason or "Check mkvmerge output for more details"
        super().__init__(message, details)
        self.file_path = file_path
        self.reason = reason


class NoAudioTracksFoundError(AudioFilterError):
    """Raised when no audio tracks matching the language are found"""

    def __init__(self, file_path: str, language: str):
        details = (
            "The file may not contain audio in the specified language. "
            "Try analyzing the file with 'mkvmerge -i <file>' to see available tracks."
        )
        super().__init__(file_path, details)
        self.language = language


class IMDBLookupError(MediaOrganizerError):
    """Raised when IMDB lookup fails"""

    def __init__(self, series_name: str, reason: str | None = None):
        message = f"IMDB lookup failed for: {series_name}"
        details = reason or "Series not found or API unavailable"
        super().__init__(message, details)
        self.series_name = series_name


class InvalidFormatError(MediaOrganizerError):
    """Raised when file format is not supported"""

    def __init__(self, file_path: str, expected_formats: list | None = None):
        message = f"Unsupported file format: {file_path}"
        if expected_formats:
            details = f"Expected one of: {', '.join(expected_formats)}"
        else:
            details = "File format is not supported"
        super().__init__(message, details)
        self.file_path = file_path
        self.expected_formats = expected_formats


class ConfigurationError(MediaOrganizerError):
    """Raised when configuration is invalid"""

    def __init__(self, config_key: str, reason: str | None = None):
        message = f"Invalid configuration: {config_key}"
        details = reason or "Please check your configuration settings"
        super().__init__(message, details)
        self.config_key = config_key


class PermissionError(MediaOrganizerError):
    """Raised when permission is denied"""

    def __init__(self, path: str, operation: str = "access"):
        message = f"Permission denied to {operation}: {path}"
        details = "Please check file/directory permissions"
        super().__init__(message, details)
        self.path = path
        self.operation = operation


class DiskSpaceError(MediaOrganizerError):
    """Raised when insufficient disk space"""

    def __init__(self, required_bytes: int, available_bytes: int):
        message = "Insufficient disk space"
        details = (
            f"Required: {required_bytes / (1024**3):.2f} GB, "
            f"Available: {available_bytes / (1024**3):.2f} GB"
        )
        super().__init__(message, details)
        self.required_bytes = required_bytes
        self.available_bytes = available_bytes

