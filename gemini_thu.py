import os

import requests
from dotenv import load_dotenv

load_dotenv()
KHOA = os.getenv("GEMINI_API_KEY")
if not KHOA:
    raise SystemExit("Chưa có GEMINI_API_KEY trong file .env")

GOC = "https://generativelanguage.googleapis.com/v1beta"
TIEU_DE = {"x-goog-api-key": KHOA}

# 1. Hỏi Google xem khóa này dùng được những mô hình nào
kq = requests.get(f"{GOC}/models", headers=TIEU_DE, params={"pageSize": 200}, timeout=15)
if kq.status_code != 200:
    raise SystemExit(f"Khóa không hợp lệ hoặc bị từ chối, mã {kq.status_code}")

ten_mo_hinh = [
    m["name"].split("/", 1)[1]
    for m in kq.json().get("models", [])
    if "generateContent" in m.get("supportedGenerationMethods", [])
    and "flash" in m["name"]
    and not any(t in m["name"] for t in ("image", "tts", "live", "audio", "embedding", "thinking"))
]
print("Các mô hình flash dùng được:")
for ten in ten_mo_hinh:
    print(" -", ten)

# 2. Thử gọi lần lượt cho tới khi có mô hình trả lời được
for ten in ten_mo_hinh:
    phan_hoi = requests.post(
        f"{GOC}/models/{ten}:generateContent",
        headers=TIEU_DE,
        json={"contents": [{"parts": [{"text": "Trả lời đúng một câu ngắn bằng tiếng Việt: xin chào."}]}]},
        timeout=30,
    )
    if phan_hoi.status_code == 200:
        van_ban = phan_hoi.json()["candidates"][0]["content"]["parts"][0]["text"]
        print(f"\nMô hình {ten} hoạt động. Câu trả lời: {van_ban.strip()}")
        break
    print(f"{ten}: lỗi {phan_hoi.status_code}")
else:
    print("Chưa có mô hình nào gọi được.")
