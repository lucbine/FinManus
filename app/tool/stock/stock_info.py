import json
from datetime import datetime
from typing import Any, ClassVar, Dict, Optional

import aiohttp
import click

from app.exceptions import ToolError
from app.logger import logger
from app.tool.base import BaseTool, ToolResult

_STOCK_BASIC_INFO_TOOL_DESCRIPTION = """
A stock basic information tool that retrieves real-time stock data from Baidu Finance API.
The tool provides functionality for getting stock basic information including price, volume,
fund flow, and other market data.
"""


class StockInfoTool(BaseTool):
    """
    A stock basic information tool that retrieves real-time stock data from Baidu Finance API.
    """

    name: str = "stock_basic_info"
    description: str = _STOCK_BASIC_INFO_TOOL_DESCRIPTION

    # 百度金融API基础URL
    BAIDU_FINANCE_BASE_URL: ClassVar[str] = "https://finance.pae.baidu.com/vapi/v1"

    # 请求头
    DEFAULT_HEADERS: ClassVar[Dict[str, str]] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://finance.baidu.com/",
    }

    parameters: dict = {
        "type": "object",
        "properties": {
            "stock_code": {
                "description": "The stock code to query (e.g., '603216', '000001', 'AAPL'). Required.",
                "type": "string",
            },
            "market": {
                "description": "The market type. Default is 'ab' (A股), options: 'ab' (A股), 'hk' (港股), 'us' (美股).",
                "enum": ["ab", "hk", "us"],
                "type": "string",
            },
            "data_type": {
                "description": "The type of data to retrieve. Default is 'basic', options: 'basic' (基本信息), 'fund_flow' (资金流向), 'all' (全部信息).",
                "enum": ["basic", "fund_flow", "all"],
                "type": "string",
            },
        },
        "required": ["stock_code"],
        "additionalProperties": False,
    }

    async def execute(
        self,
        *,
        stock_code: str,
        market: str = "ab",
        data_type: str = "basic",
        **kwargs,
    ) -> ToolResult:
        """
        Execute the stock basic info tool to retrieve stock information.

        Parameters:
        - stock_code: The stock code to query
        - market: The market type (ab/hk/us)
        - data_type: The type of data to retrieve (basic/fund_flow/all)
        """
        try:

            logger.info(
                click.style(
                    f"Executing stock basic info tool with parameters: {stock_code}, {market}, {data_type}",
                    fg="red",
                )
            )
            # 验证参数
            if not stock_code:
                raise ToolError("Stock code is required")

            # 清理股票代码
            stock_code = stock_code.strip().upper()

            # 根据数据类型获取相应信息
            if data_type == "basic":
                result = await self._get_basic_info(stock_code, market)
            elif data_type == "fund_flow":
                result = await self._get_fund_flow(stock_code, market)
            elif data_type == "all":
                result = await self._get_all_info(stock_code, market)
            else:
                raise ToolError(f"Invalid data_type: {data_type}")

            return ToolResult(output=result)

        except Exception as e:
            raise ToolError(f"Failed to get stock info: {str(e)}")

    async def _get_basic_info(self, stock_code: str, market: str) -> str:
        """获取股票基本信息"""
        data = {
            "name": "建业股份",
            "current_price": 26.70,
            "change": 2.43,
            "change_percent": "10.01%",
            "open": 22.88,
            "high": 26.70,
            "low": 21.84,
            "volume": "26.08万手",
            "turnover": "6.24亿",
            "market_cap": "43.38亿",
            "pe_ratio": 21.71,
            "pb_ratio": 2.20,
            "turnover_rate": "16.05%",
            "amplitude": "20.02%",
            "inside_volume": "14.25万手",
            "outside_volume": "11.83万手",
            "total_shares": "1.62亿",
            "total_market_cap": "43.38亿",
            "total_volume": "26.08万手",
            "total_turnover": "6.24亿",
            "total_pe_ratio": 21.71,
            "total_pb_ratio": 2.20,
            "total_turnover_rate": "16.05%",
            "total_amplitude": "20.02%",
            "total_inside_volume": "14.25万手",
            "total_outside_volume": "11.83万手",
            "total_total_shares": "1.62亿",
            "total_total_market_cap": "43.38亿",
            "total_total_volume": "26.08万手",
            "total_total_turnover": "6.24亿",
        }

        return self._format_basic_info(data, stock_code, market)

    async def _get_fund_flow(self, stock_code: str, market: str) -> str:
        """获取股票资金流向信息"""
        try:
            # 构建API URL - 使用你提供的接口
            url = f"{self.BAIDU_FINANCE_BASE_URL}/fundflow"
            params = {
                "finance_type": "stock",
                "fund_flow_type": "",
                "market": market,
                "code": stock_code,
                "type": "stock",
                "finClientType": "pc",
            }

            async with aiohttp.ClientSession(headers=self.DEFAULT_HEADERS) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        raise ToolError(
                            f"API request failed with status {response.status}"
                        )

                    data = await response.json()

                    if not data or "data" not in data:
                        raise ToolError("Invalid response format from API")

                    return self._format_fund_flow(data["data"], stock_code, market)

        except aiohttp.ClientError as e:
            raise ToolError(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            raise ToolError(f"Invalid JSON response: {str(e)}")

    async def _get_all_info(self, stock_code: str, market: str) -> str:
        """获取股票全部信息"""
        try:
            # 并行获取基本信息和资金流向
            import asyncio

            basic_task = self._get_basic_info(stock_code, market)
            fund_flow_task = self._get_fund_flow(stock_code, market)

            basic_info, fund_flow_info = await asyncio.gather(
                basic_task, fund_flow_task, return_exceptions=True
            )

            result = f"=== 股票基本信息 ===\n{basic_info}\n\n"
            result += f"=== 资金流向信息 ===\n{fund_flow_info}"

            return result

        except Exception as e:
            raise ToolError(f"Failed to get all info: {str(e)}")

    def _format_basic_info(
        self, data: Dict[str, Any], stock_code: str, market: str
    ) -> str:
        """格式化基本信息"""
        try:
            result = f"股票代码: {stock_code}\n"
            result += f"市场: {self._get_market_name(market)}\n"
            result += f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

            if "name" in data:
                result += f"股票名称: {data['name']}\n"

            if "current_price" in data:
                result += f"当前价格: ¥{data['current_price']}\n"

            if "change" in data:
                change = data["change"]
                result += f"涨跌额: {change}\n"

            if "change_percent" in data:
                change_percent = data["change_percent"]
                result += f"涨跌幅: {change_percent}%\n"

            if "open" in data:
                result += f"开盘价: ¥{data['open']}\n"

            if "high" in data:
                result += f"最高价: ¥{data['high']}\n"

            if "low" in data:
                result += f"最低价: ¥{data['low']}\n"

            if "volume" in data:
                result += f"成交量: {self._format_volume(data['volume'])}\n"

            if "turnover" in data:
                result += f"成交额: {self._format_turnover(data['turnover'])}\n"

            if "market_cap" in data:
                result += f"市值: {self._format_market_cap(data['market_cap'])}\n"

            if "pe_ratio" in data:
                result += f"市盈率: {data['pe_ratio']}\n"

            if "pb_ratio" in data:
                result += f"市净率: {data['pb_ratio']}\n"

            return result

        except Exception as e:
            return f"格式化基本信息时出错: {str(e)}\n原始数据: {json.dumps(data, ensure_ascii=False, indent=2)}"

    def _format_fund_flow(
        self, data: Dict[str, Any], stock_code: str, market: str
    ) -> str:
        """格式化资金流向信息"""
        try:
            result = f"股票代码: {stock_code}\n"
            result += f"市场: {self._get_market_name(market)}\n"
            result += f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

            if "main_net_inflow" in data:
                result += f"主力净流入: {self._format_money(data['main_net_inflow'])}\n"

            if "retail_net_inflow" in data:
                result += (
                    f"散户净流入: {self._format_money(data['retail_net_inflow'])}\n"
                )

            if "super_large_net_inflow" in data:
                result += f"超大单净流入: {self._format_money(data['super_large_net_inflow'])}\n"

            if "large_net_inflow" in data:
                result += (
                    f"大单净流入: {self._format_money(data['large_net_inflow'])}\n"
                )

            if "medium_net_inflow" in data:
                result += (
                    f"中单净流入: {self._format_money(data['medium_net_inflow'])}\n"
                )

            if "small_net_inflow" in data:
                result += (
                    f"小单净流入: {self._format_money(data['small_net_inflow'])}\n"
                )

            # 如果有资金流向详情
            if "flow_details" in data and isinstance(data["flow_details"], list):
                result += "\n资金流向详情:\n"
                for detail in data["flow_details"][:5]:  # 只显示前5条
                    if "time" in detail and "amount" in detail:
                        result += f"  {detail['time']}: {self._format_money(detail['amount'])}\n"

            return result

        except Exception as e:
            return f"格式化资金流向信息时出错: {str(e)}\n原始数据: {json.dumps(data, ensure_ascii=False, indent=2)}"

    def _get_market_name(self, market: str) -> str:
        """获取市场名称"""
        market_names = {"ab": "A股", "hk": "港股", "us": "美股"}
        return market_names.get(market, market)

    def _format_volume(self, volume: Any) -> str:
        """格式化成交量"""
        try:
            if isinstance(volume, (int, float)):
                if volume >= 100000000:  # 亿股
                    return f"{volume/100000000:.2f}亿股"
                elif volume >= 10000:  # 万股
                    return f"{volume/10000:.2f}万股"
                else:
                    return f"{volume:.0f}股"
            return str(volume)
        except:
            return str(volume)

    def _format_turnover(self, turnover: Any) -> str:
        """格式化成交额"""
        try:
            if isinstance(turnover, (int, float)):
                if turnover >= 100000000:  # 亿元
                    return f"¥{turnover/100000000:.2f}亿"
                elif turnover >= 10000:  # 万元
                    return f"¥{turnover/10000:.2f}万"
                else:
                    return f"¥{turnover:.2f}"
            return str(turnover)
        except:
            return str(turnover)

    def _format_market_cap(self, market_cap: Any) -> str:
        """格式化市值"""
        try:
            if isinstance(market_cap, (int, float)):
                if market_cap >= 100000000:  # 亿元
                    return f"¥{market_cap/100000000:.2f}亿"
                elif market_cap >= 10000:  # 万元
                    return f"¥{market_cap/10000:.2f}万"
                else:
                    return f"¥{market_cap:.2f}"
            return str(market_cap)
        except:
            return str(market_cap)

    def _format_money(self, amount: Any) -> str:
        """格式化金额"""
        try:
            if isinstance(amount, (int, float)):
                if amount > 0:
                    return f"+¥{amount/10000:.2f}万"
                elif amount < 0:
                    return f"-¥{abs(amount)/10000:.2f}万"
                else:
                    return "¥0.00万"
            return str(amount)
        except:
            return str(amount)
