
import json
import logging
import requests
from app.config import settings
logger = logging.getLogger(__name__)

class WeWorkService:
    """企业微信（WeWork）消息推送服务"""

    def __init__(self):
        self.webhook_url = settings.wechat_webhook_url
        if not self.webhook_url:
            logger.error('企业微信 webhook URL 未配置，推送功能不可用')

    def send_message(self, content: str, mentioned_user: str = None) -> dict:
        """向企业微信机器人推送文本消息

        Args:
            content: 消息正文
            mentioned_user: 可选的被@用户的username（企业微信内部）
        Returns:
            dict: {"success": bool, "status_code": int, "message": str}
        """
        if not self.webhook_url:
            return {"success": False, "status_code": 500, "message": '未配置 webhook'}
        payload = {
            "msgtype": "text",
            "text": {"content": content},
        }
        if mentioned_user:
            payload["text"]["mentioned_list"] = [mentioned_user]
        try:
            print(f"[WeWork] Sending to URL: {self.webhook_url[:50]}...")
            print(f"[WeWork] Payload: {payload}")
            resp = requests.post(self.webhook_url, json=payload, timeout=5)
            print(f"[WeWork] Response status: {resp.status_code}, body: {resp.text}")
            if resp.status_code == 200:
                logger.info(f'企业微信消息发送成功: {content[:30]}...')
                return {"success": True, "status_code": 200, "message": '发送成功'}
            else:
                logger.error(f'企业微信推送失败, 状态码 {resp.status_code}, 响应: {resp.text}')
                return {"success": False, "status_code": resp.status_code, "message": resp.text}
        except Exception as e:
            logger.exception('企业微信发送异常')
            return {"success": False, "status_code": 500, "message": str(e)}
