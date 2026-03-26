# -*- coding: utf-8 -*-
import json
import logging
import requests
import pytz
from datetime import datetime
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# ===== Gemini Config =====
try:
    import google.generativeai as genai
    HAS_GENAI = True
    GEMINI_API_KEY = "AIzaSyDmdasAZQapGTWHyTLoGBRCgzUrt2AzIp0"
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    _logger.error(f"Failed to load genai: {str(e)}")
    HAS_GENAI = False

TELEGRAM_BOT_TOKEN = "8188180715:AAEo8OlO7jw4LHLs_mXWjpKXVjRSDwiv8MU"

class TelegramWebhook(http.Controller):

<<<<<<< HEAD
    @http.route('/telegram/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def process_webhook(self, **kw):
        try:
            # ✅ FIX 1: decode utf-8
            raw_data = request.httprequest.data.decode('utf-8')
            _logger.info(f"RAW TELEGRAM: {raw_data}")

            update = json.loads(raw_data)

        except Exception as e:
            _logger.error(f"Parse error: {str(e)}")
            return request.make_response("Bad Request", status=400)

        # ✅ FIX 2: tránh crash khi request rỗng
        if not update or "message" not in update:
            return request.make_response("OK", status=200)

        try:
            if "text" not in update["message"]:
                return request.make_response("OK", status=200)

            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"]
            username = update["message"]["chat"].get("username", "")

            session_sudo = request.env['bot_telegram_session'].sudo()
            session = session_sudo.search([('chat_id', '=', str(chat_id))], limit=1)

            if not session:
                session = session_sudo.create({
                    'chat_id': str(chat_id),
                    'username': username,
                    'chat_history': json.dumps([]),
                    'collected_data': json.dumps({})
                })

            # Reset
            if user_text.strip().lower() == '/reset':
                session.unlink()
                self._send_telegram(chat_id, "🔄 Đã reset cuộc hội thoại.")
                return request.make_response("OK", status=200)

            # Nếu chưa có Gemini
            if not HAS_GENAI:
                self._send_telegram(chat_id, "⚠️ AI chưa sẵn sàng.")
                return request.make_response("OK", status=200)

            # Xử lý chat
            self._handle_chat_with_gemini(session, user_text)

        except Exception as e:
            _logger.error(f"Webhook crash: {str(e)}")

        return request.make_response("OK", status=200)

    # ================================
    def _handle_chat_with_gemini(self, session, user_text):
        try:
            phong_hop_sudo = request.env['quan_ly_phong_hop'].sudo().search([])
=======
    # Đổi auth='none' để vượt qua khiên chắn bảo vệ tự động của Odoo,
    # Ép Odoo tự động tìm đến đúng Database thay vì báo lỗi 404 Nodb.
    @http.route('/telegram/webhook', type='http', auth='none', methods=['POST', 'GET'], csrf=False)
    def process_webhook(self, **kw):
        db_name = kw.get('db', 'HNDN_Final') # Trích xuất tên DB từ link Ngrok
        
        try:
            # 1. Kích hoạt Kết nối cưỡng bức tới Database
            from odoo import registry, SUPERUSER_ID, api
            db_registry = registry(db_name)
            with db_registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                
                # 2. Bóc tách cục JSON của Telegram
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
                    # 3. Quản lý Session bằng Môi trường (env) vừa lấy được
                    session = env['bot_telegram_session'].search([('chat_id', '=', str(chat_id))], limit=1)
                    
                    if not session:
                        session = env['bot_telegram_session'].create({
                            'chat_id': str(chat_id),
                            'username': username,
                            'chat_history': json.dumps([]),
                            'collected_data': json.dumps({})
                        })

                    # Cú pháp Reset
                    if user_text.strip().lower() == '/reset':
                        session.unlink()
                        self._send_telegram(chat_id, "🔄 Đã reset cuộc hội thoại.")
                        return request.make_response("OK", status=200)

                    # Báo lỗi nếu thiếu thư viện AI
                    if not HAS_GENAI:
                        self._send_telegram(chat_id, "⚠️ AI chưa sẵn sàng.")
                        return request.make_response("OK", status=200)

                    # 4. Giao tiếp với AI
                    self._handle_chat_with_gemini(env, session, user_text)

                except Exception as e:
                    _logger.error(f"Lỗi Logic Bot: {str(e)}")
                    # self._send_telegram(chat_id, f"Lỗi hệ thống: {str(e)}") # Bật lên nếu muốn check lỗi

        except Exception as e:
            _logger.error(f"Lỗi Sập Webhook Odoo/Sai DB: {str(e)}")
            return request.make_response("Bad Request", status=400)

        return request.make_response("OK", status=200)

    # Truyền thêm biến env từ hàm trên vào đây để AI truy vấn Database
    def _handle_chat_with_gemini(self, env, session, user_text):
        try:
            phong_hop_sudo = env['quan_ly_phong_hop'].search([])
>>>>>>> 650bb4e2702a62dc64cea368b2074c3087058603
            rooms_info = []

            for p in phong_hop_sudo:
                tb = ", ".join([t.name for t in p.thiet_bi_ids])
                rooms_info.append(f"{p.name} ({p.suc_chua} người) - {tb}")

<<<<<<< HEAD
            nhan_vien_sudo = request.env['nhan_vien'].sudo().search([])
=======
            nhan_vien_sudo = env['nhan_vien'].search([])
>>>>>>> 650bb4e2702a62dc64cea368b2074c3087058603
            employees_info = ", ".join([nv.name for nv in nhan_vien_sudo])

            chat_history = json.loads(session.chat_history or "[]")
            collected_data = json.loads(session.collected_data or "{}")

            prompt = f"""
Bạn là trợ lý đặt phòng.
Danh sách phòng: {rooms_info}
Nhân viên: {employees_info}

Dữ liệu hiện có: {collected_data}
User: {user_text}

Trả về JSON:
{{
  "reply": "text",
  "json_data": {{
    "so_luong_nguoi": null,
    "nhan_vien": null,
    "ten_phong": null,
    "thoi_gian_muon": null,
    "thoi_gian_tra": null,
    "booking_confirmed": false
  }}
}}
"""

            # ✅ FIX 3: chống crash Gemini
            response = model.generate_content(prompt)
            raw_text = response.text.strip()

            raw_text = raw_text.replace("```json", "").replace("```", "").strip()

            result = json.loads(raw_text)

            reply = result.get("reply", "OK")
            new_data = result.get("json_data", {})

            chat_history.append({"user": user_text, "bot": reply})

            session.write({
                'chat_history': json.dumps(chat_history[-8:]),
                'collected_data': json.dumps(new_data)
            })
<<<<<<< HEAD

            if str(new_data.get('booking_confirmed')).lower() == 'true':
                self._tao_ho_so_dat_phong(new_data, session)
            else:
                self._send_telegram(session.chat_id, reply)

        except Exception as e:
            _logger.error(f"Gemini error: {str(e)}")
            self._send_telegram(session.chat_id, "⚠️ AI lỗi, thử lại sau.")

    # ================================
    def _tao_ho_so_dat_phong(self, data, session):
        try:
            nv = request.env['nhan_vien'].sudo().search([('name', 'ilike', data.get('nhan_vien'))], limit=1)
            phong = request.env['quan_ly_phong_hop'].sudo().search([('name', 'ilike', data.get('ten_phong'))], limit=1)

            if not nv or not phong:
                self._send_telegram(session.chat_id, "❌ Không tìm thấy dữ liệu.")
=======

            if str(new_data.get('booking_confirmed')).lower() == 'true':
                self._tao_ho_so_dat_phong(env, new_data, session)
            else:
                self._send_telegram(session.chat_id, reply)

        except Exception as e:
            _logger.error(f"Gemini error: {str(e)}")
            self._send_telegram(session.chat_id, "⚠️ AI đang bận suy nghĩ, thử lại sau.")

    # ================================
    def _tao_ho_so_dat_phong(self, env, data, session):
        try:
            nv = env['nhan_vien'].search([('name', 'ilike', data.get('nhan_vien'))], limit=1)
            phong = env['quan_ly_phong_hop'].search([('name', 'ilike', data.get('ten_phong'))], limit=1)

            if not nv or not phong:
                self._send_telegram(session.chat_id, "❌ Không tìm thấy dữ liệu tên nhân viên hoặc tên phòng trên hệ thống. Phiếu chưa duyệt.")
>>>>>>> 650bb4e2702a62dc64cea368b2074c3087058603
                return

            vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

            t_muon = vn_tz.localize(datetime.strptime(data.get('thoi_gian_muon'), '%Y-%m-%d %H:%M')).astimezone(pytz.UTC).replace(tzinfo=None)
            t_tra = vn_tz.localize(datetime.strptime(data.get('thoi_gian_tra'), '%Y-%m-%d %H:%M')).astimezone(pytz.UTC).replace(tzinfo=None)

<<<<<<< HEAD
            request.env['dat_phong'].sudo().create({
=======
            env['dat_phong'].create({
>>>>>>> 650bb4e2702a62dc64cea368b2074c3087058603
                'phong_id': phong.id,
                'nguoi_muon_id': nv.id,
                'so_luong_nguoi': int(data.get('so_luong_nguoi', 0)),
                'thoi_gian_muon_du_kien': t_muon,
                'thoi_gian_tra_du_kien': t_tra,
                'trang_thai': 'chờ_duyệt',
            })

<<<<<<< HEAD
            self._send_telegram(session.chat_id, "🎉 Đặt phòng thành công!")
=======
            self._send_telegram(session.chat_id, "🎉 Đặt phòng thành công trên hệ thống Odoo!")
>>>>>>> 650bb4e2702a62dc64cea368b2074c3087058603
            session.unlink()

        except Exception as e:
            _logger.error(f"Create booking error: {str(e)}")
<<<<<<< HEAD
            self._send_telegram(session.chat_id, "❌ Lỗi tạo đơn.")
=======
            self._send_telegram(session.chat_id, "❌ Lỗi tạo đơn (Có bị thể kẹt do đặt phòng trong quá khứ hoặc trùng thời gian). Cú pháp: /reset")
>>>>>>> 650bb4e2702a62dc64cea368b2074c3087058603

    # ================================
    def _send_telegram(self, chat_id, message):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}

        try:
            requests.post(url, json=payload, timeout=5)
        except Exception:
            pass