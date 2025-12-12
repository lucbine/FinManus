"""Collection classes for managing multiple tools."""

from typing import Any, Dict, List

from app.exceptions import ToolError
from app.tool.base import BaseTool, ToolFailure, ToolResult

# 工具集合


class ToolCollection:
    """A collection of defined tools."""

    # 工具列表
    tools: List[BaseTool] = []
    # 工具映射
    tool_map: Dict[str, BaseTool] = {}

    class Config:
        arbitrary_types_allowed = True

    # 初始化
    def __init__(self, *tools: BaseTool):
        self.tools = tools
        self.tool_map = {tool.name: tool for tool in tools}

    # 迭代器
    def __iter__(self):
        return iter(self.tools)

    # 转换为参数
    def to_params(self) -> List[Dict[str, Any]]:
        return [tool.to_param() for tool in self.tools]

    # 执行工具
    async def execute(
        self, *, name: str, tool_input: Dict[str, Any] = None
    ) -> ToolResult:
        tool = self.tool_map.get(name)
        if not tool:
            return ToolFailure(error=f"Tool {name} is invalid")
        try:
            result = await tool(**tool_input)
            return result
        except ToolError as e:
            return ToolFailure(error=e.message)

    # 执行所有工具
    async def execute_all(self) -> List[ToolResult]:
        """Execute all tools in the collection sequentially."""
        results = []
        for tool in self.tools:
            try:
                result = await tool()
                results.append(result)
            except ToolError as e:
                results.append(ToolFailure(error=e.message))
        return results

    # 获取工具
    def get_tool(self, name: str) -> BaseTool:
        return self.tool_map.get(name)

    # 添加工具
    def add_tool(self, tool: BaseTool):
        self.tools += (tool,)
        self.tool_map[tool.name] = tool
        return self

    # 添加多个工具
    def add_tools(self, *tools: BaseTool):
        for tool in tools:
            self.add_tool(tool)
        return self
