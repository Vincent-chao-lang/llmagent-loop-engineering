"""
LLM Agent协作协议

定义Agent间通信和协作的协议标准。
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class MessageType(Enum):
    """消息类型"""
    PROPOSAL = "proposal"           # 提案
    REQUEST = "request"             # 请求
    RESPONSE = "response"           # 响应
    NEGOTIATION = "negotiation"     # 协商
    AGREEMENT = "agreement"         # 协议
    REJECTION = "rejection"         # 拒绝
    NOTIFICATION = "notification"   # 通知
    QUERY = "query"                 # 查询


class MessagePriority(Enum):
    """消息优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class AgentMessage:
    """Agent间消息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.NOTIFICATION
    sender: str = ""
    receiver: str = ""  # 空表示广播
    subject: str = ""
    content: Any = None
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = ""  # 用于关联请求-响应
    reply_to: str = ""  # 回复的消息ID
    ttl: int = 3600  # 消息生存时间（秒）
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_broadcast(self) -> bool:
        """是否为广播消息"""
        return not self.receiver

    def is_expired(self) -> bool:
        """是否已过期"""
        if self.ttl <= 0:
            return False
        elapsed = (datetime.now() - self.timestamp).total_seconds()
        return elapsed > self.ttl

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "subject": self.subject,
            "content": self.content,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "metadata": self.metadata
        }


class CollaborationProtocol:
    """协作协议

    管理LLM Agent之间的通信协议和规则
    """

    def __init__(self):
        """初始化协作协议"""
        self.message_handlers = {}
        self.message_history = []
        self.active_negotiations = {}

    def register_handler(
        self,
        message_type: MessageType,
        handler: Callable
    ):
        """注册消息处理器

        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        self.message_handlers[message_type] = handler

    async def send_message(
        self,
        message: AgentMessage,
        recipient_func: Callable = None
    ) -> Optional[AgentMessage]:
        """发送消息

        Args:
            message: 要发送的消息
            recipient_func: 接收者处理函数

        Returns:
            响应消息（如果有）
        """
        # 记录消息历史
        self.message_history.append(message)

        # 如果是广播消息，发送给所有Agent
        if message.is_broadcast():
            if recipient_func:
                await recipient_func(message)
            return None

        # 如果是定向消息，发送给特定Agent
        if recipient_func:
            response = await recipient_func(message)
            return response

        return None

    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """处理接收到的消息

        Args:
            message: 接收到的消息

        Returns:
            响应消息
        """
        handler = self.message_handlers.get(message.type)

        if handler:
            return await handler(message)

        # 默认处理
        return AgentMessage(
            type=MessageType.RESPONSE,
            sender="system",
            receiver=message.sender,
            subject=f"Re: {message.subject}",
            content={"status": "received", "message_id": message.id},
            correlation_id=message.id
        )

    def create_proposal(
        self,
        sender: str,
        proposal: str,
        receivers: List[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> AgentMessage:
        """创建提案消息

        Args:
            sender: 发送者ID
            proposal: 提案内容
            receivers: 接收者列表（None表示广播）
            priority: 消息优先级

        Returns:
            提案消息
        """
        return AgentMessage(
            type=MessageType.PROPOSAL,
            sender=sender,
            receiver="" if not receivers else receivers[0],
            subject="协作提案",
            content={"proposal": proposal, "type": "collaboration_proposal"},
            priority=priority
        )

    def create_response(
        self,
        original_message: AgentMessage,
        response_content: Any,
        accept: bool = True
    ) -> AgentMessage:
        """创建响应消息

        Args:
            original_message: 原始消息
            response_content: 响应内容
            accept: 是否接受

        Returns:
            响应消息
        """
        msg_type = MessageType.RESPONSE if accept else MessageType.REJECTION

        return AgentMessage(
            type=msg_type,
            sender="system",  # 会被实际发送者替换
            receiver=original_message.sender,
            subject=f"Re: {original_message.subject}",
            content=response_content,
            correlation_id=original_message.id,
            reply_to=original_message.id
        )

    def get_conversation(
        self,
        agent_id: str,
        limit: int = 10
    ) -> List[AgentMessage]:
        """获取对话历史

        Args:
            agent_id: Agent ID
            limit: 返回数量限制

        Returns:
            相关消息列表
        """
        conversations = []

        for message in reversed(self.message_history):
            if len(conversations) >= limit:
                break

            # 包含该Agent的消息
            if (message.sender == agent_id or
                message.receiver == agent_id or
                message.is_broadcast()):
                conversations.append(message)

        return conversations

    def get_stats(self) -> Dict[str, Any]:
        """获取协议统计"""
        message_types = {}
        for message in self.message_history:
            msg_type = message.type.value
            if msg_type not in message_types:
                message_types[msg_type] = 0
            message_types[msg_type] += 1

        return {
            "total_messages": len(self.message_history),
            "message_types": message_types,
            "active_negotiations": len(self.active_negotiations)
        }


__all__ = [
    "MessageType",
    "MessagePriority",
    "AgentMessage",
    "CollaborationProtocol"
]
