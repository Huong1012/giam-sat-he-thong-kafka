"""Dựng ảnh báo cáo sự cố: biểu đồ số liệu, tiến trình tốn tài nguyên và nhận định của AI."""
import io
import textwrap
from datetime import datetime, timedelta

import matplotlib  # type: ignore

matplotlib.use("Agg")
import matplotlib.dates as mdates  # type: ignore  # noqa: E402
import matplotlib.pyplot as plt  # type: ignore  # noqa: E402
from matplotlib import font_manager  # type: ignore  # noqa: E402

from common.config import BUOC_GIAY, NGUONG_PIN, NGUONG_ROT, NGUONG_SWAP, NGUONG_VE  # noqa: E402

# Chọn phông có sẵn trong máy, ưu tiên phông hỗ trợ tiếng Việt đầy đủ
_PHONG = ["Segoe UI", "Arial", "DejaVu Sans"]
_co_san = {f.name for f in font_manager.fontManager.ttflist}
plt.rcParams["font.family"] = next((p for p in _PHONG if p in _co_san), "sans-serif")

NEN = "#111827"
O_NEN = "#1f2937"
CHU = "#e5e7eb"
CHU_MO = "#9ca3af"
LUOI = "#374151"
XANH_LA = "#34d399"
XANH_DUONG = "#60a5fa"
VANG = "#fbbf24"
DO = "#f87171"


def so(v, nd=1):
    """Số thập phân theo kiểu Việt Nam, dùng dấu phẩy."""
    return f"{v:.{nd}f}".replace(".", ",")


def _dinh_dang_truc(ax, tieu_de):
    ax.set_facecolor(O_NEN)
    ax.set_title(tieu_de, color=CHU, fontsize=11, loc="left", pad=8)
    ax.tick_params(colors=CHU_MO, labelsize=8)
    for canh in ax.spines.values():
        canh.set_color(LUOI)
    ax.grid(color=LUOI, linewidth=0.6, alpha=0.7)


def _khong_co_du_lieu(ax):
    ax.text(0.5, 0.5, "Không có dữ liệu", color=CHU_MO, ha="center", va="center", transform=ax.transAxes)
    ax.set_xticks([])
    ax.set_yticks([])


def _ve_chuoi(ax, tieu_de, cac_duong, t_canh_bao, khoang, nguong=None, gioi_han_tren=None, duoi=False, hep=False, don_vi_nguong="%"):
    """Vẽ một hoặc nhiều đường theo giờ thật. Có ngưỡng thì tô đỏ đoạn vượt ngưỡng."""
    _dinh_dang_truc(ax, tieu_de)
    co_ve = False
    da_co_nhan_vuot = False
    for chuoi, nhan, mau in cac_duong:
        if not chuoi:
            continue
        co_ve = True
        x = [datetime.fromtimestamp(t) for t, _ in chuoi]
        y = [v for _, v in chuoi]
        ax.plot(x, y, color=mau, linewidth=1.8, label=nhan if len(cac_duong) > 1 else "_nolegend_")
        if nguong:
            ax.fill_between(x, nguong, y, where=[(v <= nguong) if duoi else (v >= nguong) for v in y], color=DO, alpha=0.55,
                            interpolate=True,
                            label=("_nolegend_" if da_co_nhan_vuot else ("Dưới ngưỡng" if duoi else "Vượt ngưỡng")))
            da_co_nhan_vuot = True
    if not co_ve:
        _khong_co_du_lieu(ax)
        return
    ax.set_xlim(datetime.fromtimestamp(khoang[0]), datetime.fromtimestamp(khoang[1]))
    ax.set_ylim(bottom=0, top=gioi_han_tren)
    if gioi_han_tren is None and all(v <= 0 for chuoi, _, _ in cac_duong for _, v in chuoi):
        ax.set_ylim(0, 1)
    if nguong:
        ax.axhline(nguong, color=DO, linestyle="--", linewidth=1, label=f"Ngưỡng {nguong:.0f}{don_vi_nguong}")
    ax.axvline(datetime.fromtimestamp(t_canh_bao), color=CHU, linestyle=":", linewidth=1.3, label="Lúc cảnh báo")
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=4, minticks=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    ax.legend(facecolor=O_NEN, edgecolor=LUOI, labelcolor=CHU, fontsize=7 if hep else 8,
              loc="upper center", bbox_to_anchor=(0.5, -0.17),
              ncol=2 if hep else ((3 if len(cac_duong) > 1 else 2) if nguong else 3))


