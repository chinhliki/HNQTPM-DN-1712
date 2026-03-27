# -*- coding: utf-8 -*-
import requests
import json
import base64
import logging

_logger = logging.getLogger(__name__)

class AIMessengerUtils:
    
    @staticmethod
    def get_gemini_response(api_key, prompt, image_data=None, image_type='image/jpeg'):
        """
        Gửi yêu cầu đến Gemini API.
        """
        if not api_key:
            _logger.error("Gemini API Key is missing!")
            return None
        
        api_key = api_key.strip()
        
        # Sử dụng v1beta và model gemini-flash-latest theo KHỚP CHÍNH XÁC curl của người dùng
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': api_key
        }
        parts = [{"text": prompt}]
        if image_data:
            # Nếu là byte, chuyển sang base64 string
            if not isinstance(image_data, str):
                image_data = base64.b64encode(image_data).decode('utf-8')
            
            parts.append({
                "inline_data": {
                    "mime_type": image_type,
                    "data": image_data
                }
            })
        data = {"contents": [{"parts": parts}]}
        
        try:
            _logger.info(f"Calling Gemini API with URL: {url}")
            response = requests.post(url, headers=headers, json=data, timeout=30)
            _logger.info(f"Gemini API Response Status: {response.status_code}")
            
            if response.status_code != 200:
                _logger.error(f"Gemini API Error {response.status_code}: {response.text}")
                return None
            result = response.json()
            if 'candidates' in result and result['candidates']:
                return result['candidates'][0]['content']['parts'][0]['text']
            
            if 'error' in result:
                _logger.error(f"Gemini API returned an error: {result['error']}")
            else:
                _logger.warning(f"Gemini returned no candidates: {result}")
            return None
        except Exception as e:
            _logger.error(f"Unexpected error calling Gemini API: {str(e)}")
            import traceback
            _logger.error(traceback.format_exc())
            return None

    @staticmethod
    def send_telegram_notification(token, chat_id, message):
        """
        Gửi tin nhắn thông báo qua Telegram Bot.
        Trả về: (True, "Success") hoặc (False, "Error message")
        """
        if not token or not chat_id:
            return False, "Thiếu Token hoặc Chat ID!"
            
        url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
        data = {
            'chat_id': chat_id.strip(),
            'text': message,
            'parse_mode': 'HTML'
        }
        
        try:
            _logger.info(f"Sending Telegram notification to Chat ID: {chat_id}")
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                _logger.info("Telegram notification sent successfully.")
                return True, "Thành công"
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('description', response.text)
                _logger.error(f"Telegram API Error {response.status_code}: {error_msg}")
                return False, f"Telegram API Error {response.status_code}: {error_msg}"
        except Exception as e:
            _logger.error(f"Unexpected error sending Telegram notification: {str(e)}")
            return False, f"Lỗi kết nối: {str(e)}"
