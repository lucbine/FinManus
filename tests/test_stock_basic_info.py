import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.tool.stock.stock_info import StockInfoTool


class TestStockBasicInfoTool:
    """测试股票基本信息工具"""

    @pytest.fixture
    def tool(self):
        """创建工具实例"""
        return StockInfoTool()

    def test_tool_initialization(self, tool):
        """测试工具初始化"""
        assert tool.name == "stock_basic_info"
        assert "stock basic information" in tool.description.lower()
        assert "stock_code" in tool.parameters["properties"]
        assert "market" in tool.parameters["properties"]
        assert "data_type" in tool.parameters["properties"]

    def test_parameters_validation(self, tool):
        """测试参数验证"""
        # 测试必需参数
        required_params = tool.parameters["required"]
        assert "stock_code" in required_params

        # 测试可选参数
        properties = tool.parameters["properties"]
        assert properties["market"]["enum"] == ["ab", "hk", "us"]
        assert properties["data_type"]["enum"] == ["basic", "fund_flow", "all"]

    @pytest.mark.asyncio
    async def test_execute_with_invalid_stock_code(self, tool):
        """测试无效股票代码"""
        with pytest.raises(Exception) as exc_info:
            await tool.execute(stock_code="")
        assert "Stock code is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_with_invalid_data_type(self, tool):
        """测试无效数据类型"""
        with pytest.raises(Exception) as exc_info:
            await tool.execute(stock_code="603216", data_type="invalid")
        assert "Invalid data_type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_basic_info_success(self, tool):
        """测试获取基本信息成功"""
        # 模拟API响应
        mock_response_data = {
            "data": {
                "name": "测试股票",
                "current_price": 10.50,
                "change": 0.25,
                "change_percent": 2.44,
                "open": 10.20,
                "high": 10.80,
                "low": 10.15,
                "volume": 1000000,
                "turnover": 10500000,
                "market_cap": 1000000000,
                "pe_ratio": 15.5,
                "pb_ratio": 2.1,
            }
        }

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            result = await tool._get_basic_info("603216", "ab")

            assert "股票代码: 603216" in result
            assert "市场: A股" in result
            assert "股票名称: 测试股票" in result
            assert "当前价格: ¥10.5" in result
            assert "涨跌额: 0.25" in result
            assert "涨跌幅: 2.44%" in result

    @pytest.mark.asyncio
    async def test_get_fund_flow_success(self, tool):
        """测试获取资金流向成功"""
        # 模拟API响应
        mock_response_data = {
            "data": {
                "main_net_inflow": 5000000,
                "retail_net_inflow": -2000000,
                "super_large_net_inflow": 3000000,
                "large_net_inflow": 2000000,
                "medium_net_inflow": -1000000,
                "small_net_inflow": -1000000,
                "flow_details": [
                    {"time": "09:30", "amount": 1000000},
                    {"time": "10:00", "amount": 2000000},
                ],
            }
        }

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            result = await tool._get_fund_flow("603216", "ab")

            assert "股票代码: 603216" in result
            assert "市场: A股" in result
            assert "主力净流入: +¥500.00万" in result
            assert "散户净流入: -¥200.00万" in result

    @pytest.mark.asyncio
    async def test_api_request_failure(self, tool):
        """测试API请求失败"""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 404

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            with pytest.raises(Exception) as exc_info:
                await tool._get_basic_info("603216", "ab")
            assert "API request failed with status 404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_network_error(self, tool):
        """测试网络错误"""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.return_value.__aenter__.return_value.get.side_effect = (
                Exception("Network error")
            )

            with pytest.raises(Exception) as exc_info:
                await tool._get_basic_info("603216", "ab")
            assert "Network error" in str(exc_info.value)

    def test_format_volume(self, tool):
        """测试成交量格式化"""
        assert tool._format_volume(100000000) == "1.00亿股"
        assert tool._format_volume(50000000) == "5000.00万股"
        assert tool._format_volume(1000) == "1000股"

    def test_format_turnover(self, tool):
        """测试成交额格式化"""
        assert tool._format_turnover(100000000) == "¥1.00亿"
        assert tool._format_turnover(50000000) == "¥5000.00万"
        assert tool._format_turnover(1000) == "¥1000.00"

    def test_format_money(self, tool):
        """测试金额格式化"""
        assert tool._format_money(1000000) == "+¥100.00万"
        assert tool._format_money(-500000) == "-¥50.00万"
        assert tool._format_money(0) == "¥0.00万"

    def test_get_market_name(self, tool):
        """测试市场名称获取"""
        assert tool._get_market_name("ab") == "A股"
        assert tool._get_market_name("hk") == "港股"
        assert tool._get_market_name("us") == "美股"
        assert tool._get_market_name("unknown") == "unknown"

    @pytest.mark.asyncio
    async def test_execute_basic_info(self, tool):
        """测试执行基本信息获取"""
        # 模拟API响应
        mock_response_data = {
            "data": {
                "name": "测试股票",
                "current_price": 10.50,
                "change": 0.25,
                "change_percent": 2.44,
            }
        }

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            result = await tool.execute(stock_code="603216", data_type="basic")

            assert result.output is not None
            assert "股票代码: 603216" in result.output
            assert "股票名称: 测试股票" in result.output

    @pytest.mark.asyncio
    async def test_execute_fund_flow(self, tool):
        """测试执行资金流向获取"""
        # 模拟API响应
        mock_response_data = {
            "data": {"main_net_inflow": 5000000, "retail_net_inflow": -2000000}
        }

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            result = await tool.execute(stock_code="603216", data_type="fund_flow")

            assert result.output is not None
            assert "股票代码: 603216" in result.output
            assert "主力净流入" in result.output


if __name__ == "__main__":
    pytest.main([__file__])