def _ve_o_dia(ax, ten, da_dung, con_trong, t_canh_bao, khoang, tieu_de=None):
    """Một ổ đĩa: vùng xếp chồng đã dùng và còn trống bằng GB, đường ngưỡng 90% của ổ đó."""
    if not da_dung or not con_trong:
        _dinh_dang_truc(ax, f"{tieu_de} (GB)" if tieu_de else f"Ổ {ten.rstrip(':')} (GB)")
        _khong_co_du_lieu(ax)
        return
    n = min(len(da_dung), len(con_trong))
    x = [datetime.fromtimestamp(t) for t, _ in da_dung[-n:]]
    dung = [v for _, v in da_dung[-n:]]
    trong = [v for _, v in con_trong[-n:]]
    if n < 2:
        # Mới có một điểm thì vùng tô không hiện, kéo dài thêm một bước để vẫn thấy
        x.append(x[0] + timedelta(seconds=BUOC_GIAY))
        dung.append(dung[0])
        trong.append(trong[0])
    tong = max(d + t for d, t in zip(dung, trong))
    nguong_gb = tong * NGUONG_VE / 100
    _dinh_dang_truc(ax, f"{tieu_de}: tổng {so(tong, 1 if tong < 100 else 0)} GB" if tieu_de else f"Ổ {ten.rstrip(':')}: tổng {so(tong, 0)} GB")
    ax.stackplot(x, dung, trong, colors=[VANG, XANH_LA], alpha=0.75, labels=["Đang dùng", "Còn trống"])
    ax.fill_between(x, nguong_gb, dung, where=[v >= nguong_gb for v in dung], color=DO, alpha=0.8,
                    interpolate=True, label="Vượt ngưỡng")
    ax.axhline(nguong_gb, color=DO, linestyle="--", linewidth=1, label=f"Ngưỡng {NGUONG_VE:.0f}%")
    ax.axvline(datetime.fromtimestamp(t_canh_bao), color=CHU, linestyle=":", linewidth=1.3, label="Lúc cảnh báo")
    ax.set_xlim(datetime.fromtimestamp(khoang[0]), datetime.fromtimestamp(khoang[1]))
    ax.set_ylim(0, tong)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=4, minticks=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    ax.legend(facecolor=O_NEN, edgecolor=LUOI, labelcolor=CHU, fontsize=7.5, loc="upper center",
              bbox_to_anchor=(0.5, -0.17), ncol=3)


def _ve_thanh(ax, tieu_de, muc, don_vi, toi_da=None, nguong=None):
    _dinh_dang_truc(ax, tieu_de)
    if not muc:
        _khong_co_du_lieu(ax)
        return
    ten = [(m[0][:16] + "…") if len(m[0]) > 17 else m[0] for m in muc][::-1]
    gia_tri = [m[1] for m in muc][::-1]
    mau = [DO if (nguong and v >= nguong) else XANH_DUONG for v in gia_tri]
    # Dùng vị trí số thay cho tên, vì nhiều tiến trình có thể trùng tên
    vi_tri = list(range(len(ten)))
    ax.barh(vi_tri, gia_tri, color=mau, height=0.6)
    ax.set_yticks(vi_tri)
    ax.set_yticklabels(ten)
    ax.set_xlim(0, toi_da if toi_da else (max(gia_tri) * 1.3 or 1))
    for i, v in enumerate(gia_tri):
        ax.text(v, i, f" {so(v, 0 if don_vi == ' MB' else 1)}{don_vi}", va="center", color=CHU, fontsize=8)
    if nguong:
        ax.axvline(nguong, color=DO, linestyle="--", linewidth=1)
    ax.grid(axis="y", visible=False)


