"""
钉钉机器人 Webhook 推送测试
使用方法：
  cd /Users/hejibo/2409/project/Deploy_and_Use/ai_sales_followup_system
  source .venv/bin/activate
  python app/tests/test_dingtalk.py
"""
import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

from app.services.dingtalk_service import DingTalkService

def main():
    print("=" * 60)
    print("钉钉机器人 Webhook 推送测试")
    print("=" * 60)

    # 检查配置
    webhook_url = os.getenv('DINGTALK_WEBHOOK_URL')
    webhook = os.getenv('DINGTALK_WEBHOOK')
    secret = os.getenv('DINGTALK_SECRET')

    print(f"\n[配置检查]")
    print(f"  DINGTALK_WEBHOOK_URL: {'已配置' if webhook_url else '未配置'}")
    print(f"  DINGTALK_WEBHOOK: {'已配置' if webhook else '未配置'}")
    print(f"  DINGTALK_SECRET: {'已配置' if secret else '未配置'}")

    service = DingTalkService()

    # 测试1: 发送普通文本消息
    print(f"\n[测试1] 发送普通文本消息...")
    result = service.send_text("【AI Sales】钉钉机器人测试消息 - 发送时间：2026-05-04")
    print(f"  结果: {result}")

    # 测试2: 发送 @某人 消息（如有手机号可测试）
    print(f"\n[测试2] 发送 @所有人 消息...")
    result = service.send_text("【AI Sales】高意向线索提醒：测试公司请联系！", at_all=True)
    print(f"  结果: {result}")

    print(f"\n{'=' * 60}")
    print("测试完成")
    print(f"{'=' * 60}")

if __name__ == '__main__':
    main()
