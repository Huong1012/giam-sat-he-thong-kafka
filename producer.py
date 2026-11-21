import json
import time

from confluent_kafka import Producer  # type: ignore

from common.config import CHU_KY, PRODUCER_KAFKA_CONF, TEN_MAY, TOPIC_SO_LIEU
from common.logger import configure_logger
from sysinfo import lay_so_lieu

logger = configure_logger("producer")
producer = Producer(PRODUCER_KAFKA_CONF)


def bao_loi(err, msg):
    if err is not None:
        logger.error(f"Gửi thất bại: {err}")


def main():
    logger.info(f"Producer chạy cho máy {TEN_MAY}, nhấn Ctrl+C để dừng")
    lay_so_lieu()
    time.sleep(CHU_KY)
    try:
        while True:
            so_lieu = lay_so_lieu()
            so_lieu["host"] = TEN_MAY
            producer.produce(
                TOPIC_SO_LIEU,
                key=TEN_MAY,
                value=json.dumps(so_lieu, ensure_ascii=False),
                callback=bao_loi,
            )
            producer.poll(0)
            logger.info(f"Đã gửi: cpu={so_lieu['cpu']}% ram={so_lieu['ram']}%")
            time.sleep(CHU_KY)
    except KeyboardInterrupt:
        logger.info("Đã dừng")
    finally:
        producer.flush()


if __name__ == "__main__":
    main()
