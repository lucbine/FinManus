from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, model_validator

from app.agent.base import BaseAgentEvents
from app.agent.react import ReActAgent
from app.context.browser import BrowserContextHelper
from app.context.toolcall import ToolCallContextHelper
from app.logger import logger
from app.prompt.manus import (
    NEXT_STEP_PROMPT,
    PLAN_PROMPT,
    STOCK_PLAN_PROMPT,
    STOCK_PLAN_PROMPT_ZH,
    SYSTEM_PROMPT,
)
from app.schema import Message
from app.tool import Terminate, ToolCollection
from app.tool.base import BaseTool
from app.tool.bash import Bash
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.create_chat_completion import CreateChatCompletion
from app.tool.deep_research import DeepResearch
from app.tool.file_operators import FileOperator
from app.tool.planning import PlanningTool
from app.tool.stock.stock_info import StockInfoTool
from app.tool.stock.stock_policy import StockPolicyTool
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.web_search import WebSearch

SYSTEM_TOOLS: list[BaseTool] = [
    Bash(),  # 执行命令
    WebSearch(),  # 网络搜索
    DeepResearch(),  # 深度研究
    BrowserUseTool(),  # 浏览器使用
    FileOperator(),  # 文件操作
    StrReplaceEditor(),  # 字符串替换
    PlanningTool(),  # 计划
    CreateChatCompletion(),  # 创建聊天完成
    StockInfoTool(),  # 股票基本信息
    StockPolicyTool(),  # 股票政策查询
]

SYSTEM_TOOLS_MAP = {tool.name: tool.__class__ for tool in SYSTEM_TOOLS}


# 工具配置
class McpToolConfig(BaseModel):
    id: str
    name: str
    # for stdio
    command: str
    args: list[str]
    env: dict[str, str]
    # for sse
    url: str
    headers: dict[str, Any]


