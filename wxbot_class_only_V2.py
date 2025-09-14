#!/usr/bin/env python3
# Siver 微信机器人 siver_wxbot - 面向对象版本 - wxautox V2版本（改造插件化主程序）
# 版本: V2.59
# 说明: 此版本已移除 AI 逻辑，增加插件管理器，移除邮件通知，仅保留企业微信通知选项（插件可使用）
# 作者: https://siver.top （原作者），本次改造：按用户要求整理

version = "V2.59"
version_log = "V2.59 feat: 移除AI并加入插件管理、移除邮件通知"

import os
import sys
import time
import json
import re
import traceback
import random
import threading
import importlib.util
from datetime import datetime
from typing import List, Dict, Any

# ====== 依赖 wxautox ======
try:
    from wxautox import WeChat
    from wxautox.msgs import FriendMessage, SystemMessage, HumanMessage
    from wxautox import WxParam
    from wxautox.utils.useful import check_license
    WXAUTO_AVAILABLE = True
except Exception as e:
    WXAUTO_AVAILABLE = False

# ====== 日志模块（复用你之前的 log 实现） ======
LOG_PATH = "./logs"
if not os.path.exists(LOG_PATH):
    try:
        os.makedirs(LOG_PATH, exist_ok=True)
    except Exception:
        pass

# 内存日志（网页管理控制台可使用）
log_messages = []

