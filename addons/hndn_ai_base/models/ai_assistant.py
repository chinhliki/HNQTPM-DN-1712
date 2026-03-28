# -*- coding: utf-8 -*-
import re
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

    @staticmethod
    def _format_ai_response(text):
        """
        Chuyển đổi text thuần từ Gemini thành HTML dễ đọc trong bubble chat.
        Xử lý: xuống dòng, in đậm (**text**), danh sách gạch đầu dòng (- item), emoji giữ nguyên.
        """
        if not text:
            return text

        # Escape HTML cơ bản để tránh XSS (trừ các tag sẽ tự thêm)
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # In đậm **text** → <b>text</b>
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

        # In nghiêng *text* (không phải **) → <i>text</i>
        text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)

        # Xử lý từng dòng
        lines = text.split('\n')
        result_lines = []
        for line in lines:
            stripped = line.strip()
            # Dòng bắt đầu bằng "- " hoặc "• " → bullet point
            if re.match(r'^[-•] ', stripped):
                content = stripped[2:]
                result_lines.append(f'<div style="margin:2px 0; padding-left:12px;">• {content}</div>')
            # Dòng bắt đầu bằng số "1. ", "2. " → numbered list
            elif re.match(r'^\d+\. ', stripped):
                result_lines.append(f'<div style="margin:2px 0; padding-left:12px;">{stripped}</div>')
            # Dòng trống → khoảng cách nhỏ
            elif stripped == '':
                result_lines.append('<div style="height:6px;"></div>')
            # Dòng bình thường
            else:
                result_lines.append(f'<div>{stripped}</div>')

        return '\n'.join(result_lines)

    def action_ask_ai(self):
        import json
        from datetime import datetime as dt
        for rec in self:
            api_key = self.env['ir.config_parameter'].sudo().get_param('hndn_ai_base.hndn_gemini_api_key')
            if not api_key:
                return "Vui lòng cấu hình Gemini API Key!"

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

            # 3. DỮ LIỆU THỰC TẾ: Phòng + Lịch đặt đang hoạt động
            from datetime import datetime as dt_now, timedelta
            now = dt_now.now()
            now_str = now.strftime('%d/%m/%Y %H:%M')
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=7)  # Hiển thị lịch 7 ngày tới

            phong_list = self.env['quan_ly_phong_hop'].search([])
            phong_info_lines = []
            for p in phong_list:
                # Lấy các đơn đặt đang active trong 7 ngày tới của phòng này
                bookings = self.env['dat_phong'].search([
                    ('phong_id', '=', p.id),
                    ('trang_thai', 'in', ['đã_duyệt', 'đang_sử_dụng', 'chờ_duyệt']),
                    ('thoi_gian_tra_du_kien', '>=', now),
                    ('thoi_gian_muon_du_kien', '<=', today_end),
                ], order='thoi_gian_muon_du_kien asc')

                # Lấy danh sách thiết bị
                thiet_bi = []
                for tb in p.thiet_bi_ids:
                    status_icon = "✅" if tb.trang_thai == 'san_sang' else "🛠"
                    thiet_bi.append(f"      {status_icon} {tb.name} (SL: {tb.so_luong})")
                thiet_bi_str = "\n".join(thiet_bi) if thiet_bi else "      (Không có thiết bị)"

                if bookings:
                    lich = []
                    for b in bookings:
                        import pytz
                        tz = pytz.timezone('Asia/Ho_Chi_Minh')
                        t_bat_dau = b.thoi_gian_muon_du_kien.replace(tzinfo=pytz.UTC).astimezone(tz).strftime('%d/%m %H:%M')
                        t_ket_thuc = b.thoi_gian_tra_du_kien.replace(tzinfo=pytz.UTC).astimezone(tz).strftime('%H:%M')
                        trang_thai_label = {'chờ_duyệt': 'chờ duyệt', 'đã_duyệt': 'đã đặt', 'đang_sử_dụng': 'đang dùng'}.get(b.trang_thai, b.trang_thai)
                        nguoi_muon = b.nguoi_muon_id.name or "Không rõ"
                        lich.append(f"    🔴 {t_bat_dau}–{t_ket_thuc}: {nguoi_muon} ({trang_thai_label})")
                    lich_str = "\n".join(lich)
                    phong_info_lines.append(f"  📌 {p.name} | Sức chứa: {p.suc_chua} người\n    Thiết bị:\n{thiet_bi_str}\n    Lịch bận:\n{lich_str}")
                else:
                    phong_info_lines.append(f"  ✅ {p.name} | Sức chứa: {p.suc_chua} người | Trống hoàn toàn\n    Thiết bị:\n{thiet_bi_str}")

            phong_info = "\n".join(phong_info_lines) or "  (Chưa có phòng nào trong hệ thống)"

            # 4. Ngữ cảnh bổ sung theo từ khóa
            extra_context = ""
            if any(k in question.lower() for k in ['nhân viên', 'lương', 'phòng ban']):
                employees = self.env['nhan_vien'].search([], limit=5)
                emp_info = "\n".join([f"- {e.name}" for e in employees])
                extra_context += f"\nDanh sách một số nhân viên:\n{emp_info}\n"

            system_prompt = f"""Bạn là Trợ lý AI chuyên nghiệp của hệ thống Quản lý Phòng họp.
Ngày giờ hiện tại: {now_str} (múi giờ Việt Nam)
Nhiệm vụ: Hỗ trợ nhân viên tìm phòng TRỐNG và ĐẶT PHÒNG thay cho họ.

=== TRẠNG THÁI PHÒNG HỌP (CẬP NHẬT THỰC TẾ TỪ HỆ THỐNG) ===
{phong_info}
{extra_context}
=== QUY TRÌNH XỬ LÝ ===
1. Đọc kỹ danh sách phòng & lịch bận bên trên trước khi gợi ý.
2. Nếu user hỏi phòng nào trống → dựa vào lịch thực tế bên trên để trả lời chính xác.
3. Nếu thiếu thông tin (số người, thời gian) → hỏi lại CỤ THỂ từng thứ.
4. Khi đủ thông tin → kiểm tra xem phòng có bị trùng lịch không → gợi ý phòng phù hợp → hỏi xác nhận:
   "Tôi sẽ đặt [Tên phòng] từ [HH:MM] đến [HH:MM] ngày [DD/MM] cho [N] người. Bạn xác nhận chứ?"
5. Nếu user đồng ý (ok, được, đặt đi, xác nhận, ừ, yes...) → xuất JSON:
   JSON_DATA: {{"phong": "Tên phòng", "nguoi": "", "bat_dau": "YYYY-MM-DD HH:MM:SS", "ket_thuc": "YYYY-MM-DD HH:MM:SS", "so_nguoi": 5, "confirmed": true}}
6. Nếu chưa xác nhận → KHÔNG xuất JSON_DATA.

LƯU Ý: Lịch bận hiển thị theo giờ VN. Chỉ gợi ý phòng không có lịch trùng với thời gian user yêu cầu.

Lịch sử hội thoại:
{history}"""

            from odoo.addons.hndn_ai_base.utils.ai_messenger_utils import AIMessengerUtils
            response = AIMessengerUtils.get_gemini_response(api_key, f"{system_prompt}\nCâu hỏi hiện tại: {question}")

            if response:
                # Tách phần text sạch (bỏ JSON nếu có)
                clean_text = response.split("JSON_DATA:")[0].strip() if "JSON_DATA:" in response else response

                # ✅ Format đẹp: xuống dòng, in đậm, bullet list → HTML
                formatted_text = self._format_ai_response(clean_text)

                self.env['ai_chat_message'].create({
                    'session_id': rec.id,
                    'role': 'assistant',
                    'content': formatted_text
                })
                rec.answer = clean_text  # Lưu dạng thuần cho field answer

                # Trích xuất JSON và tự động đặt phòng nếu user đã xác nhận
                booking_created = rec._process_booking_data(response)

                if booking_created:
                    # AI vừa tạo đơn thành công — thông báo ngay trong chat
                    self.env['ai_chat_message'].create({
                        'session_id': rec.id,
                        'role': 'assistant',
                        'content': f"✅ Đã đặt phòng thành công! Đơn mượn đang chờ phê duyệt từ quản lý."
                    })

                # Câu hỏi gợi ý cho lần sau
                suggestions = ["Đặt phòng khác", "Xem phòng nào còn trống", "Hủy đặt phòng", "Xem lịch sử đặt"]
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
        """Tự động trích xuất thông tin và ĐẶT PHÒNG luôn nếu user đã xác nhận (confirmed=true)"""
        import json
        import logging
        from datetime import datetime as dt
        _logger = logging.getLogger(__name__)

        if "JSON_DATA:" not in text:
            return False
        try:
            json_raw = text.split("JSON_DATA:")[1].strip()
            json_raw = json_raw.replace('```json', '').replace('```', '').strip()
            end = json_raw.find('}')
            if end != -1:
                json_raw = json_raw[:end + 1]
            data = json.loads(json_raw)

            # Điền thông tin vào record
            phong = None
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

            # ✅ TỰ ĐỘNG ĐẶT PHÒNG nếu user đã xác nhận (confirmed=true)
            if data.get('confirmed') and self.phong_id and self.thoi_gian_muon and self.thoi_gian_tra:
                vals = {
                    'phong_id': self.phong_id.id,
                    'thoi_gian_muon_du_kien': self.thoi_gian_muon,
                    'thoi_gian_tra_du_kien': self.thoi_gian_tra,
                    'so_luong_nguoi': self.so_luong_nguoi or 1,
                    'trang_thai': 'chờ_duyệt',
                    'ai_session_id': self.id,  # ✅ Liên kết với phiên chat này
                }
                # Ưu tiên người mượn từ chat, nếu không có thì dùng user hiện tại
                if self.nguoi_muon_id:
                    vals['nguoi_muon_id'] = self.nguoi_muon_id.id
                else:
                    nv = self.env['nhan_vien'].search([('user_id', '=', self.env.uid)], limit=1)
                    if nv:
                        vals['nguoi_muon_id'] = nv.id

                booking = self.env['dat_phong'].create(vals)
                self.dat_phong_id = booking.id
                _logger.info(f"AI auto-created booking #{booking.id} for room {self.phong_id.name}")
                return True  # Báo hiệu đã tạo đơn thành công

            return False  # Chưa xác nhận, chỉ lưu thông tin tạm

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Parse booking JSON error: {e}")
            return False

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
            'ai_session_id': self.id,  # ✅ Liên kết với phiên chat này
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
