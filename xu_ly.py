"""Xử lý một cảnh báo: lấy số liệu, nhờ AI nhận định, vẽ ảnh, gửi đi."""
import time
from datetime import datetime

from ai_tom_tat import tom_tat
from common.config import DOI_TOI, THU_MUC_ANH
from common.logger import configure_logger
from gui_tin import gui_discord, gui_telegram
from thu_thap import lay_du_lieu
from ve_anh import ve

logger = configure_logger("xu_ly")

TEN_LOAI = {
    "RAM_CAO": "RAM cao",
    "CPU_CAO": "CPU cao",
    "DIA_DAY_C": "Ổ đĩa C đầy",
    "DIA_DAY_D": "Ổ đĩa D đầy",
    "SWAP_CAO": "Swap cao",
    "PIN_YEU": "Pin yếu",
    "GOI_ROT": "Mạng rớt gói",
    "MAT_DU_LIEU": "Mất dữ liệu từ máy",
}
DON_VI = {"MAT_DU_LIEU": " giây", "GOI_ROT": " gói/giây"}


def nhan_dinh_du_phong(canh_bao, du_lieu):
    """Dùng khi AI không trả lời được: nêu số liệu và tiến trình tốn nhất, không suy diễn."""
    dong = [f"Nhận định: {canh_bao['ten_loai']}, giá trị {canh_bao['gia_tri']}{canh_bao['don_vi']}, vượt ngưỡng cảnh báo."]
    if du_lieu["top_cpu"] and canh_bao["loai"] == "CPU_CAO":
        t, v = du_lieu["top_cpu"][0]
        dong.append(f"Tiến trình tốn CPU nhất lúc này là {t} với {v:.1f}%.")
    elif du_lieu["top_ram"]:
        t, v = du_lieu["top_ram"][0]
        dong.append(f"Tiến trình tốn RAM nhất lúc này là {t} với {v:.0f} MB.")
    dong.append("Đề xuất: kiểm tra các tiến trình trên và đóng bớt ứng dụng không cần thiết.")
    return "\n".join(dong)


def gia_tri_o_dia(loai, du_lieu, t_canh_bao):
    """Với cảnh báo ổ đĩa, trả về dạng 'đã dùng/tổng GB' lấy tại điểm gần lúc cảnh báo nhất. Không có thì trả None."""
    if loai == "RAM_CAO":
        c = du_lieu.get("chuoi", {})
        d, f = c.get("ram_dung_gb"), c.get("ram_trong_gb")
        if not d or not f:
            return None
        gd = min(d, key=lambda p: abs(p[0] - t_canh_bao))[1]
        gf = min(f, key=lambda p: abs(p[0] - t_canh_bao))[1]
        return f"{gd:.1f}/{gd + gf:.1f} GB".replace(".", ",")
    if not loai.startswith("DIA_DAY_"):
        return None
    o = loai[-1] + ":"
    gb = du_lieu.get("disk_gb", {})
    da_dung = gb.get("da_dung", {}).get(o)
    con_trong = gb.get("con_trong", {}).get(o)
    if not da_dung or not con_trong:
        return None
    d = min(da_dung, key=lambda p: abs(p[0] - t_canh_bao))[1]
    t = min(con_trong, key=lambda p: abs(p[0] - t_canh_bao))[1]
    return f"{d:.0f}/{d + t:.0f} GB".replace(".", ",")


def doi_thoi_gian(thoi_gian):
    """Đổi chuỗi thời gian của bản ghi thành mốc giây. Không đọc được thì coi là vừa xảy ra."""
    try:
        return datetime.strptime(thoi_gian, "%Y-%m-%d %H:%M:%S").timestamp()
    except (ValueError, TypeError):
        return time.time() - 2


def xu_ly_canh_bao(host, loai, gia_tri, thoi_gian, chay_thu=False):
    bat_dau = time.time()
    t_canh_bao = doi_thoi_gian(thoi_gian)
    # Chờ để số liệu sau thời điểm cảnh báo kịp đi qua Kafka và Prometheus
    cho = t_canh_bao + DOI_TOI - time.time()
    if cho > 0:
        time.sleep(cho)
    canh_bao = {
        "host": host,
        "loai": loai,
        "ten_loai": TEN_LOAI.get(loai, loai),
        "don_vi": DON_VI.get(loai, "%"),
        "gia_tri": gia_tri,
        "thoi_gian": thoi_gian,
        "chay_thu": chay_thu,
    }

    t0 = time.time()
    du_lieu = lay_du_lieu(host, t_canh_bao)
    t_so_lieu = time.time() - t0
    if chay_thu and loai == "GOI_ROT":
        tong = du_lieu["chuoi"].get("rot_tong", [])
        if not tong or max(v for _, v in tong) < 1:
            # Máy thật không rớt gói, dựng đoạn mô phỏng quanh lúc cảnh báo để minh họa ảnh
            moc = [t for t, _ in du_lieu["chuoi"].get("cpu", [])] or [t_canh_bao]
            du_lieu["chuoi"]["rot_tong"] = [
                (t, float(gia_tri) if t_canh_bao - 12 <= t <= t_canh_bao + 5 else 0.0) for t in moc
            ]
            canh_bao["mo_phong"] = True
    gia_tri_gb = gia_tri_o_dia(loai, du_lieu, t_canh_bao)
    if gia_tri_gb:
        canh_bao["gia_tri_chu"] = gia_tri_gb

    t0 = time.time()
    nhan_dinh = tom_tat(canh_bao, du_lieu)
    t_ai = time.time() - t0
    nguon = "Gemini"
    if not nhan_dinh:
        nhan_dinh = nhan_dinh_du_phong(canh_bao, du_lieu)
        nguon = "AI chưa phản hồi, dùng nhận định tự động"

    t0 = time.time()
    anh = ve(canh_bao, du_lieu, nhan_dinh, nguon)
    t_ve = time.time() - t0

    THU_MUC_ANH.mkdir(parents=True, exist_ok=True)
    duong_dan = THU_MUC_ANH / f"{datetime.now():%Y%m%d_%H%M%S}_{loai}.png"
    duong_dan.write_bytes(anh)

    gia_tri_hien_thi = canh_bao.get("gia_tri_chu") or f"{gia_tri}".replace(".", ",") + canh_bao["don_vi"]
    chu_thich = (
        f"{'[CHẠY THỬ] ' if chay_thu else ''}CẢNH BÁO: {canh_bao['ten_loai']}\n"
        f"Máy: {host}\nGiá trị: {gia_tri_hien_thi}\nThời điểm: {thoi_gian}"
    )
    t0 = time.time()
    ok_tele = gui_telegram(anh, chu_thich)
    ok_disc = gui_discord(anh, chu_thich)
    t_gui = time.time() - t0

    logger.info(
        f"Cảnh báo {loai} của {host}: số liệu {t_so_lieu:.1f}s, AI {t_ai:.1f}s, vẽ ảnh {t_ve:.1f}s, "
        f"gửi {t_gui:.1f}s, tổng {time.time() - bat_dau:.1f}s, "
        f"Telegram {'ok' if ok_tele else 'lỗi'}, Discord {'ok' if ok_disc else 'không gửi'}, ảnh {duong_dan.name}"
    )
    return ok_tele or ok_disc
