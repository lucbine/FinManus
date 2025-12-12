from unittest.mock import AsyncMock, patch

import pytest

from app.tool.stock.stock_policy import StockPolicyTool


class TestStockPolicyTool:

    @pytest.fixture
    def tool(self):
        """创建股票政策工具实例"""
        return StockPolicyTool()

    @pytest.mark.asyncio
    async def test_execute_regulation_policies(self, tool):
        """测试执行监管政策查询"""
        result = await tool.execute(query="注册制", policy_type="regulation")

        assert result.output is not None
        assert "查询关键词: 注册制" in result.output
        assert "监管政策信息:" in result.output
        assert "注册制改革配套政策实施细则" in result.output

    @pytest.mark.asyncio
    async def test_execute_trading_rules(self, tool):
        """测试执行交易规则查询"""
        result = await tool.execute(query="交易规则", policy_type="trading")

        assert result.output is not None
        assert "查询关键词: 交易规则" in result.output
        assert "交易规则信息:" in result.output
        assert "科创板交易规则优化方案" in result.output

    @pytest.mark.asyncio
    async def test_execute_listing_policies(self, tool):
        """测试执行上市制度查询"""
        result = await tool.execute(query="上市", policy_type="listing")

        assert result.output is not None
        assert "查询关键词: 上市" in result.output
        assert "上市制度信息:" in result.output
        assert "创业板注册制改革实施方案" in result.output

    @pytest.mark.asyncio
    async def test_execute_announcements(self, tool):
        """测试执行公告通知查询"""
        result = await tool.execute(query="休市", policy_type="announcement")

        assert result.output is not None
        assert "查询关键词: 休市" in result.output
        assert "公告通知信息:" in result.output
        assert "春节休市安排" in result.output

    @pytest.mark.asyncio
    async def test_execute_all_policies(self, tool):
        """测试执行全部政策查询"""
        result = await tool.execute(query="政策", policy_type="all")

        assert result.output is not None
        assert "查询关键词: 政策" in result.output
        assert "=== 监管政策 ===" in result.output
        assert "=== 交易规则 ===" in result.output
        assert "=== 上市制度 ===" in result.output
        assert "=== 公告通知 ===" in result.output

    @pytest.mark.asyncio
    async def test_execute_with_market_filter(self, tool):
        """测试执行带市场过滤的查询"""
        result = await tool.execute(query="注册制", market="ab")

        assert result.output is not None
        assert "市场范围: A股" in result.output

    @pytest.mark.asyncio
    async def test_execute_with_time_range(self, tool):
        """测试执行带时间范围的查询"""
        result = await tool.execute(query="政策", time_range="month")

        assert result.output is not None
        assert "时间范围: 近一月" in result.output

    @pytest.mark.asyncio
    async def test_execute_empty_query(self, tool):
        """测试空查询参数"""
        with pytest.raises(Exception) as exc_info:
            await tool.execute(query="")
        assert "Query keywords are required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_invalid_policy_type(self, tool):
        """测试无效的政策类型"""
        with pytest.raises(Exception) as exc_info:
            await tool.execute(query="政策", policy_type="invalid")
        assert "Invalid policy_type: invalid" in str(exc_info.value)

    def test_get_market_name(self, tool):
        """测试市场名称获取"""
        assert tool._get_market_name("all") == "全部市场"
        assert tool._get_market_name("ab") == "A股"
        assert tool._get_market_name("hk") == "港股"
        assert tool._get_market_name("us") == "美股"
        assert tool._get_market_name("unknown") == "unknown"

    def test_get_time_range_name(self, tool):
        """测试时间范围名称获取"""
        assert tool._get_time_range_name("recent") == "最近"
        assert tool._get_time_range_name("month") == "近一月"
        assert tool._get_time_range_name("quarter") == "近一季度"
        assert tool._get_time_range_name("year") == "近一年"
        assert tool._get_time_range_name("unknown") == "unknown"

    def test_format_regulation_policies(self, tool):
        """测试监管政策格式化"""
        policies = [
            {
                "title": "测试政策",
                "source": "证监会",
                "date": "2024-01-01",
                "summary": "测试摘要",
                "impact": "测试影响",
                "status": "已生效",
            }
        ]

        result = tool._format_regulation_policies(policies, "测试", "all", "recent")

        assert "查询关键词: 测试" in result
        assert "市场范围: 全部市场" in result
        assert "时间范围: 最近" in result
        assert "监管政策信息:" in result
        assert "1. 测试政策" in result
        assert "来源: 证监会" in result

    def test_format_trading_rules(self, tool):
        """测试交易规则格式化"""
        rules = [
            {
                "title": "测试规则",
                "source": "上交所",
                "date": "2024-01-01",
                "summary": "测试摘要",
                "impact": "测试影响",
                "status": "已生效",
            }
        ]

        result = tool._format_trading_rules(rules, "测试", "ab", "month")

        assert "查询关键词: 测试" in result
        assert "市场范围: A股" in result
        assert "时间范围: 近一月" in result
        assert "交易规则信息:" in result
        assert "1. 测试规则" in result
        assert "来源: 上交所" in result

    def test_format_listing_policies(self, tool):
        """测试上市制度格式化"""
        policies = [
            {
                "title": "测试制度",
                "source": "深交所",
                "date": "2024-01-01",
                "summary": "测试摘要",
                "impact": "测试影响",
                "status": "已生效",
            }
        ]

        result = tool._format_listing_policies(policies, "测试", "hk", "quarter")

        assert "查询关键词: 测试" in result
        assert "市场范围: 港股" in result
        assert "时间范围: 近一季度" in result
        assert "上市制度信息:" in result
        assert "1. 测试制度" in result
        assert "来源: 深交所" in result

    def test_format_announcements(self, tool):
        """测试公告通知格式化"""
        announcements = [
            {
                "title": "测试公告",
                "source": "北交所",
                "date": "2024-01-01",
                "summary": "测试摘要",
                "impact": "测试影响",
                "status": "已发布",
            }
        ]

        result = tool._format_announcements(announcements, "测试", "us", "year")

        assert "查询关键词: 测试" in result
        assert "市场范围: 美股" in result
        assert "时间范围: 近一年" in result
        assert "公告通知信息:" in result
        assert "1. 测试公告" in result
        assert "来源: 北交所" in result
