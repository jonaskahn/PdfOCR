import os
import re

from dotenv import load_dotenv

load_dotenv()

DEBUG_MODE = os.getenv("DEBUG_MODE", "on")
SUPPORTED_LANGUAGES = re.split("[,;]", os.getenv("SUPPORTED_LANGUAGES", "vi"))
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "52428800"))
MINIMUM_WORDS_PER_PAGE = int(os.getenv("MINIMUM_WORDS_PER_PAGE", 100))
WATERMARK_PATTERNS = os.getenv(
    "WATERMARK_PATTERNS", "watermark|confidential|draft|copy|www.LuatVietnam.vn"
)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/storage")
os.makedirs(UPLOAD_DIR, exist_ok=True)
