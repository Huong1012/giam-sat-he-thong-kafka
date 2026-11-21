import sys
import time
import psutil  # type: ignore
from datetime import datetime
from typing import Any, Optional

# Đảm bảo hiển thị đúng tiếng Việt có dấu trên Windows console
try:
    if hasattr(sys.stdout, "reconfigure"):
        getattr(sys.stdout, "reconfigure")(encoding="utf-8")
except Exception:
    pass

# Biến lưu trữ trạng thái mạng và thời gian lần đo trước
_prev_net: Any = None
_prev_time: Optional[float] = None
_prev_disk_io: Any = None
_cac_tien_trinh: dict = {}
_SO_LUONG = psutil.cpu_count() or 1


def _lay_disk_io(dt):
    """Tốc độ đọc và ghi đĩa, KB/s."""
    global _prev_disk_io
    hien_tai = psutil.disk_io_counters()
    if hien_tai is None or _prev_disk_io is None:
        _prev_disk_io = hien_tai
        return {"doc_kbps": 0.0, "ghi_kbps": 0.0}
    doc = (hien_tai.read_bytes - _prev_disk_io.read_bytes) / dt / 1024
    ghi = (hien_tai.write_bytes - _prev_disk_io.write_bytes) / dt / 1024
    _prev_disk_io = hien_tai
    return {"doc_kbps": round(max(doc, 0.0), 1), "ghi_kbps": round(max(ghi, 0.0), 1)}


def _lay_top_tien_trinh(so_luong=5):
    """Lấy các tiến trình tốn CPU nhất và tốn RAM nhất."""
    danh_sach = []
    con_song = set()
    for p in psutil.process_iter(["pid", "name"]):
        pid = p.info["pid"]
        con_song.add(pid)
        if pid == 0:
            continue
        try:
            proc = _cac_tien_trinh.get(pid)
            if proc is None:
                proc = psutil.Process(pid)
                _cac_tien_trinh[pid] = proc
                proc.cpu_percent(None)
                cpu_tp = 0.0
            else:
                cpu_tp = proc.cpu_percent(None) / _SO_LUONG
            ram_mb = proc.memory_info().rss / 1024 / 1024
            danh_sach.append(
                {"ten": p.info["name"] or "?", "cpu": round(cpu_tp, 1), "ram_mb": round(ram_mb, 1)}
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    for pid in list(_cac_tien_trinh):
        if pid not in con_song:
            del _cac_tien_trinh[pid]
    top_cpu = sorted(danh_sach, key=lambda x: x["cpu"], reverse=True)[:so_luong]
    top_ram = sorted(danh_sach, key=lambda x: x["ram_mb"], reverse=True)[:so_luong]
    return top_cpu, top_ram


def lay_so_lieu():
    """
    Thu thập số liệu hệ thống và trả về dictionary gồm:
    - thoi_gian: chuỗi thời gian định dạng YYYY-MM-DD HH:MM:SS
    - cpu: % CPU tổng
    - cpu_tung_luong: danh sách % CPU từng luồng
    - ram: % RAM đang sử dụng
    - disk: dict ánh xạ từng ổ đĩa (vd: 'C:') sang % dung lượng sử dụng
    - net_gui: tốc độ mạng gửi đi (KB/s)
    - net_nhan: tốc độ mạng nhận về (KB/s)
    Các nhóm số liệu mở rộng:
    - cpu_tan_so: tần số CPU hiện tại (MHz)
    - so_tien_trinh: số tiến trình đang chạy
    - ram_da_dung_gb, ram_con_trong_gb, swap: bộ nhớ RAM và vùng nhớ tráo đổi
    - disk_io: tốc độ đọc và ghi đĩa (KB/s)
    - net_loi: số lỗi và số gói rớt mỗi giây của card mạng
    - top_cpu, top_ram: các tiến trình tốn tài nguyên nhất
    - thoi_gian_chay: số giây từ lúc khởi động máy
    - pin: phần trăm pin và trạng thái cắm sạc
    """
    global _prev_net, _prev_time

    now = time.time()
    curr_net = psutil.net_io_counters()

    # Nếu là lần đầu tiên gọi, thiết lập mốc đo ban đầu
    if _prev_net is None or _prev_time is None:
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None, percpu=True)
        _prev_net = curr_net
        _prev_time = now
        time.sleep(0.5)
        now = time.time()
        curr_net = psutil.net_io_counters()

    # Tính toán tốc độ mạng (KB/s) dựa trên độ chênh lệch và số giây
    if curr_net is None or _prev_net is None or _prev_time is None:
        net_gui = 0.0
        net_nhan = 0.0
    else:
        dt = max(now - _prev_time, 0.001)
        net_gui = (curr_net.bytes_sent - _prev_net.bytes_sent) / dt / 1024
        net_nhan = (curr_net.bytes_recv - _prev_net.bytes_recv) / dt / 1024

    # Lỗi và gói rớt của card mạng, tính theo giây
    net_loi = {"loi_vao": 0.0, "loi_ra": 0.0, "rot_vao": 0.0, "rot_ra": 0.0}
    if curr_net is not None and _prev_net is not None and _prev_time is not None:
        dt_loi = max(now - _prev_time, 0.001)
        net_loi = {
            "loi_vao": round((curr_net.errin - _prev_net.errin) / dt_loi, 2),
            "loi_ra": round((curr_net.errout - _prev_net.errout) / dt_loi, 2),
            "rot_vao": round((curr_net.dropin - _prev_net.dropin) / dt_loi, 2),
            "rot_ra": round((curr_net.dropout - _prev_net.dropout) / dt_loi, 2),
        }
    dt_chung = max(now - _prev_time, 0.001) if _prev_time is not None else 1.0

    # Cập nhật mốc đo cho lần sau
    _prev_net = curr_net
    _prev_time = now

    # 1. Thời gian hiện tại
    thoi_gian = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 2 & 6. % CPU tổng và % từng luồng
    cpu = psutil.cpu_percent(interval=None)
    raw_percpu = psutil.cpu_percent(interval=None, percpu=True)
    if isinstance(raw_percpu, list):
        cpu_tung_luong = [round(val, 1) for val in raw_percpu]
    else:
        cpu_tung_luong = [round(float(raw_percpu), 1)]

    # 3. % RAM
    ram = psutil.virtual_memory().percent

    # 4. % của mọi ổ đĩa (bọc try/except để bỏ qua ổ lỗi, không ghi cứng tên ổ)
    disk = {}
    disk_gb = {}
    for part in psutil.disk_partitions(all=False):
        if "cdrom" in part.opts or part.fstype == "":
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            # Chuẩn hóa tên ổ (vd: 'C:\' -> 'C:')
            ten_o = part.device.rstrip("\\") if part.device else part.mountpoint.rstrip("\\")
            if ten_o and ten_o not in disk:
                disk[ten_o] = usage.percent
                disk_gb[ten_o] = {
                    "da_dung": round(usage.used / 1024**3, 1),
                    "con_trong": round(usage.free / 1024**3, 1),
                    "tong": round(usage.total / 1024**3, 1),
                }
        except (PermissionError, OSError):
            continue

    # Các nhóm số liệu mở rộng
    tan_so = psutil.cpu_freq()
    bo_nho = psutil.virtual_memory()
    swap = psutil.swap_memory().percent
    top_cpu, top_ram = _lay_top_tien_trinh()
    pin = psutil.sensors_battery()

    return {
        "thoi_gian": thoi_gian,
        "cpu": cpu,
        "cpu_tung_luong": cpu_tung_luong,
        "ram": ram,
        "disk": disk,
        "disk_gb": disk_gb,
        "net_gui": net_gui,
        "net_nhan": net_nhan,
        "cpu_tan_so": round(tan_so.current, 0) if tan_so else 0.0,
        "so_tien_trinh": len(psutil.pids()),
        "ram_da_dung_gb": round(bo_nho.used / 1024**3, 2),
        "ram_con_trong_gb": round(bo_nho.available / 1024**3, 2),
        "swap": swap,
        "disk_io": _lay_disk_io(dt_chung),
        "net_loi": net_loi,
        "top_cpu": top_cpu,
        "top_ram": top_ram,
        "thoi_gian_chay": int(time.time() - psutil.boot_time()),
        "pin": {"phan_tram": round(pin.percent, 0), "cam_sac": 1 if pin.power_plugged else 0}
        if pin
        else None,
    }


