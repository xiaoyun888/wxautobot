# plugins/search_plugin.py
"""
资源搜索插件（v2.59）
功能说明：
- 触发指令：全网搜 / 搜资源 / 搜剧 / 搜索 / 看 / 搜 （支持空格与不带空格）
- 调用 API：http://103.38.82.182:2296/api/Tool/Qsearch
- 搜索结果：展示所有 data 条目，格式化排版，带表情
- 提示语：开始搜索提示语（随机），结果头表情、资源表情
- 广告：ad_switch=1 时展示广告（随机一条模板）
- 搜索失败/超时：友好提示（带表情，建议换关键词）
- 用户取用提示：20 条随机文案（可选开关，随机一条）
- 插件开关：SEARCH_ENABLED = 1/0
- 群聊 @ 用户，若 sender=self 则忽略
- 日志：插件日志写入 plugins/logs/search_plugin_xx.log，同时调用主程序 log()
"""

import time
import json
import re
import random
import requests
import os
import logging
from datetime import datetime

# -------------------------------
# 插件配置
# -------------------------------
SEARCH_ENABLED = 1  # 插件总开关（1=启用，0=禁用）

MIN_WAIT_TIME = 30
MAX_WAIT_TIME = 90
SEARCH_TIMEOUT = 120       # API 超时时间
SEARCH_RETRY_COUNT = 2     # 重试次数
AD_URL = "66oo.cc"         # 广告网址
ad_switch = 1              # 广告开关：1=显示广告，0=不显示
SHOW_EXTRACTION_TIP = 1    # 是否显示用户提取提示（1=显示，0=关闭）

SEARCH_API_URL = "http://103.38.82.182:2296/api/Tool/Qsearch"

# -------------------------------
# 提示语 / 表情 / 模板
# -------------------------------
SEARCH_PROMPTS = [
    f"🔍 收到！正在全网捕捉「{{keyword}}」的踪迹～ 大约 {MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒后回来！",
    f"🚀 搜索引擎已点火！星际搜寻「{{keyword}}」，预计 {MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒～",
    f"🕵️‍♀️ 侦探出动！正在寻找「{{keyword}}」的蛛丝马迹，请稍等 {MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒！",
    f"🧙‍♂️ 魔法阵启动，召唤「{{keyword}}」出现中～ {MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒后揭晓！",
    f"🐶 搜索汪嗅探「{{keyword}}」的气味，{MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒后带回来！",
    f"📡 宇宙信号锁定「{{keyword}}」，正在解码中（约 {MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒）...",
    f"🧩 正在拼凑「{{keyword}}」的碎片，还差最后几块拼图（{MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒）...",
    f"🏁 搜索马拉松起跑！全力冲向「{{keyword}}」终点（{MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒）！",
    f"🎭 剧本搜寻中：「{{keyword}}」即将开演，预计 {MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒～",
    f"🔮 水晶球显示「{{keyword}}」的踪迹，画面逐渐清晰（{MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒）...",
    f"🐰 小兔叽跳跳跳去找「{{keyword}}」啦～ {MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒后回来！",
    f"🚗 小车车出发！前往「{{keyword}}」的路上，约 {MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒到达～",
    f"🌐 正在全网漫游寻找「{{keyword}}」，预计 {MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒～",
    f"🐱 搜索喵出动，悄咪咪找「{{keyword}}」，{MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒后汇报！",
    f"🚁 直升机升空，侦查「{{keyword}}」位置中（{MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒）...",
    f"🔬 实验室解析「{{keyword}}」相关数据，预计 {MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒～",
    f"📖 翻阅全网资料库，检索「{{keyword}}」中（{MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒）...",
    f"🧭 导航设定目的地「{{keyword}}」，规划最佳路线中（{MIN_WAIT_TIME}-{MAX_WAIT_TIME} 秒）..."
]

RESOURCE_EMOJIS = ["📌", "🔖", "📝", "💾", "📂", "🎬", "📦", "🎁", "🔗", "📥", "📤", "📎", "📼", "💽", "🎥", "📀", "🔑"]
RESULT_HEADER_EMOJIS = ["🎉", "✨", "🔍", "💫", "🌟", "🎊", "🔮", "💎", "🎁", "💡", "🎈", "🚀"]

AD_TEMPLATES = [
    f"👇 还想要更多精彩资源？悄悄告诉你一个好地方～\n✨ {AD_URL} ✨\n超多惊喜等你！😉",
    f"💡 温馨提示：更多优质资源在 {AD_URL} 哦，快去看看吧！🥳",
    f"🎉 宝藏站点：{AD_URL}，各种好东西别错过～ 😍",
    f"📚 想解锁更多？快上 {AD_URL}，资源丰富不重样！🚀",
    f"🔗 不够看？来 {AD_URL}，新世界等你探索～ 🌍",
    f"🎁 福利时间：{AD_URL}，进去就知道有多精彩！✨",
    f"🌟 特别推荐：{AD_URL}，一定会让你收获满满！😊",
]

