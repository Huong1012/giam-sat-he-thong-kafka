import time
import psutil

# Ngưỡng RAM muốn đạt tới để kích hoạt cảnh báo (> 90%)
MUC_TIEU_PERCENT = 92.0

# Thời gian duy trì mức RAM cao (tính bằng giây)
THOI_GIAN = 60


def dot_ram():
    print("Đang chạy test RAM > 90%, nhấn Ctrl+C để dừng")
    bo_nho = []

    try:
        # Cấp phát từng khối 256MB cho đến khi RAM vượt mức mục tiêu
        while psutil.virtual_memory().percent < MUC_TIEU_PERCENT:
            # Cơ chế an toàn: Nếu RAM trống dưới 400MB thì dừng để tránh treo máy
            if psutil.virtual_memory().available < 400 * 1024 * 1024:
                break

            # Tạo khối 256MB và ghi dữ liệu để ép OS cấp phát RAM thực tế
            khoi = bytearray(256 * 1024 * 1024)
            for i in range(0, len(khoi), 4096):
                khoi[i] = 1
            bo_nho.append(khoi)
            time.sleep(0.2)

        # Giữ RAM trong thời gian quy định
        time.sleep(THOI_GIAN)
        print("Đã xong")

    except KeyboardInterrupt:
        print("\nĐã dừng")
    finally:
        bo_nho.clear()


if __name__ == "__main__":
    dot_ram()
