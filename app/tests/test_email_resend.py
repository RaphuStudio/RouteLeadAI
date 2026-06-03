"""
独立邮件测试脚本 - 用于快速验证 Resend API 配置

功能：
  1. 从 .env 文件加载环境变量
  2. 测试 EmailService.send_email() 方法
  3. 提供清晰的测试输出

使用方法：
  # 基本用法（使用 .env 中的配置）
  python -m app.tests.test_email_resend

  # 指定收件人
  python -m app.tests.test_email_resend --to test@example.com

  # 使用自定义 .env 文件
  python -m app.tests.test_email_resend --env /path/to/.env

  # 跳过 .env 加载（使用系统环境变量）
  python -m app.tests.test_email_resend --no-dotenv
"""

import argparse
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

from app.services.email_service import EmailService


def load_env_file(env_path: str = None, use_dotenv: bool = True):
    """
    加载环境变量配置文件

    Args:
        env_path: .env 文件路径，默认为项目根目录下的 .env
        use_dotenv: 是否使用 python-dotenv 加载
    """
    if not use_dotenv:
        print("⚠️  跳过 .env 文件加载，使用系统环境变量")
        return

    if not DOTENV_AVAILABLE:
        print("⚠️  python-dotenv 未安装，尝试手动加载 .env 文件")
        if env_path is None:
            env_path = PROJECT_ROOT / ".env"
        if os.path.exists(env_path):
            print(f"📂 手动加载环境变量: {env_path}")
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        try:
                            key, value = line.split("=", 1)
                            os.environ[key.strip()] = value.strip()
                        except ValueError:
                            pass
        return

    if env_path is None:
        env_path = PROJECT_ROOT / ".env"
    else:
        env_path = Path(env_path)

    if env_path.exists():
        print(f"📂 加载环境变量: {env_path}")
        load_dotenv(dotenv_path=env_path)
    else:
        print(f"⚠️  .env 文件不存在: {env_path}")
        print("   将使用系统环境变量")


def check_configuration():
    """
    检查必要的环境变量配置

    Returns:
        tuple: (是否配置完整, 缺失的配置列表)
    """
    required_vars = ["RESEND_API_KEY", "EMAIL_FROM"]
    missing = [var for var in required_vars if not os.getenv(var)]

    return len(missing) == 0, missing


def test_email_sending(to_email: str = None):
    """
    测试邮件发送功能

    Args:
        to_email: 收件人邮箱，如果为 None 则使用 TEST_EMAIL 或默认值

    Returns:
        dict: 发送结果
    """
    # 检查配置
    config_ok, missing = check_configuration()
    if not config_ok:
        print(f"❌ 配置不完整，缺少环境变量: {', '.join(missing)}")
        print("   请检查 .env 文件或系统环境变量")
        return {"success": False, "error": "配置不完整"}

    print(f"✅ 配置检查通过")
    print(f"   发件人: {os.getenv('EMAIL_FROM')}")
    print(f"   API Key: {os.getenv('RESEND_API_KEY')[:10]}...（已脱敏）")
    print()

    # 确定收件人
    if to_email is None:
        to_email = os.getenv("TEST_EMAIL", "hejibo061@gmail.com")
        print(f"⚠️  未指定收件人，使用默认: {to_email}")
        print("   可通过 --to 参数指定收件人")
    else:
        print(f"📧 收件人: {to_email}")

    print()

    # 创建邮件服务实例
    email_service = EmailService()

    # 测试邮件内容
    subject = "【测试】Resend API 邮件发送测试"
    content = """
尊敬的测试用户：

您好！

这是一封来自 AI Sales Follow-up System 的测试邮件。

【测试信息】
• 发送时间: 2026-05-03
• 测试目的: 验证 Resend API 配置
• 邮件服务: Resend

【测试结果】
如果您收到这封邮件，说明 Resend API 配置正确，邮件发送功能正常工作。

---
AI Sales Follow-up System
测试脚本自动发送
"""

    print("📤 正在发送测试邮件...")
    print(f"   主题: {subject}")
    print(f"   内容长度: {len(content)} 字符")
    print()

    # 发送邮件
    result = email_service.send_email(to_email, subject, content)

    print("📬 发送结果:")
    print(f"   成功状态: {result.get('success')}")
    print(f"   状态码: {result.get('status_code')}")
    print(f"   消息: {result.get('message')}")
    print()

    if result.get("success"):
        print("✅ 邮件发送成功！请检查收件箱（包括垃圾邮件文件夹）")
    else:
        print("❌ 邮件发送失败")
        print(f"   错误详情: {result.get('message')}")

    return result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Resend 邮件发送测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m app.tests.test_email_resend
  python -m app.tests.test_email_resend --to your@email.com
  python -m app.tests.test_email_resend --env /path/to/.env --to test@example.com
        """
    )
    parser.add_argument(
        "--to",
        type=str,
        default=None,
        help="收件人邮箱地址（默认: 使用 TEST_EMAIL 环境变量或 test@example.com）"
    )
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        help=".env 文件路径（默认: 项目根目录下的 .env）"
    )
    parser.add_argument(
        "--no-dotenv",
        action="store_true",
        help="跳过 .env 文件加载，使用系统环境变量"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("📧 Resend 邮件发送测试工具")
    print("=" * 60)
    print()

    # 加载环境变量
    load_env_file(env_path=args.env, use_dotenv=not args.no_dotenv)

    print()

    # 执行测试
    result = test_email_sending(to_email=args.to)

    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)

    # 返回适当的退出码
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
