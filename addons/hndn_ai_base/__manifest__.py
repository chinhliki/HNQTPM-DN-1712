# -*- coding: utf-8 -*-
{
    'name': "HNDN AI Base",
    'summary': "Module nền tảng cho các tính năng AI (Gemini)",
    'description': """
        Cung cấp các công cụ và cấu hình dùng chung cho AI:
        - Cấu hình Gemini API Key.
        - Tiện ích gửi yêu cầu AI (Gemini).
        - Trợ lý ảo AI tập trung.
    """,
    'author': "Antigravity",
    'category': 'Technical',
    'version': '1.0',
    'depends': ['base', 'web', 'base_setup', 'quan_li_phong_hop_hoi_truong', 'nhan_su'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter_data.xml',
        'views/res_config_settings_views.xml',
        'views/ai_assistant_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hndn_ai_base/static/src/css/ai_chat.css',
            'hndn_ai_base/static/src/js/ai_chat/ai_chat_component.js',
        ],
        'web.assets_qweb': [
            'hndn_ai_base/static/src/xml/ai_chat/ai_chat_templates.xml',
        ],
    },
    'installable': True,
    'application': True,
}
