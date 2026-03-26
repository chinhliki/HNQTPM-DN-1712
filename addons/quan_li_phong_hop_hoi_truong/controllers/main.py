# -*- coding: utf-8 -*-
import json
import logging
import requests
import pytz
from datetime import datetime
from odoo import http, registry, SUPERUSER_ID, api
from odoo.http import request

_logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    HAS_GENAI = True
    GEMINI_API_KEY = "AIzaSyDmdasAZQapGTWHyTLoGBRCgzUrt2AzIp0" # Lưu ý: Nên để trong System Parameters
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    _logger.error(f"Lỗi Gemini: {str(e)}")
    HAS_GENAI = False

TELEGRAM_BOT_TOKEN = "8188180715:AAEo8OlO7jw4LHLs_mXWjpKXVjRSDwiv8MU"

class TelegramWebhook(http.Controller):

    @http.route('/telegram/webhook', type='http', auth='none', methods=['POST'], csrf=False)
    def process_webhook(self, **kw):
        # Lấy db từ URL (?db=HNDN_Final), nếu không có thì dùng mặc định
        db_name = kw.get('db', 'HNDN_Final')
        
        try:
            # Lấy dữ liệu JSON từ Telegram
            raw_data = request.httprequest.data
            if not raw_data:
                return request.make_response("No data", status=200)
            
            update = json.loads(raw_data.decode('utf-8'))
            if "message" not in update or "text" not in update["message"]:
                return request.make_response("Not a text message", status=200)

            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"]
            username = update["message"]["chat"].get("username", "")

            # Kết nối Database thủ công
            db_registry = registry(db_name)
            with db_registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                
                # Tìm hoặc tạo Session
                session = env['bot_telegram_session'].search([('chat_id', '=', str(chat_id))], limit=1)
                if not session:
                    session = env['bot_telegram_session'].create({
                        'chat_id': str(chat_id),
                        'username': username,
                    })

                if user_text.strip().lower() == '/reset':
                    session.unlink()
                    cr.commit() # Quan trọng: Phải commit để xóa thực sự
                    self._send_telegram(chat_id, "🔄 Đã reset cuộc hội thoại.")
                    return request.make_response("OK", status=200)

                if not HAS_GENAI:
                    self._send_telegram(chat_id, "⚠️ AI chưa sẵn sàng.")
                else:
                    self._handle_chat_with_gemini(env, session, user_text)
                
                # Commit mọi thay đổi (write session, tạo booking...) vào DB
                cr.commit()

        except Exception as e:
            _logger.error(f"Webhook Crash: {str(e)}")
            return request.make_response("Error", status=500)

        return request.make_response("OK", status=200)

    def _handle_chat_with_gemini(self, env, session, user_text):
        try:
            # Lấy danh sách phòng và nhân viên để làm context cho AI
            rooms = env['quan_ly_phong_hop'].search([])
            rooms_info = [f"{r.name} ({r.suc_chua} chỗ)" for r in rooms]
            
            emps = env['nhan_vien'].search([])
            employees_info = [e.name for e in ems]

            collected_data = json.loads(session.collected_data or "{}")

            prompt = f"""
Nhiệm vụ: Bạn là nữ lễ tân ảo. 
LIST phòng: {rooms_info}
LIST nhân viên: {employees_info}
Data đã biết: {collected_data}
Khách nói: '{user_text}'

Trả về JSON thuần:
{{
  "reply": "câu trả lời",
  "json_data": {{ "so_luong_nguoi": int, "nhan_vien": "tên", "ten_phong": "tên", "thoi_gian_muon": "YYYY-MM-DD HH:MM", "thoi_gian_tra": "YYYY-MM-DD HH:MM", "booking_confirmed": bool }}
}}
"""
            response = model.generate_content(prompt)
            # Làm sạch chuỗi JSON từ AI
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            result = json.loads(clean_text)
            
            reply = result.get("reply")
            new_data = result.get("json_data")

            # Cập nhật session
            session.write({
                'collected_data': json.dumps(new_data)
            })

            if new_data.get('booking_confirmed'):
                self._tao_ho_so_dat_phong(env, new_data, session)
            else:
                self._send_telegram(session.chat_id, reply)

        except Exception as e:
            _logger.error(f"AI Error: {str(e)}")
            self._send_telegram(session.chat_id, "Bé AI đang chóng mặt, bạn thử lại nhé!")

    def _tao_ho_so_dat_phong(self, env, data, session):
        # Giữ nguyên logic cũ nhưng bỏ qua các lệnh in/log thừa
        # và đảm bảo định dạng datetime đúng chuẩn Odoo (UTC)
        try:
            nv = env['nhan_vien'].search([('name', 'ilike', data.get('nhan_vien'))], limit=1)
            phong = env['quan_ly_phong_hop'].search([('name', 'ilike', data.get('ten_phong'))], limit=1)

            if nv and phong:
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
                self._send_telegram(session.chat_id, f"✅ Đã tạo đơn đặt phòng {phong.name} thành công!")
                session.unlink()
            else:
                self._send_telegram(session.chat_id, "❌ Không tìm thấy nhân viên hoặc phòng phù hợp.")
        except Exception as e:
            _logger.error(f"Booking Error: {str(e)}")
            self._send_telegram(session.chat_id, "❌ Lỗi khi lưu đơn.")

    def _send_telegram(self, chat_id, message):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=5)
        except:
            pass