import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise SystemExit("Chưa có TELEGRAM_BOT_TOKEN trong file .env")

url = f"https://api.telegram.org/bot{TOKEN}"

# Lấy các tin nhắn đã gửi cho bot
ket_qua = requests.get(f"{url}/getUpdates", timeout=10).json()
tin_nhan = ket_qua.get("result", [])

if not tin_nhan:
    raise SystemExit("Bot chưa nhận được tin nào. Hãy mở bot trong Telegram, gửi một tin rồi chạy lại.")

chat_id = tin_nhan[-1]["message"]["chat"]["id"]
print("Chat id của bạn:", chat_id)

# Gửi tin thử
phan_hoi = requests.post(
    f"{url}/sendMessage",
    data={"chat_id": chat_id, "text": "Xin chào, bot giám sát hệ thống đã hoạt động."},
    timeout=10,
)
print("Kết quả gửi:", phan_hoi.status_code)
