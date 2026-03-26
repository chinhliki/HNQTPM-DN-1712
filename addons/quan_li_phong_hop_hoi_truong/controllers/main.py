# -*- coding: utf-8 -*-
import json
import logging
import requests
import pytz
from datetime import datetime
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# ===== GIỮ BÍ MẬT 2 ĐOẠN MÃ TOKEN NÀY =====
try:
    import google.generativeai as genai
    HAS_GENAI = True
    GEMINI_API_KEY = "AIzaSyDmdasAZQapGTWHyTLoGBRCgzUrt2AzIp0"
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    _logger.error(f"Lỗi Không thể tải Thư viện Gemini: {str(e)}")
    HAS_GENAI = False

TELEGRAM_BOT_TOKEN = "8188180715:AAEo8OlO7jw4LHLs_mXWjpKXVjRSDwiv8MU"

class TelegramWebhook(http.Controller):

    # Chặn đứng lỗi 404 Của Odoo, tự gắp đúng Database "HNDN_Final"
    @http.route('/telegram/webhook', type='http', auth='none', methods=['POST', 'GET'], csrf=False)
    def process_webhook(self, **kw):
        db_name = kw.get('db', 'HNDN_Final')
        
        try:
            from odoo import registry, SUPERUSER_ID, api
            db_registry = registry(db_name)
            with db_registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                
                # Bóc tách tin nhắn Telegram
                raw_data = request.httprequest.data.decode('utf-8')
                if not raw_data:
                    return request.make_response("OK", status=200)
                    
                update = json.loads(raw_data)
                
                if not update or "message" not in update or "text" not in update["message"]:
                    return request.make_response("OK", status=200)

                chat_id = update["message"]["chat"]["id"]
                user_text = update["message"]["text"]
                username = update["message"]["chat"].get("username", "")

                try:
                    # Nạp Lịch Sử Hội Thoại Session
                    session = env['bot_telegram_session'].search([('chat_id', '=', str(chat_id))], limit=1)
                    
                    if not session:
                        session = env['bot_telegram_session'].create({
                            'chat_id': str(chat_id),
                            'username': username,
                            'chat_history': json.dumps([]),
                            'collected_data': json.dumps({})
                        })

                    if user_text.strip().lower() == '/reset':
                        session.unlink()
                        self._send_telegram(chat_id, "🔄 Đã reset cuộc hội thoại hoàn toàn mới.")
                        return request.make_response("OK", status=200)

                    if not HAS_GENAI:
                        self._send_telegram(chat_id, "⚠️ AI chưa sẵn sàng do máy chủ văng lỗi thư viện Google AI.")
                        return request.make_response("OK", status=200)

                    self._handle_chat_with_gemini(env, session, user_text)

                except Exception as e:
                    _logger.error(f"Webhook Logic Error: {str(e)}")

        except Exception as e:
            _logger.error(f"Db/Router Crash: {str(e)}")
            return request.make_response("Bad Request", status=400)

        return request.make_response("OK", status=200)

    # Khung Xử Lý Thông Minh AI Gọi Database Nội Bộ Odoo
    def _handle_chat_with_gemini(self, env, session, user_text):
        try:
            phong_hop_sudo = env['quan_ly_phong_hop'].search([])
            rooms_info = []

            for p in phong_hop_sudo:
                tb = ", ".join([t.name for t in p.thiet_bi_ids])
                rooms_info.append(f"{p.name} ({p.suc_chua} người) - Thiết bị: {tb}")

            nhan_vien_sudo = env['nhan_vien'].search([])
            employees_info = ", ".join([nv.name for nv in nhan_vien_sudo])

            chat_history = json.loads(session.chat_history or "[]")
            collected_data = json.loads(session.collected_data or "{}")

            prompt = f"""
Nhiệm vụ: Bạn là nữ lễ tân ảo đặt phòng thông minh.
Kinh nghiệm: Thân thiện, hỏi từng dữ liệu một, nếu số lượng người phù hợp hãy mồi khách chọn 1 phòng trong list sau. 
LIST phòng: {rooms_info}
LIST tên Nhân viên nội bộ công ty (Khách phải có tên trong list): {employees_info}

Não bộ ghi nhớ hiện tại của bạn: {collected_data}
Tin nhắn khách: '{user_text}'

=== QUY TẮC MÃ HÓA (Trả về Thuần JSON, Bỏ bọc ```json) ===
{{
  "reply": "Câu trả lời trò chuyện của bạn (Đòi thông tin, Giới thiệu phòng...)",
  "json_data": {{
    "so_luong_nguoi": null,
    "nhan_vien": null,
    "ten_phong": null,
    "thoi_gian_muon": null,
    "thoi_gian_tra": null,
    "booking_confirmed": false
  }}
}}
* Mẹo: Format ngày là YYYY-MM-DD HH:MM. Nếu đủ thông tin, bạn hãy lịch sự bảo: Mọi thứ đã đủ, em chốt luôn nhé? Khi nào khách Ok/Xác nhận mới đổi booking_confirmed từ false sang true.
"""
            response = model.generate_content(prompt)
            raw_text = response.text.replace("```json", "").replace("```", "").strip()

            result = json.loads(raw_text)
            reply = result.get("reply", "OK")
            new_data = result.get("json_data", {})

            chat_history.append({"user": user_text, "bot": reply})
            session.write({
                'chat_history': json.dumps(chat_history[-8:]),
                'collected_data': json.dumps(new_data)
            })

            # Điểm chạm Giao Thức Đưa Data Chốt Phòng Cho Odoo
            if str(new_data.get('booking_confirmed')).lower() == 'true':
                self._tao_ho_so_dat_phong(env, new_data, session)
            else:
                self._send_telegram(session.chat_id, reply)

        except Exception as e:
            _logger.error(f"Lỗi Đứt Dây AI: {str(e)}")
            self._send_telegram(session.chat_id, "⚠️ AI đang bận kết nối, anh nhắn lại tin vừa rồi giúp em.")

    def _tao_ho_so_dat_phong(self, env, data, session):
        try:
            nv = env['nhan_vien'].search([('name', 'ilike', data.get('nhan_vien'))], limit=1)
            phong = env['quan_ly_phong_hop'].search([('name', 'ilike', data.get('ten_phong'))], limit=1)

            if not nv or not phong:
                self._send_telegram(session.chat_id, "❌ Thủ tục lập khống thất bại. Không tìm thấy Thông tin nhân viên hoặc Phòng khớp Data!")
                return

            vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            t_muon = vn_tz.localize(datetime.strptime(data.get('thoi_gian_muon'), '%Y-%m-%d %H:%M')).astimezone(pytz.UTC).replace(tzinfo=None)
            t_tra = vn_tz.localize(datetime.strptime(data.get('thoi_gian_tra'), '%Y-%m-%d %H:%M')).astimezone(pytz.UTC).replace(tzinfo=None)

            env['dat_phong'].create({
                'phong_id': phong.id,
                'nguoi_muon_id': nv.id,
                'so_luong_nguoi': int(data.get('so_luong_nguoi', 0)),
                'thoi_gian_muon_du_kien': t_muon,
                'thoi_gian_tra_du_kien': t_tra,
                'trang_thai': 'chờ_duyệt',
            })

            self._send_telegram(session.chat_id, f"🎉 TIN VUI: Phiếu đặt phòng '{phong.name}' đã được Bot phi thẳng vào hệ thống Odoo của Giám sát! \nvui lòng vào báo cáo để duyệt.")
            session.unlink()

        except Exception as e:
            _logger.error(f"Lỗi Lưu Đơn: {str(e)}")
            self._send_telegram(session.chat_id, "❌ Lập đơn thất bại (Có thể do bạn đã đặt lố vào khung giờ chót, trùng thời gian, hoặc sai chuẩn định dạng của máy bay). Xin gõ `/reset`!")

    def _send_telegram(self, chat_id, message):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception:
            pass