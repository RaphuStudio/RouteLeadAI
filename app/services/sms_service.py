import os
import logging

logger = logging.getLogger(__name__)

try:
    from alibabacloud_dysmsapi20221027.client import Client
    from alibabacloud_dysmsapi20221027.models import SendSmsRequest
    ALI_SDK_AVAILABLE = True
except ImportError:
    ALI_SDK_AVAILABLE = False
    logger.warning('未安装阿里云短信SDK, 如需使用短信功能请安装 alibabacloud-dysmsapi20221027')

class SMSService:
    """阿里云短信服务 (Aliyun SMS)"""

    def __init__(self):
        if not ALI_SDK_AVAILABLE:
            logger.error('阿里云短信SDK未安装')
            self.client = None
            return
        access_key_id = os.getenv('ALI_ACCESS_KEY')
        access_key_secret = os.getenv('ALI_SECRET_KEY')
        if not access_key_id or not access_key_secret:
            logger.error('阿里云AccessKey未配置')
            self.client = None
            return
        try:
            from alibabacloud_tea_openapi import models as open_api_models
            config = open_api_models.Config(
                access_key_id=access_key_id,
                access_key_secret=access_key_secret
            )
            # 默认地域
            endpoint = os.getenv('ALI_ENDPOINT', 'dysmsapi.aliyuncs.com')
            config.endpoint = endpoint
            self.client = Client(config)
        except Exception as e:
            logger.exception('阿里云SMS客户端初始化失败')
            self.client = None

    def send_template(
        self,
        phone_number: str,
        template_code: str,
        template_params: dict,
        sign_name: str = None
    ) -> dict:
        """发送模板短信

        Args:
            phone_number: 手机号（多个以英文逗号分隔）
            template_code: 短信模板CODE
            template_params: 模板变量，字典形式
            sign_name: 签名名称 (默认从环境变量读取 ALI_SIGN_NAME)
        Returns:
            dict: {"success": bool, "status_code": int, "message": str, "biz_id": str | None}
        """
        if not self.client:
            return {"success": False, "status_code": 500, "message": 'SMS服务未就绪', "biz_id": None}

        if not sign_name:
            sign_name = os.getenv('ALI_SIGN_NAME', '')

        request = SendSmsRequest()
        request.phone_numbers = phone_number
        request.sign_name = sign_name
        request.template_code = template_code
        import json
        request.template_param = json.dumps(template_params)

        try:
            response = self.client.send_sms(request)
            body = response.to_map()
            code = body.get('body', {}).get('code')
            message = body.get('body', {}).get('message')
            biz_id = body.get('body', {}).get('biz_id')

            if code == 'OK':
                logger.info(f'短信发送成功: {phone_number}, bizId: {biz_id}')
                return {"success": True, "status_code": 200, "message": message, "biz_id": biz_id}
            else:
                logger.error(f'短信发送失败: {phone_number}, code={code}, message={message}')
                return {"success": False, "status_code": 200, "message": f'{code}: {message}', "biz_id": biz_id}
        except Exception as e:
            logger.exception('阿里云SMS调用异常')
            return {"success": False, "status_code": 500, "message": str(e), "biz_id": None}
