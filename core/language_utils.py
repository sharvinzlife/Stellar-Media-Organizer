#!/usr/bin/env python3
"""
Centralized Language Utilities
Single source of truth for language detection, mapping, and keywords.
"""

from pathlib import Path

# =============================================================================
# LANGUAGE KEYWORDS - Single Source of Truth
# =============================================================================
# Comprehensive language support with ISO 639-1/639-2 codes and native scripts

LANGUAGE_KEYWORDS: dict[str, frozenset[str]] = {
    # Indian languages
    'malayalam': frozenset(['malayalam', 'mal', 'ml', 'm', 'mala', 'malay', 'mlm', 'mym', 'മലയാളം']),
    'tamil': frozenset(['tamil', 'tam', 'ta', 't', 'tml', 'தமிழ்']),
    'telugu': frozenset(['telugu', 'tel', 'te', 'tlg', 'తెలుగు']),
    'hindi': frozenset(['hindi', 'hin', 'hi', 'h', 'hnd', 'हिन्दी', 'हिंदी']),
    'kannada': frozenset(['kannada', 'kan', 'kn', 'k', 'knd', 'ಕನ್ನಡ']),
    'bengali': frozenset(['bengali', 'ben', 'bn', 'b', 'bng', 'bangla', 'বাংলা']),
    'marathi': frozenset(['marathi', 'mar', 'mr', 'mrt', 'मराठी']),
    'gujarati': frozenset(['gujarati', 'guj', 'gu', 'ગુજરાતી']),
    'punjabi': frozenset(['punjabi', 'pan', 'pa', 'pnb', 'ਪੰਜਾਬੀ', 'پنجابی']),
    'odia': frozenset(['odia', 'oriya', 'ori', 'or', 'ory', 'ଓଡ଼ିଆ']),
    # European languages
    'english': frozenset(['english', 'eng', 'en']),
    'spanish': frozenset(['spanish', 'spa', 'es', 'español']),
    'french': frozenset(['french', 'fra', 'fre', 'fr', 'français']),
    'german': frozenset(['german', 'deu', 'ger', 'de', 'deutsch']),
    'italian': frozenset(['italian', 'ita', 'it', 'italiano']),
    'portuguese': frozenset(['portuguese', 'por', 'pt', 'português']),
    'russian': frozenset(['russian', 'rus', 'ru', 'русский']),
    'polish': frozenset(['polish', 'pol', 'pl']),
    'dutch': frozenset(['dutch', 'nld', 'dut', 'nl']),
    'swedish': frozenset(['swedish', 'swe', 'sv']),
    'norwegian': frozenset(['norwegian', 'nor', 'no', 'nb', 'nn']),
    'danish': frozenset(['danish', 'dan', 'da']),
    'finnish': frozenset(['finnish', 'fin', 'fi']),
    'greek': frozenset(['greek', 'gre', 'ell', 'el']),
    'czech': frozenset(['czech', 'ces', 'cze', 'cs']),
    'hungarian': frozenset(['hungarian', 'hun', 'hu']),
    'romanian': frozenset(['romanian', 'ron', 'rum', 'ro']),
    'ukrainian': frozenset(['ukrainian', 'ukr', 'uk']),
    'turkish': frozenset(['turkish', 'tur', 'tr']),
    # Asian languages
    'japanese': frozenset(['japanese', 'jpn', 'ja', '日本語']),
    'korean': frozenset(['korean', 'kor', 'ko', '한국어']),
    'chinese': frozenset(['chinese', 'zho', 'chi', 'zh', 'cmn', 'mandarin', '中文']),
    'thai': frozenset(['thai', 'tha', 'th']),
    'vietnamese': frozenset(['vietnamese', 'vie', 'vi']),
    'indonesian': frozenset(['indonesian', 'ind', 'id']),
    'malay': frozenset(['malay', 'msa', 'may', 'ms']),
    # Middle Eastern
    'arabic': frozenset(['arabic', 'ara', 'ar', 'عربي']),
    'hebrew': frozenset(['hebrew', 'heb', 'he', 'עברית']),
}

