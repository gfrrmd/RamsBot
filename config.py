import json
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
DATABASE_URL = os.environ["DATABASE_URL"]

# API credentials milik admin (1 untuk semua user)
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]

RESTRICTED_CHANNELS_RAW = os.environ.get("RESTRICTED_CHANNELS", "[]")
try:
    RESTRICTED_CHANNELS: list = json.loads(RESTRICTED_CHANNELS_RAW)
except Exception:
    RESTRICTED_CHANNELS = []

DEVICE_MODEL = "RamsBot VIP"
SYSTEM_VERSION = "iOS 26.4"
APP_VERSION = "11.4.1"
LANG_CODE = "id"
SYSTEM_LANG_CODE = "id-ID"
