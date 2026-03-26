import requests
import json
import logging
import pytz
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
from markupsafe import Markup # Dùng để render HTML an toàn

_logger = logging.getLogger(__name__)

class DatPhongAI(models.Model):
    _name = "dat_phong_ai"
    _description = "AI Trợ lý đặt phòng"
    _order = "create_date desc"

    name = fields.Char(string="Tin nhắn", required=True)
    response = fields.Text(string="Phản hồi từ AI", readonly=True)
    # Lưu ý: Đảm bảo model 'nhan_vien' đã tồn tại, nếu không hãy đổi thành 'res.users'
    nguoi_muon_id = fields.Many2one("res.users", string="Người dùng", default=lambda self: self.env.user)
    chat_log = fields.Html(string="Lịch sử Chat", compute="_compute_chat_log")

    @api.depends('name', 'response')
    def _compute_chat_log(self):
        """Tạo giao diện khung chat từ lịch sử tin nhắn"""
        for record in self:
            # Chỉ lấy lịch sử nếu bản ghi đã có ID (tránh lỗi khi đang tạo mới)
            domain = []
            if record.id:
                domain = [('id', '<=', record.id)]
            
            history = self.search(domain, limit=10, order="create_date desc")
            # Đảo ngược lại để tin nhắn cũ ở trên, mới ở dưới
            history = sorted(history, key=lambda x: x.create_date or datetime.now())

            html = '<div style="background: #f4f7f6; padding: 20px; border-radius: 10px; max-height: 400px; overflow-y: auto; border: 1px solid #ddd;">'
            
            for msg in history:
                # Tin nhắn User
                user_time = self._get_local_time(msg.create_date)
                html += f'''
                    <div style="margin-bottom: 15px; text-align: right;">
                        <span style="background: #007bff; color: white; padding: 8px 15px; border-radius: 15px 15px 0 15px; display: inline-block; max-width: 70%; word-wrap: break-word;">
                            {msg.name}
                        </span>
                        <div style="font-size: 10px; color: #888; margin-top: 3px;">Bạn - {user_time}</div>
                    </div>
                '''
                # Tin nhắn AI
                if msg.response:
                    ai_response = msg.response.replace("\n", "<br/>")
                    html += f'''
                        <div style="margin-bottom: 15px; text-align: left;">
                            <span style="background: #ffffff; color: #333; padding: 8px 15px; border-radius: 15px 15px 15px 0; display: inline-block; max-width: 80%; word-wrap: break-word; border: 1px solid #dee2e6; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                                {ai_response}
                            </span>
                            <div style="font-size: 10px; color: #888; margin-top: 3px;">🤖 Gemini AI - {user_time}</div>
                        </div>
                    '''
            html += '</div>'
            record.chat_log = Markup(html) # Ép kiểu về Markup để Odoo không sanitize mất CSS

    def _get_local_time(self, dt):
        if not dt: 
            dt = datetime.now()
        user_tz = pytz.timezone(self.env.user.tz or 'Asia/Ho_Chi_Minh')
        return dt.replace(tzinfo=pytz.UTC).astimezone(user_tz).strftime('%H:%M')

    def action_chat_ai(self):
        """Gửi tin nhắn, nhận phản hồi và xử lý logic ý định (intent)"""
        self.ensure_one()
        
        # 1. Gọi AI để lấy câu trả lời tư vấn
        self.action_ask_ai()
        
        # 2. Phân tích ý định (Simple Logic): Nếu khách muốn đặt phòng
        # Dựa trên từ khóa trong tin nhắn người dùng
        booking_keywords = ['đặt', 'book', 'mượn', 'thuê', 'lấy phòng']
        if any(key in self.name.lower() for key in booking_keywords):
            # Nếu người dùng có ý định đặt phòng, chúng ta có thể bổ sung thông tin vào response
            # Hoặc thực hiện hành động gì đó. Ở đây mình gợi ý AI luôn đưa ra link dẫn tới menu đặt phòng.
            pass

        return True

    def action_ask_ai(self):
        """Kết nối trực tiếp tới Google AI Studio v1 Stable"""
        api_key = "AIzaSyB1-huV0N_l1aM9jav21Gn9sFOC4xefiXo" 
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        # Thu thập dữ liệu ngữ cảnh
        try:
            rooms = self.env['quan_ly_phong_hop'].search([])
            room_list = []
            for r in rooms:
                room_list.append(f"- {r.name}: Sức chứa {r.suc_chua} người, Trạng thái: {r.trang_thai}")
            room_context = "\n".join(room_list)
        except:
            room_context = "Không có dữ liệu phòng."

        # Thiết lập Prompt Role-play cho AI
        system_instruction = f"""
        Bạn là Trợ lý Đặt phòng thông minh của công ty. 
        Dữ liệu phòng họp thực tế từ hệ thống:
        {room_context}

        QUY TẮC PHẢN HỒI:
        1. Nếu khách hỏi về phòng trống/phù hợp: Tư vấn dựa trên dữ liệu trên.
        2. Nếu khách muốn ĐẶT PHÒNG: Hãy bảo họ nhấn vào menu 'Đăng ký mượn phòng' để tạo đơn chính thức.
        3. Văn phong: Chuyên nghiệp, dùng tiếng Việt, có emoji.
        4. Trả lời ngắn gọn, đi thẳng vào vấn đề.
        """

        payload = {
            "contents": [{
                "parts": [{"text": f"{system_instruction}\n\nCâu hỏi khách hàng: {self.name}"}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            }
        }

        try:
            # Sử dụng headers để đảm bảo định dạng
            headers = {'Content-Type': 'application/json'}
            res = requests.post(url, json=payload, headers=headers)
            
            if res.status_code == 404:
                self.write({'response': "⚠️ Lỗi 404: Endpoint API v1 không tìm thấy. Có thể Key hoặc Model chưa khớp."})
                return False
                
            res.raise_for_status()
            result = res.json()
            
            if 'candidates' in result:
                answer = result['candidates'][0]['content']['parts'][0]['text']
                self.write({'response': answer})
        except Exception as e:
            error_msg = str(e)
            _logger.error(f"Gemini AI Error: {error_msg}")
            # Hiển thị lỗi thân thiện hơn nhưng vẫn chi tiết để debug
            self.write({'response': f"🤖 Rất tiếc, AI đang bận hoặc gặp lỗi kết nối. Vui lòng thử lại sau giây lát.\n(Chi tiết: {error_msg})"})