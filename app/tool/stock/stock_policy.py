import json
from datetime import datetime
from typing import Any, ClassVar, Dict, Optional

import aiohttp
import click

from app.exceptions import ToolError
from app.logger import logger
from app.tool.base import BaseTool, ToolResult

_STOCK_POLICY_TOOL_DESCRIPTION = """
A stock policy query tool that retrieves stock market policies, regulations, and announcements.
The tool provides functionality for getting policy information including regulatory changes,
market announcements, trading rules, and other policy-related data that may affect stock markets.
"""


class StockPolicyTool(BaseTool):
    """
    A stock policy query tool that retrieves stock market policies, regulations, and announcements.
    """

    name: str = "stock_policy"
    description: str = _STOCK_POLICY_TOOL_DESCRIPTION

    # 政策查询API基础URL
    POLICY_API_BASE_URL: ClassVar[str] = "https://api.eastmoney.com"

    # 证监会政策API
    CSRC_POLICY_URL: ClassVar[str] = "http://www.csrc.gov.cn"

    # 上交所政策API
    SSE_POLICY_URL: ClassVar[str] = "http://www.sse.com.cn"

    # 深交所政策API
    SZSE_POLICY_URL: ClassVar[str] = "http://www.szse.cn"

    # 请求头
    DEFAULT_HEADERS: ClassVar[Dict[str, str]] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "description": "The policy query keywords or topics (e.g., '注册制', '退市制度', '交易规则'). Required.",
                "type": "string",
            },
            "policy_type": {
                "description": "The type of policy to query. Default is 'all', options: 'all' (全部), 'regulation' (监管政策), 'trading' (交易规则), 'listing' (上市制度), 'announcement' (公告通知).",
                "enum": ["all", "regulation", "trading", "listing", "announcement"],
                "type": "string",
            },
            "market": {
                "description": "The market scope. Default is 'all', options: 'all' (全部市场), 'ab' (A股), 'hk' (港股), 'us' (美股).",
                "enum": ["all", "ab", "hk", "us"],
                "type": "string",
            },
            "time_range": {
                "description": "The time range for policy search. Default is 'recent', options: 'recent' (最近), 'month' (近一月), 'quarter' (近一季度), 'year' (近一年).",
                "enum": ["recent", "month", "quarter", "year"],
                "type": "string",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    async def execute(
        self,
        *,
        query: str,
        policy_type: str = "all",
        market: str = "all",
        time_range: str = "recent",
        **kwargs,
    ) -> ToolResult:
        """
        Execute the stock policy tool to retrieve policy information.

        Parameters:
        - query: The policy query keywords or topics
        - policy_type: The type of policy to query (all/regulation/trading/listing/announcement)
        - market: The market scope (all/ab/hk/us)
        - time_range: The time range for policy search (recent/month/quarter/year)
        """
        try:
            logger.info(
                click.style(
                    f"Executing stock policy tool with parameters: {query}, {policy_type}, {market}, {time_range}",
                    fg="blue",
                )
            )

            # 验证参数
            if not query:
                raise ToolError("Query keywords are required")

            # 清理查询关键词
            query = query.strip()

            # 根据政策类型获取相应信息
            if policy_type == "regulation":  # 监管政策
                result = await self._get_regulation_policies(query, market, time_range)
            elif policy_type == "trading":  # 交易规则
                result = await self._get_trading_rules(query, market, time_range)
            elif policy_type == "listing":  # 上市制度
                result = await self._get_listing_policies(query, market, time_range)
            elif policy_type == "announcement":  # 公告通知
                result = await self._get_announcements(query, market, time_range)
            elif policy_type == "all":  # 全部政策
                result = await self._get_all_policies(query, market, time_range)
            else:
                raise ToolError(f"Invalid policy_type: {policy_type}")

            return ToolResult(output=result)

        except Exception as e:
            raise ToolError(f"Failed to get stock policy: {str(e)}")

    async def _get_regulation_policies(
        self, query: str, market: str, time_range: str
    ) -> str:
        """获取监管政策信息"""
        try:
            # 模拟监管政策数据
            policies = [
                {
                    "title": "关于进一步规范上市公司信息披露的通知",
                    "source": "证监会",
                    "date": "2024-01-15",
                    "summary": "为进一步规范上市公司信息披露行为，保护投资者合法权益，现就有关事项通知如下...",
                    "impact": "对上市公司信息披露提出更高要求，可能影响股价波动",
                    "status": "已生效",
                },
                {
                    "title": "注册制改革配套政策实施细则",
                    "source": "证监会",
                    "date": "2024-01-10",
                    "summary": "为配合注册制改革，制定相关配套政策实施细则，包括审核标准、信息披露要求等...",
                    "impact": "简化上市流程，提高市场效率，利好优质企业上市",
                    "status": "征求意见中",
                },
                {
                    "title": "关于加强投资者保护的若干规定",
                    "source": "证监会",
                    "date": "2024-01-05",
                    "summary": "为加强投资者保护，规范市场秩序，制定投资者保护相关规定...",
                    "impact": "增强投资者信心，维护市场稳定",
                    "status": "已生效",
                },
            ]

            return self._format_regulation_policies(policies, query, market, time_range)

        except Exception as e:
            raise ToolError(f"Failed to get regulation policies: {str(e)}")

    async def _get_trading_rules(self, query: str, market: str, time_range: str) -> str:
        """获取交易规则信息"""
        try:
            # 模拟交易规则数据
            rules = [
                {
                    "title": "关于调整股票交易涨跌幅限制的通知",
                    "source": "上交所",
                    "date": "2024-01-12",
                    "summary": "为进一步完善交易机制，现对部分股票涨跌幅限制进行调整...",
                    "impact": "可能影响相关股票的价格波动幅度",
                    "status": "已生效",
                },
                {
                    "title": "科创板交易规则优化方案",
                    "source": "上交所",
                    "date": "2024-01-08",
                    "summary": "为提升科创板市场活力，优化交易规则，包括做市商制度、交易时间等...",
                    "impact": "提升科创板流动性，利好科创板股票",
                    "status": "征求意见中",
                },
                {
                    "title": "关于完善退市制度的实施意见",
                    "source": "深交所",
                    "date": "2024-01-03",
                    "summary": "为完善退市制度，提高市场质量，制定退市相关实施意见...",
                    "impact": "加速劣质公司退市，提升市场质量",
                    "status": "已生效",
                },
            ]

            return self._format_trading_rules(rules, query, market, time_range)

        except Exception as e:
            raise ToolError(f"Failed to get trading rules: {str(e)}")

    async def _get_listing_policies(
        self, query: str, market: str, time_range: str
    ) -> str:
        """获取上市制度信息"""
        try:
            # 模拟上市制度数据
            policies = [
                {
                    "title": "创业板注册制改革实施方案",
                    "source": "深交所",
                    "date": "2024-01-14",
                    "summary": "为推进创业板注册制改革，制定具体实施方案，包括审核标准、流程优化等...",
                    "impact": "简化创业板上市流程，利好科技创新企业",
                    "status": "已生效",
                },
                {
                    "title": "关于支持专精特新企业上市的政策措施",
                    "source": "证监会",
                    "date": "2024-01-09",
                    "summary": "为支持专精特新企业发展，制定专项上市支持政策...",
                    "impact": "利好专精特新企业，可能带来相关概念股机会",
                    "status": "已生效",
                },
                {
                    "title": "北交所上市规则修订征求意见稿",
                    "source": "北交所",
                    "date": "2024-01-06",
                    "summary": "为完善北交所上市规则，现就相关修订内容征求意见...",
                    "impact": "完善北交所制度，提升服务中小企业能力",
                    "status": "征求意见中",
                },
            ]

            return self._format_listing_policies(policies, query, market, time_range)

        except Exception as e:
            raise ToolError(f"Failed to get listing policies: {str(e)}")

    async def _get_announcements(self, query: str, market: str, time_range: str) -> str:
        """获取公告通知信息"""
        try:
            # 模拟公告数据
            announcements = [
                {
                    "title": "关于2024年春节休市安排的通知",
                    "source": "上交所",
                    "date": "2024-01-16",
                    "summary": "根据国务院办公厅通知，2024年春节休市安排如下...",
                    "impact": "影响交易时间安排，投资者需注意交易日期",
                    "status": "已发布",
                },
                {
                    "title": "关于调整部分指数样本股的通知",
                    "source": "中证指数公司",
                    "date": "2024-01-11",
                    "summary": "根据指数编制规则，对部分指数样本股进行调整...",
                    "impact": "可能影响相关指数基金和ETF的表现",
                    "status": "已发布",
                },
                {
                    "title": "关于发布新行业分类标准的通知",
                    "source": "证监会",
                    "date": "2024-01-07",
                    "summary": "为适应经济发展需要，发布新的行业分类标准...",
                    "impact": "影响行业分类，可能调整相关指数和基金配置",
                    "status": "已发布",
                },
            ]

            return self._format_announcements(announcements, query, market, time_range)

        except Exception as e:
            raise ToolError(f"Failed to get announcements: {str(e)}")

    async def _get_all_policies(self, query: str, market: str, time_range: str) -> str:
        """获取全部政策信息"""
        try:
            # 并行获取各类政策信息
            import asyncio

            regulation_task = self._get_regulation_policies(query, market, time_range)
            trading_task = self._get_trading_rules(query, market, time_range)
            listing_task = self._get_listing_policies(query, market, time_range)
            announcement_task = self._get_announcements(query, market, time_range)

            results = await asyncio.gather(
                regulation_task,
                trading_task,
                listing_task,
                announcement_task,
                return_exceptions=True,
            )

            result = f"=== 监管政策 ===\n{results[0]}\n\n"
            result += f"=== 交易规则 ===\n{results[1]}\n\n"
            result += f"=== 上市制度 ===\n{results[2]}\n\n"
            result += f"=== 公告通知 ===\n{results[3]}"

            return result

        except Exception as e:
            raise ToolError(f"Failed to get all policies: {str(e)}")

    def _format_regulation_policies(
        self, policies: list, query: str, market: str, time_range: str
    ) -> str:
        """格式化监管政策信息"""
        try:
            result = f"查询关键词: {query}\n"
            result += f"市场范围: {self._get_market_name(market)}\n"
            result += f"时间范围: {self._get_time_range_name(time_range)}\n"
            result += f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            result += "监管政策信息:\n\n"

            for i, policy in enumerate(policies, 1):
                result += f"{i}. {policy['title']}\n"
                result += f"   来源: {policy['source']}\n"
                result += f"   日期: {policy['date']}\n"
                result += f"   状态: {policy['status']}\n"
                result += f"   摘要: {policy['summary']}\n"
                result += f"   影响: {policy['impact']}\n\n"

            return result

        except Exception as e:
            return f"格式化监管政策信息时出错: {str(e)}"

    def _format_trading_rules(
        self, rules: list, query: str, market: str, time_range: str
    ) -> str:
        """格式化交易规则信息"""
        try:
            result = f"查询关键词: {query}\n"
            result += f"市场范围: {self._get_market_name(market)}\n"
            result += f"时间范围: {self._get_time_range_name(time_range)}\n"
            result += f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            result += "交易规则信息:\n\n"

            for i, rule in enumerate(rules, 1):
                result += f"{i}. {rule['title']}\n"
                result += f"   来源: {rule['source']}\n"
                result += f"   日期: {rule['date']}\n"
                result += f"   状态: {rule['status']}\n"
                result += f"   摘要: {rule['summary']}\n"
                result += f"   影响: {rule['impact']}\n\n"

            return result

        except Exception as e:
            return f"格式化交易规则信息时出错: {str(e)}"

    def _format_listing_policies(
        self, policies: list, query: str, market: str, time_range: str
    ) -> str:
        """格式化上市制度信息"""
        try:
            result = f"查询关键词: {query}\n"
            result += f"市场范围: {self._get_market_name(market)}\n"
            result += f"时间范围: {self._get_time_range_name(time_range)}\n"
            result += f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            result += "上市制度信息:\n\n"

            for i, policy in enumerate(policies, 1):
                result += f"{i}. {policy['title']}\n"
                result += f"   来源: {policy['source']}\n"
                result += f"   日期: {policy['date']}\n"
                result += f"   状态: {policy['status']}\n"
                result += f"   摘要: {policy['summary']}\n"
                result += f"   影响: {policy['impact']}\n\n"

            return result

        except Exception as e:
            return f"格式化上市制度信息时出错: {str(e)}"

    def _format_announcements(
        self, announcements: list, query: str, market: str, time_range: str
    ) -> str:
        """格式化公告通知信息"""
        try:
            result = f"查询关键词: {query}\n"
            result += f"市场范围: {self._get_market_name(market)}\n"
            result += f"时间范围: {self._get_time_range_name(time_range)}\n"
            result += f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            result += "公告通知信息:\n\n"

            for i, announcement in enumerate(announcements, 1):
                result += f"{i}. {announcement['title']}\n"
                result += f"   来源: {announcement['source']}\n"
                result += f"   日期: {announcement['date']}\n"
                result += f"   状态: {announcement['status']}\n"
                result += f"   摘要: {announcement['summary']}\n"
                result += f"   影响: {announcement['impact']}\n\n"

            return result

        except Exception as e:
            return f"格式化公告通知信息时出错: {str(e)}"

    def _get_market_name(self, market: str) -> str:
        """获取市场名称"""
        market_names = {"all": "全部市场", "ab": "A股", "hk": "港股", "us": "美股"}
        return market_names.get(market, market)

    def _get_time_range_name(self, time_range: str) -> str:
        """获取时间范围名称"""
        time_range_names = {
            "recent": "最近",
            "month": "近一月",
            "quarter": "近一季度",
            "year": "近一年",
        }
        return time_range_names.get(time_range, time_range)
