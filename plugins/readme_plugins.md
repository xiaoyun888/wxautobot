# 微信机器人插件开发指南

## 1. 插件基础概述

微信机器人（`wxbot_class_only_V2.py`）采用插件化架构，所有功能扩展通过插件实现。插件是独立的Python模块，放置在`./plugins`目录下，遵循特定规范即可被主程序自动加载和调用。

插件的核心优势：
- 松耦合设计，不修改主程序即可扩展功能
- 支持动态加载与优先级调度
- 统一的消息处理接口，易于开发

## 2. 插件目录结构

```
项目根目录/
├── wxbot_class_only_V2.py  # 主程序
├── config.json             # 配置文件
└── plugins/                # 插件目录
    ├── search_plugin.py    # 示例搜索插件
    ├── weather_plugin.py   # 示例天气插件
    └── logs/               # 插件日志目录（可选）
```

**注意**：
- 插件文件名必须以`.py`结尾，且不能以`_`开头
- 日志建议放在`plugins/logs`目录，便于管理

## 3. 插件核心规范

每个插件必须包含以下要素：

| 要素 | 类型 | 说明 |
|------|------|------|
| `PLUGIN_NAME` | 字符串 | 插件唯一标识（如"search"、"weather"） |
| `PLUGIN_ENABLED` | 整数 | 插件开关（1=启用，0=禁用） |
| `PLUGIN_PRIORITY` | 整数 | 优先级（数值越大越先执行，建议范围1-100） |
| `check(msg, chat, chat_info)` | 函数 | 检测消息是否需要本插件处理 |
| `handle(msg, chat, chat_info, data)` | 函数 | 处理匹配的消息逻辑 |

## 4. 核心函数详解

### 4.1 check() 函数

**功能**：判断当前消息是否应该由本插件处理

**参数**：
- `msg`：消息对象（wxautox提供），包含消息内容、类型等信息
- `chat`：聊天窗口对象（wxautox提供），用于发送消息等操作
- `chat_info`：聊天信息字典，结构如下：
  ```python
  {
      "type": "group" or "friend",  # 聊天类型
      "name": "群聊名称"或"好友昵称",  # 聊天窗口名称
      "sender": "发送者ID",
      "sender_remark": "发送者备注名",
      "msg_time": "消息时间字符串"
  }
  ```

**返回值**：
- `(True, data)`：消息匹配成功，`data`为需要传递给`handle`的参数
- `(False, None)`：消息不匹配

**示例**：
```python
def check(msg, chat, chat_info):
    # 仅处理文本消息
    if msg.type != "text":
        return (False, None)
    
    content = getattr(msg, "content", "").strip()
    # 匹配"天气 城市名"格式的指令
    if content.startswith("天气 "):
        city = content.split(" ", 1)[1]
        return (True, city)  # 返回城市名给handle处理
    return (False, None)
```

### 4.2 handle() 函数

**功能**：处理`check`函数匹配成功的消息

**参数**：
- 前三个参数与`check`函数相同
- `data`：`check`函数返回的处理参数

**返回值**：
- 任意值（主程序仅通过返回非`None`判断处理完成）

**示例**：
```python
def handle(msg, chat, chat_info, data):
    city = data  # data为check传递的城市名
    weather_info = get_weather(city)  # 自定义函数获取天气
    chat.SendMsg(f"{city}的天气：{weather_info}")  # 发送消息
    return True  # 表示处理完成
```

## 5. 常用API参考

### 5.1 消息对象（msg）常用属性
- `msg.type`：消息类型（"text"=文本，"image"=图片等）
- `msg.content`：消息内容（文本消息）
- `msg.attr`：消息属性（"self"表示自己发送的消息）
- `msg.sender`：发送者ID
- `msg.sender_remark`：发送者备注名

### 5.2 聊天窗口对象（chat）常用方法
- `chat.SendMsg(msg, at="")`：发送消息
  - `msg`：消息内容字符串
  - `at`：群聊中@的用户昵称（可选）
- `chat.who`：聊天窗口名称
- `chat.ChatInfo()`：获取聊天窗口详细信息

### 5.3 日志功能
主程序提供全局日志函数，可直接使用：
```python
from wxbot_class_only_V2 import log
log("插件处理成功", level="INFO")  # 普通日志
log("处理失败", level="ERROR")      # 错误日志
```

## 6. 插件开发流程

1. **创建插件文件**：在`./plugins`目录下新建`{功能名}_plugin.py`（如`calc_plugin.py`）

2. **定义插件元信息**：
   ```python
   PLUGIN_NAME = "calculator"  # 唯一标识
   PLUGIN_ENABLED = 1          # 启用插件
   PLUGIN_PRIORITY = 80        # 优先级（低于搜索插件）
   ```

3. **实现check()函数**：
   ```python
   def check(msg, chat, chat_info):
       if msg.type != "text":
           return (False, None)
       content = getattr(msg, "content", "").strip()
       # 匹配"计算 表达式"指令
       if content.startswith("计算 "):
           expression = content.split(" ", 1)[1]
           return (True, expression)
       return (False, None)
   ```

4. **实现handle()函数**：
   ```python
   def handle(msg, chat, chat_info, data):
       try:
           expression = data
           result = eval(expression)  # 简易计算（实际需考虑安全）
           chat.SendMsg(f"计算结果：{expression} = {result}")
           return True
       except Exception as e:
           chat.SendMsg(f"计算错误：{str(e)}")
           return None
   ```

5. **测试插件**：
   - 将插件放入`./plugins`目录
   - 启动主程序`wxbot_class_only_V2.py`
   - 在监听的聊天窗口发送"计算 1+2*3"测试

## 7. 高级技巧

### 7.1 多线程处理
对于耗时操作（如API调用），建议使用多线程避免阻塞主程序：
```python
import threading

def handle(msg, chat, chat_info, data):
    def process():
        # 耗时操作
        time.sleep(5)
        chat.SendMsg("处理完成")
    
    threading.Thread(target=process, daemon=True).start()
    return True
```

### 7.2 配置管理
可在插件中读取主程序配置：
```python
from wxbot_class_only_V2 import WXBotConfig
config = WXBotConfig()
admin = config.admin  # 获取管理员配置
```

### 7.3 插件间优先级
通过`PLUGIN_PRIORITY`控制执行顺序：
- 高优先级插件（如紧急指令）设为90-100
- 普通插件设为50-80
- 低优先级插件设为1-40

## 8. 注意事项

1. 避免在`check`和`handle`中执行耗时操作，耗时任务应放线程中
2. 处理自己发送的消息时需判断`msg.attr == "self"`并忽略
3. 群聊@功能需使用`chat.SendMsg(msg, at=sender)`
4. 插件异常不会导致主程序崩溃，但需做好异常捕获
5. 定期清理日志文件，避免占用过多磁盘空间

## 9. 示例插件参考

- 搜索插件（`search_plugin.py`）：展示了API调用、多线程、日志管理等功能
- 天气插件（`weather_plugin.py`）：展示了指令匹配、消息格式化等基础功能

可参考以上插件实现自己的业务逻辑，遵循规范即可无缝集成到主程序中。