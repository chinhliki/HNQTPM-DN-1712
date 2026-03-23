from odoo import models, fields, api

class PhongBan(models.Model):
    _name = 'phong_ban'
    _description = 'Bảng chứa thông tin phòng ban'
    _rec_name = 'ten_phong_ban' # Nâng cấp hiển thị

    ma_phong_ban = fields.Char("Mã phòng ban", required=True)
    ten_phong_ban = fields.Char("Tên phòng ban", required=True)
    mo_ta = fields.Text("Mô tả")
    # Tự động đếm nhân viên dựa trên các chức vụ thuộc phòng này
    so_nhan_vien = fields.Integer("Số nhân viên", compute="_compute_so_nhan_vien", store=True)

    @api.depends('ma_phong_ban')
    def _compute_so_nhan_vien(self):
        for record in self:
            chuc_vu_ids = self.env['chuc_vu'].search([('phong_ban_id', '=', record.id)])
            record.so_nhan_vien = self.env['nhan_vien'].search_count([('chuc_vu_id', 'in', chuc_vu_ids.ids)])