def log_server(level, msg):
    """
    记录日志到内存和文件（简易内存缓存 + 本地文件）
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = {'time': timestamp, 'level': level, 'message': msg}
    log_messages.append(entry)
    # 限制内存日志长度
    if len(log_messages) > 2000:
        log_messages.pop(0)
    # 输出控制台
    print(f"[{timestamp}] [{level}] {msg}")
    # 写文件
    try:
        now_day = datetime.now().strftime("%y%m%d")
        with open(os.path.join(LOG_PATH, f'log_{now_day}.txt'), 'a', encoding='utf-8-sig') as f:
            f.write(f'[{timestamp}] [{level}] {msg}\n')
    except Exception:
        # 若写文件失败，尽量创建目录再写
        try:
            os.makedirs(LOG_PATH, exist_ok=True)
            with open(os.path.join(LOG_PATH, f'log_{now_day}.txt'), 'a', encoding='utf-8-sig') as f:
                f.write(f'[{timestamp}] [{level}] {msg}\n')
        except Exception:
            print(f"[{timestamp}] [ERROR] 无法写入日志文件")

def log(message="", level="INFO"):
    """统一日志接口"""
    log_server(level, str(message))

# ====== 全局参数调整（与 wxautox 一致可配置） ======
try:
    WxParam.MESSAGE_HASH = True
    WxParam.FORCE_MESSAGE_XBIAS = True
except Exception:
    pass

# ====== 配置类 ======
class WXBotConfig:
    """微信机器人配置类，负责读取/写入 config.json"""
    def __init__(self, config_file: str = "config.json"):
        self.CONFIG_FILE = config_file
        self.config = {}
        # 默认配置项（精简与必要项）
        self.defaults = {
            "admin": "管理员",
            "AllListen_switch": False,
            "listen_list": [],  # 白名单/黑名单视AllListen_switch而定
            "group": [],
            "group_switch": False,
            "group_reply_at": False,
            "group_welcome": False,
            "group_welcome_random": 1.0,
            "group_welcome_msg": "欢迎新朋友！请先查看群公告！本消息由wxautox发送!",
            "new_friend_switch": False,
            "new_friend_msg": [],
            # 插件相关配置（网页端会用到）
            "plugins": {
                # "search_plugin": 1
            },
            # 企业微信推送（选项保留，邮件去掉）
            "notify_method": "wechat",  # "wechat" or ""（空为不推送）
            "wechat_notify": {
                "corp_id": "",
                "secret": "",
                "agentid": ""
            }
        }
        self.load_or_create()

    def load_or_create(self):
        """加载配置文件，若不存在则创建默认"""
        if not os.path.exists(self.CONFIG_FILE):
            # 创建默认文件
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.defaults, f, ensure_ascii=False, indent=4)
            self.config = dict(self.defaults)
            log("已创建默认配置文件：" + os.path.abspath(self.CONFIG_FILE))
        else:
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                # 补缺失的默认字段
                updated = False
                for k, v in self.defaults.items():
                    if k not in self.config:
                        self.config[k] = v
                        updated = True
                if updated:
                    self.save()
                log("配置文件加载成功")
            except Exception as e:
                log(f"加载配置文件失败: {e}", level="ERROR")
                # 备份旧文件并重建
                try:
                    os.rename(self.CONFIG_FILE, self.CONFIG_FILE + ".bak")
                    with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                        json.dump(self.defaults, f, ensure_ascii=False, indent=4)
                    self.config = dict(self.defaults)
                except Exception as ex:
                    log(f"重建配置失败: {ex}", level="ERROR")

    def save(self):
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            log("配置已保存")
        except Exception as e:
            log(f"保存配置失败: {e}", level="ERROR")

    # 读取常用字段的便捷方法
    @property
    def admin(self):
        return self.config.get("admin", self.defaults["admin"])

    @property
    def AllListen_switch(self):
        return self.config.get("AllListen_switch", False)

    @property
    def listen_list(self):
        return self.config.get("listen_list", [])

    @property
    def group(self):
        return self.config.get("group", [])

    @property
    def group_switch(self):
        return self.config.get("group_switch", False)

    @property
    def group_welcome(self):
        return self.config.get("group_welcome", False)

    @property
    def group_welcome_msg(self):
        return self.config.get("group_welcome_msg", "")

    def update(self, key, value):
        self.config[key] = value
        self.save()

# ====== 插件管理器 ======
class PluginManager:
    """
    插件管理器：动态加载 ./plugins 目录下的插件模块（按文件名）
    插件规范（推荐）：
    - PLUGIN_NAME: str
    - PLUGIN_ENABLED: int (1 开启, 0 关闭)
    - PLUGIN_PRIORITY: int (优先级, 大的先执行)
    - def check(msg, chat, chat_info) -> (bool, data)  # 是否匹配
    - def handle(msg, chat, chat_info, data) -> WxResponse | None  # 执行处理
    主程序调用逻辑：
    - 按 PLUGIN_PRIORITY 降序遍历已加载并启用的插件
    - 对每个插件调用 check，若返回 (True, data)，则调用 handle 并终止后续处理（插件表明已处理）
    """
    def __init__(self, plugins_dir: str = "./plugins"):
        self.plugins_dir = plugins_dir
        self.plugins = []  # 每项为 dict: {'name':..., 'module':..., 'priority':..., 'enabled':...}
        self.load_plugins()

    def load_plugins(self):
        """扫描插件目录并尝试加载 py 文件"""
        log(f"开始扫描插件目录：{self.plugins_dir}")
        if not os.path.isdir(self.plugins_dir):
            log(f"插件目录不存在，创建：{self.plugins_dir}")
            try:
                os.makedirs(self.plugins_dir, exist_ok=True)
            except Exception as e:
                log(f"创建插件目录失败：{e}", level="ERROR")
                return

        for fname in os.listdir(self.plugins_dir):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            fpath = os.path.join(self.plugins_dir, fname)
            modulename = os.path.splitext(fname)[0]
            try:
                # 动态导入模块
                spec = importlib.util.spec_from_file_location(modulename, fpath)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # 读取插件属性
                p_name = getattr(module, "PLUGIN_NAME", modulename)
                p_enabled = int(getattr(module, "PLUGIN_ENABLED", 1))
                p_priority = int(getattr(module, "PLUGIN_PRIORITY", 50))
                self.plugins.append({
                    "name": p_name,
                    "module": module,
                    "priority": p_priority,
                    "enabled": bool(p_enabled),
                    "path": fpath
                })
                log(f"加载插件: {p_name} (enabled={p_enabled}, priority={p_priority})")
            except Exception as e:
                log(f"加载插件 {modulename} 失败: {e}", level="ERROR")
                log(traceback.format_exc(), level="ERROR")
        # 按优先级排序（降序）
        self.plugins.sort(key=lambda x: x["priority"], reverse=True)
        log(f"插件加载完成，共 {len(self.plugins)} 个插件（包含未启用）")

    def reload_plugins(self):
        """重新加载插件（可由外部命令调用）"""
        self.plugins = []
        self.load_plugins()

    def dispatch(self, msg, chat, chat_info):
        """
        将消息分发给插件处理。按优先级顺序尝试。
        如果插件匹配并处理了消息，返回该插件的处理结果（或 True 表示已处理）。
        若无插件处理，返回 None。
        """
        for p in self.plugins:
            if not p["enabled"]:
                continue
            module = p["module"]
            try:
                check_fn = getattr(module, "check", None)
                handle_fn = getattr(module, "handle", None)
                if callable(check_fn):
                    matched, data = check_fn(msg, chat, chat_info)
                    if matched:
                        log(f"插件 {p['name']} 匹配消息，调用 handle()", level="INFO")
                        if callable(handle_fn):
                            try:
                                result = handle_fn(msg, chat, chat_info, data)
                                # 如果插件返回非 None，视为已处理（可返回具体 WxResponse）
                                return {"plugin": p["name"], "result": result}
                            except Exception as e:
                                log(f"插件 {p['name']} 执行 handle() 出错: {e}", level="ERROR")
                                log(traceback.format_exc(), level="ERROR")
                                return {"plugin": p["name"], "result": None}
                        else:
                            # 模块没有 handle 函数，仅标记为匹配并返回
                            return {"plugin": p["name"], "result": None}
                else:
                    # 没有 check 函数，忽略
                    continue
            except Exception as e:
                log(f"插件 {p['name']} 处理异常: {e}", level="ERROR")
                log(traceback.format_exc(), level="ERROR")
        return None

    def list_plugins(self):
        return [{"name": p["name"], "enabled": p["enabled"], "priority": p["priority"], "path": p["path"]} for p in self.plugins]

# ====== 微信机器人主类（简化/插件化） ======
class WXBot:
    def __init__(self):
        self.ver = version
        self.ver_log = version_log
        self.config = WXBotConfig()
        self.wx = None
        self.plugin_mgr = PluginManager("./plugins")
        self.run_flag = True
        self.start_time = datetime.now()
        self.callback_is_die = False
        self.all_Mode_listen_list = []  # 用于全局模式动态监听
        # 监听初始化时设置的子窗口对象
        self.listen_windows = {}
        # 其他必要初始化
        if WXAUTO_AVAILABLE:
            # Set wxautox params if needed
            pass
        else:
            log("wxautox 未安装或无法导入，请确保 wxautox 可用！", level="WARNING")

    def check_wx_license(self):
        """校验 wxautox 授权（如可用）"""
        try:
            return check_license()
        except Exception:
            # 若不可用，则返回 True（避免阻断），但记录日志
            log("检查 wxautox 授权失败（可能方法不存在），继续执行", level="WARNING")
            return True

    def init_wechat(self):
        """初始化 WeChat 客户端并启动监听（若尚未初始化）"""
        if not WXAUTO_AVAILABLE:
            log("wxautox 模块不可用，无法初始化微信客户端", level="ERROR")
            return False
        if not self.wx:
            try:
                self.wx = WeChat()
                self.wx.Show()
                time.sleep(0.5)
                log(f"已连接微信客户端: {self.wx.nickname}")
            except Exception as e:
                log(f"初始化微信客户端失败: {e}", level="ERROR")
                log(traceback.format_exc(), level="ERROR")
                return False
        # 启动监听
        try:
            self.wx.StartListening()
            log("微信监听器已启动")
        except Exception as e:
            log(f"启动微信监听器失败: {e}", level="ERROR")
            log(traceback.format_exc(), level="ERROR")
            return False
        # 绑定管理员监听（原本逻辑）
        try:
            admin = self.config.admin
            if admin:
                res = self.wx.AddListenChat(nickname=admin, callback=self.message_handle_callback)
                if res:
                    log(f"已为管理员 {admin} 添加监听")
                else:
                    log(f"为管理员添加监听失败: {res}", level="WARNING")
        except Exception as e:
            log(f"添加管理员监听失败: {e}", level="ERROR")

        # 根据配置添加白名单/群组监听（若非全局模式）
        if not self.config.AllListen_switch:
            for name in self.config.listen_list:
                try:
                    res = self.wx.AddListenChat(nickname=name, callback=self.message_handle_callback)
                    if res:
                        log(f"为用户 {name} 添加监听")
                except Exception as e:
                    log(f"添加 {name} 监听失败: {e}", level="ERROR")
        # 群组监听（若开启）
        if self.config.group_switch:
            for g in self.config.group:
                try:
                    res = self.wx.AddListenChat(nickname=g, callback=self.message_handle_callback)
                    if res:
                        log(f"为群组 {g} 添加监听")
                except Exception as e:
                    log(f"为群组 {g} 添加监听失败: {e}", level="ERROR")
        return True

    def stop_listening(self):
        """停止微信监听"""
        if self.wx:
            try:
                self.wx.StopListening()
                log("微信监听器已停止")
            except Exception as e:
                log(f"停止监听失败: {e}", level="ERROR")

    # ---------- 消息处理主入口（AddListenChat 的回调） ----------
    def message_handle_callback(self, msg, chat):
        """
        监听回调：wxautox 在监听到新消息时会回调到这里
        参数:
            msg: Message 对象（wxautox）
            chat: Chat 对象（wxautox 子窗口）
        处理流程：
            1. 忽略自己发送的消息（msg.attr == 'self'）
            2. 构造 chat_info (dict)，包含 type/name/sender/sender_remark 等
            3. 将消息交给 PluginManager.dispatch 逐个插件判断处理（插件返回表示已处理则停止）
            4. 若所有插件均未处理，执行默认行为（目前仅记录日志，可扩展为其他功能）
        """
        try:
            # 基本日志
            chat_name = getattr(chat, "who", None) or (chat.ChatInfo().get("chat_name") if hasattr(chat, "ChatInfo") else "unknown")
            sender = getattr(msg, "sender", "")
            sender_remark = getattr(msg, "sender_remark", "") if hasattr(msg, "sender_remark") else ""
            log(f"{datetime.now().strftime('%Y/%m/%d %H:%M:%S')} 类型：{msg.type} 属性：{msg.attr} 窗口：{chat_name} 发送人：{sender_remark or sender} - 消息：{getattr(msg, 'content', '')}")

            # 忽略机器人自己发送的消息（避免循环）
            if msg.attr == "self":
                log("忽略自己发送的消息", level="DEBUG")
                return

            # 构造 chat_info 字典，传给插件
            chat_info = {}
            try:
                ci = msg.chat_info() if hasattr(msg, "chat_info") else {}
                chat_info['type'] = ci.get('chat_type', 'friend') if isinstance(ci, dict) else 'friend'
                chat_info['name'] = ci.get('chat_name', chat_name) if isinstance(ci, dict) else chat_name
            except Exception:
                chat_info['type'] = 'friend'
                chat_info['name'] = chat_name
            chat_info['sender'] = sender
            chat_info['sender_remark'] = sender_remark
            chat_info['msg_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 先交给插件处理（插件按优先级顺序）
            dispatch_res = self.plugin_mgr.dispatch(msg, chat, chat_info)
            if dispatch_res is not None:
                # 插件已处理（或至少匹配并执行）
                plugin_name = dispatch_res.get("plugin")
                log(f"消息由插件 {plugin_name} 处理完毕", level="INFO")
                return

            # 若没有插件处理，则执行默认行为（目前仅记录日志；可以在此扩展为内置处理）
            log(f"未被插件处理的消息：{chat_info['name']} - {getattr(msg, 'content', '')}", level="DEBUG")

            # 群欢迎逻辑（如果是 system 消息并启用）
            if isinstance(msg, SystemMessage) and self.config.group_welcome and chat_info.get('type') == 'group':
                # 处理入群类 system 消息
                try:
                    content = getattr(msg, 'content', '') or ""
                    # 简单匹配“加入群聊”或“加入了群聊”
                    if "加入群聊" in content or "加入了群聊" in content:
                        # 提取用户名（尽量兼容多种 system 文本）
                        m = re.findall(r'"([^"]+)"', content)
                        new_name = m[0] if m else None
                        if new_name:
                            time.sleep(3)
                            try:
                                chat.SendMsg(msg=self.config.group_welcome_msg, at=new_name)
                                log(f"群欢迎消息已发送，at: {new_name}")
                            except Exception:
                                chat.SendMsg(self.config.group_welcome_msg)
                                log("群欢迎消息发送（未能 at）")
                except Exception as e:
                    log(f"处理群欢迎消息失败: {e}", level="ERROR")
            # 其他默认行为可在此处扩展
        except Exception as e:
            log(f"回调处理出错: {e}", level="ERROR")
            log(traceback.format_exc(), level="ERROR")

    # ---------- 新好友处理（定期执行） ----------
    def pass_new_friends(self):
        """检查并自动通过新的好友申请（如果配置开启）"""
        try:
            if not self.wx:
                return
            if not self.config.new_friend_switch:
                return
            newfriends = self.wx.GetNewFriends(acceptable=True)
            time.sleep(1)
            if not newfriends:
                return
            log(f"发现 {len(newfriends)} 个新的好友申请")
            for new in newfriends:
                try:
                    remark = new.name + "_机器人备注"
                    new.accept(remark=remark)
                    log(f"已接受好友：{new.name} 并备注为 {remark}")
                    time.sleep(2)
                    # 发送欢迎语
                    for msg in self.config.new_friend_msg:
                        if os.path.exists(msg) and os.path.isfile(msg):
                            self.wx.SendFiles(who=remark, filepath=msg)
                        else:
                            self.wx.SendMsg(who=remark, msg=msg)
                        time.sleep(random.randint(1, 3))
                    self.wx.SwitchToChat()
                    time.sleep(1)
                    self.wx.SwitchToContact()
                except Exception as e:
                    log(f"处理新好友 {getattr(new,'name', '')} 失败: {e}", level="ERROR")
        except Exception as e:
            log(f"自动处理新好友出错: {e}", level="ERROR")
            log(traceback.format_exc(), level="ERROR")

    # ---------- 主运行循环 ----------
    def main(self):
        """主运行函数：初始化、启动监听并循环检查任务"""
        log(f"wxbot 启动 - 版本: {self.ver}")
        # 检查 wxautox 激活授权
        activated = True
        try:
            activated = self.check_wx_license()
        except Exception as e:
            log(f"授权检查异常: {e}", level="WARNING")
        if not activated:
            log("wxautox 未激活，请激活后再运行", level="ERROR")
            return False

        # 初始化微信客户端与监听器
        ok = self.init_wechat()
        if not ok:
            log("初始化微信失败，退出", level="ERROR")
            return False

        # 主循环
        self.run_flag = True
        check_counter = 0
        check_interval = 10
        new_friend_counter = 0
        try:
            while self.run_flag:
                try:
                    # 定期检查微信是否在线
                    check_counter += 1
                    if check_counter >= check_interval:
                        check_counter = 0
                        try:
                            if self.wx and not self.wx.IsOnline():
                                log("检测到微信客户端不在线，请检查登录状态", level="ERROR")
                                # 此处不直接退出，但记录并继续
                        except Exception as e:
                            log(f"检测微信在线状态出错: {e}", level="ERROR")

                    # 定期处理新好友
                    new_friend_counter += 1
                    if new_friend_counter >= 60:  # 约每分钟检查一次（可 ajustar）
                        new_friend_counter = 0
                        try:
                            self.pass_new_friends()
                        except Exception as e:
                            log(f"自动接受新好友出错: {e}", level="ERROR")

                    # 这里不再处理 AI 或 GetNextNewMessage，所有处理通过 AddListenChat 的回调完成
                    # 运行中的其他定时任务（例如 config.everyday_msg）可以在插件中实现
                except Exception as e:
                    log(f"主循环内部错误: {e}", level="ERROR")
                    log(traceback.format_exc(), level="ERROR")
                time.sleep(1)
        except KeyboardInterrupt:
            log("接收到中断信号，正在停止...")
            self.stop_listening()
        except Exception as e:
            log(f"主线程异常退出: {e}", level="ERROR")
            log(traceback.format_exc(), level="ERROR")
        log("主线程安全退出")
        return True

    def stop(self):
        """停止机器人"""
        self.run_flag = False
        try:
            self.stop_listening()
        except Exception:
            pass
        log("机器人已停止", level="WARNING")

# ====== 简单插件 demo（供测试） ======
# 说明：此处不启用为文件，而是示范插件规范。真正的插件应放到 ./plugins 目录下，
# 并实现 check(msg, chat, chat_info) 和 handle(msg, chat, chat_info, data) 接口。
#
# 例如插件文件: plugins/search_plugin.py
# PLUGIN_NAME = "search_plugin"
# PLUGIN_ENABLED = 1
# PLUGIN_PRIORITY = 100
# def check(msg, chat, chat_info):
#     # 返回 (True, keyword) 表示匹配
#     # 返回 (False, None) 表示不匹配
# def handle(msg, chat, chat_info, data):
#     # 执行处理逻辑（例如发起搜索并回复），可以返回 WxResponse 或 None

# ====== 启动入口 ======
if __name__ == "__main__":
    bot = WXBot()
    bot.main()