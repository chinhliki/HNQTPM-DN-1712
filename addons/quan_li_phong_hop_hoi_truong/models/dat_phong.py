from odoo import models, fields, api, exceptions
from datetime import datetime
from odoo.exceptions import ValidationError
import requests
import pytz

class DatPhong(models.Model):
    _name = "dat_phong"
    _description = "Đăng ký mượn phòng"

    # --- GIỮ NGUYÊN FIELDS CŨ + Nâng cấp Performance (Thêm index=True) ---
    # Tối ưu hóa hiệu năng: Việc đánh index ở Cổng DB sẽ làm tốc độ truy vấn search phòng và người mượn nhanh hơn đáng kể.
    phong_id = fields.Many2one("quan_ly_phong_hop", string="Phòng họp", required=True, index=True, ondelete="cascade")
    nguoi_muon_id = fields.Many2one("nhan_vien", string="Người mượn", required=True, index=True)  
    thiet_bi_ids = fields.One2many("thiet_bi", related="phong_id.thiet_bi_ids", string="Thiết bị trong phòng", readonly=True)
    chi_tiet_muon_thiet_bi_ids = fields.One2many("chi_tiet_muon_thiet_bi", "dat_phong_id", string="Chi tiết thiết bị mượn")
    thoi_gian_muon_du_kien = fields.Datetime(string="Thời gian mượn dự kiến", required=True)
    thoi_gian_muon_thuc_te = fields.Datetime(string="Thời gian mượn thực tế")
    thoi_gian_tra_du_kien = fields.Datetime(string="Thời gian trả dự kiến", required=True)
    thoi_gian_tra_thuc_te = fields.Datetime(string="Thời gian trả thực tế")
    trang_thai = fields.Selection([
        ("chờ_duyệt", "Chờ duyệt"),
        ("đã_duyệt", "Đã duyệt"),
        ("đang_sử_dụng", "Đang sử dụng"),
        ("đã_hủy", "Đã hủy"),
        ("đã_trả", "Đã trả")
    ], string="Trạng thái", default="chờ_duyệt", index=True)
    lich_su_ids = fields.One2many("lich_su_thay_doi", "dat_phong_id", string="Lịch sử mượn trả")
    chi_tiet_su_dung_ids = fields.One2many("dat_phong", "phong_id", string="Chi Tiết Sử Dụng", domain=[("trang_thai", "in", ["đang_sử_dụng", "đã_trả"])])
    
    # --- LIÊN KẾT AI ---
    ai_session_id = fields.Many2one("ai_assistant", string="Phiên Chat AI tạo đơn", ondelete="set null")

    # --- NÂNG CẤP: THÊM DỮ LIỆU CHO AI ---
    so_luong_nguoi = fields.Integer("Số lượng người tham gia", default=1)

    @api.constrains('so_luong_nguoi', 'phong_id')
    def _check_so_luong_nguoi_hop_le(self):
        for record in self:
            if record.so_luong_nguoi <= 0:
                raise ValidationError("❌ Số lượng người tham gia phải lớn hơn 0.")
            if record.phong_id and record.phong_id.suc_chua > 0 and record.so_luong_nguoi > record.phong_id.suc_chua:
                raise ValidationError(f"❌ Số lượng người ({record.so_luong_nguoi}) vượt quá sức chứa của phòng '{record.phong_id.name}' (Tối đa {record.phong_id.suc_chua} người). Vui lòng chọn phòng lớn hơn.")

    # --- NÂNG CẤP: HÀM GỢI Ý PHÒNG THÔNG MINH (AI LOGIC) ---
    def action_goi_y_phong_ai(self):
        """ 
        Thuật toán AI: Tự động phân tích sức chứa và trùng lịch 
        để đưa ra gợi ý phòng phù hợp và tiết kiệm tài nguyên nhất.
        """
        for record in self:
            if record.so_luong_nguoi <= 0:
                raise ValidationError("Vui lòng nhập số người tham gia để AI gợi ý!")
            
            if not record.thoi_gian_muon_du_kien or not record.thoi_gian_tra_du_kien:
                raise ValidationError("Vui lòng nhập thời gian mượn/trả dự kiến để AI kiểm tra lịch trống!")

            # 1. Tìm các phòng có sức chứa đủ yêu cầu
            phong_phu_hop = self.env['quan_ly_phong_hop'].search([('suc_chua', '>=', record.so_luong_nguoi)])

            # 2. Lọc ra các phòng KHÔNG bị trùng lịch trong khoảng thời gian đã chọn
            phong_trong = []
            for phong in phong_phu_hop:
                trung_lich = self.env['dat_phong'].search([
                    ('phong_id', '=', phong.id),
                    ('trang_thai', 'in', ['đã_duyệt', 'đang_sử_dụng']),
                    ('thoi_gian_muon_du_kien', '<', record.thoi_gian_tra_du_kien),
                    ('thoi_gian_tra_du_kien', '>', record.thoi_gian_muon_du_kien)
                ])
                if not trung_lich:
                    phong_trong.append(phong)

            if not phong_trong:
                raise exceptions.UserError("Hiện tại không có phòng nào vừa đủ sức chứa vừa trống vào thời gian này.")

            # 3. Thuật toán AI "Best Fit": Chọn phòng nhỏ nhất nhưng vẫn đủ chỗ
            phong_trong.sort(key=lambda p: p.suc_chua)
            phong_chon = phong_trong[0]

            record.phong_id = phong_chon.id
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'AI Gợi ý thành công',
                    'message': f'Đã xếp phòng "{phong_chon.name}" (Sức chứa: {phong_chon.suc_chua}).',
                    'type': 'success',
                    'sticky': False,
                }
            }

    # --- GIỮ NGUYÊN CÁC HÀM LOGIC GỐC (xac_nhan_duyet_phong, bat_dau_su_dung, etc.) ---
    @api.constrains('thoi_gian_muon_du_kien', 'thoi_gian_tra_du_kien')
    def _check_thoi_gian(self):
        for record in self:
            if record.thoi_gian_muon_du_kien and record.thoi_gian_tra_du_kien:
                if record.thoi_gian_tra_du_kien <= record.thoi_gian_muon_du_kien:
                    raise ValidationError("Lỗi: Thời gian trả dự kiến phải sau thời gian mượn dự kiến!")
            
            # Chỉ check lỗi thời gian khi mới "chờ duyệt" để không khóa record đang dùng
            if record.trang_thai == "chờ_duyệt" and record.thoi_gian_muon_du_kien and record.thoi_gian_muon_du_kien < fields.Datetime.now():
                raise ValidationError("❌ Thời gian mượn phòng không hợp lệ. Bạn không được chọn thời gian trong quá khứ.")

    @api.constrains('phong_id', 'thoi_gian_muon_du_kien', 'thoi_gian_tra_du_kien')
    def _check_trung_lich(self):
        for record in self:
            if record.phong_id and record.thoi_gian_muon_du_kien and record.thoi_gian_tra_du_kien:
                trung_lich = self.search([
                    ('phong_id', '=', record.phong_id.id),
                    ('id', '!=', record.id),
                    ('trang_thai', 'in', ['đã_duyệt', 'đang_sử_dụng']),
                    ('thoi_gian_muon_du_kien', '<', record.thoi_gian_tra_du_kien),
                    ('thoi_gian_tra_du_kien', '>', record.thoi_gian_muon_du_kien)
                ])
                if trung_lich:
                    raise ValidationError(f"⚠️ Lỗi: Phòng '{record.phong_id.name}' đã có người duyệt mượn hoặc đang sử dụng trong khoảng thời gian này! Vui lòng chọn giờ khác.")

    def _get_local_time_str(self, dt):
        """ Chuyển đổi giờ UTC (chuẩn của hệ thống Odoo) sang giờ địa phương (Việt Nam) """
        if not dt:
            return ''
        user_tz = pytz.timezone(self.env.user.tz or 'Asia/Ho_Chi_Minh')
        return dt.replace(tzinfo=pytz.UTC).astimezone(user_tz).strftime('%d/%m/%Y %H:%M')

    def xac_nhan_duyet_phong(self):
        for record in self:
            if record.trang_thai != "chờ_duyệt":
                raise exceptions.UserError("Chỉ có thể duyệt yêu cầu có trạng thái 'Chờ duyệt'.")
            record.write({"trang_thai": "đã_duyệt"})
            self.lich_su(record)
            
            # --- MỨC 3: Tích hợp API External (Telegram Bot) ---
            thoi_gian_muon = self._get_local_time_str(record.thoi_gian_muon_du_kien)
            thoi_gian_tra = self._get_local_time_str(record.thoi_gian_tra_du_kien)
            msg = (
                f"✅ *PHÒNG ĐƯỢC DUYỆT: {record.phong_id.name}*\n"
                f"👤 Người mượn: {record.nguoi_muon_id.name}\n"
                f"👥 Số lượng: {record.so_luong_nguoi} người\n"
                f"🕒 Bắt đầu: {thoi_gian_muon}\n"
                f"🕰 Kết thúc: {thoi_gian_tra}\n"
                f"🔔 Trạng thái: Đã duyệt và sẵn sàng sử dụng."
            )
            self._send_telegram_notification(msg)
            self._notify_ai_session(record, f"✅ Đơn đặt phòng **{record.phong_id.name}** của bạn đã được **phê duyệt**.")
            
            cung_phong_trung_thoi_gian = [
                ('phong_id', '=', record.phong_id.id),
                ('id', '!=', record.id),
                ('trang_thai', '=', 'chờ_duyệt'),
                ('thoi_gian_muon_du_kien', '<', record.thoi_gian_tra_du_kien),
                ('thoi_gian_tra_du_kien', '>', record.thoi_gian_muon_du_kien)
            ]
            xu_li_cung_phong_trung_thoi_gian = self.search(cung_phong_trung_thoi_gian)
            for other in xu_li_cung_phong_trung_thoi_gian:
                other.write({"trang_thai": "đã_hủy"})
                self.lich_su(other)
            khac_phong_trung_thoi_gian = [
                ('nguoi_muon_id', '=', record.nguoi_muon_id.id),
                ('id', '!=', record.id),
                ('trang_thai', '=', 'chờ_duyệt'),
                ('thoi_gian_muon_du_kien', '<', record.thoi_gian_tra_du_kien),
                ('thoi_gian_tra_du_kien', '>', record.thoi_gian_muon_du_kien)
            ]
            xu_li_khac_phong_trung_thoi_gian = self.search(khac_phong_trung_thoi_gian)
            for other in xu_li_khac_phong_trung_thoi_gian:
                other.write({"trang_thai": "đã_hủy"})
                self.lich_su(other)
                
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Duyệt thành công',
                'message': 'Đã xác nhận cho mượn phòng!',
                'type': 'success',
                'sticky': False,
            }
        }

    def huy_muon_phong(self):
        for record in self:
            if record.trang_thai != "chờ_duyệt":
                raise exceptions.UserError("Chỉ có thể hủy yêu cầu có trạng thái 'Chờ duyệt'.")
            record.write({"trang_thai": "đã_hủy"})
            self.lich_su(record)

            thoi_gian_muon = self._get_local_time_str(record.thoi_gian_muon_du_kien)
            msg = (
                f"❌ *TỪ CHỐI / HỦY PHÒNG: {record.phong_id.name}*\n"
                f"👤 Người định mượn: {record.nguoi_muon_id.name}\n"
                f"🕒 Kế hoạch thuê: {thoi_gian_muon}\n"
                f"🛑 Trạng thái: Yêu cầu đã bị hủy bỏ."
            )
            self._send_telegram_notification(msg)
            self._notify_ai_session(record, f"🛑 Rất tiếc, yêu cầu đặt phòng **{record.phong_id.name}** của bạn đã bị **từ chối/hủy bỏ**.")
            self._notify_ai_session(record, f"🛑 Rất tiếc, yêu cầu đặt phòng **{record.phong_id.name}** của bạn đã bị **từ chối/hủy bỏ**.")

    def huy_da_duyet(self):
        for record in self:
            if record.trang_thai != "đã_duyệt":
                raise exceptions.UserError("Chỉ có thể hủy yêu cầu có trạng thái 'Đã duyệt'.")
            record.write({"trang_thai": "đã_hủy"})
            self.lich_su(record)

            thoi_gian_muon = self._get_local_time_str(record.thoi_gian_muon_du_kien)
            msg = (
                f"⚠️ *HỦY SAU KHI ĐÃ DUYỆT: {record.phong_id.name}*\n"
                f"👤 Người định mượn: {record.nguoi_muon_id.name}\n"
                f"🕒 Lịch ban đầu: {thoi_gian_muon}\n"
                f"🛑 Trạng thái: Lịch phòng đã bị hủy giữa chừng."
            )
            self._send_telegram_notification(msg)
            self._notify_ai_session(record, f"⚠️ Lịch phòng **{record.phong_id.name}** đã được duyệt của bạn vừa bị **hủy bỏ**.")

    def bat_dau_su_dung(self):
        for record in self:
            if record.trang_thai != "đã_duyệt":
                raise exceptions.UserError("Chỉ có thể bắt đầu sử dụng phòng có trạng thái 'Đã duyệt'.")
            kiem_tra_phong = self.env["dat_phong"].search([
                ("phong_id", "=", record.phong_id.id),
                ("trang_thai", "=", "đang_sử_dụng"),
                ("id", "!=", record.id)
            ])
            if kiem_tra_phong:
                raise exceptions.UserError(f"Phòng {record.phong_id.name} hiện đang được sử dụng.")
            record.write({
                "trang_thai": "đang_sử_dụng",
                "thoi_gian_muon_thuc_te": datetime.now()
            })
            self.lich_su(record)
            
            # Mức 2: Trừ số lượng thiết bị mượn
            for chi_tiet in record.chi_tiet_muon_thiet_bi_ids:
                if chi_tiet.so_luong_muon > chi_tiet.thiet_bi_id.so_luong:
                    raise ValidationError(f"Thiết bị '{chi_tiet.thiet_bi_id.name}' không đủ số lượng để mượn (hiện còn {chi_tiet.thiet_bi_id.so_luong}).")
                chi_tiet.thiet_bi_id.so_luong -= chi_tiet.so_luong_muon
                if chi_tiet.thiet_bi_id.so_luong == 0:
                    chi_tiet.thiet_bi_id.trang_thai = 'dang_su_dung'

            # Logic cũ nếu không có thiết bị chi tiết
            if not record.chi_tiet_muon_thiet_bi_ids:
                thiet_bi_trong_phong = record.phong_id.thiet_bi_ids.filtered(lambda t: t.trang_thai == 'san_sang')
                if thiet_bi_trong_phong:
                    thiet_bi_trong_phong.write({'trang_thai': 'dang_su_dung'})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Đã nhận phòng',
                'message': 'Bắt đầu tính thời gian sử dụng phòng.',
                'type': 'success',
                'sticky': False,
            }
        }

    def tra_phong(self):
        for record in self:
            if record.trang_thai != "đang_sử_dụng":
                raise exceptions.UserError("Chỉ có thể trả phòng đang ở trạng thái 'Đang sử dụng'.")
            current_time = datetime.now()
            record.write({
                "trang_thai": "đã_trả",
                "thoi_gian_tra_thuc_te": current_time,
                "thoi_gian_muon_thuc_te": record.thoi_gian_muon_thuc_te or current_time
            })
            self.lich_su(record)

            # Trả số lượng thiết bị
            for chi_tiet in record.chi_tiet_muon_thiet_bi_ids:
                chi_tiet.thiet_bi_id.so_luong += chi_tiet.so_luong_muon
                chi_tiet.thiet_bi_id.trang_thai = 'san_sang'

            # Logic cũ nếu không có thiết bị chi tiết
            if not record.chi_tiet_muon_thiet_bi_ids:
                thiet_bi_dang_dung = record.phong_id.thiet_bi_ids.filtered(lambda t: t.trang_thai == 'dang_su_dung')
                if thiet_bi_dang_dung:
                    thiet_bi_dang_dung.write({'trang_thai': 'san_sang'})
                    
        # Cập nhật bảng dữ liệu lịch sử mượn trả
        self.env["lich_su_muon_tra"].update_lich_su_muon_tra()

        thoi_gian_muon = self._get_local_time_str(record.thoi_gian_muon_thuc_te)
        thoi_gian_tra = self._get_local_time_str(record.thoi_gian_tra_thuc_te)
        msg = (
            f"🏠 *TRẢ PHÒNG THÀNH CÔNG: {record.phong_id.name}*\n"
            f"👤 Người mượn: {record.nguoi_muon_id.name}\n"
            f"🕒 Giờ Check-in: {thoi_gian_muon}\n"
            f"🕰 Giờ Check-out: {thoi_gian_tra}\n"
            f"✅ Trạng thái: Phòng dọn xong, thiết bị trả đủ."
        )
        self._send_telegram_notification(msg)
        self._notify_ai_session(record, f"🏠 Bạn đã **trả phòng {record.phong_id.name}** thành công. Cảm ơn bạn!")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Trả phòng hoàn tất',
                'message': 'Phòng và các thiết bị đã được thu hồi!',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def lich_su(self, record):
        self.env["lich_su_thay_doi"].create({
            "dat_phong_id": record.id,
            "nguoi_muon_id": record.nguoi_muon_id.id,
            "thoi_gian_muon_du_kien": record.thoi_gian_muon_du_kien,
            "thoi_gian_muon_thuc_te": record.thoi_gian_muon_thuc_te,
            "thoi_gian_tra_du_kien": record.thoi_gian_tra_du_kien,
            "thoi_gian_tra_thuc_te": record.thoi_gian_tra_thuc_te,
            "trang_thai": record.trang_thai
        })

    def _send_telegram_notification(self, message):
        """ 
        MỨC 3: TÍCH HỢP EXTERNAL API
        Hàm gửi tin nhắn tự động qua Telegram bằng HTTP POST request.
        """
        # BƯỚC 1: ĐIỀN THÔNG TIN TOKEN VÀ CHAT ID CỦA BẠN VÀO ĐÂY SAU KHI TẠO BOT
        BOT_TOKEN = "8188180715:AAEo8OlO7jw4LHLs_mXWjpKXVjRSDwiv8MU"  # Ví dụ: "123456789:ABCDefghIJKlmnOPQRstuVWXyz"
        CHAT_ID = "8481931785"     
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            # Gửi tín hiệu JSON API qua Server Telegram (Giới hạn timeout 5s để Odoo không bị đơ)
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            # Ghi log ẩn thay vì báo lỗi popup để không làm gián đoạn trải nghiệm người dùng Odoo
            pass

    def _notify_ai_session(self, record, message):
        """ Gửi thông báo ngược lại phiên chat AI nếu đơn được tạo từ AI """
        if record.ai_session_id:
            try:
                self.env['ai_chat_message'].sudo().create({
                    'session_id': record.ai_session_id.id,
                    'role': 'assistant',
                    'content': message
                })
            except Exception:
                pass

class ChiTietMuonThietBi(models.Model):
    _name = "chi_tiet_muon_thiet_bi"
    _description = "Chi tiết thiết bị được mượn"

    dat_phong_id = fields.Many2one("dat_phong", string="Đặt phòng", ondelete="cascade")
    thiet_bi_id = fields.Many2one("thiet_bi", string="Thiết bị", required=True)
    so_luong_muon = fields.Integer(string="Số lượng mượn", default=1, required=True)

    @api.constrains('so_luong_muon')
    def _check_so_luong_muon(self):
        for record in self:
            if record.so_luong_muon <= 0:
                raise ValidationError("Số lượng mượn phải lớn hơn 0.")