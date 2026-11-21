import json
import time
from datetime import datetime

from confluent_kafka import Consumer  # type: ignore
from prometheus_client import Gauge, start_http_server  # type: ignore

from common.config import CONG_METRICS, CONSUMER_KAFKA_CONF, TOPIC_SO_LIEU
from common.logger import configure_logger

logger = configure_logger("consumer")

cpu = Gauge("system_cpu_percent", "Phần trăm CPU tổng", ["host"])
cpu_core = Gauge("system_cpu_core_percent", "Phần trăm CPU từng luồng", ["host", "core"])
ram = Gauge("system_memory_percent", "Phần trăm RAM đang dùng", ["host"])
disk = Gauge("system_disk_percent", "Phần trăm dung lượng ổ đĩa đã dùng", ["host", "disk"])
net_gui = Gauge("system_network_sent_kbps", "Tốc độ mạng gửi đi, KB/s", ["host"])
net_nhan = Gauge("system_network_recv_kbps", "Tốc độ mạng nhận về, KB/s", ["host"])
cpu_tan_so = Gauge("system_cpu_frequency_mhz", "Tần số CPU hiện tại, MHz", ["host"])
tien_trinh = Gauge("system_process_count", "Số tiến trình đang chạy", ["host"])
ram_dung = Gauge("system_memory_used_gb", "Dung lượng RAM đã dùng, GB", ["host"])
ram_trong = Gauge("system_memory_available_gb", "Dung lượng RAM còn trống, GB", ["host"])
swap = Gauge("system_swap_percent", "Phần trăm vùng nhớ tráo đổi đã dùng", ["host"])
disk_doc = Gauge("system_disk_read_kbps", "Tốc độ đọc đĩa, KB/s", ["host"])
disk_ghi = Gauge("system_disk_write_kbps", "Tốc độ ghi đĩa, KB/s", ["host"])
net_loi = Gauge("system_network_errors_per_second", "Số lỗi card mạng mỗi giây", ["host", "huong"])
net_rot = Gauge("system_network_drops_per_second", "Số gói rớt mỗi giây", ["host", "huong"])
chay = Gauge("system_uptime_seconds", "Số giây từ lúc khởi động máy", ["host"])
pin_pt = Gauge("system_battery_percent", "Phần trăm pin", ["host"])
pin_sac = Gauge("system_battery_plugged", "Đang cắm sạc, 1 là có", ["host"])
top_cpu = Gauge(
    "system_top_process_cpu_percent", "Tiến trình tốn CPU nhất", ["host", "hang", "ten"]
)
top_ram = Gauge(
    "system_top_process_memory_mb", "Tiến trình tốn RAM nhất, MB", ["host", "hang", "ten"]
)
disk_dung_gb = Gauge("system_disk_used_gb", "Dung lượng ổ đĩa đã dùng, GB", ["host", "disk"])
disk_trong_gb = Gauge("system_disk_free_gb", "Dung lượng ổ đĩa còn trống, GB", ["host", "disk"])
disk_tong_gb = Gauge("system_disk_total_gb", "Tổng dung lượng ổ đĩa, GB", ["host", "disk"])
_nhan_top: dict = {}
cap_nhat = Gauge(
    "system_last_update_timestamp_seconds",
    "Thời điểm nhận bản ghi gần nhất, tính bằng giây",
    ["host"],
)
tre = Gauge(
    "system_pipeline_delay_seconds",
    "Độ trễ từ lúc đo đến lúc consumer nhận, tính bằng giây",
    ["host"],
)


def cap_nhat_top(gauge, host, ten_nhom, danh_sach, truong):
    """Đặt lại các dòng top, xóa nhãn của tiến trình đã rời khỏi bảng xếp hạng."""
    khoa = (ten_nhom, host)
    for nhan in _nhan_top.get(khoa, set()):
        try:
            gauge.remove(*nhan)
        except KeyError:
            pass
    moi = set()
    for i, tt in enumerate(danh_sach, start=1):
        nhan = (host, str(i), tt["ten"])
        gauge.labels(*nhan).set(tt[truong])
        moi.add(nhan)
    _nhan_top[khoa] = moi


