import json
import time

from confluent_kafka import Consumer  # type: ignore

from common.config import CANHBAO_KAFKA_CONF, KHOANG_NGHI, TOPIC_CANH_BAO
from common.logger import configure_logger
from xu_ly import xu_ly_canh_bao

logger = configure_logger("canhbao")
lan_gui_cuoi = {}


def main():
    consumer = Consumer(CANHBAO_KAFKA_CONF)
    consumer.subscribe([TOPIC_CANH_BAO])
    logger.info("Chương trình gửi cảnh báo đang chạy, nhấn Ctrl+C để dừng")

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            loi = msg.error()
            if loi:
                logger.error(f"Lỗi Kafka: {loi}")
                continue

            du_lieu = msg.value()
            if du_lieu is None:
                continue

            try:
                canh_bao = json.loads(du_lieu.decode("utf-8"))
                host = canh_bao["HOST"]
                loai = canh_bao["LOAI"]
                gia_tri = canh_bao.get("GIA_TRI", "N/A")
                thoi_gian = canh_bao.get("THOI_GIAN", "N/A")
            except (ValueError, KeyError) as e:
                logger.error(f"Bản ghi không hợp lệ: {e}")
                continue

            khoa = (host, loai)
            bay_gio = time.time()
            if bay_gio - lan_gui_cuoi.get(khoa, 0) < KHOANG_NGHI:
                continue

            if isinstance(gia_tri, float):
                gia_tri = round(gia_tri, 1)
            try:
                if xu_ly_canh_bao(host, loai, gia_tri, thoi_gian):
                    lan_gui_cuoi[khoa] = bay_gio
            except Exception as e:
                logger.error(f"Lỗi khi xử lý cảnh báo: {type(e).__name__}: {e}")
    except KeyboardInterrupt:
        logger.info("Đã dừng")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
