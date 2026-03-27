# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hndn_gemini_api_key = fields.Char(
        string="Gemini API Key",
        config_parameter='hndn_ai_base.hndn_gemini_api_key',
        help="API Key cho Gemini AI."
    )

    def action_test_gemini_connection(self):
        """
        Kiểm tra kết nối tới Gemini API.
        """
        self.ensure_one()
        api_key = self.hndn_gemini_api_key or self.env['ir.config_parameter'].sudo().get_param('hndn_ai_base.hndn_gemini_api_key')
        if not api_key:
            raise models.ValidationError("Vui lòng nhập Gemini API Key trước khi kiểm tra!")
        
        from odoo.addons.hndn_ai_base.utils.ai_messenger_utils import AIMessengerUtils
        response = AIMessengerUtils.get_gemini_response(api_key.strip(), "Kiểm tra kết nối. Hãy trả lời 'OK' nếu bạn nhận được tin nhắn này.")
        
        if response:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thành công',
                    'message': f'Kết nối Gemini AI thành công! Phản hồi: {response}',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise models.ValidationError("Kết nối thất bại! Vui lòng kiểm tra lại API Key hoặc kết nối mạng của máy chủ.")
