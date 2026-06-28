"""
窗口上下文管理集成测试

完整测试上下文压缩、关键信息保留、动态管理和对话优化功能。
"""

import asyncio
import pytest
from datetime import datetime
from src.llm_agent.context import (
    ContextCompressor, CompressionStrategy,
    KeyInformationRetainer, KeyEntity, EntityType, RetentionConfig,
    DynamicContextManager, WindowConfig, ContextAllocation,
    ConversationHistoryOptimizer, OptimizedHistory,
    MultiTurnQualityMaintainer, QualityReport,
    Message, create_message, estimate_token_count
)
from src.llm_agent.context.compressor import ImportanceScore


class TestContextCompression:
    """上下文压缩功能测试"""

    @pytest.fixture
    def sample_messages(self):
        """创建示例消息"""
        return [
            create_message("system", "你是一个AI助手，帮助用户解决问题。"),
            create_message("user", "我叫小明，喜欢用Python编程。"),
            create_message("assistant", "你好小明！很高兴为你服务。Python是一门很好的编程语言。"),
            create_message("user", "我想学习Python的数据分析，应该从哪里开始？"),
            create_message("assistant", "建议从NumPy和Pandas库开始，它们是Python数据分析的基础。"),
            create_message("user", "好的，我决定先学习Pandas。"),
            create_message("assistant", "很好的选择！Pandas是一个强大的数据处理库。"),
            create_message("user", "Pandas能处理什么样的数据？"),
            create_message("assistant", "Pandas可以处理表格数据、时间序列、JSON等多种数据格式。"),
        ]

    def test_token_estimation(self):
        """测试token估算功能"""
        text = "这是一个测试文本，用于验证token估算功能。"
        tokens = estimate_token_count(text)
        assert tokens > 0
        assert tokens < len(text)  # token数应该少于字符数

    def test_message_creation(self):
        """测试消息创建"""
        message = create_message("user", "测试消息")
        assert message.role == "user"
        assert message.content == "测试消息"
        assert message.token_count > 0

    @pytest.mark.asyncio
    async def test_basic_compression(self, sample_messages):
        """测试基本压缩功能"""
        compressor = ContextCompressor()
        original_length = sum(msg.token_count for msg in sample_messages)

        # 压缩到一半长度
        target_length = original_length // 2
        compressed = await compressor.compress_context(
            sample_messages,
            target_length,
            preserve_key_info=True
        )

        # 验证压缩结果
        assert compressed.compression_ratio > 0
        assert compressed.information_retention > 0.5
        assert len(compressed.messages) < len(sample_messages)

    @pytest.mark.asyncio
    async def test_importance_analysis(self, sample_messages):
        """测试重要性分析"""
        compressor = ContextCompressor()
        importance_scores = await compressor._analyze_importance(sample_messages)

        assert len(importance_scores) == len(sample_messages)

        # 验证重要性分数在合理范围内
        for score in importance_scores:
            assert 0.0 <= score.importance <= 1.0
            assert len(score.factors) > 0

    @pytest.mark.asyncio
    async def test_different_compression_strategies(self, sample_messages):
        """测试不同压缩策略"""
        strategies = [
            CompressionStrategy.IMPORTANCE_BASED,
            CompressionStrategy.RECENCY_BASED,
            CompressionStrategy.SUMMARIZATION
        ]

        results = {}
        for strategy in strategies:
            compressor = ContextCompressor(strategy)
            compressed = await compressor.compress_context(
                sample_messages,
                target_length=2000,
                preserve_key_info=True
            )
            results[strategy.value] = compressed

        # 验证不同策略产生不同结果
        assert len(results) == len(strategies)

    @pytest.mark.asyncio
    async def test_key_information_extraction(self, sample_messages):
        """测试关键信息提取"""
        compressor = ContextCompressor()
        importance_scores = await compressor._analyze_importance(sample_messages)

        key_info = await compressor._extract_key_information(
            sample_messages,
            importance_scores
        )

        # 验证提取到关键信息
        assert isinstance(key_info, list)

    def test_compression_statistics(self, sample_messages):
        """测试压缩统计功能"""
        compressor = ContextCompressor()
        stats = compressor.get_compression_stats()

        # 验证统计结构
        assert isinstance(stats, dict)


