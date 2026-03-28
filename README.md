# 🏢 Hệ thống Quản lý Phòng họp & Trợ lý AI Đặt phòng

<div align="center">

![Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Odoo](https://img.shields.io/badge/Odoo-15.0-714B67?style=for-the-badge&logo=odoo&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram_Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)

**Nhóm HNQTPM-DN-1712 · Môn Hội nhập & Quản trị Phần mềm Doanh nghiệp**

_Kế thừa từ module gốc của Khoa CNTT - Đại học Đại Nam (TTDN-16-05) và nâng cấp toàn diện_

[📺 Xem Demo](#) · [📋 Kịch bản Video](#) · [🐛 Báo lỗi](https://github.com/chinhliki/HNQTPM-DN-1712/issues)

</div>

---

## 📌 Giới thiệu

Dự án xây dựng hệ thống **Quản lý Phòng họp & Hội trường** tích hợp trên nền tảng **Odoo 15**, bao gồm:

- ✅ Quản lý danh sách phòng họp và thiết bị đi kèm
- ✅ Luồng đặt phòng → phê duyệt → sử dụng → trả phòng hoàn chỉnh
- ✅ Kiểm soát thiết bị tự động khi Check-in / Check-out
- ✅ Thông báo Telegram realtime khi có thay đổi trạng thái
- ✅ Dashboard phân tích theo Pivot & Graph
- 🤖 **Trợ lý AI Gemini — đặt phòng qua hội thoại tự nhiên**

---

## 🆚 Điểm khác biệt so với module gốc (TTDN-16-05)

| Tính năng | Module gốc | Phiên bản nhóm HNQTPM-DN-1712 |
|-----------|-----------|-------------------------------|
| Đặt phòng cơ bản | ✅ | ✅ |
| Kiểm tra trùng lịch | ❌ | ✅ Tự động, chặn khi lưu |
| Ngăn đặt phòng quá khứ | ❌ | ✅ Validate trước khi lưu |
| Validate sức chứa | ❌ | ✅ Báo lỗi nếu vượt quá |
| Quản lý thiết bị | Cơ bản | ✅ Trừ/cộng số lượng tự động |
| Thông báo Telegram | ❌ | ✅ Realtime, đúng múi giờ VN |
| Dashboard & báo cáo | ❌ | ✅ Pivot + Graph nâng cao |
| Gợi ý phòng thông minh | ❌ | ✅ Thuật toán Best Fit |
| **Trợ lý AI Chat** | ❌ | ✅ **Gemini 2.5 Flash** |

---

## 🗂️ Cấu trúc Module

```
addons/
├── quan_li_phong_hop_hoi_truong/   # Module chính quản lý phòng họp
│   ├── models/
│   │   ├── dat_phong.py            # Logic đặt phòng, duyệt, check-in/out, Telegram
│   │   ├── quan_ly_phong_hop.py    # Model phòng & sức chứa
│   │   ├── thiet_bi.py             # Model thiết bị
│   │   └── lich_su_muon_tra.py     # Lịch sử mượn trả (caching)
│   └── views/
│       ├── dat_phong.xml           # Form đặt phòng
│       ├── dat_phong_dashboard.xml # Dashboard Pivot & Graph
│       └── ...
│
├── hndn_ai_base/                   # Module Trợ lý AI
│   ├── models/
│   │   ├── ai_assistant.py         # AI chat logic + đặt phòng tự động
│   │   └── res_config_settings.py  # Cấu hình API Key qua Settings UI
│   ├── utils/
│   │   └── ai_messenger_utils.py   # Gemini API caller (v1, retry, fallback)
│   └── static/src/
│       ├── js/ai_chat/             # OWL Component chat realtime
│       └── xml/ai_chat/            # Template giao diện Messenger
│
└── nhan_su/                        # Module nhân sự (dependency)
```

---

## ✨ Tính năng chi tiết

### 🏠 Quản lý Phòng họp

- **Danh sách phòng** với sức chứa và thiết bị kèm theo
- **Đặt phòng** với validation đầy đủ:
  - Không cho đặt trong quá khứ
  - Không cho trùng lịch với đơn đã duyệt
  - Không cho vượt quá sức chứa
- **Luồng trạng thái:** `Chờ duyệt` → `Đã duyệt` → `Đang sử dụng` → `Đã trả`
- **Gợi ý phòng AI (Best Fit):** Chọn phòng nhỏ nhất vừa đủ sức chứa, còn trống trong khung giờ

### ⚙️ Quản lý Thiết bị

- Mỗi phòng có danh sách thiết bị riêng
- Check-in → Tự động trừ số lượng thiết bị
- Check-out → Tự động hoàn trả và đặt trạng thái `Sẵn sàng`

### 🔔 Thông báo Telegram

- Tự động gửi khi: **Duyệt đơn / Hủy đơn / Trả phòng thành công**
- Đúng múi giờ Việt Nam (Asia/Ho_Chi_Minh)
- Kèm đầy đủ: tên phòng, người mượn, giờ check-in/out

### 📊 Dashboard & Báo cáo

- **Pivot View:** Phân tích đa chiều theo phòng, thời gian, người mượn
- **Graph View:** Biểu đồ cột trực quan tỷ lệ sử dụng từng phòng
- **Lịch sử mượn trả:** Bảng ghi nhận thời gian thực tế theo ngày

### 🤖 Trợ lý AI Đặt phòng (Gemini 2.5 Flash)

- **Giao diện Messenger** (OWL Component) — chat realtime, không cần reload trang
- AI **tự đọc dữ liệu** phòng từ database, biết sức chứa thực tế
- **Hội thoại tự nhiên:** Người dùng chỉ cần mô tả nhu cầu
- AI **tự động trích xuất** thông tin (phòng, giờ, số người) và điền vào đơn
- Nhấn 1 nút `Xác nhận Đặt Phòng` → Đơn được tạo ngay
- **Retry tự động** khi gặp lỗi 429 (quota), 404, timeout

---

## 🚀 Hướng dẫn cài đặt

### Yêu cầu hệ thống

- Ubuntu 20.04 / 22.04
- Python 3.10+
- PostgreSQL 13+
- Odoo 15.0

### Bước 1: Clone project

```bash
git clone https://github.com/chinhliki/HNQTPM-DN-1712.git
cd HNQTPM-DN-1712
```

### Bước 2: Tạo môi trường ảo & cài thư viện

```bash
python3.10 -m venv ./venv
source venv/bin/activate
pip install -r requirements.txt
```

Nếu gặp lỗi build, cài thêm:
```bash
sudo apt-get install libxml2-dev libxslt-dev libldap2-dev libsasl2-dev \
  libssl-dev python3.10-distutils python3.10-dev build-essential libpq-dev
```

### Bước 3: Khởi tạo Database

```bash
docker-compose up -d
```

### Bước 4: Cấu hình Odoo

Tạo file `odoo.conf`:

```ini
[options]
addons_path = addons
db_host = localhost
db_password = odoo
db_user = odoo
db_port = 5435
xmlrpc_port = 8069
```

### Bước 5: Khởi động hệ thống

```bash
python3 odoo-bin.py -c odoo.conf -u all
```

Truy cập: **http://localhost:8069**

---

## 🔑 Cấu hình sau khi cài đặt

### Cấu hình Gemini API Key

1. Vào **Settings** → Tìm mục **HNDN AI**
2. Nhập **Gemini API Key** (lấy tại [aistudio.google.com](https://aistudio.google.com))
3. Nhấn **"Kiểm tra kết nối"** để xác nhận
4. **Save**

> ℹ️ Module sử dụng **Gemini 2.5 Flash** qua endpoint `v1` chuẩn của Google.

### Cấu hình Telegram Bot (tùy chọn)

Trong file `addons/quan_li_phong_hop_hoi_truong/models/dat_phong.py`, cập nhật:

```python
BOT_TOKEN = "your_bot_token_here"
CHAT_ID = "your_chat_id_here"
```

> Tham khảo: [Tạo Telegram Bot](https://core.telegram.org/bots#how-do-i-create-a-bot)

---

## 🛠️ Stack Công nghệ

| Thành phần | Công nghệ |
|-----------|-----------|
| Backend | Python 3.10, Odoo ORM |
| Frontend | OWL (Odoo Web Library), JavaScript |
| Database | PostgreSQL 13 |
| AI Model | Google Gemini 2.5 Flash (API v1) |
| Notification | Telegram Bot API |
| OS | Ubuntu 20.04/22.04 |

---

## 👥 Nhóm phát triển

**HNQTPM-DN-1712** · Môn Hội nhập & Quản trị Phần mềm Doanh nghiệp

> Phát triển dựa trên module gốc của **Khoa CNTT - Đại học Đại Nam (TTDN-16-05-N4)**  
> Repository gốc: [TTDN-16-05-N5](https://github.com/Nemmer772004/TTDN-16-05-N5)

---

## 📄 License

Module này được phân phối theo giấy phép **LGPL-3**.  
Xem thêm: [GNU Lesser General Public License v3.0](https://www.gnu.org/licenses/lgpl-3.0.html)
