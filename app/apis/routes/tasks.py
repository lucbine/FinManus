import asyncio
import json
from json import dumps
from pathlib import Path
from typing import List, Optional, Union, cast

import nanoid
from fastapi import APIRouter, Body, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.agent.base import BaseAgentEvents
from app.agent.manus import AgentFactory, Manus, McpToolConfig
from app.apis.services.task_manager import task_manager
from app.config import LLMSettings, config
from app.llm import LLM
from app.logger import logger

# 任务路由
router = APIRouter(prefix="/tasks", tags=["tasks"])

AGENT_NAME = "Manus"


# 任务事件处理
async def handle_agent_event(task_id: str, event_name: str, step: int, **kwargs):
    """Handle agent events and update task status.

    Args:
        event_name: Name of the event
        **kwargs: Additional parameters related to the event
    """
    if not task_id:
        logger.warning(f"No task_id provided for event: {event_name}")
        return

    # 更新任务进度
    await task_manager.update_task_progress(
        task_id=task_id, event_name=event_name, step=step, **kwargs
    )


# 运行任务
async def run_task(task_id: str, prompt: str):
    """Run the task and set up corresponding event handlers.

    Args:
        task_id: Task ID
        prompt: Task prompt
        llm_config: Optional LLM configuration
    """
    try:
        task = task_manager.tasks[task_id]
        agent = task.agent

        # 设置正则表达式，匹配所有事件
        event_patterns = [r"agent:.*"]

        # 注册每个事件模式的事件处理程序
        # lambda 关键字在 Python 中用于创建匿名函数 lambda 参数1, 参数2, ... : 表达式
        for pattern in event_patterns:
            agent.on(
                pattern,
                lambda event_name, step, **kwargs: handle_agent_event(
                    task_id=task_id,
                    event_name=event_name,
                    step=step,
                    **{k: v for k, v in kwargs.items() if k != "task_id"},
                ),
            )

        # 运行任务
        await agent.run(prompt)

        # 清理任务
        await agent.cleanup()
    except Exception as e:
        logger.exception(f"Error in task {task_id}: {str(e)}")


# 解析工具
def parse_tools(tools: list[str]) -> list[Union[str, McpToolConfig]]:
    """Parse tools list which may contain both tool names and MCP configurations.

    Args:
        tools: List of tool strings, which can be either tool names or MCP config JSON strings

    Returns:
        List of processed tools, containing both tool names and McpToolConfig objects

    Raises:
        HTTPException: If any tool configuration is invalid
    """
    processed_tools = []
    for tool in tools:
        try:
            tool_config = json.loads(tool)
            if isinstance(tool_config, dict):
                mcp_tool = McpToolConfig.model_validate(tool_config)
                processed_tools.append(mcp_tool)
            else:
                processed_tools.append(tool)
        except json.JSONDecodeError:
            processed_tools.append(tool)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid tool configuration for '{tool}': {str(e)}",
            )
    return processed_tools


# 请求体结构定义
class TaskRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="任务提示词，必填")
    agent_name: Optional[str] = Field(AGENT_NAME, description="智能体名称")
    task_id: Optional[str] = Field(
        None, min_length=1, description="任务ID，格式为 organization_id/task_id"
    )
    should_plan: bool = Field(False, description="是否启用规划 默认false")
    tools: Optional[List[str]] = Field(None, description="工具列表")
    preferences: Optional[dict] = Field(None, description="偏好设置")
    llm_config: Optional[dict] = Field(None, description="LLM配置")
    files: Optional[List[UploadFile]] = Field(None, description="文件列表")