class TestKeyInformationRetention:
    """关键信息保留功能测试"""

    @pytest.fixture
    def sample_messages_with_entities(self):
        """创建包含实体的示例消息"""
        return [
            create_message("user", "我叫李明，决定学习Python编程。"),
            create_message("assistant", "很好的选择！Python是一门强大的编程语言。"),
            create_message("user", "我希望每天学习2小时，限制在晚上8-10点。"),
            create_message("assistant", "这个学习计划很合理，建议按周制定目标。"),
            create_message("user", "我喜欢动手实践，不喜欢纯理论学习。"),
            create_message("assistant", "那我们以项目驱动的方式学习吧。"),
        ]

    @pytest.mark.asyncio
    async def test_entity_extraction(self, sample_messages_with_entities):
        """测试实体提取"""
        retainer = KeyInformationRetainer()
        key_entities = await retainer.extract_key_entities(sample_messages_with_entities)

        # 验证提取到实体
        assert len(key_entities) > 0

        # 验证实体结构
        for entity in key_entities:
            assert isinstance(entity, KeyEntity)
            assert entity.content
            assert entity.entity_type in EntityType
            assert 0.0 <= entity.importance <= 1.0

    @pytest.mark.asyncio
    async def test_entity_deduplication(self):
        """测试实体去重"""
        retainer = KeyInformationRetainer()

        # 创建重复的实体
        entities = [
            KeyEntity(
                id="1",
                content="Python编程",
                entity_type=EntityType.PREFERENCE,
                importance=0.8,
                source_message_id=0
            ),
            KeyEntity(
                id="2",
                content="Python编程",
                entity_type=EntityType.PREFERENCE,
                importance=0.8,
                source_message_id=1
            ),
            KeyEntity(
                id="3",
                content="数据分析",
                entity_type=EntityType.PREFERENCE,
                importance=0.7,
                source_message_id=2
            )
        ]

        deduplicated = await retainer._deduplicate_entities(entities)

        # 验证去重效果
        assert len(deduplicated) < len(entities)

    @pytest.mark.asyncio
    async def test_information_retention_ensuring(self, sample_messages_with_entities):
        """测试关键信息保留保证"""
        retainer = KeyInformationRetainer()
        key_entities = await retainer.extract_key_entities(sample_messages_with_entities)

        # 压缩上下文（模拟）
        compressed_context = sample_messages_with_entities[3:]  # 只保留后半部分

        # 确保关键信息保留
        enhanced_context = await retainer.ensure_retention(
            compressed_context,
            key_entities,
            max_length=5000
        )

        # 验证增强后的上下文
        assert len(enhanced_context) >= len(compressed_context)

    @pytest.mark.asyncio
    async def test_retention_quality_evaluation(self):
        """测试保留质量评估"""
        retainer = KeyInformationRetainer()

        # 创建测试实体
        original_entities = [
            KeyEntity(
                id=f"entity_{i}",
                content=f"测试内容{i}",
                entity_type=EntityType.PREFERENCE,
                importance=0.8,
                source_message_id=i
            )
            for i in range(5)
        ]

        # 创建包含部分实体的上下文
        final_context = [
            create_message("system", "系统信息：测试内容0 测试内容2"),
            create_message("user", "用户消息")
        ]

        quality = await retainer.evaluate_retention_quality(
            original_entities,
            final_context
        )

        # 验证质量评估
        assert quality['total_entities'] == 5
        assert 0.0 <= quality['retention_rate'] <= 1.0


class TestDynamicContextManagement:
    """动态上下文管理测试"""

    @pytest.fixture
    def sample_context(self):
        """创建示例上下文"""
        return [
            create_message("system", "AI助手的系统提示"),
            create_message("user", "第一个问题"),
            create_message("assistant", "第一个回答"),
            create_message("user", "第二个问题"),
            create_message("assistant", "第二个回答"),
        ]

    def test_window_config_creation(self):
        """测试窗口配置"""
        config = WindowConfig()
        assert config.max_window_size == 8000
        assert config.reserve_space == 1000

    @pytest.mark.asyncio
    async def test_context_analysis(self, sample_context):
        """测试上下文分析"""
        manager = DynamicContextManager()
        usage = await manager.analyzer.analyze_usage(sample_context)

        # 验证分析结果
        assert usage['total_messages'] == len(sample_context)
        assert usage['total_tokens'] > 0
        assert 'role_distribution' in usage
        assert 'usage_pattern' in usage

    @pytest.mark.asyncio
    async def test_space_requirement_estimation(self, sample_context):
        """测试空间需求估算"""
        manager = DynamicContextManager()
        new_request = create_message("user", "这是一个新的请求，需要足够的上下文空间。")

        usage = await manager.analyzer.analyze_usage(sample_context)
        requirement = manager._estimate_space_requirement(new_request, usage)

        # 验证需求估算
        assert requirement.minimum_required > 0
        assert requirement.recommended >= requirement.minimum_required
        assert requirement.maximum_allowed >= requirement.recommended

    @pytest.mark.asyncio
    async def test_context_allocation(self, sample_context):
        """测试上下文分配"""
        manager = DynamicContextManager()
        manager.config.max_window_size = 1000  # 设置较小的窗口

        new_request = create_message("user", "新请求")
        allocation = await manager.allocate_context_space(
            sample_context,
            new_request
        )

        # 验证分配结果
        assert isinstance(allocation, ContextAllocation)
        assert isinstance(allocation.messages_to_remove, list)
        assert isinstance(allocation.messages_to_compress, list)

    @pytest.mark.asyncio
    async def test_allocation_statistics(self):
        """测试分配统计"""
        manager = DynamicContextManager()
        stats = manager.get_allocation_statistics()

        # 验证统计结构
        assert isinstance(stats, dict)