# 通用智能体
class Manus(ReActAgent):
    """A versatile general-purpose agent."""

    name: str = "Manus"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )

    # 系统提示词
    system_prompt: str = SYSTEM_PROMPT.format(
        task_id="Not Specified",
        language="English",
        max_steps=20,
        current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
    )

    # 下一步提示词
    next_step_prompt: str = NEXT_STEP_PROMPT.format(
        max_steps=20,
        current_step=0,
        remaining_steps=20,
        task_dir="Not Specified",
    )

    # 计划提示词
    plan_prompt: str = PLAN_PROMPT.format(
        max_steps=20,
        language="English",
        available_tools="",
    )

    # 最大步骤
    max_steps: int = 20
    # 任务请求
    task_request: str = ""

    # 工具
    tools: Optional[list[Union[McpToolConfig, str]]] = None

    # 工具调用上下文助手
    tool_call_context_helper: Optional[ToolCallContextHelper] = None

    # 浏览器上下文助手
    browser_context_helper: Optional[BrowserContextHelper] = None

    # 任务目录
    task_dir: str = ""
    # 语言
    language: Optional[str] = Field(None, description="Language for the agent")

    # 初始化
    def initialize(
        self,
        task_id: str,
        language: Optional[str] = None,
        tools: Optional[list[Union[McpToolConfig, str]]] = None,
        max_steps: Optional[int] = None,
        task_request: Optional[str] = None,
    ):
        self.task_id = task_id
        self.language = language
        self.task_dir = f"/workspace/{task_id}"
        self.current_step = 0
        self.tools = tools

        if max_steps is not None:
            self.max_steps = max_steps

        if task_request is not None:
            self.task_request = task_request

        return self

    # 是 Pydantic v2 中的一个装饰器，用于对模型（Model）进行校验。它是 Pydantic 的新校验机制的一部分，用来定义在模型初始化之后运行的校验逻辑
    @model_validator(mode="after")
    def initialize_helper(self) -> "Manus":
        return self

    # 准备
    async def prepare(self) -> None:
        """Prepare the agent for execution."""
        await super().prepare()
        task_id_without_orgnization_id = self.task_id.split("/")[-1]

        # 系统提示词
        self.system_prompt = SYSTEM_PROMPT.format(
            task_id=task_id_without_orgnization_id,
            language=self.language or "English",
            max_steps=self.max_steps,
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        )

        # 下一步提示词
        self.next_step_prompt = NEXT_STEP_PROMPT.format(
            max_steps=self.max_steps,
            current_step=self.current_step,
            remaining_steps=self.max_steps - self.current_step,
        )

        # 更新记忆
        await self.update_memory(
            role="system", content=self.system_prompt, base64_image=None
        )

        # 浏览器上下文助手
        self.browser_context_helper = BrowserContextHelper(self)
        # 工具调用上下文助手
        self.tool_call_context_helper = ToolCallContextHelper(self)
        # 工具调用上下文助手 可用工具
        self.tool_call_context_helper.available_tools = ToolCollection(Terminate())

        if self.tools:
            for tool in self.tools:
                if isinstance(tool, str) and tool in SYSTEM_TOOLS_MAP:
                    inst = SYSTEM_TOOLS_MAP[tool]()
                    await self.tool_call_context_helper.add_tool(inst)
                    if hasattr(inst, "llm"):
                        inst.llm = self.llm
                    if hasattr(inst, "sandbox"):
                        inst.sandbox = self.sandbox
                elif isinstance(tool, McpToolConfig):
                    await self.tool_call_context_helper.add_mcp(
                        {
                            "client_id": tool.id,
                            "url": tool.url,
                            "command": tool.command,
                            "args": tool.args,
                            "env": tool.env,
                            "headers": tool.headers,
                        }
                    )

    # 计划
    async def plan(self) -> str:
        """Create an initial plan based on the user request."""
        # Create planning message
        self.emit(BaseAgentEvents.LIFECYCLE_PLAN_START, {})

        # 计划提示词
        self.plan_prompt = PLAN_PROMPT.format(
            language=self.language or "English",
            max_steps=self.max_steps,
            available_tools="\n".join(
                [
                    f"- {tool.name}: {tool.description}"
                    for tool in self.tool_call_context_helper.available_tools
                ]
            ),
        )
        planning_message = await self.llm.ask(
            [
                Message.system_message(self.plan_prompt),
                Message.user_message(self.task_request),
            ],
            system_msgs=[Message.system_message(self.system_prompt)],
        )

        # Add the planning message to memory
        await self.update_memory("user", planning_message)
        self.emit(BaseAgentEvents.LIFECYCLE_PLAN_COMPLETE, {"plan": planning_message})
        return planning_message

    # 思考
    async def think(self) -> bool:
        """Process current state and decide next actions with appropriate context."""
        # Update next_step_prompt with current step information
        # 更新下一步提示词
        original_prompt = self.next_step_prompt
        self.next_step_prompt = NEXT_STEP_PROMPT.format(
            max_steps=self.max_steps,
            current_step=self.current_step,
            remaining_steps=self.max_steps - self.current_step,
        )

        # 检查浏览器是否最近使用过
        browser_in_use = self._check_browser_in_use_recently()

        if browser_in_use:
            # 使用浏览器 执行结果 构建下一步提示词
            self.next_step_prompt = (
                await self.browser_context_helper.format_next_step_prompt()
            )

        # 询问工具
        result = await self.tool_call_context_helper.ask_tool()

        # Restore original prompt
        self.next_step_prompt = original_prompt

        return result

    # 行动
    async def act(self) -> str:
        """Execute decided actions"""
        results = await self.tool_call_context_helper.execute_tool()
        return "\n\n".join(results)

    # 检查浏览器是否最近使用过
    def _check_browser_in_use_recently(self) -> bool:
        """Check if the browser is in use by looking at the last 3 messages."""
        recent_messages = self.memory.messages[-3:] if self.memory.messages else []

        # any(iterable)：只要 有一个元素为 True，就返回 True，否则返回 False
        browser_in_use = any(
            tc.function.name == BrowserUseTool().name
            for msg in recent_messages
            if msg.tool_calls
            for tc in msg.tool_calls
        )
        return browser_in_use

    # 清理
    async def cleanup(self):
        """Clean up Manus agent resources."""
        logger.info(f"🧹 Cleaning up resources for agent '{self.name}'...")

        # 清理浏览器
        if self.browser_context_helper:
            await self.browser_context_helper.cleanup_browser()

        # 清理工具
        if self.tool_call_context_helper:
            await self.tool_call_context_helper.cleanup_tools()

        # 清理父类
        await super().cleanup()
        logger.info(f"✨ Cleanup complete for agent '{self.name}'.")