# 创建任务
@router.post("/create")
async def create_task(taskRequest: TaskRequest):
    """
    创建任务，创建任务时，会创建一个任务实例，并返回任务ID
    task_id: 任务ID，如果不传则自动生成
    prompt: 任务提示，不能为空
    should_plan: 是否启用计划
    tools: 工具列表
    preferences: 偏好设置
    llm_config: LLM配置
    """

    prompt = taskRequest.prompt
    task_id = taskRequest.task_id
    should_plan = taskRequest.should_plan
    tools = taskRequest.tools
    preferences = taskRequest.preferences
    llm_config = taskRequest.llm_config
    files = taskRequest.files
    agent_name = taskRequest.agent_name

    # 验证 prompt 不能为空
    if not prompt or not prompt.strip():
        raise HTTPException(status_code=400, detail="prompt cannot be empty")

    # 如果没有提供 task_id，则自动生成一个
    if not task_id:
        task_id = (
            nanoid.generate(size=25) + "/" + nanoid.generate(size=25)
        )  # 生成一个25位的唯一标识符

    logger.info(
        f"Creating task {task_id} with prompt: {prompt}, should_plan: {should_plan}, tools: {tools}, preferences: {preferences}, llm_config: {llm_config}"
    )

    # Parse preferences and llm_config from JSON strings
    preferences_dict = None
    if preferences:
        try:
            # 如果已经是字典，直接使用
            if isinstance(preferences, dict):
                preferences_dict = preferences
            else:
                preferences_dict = json.loads(preferences)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid preferences format: {str(e)}",
            )

    llm_config_obj = None
    if llm_config:
        try:
            # 如果已经是字典，直接使用 model_validate
            if isinstance(llm_config, dict):
                llm_config_obj = LLMSettings.model_validate(llm_config)
            else:
                llm_config_obj = LLMSettings.model_validate_json(llm_config)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid llm_config format: {str(e)}"
            )

    # 解析工具
    processed_tools = parse_tools(tools or [])

    # 使用工厂模式创建智能体
    agent = AgentFactory.create_agent(
        agent_name=agent_name or AGENT_NAME,
        name=agent_name,
        description="A versatile agent that can solve various tasks using multiple tools",
        should_plan=should_plan,
        llm=(
            LLM(config_name=task_id, llm_config=llm_config_obj)
            if llm_config_obj
            else None
        ),
        enable_event_queue=True,  # Enable event queue
    )

    # 创建任务
    task = task_manager.create_task(task_id, agent)

    # 初始化任务
    task.agent.initialize(
        task_id,
        language=(
            preferences_dict.get("language", "English") if preferences_dict else None
        ),
        tools=processed_tools,
        task_request=prompt,
    )

    if files:
        import os

        task_dir = Path(
            os.path.join(
                config.workspace_root,
                task.agent.task_dir.replace("/workspace/", ""),
            )
        )
        task_dir.mkdir(parents=True, exist_ok=True)
        for file in files or []:
            # 保存文件
            logger.info("save file, task_dir: %s, file: %s", task_dir, file.filename)
            file = cast(UploadFile, file)
            try:
                safe_filename = Path(file.filename).name
                if not safe_filename:
                    raise HTTPException(status_code=400, detail="Invalid filename")

                file_path = task_dir / safe_filename

                MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
                file_content = file.file.read()
                if len(file_content) > MAX_FILE_SIZE:
                    raise HTTPException(status_code=400, detail="File too large")

                # 保存文件
                with open(file_path, "wb") as f:
                    f.write(file_content)

            except Exception as e:
                logger.error(f"Error saving file {file.filename}: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"Error saving file: {str(e)}"
                )

        # 更新任务提示，添加文件信息
        prompt = (
            prompt
            + "\n\n"
            + "Here are the files I have uploaded: "
            + "\n\n".join([f"File: {file.filename}" for file in files])
        )
    # 创建任务 并运行任务
    """
    asyncio.create_task() 是 Python asyncio 库中的核心函数，用于并发执行协程（coroutines）。它的主要作用是将一个协程包装成 Task 对象并立即调度到事件循环中执行，允许程序在后台运行多个异步操作而不阻塞主线程。
    """
    asyncio.create_task(run_task(task.id, prompt))
    return {"task_id": task.id}


class EventRequest(BaseModel):
    task_id: str = Field(..., description="任务ID，必填")
    organization_id: str = Field(..., description="组织ID，必填")


