from logging import Formatter
from datetime import datetime, timezone, timedelta


class ISO8601Formatter(Formatter):
    """自定义 Formatter：输出 ISO 8601 格式带时区（CST +08:00）"""
    def formatTime(self, record, datefmt=None):
        # 系统时间已是 CST（UTC+8），直接格式化并添加 +08:00
        dt = datetime.fromtimestamp(record.created, tz=timezone(timedelta(hours=8)))
        return dt.strftime('%Y-%m-%dT%H:%M:%S+08:00')
