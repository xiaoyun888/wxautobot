# logger.py
# 通用日志模块：控制台输出 + 内存缓存（web 用）+ 本地文件记录
# 可被主程序与插件 import 复用
from datetime import datetime
import os
import threading

LOG_PATH = "./logs"
_lock = threading.Lock()

# 内存中的最近日志（可供 web 前端读取）
log_messages = []

# 限制内存日志条数
MAX_MEM_LOG = 2000

def log_server(level, msg):
    """
    将日志写到内存缓存（供 web 页面读取）并输出到控制台。
    level: "INFO","ERROR","WARNING","DEBUG","SUCCESS"
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = {
        'time': timestamp,
        'level': level,
        'message': msg
    }
    with _lock:
        log_messages.append(entry)
        if len(log_messages) > MAX_MEM_LOG:
            log_messages.pop(0)
    # 控制台输出
    print(f"[{timestamp}] [{level}] {msg}")

def write_file(msg):
    """将单行日志写入文件（按天分文件）"""
    try:
        now_day = datetime.now().strftime("%y%m%d")
        if not os.path.exists(LOG_PATH):
            os.makedirs(LOG_PATH, exist_ok=True)
        with open(os.path.join(LOG_PATH, f'log_{now_day}.txt'), 'a', encoding='utf-8') as f:
            f.write(msg + '\n')
    except Exception as e:
        print("logger write file error:", e)

def log(level="INFO", message=''):
    """
    统一日志接口，主程序与插件请调用此函数。
    level: INFO/WARNING/ERROR/DEBUG/SUCCESS
    """
    timestamp = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    full = f"{timestamp} [{level}] {message}"
    log_server(level, message)
    try:
        write_file(full)
    except Exception:
        pass

# 读取内存缓存（web 前端可调用）
def get_recent_logs(limit=200):
    with _lock:
        return log_messages[-limit:]