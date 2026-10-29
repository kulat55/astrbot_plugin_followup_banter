# -*- coding: utf-8 -*-
"""追问机制插件：被吐槽回怼后，偶尔追加一条追问补刀。

场景示例：
  用户: 肥猪啊
  林小瞒: 你才是肥猪，我这是正常吃饭
  （几秒后追加）: 你不吃的比我多！

触发条件：
  1. 用户消息含吐槽/调侃词（胖/肥/猪/傻/菜/懒 等）
  2. 助手回复含反驳特征（才是/才不/我这是/正常/胡说 等）
  3. 概率约 15%（10 次对话触发 1-2 次），不重复触发
"""
import asyncio
import random

from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.star import Star

# 用户吐槽 / 调侃词
_TEASE_WORDS = (
    "胖", "肥", "猪", "傻", "笨", "蠢", "菜", "弱", "懒",
    "丑", "矮", "穷", "抠", "装", "秀", "离谱", "虚胖", "肥猪",
)
# 助手反驳 / 回怼特征
_RETORT_MARKS = (
    "才是", "才不", "我这是", "正常", "胡说", "哪有", "谁说的",
    "明明", "本来就是", "凭啥", "你才", "才怪", "才没有",
)
# 追问补刀模板（林小瞒口吻）
_FOLLOWUPS = (
    "你不吃的比我多！",
    "你倒是说说，我哪胖了？",
    "哼，你这就是羡慕我吃得好。",
    "那你昨天吃了三碗饭的事，要不要聊聊？",
    "我这是标准身材，懂不懂啊。",
    "你先管好你自己再说我。",
    "你再说一遍？我录音了。",
    "行行行，你瘦你瘦，你最瘦了行吧。",
    "你说我胖，那你倒是给我买点减肥餐啊。",
    "哦？那你吃的比我多的时候怎么说？",
    "你这话说的，我可记小本本上了。",
    "胖怎么了，我又没吃你家大米。",
)


class FollowUpBanterPlugin(Star):
    def __init__(self, context):
        super().__init__(context)
        self._pending = {}  # unified_msg_origin -> 追问文本

    @filter.on_llm_response(priority=2000)
    async def maybe_queue(self, event: AstrMessageEvent, response) -> None:
        """在 LLM 回复生成后判断是否触发追问，先记录，等消息发完再补刀。"""
        try:
            reply = getattr(response, "completion_text", "") or ""
            user_text = event.message_str or ""
            if not reply or not user_text:
                return
            # 只对私聊生效（她只跟好友斗嘴）
            if "FriendMessage" not in event.unified_msg_origin:
                return
            if not any(w in user_text for w in _TEASE_WORDS):
                return
            if not any(m in reply for m in _RETORT_MARKS):
                return
            if random.random() >= 0.15:
                return
            self._pending[event.unified_msg_origin] = random.choice(_FOLLOWUPS)
        except Exception:
            pass

    @filter.after_message_sent(priority=2000)
    async def send_followup(self, event: AstrMessageEvent) -> None:
        """回复已发出，隔 1-3 秒再发追问，像真人补刀。"""
        text = self._pending.pop(event.unified_msg_origin, None)
        if text is None:
            return
        try:
            await asyncio.sleep(random.uniform(1.0, 3.0))
            await event.send(MessageChain().message(text))
        except Exception:
            pass