def in_so_lieu(d):
    """
    Nhận dict dữ liệu và in ra 2 dòng thông tin theo đúng định dạng yêu cầu.
    """
    # Chuỗi hiển thị các ổ đĩa, ví dụ: "C: 72.0% D: 35.4%"
    disk_str = " ".join(f"{ten_o} {pt:.1f}%" for ten_o, pt in d["disk"].items())
    disk_hien_thi = f"Disk {disk_str}" if disk_str else "Disk N/A"

    # Dòng 1: Thời gian | CPU | RAM | Disk | Net
    dong_1 = (
        f"{d['thoi_gian']} | "
        f"CPU {d['cpu']:.1f}% | "
        f"RAM {d['ram']:.1f}% | "
        f"{disk_hien_thi} | "
        f"Net ↑ {d['net_gui']:.1f} KB/s ↓ {d['net_nhan']:.1f} KB/s"
    )

    # Dòng 2: CPU từng luồng
    dong_2 = f"CPU từng luồng: {d['cpu_tung_luong']}"

    dong_3 = (
        f"Tần số {d['cpu_tan_so']:.0f} MHz | Tiến trình {d['so_tien_trinh']} | "
        f"RAM dùng {d['ram_da_dung_gb']} GB, còn {d['ram_con_trong_gb']} GB | Swap {d['swap']:.1f}% | "
        f"Đĩa đọc {d['disk_io']['doc_kbps']} ghi {d['disk_io']['ghi_kbps']} KB/s"
    )
    top = ", ".join(f"{t['ten']} {t['cpu']}%" for t in d["top_cpu"][:3])
    dong_4 = f"Top CPU: {top}"

    print(dong_1)
    print(dong_2)
    print(dong_3)
    print(dong_4)


if __name__ == "__main__":
    try:
        while True:
            d = lay_so_lieu()
            in_so_lieu(d)
            time.sleep(2)
    except KeyboardInterrupt:
        print("Đã dừng")
