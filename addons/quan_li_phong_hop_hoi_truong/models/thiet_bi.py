from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ThietBi(models.Model):
    _name = "thiet_bi"
    _description = "Quản lý thiết bị phòng họp"
    _order = "phong_id asc, trang_thai asc"

    name = fields.Char(string="Tên thiết bị", required=True)
    loai_thiet_bi = fields.Selection([
        ('may_chieu', 'Máy chiếu'),
        ('micro', 'Micro'),
        ('loa', 'Loa'),
        ('dieu_hoa', 'Điều hòa'),
        ('may_tinh', 'Máy tính'),
    ], string="Loại thiết bị", required=True)
    so_luong = fields.Integer(string="Số lượng", default=1)
    
    @api.constrains('so_luong')
    def _check_so_luong(self):
        for record in self:
            if record.so_luong < 0:
                raise ValidationError("❌ Số lượng thiết bị không được là số âm.")
            if record.so_luong == 0:
                # Cho phép = 0 (hết hàng) nhưng tự chuyển trạng thái
                if record.trang_thai == 'san_sang':
                    record.trang_thai = 'dang_su_dung'
    
    
    phong_id = fields.Many2one("quan_ly_phong_hop", string="Phòng họp", required=True, ondelete="cascade")
    nguoi_quan_ly_id = fields.Many2one("nhan_vien", string="Người quản lý/Bảo trì")
    
    trang_thai = fields.Selection([
        ('dang_su_dung', 'Đang sử dụng'),
        ('san_sang', 'Sẵn sàng'),
        ('can_bao_tri', 'Cần bảo trì'),
        ('hong', 'Hỏng'),
    ], string="Trạng thái", default="san_sang")

    mo_ta = fields.Text(string="Mô tả")
    
    

    @api.model
    def bao_tri_thiet_bi(self):
        """ Chuyển thiết bị có trạng thái 'Cần bảo trì' thành 'Sẵn sàng' sau khi bảo trì """
        thiet_bi_bao_tri = self.search([('trang_thai', '=', 'can_bao_tri')])
        thiet_bi_bao_tri.write({'trang_thai': 'san_sang'})
