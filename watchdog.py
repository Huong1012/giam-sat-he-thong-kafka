"""Canh gác mất dữ liệu: nếu một máy ngừng gửi số liệu quá lâu thì đẩy cảnh báo vào topic canh-bao.
ksqlDB chỉ lọc được tin nhắn đã đến, không phát hiện được tin nhắn không đến, nên cần chương trình này."""
import json
import time
from datetime import datetime

import requests  # type: ignore
from confluent_kafka import Producer  # type: ignore

from common.config import (
    MAT_DU_LIEU_GIAY,
    PROMETHEUS_URL,
    PRODUCER_KAFKA_CONF,
    TOPIC_CANH_BAO,
    WATCHDOG_CHU_KY,
)
from common.logger import configure_logger

logger = configure_logger("watchdog")


def phat_hien_mat(tuoi_hien_tai, lan_cuoi_thay, da_bao, bay_gio, nguong=MAT_DU_LIEU_GIAY):
    """tuoi_hien_tai: host -> số giây từ bản ghi gần nhất (chỉ có với host còn thấy trên Prometheus).
    lan_cuoi_thay: host -> mốc giây lần cuối thấy số liệu mới, được cập nhật tại chỗ.
    da_bao: tập host đã báo trong đợt mất hiện tại, được cập nhật tại chỗ.
    Trả về danh sách (host, số giây đã mất)."""
    for host, tuoi in tuoi_hien_tai.items():
        if tuoi <= nguong:
            lan_cuoi_thay[host] = bay_gio - tuoi
            da_bao.discard(host)
    ket_qua = []
    for host, luc in lan_cuoi_thay.items():
        mat = bay_gio - luc
        if mat > nguong and host not in da_bao:
            da_bao.add(host)
            ket_qua.append((host, int(mat)))
    return ket_qua


def hoi_tuoi_so_lieu():
    kq = requests.get(
        f"{PROMETHEUS_URL}/api/v1/query",
        # last_over_time nhìn lại 1 giờ để vẫn thấy máy khi consumer đã dừng và chỉ số trên Prometheus đã cũ
        params={"query": "time() - last_over_time(system_last_update_timestamp_seconds[1h])"},
        timeout=10,
    )
    kq.raise_for_status()
    return {r["metric"]["host"]: float(r["value"][1]) for r in kq.json()["data"]["result"]}


def main():
    producer = Producer(PRODUCER_KAFKA_CONF)
    lan_cuoi_thay, da_bao = {}, set()
    logger.info(f"Canh gác mất dữ liệu đang chạy, ngưỡng {MAT_DU_LIEU_GIAY} giây, nhấn Ctrl+C để dừng")
    try:
        while True:
            try:
                tuoi = hoi_tuoi_so_lieu()
            except Exception as loi:
                # Không hỏi được Prometheus thì không kết luận gì về máy
                logger.error(f"Không hỏi được Prometheus: {type(loi).__name__}")
                time.sleep(WATCHDOG_CHU_KY)
                continue
            bay_gio = time.time()
            for host, giay in phat_hien_mat(tuoi, lan_cuoi_thay, da_bao, bay_gio):
                ban_ghi = {
                    "HOST": host,
                    "LOAI": "MAT_DU_LIEU",
                    "GIA_TRI": giay,
                    "THOI_GIAN": datetime.fromtimestamp(bay_gio).strftime("%Y-%m-%d %H:%M:%S"),
                }
                producer.produce(TOPIC_CANH_BAO, key=host, value=json.dumps(ban_ghi, ensure_ascii=False))
                producer.flush(5)
                logger.warning(f"Máy {host} đã ngừng gửi số liệu {giay} giây, đã đẩy cảnh báo")
            time.sleep(WATCHDOG_CHU_KY)
    except KeyboardInterrupt:
        logger.info("Đã dừng")


if __name__ == "__main__":
    main()