SEARCH_FAIL_TEMPLATES = [
    "❌ 没找到相关资源。建议：换个关键词再试一次～",
    "⚠️ 没有搜到结果，可以尝试写完整点，宁写多不写错！",
    "🚫 没有命中该关键词，建议换个词或详细点再搜一次～"
]

SEARCH_TIMEOUT_TEMPLATES = [
    "⏳ 搜索超时啦～稍后再试试吧！",
    "⌛ 这次搜索太久没结果，建议换个关键词再来一次。",
    "🔄 没等到回应，重新搜一遍或许就能找到～"
]

USER_EXTRACTION_TIPS = [
    "🔎 提示：点击上方链接即可跳转。",
    "📌 建议：打不开就复制链接到浏览器。",
    "🧩 小技巧：加上主演或年份再试试～",
    "🚀 经验：关键词越完整，命中率越高！",
    "🌟 方法：『电影名+主演』搜索更精准。",
    "💡 提示：尝试不同关键词组合可能有惊喜。",
    "🔍 建议：有时年份能帮你找到更准确的资源。",
    "📖 小贴士：片名别写错字，否则搜不到哦！",
    "🎬 经验分享：电影+导演名字也很好用。",
    "📂 友情提示：部分链接可能失效，换关键词再来一次。",
    "🎁 建议：关键词加长更容易找到目标。",
    "💬 小技巧：别只写一个字，尽量写全称。",
    "📝 提示：结果少时，试试换同义词。",
    "📡 搜索经验：加上『高清』或『完整版』试试。",
    "🧭 建议：电影+地区（如『韩国』）也很有用。",
    "🎯 小方法：专辑类加上歌手名更精准。",
    "🔗 提示：若打不开，换个浏览器试试。",
    "📱 建议：手机上打不开，可以用电脑再试。",
    "🧙 小技巧：结果不理想时换个描述方式。",
    "💎 提示：完整关键词能省不少时间。"
]

# -------------------------------
# 日志配置（插件内 + 主程序 log）
# -------------------------------
def init_logger():
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"search_plugin_{datetime.now().strftime('%Y%m%d')}.log")

    logger = logging.getLogger("search_plugin")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(fmt)

    if not logger.handlers:
        logger.addHandler(fh)
        logger.addHandler(logging.StreamHandler())

    return logger

search_logger = init_logger()

def plugin_log(message, level="INFO"):
    """
    同时写入插件日志文件 + 调用主程序 log()（若存在）
    """
    try:
        from wxbot_class_only_V2 import log as main_log
        main_log(message, level=level)
    except Exception:
        pass  # 主程序 log 不可用时忽略

    if level == "ERROR":
        search_logger.error(message)
    else:
        search_logger.info(message)

# -------------------------------
# 工具函数
# -------------------------------
def split_long_text(text, chunk_size=2000):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

# -------------------------------
# 插件主逻辑
# -------------------------------
def search_resources_thread(chat, keyword, chat_info=None, is_group_chat=False, sender=None):
    """搜索线程函数"""
    if not SEARCH_ENABLED:
        return

    if chat_info and chat_info.get("sender", "").lower() in ("self", "我"):
        plugin_log("忽略自己消息，不触发搜索。", "DEBUG")
        return

    # 发送提示语（随机一条）
    prompt_msg = random.choice(SEARCH_PROMPTS).format(keyword=keyword)
    try:
        if is_group_chat and sender:
            chat.SendMsg(msg=prompt_msg, at=sender)
        else:
            chat.SendMsg(prompt_msg)
    except Exception as e:
        plugin_log(f"发送搜索提示语失败: {e}", "ERROR")

    # 调用 API 搜索
    result_msg = search_resources(keyword, chat_info)

    # 结果处理
    if not result_msg:
        reply_msg = random.choice(SEARCH_FAIL_TEMPLATES)
    else:
        reply_msg = result_msg

    # 发送结果
    try:
        if len(reply_msg) > 2000:
            for seg in split_long_text(reply_msg):
                chat.SendMsg(seg)
                time.sleep(1)
        else:
            if is_group_chat and sender:
                chat.SendMsg(msg=reply_msg, at=sender)
            else:
                chat.SendMsg(reply_msg)
    except Exception as e:
        plugin_log(f"搜索插件发送消息失败: {e}", "ERROR")

