---
![Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)
![GitLab](https://img.shields.io/badge/gitlab-%23181717.svg?style=for-the-badge&logo=gitlab&logoColor=white)
![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)

![Python](https://img.shields.io/badge/python-v3.10+-blue.svg)
![Odoo](https://img.shields.io/badge/Odoo_15-714B67?style=for-the-badge&logo=odoo&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google_Gemini_AI-4285F4?style=for-the-badge&logo=google&logoColor=white)
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)

---

<div align="center">

<img src="https://dainam.edu.vn/uploads/images/logo-DNU.png" alt="Logo Đại học Đại Nam" width="130"/>

# 🏛️ TRƯỜNG ĐẠI HỌC ĐẠI NAM
### Khoa Công nghệ Thông tin

**HỌC PHẦN:** Hội nhập và Quản trị Phần mềm Doanh nghiệp  
**MÃ LỚP:** HNQTPM-DN-17-12 &nbsp;|&nbsp; **NHÓM:** 6

</div>

---

## 📋 Giới thiệu Dự án

Hệ thống **Quản lý Phòng họp & Hội trường Thông minh** được xây dựng trên nền tảng **Odoo 15**, tích hợp trí tuệ nhân tạo **Google Gemini AI** để hỗ trợ đặt phòng qua giao diện chat ngôn ngữ tự nhiên.

### 🎯 Mục tiêu
- Số hóa toàn bộ quy trình đăng ký, phê duyệt và sử dụng phòng họp
- Tích hợp AI Chatbot (Gemini) giúp đặt phòng bằng hội thoại tự nhiên
- Cung cấp Dashboard phân tích đa chiều phục vụ ban quản lý
- Thông báo Telegram tức thời khi phê duyệt / hủy / trả phòng

---

## 🗂️ Cấu trúc Module

```
addons/
├── quan_li_phong_hop_hoi_truong/   # Module quản lý chính
│   ├── models/
│   │   ├── quan_ly_phong_hop.py    # Model phòng họp & hội trường
│   │   ├── dat_phong.py            # Model đặt phòng (toàn bộ logic nghiệp vụ)
│   │   ├── thiet_bi.py             # Model quản lý thiết bị
│   │   ├── lich_su_thay_doi.py     # Lịch sử thay đổi trạng thái
│   │   └── lich_su_muon_tra.py     # Thống kê lịch sử sử dụng phòng
│   └── views/                      # Giao diện XML (form, tree, dashboard)
│
└── hndn_ai_base/                   # Module AI Chatbot đặt phòng
    ├── models/
    │   ├── ai_assistant.py         # Logic AI: chat + trích xuất + đặt phòng
    │   └── res_config_settings.py  # Cấu hình Gemini API Key
    ├── utils/
    │   └── ai_messenger_utils.py   # Tiện ích gọi Gemini API & Telegram
    └── static/src/
        ├── js/ai_chat/             # OWL Component — giao diện chat realtime
        └── xml/ai_chat/            # Template HTML chat bong bóng
```

---

## ✨ Tính năng Nổi bật

### 🏢 Quản lý Phòng họp & Hội trường

| Tính năng | Mô tả |
|---|---|
| **Đăng ký mượn phòng** | Form đầy đủ, kiểm tra đầu vào nghiêm ngặt |
| **Chống trùng lịch** | Tự động phát hiện và từ chối khi phòng đã được đặt trong khung giờ |
| **Chống mượn quá khứ** | Không cho phép đặt phòng có thời gian đã qua |
| **Kiểm soát sức chứa** | Báo lỗi khi số người vượt sức chứa phòng đã chọn |
| **Quản lý thiết bị** | Tự động trừ/cộng số lượng thiết bị khi Check-in/Check-out |
| **AI Gợi ý phòng** | Thuật toán Best-Fit: chọn phòng nhỏ nhất vừa đủ chỗ và không trùng lịch |

### 🔄 Quy trình Phê duyệt

```
Chờ duyệt ──► Đã duyệt ──► Đang sử dụng ──► Đã trả
                  │
                  └──► Đã hủy
```

Mỗi lần chuyển trạng thái:
- Ghi nhận tự động vào **Lịch sử thay đổi**
- Gửi **thông báo Telegram** tức thời (múi giờ Việt Nam GMT+7)

### 📊 Dashboard & Báo cáo

- **Pivot View**: Phân tích đa chiều số lượt mượn theo tháng, theo phòng
- **Graph View**: Biểu đồ cột — thống kê phòng được sử dụng nhiều nhất
- **Lịch sử mượn trả**: Thống kê tổng thời gian sử dụng theo ngày và từng phòng

### 🤖 AI Chat Đặt Phòng (Google Gemini)

- Giao diện chat **OWL Component** — realtime, không cần tải lại trang
- AI tự động đọc danh sách phòng và giờ trống từ CSDL
- Trích xuất thông tin (phòng, thời gian, số người) từ hội thoại tự nhiên
- Tự động tạo đơn đặt phòng sau khi AI xác nhận đủ thông tin
- Câu hỏi gợi ý nhanh: Đặt phòng / Xem phòng / Lịch trống / Hướng dẫn

---

## 🔒 Kiểm tra Đầu vào (Validation)

| Model | Trường kiểm tra | Ràng buộc |
|---|---|---|
| `quan_ly_phong_hop` | `suc_chua` | Phải > 0 |
| `dat_phong` | `so_luong_nguoi` | Phải > 0 và ≤ sức chứa phòng đã chọn |
| `dat_phong` | `thoi_gian_muon_du_kien` | Phải ≥ thời điểm hiện tại (khi tạo mới) |
| `dat_phong` | `thoi_gian_tra_du_kien` | Phải sau `thoi_gian_muon_du_kien` |
| `dat_phong` | `phong_id + khoảng thời gian` | Không trùng với đơn đã duyệt/đang sử dụng |
| `thiet_bi` | `so_luong` | Không được < 0; = 0 thì tự chuyển trạng thái "Đang sử dụng" |
| `chi_tiet_muon_thiet_bi` | `so_luong_muon` | Phải > 0 và không vượt tồn kho thiết bị |

---

## 👥 Thành viên Nhóm 6

| STT | Họ và Tên | MSSV | Vai trò |
|---|---|---|---|
| 1 |  |  | Nhóm trưởng |
| 2 |  |  | Thành viên |
| 3 |  |  | Thành viên |
| 4 |  |  | Thành viên |
| 5 |  |  | Thành viên |

---

# 1. Cài đặt công cụ, môi trường và thư viện cần thiết

## 1.1. Clone project
```bash
git clone https://github.com/chinhliki/HNQTPM-DN-1712.git
cd HNQTPM-DN-1712
```

## 1.2. Cài đặt các thư viện hệ thống
```bash
sudo apt-get install libxml2-dev libxslt-dev libldap2-dev libsasl2-dev \
  libssl-dev python3.10-distutils python3.10-dev build-essential \
  libffi-dev zlib1g-dev python3.10-venv libpq-dev
```

## 1.3. Khởi tạo môi trường ảo Python
```bash
python3.10 -m venv ./venv
source venv/bin/activate
pip3 install -r requirements.txt
```

---

# 2. Setup Database

Khởi tạo database bằng Docker:
```bash
docker-compose up -d
```

---

# 3. Cấu hình hệ thống

## 3.1. Khởi tạo odoo.conf

Tạo tệp **`odoo.conf`** với nội dung:
```ini
[options]
addons_path = addons
db_host = localhost
db_password = odoo
db_user = odoo
db_port = 5435
xmlrpc_port = 8069
```
> Có thể copy từ `odoo.conf.template`

## 3.2. Cấu hình AI Chat — Gemini API Key

> ⚠️ **KHÔNG commit API Key lên Git!** Google sẽ tự động vô hiệu hóa key bị lộ.

1. Vào https://aistudio.google.com/apikey → Tạo API Key mới
2. Trong Odoo: **Settings → HNDN AI → Nhập Gemini API Key → Save**

## 3.3. Cấu hình Telegram Bot (Tùy chọn)

Nhận thông báo tự động khi Duyệt / Hủy / Trả phòng:

1. Tạo bot tại [@BotFather](https://t.me/BotFather) → lấy `BOT_TOKEN`
2. Lấy `CHAT_ID` của nhóm/kênh nhận thông báo
3. Cập nhật trong `addons/quan_li_phong_hop_hoi_truong/models/dat_phong.py`:
```python
BOT_TOKEN = "your_bot_token_here"
CHAT_ID   = "your_chat_id_here"
```

---

# 4. Chạy hệ thống

```bash
python3 odoo-bin.py -c odoo.conf -u all
```

Truy cập: **http://localhost:8069/**

---

## 🛠️ Công nghệ Sử dụng

| Công nghệ | Phiên bản | Mục đích |
|---|---|---|
| Odoo | 15.0 | Nền tảng ERP |
| Python | 3.10+ | Backend & business logic |
| PostgreSQL | 14+ | Cơ sở dữ liệu |
| OWL (Odoo Web Library) | 1.x | Frontend Chat Component realtime |
| Google Gemini AI | 2.0-flash | Xử lý ngôn ngữ tự nhiên |
| Telegram Bot API | — | Thông báo realtime |
| Docker | — | Containerize PostgreSQL |

---

<div align="center">

**© 2024 — Nhóm 6 | Khoa Công nghệ Thông tin — Trường Đại học Đại Nam**  
*Dự án học tập, không sử dụng cho mục đích thương mại*

</div>
