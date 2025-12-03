import logging
import json
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def json_formatter(record):
    log = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": record.levelname,
        "service": "fms-backend",
        "message": record.getMessage(),
    }

    if hasattr(record, "request_id"):
        log["request_id"] = record.request_id
    if hasattr(record, "user_id"):
        log["user_id"] = record.user_id
    if hasattr(record, "path"):
        log["path"] = record.path
    if hasattr(record, "method"):
        log["method"] = record.method

    return json.dumps(log)

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json_formatter(record)

logger = logging.getLogger("fms")
logger.setLevel(logging.INFO)

json_f = JSONFormatter()

file_handler = RotatingFileHandler(
    "logs/app.json.log",
    maxBytes=5 * 1024 * 1024,
    backupCount=5
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(json_f)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(json_f)

if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
