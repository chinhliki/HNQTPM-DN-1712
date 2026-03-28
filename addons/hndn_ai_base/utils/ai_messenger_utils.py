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
        Gửi yêu cầu đến Gemini API với cơ chế tự động thử lại (retry) khi bị 503/429.
        """
        import time
        if not api_key:
            _logger.error("Gemini API Key is missing!")
            return None
        
        api_key = api_key.strip()
        
        # Dùng gemini-1.5-flash (phiên bản ổn định, ít bị 503 hơn 'latest')
        # Fallback: gemini-1.0-pro nếu 1.5-flash tiếp tục quá tải
        MODELS_TO_TRY = [
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.0-pro",
        ]
        
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': api_key
        }
        parts = [{"text": prompt}]
        if image_data:
            if not isinstance(image_data, str):
                image_data = base64.b64encode(image_data).decode('utf-8')
            parts.append({
                "inline_data": {
                    "mime_type": image_type,
                    "data": image_data
                }
            })
        data = {"contents": [{"parts": parts}]}
        
        for model in MODELS_TO_TRY:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            MAX_RETRIES = 3
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    _logger.info(f"Calling Gemini [{model}] - Attempt {attempt}/{MAX_RETRIES}")
                    response = requests.post(url, headers=headers, json=data, timeout=30)
                    _logger.info(f"Gemini API Response Status: {response.status_code}")
                    
                    # Thành công
                    if response.status_code == 200:
                        result = response.json()
                        if 'candidates' in result and result['candidates']:
                            return result['candidates'][0]['content']['parts'][0]['text']
                        _logger.warning(f"Gemini [{model}] returned no candidates: {result}")
                        return None
                    
                    # 503 / 429: Server quá tải → đợi rồi thử lại
                    if response.status_code in (503, 429):
                        wait_sec = 2 * attempt  # 2s, 4s, 6s
                        _logger.warning(f"Gemini [{model}] {response.status_code} - Retrying in {wait_sec}s...")
                        time.sleep(wait_sec)
                        continue
                    
                    # Lỗi khác → thử model tiếp theo
                    _logger.error(f"Gemini [{model}] Error {response.status_code}: {response.text}")
                    break

                except Exception as e:
                    _logger.error(f"Gemini [{model}] Exception: {str(e)}")
                    break
        
        _logger.error("Tất cả model Gemini đều không phản hồi được. Vui lòng thử lại sau.")
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