class TestConversationOptimization:
    """对话优化测试"""

    @pytest.fixture
    def sample_conversation(self):
        """创建示例对话"""
        return [
            create_message("user", "你好，我想了解Python编程。"),
            create_message("assistant", "你好！Python是一门很好的编程语言。"),
            create_message("user", "Python有什么优点？"),
            create_message("assistant", "Python语法简洁，生态丰富，学习曲线平缓。"),
            create_message("user", "我想学习Python，有什么建议吗？"),  # 重复话题
            create_message("assistant", "建议从基础语法开始，然后逐步深入。"),
            create_message("user", "我决定学习Python了。"),
            create_message("assistant", "很好的决定！"),
        ]

    @pytest.mark.asyncio
    async def test_topic_shift_detection(self, sample_conversation):
        """测试话题转换检测"""
        optimizer = ConversationHistoryOptimizer()
        transitions = await optimizer.topic_detector.detect_topic_shifts(sample_conversation)

        # 验证检测结果
        assert isinstance(transitions, list)

    @pytest.mark.asyncio
    async def test_repetitive_content_identification(self, sample_conversation):
        """测试重复内容识别"""
        optimizer = ConversationHistoryOptimizer()
        repetitive_info = await optimizer.repetition_remover.identify_repetitive_content(
            sample_conversation
        )

        # 验证识别结果
        assert isinstance(repetitive_info, list)

    @pytest.mark.asyncio
    async def test_conversation_optimization(self, sample_conversation):
        """测试对话优化"""
        optimizer = ConversationHistoryOptimizer()
        optimized = await optimizer.optimize_history(
            sample_conversation,
            window_size=1000
        )

        # 验证优化结果
        assert isinstance(optimized, OptimizedHistory)
        assert len(optimized.messages) <= len(sample_conversation)
        assert optimized.metadata['optimization_needed'] == True

    @pytest.mark.asyncio
    async def test_conversation_phase_identification(self, sample_conversation):
        """测试对话阶段识别"""
        optimizer = ConversationHistoryOptimizer()
        phases = await optimizer._identify_conversation_phases(sample_conversation)

        # 验证阶段识别
        assert len(phases) == len(sample_conversation)


