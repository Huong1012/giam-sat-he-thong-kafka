import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise SystemExit("Chưa có TELEGRAM_BOT_TOKEN trong file .env")

url = f"https://api.telegram.org/bot{TOKEN}"

thong_tin = requests.get(f"{url}/getMe", timeout=10).json()
print("getMe:", thong_tin.get("ok"), "| tên đăng nhập bot:", thong_tin.get("result", {}).get("username"))
if not thong_tin.get("ok"):
    print("Lý do:", thong_tin.get("description"))

hook = requests.get(f"{url}/getWebhookInfo", timeout=10).json().get("result", {})
print("Webhook đang gắn:", repr(hook.get("url")))

cap_nhat = requests.get(f"{url}/getUpdates", timeout=10).json()
print("Số tin nhận được:", len(cap_nhat.get("result", [])))
