"""Lấy số liệu của một máy trong vài phút gần nhất từ Prometheus."""
import time

import requests  # type: ignore

from common.config import BUOC_GIAY, CUA_SO_GIAY, PROMETHEUS_URL, SAU_CANH_BAO
from common.logger import configure_logger

logger = configure_logger("thu_thap")

# Tên chuỗi, câu truy vấn PromQL theo nhãn host
CAC_CHUOI = {
    "cpu": "system_cpu_percent",
    "ram": "system_memory_percent",
    "ram_dung_gb": "system_memory_used_gb",
    "ram_trong_gb": "system_memory_available_gb",
    "swap": "system_swap_percent",
    "doc": "system_disk_read_kbps",
    "ghi": "system_disk_write_kbps",
    "gui": "system_network_sent_kbps",
    "nhan": "system_network_recv_kbps",
    "pin": "system_battery_percent",
}


def _nhan_host(host):
    return host.replace("\\", "").replace('"', "")


def _hoi(duong_dan, tham_so):
    kq = requests.get(f"{PROMETHEUS_URL}{duong_dan}", params=tham_so, timeout=10)
    kq.raise_for_status()
    du_lieu = kq.json()
    if du_lieu.get("status") != "success":
        raise RuntimeError(f"Prometheus báo lỗi: {du_lieu.get('error')}")
    return du_lieu["data"]["result"]


def _chuoi(ten_metric, host, bat_dau, ket_thuc):
    ket_qua = _hoi(
        "/api/v1/query_range",
        {
            "query": f'{ten_metric}{{host="{_nhan_host(host)}"}}',
            "start": bat_dau,
            "end": ket_thuc,
            "step": BUOC_GIAY,
        },
    )
    if not ket_qua:
        return []
    return [(float(t), float(v)) for t, v in ket_qua[0]["values"]]


def _chuoi_theo_nhan(ten_metric, ten_nhan, host, bat_dau, ket_thuc):
    """Một metric có nhiều chuỗi phân biệt bằng nhãn, ví dụ mỗi ổ đĩa một chuỗi."""
    ket_qua = _hoi(
        "/api/v1/query_range",
        {
            "query": f'{ten_metric}{{host="{_nhan_host(host)}"}}',
            "start": bat_dau,
            "end": ket_thuc,
            "step": BUOC_GIAY,
        },
    )
    return {
        r["metric"].get(ten_nhan, "?"): [(float(t), float(v)) for t, v in r["values"]]
        for r in ket_qua
    }


def _top(ten_metric, host, luc):
    ket_qua = _hoi(
        "/api/v1/query", {"query": f'{ten_metric}{{host="{_nhan_host(host)}"}}', "time": luc}
    )
    dong = []
    for r in ket_qua:
        nhan = r["metric"]
        dong.append((int(nhan.get("hang", 99)), nhan.get("ten", "?"), float(r["value"][1])))
    dong.sort()
    return [(ten, gia_tri) for _, ten, gia_tri in dong]


def lay_du_lieu(host, t_canh_bao=None):
    """Lấy số liệu quanh thời điểm cảnh báo: từ CUA_SO_GIAY giây trước đến SAU_CANH_BAO giây sau.
    Không có thời điểm cảnh báo thì lấy đến hiện tại. Lỗi ở phần nào thì phần đó rỗng."""
    if t_canh_bao is None:
        t_canh_bao = time.time()
    ket_thuc = min(t_canh_bao + SAU_CANH_BAO, time.time())
    bat_dau = t_canh_bao - CUA_SO_GIAY
    du_lieu = {
        "host": host, "chuoi": {}, "top_cpu": [], "top_ram": [], "disk": {}, "disk_gb": {"da_dung": {}, "con_trong": {}},
        "t_canh_bao": t_canh_bao, "bat_dau": bat_dau, "ket_thuc": ket_thuc,
    }

    for ten, metric in CAC_CHUOI.items():
        try:
            du_lieu["chuoi"][ten] = _chuoi(metric, host, bat_dau, ket_thuc)
        except Exception as loi:
            logger.error(f"Không lấy được chuỗi {ten}: {type(loi).__name__}")
            du_lieu["chuoi"][ten] = []

    # Dung lượng từng ổ đĩa theo thời gian, và gói rớt theo chiều vào ra
    try:
        du_lieu["disk_gb"]["da_dung"] = _chuoi_theo_nhan("system_disk_used_gb", "disk", host, bat_dau, ket_thuc)
        du_lieu["disk_gb"]["con_trong"] = _chuoi_theo_nhan("system_disk_free_gb", "disk", host, bat_dau, ket_thuc)
    except Exception as loi:
        logger.error(f"Không lấy được dung lượng ổ đĩa theo thời gian: {type(loi).__name__}")
    try:
        rot = _chuoi_theo_nhan("system_network_drops_per_second", "huong", host, bat_dau, ket_thuc)
        du_lieu["chuoi"]["rot_vao"] = rot.get("vao", [])
        du_lieu["chuoi"]["rot_ra"] = rot.get("ra", [])
        # Tổng hai chiều, dùng cho cảnh báo gói rớt
        tong = {}
        for chuoi_huong in (du_lieu["chuoi"]["rot_vao"], du_lieu["chuoi"]["rot_ra"]):
            for t, v in chuoi_huong:
                tong[t] = tong.get(t, 0.0) + v
        du_lieu["chuoi"]["rot_tong"] = sorted(tong.items())
    except Exception as loi:
        logger.error(f"Không lấy được gói rớt: {type(loi).__name__}")
        du_lieu["chuoi"]["rot_vao"] = du_lieu["chuoi"]["rot_ra"] = []

    for khoa, metric in (
        ("top_cpu", "system_top_process_cpu_percent"),
        ("top_ram", "system_top_process_memory_mb"),
    ):
        try:
            du_lieu[khoa] = _top(metric, host, ket_thuc)
        except Exception as loi:
            logger.error(f"Không lấy được {khoa}: {type(loi).__name__}")

    try:
        ket_qua = _hoi(
            "/api/v1/query",
            {"query": f'system_disk_percent{{host="{_nhan_host(host)}"}}', "time": ket_thuc},
        )
        du_lieu["disk"] = {r["metric"].get("disk", "?"): float(r["value"][1]) for r in ket_qua}
    except Exception as loi:
        logger.error(f"Không lấy được dung lượng ổ đĩa: {type(loi).__name__}")

    return du_lieu


def thong_ke(chuoi, so_mau=6):
    """Tóm tắt một chuỗi: hiện tại, nhỏ nhất, lớn nhất, trung bình và vài mẫu đều nhau."""
    if not chuoi:
        return None
    gia_tri = [v for _, v in chuoi]
    buoc = max(len(gia_tri) // so_mau, 1)
    mau = [round(v, 1) for v in gia_tri[::buoc][-so_mau:]]
    return {
        "hien_tai": round(gia_tri[-1], 1),
        "nho_nhat": round(min(gia_tri), 1),
        "lon_nhat": round(max(gia_tri), 1),
        "trung_binh": round(sum(gia_tri) / len(gia_tri), 1),
        "cac_mau": mau,
    }
