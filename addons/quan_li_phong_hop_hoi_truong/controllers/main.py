# -*- coding: utf-8 -*-
import json
import logging
import requests
import pytz
from datetime import datetime
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

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
    
    @http.route('/telegram/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def process_webhook(self, **kw):
        # Telegram gửi JSON THô (Raw JSON), không phải Odoo JSON-RPC nên bắt buộc type='http'
        try:
            update = json.loads(request.httprequest.data)
        except Exception:
            return request.make_response("Bad Request", status=400)

        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"]
            username = update["message"]["chat"].get("username", "")

            # 1. Tìm hoặc tạo Session (Bộ nhớ não)
            session_sudo = request.env['bot_telegram_session'].sudo()
            session = session_sudo.search([('chat_id', '=', str(chat_id))], limit=1)
            
            # Khởi tạo não bộ nếu lần đầu chat
            if not session:
                session = session_sudo.create({
                    'chat_id': str(chat_id),
                    'username': username,
                    'chat_history': json.dumps([]),
                    'collected_data': json.dumps({})
                })
            
            # Xử lý Cú pháp Reset để xóa trí nhớ bắt đầu cuộc hội thoại mới
            if user_text.strip().lower() == '/reset':
                session.unlink()
                self._send_telegram(chat_id, "🔄 Đã xóa trắng biểu mẫu phòng. Bạn cần hỗ trợ gì mới không?")
                return request.make_response("OK", status=200)

            if not HAS_GENAI:
                self._send_telegram(chat_id, "⚠️ Cảnh báo: Odoo chưa được cài thư viện google-generativeai. Bạn vui lòng chạy lệnh `pip install google-generativeai` trên máy chủ và Restart lại Odoo nhé.")
                return request.make_response("OK", status=200)

            # 2. Xử lý câu chat bằng Gemini
            self._handle_chat_with_gemini(session, user_text)

        return request.make_response("OK", status=200)

    def _handle_chat_with_gemini(self, session, user_text):
        # --- A. Cung cấp Dữ liệu Odoo nội bộ cho AI ---
        phong_hop_sudo = request.env['quan_ly_phong_hop'].sudo().search([])
        rooms_info = []
        for p in phong_hop_sudo:
            tb = ", ".join([t.name for t in p.thiet_bi_ids])
            rooms_info.append(f"Tên phòng: '{p.name}' | Sức chứa tối đa: {p.suc_chua} | Thiết bị có sẵn: {tb}")
        
        nhan_vien_sudo = request.env['nhan_vien'].sudo().search([])
        employees_info = ", ".join([nv.name for nv in nhan_vien_sudo])

        # --- B. Đọc trí nhớ ---
        chat_history = json.loads(session.chat_history)
        collected_data = json.loads(session.collected_data)

        # --- C. System Prompt Mệnh Lệnh (Cốt lõi của Bot) ---
        prompt = f"""
        Bạn là "Trợ Lý Ảo Đặt Phòng" thông minh của công ty chạy qua Telegram. Khách hàng đang nhắn tin cho bạn.
        Nhiệm vụ của bạn là lấy đủ 5 thông tin sau để Đặt Phòng:
        1. "so_luong_nguoi" (số người cần không gian phòng, dạng số nguyên).
        2. "nhan_vien" (tên người đứng ra mượn, phải nằm trong danh sách nhân viên công ty: {employees_info}).
        3. "ten_phong" (phòng mà khách muốn chốt. Hãy gợi ý phòng tự động dựa trên sức chứa và Danh sách phòng sau: {'; '.join(rooms_info)}).
        4. "thoi_gian_muon" (giờ khách bắt đầu dùng phòng, phải là định dạng 'YYYY-MM-DD HH:MM').
        5. "thoi_gian_tra" (giờ khách kết thúc, phải là định dạng 'YYYY-MM-DD HH:MM').

        Bộ chứa dữ liệu tạm thời bạn đã gom nhặt được từ trước tới nay: {json.dumps(collected_data, ensure_ascii=False)}

        CÂU CHAT MỚI NHẤT CỦA KHÁCH: "{user_text}"

        Quy tắc trả lời:
        - Đóng vai nhiệt tình, tự nhiên, và trả lời siêu ngắn gọn. 
        - Nếu khách nói cần phòng 30 người, hãy quét danh sách phòng và GỢI Ý luôn phòng phù hợp nhất và thiết bị có trong đó để khách duyệt.
        - Hãy dẫn dắt khách bằng cách hỏi từng thông tin một nếu chưa đủ (Ví dụ: "Anh ơi, anh cho em xin ngày giờ bắt đầu và kết thúc nhé?").
        - Trở thành chiếc Bot tâm lý, nếu đã thu thập đủ trọn vẹn 5 biến số, hãy đọc lại báo cáo và hỏi khách 1 câu chốt sự thật: "Dạ thông tin đã đầy đủ, em tiến hành đặt phòng luôn nhé anh?".
        - CHỈ KHI NÀO khách phản hồi đồng ý ở câu chốt (khách kêu Ok, Có, Duyệt...), bạn mới được gán giá trị biến "booking_confirmed" bằng true. Nếu khách bảo từ chối thì đổi ý, vẫn bằng false.

        === BẮT BUỘC === 
        Bảo mật hệ thống: Bạn chỉ được phép trả về kết quả là MỘT chuỗi văn bản dạng JSON THUẦN TÚY (Lưu ý: Không bọc trong markdown code block, không có chữ ```json). Mã JSON phải có chính xác 2 key sau:
        {{
            "reply": "Câu chữ bạn chat lại khách (Tự nhiên, thân thiện tiếng Việt)",
            "json_data": {{
                "so_luong_nguoi": 30, 
                "nhan_vien": "Tên nhân viên", 
                "ten_phong": "Tên phòng chốt",
                "thoi_gian_muon": "YYYY-MM-DD HH:MM", 
                "thoi_gian_tra": "YYYY-MM-DD HH:MM", 
                "booking_confirmed": false
            }}
        }}  (Nếu thông tin nào khách chưa nói hoặc bạn AI chưa biết, bạn điền giá trị là null cho key đó nhé)
        """

        try:
            # --- D. Gọi Gemini API ---
            response = model.generate_content(prompt)
            
            # --- E. Xử lý Output JSON từ AI ---
            raw_text = response.text.replace('```json', '').replace('```', '').strip()
            result = json.loads(raw_text)
            
            gemini_reply = result.get('reply', 'Dạ, em đang bị kẹt xíu, anh thử nhắn lại nhé.')
            new_data = result.get('json_data', {})
            
            # Cập nhật Session cho Trí nhớ
            chat_history.append({"user": user_text, "bot": gemini_reply})
            session.write({
                'chat_history': json.dumps(chat_history[-8:]), # Giữ trí nhớ 8 câu gần nhất
                'collected_data': json.dumps(new_data)
            })
            
            # --- F. Chốt Đơn Đặt Phòng qua Logic của Odoo ---
            if str(new_data.get('booking_confirmed')).lower() == 'true':
                self._tao_ho_so_dat_phong(new_data, session)
            else:
                self._send_telegram(session.chat_id, gemini_reply)
                
        except json.JSONDecodeError:
            _logger.error(f"Lỗi phân giải JSON từ Gemini: {response.text}")
            self._send_telegram(session.chat_id, "Hệ thống AI xử lý bị rối, bạn gõ `/reset` để làm lại từ đầu nhé.")
        except Exception as e:
            _logger.error(f"Gemini API Error: {str(e)}")
            self._send_telegram(session.chat_id, "Hệ thống AI đang bảo trì kết nối, vui lòng thử lại sau.")

    def _tao_ho_so_dat_phong(self, data, session):
        chat_id = session.chat_id
        try:
            # Đối soát nhân viên và phòng thực tế trong Odoo Data
            nv = request.env['nhan_vien'].sudo().search([('name', 'ilike', data.get('nhan_vien'))], limit=1)
            phong = request.env['quan_ly_phong_hop'].sudo().search([('name', 'ilike', data.get('ten_phong'))], limit=1)
            
            if not nv or not phong:
                self._send_telegram(chat_id, "❌ Lỗi: Không thể tìm thấy Tên nhân viên hoặc Tên phòng đã chốt trong hệ thống. Đơn đăng ký chưa được khởi tạo! Bạn vui lòng `/reset` chat lại.")
                return

            vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            t_muon_vn = datetime.strptime(data.get('thoi_gian_muon'), '%Y-%m-%d %H:%M')
            t_tra_vn = datetime.strptime(data.get('thoi_gian_tra'), '%Y-%m-%d %H:%M')
            
            t_muon_utc = vn_tz.localize(t_muon_vn).astimezone(pytz.UTC).replace(tzinfo=None)
            t_tra_utc = vn_tz.localize(t_tra_vn).astimezone(pytz.UTC).replace(tzinfo=None)

            # Lệnh Tạo Bản Ghi Tự Động
            request.env['dat_phong'].sudo().create({
                'phong_id': phong.id,
                'nguoi_muon_id': nv.id,
                'so_luong_nguoi': int(data.get('so_luong_nguoi', 0)),
                'thoi_gian_muon_du_kien': t_muon_utc,
                'thoi_gian_tra_du_kien': t_tra_utc,
                'trang_thai': 'chờ_duyệt',
            })
            
            self._send_telegram(chat_id, f"🎉 THÀNH CÔNG RỰC RỠ! Bot AI đã giúp bạn đặt lịch mượn phòng '{phong.name}'. Phiếu đang ở trạng thái CHỜ DUYỆT trên hệ thống. Xin cảm ơn bạn!")
            session.unlink()
            
        except Exception as e:
            _logger.error(f"Error Create Booking: {str(e)}")
            self._send_telegram(chat_id, f"❌ Rất tiếc, Odoo từ chối lưu phiếu tạo phòng. Nguyên nhân có thể do Lỗi Trùng Lịch hoặc vi phạm (chọn giờ quá khứ). Bạn hãy `/reset` tìm giờ khác nhé.")

    def _send_telegram(self, chat_id, message):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception:
            pass
