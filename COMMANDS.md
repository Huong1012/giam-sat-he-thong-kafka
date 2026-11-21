# 📌 TỔNG HỢP CÁC LỆNH HAY DÙNG (CHEAT SHEET)

File này tổng hợp sẵn toàn bộ câu lệnh thường dùng theo từng bước để bạn tiện **click copy** khi thao tác và báo cáo.

---

## 1. 🐍 Kích Hoạt Môi Trường Ảo (Virtual Environment)

* **Kích hoạt trên PowerShell (đầu dòng hiện `(myenv)`):**
```powershell
.\myenv\Scripts\Activate
```

* **Nếu PowerShell bị lỗi chữ đỏ không cho chạy script (chỉ cần chạy 1 lần):**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

* **Kích hoạt trên Command Prompt (CMD):**
```cmd
myenv\Scripts\activate.bat
```

* **Thoát môi trường ảo:**
```powershell
deactivate
```

---

## 2. 🐳 Quản Lý Hạ Tầng Docker (Kafka, Prometheus, Grafana, ksqlDB)

* **Khởi động toàn bộ dịch vụ (chạy ngầm):**
```powershell
docker compose up -d
```

* **Kiểm tra trạng thái các container:**
```powershell
docker compose ps
```

* **Xem log khi cần gỡ lỗi (Ctrl+C để thoát log):**
```powershell
docker compose logs -f kafka
docker compose logs -f ksqldb-server
docker compose logs -f prometheus
```

* **Dừng toàn bộ dịch vụ:**
```powershell
docker compose down
```

* **Dừng và xóa sạch toàn bộ dữ liệu volume (reset về trắng tinh):**
```powershell
docker compose down -v
```

---

## 3. ⚙️ Cấu Hình ksqlDB CLI (Tạo Luồng Cảnh Báo)

* **Truy cập vào ksqlDB CLI:**
```powershell
docker exec -it ksqldb-cli ksql http://ksqldb-server:8088
```

* **Dán trọn bộ câu lệnh tạo Stream bên dưới (khi đang ở trong ksqlDB):**
```sql
CREATE STREAM IF NOT EXISTS system_metrics_stream (
    host VARCHAR,
    thoi_gian VARCHAR,
    cpu DOUBLE,
    ram DOUBLE
) WITH (
    KAFKA_TOPIC = 'system-metrics',
    VALUE_FORMAT = 'JSON'
);

CREATE STREAM IF NOT EXISTS canh_bao_cpu WITH (KAFKA_TOPIC='canh-bao', VALUE_FORMAT='JSON') AS
SELECT
    host AS HOST,
    'CPU_CAO' AS LOAI,
    cpu AS GIA_TRI,
    thoi_gian AS THOI_GIAN
FROM system_metrics_stream
WHERE cpu > 90.0
EMIT CHANGES;

CREATE STREAM IF NOT EXISTS canh_bao_ram WITH (KAFKA_TOPIC='canh-bao', VALUE_FORMAT='JSON') AS
SELECT
    host AS HOST,
    'RAM_CAO' AS LOAI,
    ram AS GIA_TRI,
    thoi_gian AS THOI_GIAN
FROM system_metrics_stream
WHERE ram > 90.0
EMIT CHANGES;
```

* **Kiểm tra các Stream đã tạo:**
```sql
SHOW STREAMS;
```

* **Thoát khỏi ksqlDB CLI về PowerShell:**
```sql
exit
```

---

## 4. 🚀 Chạy Các Tiến Trình Python

*(Mỗi lệnh chạy trên một cửa sổ Terminal riêng)*

* **Tab 1: Chạy Consumer (Prometheus Metrics Exporter cổng 8000):**
```powershell
python consumer.py
```
*(Hoặc không cần kích hoạt venv)*:
```powershell
.\myenv\Scripts\python.exe consumer.py
```

* **Tab 2: Chạy Dịch vụ Cảnh Báo Discord:**
```powershell
python canhbao.py
```
*(Hoặc)*:
```powershell
.\myenv\Scripts\python.exe canhbao.py
```

* **Tab 3: Chạy Producer (Thu thập và gửi metrics vào Kafka):**
```powershell
python producer.py
```
*(Hoặc)*:
```powershell
.\myenv\Scripts\python.exe producer.py
```

---

## 5. 🔥 Chạy Demo Cảnh Báo (Stress Test)

* **Test cảnh báo CPU (Duy trì ~93% CPU trong 60 giây, nhấn Ctrl+C để dừng):**
```powershell
python stresscpu.py
```
*(Hoặc)*:
```powershell
.\myenv\Scripts\python.exe stresscpu.py
```

* **Test cảnh báo RAM (Đẩy RAM > 92% trong 60 giây, tự ngắt an toàn nếu RAM trống < 400MB):**
```powershell
python stressram.py
```
*(Hoặc)*:
```powershell
.\myenv\Scripts\python.exe stressram.py
```

---

## 6. 🌐 Các Đường Dẫn Web Demo Cho Giảng Viên Xem

| Giao diện | Địa chỉ URL | Mô tả / Tài khoản |
| :--- | :--- | :--- |
| **Grafana Dashboard** | `http://localhost:3000` | Tài khoản: `admin` / Mật khẩu: `admin` |
| **Prometheus UI** | `http://localhost:9090` | Xem target: `http://localhost:9090/targets` |
| **Metrics thô** | `http://localhost:8000/metrics` | Endpoint trực tiếp do `consumer.py` mở |
| **ksqlDB Server** | `http://localhost:8088/info` | Kiểm tra trạng thái ksqlDB |

---

## 7. 🔍 Lệnh Kiểm Tra Kafka Nhanh (Debug / Troubleshooting)

* **Xem danh sách các Topic trong Kafka:**
```powershell
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --list
```

* **Xem tin nhắn đang đổ vào topic `system-metrics`:**
```powershell
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic system-metrics --from-beginning --max-messages 5
```

* **Xem tin nhắn đang đổ vào topic `canh-bao`:**
```powershell
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic canh-bao --from-beginning
```
