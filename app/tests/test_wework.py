"""
企业微信（WeWork）机器人 Webhook 推送测试
使用方法：
  cd /Users/hejibo/2409/project/Deploy_and_Use/ai_sales_followup_system
  source .venv/bin/activate
  python app/tests/test_wework.py
"""
import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

from app.services.wework_service import WeWorkService

def main():
    print("=" * 60)
    print("企业微信（WeWork）机器人 Webhook 推送测试")
    print("=" * 60)

    # 检查配置
    webhook_url = os.getenv('WECHAT_WEBHOOK_URL')
    print(f"\n[配置检查]")
    print(f"  WECHAT_WEBHOOK_URL: {'已配置' if webhook_url else '未配置'}")
    if webhook_url:
        # 仅显示部分 URL 避免泄露
        masked = webhook_url[:40] + "..." if len(webhook_url) > 40 else webhook_url
        print(f"  URL (脱敏): {masked}")

    service = WeWorkService()

    # 测试: 发送文本消息
    print(f"\n[测试] 发送文本消息...")
    content = (
        "【AI Sales Follow-up System】\n"
        "企业微信机器人测试消息\n"
        f"发送时间：2026-05-04\n"
        "如果您看到此消息，说明配置正确！"
    )
    result = service.send_message(content)
    print(f"  结果: {result}")

    print(f"\n{'=' * 60}")
    print("测试完成")
    print(f"{'=' * 60}")

if __name__ == '__main__':
    main()
