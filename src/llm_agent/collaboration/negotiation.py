"""
LLM Agent协商机制

支持Agent之间的协商和冲突解决。
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class NegotiationStatus(Enum):
    """协商状态"""
    INITIATED = "initiated"       # 已启动
    IN_PROGRESS = "in_progress"   # 进行中
    AGREEMENT_REACHED = "agreement" # 达成协议
    CONFLICT = "conflict"         # 冲突
    TIMEOUT = "timeout"          # 超时
    CANCELLED = "cancelled"       # 已取消


@dataclass
class NegotiationProposal:
    """协商提案"""
    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    content: str = ""
    offer: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    priority: float = 0.5  # 0-1，1为最高优先级
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class NegotiationResult:
    """协商结果"""
    negotiation_id: str
    status: NegotiationStatus
    final_agreement: Optional[str] = None
    proposals: List[NegotiationProposal] = field(default_factory=list)
    conflict_points: List[str] = field(default_factory=list)
    resolution_method: str = ""
    satisfaction_scores: Dict[str, float] = field(default_factory=dict)
    time_taken: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class Negotiation:
    """协商管理器

    管理Agent之间的协商过程
    """

    def __init__(self, negotiation_id: str = None):
        """初始化协商

        Args:
            negotiation_id: 协商ID
        """
        self.negotiation_id = negotiation_id or str(uuid.uuid4())
        self.status = NegotiationStatus.INITIATED
        self.participants: Dict[str, Any] = {}
        self.proposals: List[NegotiationProposal] = []
        self.start_time: datetime = datetime.now()
        self.max_rounds = 5
        self.current_round = 0

    def add_participant(
        self,
        agent_id: str,
        role: str = "participant",
        priorities: Dict[str, float] = None
    ):
        """添加协商参与者

        Args:
            agent_id: Agent ID
            role: 参与者角色
            priorities: 优先级配置
        """
        self.participants[agent_id] = {
            "role": role,
            "priorities": priorities or {},
            "joined_at": datetime.now()
        }

    async def submit_proposal(
        self,
        proposal: NegotiationProposal
    ) -> bool:
        """提交提案

        Args:
            proposal: 提案

        Returns:
            是否接受提案
        """
        self.proposals.append(proposal)
        return True

    async def negotiate(
        self,
        topic: str,
        agents_dict: Dict[str, Any],
        mediation_style: str = "collaborative"
    ) -> NegotiationResult:
        """执行协商

        Args:
            topic: 协商议题
            agents_dict: Agent字典
            mediation_style: 调解风格

        Returns:
            协商结果
        """
        self.status = NegotiationStatus.IN_PROGRESS

        start_time = datetime.now()

        try:
            # 1. 收集各方的初始提案
            for agent_id, agent in agents_dict.items():
                if agent_id not in self.participants:
                    continue

                # 让Agent提交提案
                proposal_content = await agent.think(
                    f"请对议题 '{topic}' 提出你的提案和需求"
                )

                proposal = NegotiationProposal(
                    agent_id=agent_id,
                    content=proposal_content.content
                )

                await self.submit_proposal(proposal)

            # 2. 多轮协商
            for round_num in range(self.max_rounds):
                self.current_round = round_num + 1

                # 检查是否达成协议
                agreement = await self._check_agreement()
                if agreement:
                    self.status = NegotiationStatus.AGREEMENT_REACHED
                    break

                # 如果没有协议，继续协商
                if round_num < self.max_rounds - 1:
                    await self._facilitate_negotiation(topic, agents_dict)

            # 3. 如果没有达成协议，尝试调解
            if self.status != NegotiationStatus.AGREEMENT_REACHED:
                await self._mediate(topic, agents_dict)

            # 4. 生成结果
            elapsed = (datetime.now() - start_time).total_seconds()

            result = NegotiationResult(
                negotiation_id=self.negotiation_id,
                status=self.status,
                final_agreement=self._extract_agreement(),
                proposals=self.proposals,
                resolution_method=mediation_style,
                time_taken=elapsed
            )

            return result

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()

            return NegotiationResult(
                negotiation_id=self.negotiation_id,
                status=NegotiationStatus.CONFLICT,
                metadata={"error": str(e)},
                time_taken=elapsed
            )

    async def _check_agreement(self) -> Optional[str]:
        """检查是否达成协议"""
        if len(self.proposals) < 2:
            return None

        # 简化实现：检查提案的一致性
        contents = [p.content for p in self.proposals]

        # 如果所有提案内容相似，认为达成协议
        # （实际应该使用更复杂的相似度算法）
        if len(set(contents[:50] for content in contents)) == 1:
            return "一致意见达成"

        return None

    async def _facilitate_negotiation(
        self,
        topic: str,
        agents_dict: Dict[str, Any]
    ):
        """促进协商

        Args:
            topic: 协商议题
            agents_dict: Agent字典
        """
        # 为每个Agent提供其他人的提案摘要
        for agent_id, agent in agents_dict.items():
            if agent_id not in self.participants:
                continue

            # 获取其他提案摘要
            other_proposals = [
                p for p in self.proposals
                if p.agent_id != agent_id
            ]

            if other_proposals:
                summary = "其他提案:\n" + "\n".join([
                    f"- {p.agent_id}: {p.content[:100]}..."
                    for p in other_proposals
                ])

                # 让Agent思考如何调整自己的提案
                await agent.think(
                    f"在看到其他提案后，请调整你的立场:\n{summary}"
                )

    async def _mediate(
        self,
        topic: str,
        agents_dict: Dict[str, Any]
    ):
        """调解冲突

        Args:
            topic: 协商议题
            agents_dict: Agent字典
        """
        # 寻找调解方案
        mediator_prompt = f"""
        作为调解员，请为以下议题寻找妥协方案：

        议题: {topic}

        各方提案:
        {self._format_proposals()}

        请提出一个各方都能接受的调解方案。
        """

        # 简化：使用第一个Agent作为调解员
        if agents_dict:
            first_agent = next(iter(agents_dict.values()))
            mediation = await first_agent.think(mediator_prompt)

            # 创建调解提案
            mediation_proposal = NegotiationProposal(
                agent_id="mediator",
                content=mediation.content
            )

            await self.submit_proposal(mediation_proposal)

    def _extract_agreement(self) -> Optional[str]:
        """提取协议内容"""
        if self.status == NegotiationStatus.AGREEMENT_REACHED:
            # 返回最后一个提案作为协议
            return self.proposals[-1].content if self.proposals else None
        return None

    def _format_proposals(self) -> str:
        """格式化提案"""
        formatted = []
        for proposal in self.proposals:
            formatted.append(
                f"{proposal.agent_id}: {proposal.content[:200]}..."
            )
        return "\n".join(formatted)

    def get_negotiation_info(self) -> Dict[str, Any]:
        """获取协商信息"""
        return {
            "negotiation_id": self.negotiation_id,
            "status": self.status.value,
            "participants": list(self.participants.keys()),
            "proposal_count": len(self.proposals),
            "current_round": self.current_round,
            "max_rounds": self.max_rounds,
            "elapsed_time": (datetime.now() - self.start_time).total_seconds()
        }

    def set_max_rounds(self, max_rounds: int):
        """设置最大轮数

        Args:
            max_rounds: 最大轮数
        """
        if max_rounds > 0:
            self.max_rounds = max_rounds


__all__ = [
    "NegotiationStatus",
    "NegotiationProposal",
    "NegotiationResult",
    "Negotiation"
]
