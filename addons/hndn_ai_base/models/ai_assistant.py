# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AIAssistant(models.Model):
    _name = 'ai_assistant'
    _description = 'HNDN AI Virtual Assistant'
    _rec_name = 'question'
    _order = 'create_date desc'

    question = fields.Text("Câu hỏi cuối", readonly=True)
    answer = fields.Text("Trả lời cuối", readonly=True)
    user_id = fields.Many2one('res.users', string="Người hỏi", default=lambda self: self.env.user, readonly=True)
    message_ids = fields.One2many('ai_chat_message', 'session_id', string="Lịch sử hội thoại")
    suggested_questions = fields.Text("Câu hỏi gợi ý (JSON)", help="Lưu danh sách câu hỏi gợi ý dạng JSON")

    # Thông tin AI trích xuất để đặt phòng
    phong_id = fields.Many2one("quan_ly_phong_hop", string="Phòng gợi ý")
    nguoi_muon_id = fields.Many2one("nhan_vien", string="Người mượn")
    thoi_gian_muon = fields.Datetime(string="Giờ bắt đầu")
    thoi_gian_tra = fields.Datetime(string="Giờ kết thúc")
    so_luong_nguoi = fields.Integer(string="Số người")
    dat_phong_id = fields.Many2one("dat_phong", string="Đơn đặt phòng đã tạo", readonly=True)

    def action_ask_ai(self):
        import json
        from datetime import datetime as dt
        for rec in self:
            api_key = self.env['ir.config_parameter'].sudo().get_param('hndn_ai_base.hndn_gemini_api_key')
            if not api_key:
                self.env['ai_chat_message'].create({
                    'session_id': rec.id,
                    'role': 'assistant',
                    'content': "⚠️ Chưa có API Key. Vui lòng vào Settings → HNDN AI → nhập Gemini API Key!"
                })
                continue

            # 1. Lấy lịch sử 10 tin nhắn gần nhất
            history = ""
            messages = self.env['ai_chat_message'].search([('session_id', '=', rec.id)], order='create_date desc', limit=10)
            for msg in reversed(messages):
                history += f"{'Người dùng' if msg.role == 'user' else 'AI'}: {msg.content}\n"

            # 2. Lấy câu hỏi mới nhất
            last_user_msg = self.env['ai_chat_message'].search([('session_id', '=', rec.id), ('role', '=', 'user')], order='create_date desc', limit=1)
            if not last_user_msg:
                continue
            question = last_user_msg.content

            # 3. NGUỔN DỮ LIỆU THỰC TẼ: Danh sách phòng và giờ hiện tại
            phong_list = self.env['quan_ly_phong_hop'].search([])
            phong_info = "\n".join([f"  - {p.name} (Sức chứa: {p.suc_chua})" for p in phong_list]) or "  (Chưa có phòng nào)"
            now_str = dt.now().strftime('%d/%m/%Y %H:%M')

            # 4. Ngữ cảnh bổ sung theo từ khóa
            extra_context = ""
            if any(k in question.lower() for k in ['nhân viên', 'lương', 'phòng ban']):
                employees = self.env['nhan_vien'].search([], limit=5)
                emp_info = "\n".join([f"- {e.name}" for e in employees])
                extra_context += f"\nDanh sách một số nhân viên:\n{emp_info}\n"

            system_prompt = f"""Bạn là Trợ lý AI chuyên nghiệp của hệ thống Quản lý Phòng hỏp.
Ngày giờ hiện tại: {now_str}
Nhiệm vụ: Hỗ trợ nhân viên tìm và đặt phòng hỏp phù hợp.

Danh sách phòng hỏp hiện có:
{phong_info}
{extra_context}
Quy trình:
1. Tiếp nhận yêu cầu từ người dùng.
2. Nếu thiếu thông tin (số người, thời gian, mục đích), hỏi lại lịch sự.
3. Gợi ý phòng phù hợp theo sức chứa.
4. Khi đủ thông tin, nhận xét tóm tắt và thêm đúng 1 dòng cuối:
   JSON_DATA: {{"phong": "Tên phòng", "nguoi": "Tên người mượn nếu có", "bat_dau": "YYYY-MM-DD HH:MM:SS", "ket_thuc": "YYYY-MM-DD HH:MM:SS", "so_nguoi": 5}}

Dựa trên lịch sử hội thoại:
{history}"""

            from odoo.addons.hndn_ai_base.utils.ai_messenger_utils import AIMessengerUtils
            response = AIMessengerUtils.get_gemini_response(api_key, f"{system_prompt}\nCâu hỏi hiện tại: {question}")

            if response:
                # Tách phần text sạch (bỏ JSON nếu có)
                clean_text = response.split("JSON_DATA:")[0].strip() if "JSON_DATA:" in response else response

                self.env['ai_chat_message'].create({
                    'session_id': rec.id,
                    'role': 'assistant',
                    'content': clean_text
                })
                rec.answer = clean_text

                # Trích xuất JSON để tự động điền thông tin đặt phòng
                rec._process_booking_data(response)

                # Câu hỏi gợi ý cho lần sau
                suggestions = ["Phòng nào có sức chứa lớn nhất?", "Đặt phòng khác", "Hủy đặt phòng", "Xem lịch sử đặt"]
                import json
                rec.suggested_questions = json.dumps(suggestions, ensure_ascii=False)
            else:
                self.env['ai_chat_message'].create({
                    'session_id': rec.id,
                    'role': 'assistant',
                    'content': "❌ Xảy ra lỗi kết nối AI. Vui lòng thử lại."
                })
                rec.answer = "Đã có lỗi xảy ra khi kết nối với AI."

    def _process_booking_data(self, text):
        """Tự động trích xuất và lưu thông tin đặt phòng từ JSON AI trả về"""
        import json
        from datetime import datetime as dt
        if "JSON_DATA:" not in text:
            return
        try:
            json_raw = text.split("JSON_DATA:")[1].strip()
            json_raw = json_raw.replace('```json', '').replace('```', '').strip()
            end = json_raw.find('}')
            if end != -1:
                json_raw = json_raw[:end + 1]
            data = json.loads(json_raw)

            if data.get('phong'):
                phong = self.env['quan_ly_phong_hop'].search([('name', 'ilike', data['phong'])], limit=1)
                if phong:
                    self.phong_id = phong.id

            if data.get('nguoi'):
                nv = self.env['nhan_vien'].search([('name', 'ilike', data['nguoi'])], limit=1)
                if nv:
                    self.nguoi_muon_id = nv.id

            if data.get('bat_dau'):
                self.thoi_gian_muon = dt.strptime(data['bat_dau'], '%Y-%m-%d %H:%M:%S')
            if data.get('ket_thuc'):
                self.thoi_gian_tra = dt.strptime(data['ket_thuc'], '%Y-%m-%d %H:%M:%S')

            self.so_luong_nguoi = int(data.get('so_nguoi', 0))
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Parse booking JSON error: {e}")

    def action_confirm_booking(self):
        """Tạo đơn đặt phòng từ thông tin AI đã trích xuất"""
        self.ensure_one()
        from odoo.exceptions import UserError
        if not self.phong_id:
            raise UserError("Đưa ra yêu cầu đặt phòng qua chat trước (‘Tôi muốn mượn phòng...’) để AI gợi ý!")
        if not self.thoi_gian_muon or not self.thoi_gian_tra:
            raise UserError("Hãy cho AI biết thời gian bắt đầu và kết thúc của buổi hỏp!")

        vals = {
            'phong_id': self.phong_id.id,
            'thoi_gian_muon_du_kien': self.thoi_gian_muon,
            'thoi_gian_tra_du_kien': self.thoi_gian_tra,
            'so_luong_nguoi': self.so_luong_nguoi or 1,
            'trang_thai': 'chờ_duyệt',
        }
        if self.nguoi_muon_id:
            vals['nguoi_muon_id'] = self.nguoi_muon_id.id
        else:
            nv = self.env['nhan_vien'].search([('user_id', '=', self.env.uid)], limit=1)
            if nv:
                vals['nguoi_muon_id'] = nv.id

        booking = self.env['dat_phong'].create(vals)
        self.dat_phong_id = booking.id

        # Báo AI biết đã đặt thành công
        self.env['ai_chat_message'].create({
            'session_id': self.id,
            'role': 'assistant',
            'content': f"✅ Đặt phòng *{self.phong_id.name}* thành công! Đơn mượn đã được gửi chờ phê duyệt."
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dat_phong',
            'view_mode': 'form',
            'res_id': booking.id,
            'target': 'new',
        }

    def get_conversation_data(self):
        self.ensure_one()
        messages = [{
            'id': m.id,
            'role': m.role,
            'content': m.content,
            'create_date': m.create_date,
        } for m in self.message_ids]
        
        import json
        suggestions = []
        if self.suggested_questions:
            try:
                suggestions = json.loads(self.suggested_questions)
            except:
                pass
                
        return {
            'messages': messages,
            'suggestions': suggestions
        }

class AIChatMessage(models.Model):
    _name = 'ai_chat_message'
    _description = 'Lịch sử tin nhắn AI'
    _order = 'create_date asc'

    session_id = fields.Many2one('ai_assistant', string="Phiên chat", ondelete='cascade')
    role = fields.Selection([('user', 'User'), ('assistant', 'AI')], string="Vai trò")
    content = fields.Text("Nội dung")
