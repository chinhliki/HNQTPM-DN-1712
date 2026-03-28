# -*- coding: utf-8 -*-
import requests
import json
import base64
import logging
import time

_logger = logging.getLogger(__name__)

class AIMessengerUtils:

    # ✅ Cấu hình chuẩn: v1 + gemini-2.5-flash
    GEMINI_MODEL = "gemini-2.5-flash"
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/{model}:generateContent"

    @staticmethod
    def get_gemini_response(api_key, prompt, image_data=None, image_type='image/jpeg'):
        """
        Gửi yêu cầu đến Gemini API với retry tự động.
        - Endpoint: v1 (ổn định)
        - Model: gemini-2.5-flash
        - Xử lý lỗi: 400, 404, 429 (quota)
        """
        if not api_key:
            _logger.error("Gemini API Key is missing!")
            return None

        api_key = api_key.strip()
        url = AIMessengerUtils.GEMINI_API_URL.format(model=AIMessengerUtils.GEMINI_MODEL)

        headers = {"Content-Type": "application/json"}
        params = {"key": api_key}  # ✅ API key qua params, không để trong header

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

        payload = {"contents": [{"parts": parts}]}

        # Retry tối đa 2 lần (xử lý 429 quota tạm thời)
        for attempt in range(3):
            try:
                _logger.info(f"Calling Gemini API [{AIMessengerUtils.GEMINI_MODEL}] - Attempt {attempt + 1}")
                response = requests.post(url, headers=headers, params=params, json=payload, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and result['candidates']:
                        return result['candidates'][0]['content']['parts'][0]['text']
                    _logger.warning(f"Gemini returned no candidates: {result}")
                    return None

                elif response.status_code == 429:
                    # Quota exceeded - đợi rồi thử lại
                    wait = 2 ** attempt  # 1s, 2s, 4s
                    _logger.warning(f"Gemini quota exceeded (429), retrying in {wait}s...")
                    time.sleep(wait)
                    continue

                elif response.status_code == 404:
                    _logger.error(f"Gemini model not found (404): {AIMessengerUtils.GEMINI_MODEL}")
                    return None

                else:
                    _logger.error(f"Gemini API Error {response.status_code}: {response.text}")
                    return None

            except requests.exceptions.Timeout:
                _logger.error(f"Gemini API timeout (attempt {attempt + 1})")
                if attempt < 2:
                    time.sleep(1)
                    continue
                return None
            except Exception as e:
                _logger.error(f"Unexpected error calling Gemini API: {str(e)}")
                import traceback
                _logger.error(traceback.format_exc())
                return None

        _logger.error("Gemini API failed after 3 attempts")
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