def search_resources(title, chat_info=None):
    """调用 API 搜索并返回格式化结果"""
    for attempt in range(SEARCH_RETRY_COUNT + 1):
        try:
            response = requests.post(
                SEARCH_API_URL,
                data={"title": title},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=SEARCH_TIMEOUT
            )
            response.raise_for_status()
            result = response.json()
            data_list = result.get("data", [])
            if not data_list:
                return None

            header = random.choice(RESULT_HEADER_EMOJIS)
            formatted = f"\n{header} 搜索到与「{title}」相关的资源，共 {len(data_list)} 条：\n\n"

            for idx, item in enumerate(data_list, start=1):
                emo = random.choice(RESOURCE_EMOJIS)
                formatted += f"{emo} 第{idx}条：{item.get('title','未知')}\n"
                formatted += f"🔗 链接：{item.get('url','无')}\n\n"

            if SHOW_EXTRACTION_TIP:
                formatted += random.choice(USER_EXTRACTION_TIPS) + "\n"

            if ad_switch:
                formatted += "\n" + random.choice(AD_TEMPLATES)

            return formatted.strip()
        except requests.exceptions.Timeout:
            if attempt >= SEARCH_RETRY_COUNT:
                return random.choice(SEARCH_TIMEOUT_TEMPLATES)
        except Exception as e:
            plugin_log(f"搜索异常: {e}", "ERROR")
            return f"❌ 搜索「{title}」时发生未知错误，请再试一次吧。"

# -------------------------------
# 指令检测
# -------------------------------
def is_search_command(content, at_me=None):
    """检测是否为搜索指令"""
    if not content or not content.strip():
        return False, ""
    content_clean = content.strip()
    if at_me:
        content_clean = re.sub(re.escape(at_me), "", content_clean).strip()

    patterns = [
        ("全网搜", r"^全网搜\s*(.+)$"),
        ("搜资源", r"^搜资源\s*(.+)$"),
        ("搜剧", r"^搜剧\s*(.+)$"),
        ("搜索", r"^搜索\s*(.+)$"),
        ("看", r"^看\s*(.+)$"),
        ("搜", r"^搜\s*(.+)$"),
    ]
    for _, p in patterns:
        m = re.match(p, content_clean)
        if m:
            return True, m.group(1).strip()

    no_space_patterns = [p.replace(r"\s*", "") for _, p in patterns]
    for p in no_space_patterns:
        m = re.match(p, content_clean)
        if m:
            return True, m.group(1).strip()

    return False, ""


# -------------------------------
# 插件核心接口（符合主程序规范）
# -------------------------------
PLUGIN_NAME = "心悦网盘搜索插件"
PLUGIN_ENABLED = SEARCH_ENABLED  # 复用插件总开关
PLUGIN_PRIORITY = 100  # 优先级（数值越大越先执行）


def check(msg, chat, chat_info):
    """
    主程序调用：判断是否为搜索指令
    返回 (True, keyword) 表示匹配，(False, None) 表示不匹配
    """
    try:
        # 忽略自己发送的消息
        if getattr(msg, "attr", "") == "self":
            return (False, None)

        # 获取消息内容（仅处理文本消息）
        if msg.type != "text":
            return (False, None)
        content = getattr(msg, "content", "").strip()
        if not content:
            return (False, None)

        # 检测是否为搜索指令（调用现有 is_search_command 函数）
        # 群聊中可能需要处理 @ 机器人的情况（此处简化处理，可根据实际需求扩展）
        matched, keyword = is_search_command(content)
        if matched and keyword:
            return (True, keyword)  # 返回关键词作为 data
        return (False, None)
    except Exception as e:
        plugin_log(f"check 函数异常: {e}", "ERROR")
        return (False, None)


def handle(msg, chat, chat_info, data):
    """
    主程序调用：处理搜索逻辑
    data 为 check 函数返回的 keyword
    """
    try:
        keyword = data  # data 是 check 传递的关键词
        if not keyword:
            return

        # 判断是否为群聊，以及获取发送者（用于 @ 提醒）
        is_group = chat_info.get("type") == "group"
        sender = chat_info.get("sender", "")

        # 启动搜索线程（复用现有 search_resources_thread 函数）
        import threading  # 确保导入 threading 模块
        threading.Thread(
            target=search_resources_thread,
            args=(chat, keyword),
            kwargs={"is_group_chat": is_group, "sender": sender, "chat_info": chat_info},
            daemon=True
        ).start()
        return True  # 表示已处理
    except Exception as e:
        plugin_log(f"handle 函数异常: {e}", "ERROR")
        return None