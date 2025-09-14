# plugins/weather_plugin.py
"""
天气查询插件
功能说明：
- 支持模糊指令：查天气、天气查询、xxx天气、天气xxx等
- 调用天气API获取实时天气
- 支持城市名自动提取
- 友好的结果展示格式
"""

import time
import re
import random
import requests
import os
import logging
from datetime import datetime
import threading

# -------------------------------
# 插件配置
# -------------------------------
WEATHER_ENABLED = 1  # 插件总开关（1=启用，0=禁用）
WEATHER_API_KEY = "03e026a2b5e80e8bccea7ba69d5618dc"  # 需要自行申请
WEATHER_API_URL = "https://restapi.amap.com/v3/weather/weatherInfo"  # 高德天气API示例

# -------------------------------
# 提示语 / 表情配置
# -------------------------------
QUERY_PROMPTS = [
    "🌤️ 正在查询「{city}」的天气，稍等片刻...",
    "📅 马上为你获取「{city}」的天气信息～",
    "🌡️ 正在调取「{city}」的气象数据..."
]

WEATHER_EMOJI = {
    "晴": "☀️",
    "多云": "⛅",
    "阴": "☁️",
    "雨": "🌧️",
    "雪": "❄️",
    "风": "💨",
    "雾": "🌫️"
}

ERROR_MESSAGES = [
    "❌ 未查询到「{city}」的天气信息，请检查城市名是否正确",
    "⚠️ 无法获取「{city}」的天气数据，请稍后再试",
    "🔍 没有找到「{city}」的天气记录，换个城市名试试？"
]


# -------------------------------
# 日志配置
# -------------------------------
def init_logger():
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"weather_plugin_{datetime.now().strftime('%Y%m%d')}.log")

    logger = logging.getLogger("weather_plugin")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(fmt)

    if not logger.handlers:
        logger.addHandler(fh)

    return logger


weather_logger = init_logger()


def plugin_log(message, level="INFO"):
    """同时写入插件日志和主程序日志"""
    try:
        from wxbot_class_only_V2 import log as main_log
        main_log(message, level=level)
    except Exception:
        pass

    if level == "ERROR":
        weather_logger.error(message)
    else:
        weather_logger.info(message)


# -------------------------------
# 天气查询核心函数
# -------------------------------
def get_weather(city):
    """调用天气API获取天气信息"""
    if not WEATHER_API_KEY:
        return "⚠️ 天气API未配置，请联系管理员"

    try:
        params = {
            "key": WEATHER_API_KEY,
            "city": city,
            "extensions": "base",  # 基础天气
            "output": "json"
        }

        response = requests.get(WEATHER_API_URL, params=params, timeout=10)
        data = response.json()

        if data.get("status") != "1":
            return random.choice(ERROR_MESSAGES).format(city=city)

        # 解析天气数据
        lives = data.get("lives", [])
        if not lives:
            return random.choice(ERROR_MESSAGES).format(city=city)

        weather_data = lives[0]
        weather = weather_data.get("weather", "未知")
        temperature = weather_data.get("temperature", "未知")
        winddirection = weather_data.get("winddirection", "未知")
        windpower = weather_data.get("windpower", "未知")
        humidity = weather_data.get("humidity", "未知")
        reporttime = weather_data.get("reporttime", "未知")

        # 选择合适的表情
        emoji = "🌤️"
        for key, val in WEATHER_EMOJI.items():
            if key in weather:
                emoji = val
                break

        # 格式化输出
        result = f"{emoji} 「{city}」天气信息\n"
        result += f"天气状况：{weather} {emoji}\n"
        result += f"温度：{temperature}℃\n"
        result += f"风向：{winddirection}\n"
        result += f"风力：{windpower}级\n"
        result += f"湿度：{humidity}%\n"
        result += f"更新时间：{reporttime}"

        return result

    except Exception as e:
        plugin_log(f"天气查询API调用失败: {str(e)}", "ERROR")
        return f"❌ 查询天气时发生错误：{str(e)}"


# -------------------------------
# 指令处理线程
# -------------------------------
def weather_query_thread(chat, city, is_group_chat=False, sender=None):
    """天气查询线程"""
    # 发送查询提示
    prompt = random.choice(QUERY_PROMPTS).format(city=city)
    try:
        if is_group_chat and sender:
            chat.SendMsg(msg=prompt, at=sender)
        else:
            chat.SendMsg(prompt)
    except Exception as e:
        plugin_log(f"发送查询提示失败: {e}", "ERROR")
        return

    # 获取天气信息
    weather_info = get_weather(city)

    # 发送结果
    try:
        if is_group_chat and sender:
            chat.SendMsg(msg=weather_info, at=sender)
        else:
            chat.SendMsg(weather_info)
    except Exception as e:
        plugin_log(f"发送天气信息失败: {e}", "ERROR")


# -------------------------------
# 模糊指令匹配
# -------------------------------
def extract_city(content):
    """从消息中提取城市名和判断是否为天气查询指令"""
    content = content.strip()

    # 天气相关关键词
    weather_keywords = ["天气", "气温", "温度", "预报"]

    # 检查是否包含天气相关关键词
    has_weather_keyword = any(keyword in content for keyword in weather_keywords)
    if not has_weather_keyword:
        return False, None

    # 移除指令关键词，提取城市名
    # 替换所有天气关键词为空
    city_pattern = re.sub(r"天气|气温|温度|预报|查|查询|看", "", content).strip()

    # 如果提取结果不为空，则视为城市名
    if city_pattern:
        return True, city_pattern

    # 特殊情况处理：只有"天气"两个字（可能需要默认城市）
    if content in ["天气", "查天气", "天气查询"]:
        return True, "北京"  # 可改为配置的默认城市

    return False, None


# -------------------------------
# 插件核心接口
# -------------------------------
PLUGIN_NAME = "weather"
PLUGIN_ENABLED = WEATHER_ENABLED
PLUGIN_PRIORITY = 90  # 优先级低于搜索插件


def check(msg, chat, chat_info):
    """检查是否为天气查询指令"""
    try:
        # 忽略自己发送的消息
        if getattr(msg, "attr", "") == "self":
            return (False, None)

        # 只处理文本消息
        if msg.type != "text":
            return (False, None)

        content = getattr(msg, "content", "").strip()
        if not content:
            return (False, None)

        # 提取城市名并判断是否为天气指令
        matched, city = extract_city(content)
        if matched and city:
            return (True, city)

        return (False, None)
    except Exception as e:
        plugin_log(f"check函数异常: {e}", "ERROR")
        return (False, None)


def handle(msg, chat, chat_info, data):
    """处理天气查询"""
    try:
        city = data  # data是check传递的城市名
        if not city:
            return None

        # 判断是否为群聊
        is_group = chat_info.get("type") == "group"
        sender = chat_info.get("sender", "")

        # 启动线程处理
        threading.Thread(
            target=weather_query_thread,
            args=(chat, city),
            kwargs={"is_group_chat": is_group, "sender": sender},
            daemon=True
        ).start()

        return True
    except Exception as e:
        plugin_log(f"handle函数异常: {e}", "ERROR")
        return None