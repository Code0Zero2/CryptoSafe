from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

APP_NAME = "CRYPTOSAFE"
APP_VERSION = "0.1.0"
APP_MODE = "DEMO"

DEFAULT_DB_PATH = DATA_DIR / "cryptosafe.db"
DEFAULT_LOG_PATH = LOGS_DIR / "cryptosafe.log"

LOG_LEVEL = os.environ.get("CRYPTOSAFE_LOG_LEVEL", "INFO")

