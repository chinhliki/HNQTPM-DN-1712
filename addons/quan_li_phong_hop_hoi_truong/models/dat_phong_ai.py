import requests
import json
import logging
import pytz
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

_logger = logging.getLogger(__name__)

class DatPhongAI(models.Model):
    _name = "dat_phong_ai"
    _description = "AI Trợ lý đặt phòng"
    _order = "create_date desc"

    name = fields.Char(string="Tin nhắn", required=True)
    response = fields.Text(string="Phản hồi từ AI", readonly=True)
    nguoi_muon_id = fields.Many2one("nhan_vien", string="Người dùng", default=lambda self: self.env.user.nhan_vien_id)
    chat_log = fields.Html(string="Lịch sử Chat", compute="_compute_chat_log")

    @api.depends('name', 'response')
    def _compute_chat_log(self):
        """Tạo giao diện khung chat từ lịch sử tin nhắn"""
        for record in self:
            # Lấy 10 tin nhắn gần nhất của người dùng này
            history = self.search([('create_date', '<=', record.create_date or fields.Datetime.now())], limit=10, order="create_date asc")
            
            html = '<div style="background: #f4f7f6; padding: 20px; border-radius: 10px; height: 400px; overflow-y: auto; border: 1px solid #ddd;">'
            for msg in history:
                # Tin nhắn của User
                html += f'''
                    <div style="margin-bottom: 15px; text-align: right;">
                        <span style="background: #007bff; color: white; padding: 8px 15px; border-radius: 15px 15px 0 15px; display: inline-block; max-width: 70%; word-wrap: break-word;">
                            {msg.name}
                        </span>
                        <div style="font-size: 10px; color: #888; margin-top: 3px;">User - {self._get_local_time(msg.create_date)}</div>
                    </div>
                '''
                if msg.response:
                    # Phản hồi của AI
                    html += f'''
                        <div style="margin-bottom: 15px; text-align: left;">
                            <span style="background: #e9ecef; color: #333; padding: 8px 15px; border-radius: 15px 15px 15px 0; display: inline-block; max-width: 80%; word-wrap: break-word; border: 1px solid #dee2e6;">
                                {msg.response.replace("\n", "<br/>")}
                            </span>
                            <div style="font-size: 10px; color: #888; margin-top: 3px;">🤖 Gemini AI - {self._get_local_time(msg.create_date)}</div>
                        </div>
                    '''
            html += '</div>'
            record.chat_log = html

    def _get_local_time(self, dt):
        if not dt: return ""
        user_tz = pytz.timezone(self.env.user.tz or 'Asia/Ho_Chi_Minh')
        return dt.replace(tzinfo=pytz.UTC).astimezone(user_tz).strftime('%H:%M')

    def action_chat_ai(self):
        """Gửi tin nhắn và nhận phản hồi, sau đó reload để hiện khung chat mới nhất"""
        self.action_ask_ai()
        # Trả về action để mở lại chính cái view này (làm mới giao diện)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dat_phong_ai',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def action_ask_ai(self):
        api_key = "AIzaSyB1-huV0N_l1aM9jav21Gn9sFOC4xefiXo"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        rooms = self.env['quan_ly_phong_hop'].search([])
        room_data = [{"name": r.name, "suc_chua": r.suc_chua, "trang_thai": r.trang_thai} for r in rooms]

        context = f"""
        Bạn là trợ lý AI quản lý phòng họp Odoo. 
        Dữ liệu phòng thực tế: {json.dumps(room_data)}
        Hãy tư vấn dựa trên dữ liệu trên. Giao tiếp thân thiện, ngắn gọn, dùng emoji.
        Nếu người dùng muốn đặt phòng, hãy hướng dẫn họ chọn menu 'Đăng ký mượn phòng'.
        """

        payload = {
            "contents": [{"parts": [{"text": f"{context}\n\nChat: {self.name}"}]}]
        }

        try:
            res = requests.post(url, json=payload, timeout=10)
            res.raise_for_status()
            result = res.json()
            if 'candidates' in result:
                self.response = result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            self.response = f"Lỗi kết nối AI: {str(e)}"
