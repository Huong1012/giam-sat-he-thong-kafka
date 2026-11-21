"""Gửi số liệu quanh thời điểm cảnh báo cho Gemini và nhận về phần nhận định ngắn."""
import os
import time

import requests  # type: ignore

from common.config import CAC_MO_HINH_AI, CUA_SO_GIAY, SAU_CANH_BAO, THOI_GIAN_CHO_AI
from common.logger import configure_logger
from thu_thap import thong_ke

logger = configure_logger("ai_tom_tat")

GOC = "https://generativelanguage.googleapis.com/v1beta"
NHAN_CHUOI = {
    "cpu": "CPU tổng (%)",
    "ram": "RAM (%)",
    "swap": "Swap (%)",
    "doc": "Đọc đĩa (KB/s)",
    "ghi": "Ghi đĩa (KB/s)",
    "gui": "Mạng gửi (KB/s)",
    "nhan": "Mạng nhận (KB/s)",
    "pin": "Pin (%)",
    "rot_vao": "Gói rớt vào (gói/giây)",
    "rot_ra": "Gói rớt ra (gói/giây)",
}

NGU_CANH = {
    "MAT_DU_LIEU": "Máy ngừng gửi số liệu, không có số liệu mới. Nguyên nhân có thể nằm ở chương trình thu thập, Kafka hoặc đường truyền; số liệu bên dưới chỉ là đoạn trước khi mất.",
    "PIN_YEU": "Pin yếu và máy không cắm sạc, có nguy cơ tắt máy.",
    "DIA_DAY_C": "Ổ đĩa C gần đầy, giá trị là phần trăm dung lượng đã dùng.",
    "DIA_DAY_D": "Ổ đĩa D gần đầy, giá trị là phần trăm dung lượng đã dùng.",
    "GOI_ROT": "Card mạng đang rớt gói, giá trị là tổng số gói rớt mỗi giây cả hai chiều. Nguyên nhân thường là đường truyền hoặc Wi-Fi yếu, driver mạng, hoặc card mạng quá tải.",
    "SWAP_CAO": "Vùng nhớ tráo đổi dùng nhiều, thường do RAM thật không đủ.",
}


def tao_noi_dung(canh_bao, du_lieu):
    dong = [
        "Bạn là kỹ sư vận hành hệ thống. Dưới đây là cảnh báo và số liệu của máy trong vài phút gần nhất.",
        f"Cảnh báo: {canh_bao['ten_loai']}, giá trị {canh_bao['gia_tri']}{canh_bao['don_vi']}, máy {canh_bao['host']}, lúc {canh_bao['thoi_gian']}.",
        "",
        f"Số liệu bắt đầu từ {CUA_SO_GIAY // 60} phút trước cảnh báo và kết thúc khoảng {SAU_CANH_BAO} giây sau cảnh báo, "
        "nên giá trị cuối cùng có thể đã hạ so với lúc cảnh báo. Hãy nhận định theo thời điểm cảnh báo.",
        "Số liệu theo từng chỉ số (giá trị cuối, nhỏ nhất, lớn nhất, trung bình, vài mẫu theo thời gian):",
    ]
    for khoa, nhan in NHAN_CHUOI.items():
        tk = thong_ke(du_lieu["chuoi"].get(khoa, []))
        if tk:
            dong.append(
                f"- {nhan}: cuối {tk['hien_tai']}, nhỏ nhất {tk['nho_nhat']}, "
                f"lớn nhất {tk['lon_nhat']}, trung bình {tk['trung_binh']}, mẫu {tk['cac_mau']}"
            )
    if du_lieu["disk"]:
        dong.append("- Dung lượng ổ đĩa đã dùng (%): " + ", ".join(f"{o} {v:.1f}" for o, v in du_lieu["disk"].items()))
    for ten_o, chuoi_dung in sorted(du_lieu["disk_gb"]["da_dung"].items()):
        chuoi_trong = du_lieu["disk_gb"]["con_trong"].get(ten_o)
        if chuoi_dung and chuoi_trong:
            dong.append(f"- Ổ {ten_o} (GB): đã dùng {chuoi_dung[-1][1]:.1f}, còn trống {chuoi_trong[-1][1]:.1f}")
    if du_lieu["top_cpu"]:
        dong.append("- Tiến trình tốn CPU nhất (%): " + ", ".join(f"{t} {v:.1f}" for t, v in du_lieu["top_cpu"]))
    if du_lieu["top_ram"]:
        dong.append("- Tiến trình tốn RAM nhất (MB): " + ", ".join(f"{t} {v:.0f}" for t, v in du_lieu["top_ram"]))
    dong += [
        "",
        "Hãy trả lời bằng tiếng Việt, đúng ba dòng, không dùng định dạng markdown, mỗi dòng không quá 30 từ:",
        "Nhận định: tình trạng hiện tại và mức độ nghiêm trọng.",
        "Nguyên nhân có thể: dựa vào số liệu trên, nêu tên tiến trình nếu có liên quan.",
        "Đề xuất: một việc cụ thể nên làm ngay.",
        "Chỉ dùng số liệu đã cho, không bịa thêm.",
    ]
    return "\n".join(dong)


def tom_tat(canh_bao, du_lieu):
    """Trả về văn bản nhận định, hoặc None nếu mọi mô hình đều không trả lời được."""
    khoa = os.getenv("GEMINI_API_KEY")
    if not khoa:
        logger.error("Thiếu GEMINI_API_KEY trong tệp .env")
        return None

    thong_diep = {
        "contents": [{"parts": [{"text": tao_noi_dung(canh_bao, du_lieu)}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024},
    }
    for mo_hinh in CAC_MO_HINH_AI:
        for lan in range(2):
            try:
                kq = requests.post(
                    f"{GOC}/models/{mo_hinh}:generateContent",
                    headers={"x-goog-api-key": khoa},
                    json=thong_diep,
                    timeout=THOI_GIAN_CHO_AI,
                )
            except requests.RequestException as loi:
                logger.error(f"{mo_hinh}: không kết nối được, {type(loi).__name__}")
                break
            if kq.status_code == 200:
                try:
                    cac_phan = kq.json()["candidates"][0]["content"]["parts"]
                    van_ban = "".join(p.get("text", "") for p in cac_phan).strip()
                except (KeyError, IndexError, ValueError):
                    van_ban = ""
                if van_ban:
                    logger.info(f"AI trả lời bằng mô hình {mo_hinh}")
                    return van_ban
                logger.error(f"{mo_hinh}: phản hồi rỗng")
                break
            logger.error(f"{mo_hinh}: lỗi {kq.status_code}")
            if kq.status_code in (429, 500, 503) and lan == 0:
                time.sleep(2)
                continue
            break
    return None