# 获取任务事件
# organization_id 用于实现多租户（Multi-tenant）架构、
# 每个组织（organization）有自己独立的任务空间
# 确保不同组织之间的数据隔离
@router.post("/events")
async def task_events(eventRequest: EventRequest):
    # StreamingResponse 是 FastAPI 提供的一个响应类，用于流式传输数据。它允许服务器在响应中逐步发送数据，而不是一次性发送所有数据。
    # 这对于处理大型数据集或需要实时更新的场景非常有用。
    return StreamingResponse(
        event_generator(f"{eventRequest.organization_id}/{eventRequest.task_id}"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# 事件生成器，用于生成事件流
async def event_generator(task_id: str):

    # 如果任务不存在，则返回错误
    if task_id not in task_manager.queues:
        yield f"event: error\ndata: {dumps({'message': 'Task not found'})}\n\n"
        return

    queue = task_manager.queues[task_id]

    while True:
        try:
            # 超时控制
            event = await asyncio.wait_for(queue.get(), timeout=10)
            formatted_event = dumps(event)

            # 如果事件没有类型，则返回心跳
            if not event.get("type"):
                yield ":heartbeat\n\n"
                continue

            # yield 会把函数变成一个生成器，每次调用时返回一个值并暂停函数执行，等下次继续从上次的位置继续运行。
            # Send actual event data（发送实际事件数据）
            yield f"data: {formatted_event}\n\n"

            # 如果事件类型为生命周期完成，则结束事件流
            if event.get("event_name") == BaseAgentEvents.LIFECYCLE_COMPLETE:
                break
        except asyncio.TimeoutError:
            # 超时返回心跳
            yield ":heartbeat\n\n"
            continue
        except asyncio.CancelledError:
            # 客户端断开连接
            logger.warning(f"Client disconnected for task {task_id}")
            break
        except Exception as e:
            # 错误
            logger.exception(f"Error in event stream: {str(e)}")
            yield f"event: error\ndata: {dumps({'message': str(e)})}\n\n"
            break
    # 移除任务
    await task_manager.remove_task(task_id)


# 获取任务列表
@router.get("")
async def get_tasks():
    sorted_tasks = sorted(
        task_manager.tasks.values(), key=lambda task: task.created_at, reverse=True
    )
    return JSONResponse(
        content=[task.model_dump() for task in sorted_tasks],
        headers={"Content-Type": "application/json"},
    )


class RestartTaskRequest(BaseModel):
    task_id: str = Field(..., min_length=1, description="任务ID，必填")
    prompt: str = Field(..., min_length=1, description="任务提示词，必填")
    should_plan: Optional[bool] = Field(None, description="是否启用规划 默认false")
    tools: Optional[List[str]] = Field(None, description="工具列表")
    preferences: Optional[dict] = Field(None, description="偏好设置")
    llm_config: Optional[dict] = Field(None, description="LLM配置")
    history: Optional[List[dict]] = Field(None, description="历史记录")
    files: Optional[List[UploadFile]] = Field([], description="文件列表")


# 重启任务(有历史记录)
@router.post("/restart")
async def restart_task(
    restartTaskRequest: RestartTaskRequest,
):
    """Restart a task."""
    task_id = restartTaskRequest.task_id
    prompt = restartTaskRequest.prompt
    should_plan = restartTaskRequest.should_plan
    tools = restartTaskRequest.tools
    preferences = restartTaskRequest.preferences
    llm_config = restartTaskRequest.llm_config
    history = restartTaskRequest.history
    files = restartTaskRequest.files

    # Parse JSON strings
    preferences_dict = None
    if preferences:
        try:
            if isinstance(preferences, dict):
                preferences_dict = preferences
            else:
                preferences_dict = json.loads(preferences)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="Invalid preferences JSON format"
            )

    llm_config_obj = None
    if llm_config:
        try:
            if isinstance(llm_config, dict):
                llm_config_obj = LLMSettings.model_validate(llm_config)
            else:
                llm_config_obj = LLMSettings.model_validate_json(llm_config)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid llm_config format: {str(e)}"
            )

    history_list = None
    if history:
        try:
            if isinstance(history, list):
                history_list = history
            else:
                history_list = json.loads(history)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid history JSON format")

    processed_tools = parse_tools(tools or [])

    if task_id in task_manager.tasks:
        task = task_manager.tasks[task_id]
        await task.agent.terminate()

    task = task_manager.create_task(
        task_id,
        Manus(
            name=AGENT_NAME,
            description="A versatile agent that can solve various tasks using multiple tools",
            should_plan=should_plan,
            llm=(
                LLM(config_name=task_id, llm_config=llm_config_obj)
                if llm_config_obj
                else None
            ),
            enable_event_queue=True,
        ),
    )

    if history_list:
        for message in history_list:
            if message["role"] == "user":
                await task.agent.update_memory(role="user", content=message["message"])
            else:
                await task.agent.update_memory(
                    role="assistant", content=message["message"]
                )

    task.agent.initialize(
        task_id,
        language=(
            preferences_dict.get("language", "English") if preferences_dict else None
        ),
        tools=processed_tools,
        task_request=prompt,
    )

    if files:
        import os

        task_dir = Path(os.path.join(config.workspace_root, task.agent.task_dir))
        task_dir.mkdir(parents=True, exist_ok=True)

        for file in files or []:
            file = cast(UploadFile, file)
            try:
                safe_filename = Path(file.filename).name
                if not safe_filename:
                    raise HTTPException(status_code=400, detail="Invalid filename")

                file_path = task_dir / safe_filename

                MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
                file_content = file.file.read()
                if len(file_content) > MAX_FILE_SIZE:
                    raise HTTPException(status_code=400, detail="File too large")

                with open(file_path, "wb") as f:
                    f.write(file_content)

            except Exception as e:
                logger.error(f"Error saving file {file.filename}: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"Error saving file: {str(e)}"
                )
        prompt = (
            prompt
            + "\n\n"
            + "Here are the files I have uploaded: "
            + "\n\n".join([f"File: {file.filename}" for file in files])
        )

    asyncio.create_task(run_task(task.id, prompt))
    return {"task_id": task.id}


# 终止任务
class TerminateTaskRequest(BaseModel):
    task_id: str = Field(..., min_length=1, description="任务ID，必填")


@router.post("/terminate")
async def terminate_task(terminateTaskRequest: TerminateTaskRequest):
    """Terminate a task immediately.

    Args:
        task_id: The ID of the task to terminate
    """
    task_id = terminateTaskRequest.task_id
    if task_id not in task_manager.tasks:
        return {"message": f"Task {task_id} not found"}

    task = task_manager.tasks[task_id]
    await task.agent.terminate()

    return {"message": f"Task {task_id} terminated successfully", "task_id": task_id}


# 获取可用的智能体类型
@router.get("/agents")
async def get_available_agents_list():
    """获取所有可用的智能体类型"""
    agents = ["Manus", "StockManus"]
    return {
        "agents": agents,
        "count": len(agents),
        "description": "Available agent types for task creation",
    }
