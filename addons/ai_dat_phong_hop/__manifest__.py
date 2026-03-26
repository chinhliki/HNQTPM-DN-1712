{
    'name': 'AI Đặt Phòng Họp (Gemini)',
    'version': '1.0',
    'category': 'Extra Tools',
    'summary': 'Tư vấn và hỗ trợ đặt phòng họp sử dụng Google Gemini AI',
    'description': """
        Module này tích hợp Google AI Studio (Gemini) để:
        - Chat hỗ trợ tìm phòng họp phù hợp.
        - Tự động lấy thông tin từ cuộc hội thoại để gợi ý đặt phòng.
        - Xác nhận và tạo hồ sơ đặt phòng nhanh chóng.
    """,
    'author': 'Antigravity AI Assistant',
    'depends': ['base', 'quan_li_phong_hop_hoi_truong', 'nhan_su'],
    'data': [
        'security/ir.model.access.csv',
        'views/ai_dat_phong_view.xml',
    ],
    'installable': True,
    'application': True,
}
