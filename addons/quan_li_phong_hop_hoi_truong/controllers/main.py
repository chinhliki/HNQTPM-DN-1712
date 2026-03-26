# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
from datetime import datetime
import pytz
import logging
import requests

_logger = logging.getLogger(__name__)

class TelegramWebhook(http.Controller):
    
    def send_reply(self, text, chat_id):
        BOT_TOKEN = "8188180715:AAEo8OlO7jw4LHLs_mXWjpKXVjRSDwiv8MU"
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            _logger.error("Error sending Telegram reply: %s", str(e))

    @http.route('/telegram/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def telegram_webhook(self, **kwargs):
        # Odoo tự động chuyển body POST sang jsonrequest khi type='json'
        data = request.jsonrequest
        if data and "message" in data and "text" in data["message"]:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"]["text"].strip()
            
            if text.startswith("/datphong"):
                self._handle_dat_phong(text, chat_id)
            elif text.startswith("/start"):
                self.send_reply("👋 Xin chào! Hãy dùng lệnh sau để AI tự động dò tìm và đặt lịch phòng họp:\n\n👉 Lệnh mẫu: `/datphong Tên_Nhân_Viên Số_Đại_Biểu Ngày(DD/MM/YYYY) Giờ_BD-Giờ_KT`\n👉 Ví dụ: `/datphong Dung 5 26/03/2026 08:00-10:00`", chat_id)
            else:
                self.send_reply("🤖 Lệnh không tồn tại. Hãy gõ /start để xem bảng Hướng dẫn sử dụng.", chat_id)
                
        return {"status": "ok"}

    def _handle_dat_phong(self, text, chat_id):
        parts = text.split()
        # Expecting: /datphong [Tên...] [Số người] [DD/MM/YYYY] [HH:MM-HH:MM]
        if len(parts) >= 5:
            name_query = " ".join(parts[1:-3])
            people_str = parts[-3]
            date_str = parts[-2]
            time_str = parts[-1]
            
            # Sử dụng user root (user=1) để được quyền thao tác ngầm vào dữ liệu
            env = request.env(user=1)
            
            # Tìm kiếm nhân viên thông qua Like SQL (tên gần giống)
            nhan_vien = env['nhan_vien'].search([('name', 'ilike', name_query)], limit=1)
            if not nhan_vien:
                self.send_reply(f"❌ Bạn đã nhập tên '{name_query}', nhưng BOT không tìm thấy nhân viên nào có cụm tên cấu tự này trong danh sách hệ thống nội bộ.", chat_id)
                return
                
            try:
                people = int(people_str)
                time_range = time_str.split('-')
                if len(time_range) != 2:
                    raise ValueError()
                    
                vnt_tz = pytz.timezone('Asia/Ho_Chi_Minh')
                
                dt_start_local = datetime.strptime(f"{date_str} {time_range[0]}", "%d/%m/%Y %H:%M")
                dt_end_local = datetime.strptime(f"{date_str} {time_range[1]}", "%d/%m/%Y %H:%M")
                
                # Kịch bản Logic Error
                if dt_start_local < datetime.now():
                    self.send_reply(f"❌ Lỗi: Bạn đang hẹn đặt phòng vào một Thời điểm ({time_range[0]}) nằm trong Quá khứ so với thời khắc Gõ lệnh hiện tại.", chat_id)
                    return
                if dt_end_local <= dt_start_local:
                    self.send_reply("❌ Lỗi: Giờ trả phòng (Kết thúc) không được nhỏ hơn quy định Giờ bắt đầu Check-in.", chat_id)
                    return

                # Convert Local Vietnam to Server UTC DateTime
                time_muon_utc = vnt_tz.localize(dt_start_local).astimezone(pytz.UTC).replace(tzinfo=None)
                time_tra_utc = vnt_tz.localize(dt_end_local).astimezone(pytz.UTC).replace(tzinfo=None)
                
            except Exception as e:
                self.send_reply(f"❌ Lỗi do định dạng hoặc sai số.\n👉 Hãy chép ví dụ và thay ngày: `/datphong Dung 5 26/03/2026 08:00-10:00`", chat_id)
                return
                
            try:
                # 1. Tìm kho phòng theo bộ lọc Không Gian (Sức Chứa)
                phong_phu_hop = env['quan_ly_phong_hop'].search([('suc_chua', '>=', people)])
                
                # 2. Logic AI lọc Chồng Chéo Thời Gian
                phong_trong = []
                for phong in phong_phu_hop:
                    trung_lich = env['dat_phong'].search([
                        ('phong_id', '=', phong.id),
                        ('trang_thai', 'in', ['đã_duyệt', 'đang_sử_dụng']),
                        ('thoi_gian_muon_du_kien', '<', time_tra_utc),
                        ('thoi_gian_tra_du_kien', '>', time_muon_utc)
                    ])
                    if not trung_lich:
                        phong_trong.append(phong)
                
                if not phong_trong:
                    self.send_reply(f"❌ Đã rà soát: Toàn bộ phòng có sức chứa {people} người đều không rảnh từ {time_str} ngày {date_str}. Mong bạn thử khung giờ khác nhé!", chat_id)
                    return
                
                # 3. Thuật toán Tiết Kiệm Tài Nguyên (Fit Size)
                phong_trong.sort(key=lambda p: p.suc_chua)
                phong_chon = phong_trong[0]
                
                # 4. Lưu trực tiếp Data xuống Server
                dat_phong = env['dat_phong'].create({
                    'nguoi_muon_id': nhan_vien.id,
                    'phong_id': phong_chon.id,
                    'so_luong_nguoi': people,
                    'thoi_gian_muon_du_kien': time_muon_utc,
                    'thoi_gian_tra_du_kien': time_tra_utc,
                    'trang_thai': 'chờ_duyệt'
                })
                
                self.send_reply(f"🎉 *LỆNH ĐÃ THUYẾT LẬP THÀNH CÔNG!*\n\n"
                                f"🤖 AI đã auto-scan và cấp phát căn phòng rẻ nhất:\n"
                                f"👤 ĐỨNG TÊN MƯỢN: {nhan_vien.name}\n"
                                f"🏢 TÊN PHÒNG CHỌN: {phong_chon.name} (Size MAX: {phong_chon.suc_chua} người)\n"
                                f"🕒 GIỜ HẸN GIỮ: {time_str}\n📅 NGÀY CHỐT: {date_str}\n\n"
                                f"🔔 Lệnh hiện nằm ở Trạng thái <CHỜ DUYỆT>. Hãy nhắn Admin phê duyệt!", chat_id)
                
            except Exception as e:
                self.send_reply(f"❌ Mã lõi Odoo: {str(e)}", chat_id)
        else:
            self.send_reply("❌ Sai cú pháp hoặc thiếu thông tin biến.\n👉 Hãy sử dụng: `/datphong Dung 5 26/03/2026 08:00-10:00`", chat_id)