# Filename keywords for language detection (includes delimiters)
FILENAME_LANGUAGE_KEYWORDS: dict[str, list[str]] = {
    'malayalam': ['malayalam', ' mal ', '-mal-', '.mal.', 'mlm', '[mal]', '(mal)', 'mal-', '-mal'],
    'hindi': ['hindi', 'bollywood', ' hin ', '-hin-', '.hin.', '[hin]', '(hin)'],
    'tamil': ['tamil', ' tam ', '-tam-', '.tam.', '[tam]', '(tam)'],
    'telugu': ['telugu', ' tel ', '-tel-', '.tel.', '[tel]', '(tel)'],
}


def normalize_language(language: str | None) -> str | None:
    """
    Normalize a language string or code into a canonical form.
    
    Examples:
        "Malayalam" / "mal" / "ml" -> "malayalam"
        "Hindi" / "hi" -> "hindi"
        "en" / "English" -> "english"
    """
    if not language:
        return None
    
    lang = language.strip().lower()
    # Handle combined languages like "Malayalam, English"
    primary = lang.split(",")[0].strip()
    
    # Check against all known language keywords
    for canonical, keywords in LANGUAGE_KEYWORDS.items():
        if primary in keywords:
            return canonical
    
    return primary


def is_language_match(value: str, target_language: str) -> bool:
    """Check if a value matches the target language."""
    keywords = LANGUAGE_KEYWORDS.get(target_language.lower())
    if not keywords:
        return False
    return value.lower() in keywords


def detect_language_from_filename(filename: str) -> str | None:
    """
    Detect language from filename using keyword patterns.
    
    Returns: 'malayalam', 'hindi', 'tamil', 'telugu', or None
    """
    filename_lower = filename.lower()
    
    # Priority order for detection
    for lang in ['malayalam', 'hindi', 'tamil', 'telugu']:
        keywords = FILENAME_LANGUAGE_KEYWORDS.get(lang, [])
        if any(kw in filename_lower for kw in keywords):
            return lang
    
    return None


def detect_language_from_mkv(file_path: Path, log_func=None) -> str | None:
    """
    Detect primary language from MKV audio tracks.
    
    Args:
        file_path: Path to MKV file
        log_func: Optional logging function (msg, level)
    
    Returns: 'malayalam', 'hindi', 'tamil', 'telugu', 'english', or None
    """
    import json
    import shutil
    import subprocess
    
    if not file_path.exists() or file_path.suffix.lower() != '.mkv':
        return None
    
    if not shutil.which("mkvmerge"):
        return None
    
    try:
        result = subprocess.run(
            ['mkvmerge', '-J', str(file_path)],
            capture_output=True, text=True, check=True, timeout=30
        )
        info = json.loads(result.stdout)
        
        audio_tracks = [t for t in info.get('tracks', []) if t.get('type') == 'audio']
        if not audio_tracks:
            return None
        
        # Priority languages
        priority = ['malayalam', 'hindi', 'tamil', 'telugu', 'english']
        
        for lang in priority:
            keywords = LANGUAGE_KEYWORDS.get(lang, frozenset())
            for track in audio_tracks:
                track_lang = track.get('properties', {}).get('language', '').lower()
                track_name = track.get('properties', {}).get('track_name', '').lower()
                
                if track_lang in keywords or any(kw in track_name for kw in keywords):
                    if log_func:
                        log_func(f"🎵 MKV audio track language detected: {lang}", "info")
                    return lang
        
        return None
        
    except Exception:
        return None


def is_tv_content(filename: str) -> bool:
    """Detect if filename indicates TV show content."""
    import re
    
    filename_lower = filename.lower()
    tv_patterns = [
        r"s\d{1,2}e\d{1,2}",
        r"season\s*\d+",
        r"episode\s*\d+",
        r"\d{1,2}x\d{1,2}",
        r"e\d{2,3}",
        r"ep\d{1,3}",
    ]
    return any(re.search(p, filename_lower) for p in tv_patterns)


def get_category_for_language(language: str | None, is_tv: bool = False) -> str:
    """
    Get the appropriate category based on language and content type.
    
    Returns: Category string like 'malayalam movies', 'bollywood movies', 'tv-shows', etc.
    """
    lang = (language or "").lower()
    
    if is_tv:
        if lang == "malayalam":
            return "malayalam-tv-shows"
        return "tv-shows"
    
    if lang == "malayalam":
        return "malayalam movies"
    if lang == "hindi":
        return "bollywood movies"
    
    return "movies"
