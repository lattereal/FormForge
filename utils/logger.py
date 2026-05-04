import logging
import os
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

class ConsoleColor:
    HEADER    = '\033[95m'
    OKCYAN    = '\033[96m'
    OKGREEN   = '\033[92m'
    WARNING   = '\033[93m'
    FAIL      = '\033[91m'
    SUCCESS   = '\033[92m'
    BOLD      = '\033[1m'
    DIM       = '\033[2m'
    UNDERLINE = '\033[4m'
    ENDC      = '\033[0m'
    WHITE     = '\033[97m'
    BLUE      = '\033[94m'

_logger = None

def setup_logger():
    global _logger
    os.makedirs(LOG_DIR, exist_ok=True)
    session_name = datetime.now().strftime("session_%Y-%m-%d_%H-%M-%S.log")
    log_path = os.path.join(LOG_DIR, session_name)
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    _logger = logging.getLogger("FormForge")
    return log_path

def log_info(msg):
    if _logger:
        _logger.info(msg)

def log_success(msg):
    if _logger:
        _logger.info(f"[SUCCESS] {msg}")

def log_fail(msg):
    if _logger:
        _logger.warning(f"[FAIL] {msg}")

def log_warn(msg):
    if _logger:
        _logger.warning(f"[WARN] {msg}")

def get_log_dir():
    return LOG_DIR