# 股票智能体
class StockManus(ReActAgent):
    """A stock analysis specialized agent."""

    name: str = "StockManus"
    description: str = (
        "A specialized agent for stock analysis, financial research, and investment recommendations"
    )

    # 系统提示词 - 针对股票分析优化
    system_prompt: str = (
        "You are StockManus, a specialized AI financial analyst and stock research assistant. "
        "Your expertise includes:\n"
        "- Fundamental analysis (financial statements, ratios, valuation)\n"
        "- Technical analysis (price patterns, indicators, trends)\n"
        "- Market research and industry analysis\n"
        "- Risk assessment and portfolio management\n"
        "- Investment strategy development\n"
        "- Financial data interpretation and visualization\n\n"
        + SYSTEM_PROMPT.format(
            task_id="Not Specified",
            language="English",
            max_steps=20,
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        )
    )

    # 下一步提示词
    next_step_prompt: str = NEXT_STEP_PROMPT.format(
        max_steps=20,
        current_step=0,
        remaining_steps=20,
        task_dir="Not Specified",
    )

    # 计划提示词 - 使用专门的股票分析计划提示词
    plan_prompt: str = STOCK_PLAN_PROMPT.format(
        language="English",
        available_tools="",
    )

    # 最大步骤
    max_steps: int = 20
    # 任务请求
    task_request: str = ""

    # 工具
    tools: Optional[list[Union[McpToolConfig, str]]] = None

    # 工具调用上下文助手
    tool_call_context_helper: Optional[ToolCallContextHelper] = None
    # 浏览器上下文助手
    browser_context_helper: Optional[BrowserContextHelper] = None
    # 任务目录
    task_dir: str = ""
    # 语言
    language: Optional[str] = Field(None, description="Language for the agent")

    # 初始化
    def initialize(
        self,
        task_id: str,
        language: Optional[str] = None,
        tools: Optional[list[Union[McpToolConfig, str]]] = None,
        max_steps: Optional[int] = None,
        task_request: Optional[str] = None,
    ):
        self.task_id = task_id
        self.language = language
        self.task_dir = f"/workspace/{task_id}"
        self.current_step = 0
        self.tools = tools

        if max_steps is not None:
            self.max_steps = max_steps

        if task_request is not None:
            self.task_request = task_request

        return self

    # 是 Pydantic v2 中的一个装饰器，用于对模型（Model）进行校验。它是 Pydantic 的新校验机制的一部分，用来定义在模型初始化之后运行的校验逻辑
    @model_validator(mode="after")
    def initialize_helper(self) -> "StockManus":
        return self

    # 准备
    async def prepare(self) -> None:
        """Prepare the agent for execution."""
        await super().prepare()
        task_id_without_orgnization_id = self.task_id.split("/")[-1]

        # 系统提示词 - 针对股票分析优化
        self.system_prompt = (
            "You are StockManus, a specialized AI financial analyst and stock research assistant. "
            "Your expertise includes:\n"
            "- Fundamental analysis (financial statements, ratios, valuation)\n"
            "- Technical analysis (price patterns, indicators, trends)\n"
            "- Market research and industry analysis\n"
            "- Risk assessment and portfolio management\n"
            "- Investment strategy development\n"
            "- Financial data interpretation and visualization\n\n"
            + SYSTEM_PROMPT.format(
                task_id=task_id_without_orgnization_id,
                language=self.language or "English",
                max_steps=self.max_steps,
                current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            )
        )

        # 下一步提示词
        self.next_step_prompt = NEXT_STEP_PROMPT.format(
            max_steps=self.max_steps,
            current_step=self.current_step,
            remaining_steps=self.max_steps - self.current_step,
        )

        # 更新记忆
        await self.update_memory(
            role="system", content=self.system_prompt, base64_image=None
        )

        # 浏览器上下文助手
        self.browser_context_helper = BrowserContextHelper(self)
        # 工具调用上下文助手
        self.tool_call_context_helper = ToolCallContextHelper(self)
        # 工具调用上下文助手 可用工具
        self.tool_call_context_helper.available_tools = ToolCollection(Terminate())

        if self.tools:
            for tool in self.tools:
                if isinstance(tool, str) and tool in SYSTEM_TOOLS_MAP:
                    inst = SYSTEM_TOOLS_MAP[tool]()
                    await self.tool_call_context_helper.add_tool(inst)
                    if hasattr(inst, "llm"):
                        inst.llm = self.llm
                    if hasattr(inst, "sandbox"):
                        inst.sandbox = self.sandbox
                elif isinstance(tool, McpToolConfig):
                    await self.tool_call_context_helper.add_mcp(
                        {
                            "client_id": tool.id,
                            "url": tool.url,
                            "command": tool.command,
                            "args": tool.args,
                            "env": tool.env,
                            "headers": tool.headers,
                        }
                    )

    # 计划
    async def plan(self) -> str:
        """Create an initial plan based on the user request."""
        # Create planning message
        self.emit(BaseAgentEvents.LIFECYCLE_PLAN_START, {})

        # 根据语言选择相应的计划提示词
        if self.language and self.language.lower() in [
            "chinese",
            "zh",
            "zh-cn",
            "zh-tw",
        ]:
            plan_prompt_template = STOCK_PLAN_PROMPT_ZH
        else:
            plan_prompt_template = STOCK_PLAN_PROMPT

        # 计划提示词 - 使用专门的股票分析计划提示词
        self.plan_prompt = plan_prompt_template.format(
            language=self.language or "English",
            available_tools="\n".join(
                [
                    f"- {tool.name}: {tool.description}"
                    for tool in self.tool_call_context_helper.available_tools
                ]
            ),
        )
        planning_message = await self.llm.ask(
            [
                Message.system_message(self.plan_prompt),
                Message.user_message(self.task_request),
            ],
            system_msgs=[Message.system_message(self.system_prompt)],
        )

        # Add the planning message to memory
        await self.update_memory("user", planning_message)
        self.emit(BaseAgentEvents.LIFECYCLE_PLAN_COMPLETE, {"plan": planning_message})
        return planning_message

    # 思考
    async def think(self) -> bool:
        """Process current state and decide next actions with appropriate context."""
        # Update next_step_prompt with current step information
        original_prompt = self.next_step_prompt
        self.next_step_prompt = NEXT_STEP_PROMPT.format(
            max_steps=self.max_steps,
            current_step=self.current_step,
            remaining_steps=self.max_steps - self.current_step,
        )

        browser_in_use = self._check_browser_in_use_recently()

        if browser_in_use:
            self.next_step_prompt = (
                await self.browser_context_helper.format_next_step_prompt()
            )

        result = await self.tool_call_context_helper.ask_tool()

        # Restore original prompt
        self.next_step_prompt = original_prompt

        return result

    # 行动
    async def act(self) -> str:
        """Execute decided actions"""
        results = await self.tool_call_context_helper.execute_tool()
        return "\n\n".join(results)

    # 检查浏览器是否最近使用过
    def _check_browser_in_use_recently(self) -> bool:
        """Check if the browser is in use by looking at the last 3 messages."""
        recent_messages = self.memory.messages[-3:] if self.memory.messages else []
        browser_in_use = any(
            tc.function.name == BrowserUseTool().name
            for msg in recent_messages
            if msg.tool_calls
            for tc in msg.tool_calls
        )
        return browser_in_use

    # 清理
    async def cleanup(self):
        """Clean up Manus agent resources."""
        logger.info(f"🧹 Cleaning up resources for agent '{self.name}'...")

        # 清理浏览器
        if self.browser_context_helper:
            await self.browser_context_helper.cleanup_browser()

        # 清理工具
        if self.tool_call_context_helper:
            await self.tool_call_context_helper.cleanup_tools()

        # 清理父类
        await super().cleanup()
        logger.info(f"✨ Cleanup complete for agent '{self.name}'.")


# 构建智能体
class AgentFactory:

    @staticmethod
    def get_agent_class(agent_name: str):
        """获取智能体类"""
        if agent_name == "Manus":
            return Manus
        elif agent_name == "StockManus":
            return StockManus
        else:
            raise ValueError(f"Invalid agent name: {agent_name}")

    @staticmethod
    def create_agent(agent_name: str, **kwargs) -> ReActAgent:
        """创建智能体实例"""
        agent_class = AgentFactory.get_agent_class(agent_name)
        return agent_class(**kwargs)