def cap_nhat_mo_rong(host, b):
    """Các nhóm số liệu mở rộng, dùng .get để bản ghi cũ vẫn đọc được."""
    if "cpu_tan_so" in b:
        cpu_tan_so.labels(host).set(b["cpu_tan_so"])
        tien_trinh.labels(host).set(b["so_tien_trinh"])
        ram_dung.labels(host).set(b["ram_da_dung_gb"])
        ram_trong.labels(host).set(b["ram_con_trong_gb"])
        swap.labels(host).set(b["swap"])
        chay.labels(host).set(b["thoi_gian_chay"])
    io = b.get("disk_io")
    if io:
        disk_doc.labels(host).set(io["doc_kbps"])
        disk_ghi.labels(host).set(io["ghi_kbps"])
    loi = b.get("net_loi")
    if loi:
        net_loi.labels(host, "vao").set(loi["loi_vao"])
        net_loi.labels(host, "ra").set(loi["loi_ra"])
        net_rot.labels(host, "vao").set(loi["rot_vao"])
        net_rot.labels(host, "ra").set(loi["rot_ra"])
    for ten_o, gb in (b.get("disk_gb") or {}).items():
        disk_dung_gb.labels(host, ten_o).set(gb["da_dung"])
        disk_trong_gb.labels(host, ten_o).set(gb["con_trong"])
        disk_tong_gb.labels(host, ten_o).set(gb["tong"])
    pin = b.get("pin")
    if pin:
        pin_pt.labels(host).set(pin["phan_tram"])
        pin_sac.labels(host).set(pin["cam_sac"])
    if b.get("top_cpu"):
        cap_nhat_top(top_cpu, host, "cpu", b["top_cpu"], "cpu")
    if b.get("top_ram"):
        cap_nhat_top(top_ram, host, "ram", b["top_ram"], "ram_mb")


def cap_nhat_chi_so(ban_ghi):
    host = ban_ghi["host"]
    cpu.labels(host).set(ban_ghi["cpu"])
    for i, gia_tri in enumerate(ban_ghi["cpu_tung_luong"]):
        cpu_core.labels(host, f"{i + 1:02d}").set(gia_tri)
    ram.labels(host).set(ban_ghi["ram"])
    for ten_o, phan_tram in ban_ghi["disk"].items():
        disk.labels(host, ten_o).set(phan_tram)
    net_gui.labels(host).set(ban_ghi["net_gui"])
    net_nhan.labels(host).set(ban_ghi["net_nhan"])

    cap_nhat_mo_rong(host, ban_ghi)

    luc_do = datetime.strptime(ban_ghi["thoi_gian"], "%Y-%m-%d %H:%M:%S")
    tre.labels(host).set((datetime.now() - luc_do).total_seconds())
    cap_nhat.labels(host).set(time.time())


def main():
    consumer = Consumer(CONSUMER_KAFKA_CONF)
    consumer.subscribe([TOPIC_SO_LIEU])
    start_http_server(CONG_METRICS)
    logger.info(f"Consumer chạy, số liệu tại http://localhost:{CONG_METRICS}/metrics")
    logger.info("Nhấn Ctrl+C để dừng")

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
                ban_ghi = json.loads(du_lieu.decode("utf-8"))
                cap_nhat_chi_so(ban_ghi)
                logger.info(
                    f"Đã nhận: {ban_ghi['host']} "
                    f"cpu={ban_ghi['cpu']}% ram={ban_ghi['ram']}%"
                )
            except Exception as e:
                logger.error(f"Bản ghi không hợp lệ hoặc lỗi xử lý: {e}")
    except KeyboardInterrupt:
        logger.info("Đã dừng")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()