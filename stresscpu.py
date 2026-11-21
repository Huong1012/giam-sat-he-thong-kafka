import multiprocessing
import time

# Thời gian chạy test (giây)
THOI_GIAN = 60

# Mức % CPU mục tiêu bạn muốn giữ (ví dụ 93% để nằm trong khoảng 90-95%)
MUC_TIEU_PERCENT = 93


def dot_cpu(het_gio, ty_le):
    # Sử dụng kỹ thuật điều chế chu kỳ (Duty Cycle):
    # Trong mỗi 100ms: chạy tính toán bận (ty_le) và ngủ nhẹ (1 - ty_le)
    chu_ky = 0.1  # 100ms
    thoi_gian_chay = chu_ky * ty_le
    thoi_gian_nghi = chu_ky * (1.0 - ty_le)

    while time.time() < het_gio:
        bat_dau = time.time()
        # Chạy tính toán để ăn CPU
        while time.time() - bat_dau < thoi_gian_chay:
            pass
        # Nghỉ xả hơi một chút để CPU không bị chạm kịch sàn 100%
        if thoi_gian_nghi > 0:
            time.sleep(thoi_gian_nghi)


if __name__ == "__main__":
    het_gio = time.time() + THOI_GIAN
    so_tien_trinh = multiprocessing.cpu_count()
    ty_le = min(max(MUC_TIEU_PERCENT / 100.0, 0.1), 0.98)

    print(f"Đang chạy test CPU ~{MUC_TIEU_PERCENT}%, nhấn Ctrl+C để dừng")

    cac_tien_trinh = [
        multiprocessing.Process(target=dot_cpu, args=(het_gio, ty_le))
        for _ in range(so_tien_trinh)
    ]

    try:
        for t in cac_tien_trinh:
            t.start()

        for t in cac_tien_trinh:
            t.join()

        print("Đã xong")

    except KeyboardInterrupt:
        print("\nĐã dừng")
        for t in cac_tien_trinh:
            t.terminate()
