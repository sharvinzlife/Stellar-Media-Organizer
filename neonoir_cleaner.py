import re
from abc import ABC

class FormatCleaner(ABC):
    pass

class NeoNoirCleaner(FormatCleaner):
    __slots__ = ()
    _pattern = re.compile(r'^(.+?)\.(2024|2025)\.\d+p\..*?x265-NeoNoir', re.IGNORECASE)
    
    def can_clean(self, filename: str) -> bool:
        return 'NeoNoir' in filename and bool(self._pattern.search(filename))
    
    def clean(self, filename: str) -> str:
        match = self._pattern.match(filename)
        if match:
            title = match.group(1).replace('.', ' ').strip()
            return f"{title} ({match.group(2)})"
        return filename
    
    def get_format_name(self) -> str:
        return "NeoNoir Release"

# Test
cleaner = NeoNoirCleaner()
test = "Black.Phone.2.2025.1080p.MA.WEBRip.10Bit.DDP5.1.x265-NeoNoir.mkv"
print(f"Can clean: {cleaner.can_clean(test)}")
print(f"Cleaned: {cleaner.clean(test)}")
