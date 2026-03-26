import requests
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime

_logger = logging.getLogger(__name__)

class AIDatPhong(models.Model):
    _name = "ai_dat_phong"
    _description = "AI Trợ lý đặt phòng"
    _order = "create_date desc"

    GEMINI_API_KEY = "AIzaSyB1-huV0N_l1aM9jav21Gn9sFOC4xefiXo"
    GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

    name = fields.Char(string="Tiêu đề cuộc hội thoại", default=lambda self: _("Hội thoại AI %s") % datetime.now().strftime('%d/%m/%Y %H:%M'))
    user_id = fields.Many2one('res.users', string='Người sử dụng', default=lambda self: self.env.user)
    
    # Message logs
    chat_history = fields.Text(string="Lịch sử Chat (Hệ thống)", readonly=True)
    last_response = fields.Text(string="Phản hồi cuối từ AI", readonly=True)
    
    # Fields to hold extracted data
    phong_id = fields.Many2one("quan_ly_phong_hop", string="Phòng gợi ý")
    nguoi_muon_id = fields.Many2one("nhan_vien", string="Người mượn")
    thoi_gian_muon = fields.Datetime(string="Thời gian bắt đầu")
    thoi_gian_tra = fields.Datetime(string="Thời gian kết thúc")
    so_luong_nguoi = fields.Integer(string="Số lượng người")

    @api.model
    def create(self, vals):
        # Initialize chat history with system prompt
        phong_list = self.env['quan_ly_phong_hop'].search([]).mapped(lambda p: f"- {p.name} (Sức chứa: {p.suc_chua})")
        system_prompt = f"""
        Bạn là Trợ lý AI chuyên nghiệp của hệ thống Quản lý phòng họp Odoo.
        Nhiệm vụ: Giúp nhân viên tìm và đặt phòng họp.
        Dưới đây là danh sách các phòng đang có:
        {chr(10).join(phong_list)}

        Quy trình:
        1. Nhận yêu cầu từ người dùng (ví dụ: tôi muốn mượn phòng cho 10 người vào sáng mai).
        2. Nếu thiếu thông tin (số người, thời gian, tên phòng), hãy hỏi lại lịch sự.
        3. Dựa trên danh sách phòng, gợi ý phòng phù hợp (sức chứa đủ cho số người).
        4. Khi đã đủ thông tin, hãy CHỐT lại bằng một câu trả lời chứa từ khóa JSON_DATA: {{'phong': 'Tên phòng', 'nguoi': 'Tên nhân viên (nếu có)', 'nguoi_muon_id': 'ID nhân viên (nếu biết)', 'bat_dau': 'YYYY-MM-DD HH:MM:SS', 'ket_thuc': 'YYYY-MM-DD HH:MM:SS', 'so_nguoi': 10}}
        """
        vals['chat_history'] = system_prompt
        return super(AIDatPhong, self).create(vals)

    def action_chat_with_gemini(self):
        """Mở Wizard để chat hoặc xử lý tin nhắn mới"""
        return {
            'name': 'Hỏi Trợ lý AI',
            'type': 'ir.actions.act_window',
            'res_model': 'ai_chat_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_ai_session_id': self.id}
        }

    def _call_gemini_api(self, user_msg):
        headers = {'Content-Type': 'application/json'}
        full_prompt = f"{self.chat_history}\nNgười dùng: {user_msg}\nAI:"
        
        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }]
        }

        try:
            response = requests.post(
                f"{self.GEMINI_URL}?key={self.GEMINI_API_KEY}",
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            res_data = response.json()
            
            ai_text = res_data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            
            # Update history
            self.chat_history = f"{full_prompt} {ai_text}"
            self.last_response = ai_text
            
            # Try to extract JSON if present
            self._process_extracted_data(ai_text)
            
            return ai_text
        except Exception as e:
            _logger.error(f"Gemini API Error: {str(e)}")
            return "Xin lỗi, tôi gặp sự cố kết nối với AI. Vui lòng thử lại sau."

    def _process_extracted_data(self, text):
        if "JSON_DATA" in text:
            try:
                # Extract JSON string
                json_part = text.split("JSON_DATA:")[1].strip()
                # Clean potential markdown
                json_part = json_part.replace('```json', '').replace('```', '').strip()
                data = json.loads(json_part)
                
                # Search Room
                phong_name = data.get('phong')
                phong = self.env['quan_ly_phong_hop'].search([('name', 'ilike', phong_name)], limit=1)
                if phong:
                    self.phong_id = phong.id
                
                # Search Employee
                nguoi_name = data.get('nguoi')
                if nguoi_name:
                    nhan_vien = self.env['nhan_vien'].search([('name', 'ilike', nguoi_name)], limit=1)
                    if nhan_vien:
                        self.nguoi_muon_id = nhan_vien.id
                
                # Times
                if data.get('bat_dau'):
                    self.thoi_gian_muon = datetime.strptime(data['bat_dau'], '%Y-%m-%d %H:%M:%S')
                if data.get('ket_thuc'):
                    self.thoi_gian_tra = datetime.strptime(data['ket_thuc'], '%Y-%m-%d %H:%M:%S')
                
                self.so_luong_nguoi = data.get('so_nguoi', 0)
                
            except Exception as e:
                _logger.warning(f"Failed to parse AI JSON: {str(e)}")

    def action_confirm_booking(self):
        self.ensure_one()
        if not self.phong_id or not self.nguoi_muon_id or not self.thoi_gian_muon or not self.thoi_gian_tra:
            raise UserError("Vui lòng cung cấp đủ thông tin (Phòng, Người mượn, Thời gian) qua chat trước khi xác nhận!")
            
        new_booking = self.env['dat_phong'].create({
            'phong_id': self.phong_id.id,
            'nguoi_muon_id': self.nguoi_muon_id.id,
            'thoi_gian_muon_du_kien': self.thoi_gian_muon,
            'thoi_gian_tra_du_kien': self.thoi_gian_tra,
            'so_luong_nguoi': self.so_luong_nguoi,
            'trang_thai': 'chờ_duyệt'
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dat_phong',
            'view_mode': 'form',
            'res_id': new_booking.id,
            'target': 'current',
        }

class AIChatWizard(models.TransientModel):
    _name = "ai_chat_wizard"
    _description = "Cửa sổ Chat AI"

    ai_session_id = fields.Many2one('ai_dat_phong', string="Phiên AI")
    user_message = fields.Text(string="Tin nhắn của bạn")
    ai_response = fields.Text(string="Phản hồi từ Gemini", readonly=True)

    def action_send_message(self):
        if not self.user_message:
            return
        
        response = self.ai_session_id._call_gemini_api(self.user_message)
        self.ai_response = response
        self.user_message = "" # Clear message field
        
        # Re-open the wizard with response
        return {
            'name': 'Chat với AI',
            'type': 'ir.actions.act_window',
            'res_model': 'ai_chat_wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context
        }
