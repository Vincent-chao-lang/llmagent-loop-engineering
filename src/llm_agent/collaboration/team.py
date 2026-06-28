"""
LLM Agent团队协作

支持多个LLM Agent组成团队进行协作。
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class TeamRole(Enum):
    """团队角色"""
    LEADER = "leader"           # 领导者
    SPECIALIST = "specialist"   # 专家
    EXECUTOR = "executor"       # 执行者
    VALIDATOR = "validator"     # 验证者
    OBSERVER = "observer"       # 观察者


@dataclass
class TeamConfig:
    """团队配置"""
    team_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    team_name: str = ""
    goal: str = ""
    max_members: int = 10
    voting_rule: str = "majority"  # majority, unanimous, consensus
    communication_style: str = "direct"  # direct, hierarchical, peer_to_peer


@dataclass
class TeamMember:
    """团队成员"""
    agent_id: str
    role: TeamRole
    capabilities: List[str] = field(default_factory=list)
    join_date: datetime = field(default_factory=datetime.now)
    contribution_score: float = 0.0
    is_active: bool = True


@dataclass
class TeamResult:
    """团队协作结果"""
    team_id: str
    goal: str
    success: bool
    individual_results: List[Any] = field(default_factory=list)
    consensus: Optional[str] = None
    conflict_count: int = 0
    collaboration_quality: float = 0.0
    time_taken: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None  # 协作失败时的错误信息


class LLMAgentTeam:
    """LLM Agent团队

    管理多个LLM Agent的协作
    """

    def __init__(self, config: TeamConfig):
        """初始化Agent团队

        Args:
            config: 团队配置
        """
        self.config = config
        self.members: Dict[str, TeamMember] = {}
        self.shared_memory = {}
        self.collaboration_history = []
        self.active_tasks = []

    def add_member(
        self,
        agent_id: str,
        role: TeamRole,
        capabilities: List[str] = None
    ):
        """添加团队成员

        Args:
            agent_id: Agent ID
            role: 团队角色
            capabilities: 能力列表
        """
        if len(self.members) >= self.config.max_members:
            raise ValueError(f"团队已满，最大成员数: {self.config.max_members}")

        if agent_id in self.members:
            raise ValueError(f"Agent {agent_id} 已在团队中")

        member = TeamMember(
            agent_id=agent_id,
            role=role,
            capabilities=capabilities or []
        )

        self.members[agent_id] = member

    def remove_member(self, agent_id: str):
        """移除团队成员

        Args:
            agent_id: Agent ID
        """
        if agent_id not in self.members:
            raise ValueError(f"Agent {agent_id} 不在团队中")

        del self.members[agent_id]

    def get_member(self, agent_id: str) -> Optional[TeamMember]:
        """获取团队成员

        Args:
            agent_id: Agent ID

        Returns:
            团队成员或None
        """
        return self.members.get(agent_id)

    def list_members(self, role: TeamRole = None) -> List[TeamMember]:
        """列出团队成员

        Args:
            role: 角色筛选（可选）

        Returns:
            成员列表
        """
        members = list(self.members.values())

        if role:
            members = [m for m in members if m.role == role]

        return members

    async def collaborate(
        self,
        task: str,
        agents_dict: Dict[str, Any],
        collaboration_style: str = None
    ) -> TeamResult:
        """团队协作执行任务

        Args:
            task: 任务描述
            agents_dict: Agent字典 {agent_id: agent_instance}
            collaboration_style: 协作风格（可选）

        Returns:
            团队协作结果
        """
        start_time = datetime.now()

        try:
            # 1. 分析任务，确定参与Agent
            relevant_agents = self._identify_relevant_agents(task, agents_dict)

            if not relevant_agents:
                return TeamResult(
                    team_id=self.config.team_id,
                    goal=task,
                    success=False,
                    metadata={"error": "没有相关Agent参与"}
                )

            # 2. 根据协作风格组织协作
            style = collaboration_style or self.config.communication_style

            if style == "hierarchical":
                results = await self._hierarchical_collaboration(
                    task, relevant_agents, agents_dict
                )
            elif style == "peer_to_peer":
                results = await self._peer_to_peer_collaboration(
                    task, relevant_agents, agents_dict
                )
            else:  # direct
                results = await self._direct_collaboration(
                    task, relevant_agents, agents_dict
                )

            # 3. 整合结果
            integrated = self._integrate_results(results)

            # 4. 记录协作历史
            collaboration_record = {
                "task": task,
                "style": style,
                "participants": list(relevant_agents.keys()),
                "results": integrated,
                "timestamp": datetime.now().isoformat()
            }
            self.collaboration_history.append(collaboration_record)

            # 5. 计算协作质量
            quality = self._assess_collaboration_quality(integrated)

            elapsed = (datetime.now() - start_time).total_seconds()

            return TeamResult(
                team_id=self.config.team_id,
                goal=task,
                success=True,
                individual_results=integrated,
                collaboration_quality=quality,
                time_taken=elapsed
            )

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            return TeamResult(
                team_id=self.config.team_id,
                goal=task,
                success=False,
                error=str(e),
                time_taken=elapsed
            )

    async def vote(
        self,
        proposal: str,
        agents_dict: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, bool]:
        """团队投票

        Args:
            proposal: 提案内容
            agents_dict: Agent字典
            timeout: 超时时间

        Returns:
            投票结果 {agent_id: vote}
        """
        votes = {}

        # 为每个成员获取投票
        for member_id, member in self.members.items():
            if not member.is_active:
                continue

            agent = agents_dict.get(member_id)
            if not agent:
                continue

            try:
                # 让Agent对提案进行思考并投票
                response = await asyncio.wait_for(
                    agent.think(f"请对以下提案进行投票: {proposal}"),
                    timeout=timeout
                )

                # 简化的投票逻辑：根据置信度决定
                vote = response.confidence > 0.6
                votes[member_id] = vote

            except asyncio.TimeoutError:
                votes[member_id] = False  # 超时视为反对
            except Exception:
                votes[member_id] = False  # 错误视为反对

        return votes

    async def consensus(
        self,
        topic: str,
        agents_dict: Dict[str, Any]
    ) -> Optional[str]:
        """达成共识

        Args:
            topic: 议题
            agents_dict: Agent字典

        Returns:
            共识结果或None
        """
        # 简化实现：通过多数投票达成共识
        votes = await self.vote(topic, agents_dict)

        agree_count = sum(1 for v in votes.values() if v)
        total_count = len(votes)

        if agree_count > total_count / 2:
            return "consensus_reached"

        return None

    def _identify_relevant_agents(
        self,
        task: str,
        agents_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """识别相关Agent

        Args:
            task: 任务描述
            agents_dict: Agent字典

        Returns:
            相关Agent字典
        """
        # 简化实现：返回所有在团队中的Agent
        relevant = {}

        for member_id in self.members.keys():
            if member_id in agents_dict:
                relevant[member_id] = agents_dict[member_id]

        return relevant

    async def _hierarchical_collaboration(
        self,
        task: str,
        agents: Dict[str, Any],
        all_agents: Dict[str, Any]
    ) -> List[Any]:
        """层级协作"""
        # 领导者制定计划
        leaders = [m for m in self.members.values() if m.role == TeamRole.LEADER]

        if leaders:
            leader = leaders[0]
            leader_agent = all_agents.get(leader.agent_id)

            if leader_agent:
                plan = await leader_agent.plan(f"制定团队协作计划: {task}")

        # 专家并行执行
        specialists = [m for m in self.members.values() if m.role == TeamRole.SPECIALIST]

        tasks = []
        for specialist in specialists:
            agent = all_agents.get(specialist.agent_id)
            if agent:
                tasks.append(agent.execute(f"执行任务: {task}"))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return [r for r in results if not isinstance(r, Exception)]

        return []

    async def _peer_to_peer_collaboration(
        self,
        task: str,
        agents: Dict[str, Any],
        all_agents: Dict[str, Any]
    ) -> List[Any]:
        """点对点协作"""
        # 所有Agent并行处理，然后整合结果
        tasks = []

        for agent_id, agent in agents.items():
            tasks.append(agent.execute(f"协作处理: {task}"))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return [r for r in results if not isinstance(r, Exception)]

        return []

    async def _direct_collaboration(
        self,
        task: str,
        agents: Dict[str, Any],
        all_agents: Dict[str, Any]
    ) -> List[Any]:
        """直接协作"""
        # 简化的直接协作：按角色顺序执行
        results = []

        # 1. 规划者
        planners = [m for m in self.members.values() if m.role == TeamRole.LEADER]
        if planners:
            planner_agent = all_agents.get(planners[0].agent_id)
            if planner_agent:
                plan_result = await planner_agent.plan(task)
                results.append({"role": "planner", "result": plan_result})

        # 2. 执行者
        executors = [m for m in self.members.values() if m.role == TeamRole.EXECUTOR]
        for executor in executors:
            executor_agent = all_agents.get(executor.agent_id)
            if executor_agent:
                exec_result = await executor_agent.execute(task)
                results.append({"role": "executor", "result": exec_result})

        # 3. 验证者
        validators = [m for m in self.members.values() if m.role == TeamRole.VALIDATOR]
        for validator in validators:
            validator_agent = all_agents.get(validator.agent_id)
            if validator_agent:
                # 反思验证
                reflection = await validator_agent.reflect(task, results)
                results.append({"role": "validator", "result": reflection})

        return results

    def _integrate_results(self, results: List[Any]) -> List[Any]:
        """整合结果"""
        return results

    def _assess_collaboration_quality(self, results: List[Any]) -> float:
        """评估协作质量"""
        if not results:
            return 0.0

        # 简化评估：基于成功率
        success_count = sum(
            1 for r in results
            if isinstance(r, dict) and r.get("success", True)
        )

        return success_count / len(results)

    def get_team_info(self) -> Dict[str, Any]:
        """获取团队信息"""
        active_members = [m for m in self.members.values() if m.is_active]

        role_distribution = {}
        for member in self.members.values():
            role = member.role.value
            if role not in role_distribution:
                role_distribution[role] = 0
            role_distribution[role] += 1

        return {
            "team_id": self.config.team_id,
            "team_name": self.config.team_name,
            "goal": self.config.goal,
            "total_members": len(self.members),
            "active_members": len(active_members),
            "max_members": self.config.max_members,
            "role_distribution": role_distribution,
            "collaboration_count": len(self.collaboration_history)
        }

    def update_shared_memory(self, key: str, value: Any):
        """更新共享记忆

        Args:
            key: 键
            value: 值
        """
        self.shared_memory[key] = value

    def get_shared_memory(self, key: str) -> Any:
        """获取共享记忆

        Args:
            key: 键

        Returns:
            值
        """
        return self.shared_memory.get(key)


__all__ = [
    "TeamRole",
    "TeamConfig",
    "TeamMember",
    "TeamResult",
    "LLMAgentTeam"
]
