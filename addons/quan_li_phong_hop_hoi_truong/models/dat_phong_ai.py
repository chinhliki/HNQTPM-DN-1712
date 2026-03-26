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
        """Gửi tin nhắn và nhận phản hồi"""
        self.ensure_one()
        self.action_ask_ai()
        # Không cần return action nếu bạn muốn ở lại trang hiện tại, Odoo sẽ tự reload field compute
        return True

    def action_ask_ai(self):
        # Tốt nhất nên lấy từ Settings: self.env['ir.config_parameter'].sudo().get_param('gemini.api_key')
        api_key = "AIzaSyB1-huV0N_l1aM9jav21Gn9sFOC4xefiXo" 
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        # Lấy dữ liệu phòng họp thực tế
        try:
            rooms = self.env['quan_ly_phong_hop'].search([])
            room_data = [{"phòng": r.name, "sức chứa": r.suc_chua, "trạng thái": r.trang_thai} for r in rooms]
        except:
            room_data = "Không thể lấy dữ liệu phòng."

        context = f"""
        Bạn là trợ lý AI thông minh trong hệ thống Odoo của doanh nghiệp.
        Dữ liệu phòng họp hiện tại: {json.dumps(room_data, ensure_ascii=False)}
        Nhiệm vụ: Tư vấn phòng phù hợp dựa trên yêu cầu người dùng. 
        Nếu họ muốn đặt, hãy bảo họ vào menu 'Đăng ký mượn phòng'.
        Trả lời bằng tiếng Việt, thân thiện, dùng icon.
        """

        payload = {
            "contents": [{"parts": [{"text": f"{context}\n\nNgười dùng hỏi: {self.name}"}]}]
        }

        try:
            res = requests.post(url, json=payload, timeout=15)
            res.raise_for_status()
            result = res.json()
            if 'candidates' in result:
                answer = result['candidates'][0]['content']['parts'][0]['text']
                self.write({'response': answer})
        except Exception as e:
            _logger.error(f"Gemini AI Error: {str(e)}")
            self.write({'response': f"⚠️ Xin lỗi, tôi gặp trục trặc kết nối: {str(e)}"})