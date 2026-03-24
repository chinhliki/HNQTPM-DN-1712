from odoo import models, fields, api
from datetime import datetime, timedelta

class LichSuMuonTra(models.Model):
    _name = "lich_su_muon_tra"
    _description = "Lịch sử sử dụng phòng họp"
    _order = "ngay_su_dung desc, phong_id asc"

    ngay_su_dung = fields.Date(string="📅 Ngày", required=True, default=fields.Date.today)
    phong_id = fields.Many2one("quan_ly_phong_hop", string="🏢 Phòng", required=True)    
    tong_thoi_gian_su_dung = fields.Char(string="⏳ Tổng thời gian sử dụng", compute="_compute_tong_thoi_gian", store=True)

    chi_tiet_su_dung_ids = fields.Many2many("dat_phong", compute="_compute_chi_tiet_su_dung", string="👥 Chi tiết sử dụng")

    @api.depends('ngay_su_dung', 'phong_id')
    def _compute_chi_tiet_su_dung(self):
        for record in self:
            if not record.ngay_su_dung or not record.phong_id:
                record.chi_tiet_su_dung_ids = False
                continue
                
            matching_records = self.env['dat_phong'].search([
                ('phong_id', '=', record.phong_id.id),
                ('trang_thai', '=', 'đã_trả'),
                ('thoi_gian_muon_thuc_te', '!=', False),
                ('thoi_gian_tra_thuc_te', '!=', False)
            ])
            valid_ids = []
            for m in matching_records:
                if m.thoi_gian_muon_thuc_te.date() <= record.ngay_su_dung <= m.thoi_gian_tra_thuc_te.date():
                    valid_ids.append(m.id)
            record.chi_tiet_su_dung_ids = [(6, 0, valid_ids)]

    @api.depends("chi_tiet_su_dung_ids.thoi_gian_muon_thuc_te", "chi_tiet_su_dung_ids.thoi_gian_tra_thuc_te")
    def _compute_tong_thoi_gian(self):
        """ Tính tổng thời gian sử dụng phòng theo giờ:phút:giây """
        for record in self:
            total_seconds = 0
            for usage in record.chi_tiet_su_dung_ids:
                if usage.thoi_gian_muon_thuc_te and usage.thoi_gian_tra_thuc_te:
                    muon_date = usage.thoi_gian_muon_thuc_te.date()
                    tra_date = usage.thoi_gian_tra_thuc_te.date()

                    if muon_date == record.ngay_su_dung or tra_date == record.ngay_su_dung:
                        delta = usage.thoi_gian_tra_thuc_te - usage.thoi_gian_muon_thuc_te
                        total_seconds += delta.total_seconds()
            
            # Chuyển đổi từ giây thành giờ:phút:giây
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            record.tong_thoi_gian_su_dung = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

    @api.model
    def update_lich_su_muon_tra(self):
        """ Cập nhật dữ liệu lịch sử mượn trả mỗi khi có phòng được trả """
        today = fields.Date.today()
        dat_phong_records = self.env["dat_phong"].search([("trang_thai", "=", "đã_trả"), ("thoi_gian_tra_thuc_te", "!=", False)])

        existing_history = self.search([])
        existing_keys = set((h.ngay_su_dung, h.phong_id.id) for h in existing_history)

        for record in dat_phong_records:
            if not record.thoi_gian_muon_thuc_te or not record.thoi_gian_tra_thuc_te:
                continue
                
            ngay_muon = record.thoi_gian_muon_thuc_te.date()
            ngay_tra = record.thoi_gian_tra_thuc_te.date()

            for n in range((ngay_tra - ngay_muon).days + 1):
                date_to_check = ngay_muon + timedelta(days=n)
                key = (date_to_check, record.phong_id.id)
                
                if key not in existing_keys:
                    self.create({
                        "ngay_su_dung": date_to_check,
                        "phong_id": record.phong_id.id,
                    })
                    existing_keys.add(key)
        
        # Cập nhật lại thời gian theo logic Many2many mới
        all_histories = self.search([])
        all_histories._compute_chi_tiet_su_dung()
        all_histories._compute_tong_thoi_gian()
