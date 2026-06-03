
import json
import logging
import requests
import hmac
import hashlib
import base64
import time
from app.config import settings
logger = logging.getLogger(__name__)

class DingTalkService:
    """钉钉机器人消息推送服务

    支持两种方式:
      1) 明文 webhook URL (直接拼接 access_token)
      2) 签名校验方式 (webhook + secret)
    """

    def __init__(self):
        # 方式1: 纯 webhook (环境变量 DINGTALK_WEBHOOK_URL)
        self.webhook_url = settings.dingtalk_webhook_url
        # 方式2: webhook+secret (环境变量 DINGTALK_WEBHOOK + DINGTALK_SECRET)
        self.webhook = settings.dingtalk_webhook
        self.secret = settings.dingtalk_secret

    @staticmethod
    def _sign(secret: str, timestamp: str) -> str:
        """计算钉钉签名"""
        string_to_sign = f'{timestamp}\n{secret}'
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(hmac_code).decode()

    def _build_webhook_url(self) -> str:
        """构造带签名的 webhook URL (若有 secret)"""
        if self.secret and self.webhook:
            ts = str(round(time.time() * 1000))
            sign = self._sign(self.secret, ts)
            return f"{self.webhook}&timestamp={ts}&sign={sign}"
        elif self.webhook:
            return self.webhook
        else:
            return self.webhook_url  # 可能是完整URL或None

    def send_text(self, content: str, at_mobiles=None, at_all=False) -> dict:
        """发送文本消息

        Args:
            content: 消息文本
            at_mobiles: 被@人的手机号列表
            at_all: 是否@所有人
        Returns:
            dict: {"success": bool, "status_code": int, "message": str}
        """
        url = self._build_webhook_url()
        if not url:
            logger.error('钉钉 webhook 未配置，推送功能不可用')
            return {"success": False, "status_code": 500, "message": '未配置 webhook'}

        payload = {"msgtype": "text", "text": {"content": content}}
        if at_mobiles or at_all:
            payload["at"] = {}
            if at_mobiles:
                payload["at"]["atMobiles"] = at_mobiles
            payload["at"]["isAtAll"] = at_all

        try:
            print(f"[DingTalk] Sending to URL: {url[:50]}...")
            print(f"[DingTalk] Payload: {payload}")
            resp = requests.post(url, json=payload, timeout=5)
            print(f"[DingTalk] Response status: {resp.status_code}, body: {resp.text}")
            if resp.status_code == 200:
                body = resp.json()
                err = body.get('errcode')
                if err == 0:
                    logger.info(f'钉钉消息发送成功: {content[:30]}...')
                    return {"success": True, "status_code": 200, "message": '发送成功'}
                else:
                    logger.error(f'钉钉接口异常: {body}')
                    return {"success": False, "status_code": 200, "message": body}
            else:
                logger.error(f'钉钉推送失败, 状态码 {resp.status_code}, 响应: {resp.text}')
                return {"success": False, "status_code": resp.status_code, "message": resp.text}
        except Exception as e:
            logger.exception('钉钉发送异常')
            return {"success": False, "status_code": 500, "message": str(e)}