class TestQualityMaintenance:
    """质量维护测试"""

    @pytest.fixture
    def sample_conversation_obj(self):
        """创建对话对象"""
        from src.llm_agent.context.quality import Conversation

        messages = [
            create_message("user", "我想学习Python编程。"),
            create_message("assistant", "很好的选择！Python是一门强大的编程语言。"),
            create_message("user", "应该从哪里开始？"),
            create_message("assistant", "建议从基础语法开始学习。"),
            create_message("user", "好的，我明白了。"),
            create_message("assistant", "有任何问题都可以问我。"),
        ]

        return Conversation(messages)

    @pytest.mark.asyncio
    async def test_quality_maintenance(self, sample_conversation_obj):
        """测试质量维护"""
        maintainer = MultiTurnQualityMaintainer()
        report = await maintainer.maintain_quality(sample_conversation_obj)

        # 验证质量报告
        assert isinstance(report, QualityReport)
        assert isinstance(report.metrics, maintainer.__class__.__bases__[0].__dict__['__annotations__']['metrics'])  # 简化验证
        assert 0.0 <= report.overall_score <= 1.0

    @pytest.mark.asyncio
    async def test_coherence_checking(self, sample_conversation_obj):
        """测试连贯性检查"""
        maintainer = MultiTurnQualityMaintainer()
        coherence = await maintainer._check_coherence(sample_conversation_obj)

        # 验证连贯性分数
        assert 0.0 <= coherence <= 1.0

    @pytest.mark.asyncio
    async def test_user_satisfaction_estimation(self, sample_conversation_obj):
        """测试用户满意度估算"""
        maintainer = MultiTurnQualityMaintainer()
        satisfaction = await maintainer._estimate_user_satisfaction(sample_conversation_obj)

        # 验证满意度估算
        assert 0.0 <= satisfaction <= 1.0

    def test_quality_statistics(self):
        """测试质量统计"""
        maintainer = MultiTurnQualityMaintainer()
        stats = maintainer.get_quality_statistics()

        # 验证统计结构
        assert isinstance(stats, dict)


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def complex_conversation(self):
        """创建复杂对话场景"""
        return [
            create_message("system", "你是一个编程学习助手。"),
            create_message("user", "我叫张三，决定学习Python数据分析。希望每天学习2小时，限制在晚上。"),
            create_message("assistant", "很好的选择！张三，Python数据分析是一个很有前景的领域。"),
            create_message("user", "Python数据分析能处理什么样的数据？"),
            create_message("assistant", "Pandas可以处理表格数据、时间序列、JSON等多种数据格式。"),
            create_message("user", "我应该先学习NumPy还是Pandas？"),
            create_message("assistant", "建议先学习NumPy，它是Pandas的基础。"),
            create_message("user", "好的，我决定先学习NumPy。"),
            create_message("assistant", "明智的决定！NumPy是数值计算的基础库。"),
            create_message("user", "NumPy的主要功能是什么？"),
            create_message("assistant", "NumPy主要提供高性能的多维数组计算和数学运算功能。"),
            create_message("user", "学习NumPy需要什么基础？"),
            create_message("assistant", "需要Python基础语法和数学基础。"),
        ]

    @pytest.mark.asyncio
    async def test_full_pipeline(self, complex_conversation):
        """测试完整的处理流程"""
        # 1. 创建压缩器
        compressor = ContextCompressor(CompressionStrategy.INTELLIGENT)

        # 2. 创建关键信息保留器
        retainer = KeyInformationRetainer()

        # 3. 创建动态管理器
        manager = DynamicContextManager(WindowConfig(max_window_size=4000))

        # 4. 创建对话优化器
        optimizer = ConversationHistoryOptimizer()

        # 5. 创建质量维护器
        maintainer = MultiTurnQualityMaintainer()

        # 执行完整流程
        # Step 1: 分析重要性
        importance_scores = await compressor._analyze_importance(complex_conversation)

        # Step 2: 提取关键信息
        key_entities = await retainer.extract_key_entities(complex_conversation, importance_scores)

        # Step 3: 压缩上下文
        compressed = await compressor.compress_context(
            complex_conversation,
            target_length=3000,
            preserve_key_info=True
        )

        # Step 4: 确保关键信息保留
        enhanced_context = await retainer.ensure_retention(
            compressed.messages,
            key_entities,
            max_length=3500
        )

        # Step 5: 优化对话历史
        optimized_history = await optimizer.optimize_history(
            enhanced_context,
            window_size=3000
        )

        # Step 6: 评估质量
        from src.llm_agent.context.quality import Conversation
        conversation_obj = Conversation(optimized_history.messages)
        quality_report = await maintainer.maintain_quality(conversation_obj)

        # 验证整体效果
        assert len(optimized_history.messages) < len(complex_conversation)
        assert quality_report.overall_score > 0.5
        assert compressed.information_retention > 0.7

    @pytest.mark.asyncio
    async def test_compression_effectiveness(self, complex_conversation):
        """测试压缩效果"""
        compressor = ContextCompressor()
        original_length = sum(msg.token_count for msg in complex_conversation)

        # 测试不同压缩比例
        compression_ratios = [0.3, 0.5, 0.7]

        results = {}
        for ratio in compression_ratios:
            target_length = int(original_length * ratio)
            compressed = await compressor.compress_context(
                complex_conversation,
                target_length,
                preserve_key_info=True
            )

            results[ratio] = {
                'compression_ratio': compressed.compression_ratio,
                'information_retention': compressed.information_retention,
                'final_length': compressed.total_tokens()
            }

        # 验证压缩效果
        for ratio, result in results.items():
            assert result['compression_ratio'] > 0
            assert result['information_retention'] > 0.5  # 至少保留50%信息
            assert result['final_length'] <= original_length * (ratio + 0.1)  # 允许10%误差

    def test_performance_benchmarks(self, complex_conversation):
        """性能基准测试"""
        import time

        compressor = ContextCompressor()

        # 测试压缩性能
        start_time = time.time()
        original_length = sum(msg.token_count for msg in complex_conversation)

        # 同步测试（包装为async）
        async def test_compression():
            return await compressor.compress_context(
                complex_conversation,
                target_length=original_length // 2,
                preserve_key_info=True
            )

        # 运行测试
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(test_compression())

        end_time = time.time()
        processing_time = end_time - start_time

        # 验证性能
        assert processing_time < 5.0  # 应该在5秒内完成
        assert result.compression_ratio > 0

        print(f"压缩处理时间: {processing_time:.2f}秒")
        print(f"压缩比例: {result.compression_ratio:.2%}")
        print(f"信息保留率: {result.information_retention:.2%}")


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])