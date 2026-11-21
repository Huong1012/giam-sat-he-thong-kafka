import configparser
import socket
from pathlib import Path

from dotenv import load_dotenv  # type: ignore

# Đọc config.ini nằm cùng thư mục dự án, không phụ thuộc thư mục đang chạy
THU_MUC_DU_AN = Path(__file__).resolve().parent.parent

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

config = configparser.ConfigParser(interpolation=None)
config.read(THU_MUC_DU_AN / "config.ini", encoding="utf-8")

TEN_MAY = socket.gethostname()

BOOTSTRAP_SERVERS = config.get("KAFKA", "bootstrap_servers")
TOPIC_SO_LIEU = config.get("KAFKA", "topic_so_lieu")
TOPIC_CANH_BAO = config.get("KAFKA", "topic_canh_bao")

CHU_KY = config.getfloat("PRODUCER", "chu_ky")

PRODUCER_KAFKA_CONF = {
    "bootstrap.servers": BOOTSTRAP_SERVERS,
    "client.id": TEN_MAY,
}
CONSUMER_KAFKA_CONF = {
    "bootstrap.servers": BOOTSTRAP_SERVERS,
    "group.id": config.get("CONSUMER", "group_id"),
    "auto.offset.reset": config.get("CONSUMER", "auto_offset_reset"),
}
CONG_METRICS = config.getint("CONSUMER", "cong_metrics")

CANHBAO_KAFKA_CONF = {
    "bootstrap.servers": BOOTSTRAP_SERVERS,
    "group.id": config.get("CANHBAO", "group_id"),
    "auto.offset.reset": "latest",
}
KHOANG_NGHI = config.getint("CANHBAO", "khoang_nghi")

logging_config = {
    "filename": THU_MUC_DU_AN / config.get("LOGGING", "file_name"),
    "level": config.get("LOGGING", "log_level"),
    "format": config.get("LOGGING", "format"),
}

PROMETHEUS_URL = config.get("PROMETHEUS", "dia_chi").rstrip("/")
CUA_SO_GIAY = config.getint("PROMETHEUS", "cua_so_giay")
BUOC_GIAY = config.getint("PROMETHEUS", "buoc_giay")
SAU_CANH_BAO = config.getint("PROMETHEUS", "sau_canh_bao_giay")
DOI_TOI = config.getint("PROMETHEUS", "doi_toi_giay")

CAC_MO_HINH_AI = [m.strip() for m in config.get("AI", "cac_mo_hinh").split(",") if m.strip()]
THOI_GIAN_CHO_AI = config.getint("AI", "thoi_gian_cho")

THU_MUC_ANH = THU_MUC_DU_AN / config.get("ANH", "thu_muc")
NGUONG_VE = config.getfloat("ANH", "nguong")
NGUONG_SWAP = config.getfloat("ANH", "nguong_swap")
NGUONG_PIN = config.getfloat("ANH", "nguong_pin")
NGUONG_ROT = config.getfloat("ANH", "nguong_rot")

WATCHDOG_CHU_KY = config.getint("WATCHDOG", "chu_ky_giay")
MAT_DU_LIEU_GIAY = config.getint("WATCHDOG", "mat_du_lieu_giay")
