"""Chạy thử toàn bộ luồng cảnh báo một lần, không cần Kafka hay ksqlDB.
Với CPU, RAM, Swap và Pin, lấy điểm cao nhất (hoặc thấp nhất với Pin) trong vài phút gần nhất
làm thời điểm cảnh báo. Ảnh gửi đi sẽ ghi rõ CHẠY THỬ.
Cách dùng: python canhbao_thu.py [RAM_CAO|CPU_CAO|SWAP_CAO|PIN_YEU|DIA_DAY_C|DIA_DAY_D|GOI_ROT|MAT_DU_LIEU]"""
import sys
import time
from datetime import datetime

from common.config import TEN_MAY
from thu_thap import lay_du_lieu
from xu_ly import xu_ly_canh_bao

loai = sys.argv[1] if len(sys.argv) > 1 else "RAM_CAO"
du_lieu = lay_du_lieu(TEN_MAY)
chuoi = {"RAM_CAO": "ram", "CPU_CAO": "cpu", "SWAP_CAO": "swap", "PIN_YEU": "pin", "GOI_ROT": "rot_tong"}.get(loai)

t_dinh, gia_tri = time.time() - 15, 0.0
if chuoi and du_lieu["chuoi"].get(chuoi):
    chon = min if loai == "PIN_YEU" else max
    t_dinh, gia_tri = chon(du_lieu["chuoi"][chuoi], key=lambda p: p[1])
    if loai == "GOI_ROT" and gia_tri <= 0:
        t_dinh, gia_tri = time.time() - 15, 12.0  # Máy bình thường không rớt gói, đặt giá trị mẫu để thử ảnh
elif loai.startswith("DIA_DAY_"):
    gia_tri = du_lieu["disk"].get(loai[-1] + ":", 0.0)
elif loai == "MAT_DU_LIEU":
    gia_tri = 45.0

thoi_gian = datetime.fromtimestamp(t_dinh).strftime("%Y-%m-%d %H:%M:%S")
print(f"Chạy thử cảnh báo {loai} lúc {thoi_gian}, giá trị {gia_tri:.1f}. Đây không phải cảnh báo thật, ảnh sẽ ghi CHẠY THỬ.")
xu_ly_canh_bao(TEN_MAY, loai, round(gia_tri, 1), thoi_gian, chay_thu=True)