def ve(canh_bao, du_lieu, nhan_dinh, nguon_nhan_dinh):
    """Trả về nội dung ảnh PNG dạng bytes."""
    t_cb = du_lieu["t_canh_bao"]
    khoang = (du_lieu["bat_dau"], du_lieu["ket_thuc"])

    fig = plt.figure(figsize=(9.2, 15.8), dpi=140, facecolor=NEN)
    luoi = fig.add_gridspec(
        7, 6, height_ratios=[0.7, 2.0, 2.0, 2.0, 1.7, 2.0, 3.1], hspace=1.0, wspace=1.4,
        left=0.12, right=0.97, top=0.97, bottom=0.03,
    )

    # Dải tiêu đề
    ax = fig.add_subplot(luoi[0, :])
    ax.axis("off")
    tieu_de = f"CẢNH BÁO: {canh_bao['ten_loai']}"
    if canh_bao.get("chay_thu"):
        tieu_de += "  (CHẠY THỬ)"
    ax.text(0, 0.78, tieu_de, color=VANG if canh_bao.get("chay_thu") else DO, fontsize=20, fontweight="bold", va="center")
    gia_tri = canh_bao["gia_tri"]
    gia_tri_hien_thi = so(gia_tri) if isinstance(gia_tri, (int, float)) else gia_tri
    gia_tri_hien_thi = canh_bao.get("gia_tri_chu") or f"{gia_tri_hien_thi}{canh_bao.get('don_vi', '%')}"
    ax.text(0, 0.18,
            f"Máy {canh_bao['host']}   |   Giá trị {gia_tri_hien_thi}   |   Lúc {canh_bao['thoi_gian']}",
            color=CHU, fontsize=10.5, va="center")

    c = du_lieu["chuoi"]
    # Hàng 1: CPU và RAM, mỗi chỉ số một biểu đồ riêng
    _ve_chuoi(fig.add_subplot(luoi[1, 0:3]), "CPU (%)", [(c.get("cpu"), "CPU", XANH_DUONG)],
              t_cb, khoang, nguong=NGUONG_VE, gioi_han_tren=100)
    if c.get("ram_dung_gb") and c.get("ram_trong_gb"):
        _ve_o_dia(fig.add_subplot(luoi[1, 3:6]), "RAM", c["ram_dung_gb"], c["ram_trong_gb"], t_cb, khoang,
                  tieu_de="RAM")
    else:
        _ve_chuoi(fig.add_subplot(luoi[1, 3:6]), "RAM (%)", [(c.get("ram"), "RAM", VANG)],
                  t_cb, khoang, nguong=NGUONG_VE, gioi_han_tren=100)
    # Hàng 2: đĩa và mạng
    _ve_chuoi(fig.add_subplot(luoi[2, 0:3]), "Đọc và ghi ổ đĩa (KB/s)",
              [(c.get("doc"), "Đọc", XANH_LA), (c.get("ghi"), "Ghi", VANG)], t_cb, khoang)
    _ve_chuoi(fig.add_subplot(luoi[2, 3:6]), "Tốc độ mạng (KB/s)",
              [(c.get("gui"), "Gửi", XANH_LA), (c.get("nhan"), "Nhận", XANH_DUONG)], t_cb, khoang)
    # Hàng 3: mỗi ổ đĩa một biểu đồ riêng, tính bằng GB
    gb = du_lieu["disk_gb"]
    cac_o = [o for o in sorted(set(gb["da_dung"]) & set(gb["con_trong"]))
             if gb["da_dung"][o] and gb["da_dung"][o][-1][1] + gb["con_trong"][o][-1][1] > 0][:3]
    if cac_o:
        rong = 6 // len(cac_o)
        for k, o in enumerate(cac_o):
            _ve_o_dia(fig.add_subplot(luoi[3, k * rong:(k + 1) * rong]), o,
                      gb["da_dung"][o], gb["con_trong"][o], t_cb, khoang)
    else:
        ax = fig.add_subplot(luoi[3, :])
        _dinh_dang_truc(ax, "Ổ đĩa (GB)")
        _khong_co_du_lieu(ax)
    # Hàng 4: gói rớt, swap và pin (pin chỉ có trên máy xách tay)
    co_pin = bool(c.get("pin"))
    cot = [(0, 2), (2, 4), (4, 6)] if co_pin else [(0, 3), (3, 6)]
    if canh_bao.get("loai") == "GOI_ROT":
        _ve_chuoi(fig.add_subplot(luoi[4, cot[0][0]:cot[0][1]]), "Gói rớt/giây (mô phỏng)" if canh_bao.get("mo_phong") else "Gói rớt mỗi giây (tổng vào và ra)",
                  [(c.get("rot_tong"), "Tổng", DO)], t_cb, khoang, nguong=NGUONG_ROT, hep=co_pin,
                  don_vi_nguong=" gói")
    else:
        _ve_chuoi(fig.add_subplot(luoi[4, cot[0][0]:cot[0][1]]), "Gói rớt mỗi giây",
                  [(c.get("rot_vao"), "Rớt vào", XANH_DUONG), (c.get("rot_ra"), "Rớt ra", VANG)],
                  t_cb, khoang, hep=co_pin)
    _ve_chuoi(fig.add_subplot(luoi[4, cot[1][0]:cot[1][1]]), "Swap (%)", [(c.get("swap"), "Swap", XANH_LA)],
              t_cb, khoang, nguong=NGUONG_SWAP, gioi_han_tren=100, hep=co_pin)
    if co_pin:
        _ve_chuoi(fig.add_subplot(luoi[4, cot[2][0]:cot[2][1]]), "Pin (%)", [(c.get("pin"), "Pin", VANG)],
                  t_cb, khoang, nguong=NGUONG_PIN, gioi_han_tren=100, duoi=True, hep=True)
    # Hàng 5: tiến trình tốn tài nguyên, lấy đúng thời điểm cảnh báo
    _ve_thanh(fig.add_subplot(luoi[5, 0:3]), "Top CPU (%)", du_lieu["top_cpu"], "%")
    _ve_thanh(fig.add_subplot(luoi[5, 3:6]), "Top RAM (MB)", du_lieu["top_ram"], " MB")

    # Khung nhận định
    ax = fig.add_subplot(luoi[6, :])
    ax.set_facecolor(O_NEN)
    ax.set_xticks([])
    ax.set_yticks([])
    for canh in ax.spines.values():
        canh.set_color(LUOI)
    ax.text(0.015, 0.93, f"Nhận định của AI ({nguon_nhan_dinh})", color=XANH_LA, fontsize=12,
            fontweight="bold", va="top", transform=ax.transAxes)
    dong = []
    for doan in nhan_dinh.splitlines():
        if doan.strip():
            dong += textwrap.wrap(doan.strip(), width=92, subsequent_indent="    ") or [""]
    ax.text(0.015, 0.80, "\n".join(dong[:12]), color=CHU, fontsize=10.5, va="top",
            linespacing=1.55, transform=ax.transAxes)
    ax.text(0.985, 0.04, f"Tạo lúc {datetime.now():%Y-%m-%d %H:%M:%S}", color=CHU_MO, fontsize=8,
            ha="right", transform=ax.transAxes)

    bo_nho = io.BytesIO()
    fig.savefig(bo_nho, format="png", facecolor=NEN)
    plt.close(fig)
    return bo_nho.getvalue()
