from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re

class NhanVien(models.Model):
    _name = 'nhan_vien'
    _description = 'Bảng chứa thông tin nhân viên'

    name = fields.Char("Tên nhân viên", required=True)
    ma_dinh_danh = fields.Char("Mã định danh", required=True)
    ngay_sinh = fields.Date("Ngày sinh")
    que_quan = fields.Char("Quê quán")
    email = fields.Char("Email")
    so_dien_thoai = fields.Char("Số điện thoại")
    chuc_vu_id = fields.Many2one("chuc_vu", string="Chức vụ")
    lich_su_cong_tac_ids = fields.One2many("lich_su_cong_tac", inverse_name="nhan_vien_id", string="Lịch sử công tác")

    @api.constrains('email')
    def _check_email(self):
        for record in self:
            if record.email and not re.match(r"[^@]+@[^@]+\.[^@]+", record.email):
                raise ValidationError("Lỗi: Định dạng Email không hợp lệ!")

    @api.constrains('ngay_sinh')
    def _check_ngay_sinh(self):
        for record in self:
            if record.ngay_sinh and record.ngay_sinh > fields.Date.today():
                raise ValidationError("Lỗi: Ngày sinh không thể ở tương lai!")